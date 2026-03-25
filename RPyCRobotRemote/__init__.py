"""
__init__.py for RPyCRobotRemote
"""
from .RPyCRobotRemoteClient import RPyCRobotRemoteClient as Client
from .RPyCRobotRemoteServer import (  # noqa: F401
    RPyCRobotRemoteServer as Server,
    SingleServer,
    ThreadedServer,
)


RPyCRobotRemote = Client
