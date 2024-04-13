import sys
import functools
import inspect
import rpyc
from typing import Optional, List, Dict, Callable
from contextlib import contextmanager


@contextmanager
def redirect(conn):
    """
    Redirects the other party's ``stdout`` and ``stderr`` to
    StringIO and reformat the output
    """
    if not conn._redirected:
        conn._redirected = True
        orig_stdout = conn.root.stdout
        orig_stderr = conn.root.stderr

        try:
            conn.root.stdout = sys.stdout
            conn.root.stderr = sys.stderr
            yield
        finally:
            conn.root.stdout = orig_stdout
            conn.root.stderr = orig_stderr
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

    def __init__(self, peer: str = 'localhost', port: int = 18861):
        self._dir_cache = None
        self._keywords_cache = None
        self._client = rpyc.connect(
            peer,
            port,
            config={
                'allow_all_attr': True,
                'allow_setattr': True,
                'allow_delattr': True,
                'exposed_prefix': '',
            }
        )

        for name in ('ROBOT_LIBRARY_DOC_FORMAT'):
            try:
                value = getattr(self._client.root.library, name)
            except AttributeError:
                pass
            else:
                setattr(self, name, value)

        # automatic redirect stdout + stderr from remote during
        # during handling of sync_request
        self._client._redirected = False
        self._client.sync_request = redirect_output(self._client.sync_request)

    def __dir__(self):
        if self._dir_cache is None:
            dict = super().__dir__()
            for name in dir(self._client.root.library):
                if name[0:1] != '_':
                    obj = getattr(self._client.root.library, name)
                    if callable(obj):
                        dict.append(name)
            dict.sort()
            self._dir_cache = dict
        return self._dir_cache

    def __getattr__(self, name: str):
        if name[0:1] != '_':
            try:
                obj = getattr(self._client.root.library, name)
            except AttributeError:
                pass
            else:
                if callable(obj):
                    return obj
        exception = AttributeError(
            f'{type(self).__name__!r} object has no attribute {name!r}'
        )
        raise exception

    def stop_remote_server(self):
        self._client.root.stop_remote_server()

    def get_keyword_names(self):
        return self._keywords.keys()

    def run_keyword(self, name: str,
                    args: Optional[List] = None,
                    kwargs: Optional[Dict] = None):
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}
        return getattr(self, name)(*args, **kwargs)

    def get_keyword_arguments(self, name: str):
        try:
            signature = inspect.signature(self._keywords[name])
        except ValueError:  # Can occur with C functions (incl. many builtins).
            return ['*varargs']
        print(signature)
        parameters = signature.parameters.values()
        print([p.kind for p in parameters])
        res = [
            p.name
            if (p.default == inspect.Parameter.empty) else (p.name, p.default)
            for p in parameters
        ]
        print(res)
        return res

    def get_keyword_tags(self, name: str):
        return getattr(self._keywords[name], 'robot_tags', ())

    def get_keyword_documentation(self, name: str):
        return inspect.getdoc(self._keywords[name]) or ''

    def get_keyword_source(self, name: str):
        try:
            filename = inspect.getsourcefile(self._keywords[name])
            lineno = self._keywords[name].__code__.co_firstlineno
            return f'{filename}:{lineno}'
        except TypeError:
            return None

    @property
    def _keywords(self):
        if self._keywords_cache is None:
            attributes = [(name, getattr(self, name))
                          for name in dir(self) if name[0:1] != '_']
            self._keywords_cache = {
                getattr(value, 'robot_name', name): value
                for name, value in attributes
                if (callable(value) and
                    not getattr(value, 'robot_not_keyword', False))
            }
        return self._keywords_cache


if __name__ == "__main__":
    conn = RPyCRobotRemoteClient()
    print(conn.get_answer)
    print(conn.get_answer())
    print(dir(conn))

    print(inspect.getmembers(conn, callable))
    print(conn.run_keyword('get_answer', [], {'b': 57}))

    conn.stop_remote_server()
