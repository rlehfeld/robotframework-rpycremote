import weakref
import rpyc
import itertools

import gc


class Object:
    pass

server = None

class Provider:
    the_real_answer_though = 43

    def __init__(self):
        pass

    def get_answer(self):
        return 42

    def get_question(self):
        return "what is the airspeed velocity of an unladen swallow?"

    def stop_remote_server(self):
        server.active = False
        return "closed"


class RobotFrameworkService(rpyc.Service):
    def __init__(self, provider, *args, **kwargs):
        self._service = provider
        if isinstance(provider, type):
            self._args = args
            self._kwargs = kwargs
        else:
            if args or kwargs:
                raise ValueError(
                    ', '.join(
                        itertools.chain(
                            map(repr, args),
                            map(lambda x: f"{x}={kwargs[x]!r}", kwargs),
                        )
                    )
                    + ' given but provider is not a type'
                )

    def on_connect(self, conn):
        # code that runs when a connection is created
        # (to init the service, if needed)
        pass

    def on_disconnect(self, conn):
        # code that runs after the connection has already closed
        # (to finalize the service, if needed)
        pass

    def get_service(self):
        if isinstance(self._service, type):
            return self._service(*args, **kwargs)
        else:
            return self._service

    
if __name__ == "__main__":
    from rpyc.utils.helpers import classpartial
    from rpyc.utils.server import ThreadedServer
    provider = Provider()
    service = classpartial(
        RobotFrameworkService, provider
    )
    server = ThreadedServer(
        service,
        port=18861,
        auto_register=False,
        protocol_config={
            'allow_all_attr': True,
            'allow_setattr': True,
            'allow_delattr': True,
            'exposed_prefix': '',
        }
    )
    server.start()
