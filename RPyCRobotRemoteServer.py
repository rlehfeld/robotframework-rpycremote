import sys
import rpyc
from typing import IO
from rpyc.utils.server import ThreadedServer


class RPyCRobotRemoteServer:
    def __init__(self, library, host='127.0.0.1', port=18861, port_file=None,
                 serve=True, allow_remote_stop=True):
        """Configure and start-up remote server.

        :param library:     Test library instance or module to host.
        :param host:        Address to listen. Use ``'0.0.0.0'`` to listen
                            to all available interfaces.
        :param port:        Port to listen. Use ``0`` to select a free port
                            automatically. Can be given as an integer or as
                            a string.
        :param port_file:   File to write the port that is used. ``None`` means
                            no such file is written. Port file is created after
                            the server is started and removed automatically
                            after it has stopped.
        :param allow_stop:  DEPRECATED since version 1.1. Use
                            ``allow_remote_stop`` instead.
        :param serve:       If ``True``, start the server automatically and
                            wait for it to be stopped.
        :param allow_remote_stop:  Allow/disallow stopping the server using
                            ``Stop Remote Server`` keyword and
                            ``stop_remote_server`` XML-RPC method.
        """
        class Service(rpyc.Service):
            def __init__(self, library):
                super().__init__()
                self._library = library

            if allow_remote_stop:
                @staticmethod
                def stop_remote_server():
                    self._server.active = False

            @property
            def library(self):
                return self._library

            @property
            def stdin(self):
                return sys.stdin

            @stdin.setter
            def stdin(self, value: IO):
                print("std.setter", file=sys.__stdout__)
                sys.stdin = value

            @property
            def stdout(self):
                return sys.stdout

            @stdout.setter
            def stdout(self, value: IO):
                sys.stdout = value

            @property
            def stderr(self):
                return sys.stderr

            @stderr.setter
            def stderr(self, value: IO):
                sys.stderr = value

            def _rpyc_setattr(self, name: str, value):
                if name in ('stdin', 'stdout', 'stderr'):
                    return setattr(self, name, value)
                return super()._rpyc_setattr(name, value)

        self._port_file = port_file

        self._server = ThreadedServer(
            Service(library),
            hostname=host,
            port=port,
            auto_register=False,
            protocol_config={
                'allow_all_attr': True,
                'allow_setattr': True,
                'allow_delattr': True,
                'exposed_prefix': '',
            }
        )

        if serve:
            self.serve()

    def serve(self):
        self._server.start()

    @property
    def server_address(self):
        """Server address as a tuple ``(host, port)``."""
        return self._server.host

    @property
    def server_port(self):
        """Server port as an integer.

        If the initial given port is 0, also this property returns 0 until
        the server is activated.
        """
        return self._server.port


if __name__ == "__main__":
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

    RPyCRobotRemoteServer(
        Provider(),
        port=18861,
    )
