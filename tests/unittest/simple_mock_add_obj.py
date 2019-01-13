"""
Test file for use with wbemcli -mock-server parameter that adds an instance
to the mock repository
This file assumes that the file simple_mock_model.mof has already been loaded
so the class CIM_Foo exists.
"""

from __future__ import absolute_import, print_function

from pywbem import CIMInstance, CIMInstanceName

_INAME = 'CIM_Foo%s' % 'wbemcli_tst-1'
_INST_PATH = CIMInstanceName('CIM_Foo', {'InstanceID': _INAME})
_INST = CIMInstance('CIM_Foo',
                    properties={'InstanceID': _INAME},
                    path=_INST_PATH)

# CONN is a defined global variable in the wbemcli environment
global CONN  # pylint: disable=global-at-module-level

CONN.add_cimobjects(_INST)  # noqa: F821 pylint: disable=undefined-variable

# test that instance inserted
assert(CONN.GetInstance(_INST_PATH))  # noqa: F821,E501 pylint: disable=undefined-variable
