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
import os
import unittest
from os.path import join as pjoin
try:
	import simplejson as json
except:
	import json

from libcloud.utils.py3 import httplib, urlparse

from rackspace_database.base import (DatabaseDriver, Instance,
								InstanceStatus, Flavor, Database, User)

from rackspace_database.drivers.rackspace import (RackspaceDatabaseDriver,
											RackspaceDatabaseValidationError)

from test import MockResponse, MockHttpTestCase
from test.file_fixtures import FIXTURES_ROOT
from test.file_fixtures import FileFixtures
from secrets import RACKSPACE_PARAMS

FIXTURES_ROOT['database'] = pjoin(os.getcwd(), 'test/fixtures')


class DatabaseFileFixtures(FileFixtures):
	def __init__(self, sub_dir=''):
		super(DatabaseFileFixtures, self).__init__(
													fixtures_type='database',
													sub_dir=sub_dir)


class RackspaceTests(unittest.TestCase):
	def setUp(self):
		RackspaceDatabaseDriver.connectionCls.conn_classes = (
				RackspaceMockHttp, RackspaceMockHttp)
		RackspaceDatabaseDriver.connectionCls.auth_url = \
				'https://auth.api.example.com/v1.1/'

		RackspaceMockHttp.type = None
		self.driver = RackspaceDatabaseDriver(key=RACKSPACE_PARAMS[0],
												secret=RACKSPACE_PARAMS[1],
				ex_force_base_url='http://www.todo.com')


	def test_list_flavors(self):
		results = self.driver.list_flavors()
		self.assertEqual(len(results), 4)
		self.assertEqual(results[0].id, 3)
		self.assertEqual(results[0].ram, 2048)
		self.assertEqual(results[0].href,
			"http://ord.databases.api.rackspacecloud.com/v1.0/586067/flavors/3")

	def test_get_flavor(self):
		href = ("http://ord.databases.api." +
			"rackspacecloud.com/v1.0/586067/flavors/3")
		f = Flavor(3, 'm1.medium', 1, 2048, href)
		result = self.driver.get_flavor(3)
		self.assertEqual(result.id, f.id)
		self.assertEqual(result.name, f.name)
		self.assertEqual(result.vcpus, f.vcpus)
		self.assertEqual(result.ram, f.ram)
		self.assertEqual(result.href, f.href)

	def test_delete_instance(self):
		result = self.driver.delete_instance('68345c52')
		self.assertEqual(result, [])

	def test_list_instances(self):
		result = list(self.driver.list_instances())
		self.assertEqual(len(result), 2)
		self.assertEqual(result[0].id, '68345c52')
		self.assertEqual(result[0].databases, None)
		self.assertEqual(result[0].rootEnabled, None)
		self.assertEqual(result[1].id, '12345c52')
		self.assertEqual(result[1].databases, None)
		self.assertEqual(result[1].rootEnabled, None)

	def test_get_instance(self):
		flavorRef = ("http://ord.databases.api." +
			"rackspacecloud.com/v1.0/586067/flavors/1")
		databases=[
				Database(name='nextround',collate='utf8_general_ci',
					character_set='utf8'),
				Database(name='sampledb', collate='utf8_general_ci',
					character_set='utf8')
		]
		i = Instance(flavorRef, 2, name='a_rack_instance',
				id='68345c52', databases=databases,
				status=InstanceStatus.ACTIVE, rootEnabled=False)
		result = self.driver.get_instance('68345c52')

		self.assertEqual(result.flavorRef, i.flavorRef)
		self.assertEqual(result.name, i.name)
		self.assertEqual(result.status, i.status)
		self.assertEqual(result.id, i.id)
		self.assertEqual(result.rootEnabled, i.rootEnabled)
		self.assertEqual(str(result.databases[0]),
				str(i.databases[0]))
		self.assertEqual(str(result.databases[1]),
				str(i.databases[1]))

	def test_create_instance_with_databases(self):
		flavorRef = "http://ord.databases.api.rackspacecloud.com/v1.0/586067/flavors/1"
		databases = [Database('some_database'),
				Database('another_database', character_set='utf8')]
		i = Instance(flavorRef, 2, name='a_rack_instance', databases=databases)
		result = self.driver.create_instance(i)
		self.assertEqual(result.name, 'a_rack_instance')

	def test_restart_instance(self):
		result = self.driver.restart_instance('123456')
		self.assertEqual(result, [])

	def test_resize_instance_volume(self):
		result = self.driver.resize_instance_volume('1234567', 4)
		self.assertEqual(result, [])

	def test_resize_instance(self):
		flavorRef = "http://ord.databases.api.rackspacecloud.com/v1.0/586067/flavors/1"
		result = self.driver.resize_instance('12345678', flavorRef)
		self.assertEqual(result, [])

	def test_create_databases(self):
		databases = [Database('a_database', character_set='utf8',
				collate='utf8_general_ci'),
				Database('another_database')]
		result = self.driver.create_databases('123456', databases)
		self.assertEqual(result, [])

	def test_create_database(self):
		database = Database('a_database', character_set='cset',
				collate='cset_general_ci')
		result = self.driver.create_database('1234567', database)
		self.assertEqual(result, [])

	def test_list_databases(self):
		databases = [Database('a_database', character_set='utf8',
				collate='utf8_general_ci'),
				Database('another_database')]
		results = self.driver.list_databases('123456')
		self.assertEqual(len(results), 2)
		self.assertEqual(str(results[0]), str(databases[0]))
		self.assertEqual(str(results[1]), str(databases[1]))

	def test_delete_database(self):
		result = self.driver.delete_database('123456', 'adatabase')
		self.assertEqual(result, [])

	def test_create_users(self):
		users = [User('a_user', password='a_password'),
				User('another_user', password='another_password')]
		database_lists = [[Database('a_database'), Database('another_database')],
				[Database('yet_another_database')]]

		result = self.driver.create_users('123456',
				[
					(users[0], database_lists[0]),
					(users[1], database_lists[1])
				])

		self.assertEqual(result, [])

	def test_create_user(self):
		user = User('a_user', password='a_password')
		database_list = [Database('a_database'), Database('another_database')]

		result = self.driver.create_user('1234567', user, database_list)
		self.assertEqual(result, [])

	def test_list_users(self):
		results = self.driver.list_users('123456')
		expected = [User('dbuser3'), User('dbuser4'),
				User('testuser'), User('userwith2dbs')]
		self.assertEqual(str(results), str(expected))

	def test_delete_user(self):
		result = self.driver.delete_user('123456', 'auser')
		self.assertEqual(result, [])

	def test_enable_root(self):
		expected = User('root', password='12345-678910')
		result = self.driver.enable_root('123456')
		self.assertEqual(str(result), str(expected))

	def test_has_root_enabled(self):
		result = self.driver.has_root_enabled('123456')
		self.assertEqual(result, True)
		result = self.driver.has_root_enabled('1234567')
		self.assertEqual(result, False)


