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
The interactive shell of wbemcli provides Python functions for the WBEM
operations, and some functions for help display and debugging:

=====================  ========================================================
Function               WBEM operation
=====================  ========================================================
:func:`~wbemcli.ei`    EnumerateInstances
:func:`~wbemcli.ein`   EnumerateInstanceNames
:func:`~wbemcli.gi`    GetInstance
:func:`~wbemcli.mi`    ModifyInstance
:func:`~wbemcli.ci`    CreateInstance
:func:`~wbemcli.di`    DeleteInstance
:func:`~wbemcli.a`     Associators
:func:`~wbemcli.an`    AssociatorNames
:func:`~wbemcli.r`     References
:func:`~wbemcli.rn`    ReferenceNames
:func:`~wbemcli.im`    InvokeMethod
:func:`~wbemcli.eqy`   ExecQuery
---------------------  --------------------------------------------------------
:func:`~wbemcli.iei`   IterEnumerateInstances (pywbem only)
:func:`~wbemcli.ieip`  IterEnumerateInstancePaths (pywbem only)
:func:`~wbemcli.iai`   IterAssociatorInstances (pywbem only)
:func:`~wbemcli.iaip`  IterAssociatorInstancePaths (pywbem only)
:func:`~wbemcli.iri`   IterReferenceInstances (pywbem only)
:func:`~wbemcli.irip`  IterReferenceInstancePaths (pywbem only)
:func:`~wbemcli.iqi`   IterQueryInstances (pywbem only)
---------------------  --------------------------------------------------------
:func:`~wbemcli.oei`   OpenEnumerateInstances
:func:`~wbemcli.oeip`  OpenEnumerateInstancePaths
:func:`~wbemcli.oai`   OpenAssociatorInstances
:func:`~wbemcli.oaip`  OpenAssociatorInstancePaths
:func:`~wbemcli.ori`   OpenReferenceInstances
:func:`~wbemcli.orip`  OpenReferenceInstancePaths
:func:`~wbemcli.oqi`   OpenQueryInstances
:func:`~wbemcli.piwp`  PullInstancesWithPath
:func:`~wbemcli.pip`   PullInstancePaths
:func:`~wbemcli.pi`    PullInstances
:func:`~wbemcli.ce`    CloseEnumeration
---------------------  --------------------------------------------------------
:func:`~wbemcli.ec`    EnumerateClasses
:func:`~wbemcli.ecn`   EnumerateClassNames
:func:`~wbemcli.gc`    GetClass
:func:`~wbemcli.mc`    ModifyClass
:func:`~wbemcli.cc`    CreateClass
:func:`~wbemcli.dc`    DeleteClass
---------------------  --------------------------------------------------------
:func:`~wbemcli.eq`    EnumerateQualifiers
:func:`~wbemcli.gq`    GetQualifier
:func:`~wbemcli.sq`    SetQualifier
:func:`~wbemcli.dq`    DeleteQualifier
---------------------  --------------------------------------------------------
:func:`~wbemcli.h`     Print help text for interactive environment
:func:`~wbemcli.pdb`   Run a statement under the PDB debugger
``pp()``               Alias for :func:`~py:pprint.pprint`
=====================  ========================================================

The interactive Python environment of the ``wbemcli`` command has ``wbemcli``
as its current Python namespace, so the functions shown below can directly be
invoked (e.g. ``ei(...)``).
"""

from __future__ import absolute_import

# We make any global symbols private, in order to keep the namespace of the
# interactive sheel as clean as possible.

import sys as _sys
import os as _os
import getpass as _getpass
import re
import traceback
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
except ImportError:
    _HAVE_READLINE = False

from pywbem import WBEMConnection
from pywbem.cim_http import get_default_ca_cert_paths
from pywbem._cliutils import SmartFormatter as _SmartFormatter
from pywbem.config import DEFAULT_ITER_MAXOBJECTCOUNT

from pywbem._logging import LOG_DESTINATIONS, \
    LOG_DETAIL_LEVELS, LOGGER_SIMPLE_NAMES, DEFAULT_LOG_DETAIL_LEVEL, \
    DEFAULT_LOG_DESTINATION, configure_loggers_from_string
from pywbem import __version__
from pywbem_mock import FakedWBEMConnection

# Connection global variable. Set by remote_connection and use
# by all functions that execute operations.
CONN = None

# global ARGS contains the argparse arguments dictionary
ARGS = None

WBEMCLI_LOG_FILENAME = 'wbemcli.log'


def build_mock_repository(conn_, file_path_list, verbose):
    """
    Build the mock repository from the file_path list and fake connection
    instance.  This allows both mof files and python files to be used to
    build the repository.

    If verbose is True, it displays the respository after it is build as
    mof.
    """
    for file_path in file_path_list:
        ext = _os.path.splitext(file_path)[1]
        if not _os.path.exists(file_path):
            raise ValueError('File name %s does not exist' % file_path)
        if ext == '.mof':
            conn_.compile_mof_file(file_path)
        elif ext == '.py':
            try:
                with open(file_path) as fp:
                    # the exec includes CONN and VERBOSE
                    globalparams = {'CONN': conn_, 'VERBOSE': verbose}
                    # pylint: disable=exec-used
                    exec(fp.read(), globalparams, None)

            except Exception as ex:
                exc_type, exc_value, exc_traceback = _sys.exc_info()
                tb = repr(traceback.format_exception(exc_type, exc_value,
                                                     exc_traceback))
                raise ValueError(
                    'Exception failure of "--mock-server" python script %r '
                    'with conn %r Exception: %r\nTraceback\n%s' %
                    (file_path, conn, ex, tb))

        else:
            raise ValueError('Invalid suffix %s on "--mock-server" '
                             'global parameter %s. Must be "py" or "mof".'
                             % (ext, file_path))

    if verbose:
        conn_.display_repository()


def _remote_connection(server, opts, argparser_):
    """Initiate a remote connection, via PyWBEM. Arguments for
       the request are part of the command line arguments and include
       user name, password, namespace, etc.
    """

    global CONN     # pylint: disable=global-statement

    if opts.timeout is not None:
        if opts.timeout < 0 or opts.timeout > 300:
            argparser_.error('timeout option(%s) out of range' % opts.timeout)

    # mock only uses the namespace timeout and statistics options from the
    # original set of options. It ignores the url
    if opts.mock_server:
        CONN = FakedWBEMConnection(
            default_namespace=opts.namespace,
            timeout=opts.timeout,
            stats_enabled=opts.statistics)

        try:
            build_mock_repository(CONN, opts.mock_server, opts.verbose)
        except ValueError as ve:
            argparser_.error('Build Repository failed: %s' % ve)

        return CONN

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
                          timeout=opts.timeout,
                          stats_enabled=opts.statistics)

    CONN.debug = True

    return CONN


#
# Create convenient global functions to reduce typing
#

def ei(cn, ns=None, lo=None, di=None, iq=None, ico=None, pl=None):
    # pylint: disable=redefined-outer-name, too-many-arguments
    """
    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.EnumerateInstances`.

    Enumerate the instances of a class (including instances of its subclasses)
    in a namespace.

    Parameters:

      cn (:term:`string` or :class:`~pywbem.CIMClassName`):
          Name of the class to be enumerated (case independent).

          If specified as a `CIMClassName` object, its `host` attribute will be
          ignored.

      ns (:term:`string`):
          Name of the CIM namespace to be used (case independent).

          If `None`, defaults to the namespace of the `cn` parameter if
          specified as a `CIMClassName`, or to the default namespace of the
          connection.

      lo (:class:`py:bool`):
          LocalOnly flag: Exclude inherited properties.

          `None` will cause the server default of `True` to be used.

          Deprecated in :term:`DSP0200`: WBEM server implementations for `True`
          may vary; this parameter should be set to `False` by the caller.

      di (:class:`py:bool`):
          DeepInheritance flag: Include properties added by subclasses.

          If `None`, this parameter will not be sent to the server, and the
          server default of `True` will be used.

      iq (:class:`py:bool`):
          IncludeQualifiers flag: Include qualifiers.

          `None` will cause the server default of `False` to be used.

          Deprecated in :term:`DSP0200`: Clients cannot rely on qualifiers to
          be returned in this operation.

      ico (:class:`py:bool`):
          IncludeClassOrigin flag: Include class origin information for the
          properties in the retrieved instances.

          `None` will cause the server default of `False` to be used.

          Deprecated in :term:`DSP0200`: WBEM servers may either implement this
          parameter as specified, or may treat any specified value as `False`.

      pl (:term:`string` or :term:`py:iterable` of :term:`string`):
          PropertyList: Names of properties to be included (if not otherwise
          excluded). An empty iterable indicates to include no properties.
          If `None`, all properties will be included.

    Returns:

      list of :class:`~pywbem.CIMInstance`:
          The instances, with their `path` attribute being a
          :class:`~pywbem.CIMInstanceName` object with its attributes set as
          follows:

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


def ein(cn, ns=None):
    """
    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.EnumerateInstanceNames`.

    Enumerate the instance paths of instances of a class (including instances
    of its subclasses) in a namespace.

    Parameters:

      cn (:term:`string` or :class:`~pywbem.CIMClassName`):
          Name of the class to be enumerated (case independent).

          If specified as a `CIMClassName` object, its `host` attribute will be
          ignored.

      ns (:term:`string`):
          Name of the CIM namespace to be used (case independent).

          If `None`, defaults to the namespace of the `cn` parameter if
          specified as a `CIMClassName`, or to the default namespace of the
          connection.

    Returns:

      list of :class:`~pywbem.CIMInstanceName`:
          The instance paths, with their attributes set as follows:

          * `classname`: Name of the creation class of the instance.
          * `keybindings`: Keybindings of the instance.
          * `namespace`: Name of the CIM namespace containing the instance.
          * `host`: `None`, indicating the WBEM server is unspecified.
    """

    return CONN.EnumerateInstanceNames(cn, ns)


def gi(ip, lo=None, iq=None, ico=None, pl=None):
    """
    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.GetInstance`.

    Retrieve an instance.

    Parameters:

      ip (:class:`~pywbem.CIMInstanceName`):
          Instance path.

          If this object does not specify a namespace, the default namespace of
          the connection is used.

          Its `host` attribute will be ignored.

      lo (:class:`py:bool`):
          LocalOnly flag: Exclude inherited properties.

          `None` will cause the server default of `True` to be used.

          Deprecated in :term:`DSP0200`: WBEM server implementations for `True`
          may vary; this parameter should be set to `False` by the caller.

      iq (:class:`py:bool`):
          IncludeQualifiers flag: Include qualifiers.

          `None` will cause the server default of `False` to be used.

          Deprecated in :term:`DSP0200`: Clients cannot rely on qualifiers to
          be returned in this operation.

      ico (:class:`py:bool`):
          IncludeClassOrigin flag: Include class origin information for the
          properties in the retrieved instance.

          `None` will cause the server default of `False` to be used.

          Deprecated in :term:`DSP0200`: WBEM servers may either implement this
          parameter as specified, or may treat any specified value as `False`.

      pl (:term:`string` or :term:`py:iterable` of :term:`string`):
          PropertyList: Names of properties to be included (if not otherwise
          excluded). An empty iterable indicates to include no properties.
          If `None`, all properties will be included.

    Returns:

      :class:`~pywbem.CIMInstance`:
          The instance, with its `path` attribute being a
          :class:`~pywbem.CIMInstanceName` object with its attributes set as
          follows:

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
    # pylint: disable=redefined-outer-name
    """
    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.ModifyInstance`.

    Modify the property values of an instance.

    Parameters:

      mi (:class:`~pywbem.CIMInstance`):
          Modified instance, also indicating its instance path.

          The properties defined in this object specify the new property
          values for the instance to be modified. Missing properties
          (relative to the class declaration) and properties provided with
          a value of `None` will be set to NULL.

      iq (:class:`py:bool`):
          IncludeQualifiers flag: Modify instance qualifiers as specified in
          the instance.

          `None` will cause the server default of `True` to be used.

          Deprecated in :term:`DSP0200`: Clients cannot rely on qualifiers to
          be modified by this operation.

      pl (:term:`string` or :term:`py:iterable` of :term:`string`):
          PropertyList: Names of properties to be modified. An empty iterable
          indicates to modify no properties. If `None`, all properties exposed
          by the instance will be modified.
    """

    CONN.ModifyInstance(mi,
                        IncludeQualifiers=iq,
                        PropertyList=pl)


def ci(ni, ns=None):
    """
    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.CreateInstance`.

    Create an instance in a namespace.

    Parameters:

      ni (:class:`~pywbem.CIMInstance`):
          New instance.

          Its `classname` attribute specifies the creation class.
          Its `properties` attribute specifies initial property values.
          Its `path` attribute is ignored, except for providing a default
          namespace.

          Instance-level qualifiers have been deprecated in CIM, so any
          qualifier values specified using the `qualifiers` attribute
          of this object will be ignored.

      ns (:term:`string`):
          Name of the CIM namespace to be used (case independent).

          If `None`, defaults to the namespace in the `path` attribute of the
          `ni` parameter, or to the default namespace of the connection.

    Returns:

      CIMInstanceName:
          The instance path of the new instance, with its attributes set as
          follows:

          * `classname`: Name of the creation class of the instance.
          * `keybindings`: Keybindings of the instance.
          * `namespace`: Name of the CIM namespace containing the instance.
          * `host`: `None`, indicating the WBEM server is unspecified.
    """

    return CONN.CreateInstance(ni, ns)


def di(ip):
    """
    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.DeleteInstance`.

    Delete an instance.

    Parameters:

      ip (:class:`~pywbem.CIMInstanceName`):
          Instance path of the instance to be deleted.

          If this object does not specify a namespace, the default namespace
          of the connection is used.
          Its `host` attribute will be ignored.
    """

    CONN.DeleteInstance(ip)


def a(op, ac=None, rc=None, r=None, rr=None, iq=None, ico=None, pl=None):
    # pylint: disable=too-many-arguments, redefined-outer-name, invalid-name
    """
    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.Associators`.

    Instance-level use: Retrieve the instances associated to a source instance.

    Class-level use: Retrieve the classes associated to a source class.

    Parameters:

      op (:class:`~pywbem.CIMInstanceName`):
          Source instance path; select instance-level use.

      op (:class:`~pywbem.CIMClassName`):
          Source class path; select class-level use.

      ac (:term:`string`):
          AssocClass filter: Include only traversals across this association
          class.

          `None` means this filter is not applied.

      rc (:term:`string`):
          ResultClass filter: Include only traversals to this associated
          (result) class.

          `None` means this filter is not applied.

      r (:term:`string`):
          Role filter: Include only traversals from this role (= reference
          name) in source object.

          `None` means this filter is not applied.

      rr (:term:`string`):
          ResultRole filter: Include only traversals to this role (= reference
          name) in associated (=result) objects.

          `None` means this filter is not applied.

      iq (:class:`py:bool`):
          IncludeQualifiers flag: Include qualifiers.

          `None` will cause the server default of `False` to be used.

          Deprecated in :term:`DSP0200`: Clients cannot rely on qualifiers to
          be returned in this operation.

      ico (:class:`py:bool`):
          IncludeClassOrigin flag: Include class origin information for the
          properties in the retrieved instances or for the properties and
          methods in the retrieved classes.

          `None` will cause the server default of `False` to be used.

          Deprecated in :term:`DSP0200` for instance-level use: WBEM servers
          may either implement this parameter as specified, or may treat any
          specified value as `False`.

      pl (:term:`string` or :term:`py:iterable` of :term:`string`):
          PropertyList: Names of properties to be included (if not otherwise
          excluded). An empty iterable indicates to include no properties.
          If `None`, all properties will be included.

    Returns:

      list of result objects:

        * For instance-level use, a list of :class:`~pywbem.CIMInstance` objects
          representing the retrieved instances, with their `path` attribute
          being a :class:`~pywbem.CIMInstanceName` object with its attributes
          set as follows:

          * `classname`: Name of the creation class of the instance.
          * `keybindings`: Keybindings of the instance.
          * `namespace`: Name of the CIM namespace containing the instance.
          * `host`: Host and optionally port of the WBEM server containing
            the CIM namespace, or `None` if the server did not return host
            information.

        * For class-level use, a list of tuple (classpath, class) representing
          the retrieved classes, with the following (unnamed) tuple items:

          * classpath (:class:`~pywbem.CIMClassName`): Class path with its
            attributes set as follows:

            * `classname`: Name of the class.
            * `namespace`: Name of the CIM namespace containing the class.
            * `host`: Host and optionally port of the WBEM server
              containing the CIM namespace, or `None` if the server did not
              return host information.

          * class (:class:`~pywbem.CIMClass`): The representation of the class.
    """

    return CONN.Associators(op,
                            AssocClass=ac,
                            ResultClass=rc,
                            Role=r,
                            ResultRole=rr,
                            IncludeQualifiers=iq,
                            IncludeClassOrigin=ico,
                            PropertyList=pl)


def an(op, ac=None, rc=None, r=None, rr=None):
    # pylint: disable=redefined-outer-name, invalid-name
    """
    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.AssociatorNames`.

    Instance-level use: Retrieve the instance paths of the instances associated
    to a source instance.

    Class-level use: Retrieve the class paths of the classes associated
    to a source class.

    Parameters:

      op (:class:`~pywbem.CIMInstanceName`):
          Source instance path; select instance-level use.

      op (:class:`~pywbem.CIMClassName`):
          Source class path; select class-level use.

      ac (:term:`string`):
          AssocClass filter: Include only traversals across this association
          class.

          `None` means this filter is not applied.

      rc (:term:`string`):
          ResultClass filter: Include only traversals to this associated
          (result) class.

          `None` means this filter is not applied.

      r (:term:`string`):
          Role filter: Include only traversals from this role (= reference
          name) in source object.

          `None` means this filter is not applied.

      rr (:term:`string`):
          ResultRole filter: Include only traversals to this role (= reference
          name) in associated (=result) objects.

          `None` means this filter is not applied.

    Returns:

      list of result objects:

        * For instance-level use, a list of :class:`~pywbem.CIMInstanceName`
          objects representing the retrieved instance paths, with their
          attributes set as follows:

          * `classname`: Name of the creation class of the instance.
          * `keybindings`: Keybindings of the instance.
          * `namespace`: Name of the CIM namespace containing the instance.
          * `host`: Host and optionally port of the WBEM server containing
            the CIM namespace, or `None` if the server did not return host
            information.

        * For class-level use, a list of :class:`~pywbem.CIMClassName` objects
          representing the retrieved class paths, with their attributes set as
          follows:

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


