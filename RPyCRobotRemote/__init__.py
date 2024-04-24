"""
__init__.py for RPyCRobotRemote
"""
from collections.abc import Iterable
from collections import UserString
from io import IOBase
import sys
import inspect
import rpyc.lib
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


# work around problems with get_id_pack in RPyC with c-like objects
def patch_get_id_pack(func):
    """patch get_id_pack"""
    def get_id_pack(obj):
        """introspects the given "local" object, returns id_pack as expected by
        BaseNetref

        The given object is "local" in the sense that it is from the local
        cache. Any object in the local cache exists in the current address
        space or is a netref. A netref in the local cache could be from a
        chained-connection. To handle type related behavior properly, the
        attribute `__class__` is a descriptor for netrefs.

        So, check thy assumptions regarding the given object when creating
        `id_pack`.
        """
        if hasattr(obj, '____id_pack__'):
            # netrefs are handled first since __class__ is a descriptor
            return obj.____id_pack__

        if (inspect.ismodule(obj) or
                getattr(obj, '__name__', None) == 'module'):
            if isinstance(obj, type):  # module
                obj_cls = type(obj)
                name_pack = (
                    f'{obj_cls.__module__}.{obj_cls.__name__}'
                )
                return (name_pack, id(type(obj)), id(obj))

            if inspect.ismodule(obj) and obj.__name__ != 'module':
                if obj.__name__ in sys.modules:
                    name_pack = obj.__name__
                else:
                    name_pack = (
                        f'{type(obj).__module__}.{obj.__name__}'
                    )
            elif inspect.ismodule(obj):
                name_pack = (
                    f'{obj.__module__}.{obj.__name__}'
                )
            elif hasattr(obj, '__module__'):
                name_pack = (
                    f'{obj.__module__}.{obj.__name__}'
                )
            else:
                obj_cls = type(obj)
                name_pack = f'{obj.__name__}'
            return (name_pack, id(type(obj)), id(obj))

        if not inspect.isclass(obj):
            name_pack = (
                f'{type(obj).__module__}.{type(obj).__name__}'
            )
            return (name_pack, id(type(obj)), id(obj))

        name_pack = (
            f'{obj.__module__}.{obj.__name__}'
        )
        return (name_pack, id(obj), 0)

    func.__code__ = get_id_pack.__code__


patch_get_id_pack(rpyc.lib.get_id_pack)
