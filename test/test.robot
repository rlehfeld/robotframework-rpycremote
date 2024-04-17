*** Settings ***
Library    RPyCRobotRemote    localhost    18861    timeout=10 min    AS    RPyCTest

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


Test Exception
    Run Keyword And Expect Error    *    RPyCTest.Raise Error

Test Stop Server
    RPyCTest.Stop Remote Server
