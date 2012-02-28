from libcloud.common.base import ConnectionUserAndKey

class InstanceStatus(object):
	BUILD = 0
	ACTIVE = 1
	BLOCKED = 2
	SHUTDOWN = 3
	FAILED = 4

class Instance(object):
	def __init__(self, id, name, status):
		self.id = id
		self.name = name
		self.status = status

	def __repr__(self):
		return ("<Instance: id=%s, name=%s, status=%s >" % (self.id, self.name, self.status))

class Flavor(object):
	def __init__(self, id, name, vcpus, ram, link):
		self.id = id
		self.name = name
		self.vcpus = vcpus
		self.ram = ram
		self.link = link

	def __repr__(self):
		return ("<Flavor: id=%s, name=%s, vcpus=%d, ram=%d, link=%s >" % (self.id, self.name, self.vcpus, self.ram, self.link))


class DatabaseDriver(object):
	"""
	A base DatabaseDriver to derive from.
	"""

	connectionCls = ConnectionUserAndKey

	def __init__(self, key, secret=None, secure=True, host=None, port=None):
		self.key = key
		self.secret = secret
		self.secure = secure
		args = [self.key]

		if self.secret != None:
			args.append(self.secret)

		args.append(secure)

		if host != None:
			args.append(host)

		if port != None:
			args.append(port)

		self.connection = self.connectionCls(*args, **self._ex_connection_class_kwargs())

		self.connection.driver = self
		self.connection.connect()

	def _ex_connection_class_kwargs(self):
		return {}

	def list_instances(self):
		raise NotImplementedError(
			'list_instances not implemented for this driver')

	def get_instance(self, instance_id):
		raise NotImplementedError(
			'get_instance not implemented for this driver')

	def create_instance(self, flavorLink, size, **kwargs):
		raise NotImplementedError(
			'create_instance not implemented for this driver')


	def list_flavors(self):
		raise NotImplementedError(
			'list_flavors not implemented for this driver')


