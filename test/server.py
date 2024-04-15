import sys
from RPyCRobotRemote import RPyCRobotRemoteServer
from robot.api.deco import keyword, not_keyword


class Provider:
    the_real_answer_though = 43

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

    def raise_error(self):
        raise RuntimeError('error')

    def get_question(self):
        return "what is the airspeed velocity of an unladen swallow?"


server = RPyCRobotRemoteServer(
    Provider(),
    serve=False,
    # port=0,
    port_file=sys.stdout,
)

server.serve()
