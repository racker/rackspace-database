# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.    You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys

try:
    import simplejson as json
except:
    import json

from libcloud.utils.py3 import httplib, urlparse
from libcloud.common.types import MalformedResponseError, LibcloudError
from libcloud.common.types import LazyList
from libcloud.common.base import Response

from rackspace_database.providers import Provider
from rackspace_database.base import (DatabaseDriver, Instance,
                            InstanceStatus, Flavor, Database, User)

from libcloud.common.rackspace import AUTH_URL_US
from libcloud.common.openstack import OpenStackBaseConnection,\
    OpenStackDriverMixin

API_VERSION = 'v1.0'
API_URL = 'https://ord.databases.api.rackspacecloud.com/%s' % (API_VERSION)


class RackspaceDatabaseValidationError(LibcloudError):

    def __init__(self, code, type, message, details, driver):
        self.code = code
        self.type = type
        self.message = message
        self.details = details
        super(RackspaceDatabaseValidationError, self).__init__(value=message,
                                                                 driver=driver)

    def __repr__(self):
        string = '<ValidationError type=%s, ' % (self.type)
        string += 'message="%s", details=%s>' % (self.message, self.details)
        return string


class RackspaceDatabaseResponse(Response):

    valid_response_codes = [httplib.CONFLICT]

    def success(self):
        i = int(self.status)
        return i >= 200 and i <= 299 or i in self.valid_response_codes

    def parse_body(self):
        if not self.body:
            return None

        if 'content-type' in self.headers:
            key = 'content-type'
        elif 'Content-Type' in self.headers:
            key = 'Content-Type'
        else:
            raise LibcloudError('Missing content-type header')

        content_type = self.headers[key]
        if content_type.find(';') != -1:
            content_type = content_type.split(';')[0]

        if content_type == 'application/json':
            try:
                data = json.loads(self.body)
            except:
                raise MalformedResponseError('Failed to parse JSON',
                                             body=self.body,
                                             driver=RackspaceDatabaseDriver)
        elif content_type == 'text/plain':
            data = self.body
        else:
            data = self.body

        return data

    def parse_error(self):
        body = self.parse_body()
        if self.status == httplib.BAD_REQUEST:
            error = RackspaceDatabaseValidationError(message=body['message'],
                                               code=body['code'],
                                               type=body['type'],
                                               details=body['details'],
                                               driver=self.connection.driver)
            raise error

        return body


class RackspaceDatabaseConnection(OpenStackBaseConnection):
    """
    Base connection class for the Rackspace Monitoring driver.
    """

    type = Provider.RACKSPACE
    responseCls = RackspaceDatabaseResponse
    auth_url = AUTH_URL_US
    _url_key = "database_url"

    def __init__(self, user_id, key, secure=True, ex_force_region='ord',
                 **kwargs):
        super(RackspaceDatabaseConnection, self).__init__(user_id, key, secure,
                                                          **kwargs)
        self.api_version = API_VERSION
        self.accept_format = 'application/json'
        self._ex_force_region = ex_force_region

    def request(self, action, params=None, data='', headers=None, method='GET',
                raw=False):
        if not headers:
            headers = {}
        if not params:
            params = {}

        headers['Accept'] = 'application/json'

        if method in ['POST', 'PUT']:
            headers['Content-Type'] = 'application/json; charset=UTF-8'
            data = json.dumps(data)

        return super(RackspaceDatabaseConnection, self).request(
            action=action,
            params=params, data=data,
            method=method, headers=headers,
            raw=raw
        )

    def get_endpoint(self):
        region = self._ex_force_region

        if '1.1' in self._auth_version:
            ep = self.service_catalog.get_endpoint(name='cloudDatabases',
                                                   region=region.upper())
            return ep['publicURL']

        if '2.0' in self._auth_version:
            ep = self.service_catalog.get_endpoint(
                name='cloudDatabases', service_type='rax:database',
                region=region.upper())
            return ep['publicURL']

        raise LibcloudError('Could not find specified endpoint')


