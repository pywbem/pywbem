"""
PyWBEM management functions related to CIM namespaces.
"""

import os
import sys
import time
from socket import getfqdn

import six

import pywbem

INTEROP_NAMESPACES = [
    'interop',
    'root/interop',
    '/interop',
    '/root/interop',
]

NAMESPACE_CLASSES = [
    'CIM_Namespace',
    '__Namespace',
]

__all__ = ['determine_interop_ns', 'validate_interop_ns', 'get_namespaces']


def determine_interop_ns(conn):
    """
    Determine the name of the Interop namespace of a WBEM server, by
    communicating with it and trying a number of possible Interop namespaces.

    Parameters:

      conn (pywbem.WBEMConnection):
        Connection to the WBEM server.

    Returns:

      A string with the Interop namespace of the WBEM server.

      `None` indicates that none of the namespace names that was attempted, is
      available on the server.

    Raises:

        Exceptions raised by :class:`~pywbem.WBEMConnection`.
    """

    test_classname = 'CIM_Namespace'
    interop_ns = None
    for ns in INTEROP_NAMESPACES:
        try:
            conn.EnumerateInstanceNames(test_classname, namespace=ns)
        except pywbem.CIMError as exc:
            if exc.status_code == CIM_ERR_INVALID_NAMESPACE:
                # Current namespace does not exist.
                continue
            elif exc.status_code in (CIM_ERR_INVALID_CLASS,
                                     CIM_ERR_NOT_FOUND):
                # Class is not implemented, but current namespace does exist.
                interop_ns = ns
                break
            else:
                # Some other error happened.
                raise
        else:
            # Namespace class is implemented in the current namespace.
            interop_ns = ns
            break
    return interop_ns


def validate_interop_ns(conn, interop_ns):
    """
    Validate whether the specified Interop namespace exists in a WBEM server, by
    communicating with it.

    If the namespace exists, this function returns. Otherwise, it raises an
    exception.

    Parameters:

      conn (pywbem.WBEMConnection):
        Connection to the WBEM server.

      interop_ns (:term:`string`):
        Name of the Interop namespace to be validated.

        Must not be `None`.

    Raises:

        pywbem.CIMError: With CIM_ERR_INVALID_NAMESPACE: The specified Interop
          namespace does not exist.

        Other exceptions raised by :class:`~pywbem.WBEMConnection`.
    """
    test_classname = 'CIM_Namespace'
    try:
        conn.EnumerateInstanceNames(test_classname, namespace=interop_ns)
    except pywbem.CIMError as exc:
        # We tolerate it if the WBEM server does not implement this class,
        # as long as it does not return CIM_ERR_INVALID_NAMESPACE.
        if exc.status_code in (CIM_ERR_INVALID_CLASS, CIM_ERR_NOT_FOUND):
            pass
        else:
            raise


def get_namespaces(conn, interop_ns=None):
    """
    Return a list with the names of the CIM namespaces in a WBEM server.

    Parameters:

      conn (pywbem.WBEMConnection):
        Connection to the WBEM server.

      interop_ns (:term:`string`):
        Name of the Interop namespace; used for enumerating the namespaces.

        If `None`, the Interop namespace is automatically determined using
        :func:`determine_interop_ns`.

    Raises:

        pywbem.CIMError: With CIM_ERR_INVALID_NAMESPACE: The specified Interop
          namespace does not exist.

        Other exceptions raised by :class:`~pywbem.WBEMConnection`.
    """
    if interop_ns is None:
        interop_ns = determine_interop_ns(conn)
        if interop_ns is None:
            raise ValueError("Cannot determine Interop namespace")
    ns_insts = None
    for ns_classname in NAMESPACE_CLASSNAMES:
        try:
            ns_insts = conn.EnumerateInstances(ns_classname,
                                               namespace=interop_ns)
        except pywbem.CIMError as exc:
            if exc.status_code in (CIM_ERR_INVALID_CLASS, CIM_ERR_NOT_FOUND):
                # Class is not implemented, try next one.
                continue
            else:
                # Some other error.
                raise
        else:
            # Found a namespace class that is implemented.
            break
    if ns_insts is None:
        raise ValueError("None of the possible namespace classes is "
                         "implemented")
    return [inst['Name'] for inst in ns_insts]

