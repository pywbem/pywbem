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
           'OPEN_MAX_TIMEOUT', 'OBJECTMANAGERCREATIONCLASSNAME']

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
