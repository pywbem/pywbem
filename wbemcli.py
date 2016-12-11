#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# (C) Copyright 2008 Hewlett-Packard Development Company, L.P.
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
The interactive shell of wbemcli provides global functions for the CIM
operations, and some functions for help display and debugging.

For tooling reasons, these functions are shown as members of the 'wbemcli'
namespace. However, they are directly available in the namespace of the
wbemcli interactive shell.
"""

from __future__ import absolute_import

# We make any global symbols private, in order to keep the namespace of the
# interactive sheel as clean as possible.

import sys as _sys
import os as _os
import getpass as _getpass
import re
import errno as _errno
import code as _code
import argparse as _argparse
from textwrap import fill

# Additional symbols for use in the interactive session
# pylint: disable=unused-import
from pprint import pprint as pp  # noqa: F401

# Conditional support of readline module
try:
    import readline as _readline
    _HAVE_READLINE = True
except ImportError as arg:
    _HAVE_READLINE = False

from pywbem import WBEMConnection
from pywbem.cim_http import get_default_ca_cert_paths
from pywbem._cliutils import SmartFormatter as _SmartFormatter

# Connection global variable. Set by remote_connection and use
# by all functions that execute operations.
CONN = None

# global ARGS contains the argparse arguments dictionary
ARGS = None


def _remote_connection(server, opts, argparser_):
    """Initiate a remote connection, via PyWBEM. Arguments for
       the request are part of the command line arguments and include
       user name, password, namespace, etc.
    """

    global CONN     # pylint: disable=global-statement

    if server[0] == '/':
        url = server

    elif re.match(r"^https{0,1}://", server) is not None:
        url = server

    elif re.match(r"^[a-zA-Z0-9]+://", server) is not None:
        argparser_.error('Invalid scheme on server argument.'
                         ' Use "http" or "https"')

    else:
        url = '%s://%s' % ('https', server)

    creds = None

    if opts.key_file is not None and opts.cert_file is None:
        argparser_.error('keyfile option requires certfile option')

    if opts.user is not None and opts.password is None:
        opts.password = _getpass.getpass('Enter password for %s: '
                                         % opts.user)

    if opts.user is not None or opts.password is not None:
        creds = (opts.user, opts.password)

    if opts.timeout is not None:
        if opts.timeout < 0 or opts.timeout > 300:
            argparser_.error('timeout option(%s) out of range' % opts.timeout)

    # if client cert and key provided, create dictionary for
    # wbem connection
    x509_dict = None
    if opts.cert_file is not None:
        x509_dict = {"cert_file": opts.cert_file}
        if opts.key_file is not None:
            x509_dict.update({'key_file': opts.key_file})

    CONN = WBEMConnection(url, creds, default_namespace=opts.namespace,
                          no_verification=opts.no_verify_cert,
                          x509=x509_dict, ca_certs=opts.ca_certs,
                          timeout=opts.timeout)

    CONN.debug = True

    return CONN


#
# Create some convenient global functions to reduce typing
#

def ein(cn, ns=None):
    """
    WBEM operation: EnumerateInstanceNames

    Enumerate the instance paths of instances of a class (including instances
    of its subclasses) in a namespace.

    Parameters:

      cn (string or CIMClassName):
          Name of the class to be enumerated (case independent).

          If specified as a `CIMClassName` object, its `host` attribute will be
          ignored.

      ns (string):
          Name of the CIM namespace to be used (case independent).

          If `None`, defaults to the namespace of the `cn` parameter if
          specified as a `CIMClassName`, or to the default namespace of the
          connection.

    Returns:

      list of CIMInstanceName:
          The instance paths, with their attributes set as follows:

          * `classname`: Name of the creation class of the instance.
          * `keybindings`: Keybindings of the instance.
          * `namespace`: Name of the CIM namespace containing the instance.
          * `host`: `None`, indicating the WBEM server is unspecified.
    """

    return CONN.EnumerateInstanceNames(cn, ns)


# pylint: disable=too-many-arguments
def ei(cn, ns=None, lo=None, di=None, iq=None, ico=None, pl=None):
    """
    WBEM operation: EnumerateInstances

    Enumerate the instances of a class (including instances of its subclasses)
    in a namespace.

    Parameters:

      cn (string or CIMClassName):
          Name of the class to be enumerated (case independent).

          If specified as a `CIMClassName` object, its `host` attribute will be
          ignored.

      ns (string):
          Name of the CIM namespace to be used (case independent).

          If `None`, defaults to the namespace of the `cn` parameter if
          specified as a `CIMClassName`, or to the default namespace of the
          connection.

      lo (bool):
          LocalOnly flag: Exclude inherited properties.

          If `None`, this parameter will not be sent to the server, and the
          server default of `True` will be used.

          Deprecated: Server implementations for `True` vary; therefore it is
          recommended to set this parameter to `False`.

      di (bool):
          DeepInheritance flag: Include properties added by subclasses.

          If `None`, this parameter will not be sent to the server, and the
          server default of `True` will be used.

      iq (bool):
          IncludeQualifiers flag: Include qualifiers.

          If `None`, this parameter will not be sent to the server, and the
          server default of `True` will be used.

          Deprecated: Instance qualifiers have been deprecated in CIM. Clients
          cannot rely on qualifiers to be returned in this operation.

      ico (bool):
          IncludeClassOrigin flag: Include class origin info for properties.

          If `None`, this parameter will not be sent to the server, and the
          server default of `False` will be used.

      pl (iterable of string):
          PropertyList: Names of properties to be included (if not otherwise
          excluded). If `None`, all properties will be included.

    Returns:

      list of CIMInstance:
          The instances, with their `path` attribute being a CIMInstanceName
          object with its attributes set as follows:

          * `classname`: Name of the creation class of the instance.
          * `keybindings`: Keybindings of the instance.
          * `namespace`: Name of the CIM namespace containing the instance.
          * `host`: `None`, indicating the WBEM server is unspecified.
    """

    return CONN.EnumerateInstances(cn, ns,
                                   LocalOnly=lo,
                                   DeepInheritance=di,
                                   IncludeQualifiers=iq,
                                   IncludeClassOrigin=ico,
                                   PropertyList=pl)


def gi(ip, lo=None, iq=None, ico=None, pl=None):
    """
    WBEM operation: GetInstance

    Retrieve an instance.

    Parameters:

      ip (CIMInstanceName):
          Instance path.

          If this object does not specify a namespace, the default namespace of
          the connection is used.

          Its `host` attribute will be ignored.

      lo (bool):
          LocalOnly flag: Exclude inherited properties.

          If `None`, this parameter will not be sent to the server, and the
          server default of `True` will be used.

          Deprecated: Server implementations for `True` vary; therefore it is
          recommended to set this parameter to `False`.

      iq (bool):
          IncludeQualifiers flag: Include qualifiers.

          If `None`, this parameter will not be sent to the server, and the
          server default of `False` will be used.

          Deprecated: Instance qualifiers have been deprecated in CIM. Clients
          cannot rely on qualifiers to be returned in this operation.

      ico (bool):
          IncludeClassOrigin flag: Include class origin info for properties.

          If `None`, this parameter will not be sent to the server, and the
          server default of `False` will be used.

      pl (iterable of string):
          PropertyList: Names of properties to be included (if not otherwise
          excluded). If `None`, all properties will be included.

    Returns:

      CIMInstance:
          The instance, with its `path` attribute being a CIMInstanceName
          object with its attributes set as follows:

          * `classname`: Name of the creation class of the instance.
          * `keybindings`: Keybindings of the instance.
          * `namespace`: Name of the CIM namespace containing the instance.
          * `host`: `None`, indicating the WBEM server is unspecified.
    """

    return CONN.GetInstance(ip,
                            LocalOnly=lo,
                            IncludeQualifiers=iq,
                            IncludeClassOrigin=ico,
                            PropertyList=pl)


def mi(mi, iq=None, pl=None):
    """
    WBEM operation: ModifyInstance

    Modify the property values of an instance.

    Parameters:

      mi (CIMInstance):
          Modified instance, also indicating its instance path.

          The properties defined in this object specify the new property
          values for the instance to be modified. Missing properties
          (relative to the class declaration) and properties provided with
          a value of `None` will be set to NULL.

      iq (bool):
          IncludeQualifiers flag: Modify instance qualifiers as specified in
          the instance.

          If `None`, this parameter will not be sent to the server, and the
          server default of `False` will be used.

          Deprecated: Instance qualifiers have been deprecated in CIM. Clients
          cannot rely on qualifiers to be modified in this operation.

      pl (iterable of string):
          PropertyList: Names of properties to be modified (if not otherwise
          excluded). If `None`, all properties will be modified.
    """

    CONN.ModifyInstance(mi,
                        IncludeQualifiers=iq,
                        PropertyList=pl)


def ci(ni, ns=None):
    """
    WBEM operation: CreateInstance

    Create an instance in a namespace.

    Parameters:

      ni (CIMInstance):
          New instance.

          Its `classname` attribute specifies the creation class.
          Its `properties` attribute specifies initial property values.
          Its `path` attribute is ignored, except for providing a default
          namespace.

      ns (string):
          Name of the CIM namespace to be used (case independent).

          If `None`, defaults to the namespace in the `path` attribute of the
          `ni` parameter, or to the default namespace of the connection.

    Returns:

      CIMInstanceName:
          The instance path, with its attributes set as follows:

          * `classname`: Name of the creation class of the instance.
          * `keybindings`: Keybindings of the instance.
          * `namespace`: Name of the CIM namespace containing the instance.
          * `host`: `None`, indicating the WBEM server is unspecified.
    """

    return CONN.CreateInstance(ni, ns)


def di(ip):
    """
    WBEM operation: DeleteInstance

    Delete an instance.

    Parameters:

      ip (CIMInstanceName):
          Instance path.

          If this object does not specify a namespace, the default namespace
          of the connection is used.
          Its `host` attribute will be ignored.
    """

    CONN.DeleteInstance(ip)


def an(op, ac=None, rc=None, r=None, rr=None):
    """
    WBEM operation: AssociatorNames

    Instance level use: Retrieve the instance paths of the instances
    associated to a source instance.

    Class level use: Retrieve the class paths of the classes associated to a
    source class.

    Parameters:

      op (CIMInstanceName):
          Source instance path; select instance level use.

      op (CIMClassName):
          Source class path; select class level use.

      ac (string):
          AssociationClass filter: Include only traversals across this
          association class.

          `None` means this filter is not applied.

      rc (string):
          ResultClass filter: Include only traversals to this associated
          (result) class.

          `None` means this filter is not applied.

      r (string):
          Role filter: Include only traversals from this role (= reference
          name) in source object.

          `None` means this filter is not applied.

      rr (string):
          ResultRole filter: Include only traversals to this role (= reference
          name) in associated (=result) objects.

          `None` means this filter is not applied.

    Returns:

      list of CIMInstanceName or CIMClassName:

          For instance level use, a list of CIMInstanceName objects representing
          the instance paths, with their attributes set as follows:

          * `classname`: Name of the creation class of the instance.
          * `keybindings`: Keybindings of the instance.
          * `namespace`: Name of the CIM namespace containing the instance.
          * `host`: Host and optionally port of the WBEM server containing
            the CIM namespace, or `None` if the server did not return host
            information.

          For class level use, a list of CIMClassName objects representing
          the class paths, with their attributes set as follows:

          * `classname`: Name of the class.
          * `namespace`: Name of the CIM namespace containing the class.
          * `host`: Host and optionally port of the WBEM server containing
            the CIM namespace, or `None` if the server did not return host
            information.
    """

    return CONN.AssociatorNames(op,
                                AssocClass=ac,
                                ResultClass=rc,
                                Role=r,
                                ResultRole=rr)


# pylint: disable=too-many-arguments
def a(op, ac=None, rc=None, r=None, rr=None, iq=None, ico=None, pl=None):
    """
    WBEM operation: Associators

    Instance level use: Retrieve the instances associated to a source instance.

    Class level use: Retrieve the classes associated to a source class.

    Parameters:

      op (CIMInstanceName):
          Source instance path; select instance level use.

      op (CIMClassName):
          Source class path; select class level use.

      ac (string):
          AssociationClass filter: Include only traversals across this
          assoiation class.

          `None` means this filter is not applied.

      rc (string):
          ResultClass filter: Include only traversals to this associated
          (result) class.

          `None` means this filter is not applied.

      r (string):
          Role filter: Include only traversals from this role (= reference
          name) in source object.

          `None` means this filter is not applied.

      rr (string):
          ResultRole filter: Include only traversals to this role (= reference
          name) in associated (=result) objects.

          `None` means this filter is not applied.

      iq (bool):
          IncludeQualifiers flag: Include qualifiers.

          Deprecated: Instance qualifiers have been deprecated in CIM.

          `None` will cause the server default of `False` to be used.

      ico (bool):
          IncludeClassOrigin flag: Include class origin info for props.

          Deprecated:  Server impls. vary; Server may treat as False.

          `None` will cause the server default of `False` to be used.

      pl (iterable of string):
          PropertyList: Names of properties to be included (if not otherwise
          excluded). If `None`, all properties will be included.

    Returns:

      list of CIMInstance or tuple (CIMClassName, CIMClass):

          For instance level use, a list of CIMInstance objects representing
          the instances, with their `path` attribute being a CIMInstanceName
          object with its attributes set as follows:

          * `classname`: Name of the creation class of the instance.
          * `keybindings`: Keybindings of the instance.
          * `namespace`: Name of the CIM namespace containing the instance.
          * `host`: Host and optionally port of the WBEM server containing
            the CIM namespace, or `None` if the server did not return host
            information.

          For class level use, a list of tuple (classpath, class) representing
          the classes, with the following (unnamed) tuple items:

          * classpath (CIMClassName): Class path with its attributes set as
            follows:

            * `classname`: Name of the class.
            * `namespace`: Name of the CIM namespace containing the class.
            * `host`: Host and optionally port of the WBEM server
              containing the CIM namespace, or `None` if the server did not
              return host information.

          * class (CIMClass): The representation of the class.
    """

    return CONN.Associators(op,
                            AssocClass=ac,
                            ResultClass=rc,
                            Role=r,
                            ResultRole=rr,
                            IncludeQualifiers=iq,
                            IncludeClassOrigin=ico,
                            PropertyList=pl)


def rn(op, rc=None, r=None):
    """
    WBEM operation: ReferenceNames

    Instance level use: Retrieve the instance paths of the association
    instances referencing a source instance.

    Class level use: Retrieve the class paths of the association classes
    referencing a source class.

    Parameters:

      op (CIMInstanceName):
          Source instance path; select instance level use.

      op (CIMClassName):
          Source class path; select class level use.

      rc (string):
          ResultClass filter: Include only traversals across this association
          (result) class.

          `None` means this filter is not applied.

      r (string):
          Role filter: Include only traversals from this role (= reference
          name) in source object.

          `None` means this filter is not applied.

    Returns:

      list of CIMInstanceName or CIMClassName:

          For instance level use, a list of CIMInstanceName objects representing
          the instance paths, with their attributes set as follows:

          * `classname`: Name of the creation class of the instance.
          * `keybindings`: Keybindings of the instance.
          * `namespace`: Name of the CIM namespace containing the instance.
          * `host`: Host and optionally port of the WBEM server containing
            the CIM namespace, or `None` if the server did not return host
            information.

          For class level use, a list of CIMClassName objects representing
          the class paths, with their attributes set as follows:

          * `classname`: Name of the class.
          * `namespace`: Name of the CIM namespace containing the class.
          * `host`: Host and optionally port of the WBEM server containing
            the CIM namespace, or `None` if the server did not return host
            information.
    """

    return CONN.ReferenceNames(op,
                               ResultClass=rc,
                               Role=r)


def r(op, rc=None, r=None, iq=None, ico=None, pl=None):
    """
    WBEM operation: References

    Instance level use: Retrieve the association instances referencing a source
    instance.

    Class level use: Retrieve the association classes referencing a source
    class.

    Parameters:

      op (CIMInstanceName):
          Source instance path; select instance level use.

      op (CIMClassName):
          Source class path; select class level use.

      rc (string):
          ResultClass filter: Include only traversals across this association
          (result) class.

          `None` means this filter is not applied.

      r (string):
          Role filter: Include only traversals from this role (= reference
          name) in source object.

          `None` means this filter is not applied.

      iq (bool):
          IncludeQualifiers flag: Include qualifiers.

          Deprecated: Instance qualifiers have been deprecated in CIM.

          `None` will cause the server default of `False` to be used.

      ico (bool):
          IncludeClassOrigin flag: Include class origin info for props.

          Deprecated:  Server impls. vary; Server may treat as False.

          `None` will cause the server default of `False` to be used.

      pl (iterable of string):
          PropertyList: Names of properties to be included (if not otherwise
          excluded). If `None`, all properties will be included.

    Returns:

      list of CIMInstance or tuple (CIMClassName, CIMClass):

          For instance level use, a list of CIMInstance objects representing
          the instances, with their `path` attribute being a CIMInstanceName
          object with its attributes set as follows:

          * `classname`: Name of the creation class of the instance.
          * `keybindings`: Keybindings of the instance.
          * `namespace`: Name of the CIM namespace containing the instance.
          * `host`: Host and optionally port of the WBEM server containing
            the CIM namespace, or `None` if the server did not return host
            information.

          For class level use, a list of tuple (classpath, class) representing
          the classes, with the following (unnamed) tuple items:

          * classpath (CIMClassName): Class path with its attributes set as
            follows:

            * `classname`: Name of the class.
            * `namespace`: Name of the CIM namespace containing the class.
            * `host`: Host and optionally port of the WBEM server
              containing the CIM namespace, or `None` if the server did not
              return host information.

          * class (CIMClass): The representation of the class.
    """

    return CONN.References(op,
                           ResultClass=rc,
                           Role=r,
                           IncludeQualifiers=iq,
                           IncludeClassOrigin=ico,
                           PropertyList=pl)


# pylint: disable=too-many-arguments
def oei(cn, ns=None, lo=None, di=None, iq=None, ico=None, pl=None, fl=None,
        fq=None, ot=None, coe=None, moc=None):
    """
    WBEM operation: OpenEnumerateInstances

    Open an enumeration sequence to enumerate the instances of a class
    (including instances of its subclasses) in a namespace. Subsequent to this
    open response, additional instances may be pulled using the
    `PullInstancesWithPath` request. The enumeration sequence may also be
    closed before it is complete with the `CloseEnumeration` request

    This operation returns a named tuple containing any instances returned and
    status of the enumeration sequence.

    Parameters:

      cn (string or CIMClassName):
          Name of the class to be enumerated (case independent).

          If specified as a `CIMClassName` object, its `host` attribute will be
          ignored.

      ns (string):
          Name of the CIM namespace to be used (case independent).

          If `None`, defaults to the namespace of the `cn` parameter if
          specified as a `CIMClassName`, or to the default namespace of the
          connection.

      lo (bool):
          LocalOnly flag: Exclude inherited properties.

          Deprecated: Server impls for True vary; Set to False.

          `None` will cause the server default of `True` to be used.

      di (bool):
          DeepInheritance flag: Include properties added by subclasses.

          `None` will cause the server default of `True` to be used.

      iq (bool):
          IncludeQualifiers flag: Include qualifiers.

          Deprecated: Instance qualifiers have been deprecated in CIM.

          `None` will cause the server default of `False` to be used.

      ico (bool):
          IncludeClassOrigin flag: Include class origin info for props.

          Deprecated: Server may treat as False.

          `None` will cause the server default of `False` to be used.

      pl (iterable of string):
          PropertyList: Names of properties to be included (if not otherwise
          excluded). If `None`, all properties will be included.

      fl (string):
          Filter query language to be used for the filter defined in the `fi`
          parameter.

          `None` means that no such filtering is peformed.

      fq (string):
          Filter to apply to objects to be returned. Based on filter query
          language defined by `fl` parameter.

          `None` means that no such filtering is peformed.

      ot (integer):
          Operation timeout in seconds. This is the minimum time the server
          must keep the enumerate session open between this open request and
          the next request.

          A value of 0 indicates that the server should never time out.

          The server may reject the proposed value.

          `None` will cause the server to use its default timeout.

      coe (bool):
          Continue on error flag.

          `None` will cause the server to use its default of `False`.

      moc (integer):
          Maximum number of objects to return for this operation.

          `None` will cause the server to use its default of 0.

    Returns:

      Named tuple, containing the following named items:

          instances (list of CIMInstance):
              The result set of instances in response to this request.

          eos (bool):
              `True` if this response is the complete response to this request
              and there are no more instances to return. Otherwise `eos` is
              `False` and the `context` item will define the context for the
              next operation.

          context (string):
              A context string that must be supplied with any subsequent pull
              or close operation on this enumeration sequence.
    """
    return CONN.OpenEnumerateInstances(cn, ns,
                                       LocalOnly=lo,
                                       DeepInheritance=di,
                                       IncludeQualifiers=iq,
                                       IncludeClassOrigin=ico,
                                       PropertyList=pl,
                                       FilterQueryLanguage=fl,
                                       FilterQuery=fq,
                                       OperationTimeout=ot,
                                       ContinueOnError=coe,
                                       MaxObjectCount=moc)


# pylint: disable=too-many-arguments
def oeip(cn, ns=None, fl=None, fq=None, ot=None, coe=None, moc=None):
    """
    WBEM operation: OpenEnumerateInstancePaths

    Open an enumeration sequence to enumerate the instances of a class
    (including instances of its subclasses) in a namespace. Subsequent to this
    open response, additional instances may be pulled using the
    `PullInstancesWithPath` request. The enumeration sequence may also be
    closed before it is complete with the `CloseEnumeration` request

    This operation returns a named tuple containing any instances returned and
    status of the enumeration sequence.

    Parameters:

      cn (string or CIMClassName):
          Name of the class to be enumerated (case independent).

          If specified as a `CIMClassName` object, its `host` attribute will be
          ignored.

      ns (string):
          Name of the CIM namespace to be used (case independent).

          If `None`, defaults to the namespace of the `cn` parameter if
          specified as a `CIMClassName`, or to the default namespace of the
          connection.

      lo (bool):
          LocalOnly flag: Exclude inherited properties.

          Deprecated: Server impls for True vary; Set to False.

          `None` will cause the server default of `True` to be used.

      fl (string):
          Filter query language to be used for the filter defined in the `fi`
          parameter.

          `None` means that no such filtering is peformed.

      fq (string):
          Filter to apply to objects to be returned. Based on filter query
          language defined by `fl` parameter.

          `None` means that no such filtering is peformed.

      ot (integer):
          Operation timeout in seconds. This is the minimum time the server
          must keep the enumerate session open between this open request and
          the next request.

          A value of 0 indicates that the server should never time out.

          The server may reject the proposed value.

          `None` will cause the server to use its default timeout.

      coe (bool):
          Continue on error flag.

          `None` will cause the server to use its default of `False`.

      moc (integer):
          Maximum number of objects to return for this operation.

          `None` will cause the server to use its default of 0.

    Returns:

      Named tuple, containing the following named items:

          paths (list of CIMInstanceName):
              The result set of instance paths in response to this request.

          eos (bool):
              `True` if this response is the complete response to this request
              and there are no more instances to return. Otherwise `eos` is
              `False` and the `context` item will define the context for the
              next operation.

          context (string):
              A context string that must be supplied with any subsequent pull
              or close operation on this enumeration sequence.
    """

    return CONN.OpenEnumerateInstancePaths(cn, ns,
                                           FilterQueryLanguage=fl,
                                           FilterQuery=fq,
                                           OperationTimeout=ot,
                                           ContinueOnError=coe,
                                           MaxObjectCount=moc)


# pylint: disable=too-many-arguments
def ori(op, rc=None, r=None, iq=None, ico=None, pl=None, fl=None, fq=None,
        ot=None, coe=None, moc=None):
    """
    WBEM operation: OpenReferenceInstances

    Open an enumeration sequence to enumerate the association instances of an
    instance in a namespace. Subsequent to this open response, additional
    instances may be pulled using the `PullInstancesWithPath` request. The
    enumeration sequence may also be closed before it is complete with the
    `CloseEnumeration` request.

    This operation returns a named tuple containing any instances returned and
    status of the enumeration sequence.

    Parameters:

      op (CIMInstanceName):
          Source instance path.

      rc (string):
          ResultClass filter: Include only traversals across this association
          (result) class.

          `None` means this filter is not applied.

      r (string):
          Role filter: Include only traversals from this role (= reference
          name) in source object.

          `None` means this filter is not applied.

      iq (bool):
          IncludeQualifiers flag: Include qualifiers.

          Deprecated: Instance qualifiers have been deprecated in CIM.

          `None` will cause the server default of `False` to be used.

      ico (bool):
          IncludeClassOrigin flag: Include class origin info for props.

          Deprecated:  Server impls. vary; Server may treat as False.

          `None` will cause the server default of `False` to be used.

      pl (iterable of string):
          PropertyList: Names of properties to be included (if not otherwise
          excluded). If `None`, all properties will be included.

      fl (string):
          Filter query language to be used for the filter defined in the `fi`
          parameter.

          `None` means that no such filtering is peformed.

      fq (string):
          Filter to apply to objects to be returned. Based on filter query
          language defined by `fl` parameter.

          `None` means that no such filtering is peformed.

      ot (integer):
          Operation timeout in seconds. This is the minimum time the server
          must keep the enumerate session open between this open request and
          the next request.

          A value of 0 indicates that the server should never time out.

          The server may reject the proposed value.

          `None` will cause the server to use its default timeout.

      coe (bool):
          Continue on error flag.

          `None` will cause the server to use its default of `False`.

      moc (integer):
          Maximum number of objects to return for this operation.

          `None` will cause the server to use its default of 0.

    Returns:

      Named tuple, containing the following named items:

          instances (list of CIMInstance):
              The result set of instances in response to this request.

          eos (bool):
              `True` if this response is the complete response to this request
              and there are no more instances to return. Otherwise `eos` is
              `False` and the `context` item will define the context for the
              next operation.

          context (string):
              A context string that must be supplied with any subsequent pull
              or close operation on this enumeration sequence.
    """
    return CONN.OpenReferenceInstances(op,
                                       ResultClass=rc,
                                       Role=r,
                                       IncludeQualifiers=iq,
                                       IncludeClassOrigin=ico,
                                       PropertyList=pl,
                                       FilterQueryLanguage=fl,
                                       FilterQuery=fq,
                                       OperationTimeout=ot,
                                       ContinueOnError=coe,
                                       MaxObjectCount=moc)


# pylint: disable=too-many-arguments
def orip(op, rc=None, r=None, fl=None, fq=None, ot=None, coe=None, moc=None):
    """
    WBEM operation: OpenReferenceInstancePaths

    Open an enumeration sequence to enumerate the association instance paths of
    an instance in a namespace. Subsequent to this open response, additional
    instances may be pulled using the `PullInstancesWithPath` request. The
    enumeration sequence may also be closed before it is complete with the
    `CloseEnumeration` request.

    This operation returns a named tuple containing any instances returned and
    status of the enumeration sequence.

    Parameters:

      op (CIMInstanceName):
          Source instance path.

      rc (string):
          ResultClass filter: Include only traversals across this association
          (result) class.

          `None` means this filter is not applied.

      r (string):
          Role filter: Include only traversals from this role (= reference
          name) in source object.

          `None` means this filter is not applied.

      fl (string):
          Filter query language to be used for the filter defined in the `fi`
          parameter.

          `None` means that no such filtering is peformed.

      fq (string):
          Filter to apply to objects to be returned. Based on filter query
          language defined by `fl` parameter.

          `None` means that no such filtering is peformed.

      ot (integer):
          Operation timeout in seconds. This is the minimum time the server
          must keep the enumerate session open between this open request and
          the next request.

          A value of 0 indicates that the server should never time out.

          The server may reject the proposed value.

          `None` will cause the server to use its default timeout.

      coe (bool):
          Continue on error flag.

          `None` will cause the server to use its default of `False`.

      moc (integer):
          Maximum number of objects to return for this operation.

          `None` will cause the server to use its default of 0.

    Returns:

      Named tuple, containing the following named items:

          paths (list of CIMInstanceName):
              The result set of instance paths in response to this request.

          eos (bool):
              `True` if this response is the complete response to this request
              and there are no more instances to return. Otherwise `eos` is
              `False` and the `context` item will define the context for the
              next operation.

          context (string):
              A context string that must be supplied with any subsequent pull
              or close operation on this enumeration sequence.
    """
    return CONN.OpenReferenceInstancePaths(op,
                                           ResultClass=rc,
                                           Role=r,
                                           FilterQueryLanguage=fl,
                                           FilterQuery=fq,
                                           OperationTimeout=ot,
                                           ContinueOnError=coe,
                                           MaxObjectCount=moc)


# pylint: disable=too-many-arguments
def oai(op, ac=None, rc=None, r=None, rr=None, iq=None, ico=None, pl=None,
        fl=None, fq=None, ot=None, coe=None, moc=None):
    """
    WBEM operation: OpenAssociatorInstances

    Open an enumeration sequence to enumerate the associated instances of an
    instance in a namespace. Subsequent to this open response, additional
    instances may be pulled using the `PullInstancesWithPath` request. The
    enumeration sequence may also be closed before it is complete with the
    `CloseEnumeration` request.

    This operation returns a named tuple containing any instances returned and
    status of the enumeration sequence.

    Parameters:

      op (CIMInstanceName):
          Source instance path.

      ac (string):
          AssociationClass filter: Include only traversals across this
          association class.

          `None` means this filter is not applied.

      rc (string):
          ResultClass filter: Include only traversals to this associated
          (result) class.

          `None` means this filter is not applied.

      r (string):
          Role filter: Include only traversals from this role (= reference
          name) in source object.

          `None` means this filter is not applied.

      rr (string):
          ResultRole filter: Include only traversals to this role (= reference
          name) in associated (=result) objects.

          `None` means this filter is not applied.

      iq (bool):
          IncludeQualifiers flag: Include qualifiers.

          Deprecated: Instance qualifiers have been deprecated in CIM.

          `None` will cause the server default of `False` to be used.

      ico (bool):
          IncludeClassOrigin flag: Include class origin info for props.

          Deprecated:  Server impls. vary; Server may treat as False.

          `None` will cause the server default of `False` to be used.

      pl (iterable of string):
          PropertyList: Names of properties to be included (if not otherwise
          excluded). If `None`, all properties will be included.

      fl (string):
          Filter query language to be used for the filter defined in the `fi`
          parameter.

          `None` means that no such filtering is peformed.

      fq (string):
          Filter to apply to objects to be returned. Based on filter query
          language defined by `fl` parameter.

          `None` means that no such filtering is peformed.

      ot (integer):
          Operation timeout in seconds. This is the minimum time the server
          must keep the enumerate session open between this open request and
          the next request.

          A value of 0 indicates that the server should never time out.

          The server may reject the proposed value.

          `None` will cause the server to use its default timeout.

      coe (bool):
          Continue on error flag.

          `None` will cause the server to use its default of `False`.

      moc (integer):
          Maximum number of objects to return for this operation.

          `None` will cause the server to use its default of 0.

    Returns:

      Named tuple, containing the following named items:

          instances (list of CIMInstance):
              The result set of instances in response to this request.

          eos (bool):
              `True` if this response is the complete response to this request
              and there are no more instances to return. Otherwise `eos` is
              `False` and the `context` item will define the context for the
              next operation.

          context (string):
              A context string that must be supplied with any subsequent pull
              or close operation on this enumeration sequence.
    """
    return CONN.OpenAssociatorInstances(op,
                                        AssocClass=ac,
                                        ResultClass=rc,
                                        Role=r,
                                        ResultRole=rr,
                                        IncludeQualifiers=iq,
                                        IncludeClassOrigin=ico,
                                        PropertyList=pl,
                                        FilterQueryLanguage=fl,
                                        FilterQuery=fq,
                                        OperationTimeout=ot,
                                        ContinueOnError=coe,
                                        MaxObjectCount=moc)


# pylint: disable=too-many-arguments
def oaip(op, ac=None, rc=None, r=None, rr=None, fl=None, fq=None, ot=None,
         coe=None, moc=None):
    """
    WBEM operation: OpenAssociatorInstancePaths

    Open an enumeration sequence to enumerate the associated instance paths of
    an instance in a namespace. Subsequent to this open response, additional
    instances may be pulled using the `PullInstancesWithPath` request. The
    enumeration sequence may also be closed before it is complete with the
    `CloseEnumeration` request.

    This operation returns a named tuple containing any instances returned and
    status of the enumeration sequence.

    Parameters:

      op (CIMInstanceName):
          Source instance path.

      rc (string):
          ResultClass filter: Include only traversals across this association
          (result) class.

          `None` means this filter is not applied.

      r (string):
          Role filter: Include only traversals from this role (= reference
          name) in source object.

          `None` means this filter is not applied.

      fl (string):
          Filter query language to be used for the filter defined in the `fi`
          parameter.

          `None` means that no such filtering is peformed.

      fq (string):
          Filter to apply to objects to be returned. Based on filter query
          language defined by `fl` parameter.

          `None` means that no such filtering is peformed.

      ot (integer):
          Operation timeout in seconds. This is the minimum time the server
          must keep the enumerate session open between this open request and
          the next request.

          A value of 0 indicates that the server should never time out.

          The server may reject the proposed value.

          `None` will cause the server to use its default timeout.

      coe (bool):
          Continue on error flag.

          `None` will cause the server to use its default of `False`.

      moc (integer):
          Maximum number of objects to return for this operation.

          `None` will cause the server to use its default of 0.

    Returns:

      Named tuple, containing the following named items:

          paths (list of CIMInstanceName):
              The result set of instance paths in response to this request.

          eos (bool):
              `True` if this response is the complete response to this request
              and there are no more instances to return. Otherwise `eos` is
              `False` and the `context` item will define the context for the
              next operation.

          context (string):
              A context string that must be supplied with any subsequent pull
              or close operation on this enumeration sequence.
    """
    return CONN.OpenAssociatorInstancePaths(op,
                                            AssocClass=ac,
                                            ResultClass=rc,
                                            Role=r,
                                            ResultRole=rr,
                                            FilterQueryLanguage=fl,
                                            FilterQuery=fq,
                                            OperationTimeout=ot,
                                            ContinueOnError=coe,
                                            MaxObjectCount=moc)


def oqi(ql, qi, ns=None, rc=None, ot=None, coe=None, moc=None):
    """
    WBEM operation: OpenQueryInstances

    Open an enumeration sequence to execute a query `fi` using the query
    language `fl`.  If this operation returns `eos` == False, the
    `PullInstances` operation is used to request additional instances.

    This operation returns a named tuple containing any instances returned and
    status of the enumeration sequence.

    Parameters:

      ql (string):
          Filter query language to be used for the filter defined in the `qi`
          parameter. This must be a query language such as CQL or WQL but NOT
          FQL.

      qi (string):
          Filter to apply to objects to be returned. Based on filter query
          language defined by the `ql` parameter.

      ns (string):
          Name of the CIM namespace to be used (case independent).

          If `None`, defaults to the default namespace of the connection.

      rc (bool):
          Controls whether a result class definition describing the returned
          instances will be returned.

          `None` will cause the server to use its default of `False`.

      ot (integer):
          Operation timeout in seconds. This is the minimum time the server
          must keep the enumerate session open between this open request and
          the next request.

          A value of 0 indicates that the server should never time out.

          The server may reject the proposed value.

          `None` will cause the server to use its default timeout.

      coe (bool):
          Continue on error flag.

          `None` will cause the server to use its default of `False`.

      moc (integer):
          Maximum number of objects to return for this operation.

          `None` will cause the server to use its default of 0.

    Returns:

      Named tuple, containing the following named items:

          instances (list of CIMInstance):
              The result set of instances in response to this request.

          eos (bool):
              `True` if this response is the complete response to this request
              and there are no more instances to return. Otherwise `eos` is
              `False` and the `context` item will define the context for the
              next operation.

          context (string):
              A context string that must be supplied with any subsequent pull
              or close operation on this enumeration sequence.

          query_result_class (CIMClass):
              Result class definition describing the returned instances, or
              `None`.
    """
    return CONN.OpenQueryInstances(FilterQueryLanguage=ql,
                                   FilterQuery=qi,
                                   namespace=ns,
                                   ReturnQueryResultClass=rc,
                                   OperationTimeout=ot,
                                   ContinueOnError=coe,
                                   MaxObjectCount=moc)


def piwp(ec, moc):
    """
    WBEM operation: PullInstancesWithPath

    Pull instances from the server as part of an already opened enumeration
    sequence.  This operation can be used as the sequence continuation for
    `OpenEnumerateInstancePaths`, `OpenAssociatorPaths` and
    `OpenReferencePaths`.

    Parameters:

      ec (string):
          Enumeration context from previous operation response for this
          enumeration session.

      moc (integer):
          Maximum number of objects to return for this operation.

    Returns:

      Named tuple, containing the following named items:

          instances (list of CIMInstance):
              The result set of instances in response to this request.

          eos (bool):
              `True` if this response is the complete response to this request
              and there are no more instances to return. Otherwise `eos` is
              `False` and the `context` item will define the context for the
              next operation.

          context (string):
              A context string that must be supplied with any subsequent pull
              or close operation on this enumeration sequence.
    """

    return CONN.PullInstancesWithPath(ec, moc)


def pip(ec, moc):
    """
    WBEM operation: PullInstancePaths

    Pull instance paths from the server as part of an already opened enumeration
    sequence.  This operation can be used as the sequence continuation for
    OpenEnumeratePaths, OpenAssociatorPaths and OpenReferencePaths.

    Parameters:

      ec (string):
          Enumeration context from previous operation response for this
          enumeration session.

      moc (integer):
          Maximum number of objects to return for this operation.

    Returns:

      Named tuple, containing the following named items:

          paths (list of CIMInstanceName):
              The result set of instance paths in response to this request.

          eos (bool):
              `True` if this response is the complete response to this request
              and there are no more instances to return. Otherwise `eos` is
              `False` and the `context` item will define the context for the
              next operation.

          context (string):
              A context string that must be supplied with any subsequent pull
              or close operation on this enumeration sequence.
    """

    return CONN.PullInstancePaths(ec, moc)


def pi(ec, moc):
    """
    WBEM operation: PullInstances

    Pull instances from the server as part of an already opened enumeration
    sequence.  This operation can be used as the sequence continuation for
    OpenQueryInstances.

    Parameters:

      ec (string):
          Enumeration context from previous operation response for this
          enumeration session.

      moc (integer):
          Maximum number of objects to return for this operation.

    Returns:

      Named tuple, containing the following named items:

          instances (list of CIMInstance):
              The result set of instances in response to this request.
              The `path` attribute is `None`.

          eos (bool):
              `True` if this response is the complete response to this request
              and there are no more instances to return. Otherwise `eos` is
              `False` and the `context` item will define the context for the
              next operation.

          context (string):
              A context string that must be supplied with any subsequent pull
              or close operation on this enumeration sequence.
    """

    return CONN.PullInstances(ec, moc)


def ce(ec):
    """
    WBEM operation: CloseEnumeration

    Close an existing open enumeration context early.  Once the sequence is
    complete, the `eos` flag is set in the last response.  Any time before
    this, the sequence may be closed early with this operation.

    Parameters:

      ec (string):
          Enumeration context from previous operation response for this
          enumeration session.
    """

    CONN.CloseEnumeration(ec)


def im(mn, op, *params, **kwparams):
    """
    WBEM operation: InvokeMethod

    Invoke a method on a target instance or a static method on a target class.

    Parameters:

      mn (string):
          Method name.

      op (CIMInstanceName):
          Target instance path.

      op (CIMClassName):
          Target class path.

      *params (named args):
          Input parameters for the method.

      **kwparams (keyword args):
          Input parameters for the method.

    Returns:

      tuple(rv, out):
          Method return value, dict with output parameters.
    """

    return CONN.InvokeMethod(mn, op, *params, **kwparams)


def ecn(ns=None, cn=None, di=None):
    """
    WBEM operation: EnumerateClassNames

    Enumerate the names of subclasses of a class, or of the top-level classes
    in a namespace.

    Parameters:

      ns (string):
          Name of the CIM namespace to be used (case independent).

          If `None`, defaults to the namespace of the `cn` parameter if
          specified as a `CIMClassName`, or to the default namespace of the
          connection.

      cn (string or CIMClassName):
          Name of the class whose subclasses are to be enumerated (case
          independent).

          `None` will enumerate the top-level classes.

          If specified as a `CIMClassName` object, its `host` attribute will be
          ignored.

      di (bool):
          DeepInheritance flag: Include also indirect subclasses.

          `None` will cause the server default of `False` to be used.

    Returns:

      list of string:
          The enumerated class names.
    """

    return CONN.EnumerateClassNames(ns,
                                    ClassName=cn,
                                    DeepInheritance=di)


def ec(ns=None, cn=None, di=None, lo=None, iq=None, ico=None):
    """
    WBEM operation: EnumerateClasses

    Enumerate the subclasses of a class, or the top-level classes in a
    namespace.

    Parameters:

      ns (string):
          Name of the CIM namespace to be used (case independent).

          If `None`, defaults to the namespace of the `cn` parameter if
          specified as a `CIMClassName`, or to the default namespace of the
          connection.

      cn (string or CIMClassName):
          Name of the class whose subclasses are to be enumerated (case
          independent).

          `None` will enumerate the top-level classes.

          If specified as a `CIMClassName` object, its `host` attribute will be
          ignored.

      di (bool):
          DeepInheritance flag: Include also indirect subclasses.

          `None` will cause the server default of `False` to be used.

      lo (bool):
          LocalOnly flag: Exclude inherited properties.

          `None` will cause the server default of `True` to be used.

      iq (bool):
          IncludeQualifiers flag: Include qualifiers.

          `None` will cause the server default of `True` to be used.

      ico (bool):
          IncludeClassOrigin flag: Include class origin info for props.

          `None` will cause the server default of `False` to be used.

    Returns:

      list of CIMClass:
          The enumerated classes.
    """

    return CONN.EnumerateClasses(ns,
                                 ClassName=cn,
                                 DeepInheritance=di,
                                 LocalOnly=lo,
                                 IncludeQualifiers=iq,
                                 IncludeClassOrigin=ico)


def gc(cn, ns=None, lo=None, iq=None, ico=None, pl=None):
    """
    WBEM operation: GetClass

    Retrieve a class.

    Parameters:

      cn (string or CIMClassName):
          Name of the class to be retrieved (case independent).

          If specified as a `CIMClassName` object, its `host` attribute will be
          ignored.

      ns (string):
          Name of the CIM namespace to be used (case independent).

          If `None`, defaults to the namespace of the `cn` parameter if
          specified as a `CIMClassName`, or to the default namespace of the
          connection.

      lo (bool):
          LocalOnly flag: Exclude inherited properties.

          `None` will cause the server default of `True` to be used.

      iq (bool):
          IncludeQualifiers flag: Include qualifiers.

          `None` will cause the server default of `True` to be used.

      ico (bool):
          IncludeClassOrigin flag: Include class origin info for props.

          `None` will cause the server default of `False` to be used.

      pl (iterable of string):
          PropertyList: Names of properties to be included (if not otherwise
          excluded). If `None`, all properties will be included.

    Returns:

      CIMClass:
          The retrieved class.
    """

    return CONN.GetClass(cn, ns,
                         LocalOnly=lo,
                         IncludeQualifiers=iq,
                         IncludeClassOrigin=ico,
                         PropertyList=pl)


def mc(mc, ns=None):
    """
    WBEM operation: ModifyClass

    Modify a class.

    Parameters:

      mc (CIMClass):
          Modified class.

      ns (string):
          Name of the CIM namespace to be used (case independent).

          `None` will use the default namespace of the connection.
    """

    CONN.ModifyClass(mc, ns)


def cc(nc, ns=None):
    """
    WBEM operation: CreateClass

    Create a class in a namespace.

    Parameters:

      nc (CIMClass):
          New class.

      ns (string):
          Name of the CIM namespace to be used (case independent).

          `None` will use the default namespace of the connection.
    """

    CONN.CreateClass(nc, ns)


def dc(cn, ns=None):
    """
    WBEM operation: DeleteClass

    Delete a class.

    Parameters:

      cn (string or CIMClassName):
          Name of the class to be deleted (case independent).

          If specified as a `CIMClassName` object, its `host` attribute will be
          ignored.

      ns (string):
          Name of the CIM namespace to be used (case independent).

          If `None`, defaults to the namespace of the `cn` parameter if
          specified as a `CIMClassName`, or to the default namespace of the
          connection.
    """

    CONN.DeleteClass(cn, ns)


def eq(ns=None):
    """
    WBEM operation: EnumerateQualifiers

    Enumerate qualifier types (= declarations) in a namespace.

    Parameters:

      ns (string):
          Name of the CIM namespace to be used (case independent).

          `None` will use the default namespace of the connection.

    Returns:

      list of CIMQualifierDeclaration:
          The enumerated qualifier types.
    """

    return CONN.EnumerateQualifiers(ns)


def gq(qn, ns=None):
    """
    WBEM operation: GetQualifier

    Retrieve a qualifier type (= declaration).

    Parameters:

      qn (string):
          Qualifier name (case independent).

      ns (string):
          Name of the CIM namespace to be used (case independent).

          `None` will use the default namespace of the connection.

    Returns:

      CIMQualifierDeclaration:
          The retrieved qualifier type.
    """

    return CONN.GetQualifier(qn, ns)


def sq(qd, ns=None):
    """
    WBEM operation: SetQualifier

    Create or modify a qualifier type (= declaration) in a namespace.

    Parameters:

      qd (CIMQualifierDeclaration):
          Qualifier type.

      ns (string):
          Name of the CIM namespace to be used (case independent).

          `None` will use the default namespace of the connection.
    """

    CONN.SetQualifier(qd, ns)


def dq(qn, ns=None):
    """
    WBEM operation: DeleteQualifier

    Delete a qualifier type (= declaration).

    Parameters:

      qn (string):
          Qualifier name (case independent).

      ns (string):
          Name of the CIM namespace to be used (case independent).

          `None` will use the default namespace of the connection.
    """

    CONN.DeleteQualifier(qn, ns)


def h():
    """Print help text for interactive environment."""

    print(_get_connection_info())
    print("""
