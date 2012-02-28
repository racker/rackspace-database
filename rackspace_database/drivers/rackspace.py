# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.	You may obtain a copy of the License at
#
#	  http://www.apache.org/licenses/LICENSE-2.0
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
							InstanceStatus, Flavor)

from libcloud.common.rackspace import AUTH_URL_US
from libcloud.common.openstack import OpenStackBaseConnection

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

	def __init__(self, user_id, key, secure=False, ex_force_base_url=API_URL,
				 ex_force_auth_url=None, ex_force_auth_version='2.0'):
		self.api_version = API_VERSION
		self.monitoring_url = ex_force_base_url
		self.accept_format = 'application/json'
		super(RackspaceDatabaseConnection, self).__init__(user_id, key,
								secure=secure,
								ex_force_base_url=ex_force_base_url,
								ex_force_auth_url=ex_force_auth_url,
								ex_force_auth_version=ex_force_auth_version)

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


class RackspaceDatabaseDriver(DatabaseDriver):
	"""
	Base Rackspace Database driver.

	"""
	name = 'Rackspace Monitoring'
	connectionCls = RackspaceDatabaseConnection

	def __init__(self, *args, **kwargs):
		self._ex_force_base_url = kwargs.pop('ex_force_base_url', None)
		self._ex_force_auth_url = kwargs.pop('ex_force_auth_url', None)
		self._ex_force_auth_version = kwargs.pop('ex_force_auth_version', None)
		super(RackspaceDatabaseDriver, self).__init__(*args, **kwargs)

		self.connection._populate_hosts_and_request_paths()
		tenant_id = self.connection.tenant_ids['compute']
		self.connection._force_base_url = '%s/%s' % (
				self.connection._force_base_url, tenant_id)

	def _ex_connection_class_kwargs(self):
		rv = {}
		if self._ex_force_base_url:
			rv['ex_force_base_url'] = self._ex_force_base_url
		if self._ex_force_auth_url:
			rv['ex_force_auth_url'] = self._ex_force_auth_url
		if self._ex_force_auth_version:
			rv['ex_force_auth_version'] = self._ex_force_auth_version
		return rv

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

		response = self.connection.request(url, method=method, data=data, params=params)

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

	def _post_request(self, value_dict):
		return self._request(value_dict, 'POST')


	def _to_instance(self, obj, value_dict):
		status = InstanceStatus.__dict__[obj['status']]
		return Instance(obj['id'], obj['name'], status)


	def list_instances(self):
		value_dict = {'url':'/instances/detail',
				'namespace': 'instances',
				'list_item_mapper': self._to_instance}
		return self._get_request(value_dict)

	def get_instance(self, instance_id):
		value_dict = {'url':'/instances/%s' % instance_id,
				'namespace' : 'instance',
				'object_mapper' : self._to_instance}
		return self._get_request(value_dict)

	def create_instance(self, flavorRef, size, **kwargs):
		data = {
			'flavorRef' : flavorRef,
			'volume' : { 'size' : size },
		}
		data.update(kwargs)
		data = {'instance' : data}

		value_dict = {'url' : '/instances',
				'namespace' : 'instance',
				'data' : data,
				'object_mapper' : self._to_instance}
		return self._post_request(value_dict), data


	def _to_flavor(self, obj, value_dict):
		for link in obj['links']:
			if link['rel'] == 'self':
				href = link['href']

		return Flavor(obj['id'], obj['name'],
				obj['vcpus'], obj['ram'], href)

	def list_flavors(self):
		value_dict = {'url' : '/flavors/detail',
				'namespace' : 'flavors',
				'list_item_mapper' : self._to_flavor}
		return self._get_request(value_dict)




