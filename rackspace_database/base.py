from libcloud.common.base import ConnectionUserAndKey

class DatabaseInstanceStatus(object):
	BUILD = 0
	ACTIVE = 1
	BLOCKED = 2
	SHUTDOWN = 3
	FAILED = 4

class DatabaseInstance(object):
	def __init__(self, id, name, status):
		self.id = id
		self.name = name
		self.status = status

	def __repr__(self):
		return ("<DatabaseInstance: id=%s, name=%s, status=%s, links=%s >" % (self.id, self.name, self.status, self.links))

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

		def list_instances():
			raise NotImplementedError(
				'list_instances not implemented for this driver')
