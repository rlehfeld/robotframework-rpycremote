import sys
import functools
import logging
import rpyc
from typing import Callable
from contextlib import contextmanager
from robot.libraries.DateTime import convert_time
from robot.api.deco import not_keyword


@contextmanager
def redirect(conn):
    """
    Redirects the other party's ``stdout`` and ``stderr`` to local
    """
    alreadyredirected, conn._redirected = conn._redirected, True
    if not alreadyredirected:
        orig_stdout = conn.root.stdout
        orig_stderr = conn.root.stderr

        try:
            conn.root.stdout = sys.stdout
            conn.root.stderr = sys.stderr
            yield
        finally:
            try:
                conn.root.stdout = orig_stdout
                conn.root.stderr = orig_stderr
            except EOFError:
                pass
            conn._redirected = False
    else:
        yield


def redirect_output(func: Callable):
    this = getattr(func, '__self__', None)
    function = getattr(func, '__func__', func)

    @functools.wraps(function)
    def sync_request(self, handler, *args, **kwargs):
        with redirect(self):
            return function(self, handler, *args, **kwargs)

    if this:
        return sync_request.__get__(this, func.__class__)
    return sync_request


class RPyCRobotRemoteClient:
    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    __slot__ = ()

    def __init__(self,
                 peer: str = 'localhost',
                 port: int = 18861,
                 ipv6: bool = False,
                 timeout=None,
                 logger=None,
                 **rpyc_config):
        self._keywords_cache = None

        if logger is None:
            logger = logging.getLogger('RPyCRobotRemote.Client')

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
            config['sync_request_timeout'] =  convert_time(
                timeout,
                result_format='number'
            )

        self._client = rpyc.connect(
            peer,
            port,
            config=config,
            ipv6=ipv6,
            keepalive=True,
        )

        # automatic redirect stdout + stderr from remote during
        # during handling of sync_request
        self._client._redirected = False
        self._client.sync_request = redirect_output(self._client.sync_request)

    @property
    def __doc__(self):
        return getattr(self._client.root.library, '__doc__')

    def __getattr__(self, name: str):
        if name[0:1] != '_':
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

    def stop_remote_server(self):
        self._client.root.stop_remote_server()

    @not_keyword
    def get_keyword_names(self):
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
