#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Example of the EnumerateInstances operation. The execution
   arguments may be either internal defaults if less than the full set of
   arguments is supplied on the command line or the supplied command
   line arguments.

   The command line arguments are:
       - server_url: scheme, server name, (optional) port
       - username
       - password
       - namespace
       - classname

   This simple example allows both http and https
   requests but does not allow verification of server cert or
   mutual authentication

   This example demonstrates executing the connection,
   operation request, displaying results and handling exceptions.
"""

from __future__ import print_function
import sys
from pywbem import WBEMConnection, Error, CIMError

# default connection attributes. Used if not all arguments are
# supplied on the command line.
USERNAME = 'blah'
PASSWORD = 'blah'
TEST_CLASS = 'CIM_ComputerSystem'
TEST_NAMESPACE = 'root/cimv2'
SERVER_URL = 'http://localhost'

def execute_request(server_url, creds, namespace, classname):
    """ Open a connection with the server_url and creds, and
        enumerate instances defined by the functions namespace and
        classname arguments.
        Displays either the error return or the mof for instances
        returned.
    """

    print('Requesting url=%s, ns=%s, class=%s' % \
        (server_url, namespace, classname))

    try:
        # Create a connection
        CONN = WBEMConnection(server_url, creds,
                              default_namespace=namespace,
                              no_verification=True)

        #Issue the request to EnumerateInstances on the defined class
        INSTANCES = CONN.EnumerateInstances(classname)

        #Display of characteristics of the result object
        print('instances type=%s len=%s' % (type(INSTANCES),
                                            len(INSTANCES)))
        #display the mof output
        for inst in INSTANCES:
            print('path=%s\n' % inst.path)
            print(inst.tomof())

    # handle any exception
    except Error as err:
        # If CIMError, display CIMError attributes
        if isinstance(err, CIMError):
            print('Operation Failed: CIMError: code=%s, Description=%s' % \
                  (err.status_code_name, err.status_description))
        else:
            print ("Operation failed: %s" % err)
        sys.exit(1)

def main():
    """ Get arguments and call the execution function"""

    if len(sys.argv) < 6:
        print("Usage: %s server_url username password namespace' \
              ' classname" %  sys.argv[0])
        print('Using internal defaults')
        server_url = SERVER_URL
        namespace = TEST_NAMESPACE
        username = USERNAME
        password = PASSWORD
        classname = TEST_CLASS
    else:
        print('Get from input')
        server_url = sys.argv[1]
        namespace = sys.argv[2]
        username = sys.argv[3]
        password = sys.argv[4]
        classname = sys.argv[5]

    # create the credentials tuple for WBEMConnection
    creds = (username, password)

    # call the method to execute the request and display results
    execute_request(server_url, creds, namespace, classname)

    return 0

if __name__ == '__main__':
    sys.exit(main())


