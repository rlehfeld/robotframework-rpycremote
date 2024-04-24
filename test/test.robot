*** Settings ***
Library    RPyCRobotRemote    localhost    18861    timeout=10 min    WITH NAME    RPyCTest
Library    Collections

*** Test Cases ***
Test Remote
    RPyCTest.Get Answer
    RPyCTest.Use Other Name

    ${obj} =    RPyCTest.Dummy Test
    Log    ${obj.value}
    ${ret} =    Call Method    ${obj}   method    1    ${2}    3    key=${5}
    ${ret} =    Call Method    ${obj}    __call__    1    ${2}    3    key=${None}
    ${obj.value}     Set Variable    ${5}
    Log    ${obj.value2}
    ${obj.value2}     Set Variable    ${10}

Test Region Scalar
    ${region}    RPyCTest.Get Region

Test Region List
    ${region}    RPyCTest.Get Region
    @{region}    Set Variable    ${{tuple($region)}}

Test Region Array via Scalar
    ${region}    RPyCTest.Get Region
    Log Many    @{region}

Test Region Array
    @{region}    RPyCTest.Get Region

Test Dictionary
    &{dict}    RPyCTest.Get Dictionary
    ${expected}    Create Dictionary    first=${1}    second=${2}
    Collections.Dictionaries Should Be Equal    ${dict}    ${expected}

Test Exception
    Run Keyword And Expect Error    *    RPyCTest.Raise Error

Test Stop Server
    RPyCTest.Stop Remote Server