class RackspaceMockHttp(MockHttpTestCase):
	auth_fixtures = DatabaseFileFixtures('rackspace/auth')
	fixtures = DatabaseFileFixtures('rackspace/v1.0')
	json_content_headers = {'content-type': 'application/json; charset=UTF-8'}

	def _v2_0_tokens(self, method, url, body, headers):
		body = self.auth_fixtures.load('_v2_0_tokens.json')
		return (httplib.OK, body, self.json_content_headers,
				httplib.responses[httplib.OK])

	def _586067_instances_detail(self, method, url, body, headers):
		body = self.fixtures.load('list_instances.json')
		return (httplib.OK, body, self.json_content_headers,
				httplib.responses[httplib.OK])

	def _586067_instances_68345c52(self, method, url, body, headers):
		if method == 'DELETE':
			self.assertEqual(body, {})
			return (httplib.NO_CONTENT, body, self.json_content_headers,
					httplib.responses[httplib.NO_CONTENT])
		elif method == 'GET':
			body = self.fixtures.load('get_instance.json')
			return (httplib.OK, body, self.json_content_headers,
					httplib.responses[httplib.OK])

		raise NotImplementedError('')

	def _586067_instances(self, method, url, body, headers):
		if method == 'POST':
			flavorRef = ("http://ord.databases.api." +
				"rackspacecloud.com/v1.0/586067/flavors/1")
			data = { 'instance' : {
				'flavorRef' : flavorRef,
				'volume' : {'size' : 2},
				'name' : 'a_rack_instance',
				'databases' : [
					{'name' : 'some_database'},
					{'name' : 'another_database',
						'character_set' : 'utf8'}
					]
			}}
			self.assertEqual(json.loads(body), data)
			body = self.fixtures.load('create_instance_response.json')
			return (httplib.OK, body, self.json_content_headers,
					httplib.responses[httplib.OK])

		raise NotImplementedError('')

	def _586067_instances_123456_action(self, method, url, body, headers):
		if method == 'POST':
			self.assertEqual(json.loads(body), {'restart' : {}})
			return (httplib.NO_CONTENT, body, self.json_content_headers,
					httplib.responses[httplib.NO_CONTENT])

		raise NotImplementedError('')

	def _586067_instances_1234567_action(self, method, url, body, headers):
		if method == 'POST':
			self.assertEqual(json.loads(body), {'resize':{'volume':{'size':4}}})
			return (httplib.NO_CONTENT, body, self.json_content_headers,
					httplib.responses[httplib.NO_CONTENT])

		raise NotImplementedError('')

	def _586067_instances_12345678_action(self, method, url, body, headers):
		if method == 'POST':
			flavorRef = "http://ord.databases.api.rackspacecloud.com/v1.0/586067/flavors/1"
			self.assertEqual(json.loads(body), {'resize':{'flavorRef': flavorRef}})
			return (httplib.NO_CONTENT, body, self.json_content_headers,
					httplib.responses[httplib.NO_CONTENT])

		raise NotImplementedError('')

	def _586067_instances_123456_databases(self, method, url, body, headers):
		if method == 'POST':
			data = { 'databases' : [
					{	'character_set' : 'utf8',
						'collate' : 'utf8_general_ci',
						'name' : 'a_database'
					},
					{	'name' : 'another_database'
					}
				] }
			self.assertEqual(json.loads(body), data)
			return (httplib.NO_CONTENT, body, self.json_content_headers,
					httplib.responses[httplib.NO_CONTENT])
		elif method == 'GET':
			body = self.fixtures.load('list_databases.json')
			return (httplib.OK, body, self.json_content_headers,
				httplib.responses[httplib.OK])
		raise NotImplementedError('')

	def _586067_instances_1234567_databases(self, method, url, body, headers):
		if method == 'POST':
			data = { 'databases' : [
					{	'character_set' : 'cset',
						'collate' : 'cset_general_ci',
						'name' : 'a_database'
					},
				] }
			self.assertEqual(json.loads(body), data)
			return (httplib.NO_CONTENT, body, self.json_content_headers,
					httplib.responses[httplib.NO_CONTENT])

		raise NotImplementedError('')

	def _586067_instances_123456_databases_adatabase(self, method, url, body, headers):
		if method == 'DELETE':
			return (httplib.NO_CONTENT, body, self.json_content_headers,
					httplib.responses[httplib.NO_CONTENT])

		raise NotImplementedError('')

	def _586067_instances_123456_users(self, method, url, body, headers):
		if method == 'POST':
			data = { 'users' : [
				{	'databases' : [
						{'name' : 'a_database'},
						{'name' : 'another_database'}
					],
					'name' : 'a_user',
					'password' : 'a_password'
				},
				{	'databases' : [ {'name' : 'yet_another_database'} ],
					'name' : 'another_user',
					'password' : 'another_password'
				}
			]}
			self.assertEqual(json.loads(body), data)
			return (httplib.NO_CONTENT, body, self.json_content_headers,
					httplib.responses[httplib.NO_CONTENT])
		elif method == 'GET':
			body = self.fixtures.load('list_users.json')
			return (httplib.OK, body, self.json_content_headers,
				httplib.responses[httplib.OK])


		raise NotImplementedError('')

	def _586067_instances_1234567_users(self, method, url, body, headers):
		if method == 'POST':
			data = { 'users' : [
				{	'databases' : [
						{'name' : 'a_database'},
						{'name' : 'another_database'}
					],
					'name' : 'a_user',
					'password' : 'a_password'
				}
			]}
			self.assertEqual(json.loads(body), data)
			return (httplib.NO_CONTENT, body, self.json_content_headers,
					httplib.responses[httplib.NO_CONTENT])

		raise NotImplementedError('')

	def _586067_instances_123456_users_auser(self, method, url, body, headers):
		if method == 'DELETE':
			return (httplib.NO_CONTENT, body, self.json_content_headers,
					httplib.responses[httplib.NO_CONTENT])

		raise NotImplementedError('')


	def _586067_flavors_detail(self, method, url, body, headers):
		if method == 'GET':
			body = self.fixtures.load('list_flavors.json')
			return (httplib.OK, body, self.json_content_headers,
					httplib.responses[httplib.OK])
		raise NotImplementedError('')

	def _586067_flavors_3(self, method, url, body, headers):
		if method == 'GET':
			body = self.fixtures.load('get_flavor.json')
			return (httplib.OK, body, self.json_content_headers,
					httplib.responses[httplib.OK])
		raise NotImplementedError('')

	def _586067_instances_123456_root(self, method, url, body, headers):
		if method == 'POST':
			body = self.fixtures.load('enable_root.json')
			return (httplib.OK, body, self.json_content_headers,
					httplib.responses[httplib.OK])
		elif method == 'GET':
			body = self.fixtures.load('has_root_enabled_true.json')
			return (httplib.OK, body, self.json_content_headers,
					httplib.responses[httplib.OK])
		raise NotImplementedError('')

	def _586067_instances_1234567_root(self, method, url, body, headers):
		if method == 'GET':
			body = self.fixtures.load('has_root_enabled_false.json')
			return (httplib.OK, body, self.json_content_headers,
					httplib.responses[httplib.OK])
		raise NotImplementedError('')


if __name__ == '__main__':
	sys.exit(unittest.main(verbosity=5))
