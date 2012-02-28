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
								InstanceStatus, Flavor)

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

	def test_list_instances(self):
		result = list(self.driver.list_instances())
		self.assertEqual(len(result), 2)
		self.assertEqual(result[0].id, '68345c52')
		self.assertEqual(result[1].id, '12345c52')

	def test_get_instance(self):
		result = self.driver.get_instance('68345c52')
		self.assertEqual(result.id, '68345c52')

	def test_list_flavors(self):
		results = self.driver.list_flavors()
		self.assertEqual(len(results), 4)
		self.assertEqual(results[0].id, 3)
		self.assertEqual(results[0].ram, 2048)
		self.assertEqual(results[0].link,
			"http://ord.databases.api.rackspacecloud.com/v1.0/586067/flavors/3")

	def test_delete_instance(self):
		result = self.driver.delete_instance('68345c52')
		self.assertEqual(result, [])

	def test_create_instance(self):
		flavorRef = "http://ord.databases.api.rackspacecloud.com/v1.0/586067/flavors/1"
		result = self.driver.create_instance(flavorRef, 2, name='a_rack_instance')
		self.assertEqual(result.name, 'a_rack_instance')

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
			flavorRef = ''.join(["http://ord.databases.api.",
				"rackspacecloud.com/v1.0/586067/flavors/1"])
			data = { 'instance' : {
				'flavorRef' : flavorRef,
				'volume' : {'size' : 2},
				'name' : 'a_rack_instance'
			}}
			self.assertEqual(json.loads(body), data)
			body = self.fixtures.load('get_instance.json')
			return (httplib.OK, body, self.json_content_headers,
					httplib.responses[httplib.OK])

		raise NotImplementedError('')

	def _586067_flavors_detail(self, method, url, body, headers):
		body = self.fixtures.load('list_flavors.json')
		return (httplib.OK, body, self.json_content_headers,
				httplib.responses[httplib.OK])




if __name__ == '__main__':
	sys.exit(unittest.main(verbosity=5))
