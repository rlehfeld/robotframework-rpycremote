"""
Test Code for RPyCRobotServer
"""
import sys
import logging
import logging.config
import yaml
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


server = RPyCRobotRemote.Server(
    Provider(),
    serve=False,
    # port=0,
    port_file=sys.stdout,
    server=RPyCRobotRemote.SingleServer
)

server.serve()
