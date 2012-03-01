import requests
import json

'''
 URL, String, String -> ([RegionalizedEndpoint], AccountID, AuthToken, UTCString)
'''
def auth_to_service(service_auth_url, rack_user, rack_api_key):
	data = json.dumps({
		"credentials": {
			"username" : rack_user,
			"key" : rack_api_key
		}
	})
	resp = requests.post(service_auth_url, data)

	if resp.ok:
		resp_obj = json.loads(resp.content)
		account_id = resp_obj['auth']['serviceCatalog']['cloudServers'][0]['publicURL'].split('/')[-1] # FIXME: Hacky (API fix)
		token_id = resp_obj['auth']['token']['id']
		token_expiration = resp_obj['auth']['token']['expires']
		regionalized_endpoints = [{ # FIXME: Hardcoded for now
			"region" : u"ORD",
			"v1Default" : u"true",
			"publicURL" : u'https://ord.databases.api.rackspacecloud.com/v1.0/%s/' % account_id
		}]

		return (regionalized_endpoints, account_id, token_id, token_expiration)
	else:
		raise StandardError("Failed to auth with status code %d with %s" % (resp.status_code, resp.content))

def gen_rack_api_v1_0_compatible_headers(account_id, token_id):
	return {
		"X-Auth-Token" : token_id,
		#"X-Auth-Project-ID" : account_id
	}

def gen_curried_api_generator_function(regionalized_endpoint_public_url, headers, dict):
	def _gen_curried_api_function(function_name, rest_endpoint, method, namespace = None):
		def f(*args, **kwargs):
			data = kwargs.get('data') or {}
			h = headers.copy()
			if method in ['post', 'patch', 'put']:
				h['Content-Type'] = 'application/json'
			resp = requests.request(method,
					regionalized_endpoint_public_url + rest_endpoint.format(*args),
					headers = h, data = json.dumps(data))
			if resp.ok:
				try:
					resp_obj = json.loads(resp.content)
					if namespace:
						return resp_obj[namespace]
					else:
						return resp_obj
				except ValueError:
					return resp.status_code
			else:
				raise StandardError("Failed to %s with status code %d. %s" % (function_name.replace('_', ' '), resp.status_code, resp.content))
		dict[function_name] = f

	return _gen_curried_api_function

# Potential base API



API_OPERATIONS = [
		#
		# method name						REST endpoint				  method response namespace
		# API Versions
		['list_apis',						'/',							'get'],#, 'versions'],
		['show_api',						'/{0}',							'get'],#, 'version'],

		# Database Instances
		['create_instance',					'/instances',					'post'],#, 'instance'],
		['list_instances',					'/instances',					'get'],#,	'instances'], # -
		['list_instances_details',			'/instances/detail',			'get'],#,	'instances'], # *
		['show_instance',					'/instances/{0}',				'get'],#,	'instance'],
		['destroy_instance',				'/instances/{0}',				'delete'],

		# Databases
		['create_instance_database',		'/instances/{0}/databases',		'post'],
		['list_instance_databases',			'/instances/{0}/databases',		'get'],#,	'databases'],
		['destroy_instance_database',		'/instances/{0}/databases/{1}',	'delete'],

		# Users
		['create_instance_user',			'/instances/{0}/users',			'post'],
		['list_instance_users',				'/instances/{0}/users',			'get'],#,	'users'],
		['destroy_instance_user',			'/instances/{0}/users/{1}',		'delete'],

		# Flavors
		['list_flavors',					'/flavors',						'get'],#,	'flavors'], # -
		['list_flavors_details',			'/flavors/detail',				'get'],#,	'flavors'], # *
		['show_flavor',						'/flavors/{0}',					'get'],#,	'flavor'],

		# Root Flag
		['enable_instance_root',			'/instances/{0}/root',			'post'],#,	'user'],
		['enabled_instance_root',			'/instances/{0}/root',			'get']#,	'rootEnabled']
]


def augment_dict_with_curried_api_functions(rack_auth_url, rack_user, rack_api, dict):
	[[re], account_id, token, expires] = auth_to_service(rack_auth_url, rack_user, rack_api)
	headers = gen_rack_api_v1_0_compatible_headers(account_id, token)

	g = gen_curried_api_generator_function(re['publicURL'], headers, dict)
	for api_operation in API_OPERATIONS:
		g(*api_operation)
	dict['account_id'] = account_id
	dict['token'] = token
	dict['url'] = re['publicURL']
	dict['headers'] = headers
