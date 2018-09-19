#
# (C) Copyright 2003,2004 Hewlett-Packard Development Company, L.P.
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
# Author: Tim Potter <tpot@hp.com>
#

"""
This section defines constants for two areas:

* CIM status codes (the ``CIM_ERR_*`` symbols). They are for example stored in
  :exc:`~pywbem.CIMError` exceptions.
* Default CIM namespace :data:`~pywbem.cim_constants.DEFAULT_NAMESPACE`. It is
  used as a default namespace for a connection (see
  :class:`~pywbem.WBEMConnection`) when no namespace is provided for an
  operation.

Note: For tooling reasons, the constants are shown in the namespace
``pywbem.cim_constants``. However, they are also available in the ``pywbem``
namespace and should be used from there.
"""

# disable flake8 tests for no whitespace before : and line too long
# for this file because of special formatting in the file.
# flake8: noqa: E203,E501

# This module is meant to be safe for 'import *'.

from ._utils import _format

__all__ = [
    'CIM_ERR_FAILED',
    'CIM_ERR_ACCESS_DENIED',
    'CIM_ERR_INVALID_NAMESPACE',
    'CIM_ERR_INVALID_PARAMETER',
    'CIM_ERR_INVALID_CLASS',
    'CIM_ERR_NOT_FOUND',
    'CIM_ERR_NOT_SUPPORTED',
    'CIM_ERR_CLASS_HAS_CHILDREN',
    'CIM_ERR_CLASS_HAS_INSTANCES',
    'CIM_ERR_INVALID_SUPERCLASS',
    'CIM_ERR_ALREADY_EXISTS',
    'CIM_ERR_NO_SUCH_PROPERTY',
    'CIM_ERR_TYPE_MISMATCH',
    'CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED',
    'CIM_ERR_INVALID_QUERY',
    'CIM_ERR_METHOD_NOT_AVAILABLE',
    'CIM_ERR_METHOD_NOT_FOUND',
    'CIM_ERR_NAMESPACE_NOT_EMPTY',
    'CIM_ERR_INVALID_ENUMERATION_CONTEXT',
    'CIM_ERR_INVALID_OPERATION_TIMEOUT',
    'CIM_ERR_PULL_HAS_BEEN_ABANDONED',
    'CIM_ERR_PULL_CANNOT_BE_ABANDONED',
    'CIM_ERR_FILTERED_ENUMERATION_NOT_SUPPORTED',
    'CIM_ERR_CONTINUATION_ON_ERROR_NOT_SUPPORTED',
    'CIM_ERR_SERVER_LIMITS_EXCEEDED',
    'CIM_ERR_SERVER_IS_SHUTTING_DOWN',
    'DEFAULT_NAMESPACE'
]

# CIM status codes

#: A general error occurred that is not covered by a more specific error code.
CIM_ERR_FAILED = 1

#: Access to a CIM resource is not available to the client.
CIM_ERR_ACCESS_DENIED = 2

#: The target namespace does not exist.
CIM_ERR_INVALID_NAMESPACE = 3

#: One or more parameter values passed to the method are not valid.
CIM_ERR_INVALID_PARAMETER = 4

#: The specified class does not exist.
CIM_ERR_INVALID_CLASS = 5

#: The requested object cannot be found. The operation can be unsupported on
#: behalf of the WBEM server in general or on behalf of an implementation of a
#: management profile.
CIM_ERR_NOT_FOUND = 6

#: The requested operation is not supported on behalf of the WBEM server, or on
#: behalf of a provided class. If the operation is supported for a provided
#: class but is not supported for particular instances of that class, then
#: CIM_ERR_FAILED shall be used.
CIM_ERR_NOT_SUPPORTED = 7

#: The operation cannot be invoked on this class because it has subclasses.
CIM_ERR_CLASS_HAS_CHILDREN = 8

#: The operation cannot be invoked on this class because one or more instances
#: of this class exist.
CIM_ERR_CLASS_HAS_INSTANCES = 9

#: The operation cannot be invoked because the specified superclass does not
#: exist.
CIM_ERR_INVALID_SUPERCLASS = 10

#: The operation cannot be invoked because an object already exists.
CIM_ERR_ALREADY_EXISTS = 11

#: The specified property does not exist.
CIM_ERR_NO_SUCH_PROPERTY = 12

#: The value supplied is not compatible with the type.
CIM_ERR_TYPE_MISMATCH = 13

#: The query language is not recognized or supported.
CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED = 14

