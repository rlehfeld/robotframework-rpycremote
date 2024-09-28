"""
__init__.py for RPyCRobotRemote
"""
from collections.abc import Iterable
from collections import UserString
from io import IOBase
import sys
import inspect
import rpyc.lib
from rpyc.core import consts
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
        except BaseException as e:  # pylint: disable=broad-exception-caught
            self.logger.info(  # pylint: disable=logging-fstring-interpolation
                f'Exception during handling connection: {e!r}'
            )


# work around problems with is_list_like and remote tuples objects
# Python seems to have a problem with isinstance here
# and throws expcetion
def patch_is_list_like(func):
    """patch is_list_like as it leads to exception with remote namedtuples"""
    def is_list_like(item):
        for t in (str, bytes, bytearray, UserString, IOBase):
            try:
                if isinstance(item, t):
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

    func.__code__ = is_list_like.__code__


patch_is_list_like(robot.utils.is_list_like)
