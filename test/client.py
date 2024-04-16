import inspect
import RPyCRobotRemote

conn = RPyCRobotRemote.Client()
print(conn.get_answer)
print(conn.get_answer())
print(dir(conn))

print(inspect.getmembers(conn, callable))

conn.stop_remote_server()