#: The query is not valid for the specified query language.
CIM_ERR_INVALID_QUERY = 15

#: The extrinsic method cannot be invoked.
CIM_ERR_METHOD_NOT_AVAILABLE = 16

#: The specified extrinsic method does not exist.
CIM_ERR_METHOD_NOT_FOUND = 17

# 18 and 19 existed once and had been removed again.

#: The specified namespace is not empty.
#: *New in pywbem 0.9.*
CIM_ERR_NAMESPACE_NOT_EMPTY = 20

#: The enumeration identified by the specified context cannot be found, is in
#: a closed state, does not exist, or is otherwise invalid.
#: *New in pywbem 0.9.*
CIM_ERR_INVALID_ENUMERATION_CONTEXT = 21

#: The specified operation timeout is not supported by the WBEM server.
#: *New in pywbem 0.9.*
CIM_ERR_INVALID_OPERATION_TIMEOUT = 22

#: The pull operation has been abandoned due to execution of a concurrent
#: CloseEnumeration operation on the same enumeration.
#: *New in pywbem 0.9.*
CIM_ERR_PULL_HAS_BEEN_ABANDONED = 23

#: The attempt to abandon a concurrent pull operation on the same enumeration
#: failed. The concurrent pull operation proceeds normally.
#: *New in pywbem 0.9.*
CIM_ERR_PULL_CANNOT_BE_ABANDONED = 24

#: Using a a filter query in pulled enumerations is not supported by the WBEM
#: server.
#: *New in pywbem 0.9.*
#pylint: disable=invalid-name
CIM_ERR_FILTERED_ENUMERATION_NOT_SUPPORTED = 25

#: The WBEM server does not support continuation on error.
#: *New in pywbem 0.9.*
#pylint: disable=invalid-name
CIM_ERR_CONTINUATION_ON_ERROR_NOT_SUPPORTED = 26

#: The WBEM server has failed the operation based upon exceeding server limits.
#: *New in pywbem 0.9.*
CIM_ERR_SERVER_LIMITS_EXCEEDED = 27

#: The WBEM server is shutting down and cannot process the operation.
#: *New in pywbem 0.9.*
CIM_ERR_SERVER_IS_SHUTTING_DOWN = 28

#pylint: disable=line-too-long
_STATUSCODE2NAME = {
    CIM_ERR_FAILED                 : 'CIM_ERR_FAILED',
    CIM_ERR_ACCESS_DENIED          : 'CIM_ERR_ACCESS_DENIED',
    CIM_ERR_INVALID_NAMESPACE      : 'CIM_ERR_INVALID_NAMESPACE',
    CIM_ERR_INVALID_PARAMETER      : 'CIM_ERR_INVALID_PARAMETER',
    CIM_ERR_INVALID_CLASS          : 'CIM_ERR_INVALID_CLASS',
    CIM_ERR_NOT_FOUND              : 'CIM_ERR_NOT_FOUND',
    CIM_ERR_NOT_SUPPORTED          : 'CIM_ERR_NOT_SUPPORTED',
    CIM_ERR_CLASS_HAS_CHILDREN     : 'CIM_ERR_CLASS_HAS_CHILDREN',
    CIM_ERR_CLASS_HAS_INSTANCES    : 'CIM_ERR_CLASS_HAS_INSTANCES',
    CIM_ERR_INVALID_SUPERCLASS     : 'CIM_ERR_INVALID_SUPERCLASS',
    CIM_ERR_ALREADY_EXISTS         : 'CIM_ERR_ALREADY_EXISTS',
    CIM_ERR_NO_SUCH_PROPERTY       : 'CIM_ERR_NO_SUCH_PROPERTY',
    CIM_ERR_TYPE_MISMATCH          : 'CIM_ERR_TYPE_MISMATCH',
    CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED : 'CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED',
    CIM_ERR_INVALID_QUERY          : 'CIM_ERR_INVALID_QUERY',
    CIM_ERR_METHOD_NOT_AVAILABLE   : 'CIM_ERR_METHOD_NOT_AVAILABLE',
    CIM_ERR_METHOD_NOT_FOUND       : 'CIM_ERR_METHOD_NOT_FOUND',
    CIM_ERR_NAMESPACE_NOT_EMPTY    : 'CIM_ERR_NAMESPACE_NOT_EMPTY',
    CIM_ERR_INVALID_ENUMERATION_CONTEXT    : 'CIM_ERR_INVALID_ENUMERATION_CONTEXT',
    CIM_ERR_INVALID_OPERATION_TIMEOUT      : 'CIM_ERR_INVALID_OPERATION_TIMEOUT',
    CIM_ERR_PULL_HAS_BEEN_ABANDONED        : 'CIM_ERR_PULL_HAS_BEEN_ABANDONED',
    CIM_ERR_PULL_CANNOT_BE_ABANDONED       : 'CIM_ERR_PULL_CANNOT_BE_ABANDONED',
    CIM_ERR_FILTERED_ENUMERATION_NOT_SUPPORTED : 'CIM_ERR_FILTERED_ENUMERATION_NOT_SUPPORTED',
    CIM_ERR_CONTINUATION_ON_ERROR_NOT_SUPPORTED : 'CIM_ERR_CONTINUATION_ON_ERROR_NOT_SUPPORTED',
    CIM_ERR_SERVER_LIMITS_EXCEEDED         : 'CIM_ERR_SERVER_LIMITS_EXCEEDED',
    CIM_ERR_SERVER_IS_SHUTTING_DOWN        : 'CIM_ERR_SERVER_IS_SHUTTING_DOWN',
}

