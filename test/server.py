"""
Test Code for RPyCRobotServer
"""
import sys
import logging
import logging.config
import inspect
import yaml
import rpyc.lib
from provider import Provider
import RPyCRobotRemote

LOGCONFIG = """
version: 1
formatters:
  simple:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
handlers:
  console:
    class: logging.StreamHandler
    level: DEBUG
    formatter: simple
    stream: ext://sys.__stderr__
loggers:
  RPyCRobotRemote:
    level: INFO
    handlers: [console]
    propagate: no
root:
  level: DEBUG
  handlers: [console]
"""

logging.config.dictConfig(
    yaml.load(
        LOGCONFIG,
        Loader=yaml.SafeLoader
    ),
)


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

server = RPyCRobotRemote.Server(
    Provider(),
    serve=False,
    # port=0,
    port_file=sys.stdout,
    server=RPyCRobotRemote.SingleServer
)

server.serve()
