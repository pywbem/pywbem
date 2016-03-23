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

"""A small utility to wrap up a PyWBEM session in a Python interactive
console.

Usage:
  wbemcli.py HOSTNAME [-u USERNAME -p PASSWORD] [-n namespace] [--no-ssl] \
      [--port PORT]

The utility creates a ``pywbem.WBEMConnection`` object for the specified
WBEM server location. Subsequent operatoins then use that connection.

There are two sets of aliases available for usage in the interpreter. For
example, the following two commands are equivalent:

  >>> EnumerateInstanceNames('SMX_ComputerSystem')
  >>> ein('SMX_ComputerSystem')

Pretty-printing of results is also available using the 'pp'
function. For example:

  >>> cs = ei('SMX_ComputerSystem')[0]
  >>> pp(cs.items())
  [(u'RequestedState', 12L),
   (u'Dedicated', [1L]),
   (u'StatusDescriptions', [u'System is Functional']),
   (u'IdentifyingNumber', u'6F880AA1-F4F5-11D5-8C45-C0116FBAE02A'),
  ...
"""

from __future__ import absolute_import

import os
import getpass
import errno
import code
import argparse

# Additional symbols for use in the interactive session
from pprint import pprint as pp # pylint: disable=unused-import

# Conditional support of readline module
try:
    import readline
    _HAVE_READLINE = True
except ImportError as arg:
    _HAVE_READLINE = False

import pywbem

__all__ = []

# Connection global variable. Set by remote_connection and use
# by all functions that execute operations.
_CONN = None

def remote_connection(server, opts):
    """Initiate a remote connection, via PyWBEM. Arguments for
       the request are part of the command line arguments and include
       user name, password, namespace, etc.
    """

    global _CONN     # pylint: disable=global-statement

    if server[0] == '/':
        url = server
    else:
        proto = 'https'

        if opts.no_ssl:
            proto = 'http'

        url = '%s://%s' % (proto, server)

        if opts.port is not None:
            url += ':%d' % opts.port

    creds = None

    if opts.user is not None and opts.password is None:
        opts.password = getpass.getpass('Enter password for %s: ' % opts.user)

    if opts.user is not None or opts.password is not None:
        creds = (opts.user, opts.password)

    _CONN = pywbem.WBEMConnection(url, creds, default_namespace=opts.namespace)

    _CONN.debug = True

    return _CONN

#
# Create some convenient global functions to reduce typing
#
# The following pylint disable is because many of the functions
# in this file use CamelCase specifically to maintain equivalence to
# the client functions in other languages. Do not change these names.
# pylint: disable=invalid-name
def EnumerateInstanceNames(classname, namespace=None):
    """Enumerate the names of the instances of a CIM Class (including the
    names of any subclasses) in the target namespace."""

    # pylint: disable=global-variable-not-assigned
    global _CONN     # pylint: disable=global-statement

    return _CONN.EnumerateInstanceNames(classname, namespace=namespace)

# pylint: disable=too-many-arguments
def EnumerateInstances(classname, namespace=None, LocalOnly=True,
                       DeepInheritance=True, IncludeQualifiers=False,
                       IncludeClassOrigin=False):
    """Enumerate instances of a CIM Class (includeing the instances of
    any subclasses in the target namespace."""

    # pylint: disable=global-variable-not-assigned
    global _CONN     # pylint: disable=global-statement

    return _CONN.EnumerateInstances(classname,
                                    namespace=namespace,
                                    LocalOnly=LocalOnly,
                                    DeepInheritance=DeepInheritance,
                                    IncludeQualifiers=IncludeQualifiers,
                                    IncludeClassOrigin=IncludeClassOrigin)


def GetInstance(instancename, LocalOnly=True, IncludeQualifiers=False,
                IncludeClassOrigin=False):
    """Return a single CIM instance corresponding to the instance name
    given.

    :param instancename: ObjectPath defining the instance.
    :param LocalOnly: Optional argument defining whether the
       only the properties defined in this instance are returned.
       Default= true. DEPRECATED
    :param IncludeQualifier: Optional argument defining whether
        qualifiers are included. Default false. DEPRECATED
    :param IncludeClassOrigin: Optional argument defining wheteher
        class origin information is cinclude in the response. Default
        is False.
    :return: Dictionary containing the retrieved instance
    :raises:
    """
    # pylint: disable=global-variable-not-assigned
    global _CONN     # pylint: disable=global-statement

    return _CONN.GetInstance(instancename,
                             LocalOnly=LocalOnly,
                             IncludeQualifiers=IncludeQualifiers,
                             IncludeClassOrigin=IncludeClassOrigin)

def DeleteInstance(instancename):
    """Delete a single CIM instance.

       :param instancename: CIMObjectPath defining the instance
       :return:
    """

    # pylint: disable=global-variable-not-assigned
    global _CONN     # pylint: disable=global-statement

    return _CONN.DeleteInstance(instancename)

