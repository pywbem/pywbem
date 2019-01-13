"""
Pywbem scriptlet to quit wbemcli. It is used
by test_wbemcli.py to force wbemcli to terminate after each test.
"""

from __future__ import absolute_import, print_function

# This script displays the connection info.  Required because what you see in
# wbemcli startup is through the python interactive module and not to
# stdout
# pylint: disable=undefined-variable
print(_get_connection_info())  # noqa: F821
quit()
