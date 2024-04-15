import inspect
from RPyCRobotRemote import RPyCRobotRemoteClient

conn = RPyCRobotRemoteClient()
print(conn.get_answer)
print(conn.get_answer())
print(dir(conn))

print(inspect.getmembers(conn, callable))

conn.stop_remote_server()
