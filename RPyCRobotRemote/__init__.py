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
from rpyc.core.protocol import Connection
from rpyc.utils.server import Server as _RPyCServer
import robot.utils
import robot.variables.replacer
import robot.variables.assigner
import robot.variables.store
from .RPyCRobotRemoteClient import RPyCRobotRemoteClient as Client
from .RPyCRobotRemoteServer import RPyCRobotRemoteServer as Server # noqa, F401


def _unbox(self, package):  # boxing
    """recreate a local object representation of the remote object: if the
    object is passed by value, just return it; if the object is passed by
    reference, create a netref to it"""
    # pylint: disable=protected-access
    label, value = package
    if label == consts.LABEL_VALUE:
        return value
    if label == consts.LABEL_TUPLE:
        return tuple(self._unbox(item) for item in value)
    if label == consts.LABEL_LOCAL_REF:
        return self._local_objects[value]
    if label == consts.LABEL_REMOTE_REF:
        id_pack = (str(value[0]), value[1], value[2])  # so value is a id_pack
        proxy = self._proxy_cache.get(id_pack)
        if proxy is not None:
            # if cached then remote incremented refcount, so sync refcount
            proxy.____refcount__ += 1
        else:
            proxy = self._netref_factory(id_pack)
            self._proxy_cache[id_pack] = proxy
        return proxy
    raise ValueError(f"invalid label {label!r}")


Connection._unbox = _unbox  # pylint: disable=protected-access
del _unbox


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


# work around problems with get_methods in RPyC with pydantic BaseModel
def patch_get_methods(func):
    """patch get_methods"""
    def get_methods(obj_attrs, obj):
        """introspects the given (local) object, returning a list of all of
         its methods (going up the MRO).

        :param obj: any local (not proxy) python object

        :returns: a list of ``(method name, docstring)`` tuples of all the
                  methods of the given object
        """
        methods = {}
        attrs = {}
        if isinstance(obj, type):
            # don't forget the darn metaclass
            mros = (
                list(reversed(type(obj).__mro__)) + list(reversed(obj.__mro__))
            )
        else:
            mros = reversed(type(obj).__mro__)
        for basecls in mros:
            attrs.update(basecls.__dict__)
        for name, attr in attrs.items():
            if name not in obj_attrs and inspect.isroutine(attr):
                methods[name] = inspect.getdoc(attr)
        return methods.items()

    func.__code__ = get_methods.__code__


patch_get_methods(rpyc.lib.get_methods)
