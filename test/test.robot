*** Settings ***
Library    RPyCRobotRemote.RPyCRobotRemoteClient    localhost    18861    WITH NAME    RpyCTest

*** Test Cases ***
Test Remote
    RpyCTest.Get Answer
    RPyCTest.Use Other Name
    #RPyCTest.Raise Error
    #RpyCTest.Stop Remote Server