# TODO KS: All of the following functions simply use args and kwargs. This
#          makes sorting out arguments difficult for the user.

def ModifyInstance(*args, **kwargs):
    """Modify an existing instance"""

    # pylint: disable=global-variable-not-assigned
    global _CONN     # pylint: disable=global-statement
    return _CONN.ModifyInstance(*args, **kwargs)

def CreateInstance(*args, **kwargs):
    """Create a new instance for an existing class"""

    # pylint: disable=global-variable-not-assigned
    global _CONN     # pylint: disable=global-statement
    return _CONN.CreateInstance(*args, **kwargs)

def InvokeMethod(*args, **kwargs):
    """Invoke a method"""

    # pylint: disable=global-variable-not-assigned
    global _CONN     # pylint: disable=global-statement
    return _CONN.InvokeMethod(*args, **kwargs)

def AssociatorNames(*args, **kwargs):
    """Return associator names for the source class or instance"""
    # pylint: disable=global-variable-not-assigned
    global _CONN     # pylint: disable=global-statement
    return _CONN.AssociatorNames(*args, **kwargs)

def Associators(*args, **kwargs):
    """Return associators for the source class or instance"""

    # pylint: disable=global-variable-not-assigned
    global _CONN     # pylint: disable=global-statement
    return _CONN.Associators(*args, **kwargs)

def ReferenceNames(*args, **kwargs):
    """Return the refernence names for the target class or instance"""

    # pylint: disable=global-variable-not-assigned
    global _CONN     # pylint: disable=global-statement
    return _CONN.ReferenceNames(*args, **kwargs)

def References(*args, **kwargs):
    """Return the instances or classes for the target instance or class"""

    # pylint: disable=global-variable-not-assigned
    global _CONN     # pylint: disable=global-statement
    return _CONN.References(*args, **kwargs)

def EnumerateClassNames(*args, **kwargs):
    "Enumerate the class names in the namespace"""

    # pylint: disable=global-variable-not-assigned
    global _CONN     # pylint: disable=global-statement
    return _CONN.EnumerateClassNames(*args, **kwargs)

def EnumerateClasses(*args, **kwargs):
    """Enumerate the classes defined by the input arguments"""

    # pylint: disable=global-variable-not-assigned
    global _CONN     # pylint: disable=global-statement
    return _CONN.EnumerateClasses(*args, **kwargs)

def GetClass(*args, **kwargs):
    """ Get the class defined by the inputs"""

    # pylint: disable=global-variable-not-assigned
    global _CONN     # pylint: disable=global-statement
    return _CONN.GetClass(*args, **kwargs)

def DeleteClass(*args, **kwargs):
    """Delete the class defined by the input. """

    # pylint: disable=global-variable-not-assigned
    global _CONN     # pylint: disable=global-statement
    return _CONN.DeleteClass(*args, **kwargs)

def ModifyClass(*args, **kwargs):
    """Modify the class defined by the input arguments"""

    # pylint: disable=global-variable-not-assigned
    global _CONN     # pylint: disable=global-statement
    return _CONN.ModifyClass(*args, **kwargs)

def CreateClass(*args, **kwargs):
    """Create a class from the input arguments"""

    # pylint: disable=global-variable-not-assigned
    global _CONN     # pylint: disable=global-statement
    return _CONN.CreateClass(*args, **kwargs)

def EnumerateQualifiers(*args, **kwargs):
    """Return the qualifier types that exist in the defined namespace"""
    # pylint: disable=global-variable-not-assigned
    global _CONN     # pylint: disable=global-statement
    return _CONN.EnumerateQualifiers(*args, **kwargs)

def GetQualifier(*args, **kwargs):
    """Return the qualifier type defined by the input argument"""

    # pylint: disable=global-variable-not-assigned
    global _CONN     # pylint: disable=global-statement
    return _CONN.GetQualifier(*args, **kwargs)

def SetQualifier(*args, **kwargs):
    """Create a new qualifier type from the input arguments"""

    # pylint: disable=global-variable-not-assigned
    global _CONN     # pylint: disable=global-statement
    return _CONN.SetQualifier(*args, **kwargs)

def DeleteQualifier(*args, **kwargs):
    """Delete a qualifier type"""

    # pylint: disable=global-variable-not-assigned
    global _CONN     # pylint: disable=global-statement
    return _CONN.DeleteQualifier(*args, **kwargs)

# Aliases for global functions above


ein = EnumerateInstanceNames
ei = EnumerateInstances
gi = GetInstance
di = DeleteInstance
mi = ModifyInstance
ci = CreateInstance

im = InvokeMethod

an = AssociatorNames
ao = Associators
rn = ReferenceNames
re = References

