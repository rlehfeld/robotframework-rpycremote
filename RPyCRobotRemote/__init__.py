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
        undef = object()
        name_pack = getattr(obj, '____id_pack__', undef)
        if name_pack is not undef:
            return name_pack

        obj_name = getattr(obj, '__name__', None)
        if (inspect.ismodule(obj) or obj_name == 'module'):
            if isinstance(obj, type):  # module
                obj_cls = type(obj)
                name_pack = (
                    f'{obj_cls.__module__}.{obj_cls.__name__}'
                )
                return (name_pack, id(type(obj)), id(obj))

            if inspect.ismodule(obj) and obj_name != 'module':
                if obj_name in sys.modules:
                    name_pack = obj_name
                else:
                    obj_cls = getattr(obj, '__class__', type(obj))
                    name_pack = (
                        f'{obj_cls.__module__}.{obj_name}'
                    )
            elif inspect.ismodule(obj):
                name_pack = (
                    f'{obj.__module__}.{obj_name}'
                )
            else:
                obj_module = getattr(obj, '__module__', undef)
                if obj_module is not undef:
                    name_pack = (
                        f'{obj.__module__}.{obj_name}'
                    )
                else:
                    name_pack = obj_name
            return (name_pack, id(type(obj)), id(obj))

        if not inspect.isclass(obj):
            obj_cls = getattr(obj, '__class__', type(obj))
            name_pack = (
                f'{obj_cls.__module__}.{obj_cls.__name__}'
            )
            return (name_pack, id(type(obj)), id(obj))

        name_pack = (
            f'{obj.__module__}.{obj_name}'
        )
        return (name_pack, id(obj), 0)

    func.__code__ = get_id_pack.__code__


patch_get_id_pack(rpyc.lib.get_id_pack)
