"""
Sample service Provide() used for testing RPyCRobot client and server
"""
import numbers
from collections import namedtuple
from robot.api.deco import keyword, not_keyword


class Region(namedtuple('Region', 'x y width height')):
    """
    namedtuple to reproduce problem in list assignment
    with robot framework
    """
    def __new__(cls, *args):
        if not all(isinstance(x, numbers.Integral) for x in args):
            raise TypeError('all parameters must be of type int')
        return super(Region, cls).__new__(cls, *args)


class Provider:
    """dummy test implementation"""
    ROBOT_LIBRARY_DOC_FORMAT = 'text'

    the_real_answer_though = 43

    class Dummy:
        """dummy class"""
        def __init__(self):
            self._value = 1
            self.value2 = 5

        def __getattribute__(self, attr):
            if attr in ('__class__'):
                raise AttributeError(f'catched {attr}')
            return super().__getattribute__(attr)

        @property
        def value(self):
            """value getter"""
            print('called value getter')
            return self._value

        @value.setter
        def value(self, v):
            print('called value setter')
            self._value = v

        def __call__(self, *args, **kwargs):
            """callable object"""
            print(f'called __call__({args}, {kwargs})')
            return '__call__'

        def method(self, *args, **kwargs):
            """and some callable method"""
            print(f'called method({args}, {kwargs})')
            return 'method'

    dummy_dict = {
        'key': 'value'
    }

    def __init__(self):
        pass

    @not_keyword
    def help_method(self):
        """help_method sample non keyword"""
        print('should not be existing')

    @keyword(name='Use Other Name')
    def renamed_keyword(self):
        """sample renmaed keyword"""
        print('via different name')

    def get_answer(self, a=42, b: int = 56, /, *args, c: int = 59):
        """keyword which requires different arguments and return something"""
        print(f'from remote {b} {args=}')
        return a, c

    def get_region(self):
        """keyword which return a region"""
        return Region(1, 2, 3, 4)

    def get_dictionary(self):
        """keyword which return a region"""
        return {"first": 1, "second": 2}

    def raise_error(self):
        """keyword which raises an error"""
        raise RuntimeError('error')

    def get_question(self):
        """keyword which returns a string"""
        return "what is the airspeed velocity of an unladen swallow?"

    def dummy_test(self):
        """keyword which returns an object"""
        return self.Dummy()
