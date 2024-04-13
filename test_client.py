import sys
import functools

import rpyc

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


def redirect_output(func):
    this = getattr(func, '__self__', None)
    function = getattr(func, '__func__', func)

    @functools.wraps(function)
    def sync_request(self, handler, *args, **kwargs):
        with redirect(self):
            return function(self, handler, *args, **kwargs)

    if this:
        return sync_request.__get__(this, func.__class__)
    return sync_request


class RPyCRemote:
    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    def __init__(self, peer='localhost', port=18861):
        self._dircache = None
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

        # automatic redirect stdout + stderr from remote during
        # during handling of sync_request
        self._client._redirected = False
        self._client.sync_request = redirect_output(self._client.sync_request)

    def __dir__(self):
        if self._dircache is None:
            dict = super().__dir__()
            for name in dir(self._client.root.library):
                if name[0:1] != '_':
                    obj = getattr(self._client.root.library, name)
                    if callable(obj):
                        dict.append(name)
            dict.sort()
            self._dircache = dict
        return self._dircache

    def __getattr__(self, name):
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

    def run_keyword(self, name, args=None, kwargs=None):
        return self._client.root.run_keyword(name, args, kwargs)


if __name__ == "__main__":
    conn = RPyCRemote()
    print(conn.get_answer)
    print(conn.get_answer())
    print(dir(conn))

    print(conn.run_keyword('get_answer'))

    conn.stop_remote_server()
