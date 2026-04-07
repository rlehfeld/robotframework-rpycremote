"""
Client Implementation for RPyCRobotRemote
"""
import sys
import functools
import logging
from typing import Callable
from contextlib import contextmanager
from threading import current_thread, _register_atexit as register_atexit
import rpyc
from rpyc.core.protocol import Connection
from robot.libraries.DateTime import convert_time
from robot.api import logger as robotapilogger
from robot.api.deco import not_keyword
from robot.output import LOGGER
from robot.output.librarylogger import LOGGING_THREADS
try:
    from robot.output.loggerapi import LoggerApi
except ImportError:
    LoggerApi = None

log = logging.getLogger('RPyCRobotRemote.Client')
log.setLevel(logging.INFO)
del log


@contextmanager
def redirect(conn):
    """
    Redirects the other party's ``stdout`` and ``stderr`` to local
    """

    if current_thread().name not in LOGGING_THREADS:
        yield
    else:
        alreadyredirected, conn._is_redirected = conn._is_redirected, True  # noqa, E501 pylint: disable=W0212
        # pylint: disable=W0212
        if not alreadyredirected and conn._is_connected:
            if conn._bgthread is not None:
                conn._bgthread.pause()

            # pylint: enable=W0212
            orig_stdout = conn.root.stdout
            orig_stderr = conn.root.stderr
            orig_robotapilogwriter = conn.root.robotapilogwriter
            orig_robotapilogconsole = conn.root.robotapilogconsole

            try:
                conn.root.stderr = sys.stderr
                conn.root.stdout = sys.stdout
                conn.root.robotapilogwriter = robotapilogger.write
                conn.root.robotapilogconsole = robotapilogger.console
                yield
            finally:
                try:
                    conn.root.stdout = orig_stdout
                    conn.root.stderr = orig_stderr
                    conn.root.robotapilogwriter = orig_robotapilogwriter
                    conn.root.robotapilogconsole = orig_robotapilogconsole
                except EOFError:
                    pass
                # pylint: disable=W0212
                conn._is_redirected = False
                if conn._bgthread is not None:
                    conn._bgthread.resume()
                # pylint: enable=W0212
        else:
            yield


def redirect_output(func: Callable):
    """
    decorator for RPyC connetion to automatically forward
    stdout and stderr from remote to local
    """
    this = getattr(func, '__self__', None)
    function = getattr(func, '__func__', func)

    @functools.wraps(function)
    def sync_request(self, handler, *args, **kwargs):
        with redirect(self):
            return function(self, handler, *args, **kwargs)

    if this:
        # pylint: disable=E1120
        return sync_request.__get__(this, type(this))
        # pylint: enable=E1120
    return sync_request


class Service(rpyc.Service):
    """Extends the simple rpyc.Service with eval and execute"""
    __slots__ = ()

    @property
    def bgthread(self):
        """Give access to BgServingThread in current connection"""
        # pylint: disable=W0212,E1101
        return Connection.current()._bgthread
        # pylint: enable=W0212,E1101

    def on_connect(self, conn):
        """called when the connection is established"""
        super().on_connect(conn)
        self._install(conn, conn.root)

        def ignore_eoferror_exception(exc):
            if not isinstance(exc, EOFError):
                raise exc from None

        # pylint: disable=W0212
        conn._is_connected = True
        conn._is_redirected = False
        conn._bgthread = rpyc.BgServingThread(
            conn,
            callback=ignore_eoferror_exception,
            active=not conn._is_redirected,
        )
        # pylint: enable=W0212

    def on_disconnect(self, conn):
        # pylint: disable=W0212
        bgthread, conn._bgthread = conn._bgthread, None
        if bgthread is not None:
            bgthread.stop()
        conn._is_connected = False
        conn._is_redirected = True
        # pylint: enable=W0212
        super().on_disconnect(conn)

    @staticmethod
    def _install(conn, slave):
        """install commands from remote on the client"""
        conn.eval = slave.eval
        conn.execute = slave.execute


