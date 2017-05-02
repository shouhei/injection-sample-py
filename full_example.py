from injector import Module, Key, provider, Injector, inject, singleton
import sqlite3


Configuration = Key('configuration')

class RequestHandler(object):
    @inject
    def __init__(self, db: sqlite3.Connection):
        self._db = db

    def get(self):
        cursor = self._db.cursor()
        cursor.execute('SELECT key, value FROM data ORDER by key')
        return cursor.fetchall()

def configure_for_testing(binder):
    configuration = {'db_connection_string': ':memory:'}
    binder.bind(Configuration, to=configuration, scope=singleton)


class DatabaseModule(Module):
    @singleton
    @provider
    def provide_sqlite_connection(self, configuration: Configuration) -> sqlite3.Connection:
        conn = sqlite3.connect(configuration['db_connection_string'])
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS data (key PRIMARY KEY, value)')
        cursor.execute('INSERT OR REPLACE INTO data VALUES ("hello", "world")')
        return conn


if __name__ == "__main__":
    injector = Injector([configure_for_testing, DatabaseModule()])
    handler = injector.get(RequestHandler)
    print(tuple(map(str, handler.get()[0])))
