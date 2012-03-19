from libcloud.common.base import ConnectionUserAndKey


class InstanceStatus(object):
    BUILD = 0
    ACTIVE = 1
    BLOCKED = 2
    SHUTDOWN = 3
    FAILED = 4


class Instance(object):
    def __init__(self, flavorRef, **kwargs):
        self.id = kwargs.get('id')
        self.name = kwargs.get('name')
        self.status = kwargs.get('status')
        self.size = kwargs.get('size')
        self.flavorRef = flavorRef
        self.databases = kwargs.get('databases')
        self.rootEnabled = kwargs.get('rootEnabled')

    def __repr__(self):
        return (("<Instance: id=%s, name=%s, status=%d," +
                "size=%d, flavorRef=%s, databases=%s, rootEnabled=%s >") %
                (self.id, self.name, self.status, self.size,
                    self.flavorRef, self.databases, str(self.rootEnabled)))


class Database(object):
    def __init__(self, name, character_set=None, collate=None):
        self.name = name
        self.character_set = character_set
        self.collate = collate

    def __repr__(self):
        return ("<Database: name=%s, character_set=%s, collate=%s >"
            % (self.name, self.character_set, self.collate))


class Flavor(object):
    def __init__(self, id, name, vcpus, ram, href):
        self.id = id
        self.name = name
        self.vcpus = vcpus
        self.ram = ram
        self.href = href

    def __repr__(self):
        return ("<Flavor: id=%d, name=%s, vcpus=%d, ram=%d, href=%s >"
            % (self.id, self.name, self.vcpus, self.ram, self.href))


class User(object):
    def __init__(self, name, password=None):
        self.name = name
        self.password = password

    def __repr__(self):
        return ("<User: name=%s, password=%s >" % (self.name, self.password))


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

        self.connection = self.connectionCls(*args,
            **self._ex_connection_class_kwargs())

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

    def create_instance(self, instance):
        raise NotImplementedError(
            'create_instance not implemented for this driver')

    def delete_instance(self, instance_id):
        raise NotImplementedError(
            'delete_instance not implemented for this driver')

    def list_flavors(self):
        raise NotImplementedError(
            'list_flavors not implemented for this driver')

    def get_flavor(self, flavor_id):
        raise NotImplementedError(
            'get_flavor not implemented for this driver')

    def restart_instance(self, instance_id):
        raise NotImplementedError(
            'restart_instance not implemented for this driver')

    def resize_instance(self, instance_id, size):
        raise NotImplementedError(
            'resize_instance not implemented for this driver')

    def resize_instance_volume(self, instance_id, size):
        raise NotImplementedError(
            'resize_instance not implemented for this driver')

    def create_databases(self, instance_id, databases):
        raise NotImplementedError(
            'create_databases not implemented for this driver')

    def create_database(self, instance_id, database):
        raise NotImplementedError(
            'create_database not implemented for this driver')

    def list_databases(self, instance_id):
        raise NotImplementedError(
            'list_databases not implemented for this driver')

    def delete_database(self, instance_id, database_name):
        raise NotImplementedError(
            'delete_database not implemented for this driver')

    def create_users(self, instance_id, user_databases_pairs):
        raise NotImplementedError(
            'create_users not implemented for this driver')

    def create_user(self, instance_id, user, databases):
        raise NotImplementedError(
            'create_user not implemented for this driver')

    def list_users(self, instance_id):
        raise NotImplementedError(
            'list_users not implemented for this driver')

    def delete_user(self, instance_id, user_name):
        raise NotImplementedError(
            'delete_user not implemented for this driver')

    def enable_root(self, instance_id):
        raise NotImplementedError(
            'enable_root not implemented for this driver')

    def has_root_enabled(self, instance_id):
        raise NotImplementedError(
            'has_root_enabled not implemented for this driver')