class RackspaceDatabaseDriver(DatabaseDriver, OpenStackDriverMixin):
    """
    Base Rackspace Database driver.

    """
    name = 'Rackspace Monitoring'
    connectionCls = RackspaceDatabaseConnection

    def __init__(self, *args, **kwargs):
        OpenStackDriverMixin.__init__(self, *args, **kwargs)
        self._ex_force_region = kwargs.pop('ex_force_region', None)
        super(RackspaceDatabaseDriver, self).__init__(*args, **kwargs)

    def _ex_connection_class_kwargs(self):
        kwargs = self.openstack_connection_kwargs()
        if self._ex_force_region:
            kwargs['ex_force_region'] = self._ex_force_region

        return kwargs

    def _get_request(self, value_dict):
        key = None

        params = value_dict.get('params', {})

        response = self.connection.request(value_dict['url'], params)

        # newdata, self._last_key, self._exhausted
        if response.status == httplib.NO_CONTENT:
            return []
        elif response.status == httplib.OK:
            resp = json.loads(response.body)
            l = None

            if 'namespace' in value_dict:
                resp = resp[value_dict['namespace']]

            if 'list_item_mapper' in value_dict:
                func = value_dict['list_item_mapper']
                l = [func(x, value_dict) for x in resp]
            else:
                l = value_dict['object_mapper'](resp, value_dict)

            return l

        body = json.loads(response.body)

        details = body['details'] if 'details' in body else ''
        raise LibcloudError('Unexpected status code: %s (url=%s, details=%s)' %
                            (response.status, value_dict['url'], details))

    def _request(self, value_dict, method):
        key = None

        params = value_dict.get('params', {})
        data = value_dict.get('data', {})
        url = value_dict.get('url')

        # TODO: this is so obviously a flaw in the API, returning a message
        # that says 'The request is accepted for processing.' along
        # with a 202 status is redundant and makes
        # me have to do hacks like this
        expects_response = value_dict.get('list_item_mapper') or\
                value_dict.get('object_mapper')

        response = self.connection.request(url,
                method=method, data=data, params=params)

        if response.status == httplib.NO_CONTENT or not expects_response:
            return []
        elif response.status == httplib.OK:
            resp = json.loads(response.body)
            l = None

            if 'namespace' in value_dict:
                resp = resp[value_dict['namespace']]

            if 'list_item_mapper' in value_dict:
                func = value_dict['list_item_mapper']
                l = [func(x, value_dict) for x in resp]
            else:
                l = value_dict['object_mapper'](resp, value_dict)

            return l

        body = json.loads(response.body)

        details = body['details'] if 'details' in body else ''
        raise LibcloudError('Unexpected status code: %s (url=%s, details=%s)' %
                            (response.status, value_dict['url'], details))

    def _post_request(self, value_dict):
        return self._request(value_dict, 'POST')

    def _delete_request(self, value_dict):
        return self._request(value_dict, 'DELETE')

    def __extract_flavor_ref(self, obj):
        for link in obj['links']:
            if link['rel'] == 'self':
                return link['href']

    def _to_database(self, obj, value_dict):
        return Database(obj['name'],
                character_set=obj.get('character_set', None),
                collate=obj.get('collate', None))

    def _from_database(self, database):
        d = dict()
        d['name'] = database.name
        if database.character_set:
            d['character_set'] = database.character_set
        if database.collate:
            d['collate'] = database.collate
        return d

    def _to_instance(self, obj, value_dict):
        status = InstanceStatus.__dict__[obj['status']]
        flavorRef = self.__extract_flavor_ref(obj['flavor'])
        rootEnabled = obj.get('rootEnabled')
        if obj.get('databases'):
            databases = [self._to_database(d, value_dict) for d
                in obj.get('databases', [])]
        else:
            databases = None

        if obj.get('volume') and obj['volume'].get('size'):
            size = obj['volume']['size']
        else:
            size = None

        return Instance(flavorRef, size=size, id=obj['id'],
                name=obj['name'], status=status, rootEnabled=rootEnabled,
                databases=databases)

    def _from_instance(self, instance):
        d = {'flavorRef': instance.flavorRef,
            'volume': {'size': instance.size}
        }
        if instance.id:
            d['id'] = instance.id
        if instance.name:
            d['name'] = instance.name
        if instance.databases:
            d['databases'] = [self._from_database(x)
                    for x in instance.databases]
        if instance.rootEnabled:
            d['rootEnabled'] = instance.rootEnabled
        return d

    def _to_flavor(self, obj, value_dict):
        href = self.__extract_flavor_ref(obj)
        return Flavor(obj['id'], obj['name'],
                obj['vcpus'], obj['ram'], href)

    def _to_user(self, obj, value_dict):
        return User(obj['name'], password=obj.get('password', None))

    def _from_user(self, user):
        d = dict()
        d['name'] = user.name
        if user.password:
            d['password'] = user.password
        return d

    def list_instances(self):
        value_dict = {'url': '/instances/detail',
                'namespace': 'instances',
                'list_item_mapper': self._to_instance}
        return self._get_request(value_dict)

    def get_instance(self, instance_id):
        value_dict = {'url': '/instances/%s' % instance_id,
                'namespace': 'instance',
                'object_mapper': self._to_instance}
        return self._get_request(value_dict)

    def create_instance(self, instance):
        data = self._from_instance(instance)

        value_dict = {'url': '/instances',
                'namespace': 'instance',
                'data': {'instance': data},
                'object_mapper': self._to_instance}
        return self._post_request(value_dict)

    def delete_instance(self, instance_id):
        value_dict = {'url': '/instances/%s' % instance_id}
        return self._delete_request(value_dict)

    def restart_instance(self, instance_id):
        data = {'restart': {}}
        value_dict = {'url': '/instances/%s/action' % instance_id,
                'data': data}
        return self._post_request(value_dict)

    def resize_instance_volume(self, instance_id, size):
        data = {'resize': {'volume': {'size': size}}}
        value_dict = {'url': '/instances/%s/action' % instance_id,
                'data': data}
        return self._post_request(value_dict)

    def resize_instance(self, instance_id, flavorRef):
        data = {'resize': {'flavorRef': flavorRef}}
        value_dict = {'url': '/instances/%s/action' % instance_id,
                'data': data}
        return self._post_request(value_dict)

    def create_databases(self, instance_id, databases):
        data = {'databases':
                [self._from_database(x) for x in databases]}
        value_dict = {'url': '/instances/%s/databases' % instance_id,
                'data': data}
        return self._post_request(value_dict)

    def create_database(self, instance_id, database):
        return self.create_databases(instance_id, [database])

    def list_databases(self, instance_id):
        value_dict = {'url': '/instances/%s/databases' % instance_id,
                'namespace': 'databases',
                'list_item_mapper': self._to_database}
        return self._get_request(value_dict)

    def delete_database(self, instance_id, database_name):
        value_dict = {'url': '/instances/%s/databases/%s' %
                (instance_id, database_name)}
        return self._delete_request(value_dict)

    def create_users(self, instance_id, user_databases_pairs):
        def _from_user_databases_pair((user, databases)):
            data = {
                'databases': [self._from_database(d) for d in databases],
                'name': user.name
            }
            if user.password:
                data['password'] = user.password
            return data

        data = {'users':
            [_from_user_databases_pair(p) for p in user_databases_pairs]
        }

        value_dict = {'url': '/instances/%s/users' % instance_id,
                'data': data}

        return self._post_request(value_dict)

    def create_user(self, instance_id, user, databases):
        return self.create_users(instance_id, [(user, databases)])

    def delete_user(self, instance_id, user_name):
        value_dict = {'url': '/instances/%s/users/%s/' %
                (instance_id, user_name)}
        return self._delete_request(value_dict)

    def list_users(self, instance_id):
        value_dict = {'url': '/instances/%s/users' % instance_id,
                'namespace': 'users',
                'list_item_mapper': self._to_user}
        return self._get_request(value_dict)

    def list_flavors(self):
        value_dict = {'url': '/flavors/detail',
                'namespace': 'flavors',
                'list_item_mapper': self._to_flavor}
        return self._get_request(value_dict)

    def get_flavor(self, flavor_id):
        value_dict = {'url': '/flavors/%s' % flavor_id,
                'namespace': 'flavor',
                'object_mapper': self._to_flavor}
        return self._get_request(value_dict)

    def enable_root(self, instance_id):
        value_dict = {'url': '/instances/%s/root' % instance_id,
                'namespace': 'user',
                'object_mapper': self._to_user}
        return self._post_request(value_dict)

    def has_root_enabled(self, instance_id):
        def id(x, value_dict):
            return x
        value_dict = {'url': '/instances/%s/root' % instance_id,
                'namespace': 'rootEnabled',
                'object_mapper': id}
        return self._get_request(value_dict)
