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
The following warnings are pywbem specific warnings that can be issued by
the WBEM client library.
"""

import six
from ._exceptions import Error

# This module is meant to be safe for 'import *'.

__all__ = ['Warning', 'ToleratedServerIssueWarning',
           'ToleratedSchemaIssueWarning', 'MissingKeybindingsWarning',
           'OldNameFilterWarning', 'OldNameDestinationWarning']


class Warning(Error, six.moves.builtins.Warning):
    # pylint: disable=redefined-builtin
    """
    Base class for pywbem specific warnings.
    """
    pass


class ToleratedServerIssueWarning(Warning):
    """
    This warning indicates an issue with the WBEM server that has been
    tolerated by pywbem.
    """
    pass


class ToleratedSchemaIssueWarning(Warning):
    """
    This warning indicates that a component in a DMTF CIM Schema is
    invalid but the issue is tolerated or corrected by pywbem.
    """
    pass


class MissingKeybindingsWarning(Warning):
    """
    This warning indicates that an instance path without keybindings has been
    encountered, either when sending a CIM-XML request to a WBEM server or
    when receiving a CIM-XML response from a WBEM server.

    A local creation of :class:`~pywbem.CIMinstanceName` objects without
    keybindings does not issue this warning.
    """
    pass


class OldNameFilterWarning(Warning):
    """
    This warning indicates that an owned indication filter instance with an old
    name format (prior to pywbem 1.3) was discovered on the WBEM server.

    Such filters are ignored when discovering owned filters. They should be
    cleaned up by the user.
    """
    pass


class OldNameDestinationWarning(Warning):
    """
    This warning indicates that an owned listener destination instance with an
    old name format (prior to pywbem 1.3) was discovered on the WBEM server.

    Such destinations are ignored when discovering owned destinations. They
    should be cleaned up by the user.
    """
    pass
