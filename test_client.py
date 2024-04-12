import inspect
import functools

import sys
import rpyc
import weakref

from io import StringIO
from contextlib import contextmanager


@contextmanager
def redirect(conn):
    """
    Redirects the other party's ``stdout`` and ``stderr`` to
    StringIO and reformat the output
    """
    if conn._stdout is None:
        conn._stdout = StringIO()
        conn._stderr = StringIO()

        orig_stdout = conn.root.stdout
        orig_stderr = conn.root.stderr

        try:
            conn.root.stdout = conn._stdout
            conn.root.stderr = conn._stderr
            yield
        finally:
            conn.root.stdout = orig_stdout
            conn.root.stderr = orig_stderr
            stdout = conn._stdout.getvalue()
            stderr = conn._stderr.getvalue()
            conn._stdout.close()
            conn._stderr.close()
            conn._stdout = None
            conn._stderr = None
            if stdout and stderr:
                if not stderr.startswith(
                        ('*TRACE*', '*DEBUG*', '*INFO*', '*HTML*',
                         '*WARN*', '*ERROR*')):
                    stderr = f'*INFO* {stderr!s}'
            if stdout and not stdout.endswith('\n'):
                stdout += '\n'
            output = stdout + stderr
            if output:
                sys.stdout.write(output)
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


class ConnectionKeeper:
    _finalizer = dict()

    @classmethod
    def keep(cls, connection):
        keeper = cls(connection)
        ref = weakref.ref(connection, keeper)
        keeper._ref = ref
        cls._finalizer[keeper] = 1

    def __init__(self, connection):
        self._client = connection

    def __call__(self):
        print("helloe")
        self._finalizer.pop(self, None)


class RPyCRemote:
    def __new__(cls, peer='localhost', port=18861):
        client = rpyc.connect(
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
        client._stdout = None
        client.sync_request = redirect_output(client.sync_request)

        # finalize conection
        ConnectionKeeper.keep(client)
        return client.root.library


conn = RPyCRemote()
print(conn.get_answer())
print(dir(conn))

print(conn.run_keyword('get_answer'))

print(inspect.signature(conn.get_answer))
conn.stop_remote_server()
