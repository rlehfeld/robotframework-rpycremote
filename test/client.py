"""
Test Code for RPyCRobotClient via python
"""
import inspect
import RPyCRobotRemote

conn = RPyCRobotRemote.Client()
print(conn.get_answer())
print(conn.dummy_test())
print(conn.get_region())
print(list(conn.get_region()))
print(conn.ROBOT_LIBRARY_DOC_FORMAT)
print(conn.__doc__)
print(conn.get_answer())
print(dir(conn))

print(inspect.getmembers(conn, callable))

conn.stop_remote_server()