def r(op, rc=None, r=None, iq=None, ico=None, pl=None):
    # pylint: disable=redefined-outer-name, invalid-name, invalid-name
    """
    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.References`.

    Instance-level use: Retrieve the association instances referencing a source
    instance.

    Class-level use: Retrieve the association classes referencing a source
    class.

    Parameters:

      op (:class:`~pywbem.CIMInstanceName`):
          Source instance path; select instance-level use.

      op (:class:`~pywbem.CIMClassName`):
          Source class path; select class-level use.

      rc (:term:`string`):
          ResultClass filter: Include only traversals across this association
          (result) class.

          `None` means this filter is not applied.

      r (:term:`string`):
          Role filter: Include only traversals from this role (= reference
          name) in source object.

          `None` means this filter is not applied.

      iq (:class:`py:bool`):
          IncludeQualifiers flag: Include qualifiers.

          `None` will cause the server default of `False` to be used.

          Deprecated in :term:`DSP0200`: Clients cannot rely on qualifiers to
          be returned in this operation.

      ico (:class:`py:bool`):
          IncludeClassOrigin flag: Include class origin information for the
          properties in the retrieved instances or for the properties and
          methods in the retrieved classes.

          `None` will cause the server default of `False` to be used.

          Deprecated in :term:`DSP0200` for instance-level use: WBEM servers
          may either implement this parameter as specified, or may treat any
          specified value as `False`.

      pl (:term:`string` or :term:`py:iterable` of :term:`string`):
          PropertyList: Names of properties to be included (if not otherwise
          excluded). An empty iterable indicates to include no properties.
          If `None`, all properties will be included.

    Returns:

      list of result objects:

        * For instance-level use, a list of :class:`~pywbem.CIMInstance` objects
          representing the retrieved instances, with their `path` attribute
          being a :class:`~pywbem.CIMInstanceName` object with its attributes
          set as follows:

          * `classname`: Name of the creation class of the instance.
          * `keybindings`: Keybindings of the instance.
          * `namespace`: Name of the CIM namespace containing the instance.
          * `host`: Host and optionally port of the WBEM server containing
            the CIM namespace, or `None` if the server did not return host
            information.

        * For class-level use, a list of tuple (classpath, class) representing
          the retrieved classes, with the following (unnamed) tuple items:

          * classpath (:class:`~pywbem.CIMClassName`): Class path with its
            attributes set as follows:

            * `classname`: Name of the class.
            * `namespace`: Name of the CIM namespace containing the class.
            * `host`: Host and optionally port of the WBEM server
              containing the CIM namespace, or `None` if the server did not
              return host information.

          * class (:class:`~pywbem.CIMClass`): The representation of the class.
    """

    return CONN.References(op,
                           ResultClass=rc,
                           Role=r,
                           IncludeQualifiers=iq,
                           IncludeClassOrigin=ico,
                           PropertyList=pl)