def _statuscode2name(status_code):
    """Return the symbolic name for a CIM status code."""
    try:
        s = _STATUSCODE2NAME[status_code]
    except KeyError:
        s = _format("Invalid status code {0}", status_code)
    return s


_STATUSCODE2STRING = {
    CIM_ERR_FAILED                 : 'A general error occurred',
    CIM_ERR_ACCESS_DENIED          : 'Resource not available',
    CIM_ERR_INVALID_NAMESPACE      : 'The target namespace does not exist',
    CIM_ERR_INVALID_PARAMETER      : 'Parameter value(s) invalid',
    CIM_ERR_INVALID_CLASS          : 'The specified Class does not exist',
    CIM_ERR_NOT_FOUND              : 'Requested object could not be found',
    CIM_ERR_NOT_SUPPORTED          : 'Operation not supported',
    CIM_ERR_CLASS_HAS_CHILDREN     : 'Class has subclasses',
    CIM_ERR_CLASS_HAS_INSTANCES    : 'Class has instances',
    CIM_ERR_INVALID_SUPERCLASS     : 'Superclass does not exist',
    CIM_ERR_ALREADY_EXISTS         : 'Object already exists',
    CIM_ERR_NO_SUCH_PROPERTY       : 'Property does not exist',
    CIM_ERR_TYPE_MISMATCH          : 'Value incompatible with type',
    CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED   : 'Query language not supported',
    CIM_ERR_INVALID_QUERY          : 'Query not valid',
    CIM_ERR_METHOD_NOT_AVAILABLE   : 'Extrinsic method not executed',
    CIM_ERR_METHOD_NOT_FOUND       : 'Extrinsic method does not exist',
    CIM_ERR_NAMESPACE_NOT_EMPTY    : 'Namespace not empty',
    CIM_ERR_INVALID_ENUMERATION_CONTEXT    : 'Enumeration context is invalid',
    CIM_ERR_INVALID_OPERATION_TIMEOUT      : 'Operation timeout not supported',
    CIM_ERR_PULL_HAS_BEEN_ABANDONED        : 'Pull operation has been abandoned',
    CIM_ERR_PULL_CANNOT_BE_ABANDONED       : 'Attempt to abandon a pull operation failed',
    CIM_ERR_FILTERED_ENUMERATION_NOT_SUPPORTED : 'Filtered pulled enumeration not supported',
    CIM_ERR_CONTINUATION_ON_ERROR_NOT_SUPPORTED : 'WBEM server does not support continuation on error',
    CIM_ERR_SERVER_LIMITS_EXCEEDED         : 'WBEM server limits exceeded',
    CIM_ERR_SERVER_IS_SHUTTING_DOWN        : 'WBEM server is shutting down',
}

def _statuscode2string(status_code):
    """Return a short message for a CIM status code."""
    try:
        s = _STATUSCODE2STRING[status_code]
    except KeyError:
        s = _format("Invalid status code {0}", status_code)
    return s


# Provider types
PROVIDERTYPE_CLASS = 1
PROVIDERTYPE_INSTANCE = 2
PROVIDERTYPE_ASSOCIATION = 3
PROVIDERTYPE_INDICATION = 4
PROVIDERTYPE_METHOD = 5
PROVIDERTYPE_CONSUMER = 6               # Indication consumer
PROVIDERTYPE_QUERY = 7

DEFAULT_NAMESPACE = 'root/cimv2'        #: Default CIM namespace