ecn = EnumerateClassNames
ec = EnumerateClasses
gc = GetClass
dc = DeleteClass
mc = ModifyClass
cc = CreateClass

eq = EnumerateQualifiers
gq = GetQualifier
sq = SetQualifier
dq = DeleteQualifier


def get_banner():
    """Return a banner message for the interactive console."""

    global _CONN     # pylint: disable=global-statement,global-variable-not-assigned

    result = ''

    # Note how we are connected
    result += 'Connected to %s' % _CONN.url
    if _CONN.creds is not None:
        result += ' as %s' % _CONN.creds[0]

    # Give hint about exiting. Most people exit with 'quit()' which will
    # not return from the interact() method, and thus will not write
    # the history.
    result += '\nPress Ctrl-D to exit'

    return result


class SmartFormatter(argparse.HelpFormatter):
    """Formatter class for `argparse`, that respects newlines in help strings.

    Idea and code from: http://stackoverflow.com/a/22157136

    Usage:

        If an argparse argument help text starts with 'R|', it will be treated
        as a *raw* string that does line formatting on its own by specifying
        newlines appropriately. The string should not exceed 55 characters per
        line. Indentation handling is still applied automatically and does not
        need to be specified within the string.

        Otherwise, the strings are formatted as normal and newlines are
        treated like blanks.

    Limitations:
        It seems this only works for the `help` argument of
        `ArgumentParser.add_argument()`, and not for group descriptions,
        and usage, description, and epilog of ArgumentParser.
"""

    def _split_lines(self, text, width):
        if text.startswith('R|'):
            return text[2:].splitlines()
        return argparse.HelpFormatter._split_lines(self, text, width)


def main():
    """Parse command line arguments, connect to the WBEM server and
    open the interactive shell.
    A help message is printed with `-h` or `--help`.
    """

    global _CONN     # pylint: disable=global-statement

    prog = "wbemcli"  # Name of the script file invoking this module
    usage = '%(prog)s [options] server'
    desc = 'Provide an interactive shell for issuing operations against a ' \
           'WBEM server.'
    epilog = """
Example:
  %s localhost --port 15989 -n root/cimv2 -u sheldon -p penny42
""" % prog
    argparser = argparse.ArgumentParser(
        prog=prog, usage=usage, description=desc, epilog=epilog,
        add_help=False, formatter_class=SmartFormatter)

    pos_arggroup = argparser.add_argument_group(
        'Positional arguments')
    pos_arggroup.add_argument(
        'server', metavar='server', nargs='?',
        help='Host name or IP address of the WBEM server.')

    server_arggroup = argparser.add_argument_group(
        'Server related options',
        'Specify the WBEM server and namespace')
    server_arggroup.add_argument(
        '--port', dest='port', metavar='port', type=int,
        default=None,
        help='Port where the WBEM server listens')
    server_arggroup.add_argument(
        '--no-ssl', dest='no_ssl',
        action='store_true',
        help='Don\'t use SSL')
    server_arggroup.add_argument(
        '-n', '--namespace', dest='namespace', metavar='namespace',
        default='root/cimv2',
        help='R|Namespace in the WBEM server to work against.\n' \
             'Default: %(default)s')
    server_arggroup.add_argument(
        '-u', '--user', dest='user', metavar='user',
        help='R|Username for authenticating with the WBEM server.\n' \
             'Default: No username')
    server_arggroup.add_argument(
        '-p', '--password', dest='password', metavar='password',
        help='R|Password for authenticating with the WBEM server.\n' \
             'Default: Will be prompted for, if username was specified.')

    general_arggroup = argparser.add_argument_group(
        'General options')
    general_arggroup.add_argument(
       '-v', '--verbose', dest='verbose',
       action='store_true', default=False,
       help='Print more messages while processing')
    general_arggroup.add_argument(
       '-h', '--help', action='help',
       help='Show this help message and exit')

    args = argparser.parse_args()

    if not args.server:
        argparser.error('No WBEM server specified')

    # Set up a client connection
    _CONN = remote_connection(args.server, args)

    # Determine file path of history file
    home_dir = '.'
    if 'HOME' in os.environ:
        home_dir = os.environ['HOME'] # Linux
    elif 'HOMEPATH' in os.environ:
        home_dir = os.environ['HOMEPATH'] # Windows
    histfile = '%s/.wbemcli_history' % home_dir

    # Read previous command line history
    if _HAVE_READLINE:
        try:
            readline.read_history_file(histfile)
        except IOError as arg:
            if arg[0] != errno.ENOENT:
                raise

    # Interact
    i = code.InteractiveConsole(globals())
    i.interact(get_banner())

    # Save command line history
    if _HAVE_READLINE:
        readline.write_history_file(histfile)

    return 0

