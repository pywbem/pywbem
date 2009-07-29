#!/usr/bin/python

# (C) Copyright 2008 Hewlett-Packard Development Company, L.P.

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; version 2 of the License.
   
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
   
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

# Author: Tim Potter <tpot@hp.com>

#
# A small utility to wrap up a PyWBEM session in a Python interactive
# console.
#
# Usage: 
#
#   wbemcli.py HOSTNAME [-u USERNAME -p PASSWORD] [-n namespace] [--no-ssl] \
#       [--port PORT]
#
# CIM operations can be executed by using the PyWBEM connection object
# called 'cli' in the global scope.  There are two sets of aliases
# available for usage in the interpreter. For example the following
# three commands are equivalent:
#
#   >>> cli.EnumerateInstanceNames('SMX_ComputerSystem')
#   >>> EnumerateInstanceNames('SMX_ComputerSystem')
#   >>> ein('SMX_ComputerSystem')
#
# Pretty-printing of results is also available using the 'pp'
# function. For example:
#
#   >>> cs = ei('SMX_ComputerSystem')[0]
#   >>> pp(cs.items())
#   [(u'RequestedState', 12L),
#    (u'Dedicated', [1L]),
#    (u'StatusDescriptions', [u'System is Functional']),
#    (u'IdentifyingNumber', u'6F880AA1-F4F5-11D5-8C45-C0116FBAE02A'),
#   ...
#

import os, stat, sys, string, getpass, errno
from pywbem import *
from code import InteractiveConsole
from optparse import OptionParser
from pprint import pprint as pp

# Conditional support of readline module

have_readline = False

try:
    import readline
    have_readline = True
except ImportError, arg:
    pass

#
# Parse command line args
#

optparser = OptionParser(
    usage = '%prog HOSTNAME [-u USER -p PASS] [-n NAMESPACE] [--no-ssl]')

# Username and password

optparser.add_option('-u', '--user', dest = 'user',
                     action = 'store', type = 'string',
                     help = 'user to connect as')

optparser.add_option('-p', '--password', dest = 'password',
                     action = 'store', type = 'string',
                     help = 'password to connect user as')

# Change the default namespace used

optparser.add_option('-n', '--namespace', dest = 'namespace',
                     action = 'store', type = 'string', default = 'root/cimv2',
                     help = 'default namespace to use')

# Don't use SSL for remote connections

optparser.add_option('--no-ssl', dest = 'no_ssl', action = 'store_true',
                     help = 'don\'t use SSL')

# Specify non-standard port

optparser.add_option('--port', dest = 'port', action = 'store', type = 'int',
                     help = 'port to connect as', default = None)

# Check usage

(opts, argv) = optparser.parse_args()

if len(argv) != 1:
    optparser.print_usage()
    sys.exit(1)

#
# Set up a client connection
#

def remote_connection():
    """Initiate a remote connection, via PyWBEM."""

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

    cli = WBEMConnection(url, creds, default_namespace = opts.namespace)

    cli.debug = True

    return cli

cli = remote_connection()

#
# Create some convenient global functions to reduce typing
#

def EnumerateInstanceNames(classname, namespace = None):
    """Enumerate the names of the instances of a CIM Class (including the
    names of any subclasses) in the target namespace."""

    return cli.EnumerateInstanceNames(classname, namespace = namespace)

def EnumerateInstances(classname, namespace = None, LocalOnly = True,
                       DeepInheritance = True, IncludeQualifiers = False,
                       IncludeClassOrigin = False):
    """Enumerate instances of a CIM Class (includeing the instances of
    any subclasses in the target namespace."""

    return cli.EnumerateInstances(classname, 
                                  namespace = namespace,
                                  DeepInheritance = DeepInheritance,
                                  IncludeQualifiers = IncludeQualifiers,
                                  IncludeClassOrigin = IncludeClassOrigin)


def GetInstance(instancename, LocalOnly = True, IncludeQualifiers = False,
                IncludeClassOrigin = False):
    """Return a single CIM instance corresponding to the instance name
    given."""

    return cli.GetInstance(instancename, 
                           LocalOnly = LocalOnly, 
                           IncludeQualifiers = IncludeQualifiers,
                           IncludeClassOrigin = IncludeClassOrigin)

def DeleteInstance(instancename):
    """Delete a single CIM instance."""

    return cli.DeleteInstance(instancename)

def ModifyInstance(*args, **kwargs):
    return cli.ModifyInstance(*args, **kwargs)

def CreateInstance(*args, **kwargs):
    return cli.CreateInstance(*args, **kwargs)

def InvokeMethod(*args, **kwargs):
    return cli.InvokeMethod(*args, **kwargs)

def AssociatorNames(*args, **kwargs):
    return cli.AssociatorNames(*args, **kwargs)

def Associators(*args, **kwargs):
    return cli.Associators(*args, **kwargs)

def ReferenceNames(*args, **kwargs):
    return cli.ReferenceNames(*args, **kwargs)

def References(*args, **kwargs):
    return cli.References(*args, **kwargs)

def EnumerateClassNames(*args, **kwargs):
    return cli.EnumerateClassNames(*args, **kwargs)

def EnumerateClasses(*args, **kwargs):
    return cli.EnumerateClasses(*args, **kwargs)

def GetClass(*args, **kwargs):
    return cli.GetClass(*args, **kwargs)

def DeleteClass(*args, **kwargs):
    return cli.DeleteClass(*args, **kwargs)

def ModifyClass(*args, **kwargs):
    return cli.ModifyClass(*args, **kwargs)

def CreateClass(*args, **kwargs):
    return cli.CreateClass(*args, **kwargs)

def EnumerateQualifiers(*args, **kwargs):
    return cli.EnumerateQualifiers(*args, **kwargs)

def GetQualifier(*args, **kwargs):
    return cli.GetQualifier(*args, **kwargs)

def SetQualifier(*args, **kwargs):
    return cli.SetQualifier(*args, **kwargs)

def DeleteQualifier(*args, **kwargs):
    return cli.DeleteQualifier(*args, **kwargs)

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

#
# Enter interactive console
#

def get_banner():
    
    result = ''

    # Note how we are connected

    result += 'Connected to %s' % cli.url
    if cli.creds is not None:
        result += ' as %s' % cli.creds[0]

    return result
        
# Read previous command line history

histfile = '%s/.wbemcli_history' % os.environ['HOME']

try:
    if have_readline:
        readline.read_history_file(histfile)
except IOError, arg:
    if arg[0] != errno.ENOENT:
        raise

# Interact

i = InteractiveConsole(globals())
i.interact(get_banner())

# Save command line history

if have_readline:
    readline.write_history_file(histfile)