def rn(op, rc=None, r=None):
    # pylint: disable=redefined-outer-name, invalid-name
    """
    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.ReferenceNames`.

    Instance-level use: Retrieve the instance paths of the association
    instances referencing a source instance.

    Class-level use: Retrieve the class paths of the association classes
    referencing a source class.

    Parameters:

      op (:class:`~pywbem.CIMInstanceName`):
          Source instance path; select instance-level use.

      op (:class:`~pywbem.CIMClassName`):
          Source class path; select class-level use.

      rc (:term:`string`):
          ResultClass filter: Include only traversals across this association
          (result) class.

          `None` means this filter is not applied.

      r (:term:`string`):
          Role filter: Include only traversals from this role (= reference
          name) in source object.

          `None` means this filter is not applied.

    Returns:

      list of result objects:

        * For instance-level use, a list of :class:`~pywbem.CIMInstanceName`
          objects representing the retrieved instance paths, with their
          attributes set as follows:

          * `classname`: Name of the creation class of the instance.
          * `keybindings`: Keybindings of the instance.
          * `namespace`: Name of the CIM namespace containing the instance.
          * `host`: Host and optionally port of the WBEM server containing
            the CIM namespace, or `None` if the server did not return host
            information.

        * For class-level use, a list of :class:`~pywbem.CIMClassName` objects
          representing the retrieved class paths, with their attributes set as
          follows:

          * `classname`: Name of the class.
          * `namespace`: Name of the CIM namespace containing the class.
          * `host`: Host and optionally port of the WBEM server containing
            the CIM namespace, or `None` if the server did not return host
            information.
    """

    return CONN.ReferenceNames(op,
                               ResultClass=rc,
                               Role=r)


def im(mn, op, params, **kwparams):
    """
    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.InvokeMethod`.

    Invoke a method on a target instance or on a target class.

    The methods that can be invoked are static and non-static methods defined
    in a class (also known as *extrinsic* methods). Static methods can be
    invoked on instances and on classes. Non-static methods can be invoked only
    on instances.

    Parameters:

      mn (:term:`string`):
          Method name.

      op (:class:`~pywbem.CIMInstanceName`):
          Target instance path.

      op (:class:`~pywbem.CIMClassName`):
          Target class path.

      params (:term:`py:iterable`):
          Input parameters for the method.

          Each item in the iterable is a single parameter value and can be any
          of:

            * :class:`~pywbem.CIMParameter` representing a parameter value. The
              `name`, `value`, `type` and `embedded_object` attributes of this
              object are used.

            * tuple of name, value, with:

                - name (:term:`string`): Parameter name (case independent)
                - value (:term:`CIM data type`): Parameter value

      **kwparams (named/keyword arguments):
          Input parameters for the method.

            * key (:term:`string`): Parameter name (case independent)
            * value (:term:`CIM data type`): Parameter value

    Returns:

      tuple(rv, out), with these tuple items:

        * rv (:term:`CIM data type`):
          Return value of the CIM method.
        * out (:ref:`NocaseDict`):
          Dictionary with all provided output parameters of the CIM method,
          with:

          * key (:term:`unicode string`):
            Parameter name
          * value (:term:`CIM data type`):
            Parameter value
    """

    return CONN.InvokeMethod(mn, op, params, **kwparams)


def eqy(ql, qs, ns=None,):
    """
    *New in pywbem 0.12*

    This function is a wrapper for :meth:`~pywbem.WBEMConnection.ExecQuery`.

    Execute a query in a namespace.

    Parameters:

      ql (:term:`string`):
          Name of the query language used in the `qs` parameter, e.g.
          "DMTF:CQL" for CIM Query Language, and "WQL" for WBEM Query
          Language. Because this is not a filter query, "DMTF:FQL" is not a
          valid query language for this request.

      qs (:term:`string`):
          Query string in the query language specified in the `ql` parameter.

      ns (:term:`string`):
          Name of the CIM namespace to be used (case independent).

          If `None`, defaults to the default namespace of the connection.

    Returns:

        A list of :class:`~pywbem.CIMInstance` objects that represents
        the query result.

        These instances have their `path` attribute set to identify
        their creation class and the target namespace of the query, but
        they are not addressable instances.
    """  # noqa: E501

    return CONN.ExecQuery(QueryLanguage=ql,
                          Query=qs,
                          namespace=ns)


def iei(cn, ns=None, lo=None, di=None, iq=None, ico=None, pl=None, fl=None,
        fs=None, ot=None, coe=None, moc=DEFAULT_ITER_MAXOBJECTCOUNT,):
    # pylint: disable=too-many-arguments, redefined-outer-name
    """
    *New in pywbem 0.10 as experimental and finalized in 0.12.*

    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.IterEnumerateInstances`.

    Enumerate the instances of a class (including instances of its
    subclasses) in a namespace,
    using the corresponding pull operations if supported by the WBEM server
    or otherwise the corresponding traditional operation, and using the
    Python :term:`py:generator` idiom to return the result.

    This method is an alternative to using the pull operations directly,
    that frees the user of having to know whether the WBEM server supports
    pull operations.

    Parameters:

      cn (:term:`string` or :class:`~pywbem.CIMClassName`):
          Name of the class to be enumerated (case independent).

          If specified as a `CIMClassName` object, its `host` attribute will be
          ignored.

      ns (:term:`string`):
          Name of the CIM namespace to be used (case independent).

          If `None`, defaults to the namespace of the `cn` parameter if
          specified as a `CIMClassName`, or to the default namespace of the
          connection.

      lo (:class:`py:bool`):
          LocalOnly flag: Exclude inherited properties.

          `None` will cause the server default of `True` to be used.

          Deprecated in :term:`DSP0200`: WBEM server implementations for `True`
          may vary; this parameter should be set to `False` by the caller.

      di (:class:`py:bool`):
          DeepInheritance flag: Include properties added by subclasses.

          `None` will cause the server default of `True` to be used.

      iq (:class:`py:bool`):
          IncludeQualifiers flag: Include qualifiers.

          `None` will cause the server default of `False` to be used.

          Deprecated in :term:`DSP0200`: Clients cannot rely on qualifiers to
          be included.

      ico (:class:`py:bool`):
          IncludeClassOrigin flag: Include class origin information for the
          properties in the retrieved instances.

          `None` will cause the server default of `False` to be used.

          Deprecated in :term:`DSP0200`: WBEM servers may either implement this
          parameter as specified, or may treat any specified value as `False`.

      pl (:term:`string` or :term:`py:iterable` of :term:`string`):
          PropertyList: Names of properties to be included (if not otherwise
          excluded). An empty iterable indicates to include no properties.
          If `None`, all properties will be included.

      fl (:term:`string`):
          Filter query language to be used for the filter defined in the `fs`
          parameter. The DMTF-defined Filter Query Language
          (see :term:`DSP0212`) is specified as "DMTF:FQL".

          `None` means that no such filtering is peformed.

      fs (:term:`string`):
          Filter to apply to objects to be returned. Based on filter query
          language defined by `fl` parameter.

          `None` means that no such filtering is peformed.

      ot (:class:`~pywbem.Uint32`):
          Operation timeout in seconds. This is the minimum time the WBEM server
          must keep the enumeration session open between requests on that
          session.

          A value of 0 indicates that the server should never time out.

          The server may reject the proposed value.

          `None` will cause the server to use its default timeout.

      coe (:class:`py:bool`):
          Continue on error flag.

          `None` will cause the server to use its default of `False`.

      moc (:class:`~pywbem.Uint32`):
          Maximum number of instances the WBEM server may return for each of
          the open and pull requests issued during the iterations over the
          returned generator object.

          Zero and `None` are not allowed.

    Returns:

      :term:`py:generator` iterating :class:`~pywbem.CIMInstance`:
      A generator object that iterates the resulting CIM instances.
      These instances include an instance path that has its host and
      namespace components set.
    """

    return CONN.IterEnumerateInstances(cn, ns,
                                       LocalOnly=lo,
                                       DeepInheritance=di,
                                       IncludeQualifiers=iq,
                                       IncludeClassOrigin=ico,
                                       PropertyList=pl,
                                       FilterQueryLanguage=fl,
                                       FilterQuery=fs,
                                       OperationTimeout=ot,
                                       ContinueOnError=coe,
                                       MaxObjectCount=moc)


def ieip(cn, ns=None, fl=None, fs=None, ot=None, coe=None,
         moc=DEFAULT_ITER_MAXOBJECTCOUNT,):
    # pylint: disable=too-many-arguments
    """
    *New in pywbem 0.10 as experimental and finalized in 0.12.*

    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.IterEnumerateInstancePaths`.

    Enumerate the instance paths of instances of a class (including
    instances of its subclasses) in a namespace,
    using the corresponding pull operations if supported by the WBEM server
    or otherwise the corresponding traditional operation, and using the
    Python :term:`py:generator` idiom to return the result.

    This method is an alternative to using the pull operations directly,
    that frees the user of having to know whether the WBEM server supports
    pull operations.

    Parameters:

      cn (:term:`string` or :class:`~pywbem.CIMClassName`):
          Name of the class to be enumerated (case independent).

          If specified as a `CIMClassName` object, its `host` attribute will be
          ignored.

      ns (:term:`string`):
          Name of the CIM namespace to be used (case independent).

          If `None`, defaults to the namespace of the `cn` parameter if
          specified as a `CIMClassName`, or to the default namespace of the
          connection.

      fl (:term:`string`):
          Filter query language to be used for the filter defined in the `fs`
          parameter. The DMTF-defined Filter Query Language
          (see :term:`DSP0212`) is specified as "DMTF:FQL".

          `None` means that no such filtering is peformed.

      fs (:term:`string`):
          Filter to apply to objects to be returned. Based on filter query
          language defined by `fl` parameter.

          `None` means that no such filtering is peformed.

      ot (:class:`~pywbem.Uint32`):
          Operation timeout in seconds. This is the minimum time the WBEM server
          must keep the enumeration session open between requests on that
          session.

          A value of 0 indicates that the server should never time out.

          The server may reject the proposed value.

          `None` will cause the server to use its default timeout.

      coe (:class:`py:bool`):
          Continue on error flag.

          `None` will cause the server to use its default of `False`.

      moc (:class:`~pywbem.Uint32`):
          Maximum number of instances the WBEM server may return for each of
          the open and pull requests issued during the iterations over the
          returned generator object.

          Zero and `None` are not allowed.

    Returns:

      :term:`py:generator` iterating :class:`~pywbem.CIMInstanceName`:
      A generator object that iterates the resulting CIM instance paths.
      These instance paths have their host and namespace components set.
    """

    return CONN.IterEnumerateInstancePaths(cn, ns,
                                           FilterQueryLanguage=fl,
                                           FilterQuery=fs,
                                           OperationTimeout=ot,
                                           ContinueOnError=coe,
                                           MaxObjectCount=moc)