class RPyCRobotRemoteClient:
    """
    Implements Remote Client Interface for Robot Framework based on RPyC
    """
    __slot__ = ('ROBOT_LIBRARY_LISTENER', )
    __connected_instances = []

    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    # pylint: disable=R0913
    def __init__(self, /,
                 peer: str = 'localhost',
                 port: int = 18861, *,
                 ipv6: bool = False,
                 timeout=None,
                 logger=None,
                 **rpyc_config):

        instance = self
        filepath = sys.modules[__name__].__file__

        class CloseListener:  # pylint: disable=R0903
            """
            Listener class to trigger disconnect and thread termination
            """
            __slots__ = ()

            ROBOT_LISTENER_API_VERSION = 3

            def close(self):
                """ called by Robot Framework when library will be removed """
                instance._disconnect()  # pylint: disable=W0212

        self.ROBOT_LIBRARY_LISTENER = CloseListener()  # pylint: disable=C0103

        if LoggerApi is not None:
            class Logger(LoggerApi):
                """
                logger class in order to recognize when library is actually
                completely imported so we can start forwarding of stdout/stderr
                """
                __slot__ = ()

                def imported(self, import_type: str, name: str, attrs):  # noqa: E501 pylint: disable=W0613
                    if (import_type == 'Library' and
                            attrs['source'] == filepath):
                        self._set_redirect_and_unregister()

                def library_import(self, library, importer):  # noqa: E501 pylint: disable=W0613
                    if library.instance is instance:
                        self._set_redirect_and_unregister()

                def _set_redirect_and_unregister(self):
                    # pylint: disable=W0212
                    if instance._client._is_connected:
                        instance._client._is_redirected = False
                    # pylint: enable=W0212
                    LOGGER.unregister_logger(self)

            LOGGER.register_logger(Logger())
        self._keywords_cache = None
        if logger is None:
            logger = logging.getLogger('RPyCRobotRemote.Client')

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

        self._client = rpyc.connect(
            peer,
            port,
            service=Service,
            config=config,
            ipv6=ipv6,
            keepalive=True,
        )
        self.__connected_instances.append(self)

        # automatic redirect stdout + stderr from remote during
        # during handling of sync_request
        self._client._is_redirected = LoggerApi is not None
        self._client.sync_request = redirect_output(self._client.sync_request)
    # pylint: enable=R0913

    @classmethod
    @not_keyword
    def _disconnect_instances(cls):
        for instance in cls.__connected_instances.copy():
            # pylint: disable=W0212
            instance._disconnect()
            # pylint: enable=W0212

    def __del__(self, /):
        self._disconnect()

    @property
    def __doc__(self, /):
        return getattr(self._client.root.library, '__doc__')

    def __getattr__(self, name: str):
        if (name[0:1] != '_' and
                (not name.startswith('ROBOT_LIBRARY_') or
                 self._client._is_connected)):
            try:
                obj = getattr(self._client.root.library, name)
            except AttributeError:
                pass
            else:
                if name.startswith('ROBOT_LIBRARY_') or callable(obj):
                    return obj
        raise AttributeError(
            f'{type(self).__name__!r} object has no attribute {name!r}'
        )

    def remote_eval(self, /, text):
        """evaluate arbitrary code (using ``eval``) on remote"""
        return self._client.eval(text)

    def remote_execute(self, /, text):
        """execute arbitrary code (using ``exec``) on remote"""
        self._client.execute(text)

    def stop_remote_server(self, /):
        """Stop remote server."""
        self._stop_bg_thread()
        try:
            self._client.root.stop_remote_server()
        except EOFError:
            pass
        self._disconnect()

    @not_keyword
    def _stop_bg_thread(self, /):
        # pylint: disable=W0212
        bgthread, self._client._bgthread = self._client._bgthread, None
        # pylint: enable=W0212
        if bgthread is not None:
            bgthread.stop()

    @not_keyword
    def _disconnect(self, /):
        try:
            self.__connected_instances.remove(self)
        except ValueError:
            pass
        # pylint: disable=W0212
        if self._client._is_connected:
            self._client._is_connected = False
            # pylint: enable=W0212
            self._stop_bg_thread()
            self._client.close()

    @not_keyword
    def get_keyword_names(self, /):
        """Return keyword names supported by the remote server."""
        if self._keywords_cache is None:
            with redirect(self._client):
                base = set(self._client.root.get_keyword_names())
                attributes = [(name, getattr(self, name))
                              for name in dir(self) if name[0:1] != '_']
                self._keywords_cache = tuple(
                    sorted(
                        base | {
                            name for name, value in attributes
                            if (callable(value) and
                                not getattr(value, 'robot_not_keyword', False))
                        }
                    )
                )
        return self._keywords_cache


# pylint: disable=W0212
register_atexit(RPyCRobotRemoteClient._disconnect_instances)
# pylint: enable=W0212
