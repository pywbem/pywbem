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

__all__ = ['Warning', 'ToleratedServerIssueWarning']


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