def iai(ip, ac=None, rc=None, r=None, rr=None, iq=None, ico=None, pl=None,
        fl=None, fs=None, ot=None, coe=None, moc=DEFAULT_ITER_MAXOBJECTCOUNT):
    # pylint: disable=too-many-arguments, redefined-outer-name, invalid-name
    """
    *New in pywbem 0.10 as experimental and finalized in 0.12.*

    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.IterAssociatorInstances`.

    Retrieve the instances associated to a source instance,
    using the corresponding pull operations if supported by the WBEM server
    or otherwise the corresponding traditional operation, and using the
    Python :term:`py:generator` idiom to return the result.

    This method is an alternative to using the pull operations directly,
    that frees the user of having to know whether the WBEM server supports
    pull operations.

    Parameters:

      ip (:class:`~pywbem.CIMInstanceName`):
          Source instance path.

      ac (:term:`string`):
          AssocClass filter: Include only traversals across this association
          class.

          `None` means this filter is not applied.

      rc (:term:`string`):
          ResultClass filter: Include only traversals to this associated
          (result) class.

          `None` means this filter is not applied.

      r (:term:`string`):
          Role filter: Include only traversals from this role (= reference
          name) in source object.

          `None` means this filter is not applied.

      rr (:term:`string`):
          ResultRole filter: Include only traversals to this role (= reference
          name) in associated (=result) objects.

          `None` means this filter is not applied.

      iq (:class:`py:bool`):
          IncludeQualifiers flag: Include qualifiers.

          `None` will cause the server default of `False` to be used.

          Deprecated in :term:`DSP0200`: Clients cannot rely on qualifiers to
          be included.

      ico (:class:`py:bool`):
          IncludeClassOrigin flag: Include class origin information for the
          properties in the retrieved instances.

          `None` will cause the server default of `False` to be used.

          Deprecated in :term:`DSP0200`: WBEM servers may either implement this
          parameter as specified, or may treat any specified value as `False`.

      pl (:term:`string` or :term:`py:iterable` of :term:`string`):
          PropertyList: Names of properties to be included (if not otherwise
          excluded). An empty iterable indicates to include no properties.
          If `None`, all properties will be included.

      fl (:term:`string`):
          Filter query language to be used for the filter defined in the `fs`
          parameter. The DMTF-defined Filter Query Language
          (see :term:`DSP0212`) is specified as "DMTF:FQL".

          `None` means that no such filtering is peformed.

      fs (:term:`string`):
          Filter to apply to objects to be returned. Based on filter query
          language defined by `fl` parameter.

          `None` means that no such filtering is peformed.

      ot (:class:`~pywbem.Uint32`):
          Operation timeout in seconds. This is the minimum time the WBEM server
          must keep the enumeration session open between requests on that
          session.

          A value of 0 indicates that the server should never time out.

          The server may reject the proposed value.

          `None` will cause the server to use its default timeout.

      coe (:class:`py:bool`):
          Continue on error flag.

          `None` will cause the server to use its default of `False`.

      moc (:class:`~pywbem.Uint32`):
          Maximum number of instances the WBEM server may return for each of
          the open and pull requests issued during the iterations over the
          returned generator object.

          Zero and `None` are not allowed.

    Returns:

      :term:`py:generator` iterating :class:`~pywbem.CIMInstance`:
      A generator object that iterates the resulting CIM instances.
      These instances include an instance path that has its host and
      namespace components set.
    """

    return CONN.IterAssociatorInstances(ip,
                                        AssocClass=ac,
                                        ResultClass=rc,
                                        Role=r,
                                        ResultRole=rr,
                                        IncludeQualifiers=iq,
                                        IncludeClassOrigin=ico,
                                        PropertyList=pl,
                                        FilterQueryLanguage=fl,
                                        FilterQuery=fs,
                                        OperationTimeout=ot,
                                        ContinueOnError=coe,
                                        MaxObjectCount=moc)


def iaip(ip, ac=None, rc=None, r=None, rr=None, fl=None, fs=None, ot=None,
         coe=None, moc=DEFAULT_ITER_MAXOBJECTCOUNT):
    # pylint: disable=too-many-arguments, redefined-outer-name, invalid-name
    """
    *New in pywbem 0.10 as experimental and finalized in 0.12.*

    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.IterAssociatorInstancePaths`.

    Retrieve the instance paths of the instances associated to a source
    instance,
    using the corresponding pull operations if supported by the WBEM server
    or otherwise the corresponding traditional operation, and using the
    Python :term:`py:generator` idiom to return the result.

    This method is an alternative to using the pull operations directly,
    that frees the user of having to know whether the WBEM server supports
    pull operations.

    Parameters:

      ip (:class:`~pywbem.CIMInstanceName`):
          Source instance path.

      ac (:term:`string`):
          AssocClass filter: Include only traversals across this association
          class.

          `None` means this filter is not applied.

      rc (:term:`string`):
          ResultClass filter: Include only traversals to this associated
          (result) class.

          `None` means this filter is not applied.

      r (:term:`string`):
          Role filter: Include only traversals from this role (= reference
          name) in source object.

          `None` means this filter is not applied.

      rr (:term:`string`):
          ResultRole filter: Include only traversals to this role (= reference
          name) in associated (=result) objects.

          `None` means this filter is not applied.

      fl (:term:`string`):
          Filter query language to be used for the filter defined in the `fs`
          parameter. The DMTF-defined Filter Query Language
          (see :term:`DSP0212`) is specified as "DMTF:FQL".

          `None` means that no such filtering is peformed.

      fs (:term:`string`):
          Filter to apply to objects to be returned. Based on filter query
          language defined by `fl` parameter.

          `None` means that no such filtering is peformed.

      ot (:class:`~pywbem.Uint32`):
          Operation timeout in seconds. This is the minimum time the WBEM server
          must keep the enumeration session open between requests on that
          session.

          A value of 0 indicates that the server should never time out.

          The server may reject the proposed value.

          `None` will cause the server to use its default timeout.

      coe (:class:`py:bool`):
          Continue on error flag.

          `None` will cause the server to use its default of `False`.

      moc (:class:`~pywbem.Uint32`):
          Maximum number of instances the WBEM server may return for each of
          the open and pull requests issued during the iterations over the
          returned generator object.

          Zero and `None` are not allowed.

    Returns:

      :term:`py:generator` iterating :class:`~pywbem.CIMInstanceName`:
      A generator object that iterates the resulting CIM instance paths.
      These instance paths have their host and namespace components set.
    """

    return CONN.IterAssociatorInstancePaths(ip,
                                            AssocClass=ac,
                                            ResultClass=rc,
                                            Role=r,
                                            ResultRole=rr,
                                            FilterQueryLanguage=fl,
                                            FilterQuery=fs,
                                            OperationTimeout=ot,
                                            ContinueOnError=coe,
                                            MaxObjectCount=moc)


def iri(ip, rc=None, r=None, iq=None, ico=None, pl=None, fl=None, fs=None,
        ot=None, coe=None, moc=DEFAULT_ITER_MAXOBJECTCOUNT):
    # pylint: disable=too-many-arguments, redefined-outer-name, invalid-name
    """
    *New in pywbem 0.10 as experimental and finalized in 0.12.*

    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.IterReferenceInstances`.

    Retrieve the association instances that reference a source instance,
    using the corresponding pull operations if supported by the WBEM server
    or otherwise the corresponding traditional operation, and using the
    Python :term:`py:generator` idiom to return the result.

    This method is an alternative to using the pull operations directly,
    that frees the user of having to know whether the WBEM server supports
    pull operations.

    Parameters:

      ip (:class:`~pywbem.CIMInstanceName`):
          Source instance path.

      rc (:term:`string`):
          ResultClass filter: Include only traversals across this association
          (result) class.

          `None` means this filter is not applied.

      r (:term:`string`):
          Role filter: Include only traversals from this role (= reference
          name) in source object.

          `None` means this filter is not applied.

      iq (:class:`py:bool`):
          IncludeQualifiers flag: Include qualifiers.

          `None` will cause the server default of `False` to be used.

          Deprecated in :term:`DSP0200`: Clients cannot rely on qualifiers to
          be included.

      ico (:class:`py:bool`):
          IncludeClassOrigin flag: Include class origin information for the
          properties in the retrieved instances.

          `None` will cause the server default of `False` to be used.

          Deprecated in :term:`DSP0200`: WBEM servers may either implement this
          parameter as specified, or may treat any specified value as `False`.

      pl (:term:`string` or :term:`py:iterable` of :term:`string`):
          PropertyList: Names of properties to be included (if not otherwise
          excluded). An empty iterable indicates to include no properties.
          If `None`, all properties will be included.

      fl (:term:`string`):
          Filter query language to be used for the filter defined in the `fs`
          parameter. The DMTF-defined Filter Query Language
          (see :term:`DSP0212`) is specified as "DMTF:FQL".

          `None` means that no such filtering is peformed.

      fs (:term:`string`):
          Filter to apply to objects to be returned. Based on filter query
          language defined by `fl` parameter.

          `None` means that no such filtering is peformed.

      ot (:class:`~pywbem.Uint32`):
          Operation timeout in seconds. This is the minimum time the WBEM server
          must keep the enumeration session open between requests on that
          session.

          A value of 0 indicates that the server should never time out.

          The server may reject the proposed value.

          `None` will cause the server to use its default timeout.

      coe (:class:`py:bool`):
          Continue on error flag.

          `None` will cause the server to use its default of `False`.

      moc (:class:`~pywbem.Uint32`):
          Maximum number of instances the WBEM server may return for each of
          the open and pull requests issued during the iterations over the
          returned generator object.

          Zero and `None` are not allowed.

    Returns:

      :term:`py:generator` iterating :class:`~pywbem.CIMInstance`:
      A generator object that iterates the resulting CIM instances.
      These instances include an instance path that has its host and
      namespace components set.
    """

    return CONN.IterReferenceInstances(ip,
                                       ResultClass=rc,
                                       Role=r,
                                       IncludeQualifiers=iq,
                                       IncludeClassOrigin=ico,
                                       PropertyList=pl,
                                       FilterQueryLanguage=fl,
                                       FilterQuery=fs,
                                       OperationTimeout=ot,
                                       ContinueOnError=coe,
                                       MaxObjectCount=moc)


