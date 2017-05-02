from abc import ABCMeta, abstractmethod
from typing import List
from injector import Module, Key, provider, Injector, inject, singleton
import sqlite3
import redis

class User(object):
    def __init__(self, user_id=None, name=None):
        self.__user_id = user_id
        self.__name = name

    @property
    def user_id(self):
        return self.__user_id

    @user_id.getter
    def user_id(self):
        return self.__user_id

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, name):
        self.__name = name

    @name.getter
    def name(self):
        return self.__name

    def __str__(self):
        return "id: {0}, name: {1}".format(self.__user_id, self.__name)

Configuration = Key('configuration')


class UserRepositoryInterface(metaclass=ABCMeta):

    @abstractmethod
    def __init__(self, configuration: Configuration):
        pass

    @abstractmethod
    def find_by_name(self, name) -> User:
        pass

    @abstractmethod
    def all(self) -> List[User]:
        pass

    @abstractmethod
    def create(self, user: User) -> User:
        pass

    @abstractmethod
    def update(self, user: User) -> User:
        pass

class TestUserRepository(UserRepositoryInterface):
    def __init__(self, configration: Configuration):
        self.__users = []

    def find_by_name(self, name) -> User:
        for u in self.__users:
            if u.name == name:
                return u
        return []

    def all(self) -> List[User]:
        return self.__users

    def create(self, user: User) -> User:
        self.__users = sorted(self.__users, key=lambda u: int(u.user_id))
        if len(self.__users) == 0:
            new_user_id = '1'
        else:
            new_user_id = str(int(self.__users[-1].user_id) + 1)
        user = User(new_user_id, user.name)
        self.__users.append(user)
        return user

    def update(self, user: User) -> User:
        for i, u in enumerate(self.__users):
            if u.user_id == user.user_id:
                self.__users[i] = user
        return user

class SQLiteUserRepository(UserRepositoryInterface):
    def __init__(self, configuration):
        conn = sqlite3.connect(configuration['db_connection_string'])
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE user (id INTEGER PRIMARY KEY AUTOINCREMENT, name)')
        self.__conn = conn

    def find_by_name(self, name) -> User:
        cursor = self.__conn.cursor()
        cursor.execute("SELECT id, name FROM user WHERE name='{0}'".format(name))
        record = cursor.fetchall()
        return User(record[0][0], record[0][1])

    def all(self) -> User:
        cursor = self.__conn.cursor()
        cursor.execute("SELECT id, name FROM user")
        records = cursor.fetchall()
        users = []
        for record in records:
            users.append(User(record[0], record[1]))
        return users

    def create(self, user) -> User:
        cursor = self.__conn.cursor()
        cursor.execute("INSERT INTO user (name) VALUES ('{0}')".format(user.name))
        self.__conn.commit()
        return User(cursor.lastrowid, user.name)

    def update(self, user) -> User:
        cursor = self.__conn.cursor()
        cursor.execute("UPDATE user SET name='{0}' WHERE id={1}".format(user.name, user.user_id))
        self.__conn.commit()
        return User(cursor.lastrowid, user.name)

class RedisUserRepository(UserRepositoryInterface):

    def __init__(self, configuration: Configuration):
        self.__r = redis.Redis(host='localhost', port=6379, db=0)

    def find_by_name(self, name) -> User:
        for i, raw in enumerate(reversed(self.__r.lrange(name='user', start=0, end=-1))):
            if  raw.decode('utf-8') == name:
                return User(i+1, name)

        return []

    def all(self) -> List[User]:
        fetched = self.__r.lrange(name='user', start=0, end=-1)
        users = []
        for i, f in enumerate(reversed(fetched)):
            users.append(User(i+1, f.decode('utf-8')))
        return users

    def create(self, user: User) -> User:
        i = self.__r.lpush('user', user.name.encode('utf-8'))
        return User(i, User.name)

    def update(self, user: User) -> User:
        index = self.__r.llen('user') - user.user_id
        row = self.__r.lindex('user', index)
        if  row is not None:
            self.__r.lset('user', index, user.name.encode('utf-8'))
            return user

    def flush(self):
        self.__r.flushall()

class RequestHandler(object):
    @inject
    def __init__(self, uer_repository: UserRepositoryInterface):
        self.__user_repository = uer_repository

    def all(self):
        user1 = self.__user_repository.create(User(name='sample1'))
        user2 = self.__user_repository.create(User(name='sample2'))
        for i in self.__user_repository.all():
            print(i)
        user2.name = 'sample_sample2'
        self.__user_repository.update(user2)
        for i in self.__user_repository.all():
            print(i)
        user2_2 = self.__user_repository.find_by_name(user2.name)
        print(user2_2)
        self.__user_repository.flush()

def configure_for_testing(binder):
    configuration = {'db_connection_string': ':memory:'}
    binder.bind(Configuration, to=configuration, scope=singleton)


class ServiceProvider(Module):
    @singleton
    @provider
    def register(self, configuration: Configuration) -> UserRepositoryInterface:
        return RedisUserRepository(configuration)

if __name__ == "__main__":
    injector = Injector([configure_for_testing, ServiceProvider()])
    handler = injector.get(RequestHandler)
    handler.all()
