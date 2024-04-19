import sys
import yaml
import logging
import logging.config
import RPyCRobotRemote
from provider import Provider


logconfig = """
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
        logconfig,
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
