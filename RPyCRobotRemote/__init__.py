"""
__init__.py for RPyCRobotRemote
"""
from collections.abc import Iterable
from collections import UserString
from io import IOBase
from rpyc.utils.server import Server as _RPyCServer
import robot.utils
import robot.variables.replacer
import robot.variables.assigner
import robot.variables.store
from .RPyCRobotRemoteClient import RPyCRobotRemoteClient as Client
from .RPyCRobotRemoteServer import RPyCRobotRemoteServer as Server # noqa, F401

RPyCRobotRemote = Client


class SingleServer(_RPyCServer):
    """
    A server that handles a single connection (blockingly)

    Parameters: see :class:`rpyc.utils.server.Server`
    """

    def _accept_method(self, sock):
        """accept method"""
        try:
            self._authenticate_and_serve_client(sock)
        finally:
            pass


# work around problems with is_list_like and remote tuples objects
# Python seems to have a problem with isinstance here
# and throws expcetion
def patch_is_list_like(func):
    """patch is_list_like as it leads to exception with remote namedtuples"""
    def is_list_like(item):
        if isinstance(item, (str, bytes, bytearray)):
            return False
        try:
            if isinstance(item, UserString):
                return False
        except TypeError:
            pass

        try:
            if isinstance(item, IOBase):
                return False
        except TypeError:
            pass

        try:
            return isinstance(item, Iterable)
        except TypeError:
            pass

        try:
            iter(item)
        except TypeError:
            return False
        return True

    code = is_list_like.__code__
    func.__code__ = func.__code__.replace(
        co_code=code.co_code,
        co_consts=code.co_consts,
        co_names=code.co_names,
        co_flags=code.co_flags,
        co_stacksize=code.co_stacksize)


patch_is_list_like(robot.utils.is_list_like)
