"""
Pywbem scriptlet to quit wbemcli. It is used
by test_wbemcli.py to force wbemcli to terminate after each test.
"""

# this displays the connection info.  Required because what you see in
# wbemcli startup is through the python interactive module and not to
# stdout
print(_get_connection_info())  # noqa: F821
quit()