def irip(ip, rc=None, r=None, fl=None, fs=None, ot=None, coe=None,
         moc=DEFAULT_ITER_MAXOBJECTCOUNT):
    # pylint: disable=too-many-arguments, redefined-outer-name, invalid-name
    """
    *New in pywbem 0.10 as experimental and finalized in 0.12.*

    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.IterReferenceInstancePaths`.

    Retrieve the instance paths of the association instances that reference
    a source instance,
    using the corresponding pull operations if supported by the WBEM server
    or otherwise the corresponding traditional operation, and using the
    Python :term:`py:generator` idiom to return the result.

    This method is an alternative to using the pull operations directly,
    that frees the user of having to know whether the WBEM server supports
    pull operations.

    Parameters:

      ip (:class:`~pywbem.CIMInstanceName`):
          Source instance path.

      rc (:term:`string`):
          ResultClass filter: Include only traversals across this association
          (result) class.

          `None` means this filter is not applied.

      r (:term:`string`):
          Role filter: Include only traversals from this role (= reference
          name) in source object.

          `None` means this filter is not applied.

      fl (:term:`string`):
          Filter query language to be used for the filter defined in the `fs`
          parameter. The DMTF-defined Filter Query Language
          (see :term:`DSP0212`) is specified as "DMTF:FQL".

          `None` means that no such filtering is peformed.

      fs (:term:`string`):
          Filter to apply to objects to be returned. Based on filter query
          language defined by `fl` parameter.

          `None` means that no such filtering is peformed.

      ot (:class:`~pywbem.Uint32`):
          Operation timeout in seconds. This is the minimum time the WBEM server
          must keep the enumeration session open between requests on that
          session.

          A value of 0 indicates that the server should never time out.

          The server may reject the proposed value.

          `None` will cause the server to use its default timeout.

      coe (:class:`py:bool`):
          Continue on error flag.

          `None` will cause the server to use its default of `False`.

      moc (:class:`~pywbem.Uint32`):
          Maximum number of instances the WBEM server may return for each of
          the open and pull requests issued during the iterations over the
          returned generator object.

          Zero and `None` are not allowed.

    Returns:

      :term:`py:generator` iterating :class:`~pywbem.CIMInstanceName`:
      A generator object that iterates the resulting CIM instance paths.
      These instance paths have their host and namespace components set.
    """

    return CONN.IterReferenceInstancePaths(ip,
                                           ResultClass=rc,
                                           Role=r,
                                           FilterQueryLanguage=fl,
                                           FilterQuery=fs,
                                           OperationTimeout=ot,
                                           ContinueOnError=coe,
                                           MaxObjectCount=moc)


def iqi(ql, qs, ns=None, rc=None, ot=None, coe=None,
        moc=DEFAULT_ITER_MAXOBJECTCOUNT,):
    # pylint: disable=line-too-long
    """
    *New in pywbem 0.10 as experimental and finalized in 0.12.*

    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.IterQueryInstances`.

    Execute a query in a namespace,
    using the corresponding pull operations if supported by the WBEM server
    or otherwise the corresponding traditional operation, and using the
    Python :term:`py:generator` idiom to return the result.

    This method is an alternative to using the pull operations directly,
    that frees the user of having to know whether the WBEM server supports
    pull operations.

    Other than the other i...() functions, this function does not return
    a generator object directly, but as a property of the returned object.

    Parameters:

      ql (:term:`string`):
          Name of the query language used in the `qs` parameter, e.g.
          "DMTF:CQL" for CIM Query Language, and "WQL" for WBEM Query
          Language. Because this is not a filter query, "DMTF:FQL" is not a
          valid query language for this request.

      qs (:term:`string`):
          Query string in the query language specified in the `ql` parameter.

      ns (:term:`string`):
          Name of the CIM namespace to be used (case independent).

          If `None`, defaults to the default namespace of the connection.

      rc (:class:`py:bool`):
          Controls whether a class definition describing the properties of the
          returned instances will be returned.

          `None` will cause the server to use its default of `False`.

      ot (:class:`~pywbem.Uint32`):
          Operation timeout in seconds. This is the minimum time the WBEM server
          must keep the enumeration session open between requests on that
          session.

          A value of 0 indicates that the server should never time out.

          The server may reject the proposed value.

          `None` will cause the server to use its default timeout.

      coe (:class:`py:bool`):
          Continue on error flag.

          `None` will cause the server to use its default of `False`.

      moc (:class:`~pywbem.Uint32`):
          Maximum number of instances the WBEM server may return for each of
          the open and pull requests issued during the iterations over the
          returned generator object.

          Zero and `None` are not allowed.

    Returns:

      :class:`~pywbem.IterQueryInstancesReturn`: An object with the
      following properties:

      * **query_result_class** (:class:`~pywbem.CIMClass`):

        The query result class, if requested via the `rc` parameter.

        `None`, if a query result class was not requested.

      * **generator** (:term:`py:generator` iterating :class:`~pywbem.CIMInstance`):

        A generator object that iterates the CIM instances representing the
        query result. These instances do not have an instance path set.
    """  # noqa: E501

    return CONN.IterQueryInstances(FilterQueryLanguage=ql,
                                   FilterQuery=qs,
                                   namespace=ns,
                                   ReturnQueryResultClass=rc,
                                   OperationTimeout=ot,
                                   ContinueOnError=coe,
                                   MaxObjectCount=moc)


def oei(cn, ns=None, lo=None, di=None, iq=None, ico=None, pl=None, fl=None,
        fs=None, ot=None, coe=None, moc=None):
    # pylint: disable=too-many-arguments, redefined-outer-name
    """
    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.OpenEnumerateInstances`.

    Open an enumeration session to enumerate the instances of a class (including
    instances of its subclasses) in a namespace.

    Use the :func:`~wbemcli.piwp` function to retrieve the next set of
    instances or the :func:`~wbcmeli.ce` function to close the enumeration
    session before it is complete.

    Parameters:

      cn (:term:`string` or :class:`~pywbem.CIMClassName`):
          Name of the class to be enumerated (case independent).

          If specified as a `CIMClassName` object, its `host` attribute will be
          ignored.

      ns (:term:`string`):
          Name of the CIM namespace to be used (case independent).

          If `None`, defaults to the namespace of the `cn` parameter if
          specified as a `CIMClassName`, or to the default namespace of the
          connection.

      lo (:class:`py:bool`):
          LocalOnly flag: Exclude inherited properties.

          `None` will cause the server default of `True` to be used.

          Deprecated in :term:`DSP0200`: WBEM server implementations for `True`
          may vary; this parameter should be set to `False` by the caller.

      di (:class:`py:bool`):
          DeepInheritance flag: Include properties added by subclasses.

          `None` will cause the server default of `True` to be used.

      iq (:class:`py:bool`):
          IncludeQualifiers flag: Include qualifiers.

          `None` will cause the server default of `False` to be used.

          Deprecated in :term:`DSP0200`: Clients cannot rely on qualifiers to
          be returned in this operation.

      ico (:class:`py:bool`):
          IncludeClassOrigin flag: Include class origin information for the
          properties in the retrieved instances.

          `None` will cause the server default of `False` to be used.

          Deprecated in :term:`DSP0200`: WBEM servers may either implement this
          parameter as specified, or may treat any specified value as `False`.

      pl (:term:`string` or :term:`py:iterable` of :term:`string`):
          PropertyList: Names of properties to be included (if not otherwise
          excluded). An empty iterable indicates to include no properties.
          If `None`, all properties will be included.

      fl (:term:`string`):
          Filter query language to be used for the filter defined in the `fs`
          parameter. The DMTF-defined Filter Query Language
          (see :term:`DSP0212`) is specified as "DMTF:FQL".

          `None` means that no such filtering is peformed.

      fs (:term:`string`):
          Filter to apply to objects to be returned. Based on filter query
          language defined by `fl` parameter.

          `None` means that no such filtering is peformed.

      ot (:class:`~pywbem.Uint32`):
          Operation timeout in seconds. This is the minimum time the WBEM server
          must keep the enumeration session open between requests on that
          session.

          A value of 0 indicates that the server should never time out.

          The server may reject the proposed value.

          `None` will cause the server to use its default timeout.

      coe (:class:`py:bool`):
          Continue on error flag.

          `None` will cause the server to use its default of `False`.

      moc (:class:`~pywbem.Uint32`):
          Maximum number of objects to return for this operation.

          `None` will cause the server to use its default of 0.

    Returns:

      A :func:`~py:collections.namedtuple` object containing the following
      named items:

        * **instances** (list of :class:`~pywbem.CIMInstance`):
          The retrieved instances.

        * **eos** (:class:`py:bool`):
          `True` if the enumeration session is exhausted after this operation.
          Otherwise `eos` is `False` and the `context` item is the context
          object for the next operation on the enumeration session.

        * **context** (:func:`py:tuple` of server_context, namespace):
          A context object identifying the open enumeration session, including
          its current enumeration state, and the namespace. This object must be
          supplied with the next pull or close operation for this enumeration
          session.
    """

    return CONN.OpenEnumerateInstances(cn, ns,
                                       LocalOnly=lo,
                                       DeepInheritance=di,
                                       IncludeQualifiers=iq,
                                       IncludeClassOrigin=ico,
                                       PropertyList=pl,
                                       FilterQueryLanguage=fl,
                                       FilterQuery=fs,
                                       OperationTimeout=ot,
                                       ContinueOnError=coe,
                                       MaxObjectCount=moc)


def oeip(cn, ns=None, fl=None, fs=None, ot=None, coe=None, moc=None):
    # pylint: disable=too-many-arguments
    """
    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.OpenEnumerateInstancePaths`.

    Open an enumeration session to enumerate the instance paths of instances of
    a class (including instances of its subclasses) in a namespace.

    Use the :func:`~wbemcli.pip` function to retrieve the next set of
    instance paths or the :func:`~wbcmeli.ce` function to close the enumeration
    session before it is complete.

    Parameters:

      cn (:term:`string` or :class:`~pywbem.CIMClassName`):
          Name of the class to be enumerated (case independent).

          If specified as a `CIMClassName` object, its `host` attribute will be
          ignored.

      ns (:term:`string`):
          Name of the CIM namespace to be used (case independent).

          If `None`, defaults to the namespace of the `cn` parameter if
          specified as a `CIMClassName`, or to the default namespace of the
          connection.

      fl (:term:`string`):
          Filter query language to be used for the filter defined in the `fs`
          parameter. The DMTF-defined Filter Query Language
          (see :term:`DSP0212`) is specified as "DMTF:FQL".

          `None` means that no such filtering is peformed.

      fs (:term:`string`):
          Filter to apply to objects to be returned. Based on filter query
          language defined by `fl` parameter.

          `None` means that no such filtering is peformed.

      ot (:class:`~pywbem.Uint32`):
          Operation timeout in seconds. This is the minimum time the WBEM server
          must keep the enumeration session open between requests on that
          session.

          A value of 0 indicates that the server should never time out.

          The server may reject the proposed value.

          `None` will cause the server to use its default timeout.

      coe (:class:`py:bool`):
          Continue on error flag.

          `None` will cause the server to use its default of `False`.

      moc (:class:`~pywbem.Uint32`):
          Maximum number of objects to return for this operation.

          `None` will cause the server to use its default of 0.

    Returns:

      A :func:`~py:collections.namedtuple` object containing the following
      named items:

        * **paths** (list of :class:`~pywbem.CIMInstanceName`):
          The retrieved instance paths.

        * **eos** (:class:`py:bool`):
          `True` if the enumeration session is exhausted after this operation.
          Otherwise `eos` is `False` and the `context` item is the context
          object for the next operation on the enumeration session.

        * **context** (:func:`py:tuple` of server_context, namespace):
          A context object identifying the open enumeration session, including
          its current enumeration state, and the namespace. This object must be
          supplied with the next pull or close operation for this enumeration
          session.
    """

    return CONN.OpenEnumerateInstancePaths(cn, ns,
                                           FilterQueryLanguage=fl,
                                           FilterQuery=fs,
                                           OperationTimeout=ot,
                                           ContinueOnError=coe,
                                           MaxObjectCount=moc)


