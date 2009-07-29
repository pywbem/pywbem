#
# (C) Copyright 2003, 2004 Hewlett-Packard Development Company, L.P.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; version 2 of the License.
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

# Author: Tim Potter <tpot@hp.com>

"""Useful CIM constants."""

# CIMError error code constants

CIM_ERR_FAILED                       = 1  # A general error occurred
CIM_ERR_ACCESS_DENIED                = 2  # Resource not available
CIM_ERR_INVALID_NAMESPACE            = 3  # The target namespace does not exist
CIM_ERR_INVALID_PARAMETER            = 4  # Parameter value(s) invalid
CIM_ERR_INVALID_CLASS                = 5  # The specified Class does not exist
CIM_ERR_NOT_FOUND                    = 6  # Requested object could not be found
CIM_ERR_NOT_SUPPORTED                = 7  # Operation not supported
CIM_ERR_CLASS_HAS_CHILDREN           = 8  # Class has subclasses
CIM_ERR_CLASS_HAS_INSTANCES          = 9  # Class has instances
CIM_ERR_INVALID_SUPERCLASS           = 10 # Superclass does not exist
CIM_ERR_ALREADY_EXISTS               = 11 # Object already exists
CIM_ERR_NO_SUCH_PROPERTY             = 12 # Property does not exist
CIM_ERR_TYPE_MISMATCH                = 13 # Value incompatible with type
CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED = 14 # Query language not supported
CIM_ERR_INVALID_QUERY                = 15 # Query not valid
CIM_ERR_METHOD_NOT_AVAILABLE         = 16 # Extrinsic method not executed
CIM_ERR_METHOD_NOT_FOUND             = 17 # Extrinsic method does not exist

# Provider types

PROVIDERTYPE_CLASS       = 1
PROVIDERTYPE_INSTANCE    = 2
PROVIDERTYPE_ASSOCIATION = 3
PROVIDERTYPE_INDICATION  = 4
PROVIDERTYPE_METHOD      = 5
PROVIDERTYPE_CONSUMER    = 6            # Indication consumer
PROVIDERTYPE_QUERY       = 7
