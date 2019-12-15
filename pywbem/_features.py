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
Pywbem indicates support for version dependent features to users of its API.

These are features that have been introduced at some point, and users may
have a need to depend on the feature being supported (i.e. active).
If a feature is supported, the corresponding attribute is `True`. Note that
before a feature was introduced, the corresponding attribute is undefined.

The attributes listed here do not allow *controlling* whether a feature is
active or not; they only *indicate* whether the feature is supported and
active.

Note: For tooling reasons, these attributes are shown as
``pywbem._features.XXX``, but they should be used as ``pywbem.XXX``.
"""

__all__ = ['PYWBEM_USES_REQUESTS']


#: Indicates that this version of pywbem uses the 'requests' Python package.
#: This influences for example the support of CA certificates by the
#: :class:`~pywbem.WBEMConnection` class, and the exceptions that may be
#: raised by that class.
PYWBEM_USES_REQUESTS = True
