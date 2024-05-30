"""
Sample service Provide() used for testing RPyCRobot client and server
"""
from pydantic import BaseModel, field_validator


class DummyModel(BaseModel):
    """DummyModel class"""
    value: int = 0

    @field_validator('value', mode='after')
    @classmethod
    def _is_valid_value(cls, v):
        assert 0 <= v, 'value should be positive'
        return v

    def __call__(self, *args, **kwargs):
        """callable object"""
        print(f'called __call__({args}, {kwargs})')
        return '__call__'

    def method(self, *args, **kwargs):
        """and some callable method"""
        print(f'called method({args}, {kwargs})')
        return 'method'


class Model:
    """dummy test implementation"""

    the_real_answer_though = 43

    def create_model(self):
        """returning Dummy Model"""
        return DummyModel()

    @property
    def constant(self):
        """constant value"""
        return 10
