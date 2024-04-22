"""
Server Implementation for RPyCRobotRemote
"""
import sys
import pathlib
import logging
import io
import inspect
from typing import TextIO, Optional, Union
from robot.libraries.DateTime import convert_time
import rpyc
from rpyc.utils.server import ThreadedServer


class RPyCRobotRemoteServer:
    """
    Implements Remote Sever Interface for Robot Framework based on RPyC
    """
    # pylint: disable=R0913
    def __init__(self,  # noqa, C901 allow higher complexity here
                 library,
                 host: Optional[str] = 'localhost',
                 port: int = 18861,
                 port_file: Optional[Union[str, pathlib.Path, TextIO]] = None,
                 serve: bool = True,
                 allow_remote_stop: bool = True,
                 ipv6: bool = False,
                 timeout=None,
                 logger=None,
                 server=None,
                 **rpyc_config):
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
            """The root service provided"""
            def __init__(self, library):
                super().__init__()
                self._library = library

            if allow_remote_stop:
                @staticmethod
                def stop_remote_server():
                    """stop server from remote"""
                    self.stop()

            def get_keyword_names(self):
                """return the methods which can be used as keywords"""
                get_kw_names = getattr(
                    self._library,
                    'get_keyword_names',
                    None
                )

                if get_kw_names:
                    return tuple(sorted(set(get_kw_names())))

                attributes = inspect.getmembers(
                    self._library,
                    is_function_or_method
                )
                return tuple(
                    name for name, value in attributes
                    if (name[0:1] != '_' and
                        not getattr(value, 'robot_not_keyword', False))
                )

            @property
            def library(self):
                """wrapprt to retrieve the library object from remote"""
                return self._library

            @property
            def stdin(self):
                """wrapprt to change stdout from remote"""
                return sys.stdin

            @stdin.setter
            def stdin(self, value: TextIO):
                sys.stdin = value

            @property
            def stdout(self):
                """wrapprt to change stdout from remote"""
                return sys.stdout

            @stdout.setter
            def stdout(self, value: TextIO):
                sys.stdout = value

            @property
            def stderr(self):
                """wrapprt to change stderr from remote"""
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

        if logger is None:
            logger = logging.getLogger('RPyCRobotRemote.Server')

        if server is None:
            server = ThreadedServer

        # pylint: disable=duplicate-code
        config = {}
        if rpyc_config:
            config.update(rpyc_config)

        config.update(
            {
                'allow_all_attrs': True,
                'allow_getattr': True,
                'allow_setattr': True,
                'allow_delattr': True,
                'allow_exposed_attrs': False,
                'logger': logger,
            }
        )

        if timeout is not None:
            config['sync_request_timeout'] = convert_time(
                timeout,
                result_format='number'
            )
        # pylint: enable=duplicate-code

        self._server = server(
            Service(library),
            hostname=host,
            port=port,
            ipv6=ipv6,
            auto_register=False,
            logger=logger,
            protocol_config=config,
        )

        if serve:
            self.serve()
    # pylint: enable=R0913

    def stop(self):
        """stop serving requests"""
        self._server.active = False

    def serve(self):
        """start serving requests"""
        if self._port_file:
            if isinstance(self._port_file, io.TextIOBase):
                print(self.server_port, file=self._port_file)
            else:
                with self._port_file.open('w', encoding='utf-8') as f:
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


def is_function_or_method(item):
    """return True in case item is a function or method"""
    return inspect.isfunction(item) or inspect.ismethod(item)
