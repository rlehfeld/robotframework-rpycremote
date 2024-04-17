import inspect
import RPyCRobotRemote

conn = RPyCRobotRemote.Client()
print(conn.get_answer)
print(conn.ROBOT_LIBRARY_DOC_FORMAT)
print(conn.__doc__)
print(conn.get_answer())
print(dir(conn))

print(inspect.getmembers(conn, callable))

conn.stop_remote_server()
