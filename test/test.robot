*** Settings ***
Library    RPyCRobotRemote.RPyCRobotRemoteClient    localhost    18861    WITH NAME    RpyCTest

*** Test Cases ***
Test Remote
    RPyCTest.Get Answer
    RPyCTest.Use Other Name

    ${obj} =    RPyCTest.Dummy Test
    Log    ${obj.value}
    ${ret} =    Call Method    ${obj}   method    1    ${2}    3    key=${5}
    ${ret} =    Call Method    ${obj}    __call__    1    ${2}    3    key=${None}
    VAR    ${obj.value}     5
    Log    ${obj.value2}
    VAR    ${obj.value2}     10

    #RpyCTest.Stop Remote Server