def oai(ip, ac=None, rc=None, r=None, rr=None, iq=None, ico=None, pl=None,
        fl=None, fs=None, ot=None, coe=None, moc=None):
    # pylint: disable=too-many-arguments,redefined-outer-name, invalid-name
    """
    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.OpenAssociatorInstances`.

    Open an enumeration session to retrieve the instances associated to a
    source instance.

    Use the :func:`~wbemcli.piwp` function to retrieve the next set of
    instances or the :func:`~wbcmeli.ce` function to close the enumeration
    session before it is complete.

    Parameters:

      ip (:class:`~pywbem.CIMInstanceName`):
          Source instance path.

      ac (:term:`string`):
          AssocClass filter: Include only traversals across this association
          class.

          `None` means this filter is not applied.

      rc (:term:`string`):
          ResultClass filter: Include only traversals to this associated
          (result) class.

          `None` means this filter is not applied.

      r (:term:`string`):
          Role filter: Include only traversals from this role (= reference
          name) in source object.

          `None` means this filter is not applied.

      rr (:term:`string`):
          ResultRole filter: Include only traversals to this role (= reference
          name) in associated (=result) objects.

          `None` means this filter is not applied.

      iq (:class:`py:bool`):
          IncludeQualifiers flag: Include qualifiers.

          `None` will cause the server default of `False` to be used.

          Deprecated in :term:`DSP0200`: Clients cannot rely on qualifiers to
          be returned in this operation.

      ico (:class:`py:bool`):
          IncludeClassOrigin flag: Include class origin information for the
          properties in the retrieved instances.

          `None` will cause the server default of `False` to be used.

          Deprecated in :term:`DSP0200`: WBEM servers may either implement this
          parameter as specified, or may treat any specified value as `False`.

      pl (:term:`string` or :term:`py:iterable` of :term:`string`):
          PropertyList: Names of properties to be included (if not otherwise
          excluded). An empty iterable indicates to include no properties.
          If `None`, all properties will be included.

      fl (:term:`string`):
          Filter query language to be used for the filter defined in the `fs`
          parameter. The DMTF-defined Filter Query Language
          (see :term:`DSP0212`) is specified as "DMTF:FQL".

          `None` means that no such filtering is peformed.

      fs (:term:`string`):
          Filter to apply to objects to be returned. Based on filter query
          language defined by `fl` parameter.

          `None` means that no such filtering is peformed.

      ot (:class:`~pywbem.Uint32`):
          Operation timeout in seconds. This is the minimum time the WBEM server
          must keep the enumeration session open between requests on that
          session.

          A value of 0 indicates that the server should never time out.

          The server may reject the proposed value.

          `None` will cause the server to use its default timeout.

      coe (:class:`py:bool`):
          Continue on error flag.

          `None` will cause the server to use its default of `False`.

      moc (:class:`~pywbem.Uint32`):
          Maximum number of objects to return for this operation.

          `None` will cause the server to use its default of 0.

    Returns:

      A :func:`~py:collections.namedtuple` object containing the following
      named items:

        * **instances** (list of :class:`~pywbem.CIMInstance`):
          The retrieved instances.

        * **eos** (:class:`py:bool`):
          `True` if the enumeration session is exhausted after this operation.
          Otherwise `eos` is `False` and the `context` item is the context
          object for the next operation on the enumeration session.

        * **context** (:func:`py:tuple` of server_context, namespace):
          A context object identifying the open enumeration session, including
          its current enumeration state, and the namespace. This object must be
          supplied with the next pull or close operation for this enumeration
          session.
    """

    return CONN.OpenAssociatorInstances(ip,
                                        AssocClass=ac,
                                        ResultClass=rc,
                                        Role=r,
                                        ResultRole=rr,
                                        IncludeQualifiers=iq,
                                        IncludeClassOrigin=ico,
                                        PropertyList=pl,
                                        FilterQueryLanguage=fl,
                                        FilterQuery=fs,
                                        OperationTimeout=ot,
                                        ContinueOnError=coe,
                                        MaxObjectCount=moc)


def oaip(ip, ac=None, rc=None, r=None, rr=None, fl=None, fs=None, ot=None,
         coe=None, moc=None):
    # pylint: disable=too-many-arguments, redefined-outer-name, invalid-name
    """
    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.OpenAssociatorInstancePaths`.

    Open an enumeration session to retrieve the instance paths of the instances
    associated to a source instance.

    Use the :func:`~wbemcli.pip` function to retrieve the next set of
    instance paths or the :func:`~wbcmeli.ce` function to close the enumeration
    session before it is complete.

    Parameters:

      ip (:class:`~pywbem.CIMInstanceName`):
          Source instance path.

      ac (:term:`string`):
          AssocClass filter: Include only traversals across this association
          class.

          `None` means this filter is not applied.

      rc (:term:`string`):
          ResultClass filter: Include only traversals to this associated
          (result) class.

          `None` means this filter is not applied.

      r (:term:`string`):
          Role filter: Include only traversals from this role (= reference
          name) in source object.

          `None` means this filter is not applied.

      rr (:term:`string`):
          ResultRole filter: Include only traversals to this role (= reference
          name) in associated (=result) objects.

          `None` means this filter is not applied.

      fl (:term:`string`):
          Filter query language to be used for the filter defined in the `fs`
          parameter. The DMTF-defined Filter Query Language
          (see :term:`DSP0212`) is specified as "DMTF:FQL".

          `None` means that no such filtering is peformed.

      fs (:term:`string`):
          Filter to apply to objects to be returned. Based on filter query
          language defined by `fl` parameter.

          `None` means that no such filtering is peformed.

      ot (:class:`~pywbem.Uint32`):
          Operation timeout in seconds. This is the minimum time the WBEM server
          must keep the enumeration session open between requests on that
          session.

          A value of 0 indicates that the server should never time out.

          The server may reject the proposed value.

          `None` will cause the server to use its default timeout.

      coe (:class:`py:bool`):
          Continue on error flag.

          `None` will cause the server to use its default of `False`.

      moc (:class:`~pywbem.Uint32`):
          Maximum number of objects to return for this operation.

          `None` will cause the server to use its default of 0.

    Returns:

      A :func:`~py:collections.namedtuple` object containing the following
      named items:

        * **paths** (list of :class:`~pywbem.CIMInstanceName`):
          The retrieved instance paths.

        * **eos** (:class:`py:bool`):
          `True` if the enumeration session is exhausted after this operation.
          Otherwise `eos` is `False` and the `context` item is the context
          object for the next operation on the enumeration session.

        * **context** (:func:`py:tuple` of server_context, namespace):
          A context object identifying the open enumeration session, including
          its current enumeration state, and the namespace. This object must be
          supplied with the next pull or close operation for this enumeration
          session.
    """

    return CONN.OpenAssociatorInstancePaths(ip,
                                            AssocClass=ac,
                                            ResultClass=rc,
                                            Role=r,
                                            ResultRole=rr,
                                            FilterQueryLanguage=fl,
                                            FilterQuery=fs,
                                            OperationTimeout=ot,
                                            ContinueOnError=coe,
                                            MaxObjectCount=moc)


def ori(ip, rc=None, r=None, iq=None, ico=None, pl=None, fl=None, fs=None,
        ot=None, coe=None, moc=None):
    # pylint: disable=too-many-arguments, redefined-outer-name, invalid-name
    """
    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.OpenReferenceInstances`.

    Open an enumeration session to retrieve the association instances that
    reference a source instance.

    Use the :func:`~wbemcli.piwp` function to retrieve the next set of
    instances or the :func:`~wbcmeli.ce` function to close the enumeration
    session before it is complete.

    Parameters:

      ip (:class:`~pywbem.CIMInstanceName`):
          Source instance path.

      rc (:term:`string`):
          ResultClass filter: Include only traversals across this association
          (result) class.

          `None` means this filter is not applied.

      r (:term:`string`):
          Role filter: Include only traversals from this role (= reference
          name) in source object.

          `None` means this filter is not applied.

      iq (:class:`py:bool`):
          IncludeQualifiers flag: Include qualifiers.

          `None` will cause the server default of `False` to be used.

          Deprecated in :term:`DSP0200`: Clients cannot rely on qualifiers to
          be returned in this operation.

      ico (:class:`py:bool`):
          IncludeClassOrigin flag: Include class origin information for the
          properties in the retrieved instances.

          `None` will cause the server default of `False` to be used.

          Deprecated in :term:`DSP0200`: WBEM servers may either implement this
          parameter as specified, or may treat any specified value as `False`.

      pl (:term:`string` or :term:`py:iterable` of :term:`string`):
          PropertyList: Names of properties to be included (if not otherwise
          excluded). An empty iterable indicates to include no properties.
          If `None`, all properties will be included.

      fl (:term:`string`):
          Filter query language to be used for the filter defined in the `fs`
          parameter. The DMTF-defined Filter Query Language
          (see :term:`DSP0212`) is specified as "DMTF:FQL".

          `None` means that no such filtering is peformed.

      fs (:term:`string`):
          Filter to apply to objects to be returned. Based on filter query
          language defined by `fl` parameter.

          `None` means that no such filtering is peformed.

      ot (:class:`~pywbem.Uint32`):
          Operation timeout in seconds. This is the minimum time the WBEM server
          must keep the enumeration session open between requests on that
          session.

          A value of 0 indicates that the server should never time out.

          The server may reject the proposed value.

          `None` will cause the server to use its default timeout.

      coe (:class:`py:bool`):
          Continue on error flag.

          `None` will cause the server to use its default of `False`.

      moc (:class:`~pywbem.Uint32`):
          Maximum number of objects to return for this operation.

          `None` will cause the server to use its default of 0.

    Returns:

      A :func:`~py:collections.namedtuple` object containing the following
      named items:

        * **instances** (list of :class:`~pywbem.CIMInstance`):
          The retrieved instances.

        * **eos** (:class:`py:bool`):
          `True` if the enumeration session is exhausted after this operation.
          Otherwise `eos` is `False` and the `context` item is the context
          object for the next operation on the enumeration session.

        * **context** (:func:`py:tuple` of server_context, namespace):
          A context object identifying the open enumeration session, including
          its current enumeration state, and the namespace. This object must be
          supplied with the next pull or close operation for this enumeration
          session.
    """

    return CONN.OpenReferenceInstances(ip,
                                       ResultClass=rc,
                                       Role=r,
                                       IncludeQualifiers=iq,
                                       IncludeClassOrigin=ico,
                                       PropertyList=pl,
                                       FilterQueryLanguage=fl,
                                       FilterQuery=fs,
                                       OperationTimeout=ot,
                                       ContinueOnError=coe,
                                       MaxObjectCount=moc)


