import requests
import json

def auth_to_service(service_auth_url, rack_user, rack_api_key):
	data = json.dumps({
		"credentials": {
			"username" : rack_user,
			"key" : rack_api_key
		}
	})
	resp = requests.post(service_auth_url, data)

	if resp.ok:
		return json.loads(resp.content)
	else:
		raise StandardError("Failed to auth with status code %d" % resp.status_code)

