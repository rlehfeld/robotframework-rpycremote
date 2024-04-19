import sys
import yaml
import logging
import logging.config
import numbers
import RPyCRobotRemote
from collections import namedtuple
from robot.api.deco import keyword, not_keyword
from rpyc.utils.server import Server


class Region(namedtuple('Region', 'x y width height')):
    def __new__(cls, *args):
        if not all(isinstance(x, numbers.Integral) for x in args):
            raise TypeError('all parameters must be of type int')
        return super(Region, cls).__new__(cls, *args)


class Provider:
    """dummy test implementation"""
    ROBOT_LIBRARY_DOC_FORMAT = 'text'

    the_real_answer_though = 43

    dummy_dict = {
        'key': 'value'
    }

    def __init__(self):
        pass

    @not_keyword
    def help_method(self):
        print('should not be existing')

    @keyword(name='Use Other Name')
    def renamed_keyword(self):
        print('via different name')

    def get_answer(self, a=4,  /, b: int = 56, *args, c: int = 59):
        print(f'from remote {b}')
        return 42

    def get_region(self):
        return Region(1, 2, 3, 4)

    def raise_error(self):
        raise RuntimeError('error')

    def get_question(self):
        return "what is the airspeed velocity of an unladen swallow?"

    def dummy_test(self):
        class Dummy:
            def __init__(self):
                self._value = 1
                self.value2 = 5

            @property
            def value(self):
                print('called value getter')
                return self._value

            @value.setter
            def value(self, v):
                print('called value setter')
                self._value = v

            def __call__(self, *args, **kwargs):
                print(f'called __call__({args}, {kwargs})')
                return '__call__'

            def method(self, *args, **kwargs):
                print(f'called method({args}, {kwargs})')
                return 'method'

        return Dummy()


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
    yaml.load(logconfig,
              Loader=yaml.SafeLoader),
)

server = RPyCRobotRemote.Server(
    Provider(),
    serve=False,
    # port=0,
    port_file=sys.stdout,
    server=RPyCRobotRemote.SingleServer
)

server.serve()
