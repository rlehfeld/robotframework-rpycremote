"""
Client Implementation for RPyCRobotRemote
"""
import sys
import functools
import logging
from typing import Callable
from contextlib import contextmanager
import rpyc
from robot.libraries.DateTime import convert_time
from robot.api import logger as robotapilogger
from robot.api.deco import not_keyword


LOGGER = logging.getLogger('RPyCRobotRemote.Client')
LOGGER.setLevel(logging.INFO)
del LOGGER


@contextmanager
def redirect(conn):
    """
    Redirects the other party's ``stdout`` and ``stderr`` to local
    """
    # pylint: disable=W0212
    alreadyredirected, conn._is_redirected = conn._is_redirected, True
    if not alreadyredirected and conn._is_connected:
        # pylint: enable=W0212
        orig_stdout = conn.root.stdout
        orig_stderr = conn.root.stderr
        orig_robotapilogwriter = conn.root.robotapilogwriter

        try:
            conn.root.stderr = sys.stderr
            conn.root.stdout = sys.stdout
            conn.root.robotapilogwriter = robotapilogger.write
            yield
        finally:
            try:
                conn.root.stdout = orig_stdout
                conn.root.stderr = orig_stderr
                conn.root.robotapilogwriter = orig_robotapilogwriter
            except EOFError:
                pass
            # pylint: disable=W0212
            conn._is_redirected = False
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
        return sync_request.__get__(this, func.__class__)
        # pylint: enable=E1120
    return sync_request


class Service(rpyc.Service):
    """Extends the simple rpyc.Service with eval and execute"""
    __slots__ = ()

    def on_connect(self, conn):
        """called when the connection is established"""
        super().on_connect(conn)
        self._install(conn, conn.root)

    @staticmethod
    def _install(conn, slave):
        """install commands from remote on the client"""
        conn.eval = slave.eval
        conn.execute = slave.execute


class RPyCRobotRemoteClient:
    """
    Implements Remote Client Interface for Robot Framework based on RPyC
    """
    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    __slot__ = ()

    # pylint: disable=R0913
    def __init__(self, /,
                 peer: str = 'localhost',
                 port: int = 18861, *,
                 ipv6: bool = False,
                 timeout=None,
                 logger=None,
                 **rpyc_config):
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

        # automatic redirect stdout + stderr from remote during
        # during handling of sync_request
        self._client._is_connected = True
        self._client._is_redirected = False
        self._client.sync_request = redirect_output(self._client.sync_request)
    # pylint: enable=R0913

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
        self._client.root.stop_remote_server()
        # pylint: disable=W0212
        self._client._is_connected = False
        # pylint: enable=W0212
        self._client.close()

    @not_keyword
    def get_keyword_names(self, /):
        """Return keyword names supported by the remote server."""
        if self._keywords_cache is None:
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
