#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
"""
Pywbem_mock supports several variables that provide configuration and
behavior control of the mock environment.

These configuration variables can be modified by the user directly after
importing pywbem. For example:

::

    import pywbem_mock
    pywbem_mock.config.SYSTEMNAME = 'MyTestSystemName'

Note that the pywbem source file defining these variables should not be changed
by the user. Instead, the technique shown in the example above should be used to
modify the configuration variables.
"""

# This module is meant to be safe for 'import *'.

__all__ = ['OBJECTMANAGERNAME', 'SYSTEMNAME',
           'SYSTEMCREATIONCLASSNAME', 'DEFAULT_MAX_OBJECT_COUNT',
           'OPEN_MAX_TIMEOUT', 'OBJECTMANAGERCREATIONCLASSNAME',
           'IGNORE_INSTANCE_IQ_PARAM', 'IGNORE_INSTANCE_ICO_PARAM']

#: Name for the object manager It is used in defining user-defined provider
#: properties for CIM_Namespace provider and CIM_ObjectManager provider if
#: if they are defined.
OBJECTMANAGERNAME = 'FakeObjectManager'

#: Value for the CIM_ObjectManagerCreationClassName defined in the
#: CIM_ObjectManager class.
OBJECTMANAGERCREATIONCLASSNAME = 'CIM_ObjectManager'

#: The name of the mock object. This string value becomes part of the
#: CIM_ObjectNamager instance and CIM_Namespace instances
SYSTEMNAME = 'MockSystem_WBEMServerTest'

#: Name for the property SystemCreationClassname defined a number of
#: CIM classes that are used by the pywbem_mock including CIM_Namespace
SYSTEMCREATIONCLASSNAME = 'CIM_ComputerSystem'

#: Default positive integer value for the Open... request responder default
#: value for MaxObjectCount if the value was not provided by the request.
DEFAULT_MAX_OBJECT_COUNT = 100

#: Maximum timeout in seconds for pull operations if the OperationTimeout
#: parameter is not included in the request
OPEN_MAX_TIMEOUT = 40

#: Use of the IncludeQualifiers parameter on instance requests is DEPRECATED in
#: DMTF DSP0200. The definition of IncludeQualifiers is ambiguous and when this
#: parameter is set to true, WBEM clients cannot be assured that any qualifiers
#: will be returned. A WBEM client should always set this parameter to false. To
#: minimize the impact of this recommendation on WBEM clients, a WBEM server may
#: choose to treat the value of IncludeQualifiers as false for all requests.
#:
#: The following variable forces pywbem_mock to ignore the client supplied
#: variable and not return qualifiers on EnumerateInstances and GetInstance
#: responses.
#:
#: * True (default): pywbem_mock always removes qualifiers from instances
#:   in responses
#: * False: pywbem_mock uses value of input parameter or its default to
#:   determine if qualifiers are to be removed
IGNORE_INSTANCE_IQ_PARAM = True

#: Use of the IncludeClassOrigin parameter on instance requests is DEPRECATED. A
#: WBEM server may choose to treat the value of IncludeClassOrigin parameter as
#: false for all requests, otherwise the implementation shall support the
#: original behavior as defined in the rest of this paragraph. If the
#: IncludeClassOrigin input parameter is true, the CLASSORIGIN attribute shall
#: be present on all appropriate elements in each returned Instance. If it is
#: false, no CLASSORIGIN attributes are present.
#:
#: The following variable forces pywbem_mock to ignore the client supplied
#: variable and not return qualifiers on EnumerateInstances and GetInstance
#: responses.
#:
#: * True (default): pywbem_mock always removes class origin attributes from
#:   instances in responses
#: * False: pywbem_mock uses value of input parameter or its default to
#:   determine if class origin attributes are to be removed
IGNORE_INSTANCE_ICO_PARAM = True