def orip(ip, rc=None, r=None, fl=None, fs=None, ot=None, coe=None, moc=None):
    # pylint: disable=too-many-arguments, redefined-outer-name, invalid-name
    """
    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.OpenReferenceInstancePaths`.

    Open an enumeration session to retrieve the instance paths of the
    association instances that reference a source instance.

    Use the :func:`~wbemcli.pip` function to retrieve the next set of
    instance paths or the :func:`~wbcmeli.ce` function to close the enumeration
    session before it is complete.

    Parameters:

      ip (:class:`~pywbem.CIMInstanceName`):
          Source instance path.

      rc (:term:`string`):
          ResultClass filter: Include only traversals across this association
          (result) class.

          `None` means this filter is not applied.

      r (:term:`string`):
          Role filter: Include only traversals from this role (= reference
          name) in source object.

          `None` means this filter is not applied.

      fl (:term:`string`):
          Filter query language to be used for the filter defined in the `fs`
          parameter. The DMTF-defined Filter Query Language
          (see :term:`DSP0212`) is specified as "DMTF:FQL".

          `None` means that no such filtering is peformed.

      fs (:term:`string`):
          Filter to apply to objects to be returned. Based on filter query
          language defined by `fl` parameter.

          `None` means that no such filtering is peformed.

      ot (:class:`~pywbem.Uint32`):
          Operation timeout in seconds. This is the minimum time the WBEM server
          must keep the enumeration session open between requests on that
          session.

          A value of 0 indicates that the server should never time out.

          The server may reject the proposed value.

          `None` will cause the server to use its default timeout.

      coe (:class:`py:bool`):
          Continue on error flag.

          `None` will cause the server to use its default of `False`.

      moc (:class:`~pywbem.Uint32`):
          Maximum number of objects to return for this operation.

          `None` will cause the server to use its default of 0.

    Returns:

      A :func:`~py:collections.namedtuple` object containing the following
      named items:

        * **paths** (list of :class:`~pywbem.CIMInstanceName`):
          The retrieved instance paths.

        * **eos** (:class:`py:bool`):
          `True` if the enumeration session is exhausted after this operation.
          Otherwise `eos` is `False` and the `context` item is the context
          object for the next operation on the enumeration session.

        * **context** (:func:`py:tuple` of server_context, namespace):
          A context object identifying the open enumeration session, including
          its current enumeration state, and the namespace. This object must be
          supplied with the next pull or close operation for this enumeration
          session.
    """

    return CONN.OpenReferenceInstancePaths(ip,
                                           ResultClass=rc,
                                           Role=r,
                                           FilterQueryLanguage=fl,
                                           FilterQuery=fs,
                                           OperationTimeout=ot,
                                           ContinueOnError=coe,
                                           MaxObjectCount=moc)


def oqi(ql, qs, ns=None, rc=None, ot=None, coe=None, moc=None):
    """
    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.OpenQueryInstances`.

    Open an enumeration session to execute a query in a namespace and to
    retrieve the instances representing the query result.

    Use the :func:`~wbemcli.pi` function to retrieve the next set of
    instances or the :func:`~wbcmeli.ce` function to close the enumeration
    session before it is complete.

    Parameters:

      ql (:term:`string`):
          Filter query language to be used for the filter defined in the `q`
          parameter, e.g. "DMTF:CQL" for CIM Query Language, and "WQL" for WBEM
          Query Language. Because this is not a filter query, "DMTF:FQL" is not
          a valid query language for this request.

      qs (:term:`string`):
          Filter to apply to objects to be returned. Based on filter query
          language defined by the `ql` parameter.

      ns (:term:`string`):
          Name of the CIM namespace to be used (case independent).

          If `None`, defaults to the default namespace of the connection.

      rc (:class:`py:bool`):
          Controls whether a class definition describing the properties of the
          returned instances will be returned.

          `None` will cause the server to use its default of `False`.

      ot (:class:`~pywbem.Uint32`):
          Operation timeout in seconds. This is the minimum time the WBEM server
          must keep the enumeration session open between requests on that
          session.

          A value of 0 indicates that the server should never time out.

          The server may reject the proposed value.

          `None` will cause the server to use its default timeout.

      coe (:class:`py:bool`):
          Continue on error flag.

          `None` will cause the server to use its default of `False`.

      moc (:class:`~pywbem.Uint32`):
          Maximum number of objects to return for this operation.

          `None` will cause the server to use its default of 0.

    Returns:

      A :func:`~py:collections.namedtuple` object containing the following
      named items:

        * **instances** (list of :class:`~pywbem.CIMInstance`):
          The retrieved instances.

        * **eos** (:class:`py:bool`):
          `True` if the enumeration session is exhausted after this operation.
          Otherwise `eos` is `False` and the `context` item is the context
          object for the next operation on the enumeration session.

        * **context** (:func:`py:tuple` of server_context, namespace):
          A context object identifying the open enumeration session, including
          its current enumeration state, and the namespace. This object must be
          supplied with the next pull or close operation for this enumeration
          session.

        * **query_result_class** (:class:`~pywbem.CIMClass`):
          Result class definition describing the properties of the returned
          instances if requested, or otherwise `None`.
    """

    return CONN.OpenQueryInstances(FilterQueryLanguage=ql,
                                   FilterQuery=qs,
                                   namespace=ns,
                                   ReturnQueryResultClass=rc,
                                   OperationTimeout=ot,
                                   ContinueOnError=coe,
                                   MaxObjectCount=moc)


def piwp(ec, moc):    # pylint: disable=redefined-outer-name
    """
    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.PullInstancesWithPath`.

    Retrieve the next set of instances from an open enumeration session. The
    retrieved instances include their instance paths.

    This operation can only be used on enumeration sessions that have been
    opened by one of the following functions:

    * :func:`~wbemcli.oei`
    * :func:`~wbemcli.oai`
    * :func:`~wbemcli.ori`

    Parameters:

      ec (:func:`py:tuple` of server_context, namespace):
          A context object identifying the open enumeration session, including
          its current enumeration state, and the namespace. This object must
          have been returned by the previous open or pull operation for this
          enumeration session.

      moc (:class:`~pywbem.Uint32`):
          Maximum number of objects to return for this operation.

          `None` is not allowed.

    Returns:

      A :func:`~py:collections.namedtuple` object containing the following
      named items:

        * **instances** (list of :class:`~pywbem.CIMInstance`):
          The retrieved instances.

        * **eos** (:class:`py:bool`):
          `True` if the enumeration session is exhausted after this operation.
          Otherwise `eos` is `False` and the `context` item is the context
          object for the next operation on the enumeration session.

        * **context** (:func:`py:tuple` of server_context, namespace):
          A context object identifying the open enumeration session, including
          its current enumeration state, and the namespace. This object must be
          supplied with the next pull or close operation for this enumeration
          session.
    """

    return CONN.PullInstancesWithPath(ec, moc)


def pip(ec, moc):    # pylint: disable=redefined-outer-name
    """
    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.PullInstancePaths`.

    Retrieve the next set of instance paths from an open enumeration session.

    This operation can only be used on enumeration sessions that have been
    opened by one of the following functions:

    * :func:`~wbemcli.oeip`
    * :func:`~wbemcli.oaip`
    * :func:`~wbemcli.orip`

    Parameters:

      ec (:func:`py:tuple` of server_context, namespace):
          A context object identifying the open enumeration session, including
          its current enumeration state, and the namespace. This object must
          have been returned by the previous open or pull operation for this
          enumeration session.

      moc (:class:`~pywbem.Uint32`):
          Maximum number of objects to return for this operation.

          `None` is not allowed.

    Returns:

      A :func:`~py:collections.namedtuple` object containing the following
      named items:

        * **paths** (list of :class:`~pywbem.CIMInstanceName`):
          The retrieved instance paths.

        * **eos** (:class:`py:bool`):
          `True` if the enumeration session is exhausted after this operation.
          Otherwise `eos` is `False` and the `context` item is the context
          object for the next operation on the enumeration session.

        * **context** (:func:`py:tuple` of server_context, namespace):
          A context object identifying the open enumeration session, including
          its current enumeration state, and the namespace. This object must be
          supplied with the next pull or close operation for this enumeration
          session.
    """

    return CONN.PullInstancePaths(ec, moc)


def pi(ec, moc):    # pylint: disable=redefined-outer-name
    """
    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.PullInstances`.

    Retrieve the next set of instances from an open enumeration session. The
    retrieved instances do not include an instance path.

    This operation can only be used on enumeration sessions that have been
    opened by one of the following functions:

    * :func:`~wbemcli.oqi`

    Parameters:

      ec (:func:`py:tuple` of server_context, namespace):
          A context object identifying the open enumeration session, including
          its current enumeration state, and the namespace. This object must
          have been returned by the previous open or pull operation for this
          enumeration session.

      moc (:class:`~pywbem.Uint32`):
          Maximum number of objects to return for this operation.

          `None` is not allowed.

    Returns:

      A :func:`~py:collections.namedtuple` object containing the following
      named items:

        * **instances** (list of :class:`~pywbem.CIMInstance`):
          The retrieved instances.

        * **eos** (:class:`py:bool`):
          `True` if the enumeration session is exhausted after this operation.
          Otherwise `eos` is `False` and the `context` item is the context
          object for the next operation on the enumeration session.

        * **context** (:func:`py:tuple` of server_context, namespace):
          A context object identifying the open enumeration session, including
          its current enumeration state, and the namespace. This object must be
          supplied with the next pull or close operation for this enumeration
          session.
    """

    return CONN.PullInstances(ec, moc)


def ce(ec):    # pylint: disable=redefined-outer-name
    """
    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.CloseEnumeration`.

    Close an open enumeration session, causing an early termination of an
    incomplete enumeration session.

    The enumeration session must still be open when this operation is performed.

    Parameters:

      ec (:func:`py:tuple` of server_context, namespace):
          A context object identifying the open enumeration session, including
          its current enumeration state, and the namespace. This object must
          have been returned by the previous open or pull operation for this
          enumeration session.
    """

    CONN.CloseEnumeration(ec)


def ec(ns=None, cn=None, di=None, lo=None, iq=None, ico=None):
    # pylint: disable=redefined-outer-name
    """
    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.EnumerateClasses`.

    Enumerate the subclasses of a class, or the top-level classes in a
    namespace.

    Parameters:

      ns (:term:`string`):
          Name of the CIM namespace to be used (case independent).

          If `None`, defaults to the namespace of the `cn` parameter if
          specified as a `CIMClassName`, or to the default namespace of the
          connection.

      cn (:term:`string` or :class:`~pywbem.CIMClassName`):
          Name of the class whose subclasses are to be enumerated (case
          independent).

          `None` will enumerate the top-level classes.

          If specified as a `CIMClassName` object, its `host` attribute will be
          ignored.

      di (:class:`py:bool`):
          DeepInheritance flag: Include also indirect subclasses.

          `None` will cause the server default of `False` to be used.

      lo (:class:`py:bool`):
          LocalOnly flag: Exclude inherited properties.

          `None` will cause the server default of `True` to be used.

      iq (:class:`py:bool`):
          IncludeQualifiers flag: Include qualifiers.

          `None` will cause the server default of `True` to be used.

      ico (:class:`py:bool`):
          IncludeClassOrigin flag: Include class origin information for
          properties and methods in the retrieved class.

          `None` will cause the server default of `False` to be used.

    Returns:

      list of :class:`~pywbem.CIMClass`:
          The enumerated classes.
    """

    return CONN.EnumerateClasses(ns,
                                 ClassName=cn,
                                 DeepInheritance=di,
                                 LocalOnly=lo,
                                 IncludeQualifiers=iq,
                                 IncludeClassOrigin=ico)


