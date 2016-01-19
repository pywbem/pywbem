#!/usr/bin/env python
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

import os
import sys
import getpass
import errno
import code
import optparse

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

_CONN = None

def remote_connection(argv, opts):
    """Initiate a remote connection, via PyWBEM."""

    global _CONN     # pylint: disable=global-statement

    if argv[0][0] == '/':
        url = argv[0]
    else:
        proto = 'https'

        if opts.no_ssl:
            proto = 'http'

        url = '%s://%s' % (proto, argv[0])

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

def EnumerateInstanceNames(classname, namespace=None):
    """Enumerate the names of the instances of a CIM Class (including the
    names of any subclasses) in the target namespace."""

    global _CONN     # pylint: disable=global-statement

    return _CONN.EnumerateInstanceNames(classname, namespace=namespace)

def EnumerateInstances(classname, namespace=None, LocalOnly=True,
                       DeepInheritance=True, IncludeQualifiers=False,
                       IncludeClassOrigin=False):
    """Enumerate instances of a CIM Class (includeing the instances of
    any subclasses in the target namespace."""

    global _CONN     # pylint: disable=global-statement

    return _CONN.EnumerateInstances(classname,
                                    namespace=namespace,
                                    DeepInheritance=DeepInheritance,
                                    IncludeQualifiers=IncludeQualifiers,
                                    IncludeClassOrigin=IncludeClassOrigin)


def GetInstance(instancename, LocalOnly=True, IncludeQualifiers=False,
                IncludeClassOrigin=False):
    """Return a single CIM instance corresponding to the instance name
    given."""

    global _CONN     # pylint: disable=global-statement

    return _CONN.GetInstance(instancename,
                             LocalOnly=LocalOnly,
                             IncludeQualifiers=IncludeQualifiers,
                             IncludeClassOrigin=IncludeClassOrigin)

def DeleteInstance(instancename):
    """Delete a single CIM instance."""

    global _CONN     # pylint: disable=global-statement

    return _CONN.DeleteInstance(instancename)

def ModifyInstance(*args, **kwargs):
    global _CONN     # pylint: disable=global-statement
    return _CONN.ModifyInstance(*args, **kwargs)

def CreateInstance(*args, **kwargs):
    global _CONN     # pylint: disable=global-statement
    return _CONN.CreateInstance(*args, **kwargs)

def InvokeMethod(*args, **kwargs):
    global _CONN     # pylint: disable=global-statement
    return _CONN.InvokeMethod(*args, **kwargs)

def AssociatorNames(*args, **kwargs):
    global _CONN     # pylint: disable=global-statement
    return _CONN.AssociatorNames(*args, **kwargs)

def Associators(*args, **kwargs):
    global _CONN     # pylint: disable=global-statement
    return _CONN.Associators(*args, **kwargs)

def ReferenceNames(*args, **kwargs):
    global _CONN     # pylint: disable=global-statement
    return _CONN.ReferenceNames(*args, **kwargs)

def References(*args, **kwargs):
    global _CONN     # pylint: disable=global-statement
    return _CONN.References(*args, **kwargs)

def EnumerateClassNames(*args, **kwargs):
    global _CONN     # pylint: disable=global-statement
    return _CONN.EnumerateClassNames(*args, **kwargs)

def EnumerateClasses(*args, **kwargs):
    global _CONN     # pylint: disable=global-statement
    return _CONN.EnumerateClasses(*args, **kwargs)

def GetClass(*args, **kwargs):
    global _CONN     # pylint: disable=global-statement
    return _CONN.GetClass(*args, **kwargs)

def DeleteClass(*args, **kwargs):
    global _CONN     # pylint: disable=global-statement
    return _CONN.DeleteClass(*args, **kwargs)

def ModifyClass(*args, **kwargs):
    global _CONN     # pylint: disable=global-statement
    return _CONN.ModifyClass(*args, **kwargs)

def CreateClass(*args, **kwargs):
    global _CONN     # pylint: disable=global-statement
    return _CONN.CreateClass(*args, **kwargs)

def EnumerateQualifiers(*args, **kwargs):
    global _CONN     # pylint: disable=global-statement
    return _CONN.EnumerateQualifiers(*args, **kwargs)

def GetQualifier(*args, **kwargs):
    global _CONN     # pylint: disable=global-statement
    return _CONN.GetQualifier(*args, **kwargs)

def SetQualifier(*args, **kwargs):
    global _CONN     # pylint: disable=global-statement
    return _CONN.SetQualifier(*args, **kwargs)

def DeleteQualifier(*args, **kwargs):
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

    global _CONN     # pylint: disable=global-statement

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


def main():
    """Main routine, when called as a script."""

    global _CONN     # pylint: disable=global-statement

    # Parse command line args
    optparser = optparse.OptionParser(
        usage='%prog HOSTNAME [-u USER -p PASS] [-n NAMESPACE] [--no-ssl]')

    # Username and password
    optparser.add_option('-u', '--user', dest='user',
                         action='store', type='string',
                         help='user to connect as')
    optparser.add_option('-p', '--password', dest='password',
                         action='store', type='string',
                         help='password to connect user as')

    # Change the default namespace used
    optparser.add_option('-n', '--namespace', dest='namespace',
                         action='store', type='string', default='root/cimv2',
                         help='default namespace to use')

    # Don't use SSL for remote connections
    optparser.add_option('--no-ssl', dest='no_ssl', action='store_true',
                         help='don\'t use SSL')

    # Specify non-standard port
    optparser.add_option('--port', dest='port', action='store', type='int',
                         help='port to connect as', default=None)

    # Check usage
    (opts, argv) = optparser.parse_args()

    if len(argv) != 1:
        optparser.print_usage()
        sys.exit(1)

    # Set up a client connection
    _CONN = remote_connection(argv, opts)

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

if __name__ == '__main__':
    exit(main())
