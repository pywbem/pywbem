"""
Test file for use with wbemcli -mock-server parameter that adds an instance
to the mock repository
This file assumes that the file simple_mock_model.mof has already been loaded
so the class CIM_Foo exists.
"""
from pywbem import CIMInstance, CIMInstanceName

iname = 'CIM_Foo%s' % 'wbemcli_tst-1'
inst_path = CIMInstanceName('CIM_Foo', {'InstanceID': iname})
inst = CIMInstance('CIM_Foo',
                   properties={'InstanceID': iname},
                   path=inst_path)

global CONN
CONN.add_cimobjects(inst)  # noqa: F821

# test that instance inserted
assert(CONN.GetInstance(inst_path))  # noqa: F821
