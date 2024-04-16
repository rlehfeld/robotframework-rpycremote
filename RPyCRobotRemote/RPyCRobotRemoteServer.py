import sys
import rpyc
import pathlib
import io
from typing import TextIO, Optional
from rpyc.utils.server import ThreadedServer


class RPyCRobotRemoteServer:
    def __init__(self,
                 library,
                 host: Optional[str] = 'localhost',
                 port: int = 18861,
                 port_file: Optional[str | pathlib.Path | TextIO] = None,
                 serve: bool = True,
                 allow_remote_stop: bool = True,
                 ipv6: bool = True):
        """Configure and start-up remote server.

        :param library:     Test library instance or module to host.
        :param host:        Address to listen. Use None to listen
                            to all available interfaces.
        :param port:        Port to listen. Use ``0`` to select a free port
                            automatically. Can be given as an integer or as
                            a string.
        :param port_file:   File to write the port that is used. ``None`` means
                            no such file is written. Port file is created after
                            the server is started and removed automatically
                            after it has stopped.
        :param serve:       If ``True``, start the server automatically and
                            wait for it to be stopped.
        :param allow_remote_stop:  Allow/disallow stopping the server using
                            ``Stop Remote Server`` keyword and
                            ``stop_remote_server`` method.
        :param ipv6         If ``True``, allow IPv6 connections,
                            if ``False``, use IPv4 only connections.
        """
        class Service(rpyc.Service):
            def __init__(self, library):
                super().__init__()
                self._library = library

            if allow_remote_stop:
                @staticmethod
                def stop_remote_server():
                    self.stop()

            @property
            def library(self):
                return self._library

            @property
            def stdin(self):
                return sys.stdin

            @stdin.setter
            def stdin(self, value: TextIO):
                sys.stdin = value

            @property
            def stdout(self):
                return sys.stdout

            @stdout.setter
            def stdout(self, value: TextIO):
                sys.stdout = value

            @property
            def stderr(self):
                return sys.stderr

            @stderr.setter
            def stderr(self, value: TextIO):
                sys.stderr = value

            def _rpyc_setattr(self, name: str, value):
                if name in ('stdin', 'stdout', 'stderr'):
                    return setattr(self, name, value)
                return super()._rpyc_setattr(name, value)

        self._port_file = (
            port_file if (
                port_file is None or isinstance(port_file, io.TextIOBase))
            else pathlib.Path(port_file).absolute()
        )
        self._server = ThreadedServer(
            Service(library),
            hostname=host,
            port=port,
            ipv6=ipv6,
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

    def stop(self):
        self._server.active = False

    def serve(self):
        if self._port_file:
            if isinstance(self._port_file, io.TextIOBase):
                print(self.server_port, file=self._port_file)
            else:
                with self._port_file.open('w') as f:
                    print(self.server_port, file=f)
        self._server.start()
        if self._port_file and not isinstance(self._port_file, io.TextIOBase):
            self._port_file.unlink()

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
