from .RPyCRobotRemoteClient import RPyCRobotRemoteClient as Client
from .RPyCRobotRemoteServer import RPyCRobotRemoteServer as Server # noqa, F401
from rpyc.utils.server import Server as _RPyCServer


RPyCRobotRemote = Client


class SingleServer(_RPyCServer):
    """
    A server that handles a single connection (blockingly)

    Parameters: see :class:`rpyc.utils.server.Server`
    """

    def _accept_method(self, sock):
        try:
            self._authenticate_and_serve_client(sock)
        finally:
            pass