def ecn(ns=None, cn=None, di=None):
    # pylint: disable=redefined-outer-name
    """
    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.EnumerateClassNames`.

    Enumerate the names of subclasses of a class, or of the top-level classes
    in a namespace.

    Parameters:

      ns (:term:`string`):
          Name of the CIM namespace to be used (case independent).

          If `None`, defaults to the namespace of the `cn` parameter if
          specified as a `CIMClassName`, or to the default namespace of the
          connection.

      cn (:term:`string` or :class:`~pywbem.CIMClassName`):
          Name of the class whose subclasses are to be enumerated (case
          independent).

          `None` will enumerate the top-level classes.

          If specified as a `CIMClassName` object, its `host` attribute will be
          ignored.

      di (:class:`py:bool`):
          DeepInheritance flag: Include also indirect subclasses.

          `None` will cause the server default of `False` to be used.

    Returns:

      list of :term:`unicode string`:
          The enumerated class names.
    """

    return CONN.EnumerateClassNames(ns,
                                    ClassName=cn,
                                    DeepInheritance=di)


def gc(cn, ns=None, lo=None, iq=None, ico=None, pl=None):
    """
    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.GetClass`.

    Retrieve a class.

    Parameters:

      cn (:term:`string` or :class:`~pywbem.CIMClassName`):
          Name of the class to be retrieved (case independent).

          If specified as a `CIMClassName` object, its `host` attribute will be
          ignored.

      ns (:term:`string`):
          Name of the CIM namespace to be used (case independent).

          If `None`, defaults to the namespace of the `cn` parameter if
          specified as a `CIMClassName`, or to the default namespace of the
          connection.

      lo (:class:`py:bool`):
          LocalOnly flag: Exclude inherited properties.

          `None` will cause the server default of `True` to be used.

      iq (:class:`py:bool`):
          IncludeQualifiers flag: Include qualifiers.

          `None` will cause the server default of `True` to be used.

      ico (:class:`py:bool`):
          IncludeClassOrigin flag: Include class origin information for
          properties and methods in the retrieved class.

          `None` will cause the server default of `False` to be used.

      pl (:term:`string` or :term:`py:iterable` of :term:`string`):
          PropertyList: Names of properties to be included (if not otherwise
          excluded). An empty iterable indicates to include no properties.
          If `None`, all properties will be included.

    Returns:

      :class:`~pywbem.CIMClass`:
          The retrieved class.
    """

    return CONN.GetClass(cn, ns,
                         LocalOnly=lo,
                         IncludeQualifiers=iq,
                         IncludeClassOrigin=ico,
                         PropertyList=pl)


def mc(mc, ns=None):    # pylint: disable=redefined-outer-name
    """
    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.ModifyClass`.

    Modify a class.

    Parameters:

      mc (:class:`~pywbem.CIMClass`):
          Modified class.

      ns (:term:`string`):
          Name of the CIM namespace to be used (case independent).

          `None` will use the default namespace of the connection.
    """

    CONN.ModifyClass(mc, ns)


def cc(nc, ns=None):
    """
    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.CreateClass`.

    Create a class in a namespace.

    Parameters:

      nc (:class:`~pywbem.CIMClass`):
          New class.

      ns (:term:`string`):
          Name of the CIM namespace to be used (case independent).

          `None` will use the default namespace of the connection.
    """

    CONN.CreateClass(nc, ns)


def dc(cn, ns=None):
    """
    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.DeleteClass`.

    Delete a class.

    Parameters:

      cn (:term:`string` or :class:`~pywbem.CIMClassName`):
          Name of the class to be deleted (case independent).

          If specified as a `CIMClassName` object, its `host` attribute will be
          ignored.

      ns (:term:`string`):
          Name of the CIM namespace to be used (case independent).

          If `None`, defaults to the namespace of the `cn` parameter if
          specified as a `CIMClassName`, or to the default namespace of the
          connection.
    """

    CONN.DeleteClass(cn, ns)


def eq(ns=None):
    """
    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.EnumerateQualifiers`.

    Enumerate qualifier types (= declarations) in a namespace.

    Parameters:

      ns (:term:`string`):
          Name of the CIM namespace to be used (case independent).

          `None` will use the default namespace of the connection.

    Returns:

      list of :class:`~pywbem.CIMQualifierDeclaration`:
          The enumerated qualifier types.
    """

    return CONN.EnumerateQualifiers(ns)


def gq(qn, ns=None):
    """
    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.GetQualifier`.

    Retrieve a qualifier type (= declaration).

    Parameters:

      qn (:term:`string`):
          Qualifier name (case independent).

      ns (:term:`string`):
          Name of the CIM namespace to be used (case independent).

          `None` will use the default namespace of the connection.

    Returns:

      :class:`~pywbem.CIMQualifierDeclaration`:
          The retrieved qualifier type.
    """

    return CONN.GetQualifier(qn, ns)


def sq(qd, ns=None):
    """
    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.SetQualifier`.

    Create or modify a qualifier type (= declaration) in a namespace.

    Parameters:

      qd (:class:`~pywbem.CIMQualifierDeclaration`):
          Qualifier type.

      ns (:term:`string`):
          Name of the CIM namespace to be used (case independent).

          `None` will use the default namespace of the connection.
    """

    CONN.SetQualifier(qd, ns)


def dq(qn, ns=None):
    """
    This function is a wrapper for
    :meth:`~pywbem.WBEMConnection.DeleteQualifier`.

    Delete a qualifier type (= declaration).

    Parameters:

      qn (:term:`string`):
          Qualifier name (case independent).

      ns (:term:`string`):
          Name of the CIM namespace to be used (case independent).

          `None` will use the default namespace of the connection.
    """

    CONN.DeleteQualifier(qn, ns)


def h():  # pylint: disable=invalid-name
    """Print help text for interactive environment."""

    print(_get_connection_info())
    print("""
Global functions for WBEM operations:

  ei               EnumerateInstances
  ein              EnumerateInstanceNames
  gi               GetInstance
  mi               ModifyInstance
  ci               CreateInstance
  di               DeleteInstance
  a                Associators
  an               AssociatorNames
  r                References
  rn               ReferenceNames
  im               InvokeMethod
  eqy              ExecQuery

  iei              IterEnumerateInstances
  ieip             IterEnumerateInstancePaths
  iai              IterAssociatorInstances
  iaip             IterAssociatorInstancePaths
  iri              IterReferenceInstances
  irip             IterReferenceInstancePaths
  iqi              IterQueryInstances

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

  ec               EnumerateClasses
  ecn              EnumerateClassNames
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


def pdb(stmt):   # pylint: disable=redefined-outer-name
    """Run the statement under the PDB debugger."""
    import pdb   # pylint: disable=redefined-outer-name
    pdb.set_trace()

    # pylint: disable=exec-used
    exec(stmt)  # Type 3 x "s" to get to stmt, and "cont" to end debugger.


conn = WBEMConnection  # pylint: disable=invalid-name


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

    # pylint: disable=protected-access
    info += ' stats=%s, ' % ('on' if CONN._statistics else 'off')

    info += 'log=%s' % ('on' if CONN._operation_recorders else 'off')

    if isinstance(CONN, FakedWBEMConnection):
        info += ', mock-server'

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
    if _sys.platform == 'win32':
        result += '\nEnter Ctrl-Z or quit() or exit() to exit'
    else:
        result += '\nPress Ctrl-D or enter quit() or exit() to exit'
    result += '\nEnter h() for help'

    return result


class _WbemcliCustomFormatter(_SmartFormatter,
                              _argparse.RawDescriptionHelpFormatter):
    """
    Define a custom Formatter to allow formatting help and epilog.

    argparse formatter specifically allows multiple inheritance for the
    formatter customization and actually recommends this in a discussion
    in one of the issues:

        https://bugs.python.org/issue13023

    Also recommended in a StackOverflow discussion:

    https://stackoverflow.com/questions/18462610/argumentparser-epilog-and-description-formatting-in-conjunction-with-argumentdef
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
        add_help=False, formatter_class=_WbemcliCustomFormatter)

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
        '-V', '--version', action='version', version='%(prog)s ' + __version__,
        help='Display pywbem version and exit.')
    general_arggroup.add_argument(
        '--statistics', dest='statistics',
        action='store_true', default=False,
        help='Enable gathering of statistics on operations.')
    general_arggroup.add_argument(
        '--mock-server', dest='mock_server', metavar='file name', nargs='*',
        help='R|Activate pywbem_mock in place of a live WBEMConnection and\n'
             'compile/build the files defined (".mof" suffix or "py" suffix.\n'
             'MOF files are compiled and python files are executed assuming\n'
             'that they include mock_pywbem methods that add objects to the\n'
             'repository.')
    general_arggroup.add_argument(
        '-l', '--log', dest='log', metavar='log_spec[,logspec]',
        action='store', default=None,
        help='R|Log_spec defines characteristics of the various named\n'
             'loggers. It is the form:\n COMP=[DEST[:DETAIL]] where:\n'
             '   COMP:   Logger component name:[{c}].\n'
             '           (Default={cd})\n'
             '   DEST:   Destination for component:[{d}].\n'
             '           (Default={dd})\n'
             '   DETAIL: Detail Level to log: [{dl}] or\n'
             '           an integer that defines the maximum length of\n'
             '           of each log record.\n'
             '           (Default={dll})\n'
             # pylint: disable=bad-continuation
             .format(c='|'.join(LOGGER_SIMPLE_NAMES),
                     cd='all',
                     d='|'.join(LOG_DESTINATIONS),
                     dd=DEFAULT_LOG_DESTINATION,
                     dl='|'.join(LOG_DETAIL_LEVELS),
                     dll=DEFAULT_LOG_DETAIL_LEVEL))

    general_arggroup.add_argument(
        '-h', '--help', action='help',
        help='Show this help message and exit')

    args = argparser.parse_args()

    # setup the global args so it is available to scripts
    global ARGS  # pylint: disable=global-statement
    ARGS = args

    if not args.server and not args.mock_server:
        argparser.error('No WBEM server specified')

    # Set up a client connection
    CONN = _remote_connection(args.server, args, argparser)

    if args.log:
        configure_loggers_from_string(args.log, WBEMCLI_LOG_FILENAME, CONN)

    # Determine file path of history file
    home_dir = '.'
    if 'HOME' in _os.environ:
        home_dir = _os.environ['HOME']  # Linux
    elif 'HOMEPATH' in _os.environ:
        home_dir = _os.environ['HOMEPATH']  # Windows
    histfile = '%s/.wbemcli_history' % home_dir

    # Read previous command line history
    if _HAVE_READLINE:
        # pylint: disable=invalid-name
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
