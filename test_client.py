import inspect

import rpyc
import weakref

class ConnectionKeeper:
    _finalizer = dict()

    @classmethod
    def keep(cls, connection):
        keeper = cls(connection)
        ref = weakref.ref(connection, keeper)
        keeper._ref = ref
        cls._finalizer[keeper] = 1

    def __init__(self, connection):
        self._client = connection

    def __call__(self):
        print("helloe")
        self._finalizer.pop(self, None)


class RPyCRemote:
    def __new__(cls, peer='localhost', port=18861):
        client = rpyc.connect(peer, port)
        ConnectionKeeper.keep(client)
        return client.root.get_service()


x = RPyCRemote()
print(x.get_answer())
print(dir(x))
x.stop_remote_server()