Global functions for WBEM operations:

  ein              EnumerateInstanceNames
  ei               EnumerateInstances
  gi               GetInstance
  mi               ModifyInstance
  ci               CreateInstance
  di               DeleteInstance

  an               AssociatorNames
  a                Associators
  rn               ReferenceNames
  r                References

  oei              OpenEnumerateInstances
  oeip             OpenEnumerateInstancePaths
  oai              OpenAssociatorInstances
  oaip             OpenAssociatorInstancePaths
  ori              OpenReferenceInstances
  orip             OpenReferenceInstancePaths
  oqi              OpenQueryInstances
  piwp             PullInstancesWithPath
  pip              PullInstancePaths
  pi               PullInstances
  ce               CloseEnumeration

  im               InvokeMethod

  ecn              EnumerateClassNames
  ec               EnumerateClasses
  gc               GetClass
  mc               ModifyClass
  cc               CreateClass
  dc               DeleteClass

  eq               EnumerateQualifiers
  gq               GetQualifier
  sq               SetQualifier
  dq               DeleteQualifier

Connection:
  CONN             Global WBEMConnection object connected to the WBEM server
  conn             Alias for WBEMConnection class

Debugging support:
  pdb('<stmt>')    Enter PDB debugger to execute <stmt>

Printing support:
  pp(<obj>)        pprint function, good for dicts
  repr(<obj>)      Operation result objects have repr() for debugging
  print(<obj>.tomof())
                   Operation result objects often have a tomof()
                   producing a MOF string
  print(<obj>.tocimxmlstr())
                   Operation result objects have a tocimxmlstr()
                   producing an XML string

