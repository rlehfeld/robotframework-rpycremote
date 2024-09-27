"""
Server Implementation for RPyCRobotRemote
"""
import sys
import pathlib
import logging
import io
import inspect
import threading
from typing import TextIO, Optional, Union
from collections.abc import Callable
from robot.libraries.DateTime import convert_time
import rpyc
# pylint: disable=E0611
from rpyc.lib.compat import execute
# pylint: enable=E0611
from rpyc.utils.helpers import classpartial
from rpyc.utils.server import ThreadedServer


LOGGER = logging.getLogger('RPyCRobotRemote.Server')
LOGGER.setLevel(logging.INFO)
del LOGGER

UNDEFINED = object()


class WrapTheadSpecific:
    """generic wrapper for any kind of object which makes it thread specific"""

    def __init__(self, default=None):
        super().__setattr__('_local', threading.local())
        super().__setattr__('_default', default)

    @property
    def __doc__(self, /):
        return self.get_thread_specific_instance().__doc__

    @property
    def __match_args__(self, /):
        return self.get_thread_specific_instance().__match_args__

    @property
    def __class__(self, /):
        return self.get_thread_specific_instance().__class__

    def __subclasshook__(self, sub):
        return issubclass(self.get_thread_specific_instance(), sub)

    def __dir__(self):
        return dir(self.get_thread_specific_instance())

    def __hash__(self):
        return hash(self.get_thread_specific_instance())

    def __str__(self):
        return str(self.get_thread_specific_instance())

    def __repr__(self):
        return repr(self.get_thread_specific_instance())

    def __getattr__(self, item):
        return getattr(self.get_thread_specific_instance(), item)

    def __setattr__(self, item, value):
        return setattr(self.get_thread_specific_instance(), item, value)

    def __delattr__(self, item):
        return delattr(self.get_thread_specific_instance(), item)

    def __reduce__(self):
        return self.get_thread_specific_instance().__reduce__()

    def __reduce_ex__(self, protocol):
        return self.get_thread_specific_instance().__reduce_ex__(protocol)

    def __format__(self, format_spec):
        return self.get_thread_specific_instance().__format__(format_spec)

    def __lt__(self, other):
        return self.get_thread_specific_instance().__lt__(other)

    def __le__(self, other):
        return self.get_thread_specific_instance().__le__(other)

    def __eq__(self, other):
        return self.get_thread_specific_instance().__eq__(other)

    def __ne__(self, other):
        return self.get_thread_specific_instance().__ne__(other)

    def __gt__(self, other):
        return self.get_thread_specific_instance().__gt__(other)

    def __ge__(self, other):
        return self.get_thread_specific_instance().__ge__(other)

    def get_thread_specific_instance(self, /):
        """return the thread specific instance stored in the wrapper"""
        return getattr(self._local, 'value', self._default)

    def set_thread_specific_instance(self, /, obj):
        """sets the thread specific instance stored in the wrapper"""
        self._local.value = obj

    def unset_thread_specific_instance(self, /):
        """unsets the thread specific instance stored in the wrapper"""
        try:
            del self._local.value
        except AttributeError:
            pass


_stdin = WrapTheadSpecific(sys.stdin)
_stdout = WrapTheadSpecific(sys.stdout)
_stderr = WrapTheadSpecific(sys.stderr)

sys.stdin = _stdin
sys.stdout = _stdout
sys.stderr = _stderr


class RPyCRobotRemoteServer:
    """
    Implements Remote Sever Interface for Robot Framework based on RPyC
    """
    # pylint: disable=R0913,R0914
    def __init__(self,  # noqa, C901 allow higher complexity here
                 library,
                 host: Optional[str] = 'localhost',
                 port: int = 18861, *,
                 port_file: Optional[Union[str, pathlib.Path, TextIO]] = None,
                 serve: bool = True,
                 allow_remote_stop: bool = True,
                 ipv6: bool = False,
                 authenticator: Optional[Callable] = None,
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
                self.namespace = {}
                self._library = library

            if allow_remote_stop:
                @staticmethod
                def stop_remote_server():
                    """stop server from remote"""
                    self.stop()

            def on_connect(self, conn):
                on_connect = getattr(self._library, '_on_connect', None)
                if on_connect:
                    on_connect()

            def on_disconnect(self, conn):
                _stdin.unset_thread_specific_instance()
                _stdout.unset_thread_specific_instance()
                _stderr.unset_thread_specific_instance()

                on_disconnect = getattr(self._library, '_on_disconnect', None)
                if on_disconnect:
                    on_disconnect()

            def execute(self, text):
                """execute arbitrary code (using ``exec``)"""
                execute(text, self.namespace)

            def eval(self, text):
                """evaluate arbitrary code (using ``eval``)"""
                # pylint: disable=W0123
                return eval(text, self.namespace)
                # pylint: enable=W0123

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
                """wrapper to change stdout from remote"""
                return _stdin.get_specific_instance()

            @stdin.setter
            def stdin(self, value: TextIO):
                _stdin.set_thread_specific_instance(value)

            @property
            def stdout(self):
                """wrapper to change stdout from remote"""
                return _stdout.get_thread_specific_instance()

            @stdout.setter
            def stdout(self, value: TextIO):
                _stdout.set_thread_specific_instance(value)

            @property
            def stderr(self):
                """wrapper to change stderr from remote"""
                return _stderr.get_thread_specific_instance()

            @stderr.setter
            def stderr(self, value: TextIO):
                _stderr.set_thread_specific_instance(value)

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

        service = classpartial(Service, library)
        self._server = server(
            service,
            hostname=host,
            port=port,
            ipv6=ipv6,
            authenticator=authenticator,
            auto_register=False,
            logger=logger,
            protocol_config=config,
        )

        if serve:
            self.serve()
    # pylint: enable=R0913,R0914

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