Help:
  help(<op>)       Help for global operation functions, e.g. help(gi)
  help(conn.<OpName>)
                   Help for operation methods on WBEMConnection, e.g.
                   help(conn.GetInstance).
  Use 'q' to get back from help().

Example:
  >>> cs = ei('CIM_ComputerSystem')[0]
  >>> pp(cs.items())
  [(u'RequestedState', 12L),
   (u'Dedicated', [1L]),
   (u'StatusDescriptions', [u'System is Functional']),
   (u'IdentifyingNumber', u'6F880AA1-F4F5-11D5-8C45-C0116FBAE02A'),
  ...

The symbols from the pywbem package namespace are available in this namespace.
""")


def pdb(stmt):
    """Run the statement under the PDB debugger."""
    import pdb
    pdb.set_trace()

    # pylint: disable=exec-used
    exec(stmt)  # Type 3 x "s" to get to stmt, and "cont" to end debugger.


conn = WBEMConnection


def _get_connection_info():
    """Return a string with the connection info."""

    info = 'Connection: %s,' % CONN.url
    if CONN.creds is not None:
        info += ' userid=%s,' % CONN.creds[0]
    else:
        info += ' no creds,'

    info += ' cacerts=%s,' % ('sys-default' if CONN.ca_certs is None
                              else CONN.ca_certs)

    info += ' verifycert=%s,' % ('off' if CONN.no_verification else 'on')

    info += ' default-namespace=%s' % CONN.default_namespace
    if CONN.x509 is not None:
        info += ', client-cert=%s' % CONN.x509['cert_file']
        try:
            kf = CONN.x509['key_file']
        except KeyError:
            kf = "none"
        info += ":%s" % kf

    if CONN.timeout is not None:
        info += ', timeout=%s' % CONN.timeout

    return fill(info, 78, subsequent_indent='    ')


def _get_banner():
    """Return a banner message for the interactive console."""

    result = ''
    result += '\nPython %s' % _sys.version
    result += '\n\nWbemcli interactive shell'
    result += '\n%s' % _get_connection_info()

    # Give hint about exiting. Most people exit with 'quit()' which will
    # not return from the interact() method, and thus will not write
    # the history.
    result += '\nPress Ctrl-D to exit'
    result += '\nType h() for help'

    return result


class _wbemcliCustomFormatter(_SmartFormatter,
                              _argparse.RawDescriptionHelpFormatter):
    """
    Define a custom Formatter to allow formatting help and epilog.

    argparse formatter specifically allows multiple inheritance for the
    formatter customization and actually recommends this in a discussion
    in one of the issues:

        http://bugs.python.org/issue13023

    Also recommended in a StackOverflow discussion:

    http://stackoverflow.com/questions/18462610/argumentparser-epilog-and-description-formatting-in-conjunction-with-argumentdef
    """
    pass


def _main():
    """
    Parse command line arguments, connect to the WBEM server and open the
    interactive shell.
    """

    global CONN     # pylint: disable=global-statement

    prog = _os.path.basename(_sys.argv[0])
    usage = '%(prog)s [options] server'
    desc = """
Provide an interactive shell for issuing operations against a WBEM server.

wbemcli executes the WBEMConnection as part of initialization so the user can
input requests as soon as the interactive shell is started.

Use h() in thenteractive shell for help for wbemcli methods and variables.
"""
    epilog = """
Examples:
  %s https://localhost:15345 -n vendor -u sheldon -p penny
          - (https localhost, port=15345, namespace=vendor user=sheldon
         password=penny)

  %s http://[2001:db8::1234-eth0] -(http port 5988 ipv6, zone id eth0)
""" % (prog, prog)

    argparser = _argparse.ArgumentParser(
        prog=prog, usage=usage, description=desc, epilog=epilog,
        add_help=False, formatter_class=_wbemcliCustomFormatter)

    pos_arggroup = argparser.add_argument_group(
        'Positional arguments')
    pos_arggroup.add_argument(
        'server', metavar='server', nargs='?',
        help='R|Host name or url of the WBEM server in this format:\n'
             '    [{scheme}://]{host}[:{port}]\n'
             '- scheme: Defines the protocol to use;\n'
             '    - "https" for HTTPs protocol\n'
             '    - "http" for HTTP protocol.\n'
             '  Default: "https".\n'
             '- host: Defines host name as follows:\n'
             '     - short or fully qualified DNS hostname,\n'
             '     - literal IPV4 address(dotted)\n'
             '     - literal IPV6 address (RFC 3986) with zone\n'
             '       identifier extensions(RFC 6874)\n'
             '       supporting "-" or %%25 for the delimiter.\n'
             '- port: Defines the WBEM server port to be used\n'
             '  Defaults:\n'
             '     - HTTP  - 5988\n'
             '     - HTTPS - 5989\n')

    server_arggroup = argparser.add_argument_group(
        'Server related options',
        'Specify the WBEM server namespace and timeout')
    server_arggroup.add_argument(
        '-n', '--namespace', dest='namespace', metavar='namespace',
        default='root/cimv2',
        help='R|Default namespace in the WBEM server for operation\n'
             'requests when namespace option not supplied with\n'
             'operation request.\n'
             'Default: %(default)s')
    server_arggroup.add_argument(
        '-t', '--timeout', dest='timeout', metavar='timeout', type=int,
        default=None,
        help='R|Timeout of the completion of WBEM Server operation\n'
             'in seconds(integer between 0 and 300).\n'
             'Default: No timeout')

    security_arggroup = argparser.add_argument_group(
        'Connection security related options',
        'Specify user name and password or certificates and keys')
    security_arggroup.add_argument(
        '-u', '--user', dest='user', metavar='user',
        help='R|User name for authenticating with the WBEM server.\n'
             'Default: No user name.')
    security_arggroup.add_argument(
        '-p', '--password', dest='password', metavar='password',
        help='R|Password for authenticating with the WBEM server.\n'
             'Default: Will be prompted for, if user name\nspecified.')
    security_arggroup.add_argument(
        '-nvc', '--no-verify-cert', dest='no_verify_cert',
        action='store_true',
        help='Client will not verify certificate returned by the WBEM'
             ' server (see cacerts). This bypasses the client-side'
             ' verification of the server identity, but allows'
             ' encrypted communication with a server for which the'
             ' client does not have certificates.')
    security_arggroup.add_argument(
        '--cacerts', dest='ca_certs', metavar='cacerts',
        help='R|File or directory containing certificates that will be\n'
             'matched against a certificate received from the WBEM\n'
             'server. Set the --no-verify-cert option to bypass\n'
             'client verification of the WBEM server certificate.\n'
             'Default: Searches for matching certificates in the\n'
             'following system directories:\n' +
        ("\n".join("%s" % p for p in get_default_ca_cert_paths())))

    security_arggroup.add_argument(
        '--certfile', dest='cert_file', metavar='certfile',
        help='R|Client certificate file for authenticating with the\n'
             'WBEM server. If option specified the client attempts\n'
             'to execute mutual authentication.\n'
             'Default: Simple authentication.')
    security_arggroup.add_argument(
        '--keyfile', dest='key_file', metavar='keyfile',
        help='R|Client private key file for authenticating with the\n'
             'WBEM server. Not required if private key is part of the\n'
             'certfile option. Not allowed if no certfile option.\n'
             'Default: No client key file. Client private key should\n'
             'then be part  of the certfile')

    general_arggroup = argparser.add_argument_group(
        'General options')
    general_arggroup.add_argument(
        '-s', '--scripts', dest='scripts', metavar='scripts', nargs='*',
        help='R|Execute the python code defined by the script before the\n'
             'user gets control. This argument may be repeated to load\n'
             'multiple scripts or multiple scripts may be listed for a\n'
             'single use of the option. Scripts are executed after the\n'
             'WBEMConnection call')
    general_arggroup.add_argument(
        '-v', '--verbose', dest='verbose',
        action='store_true', default=False,
        help='Print more messages while processing')
    general_arggroup.add_argument(
        '-h', '--help', action='help',
        help='Show this help message and exit')

    args = argparser.parse_args()

    # setup the global args so it is available to scripts
    global ARGS  # pylint: disable=global-statement
    ARGS = args

    if not args.server:
        argparser.error('No WBEM server specified')

    # Set up a client connection
    CONN = _remote_connection(args.server, args, argparser)

    # Determine file path of history file
    home_dir = '.'
    if 'HOME' in _os.environ:
        home_dir = _os.environ['HOME']  # Linux
    elif 'HOMEPATH' in _os.environ:
        home_dir = _os.environ['HOMEPATH']  # Windows
    histfile = '%s/.wbemcli_history' % home_dir

    # Read previous command line history
    if _HAVE_READLINE:
        NotFoundError = getattr(__builtins__, 'FileNotFoundError', IOError)
        try:
            _readline.read_history_file(histfile)
        except NotFoundError as exc:
            if exc.errno != _errno.ENOENT:
                raise

    # Execute any python script defined by the script argument
    if args.scripts:
        for script in args.scripts:
            if args.verbose:
                print('script %s executed' % script)
            with open(script) as fp:
                exec(fp.read(), globals(), None)  # pylint: disable=exec-used

    # Interact
    i = _code.InteractiveConsole(globals())
    i.interact(_get_banner())

    # Save command line history
    if _HAVE_READLINE:
        _readline.write_history_file(histfile)

    return 0
