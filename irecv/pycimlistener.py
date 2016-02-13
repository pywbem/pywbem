#!/usr/bin/python
#
# Simple indication receiver using Twisted Python.  HTTP post requests
# are listened for on port 5988 and port 5899 using SSL.
#
# Requires Twisted Python and
#

import sys
import optparse
import pywbem
from twisted.internet import reactor
from twisted.web import server, resource

global conn
conn=None

class WBEMConn:
    _shared_state = {}
    conn = None

    def __init__(self, options=None):
        # Borgness
        self.__dict__ = WBEMConn._shared_state
        self.conn = pywbem.SFCBUDSConnection()
        '''
        if options:
            proto = 'http'
            if options.secure:
                proto = 'https'
            url = '%s://%s' % (proto, options.host)
            self.conn = pywbem.WBEMConnection(
                    url,
                    (options.user, options.password),
                    default_namespace = options.namespace)
        '''
        global conn
        conn = self.conn



class CIMOM(resource.Resource):

    isLeaf = 1

    def render_POST(self, request):

        for line in request.content.readlines():
            print(line)

        return ''

from OpenSSL import SSL

class ServerContextFactory:
    def getContext(self):
        """Create an SSL context with a dodgy certificate."""
        ctx = SSL.Context(SSL.SSLv23_METHOD)
        ctx.use_certificate_file('server.pem')
        ctx.use_privatekey_file('server.pem')
        return ctx

from twisted.internet import ssl, reactor
from twisted.python import log
from socket import getfqdn
import time

def _createFilter(query,
                  ns,
                  querylang='WQL',
                  src_ns='root/cimv2',
                  in_name=None):
    name = in_name or 'cimfilter%s'%time.time()
    filterinst=pywbem.CIMInstance('CIM_IndicationFilter')
    filterinst['CreationClassName']='CIM_IndicationFilter'
    filterinst['SystemCreationClassName']='CIM_ComputerSystem'
    filterinst['SystemName']=getfqdn()
    filterinst['Name']=name
    filterinst['Query']=query
    filterinst['QueryLanguage']=querylang
    filterinst['SourceNamespace']=src_ns
    cop = pywbem.CIMInstanceName('CIM_IndicationFilter')
    cop.keybindings = { 'CreationClassName':'CIM_IndicationFilter',
                        'SystemClassName':'CIM_ComputerSystem',
                        'SystemName':getfqdn(),
                        'Name':name }
    cop.namespace=ns
    filterinst.path = cop
    filtercop = conn.CreateInstance(filterinst)
    return filtercop

def _createDest(destination,
                ns,
                in_name=None):
    name = in_name or 'cimlistener%s'%time.time()
    destinst=pywbem.CIMInstance('CIM_ListenerDestinationCIMXML')
    destinst['CreationClassName']='CIM_ListenerDestinationCIMXML'
    destinst['SystemCreationClassName']='CIM_ComputerSystem'
    destinst['SystemName']=getfqdn()
    print("destname=%s" % name)
    destinst['Name']=name
    destinst['Destination']=destination
    cop = pywbem.CIMInstanceName('CIM_ListenerDestinationCIMXML')
    cop.keybindings = { 'CreationClassName':'CIM_ListenerDestinationCIMXML',
                        'SystemClassName':'CIM_ComputerSystem',
                        'SystemName':getfqdn(),
                        'Name':name }
    cop.namespace=ns
    destinst.path = cop
    destcop = conn.CreateInstance(destinst)
    return destcop

def _createSubscription(ns,
                        handler,
                        indfilter):
    subinst=pywbem.CIMInstance('CIM_IndicationSubscription')
    subinst['Filter']=indfilter
    subinst['Handler']=indhandler
    cop = pywbem.CIMInstanceName('CIM_IndicationSubscription')
    cop.keybindings = { 'Filter':indfilter,
                        'Handler':indhandler }
    cop.namespace=ns
    subinst.path = cop
    subcop = conn.CreateInstance(subinst)
    return subcop


if __name__ == '__main__':
    global conn
    parser = optparse.OptionParser()
    parser.add_option('--level',
            '-l',
            action='store',
            type='int',
            dest='dbglevel',
            help='Indicate the level of debugging statements to display (default=2)',
            default=2)
    parser.add_option('-s', '--UDS', help="Use the SFCBUDSConnection to the cimom", default=False )
    parser.add_option('-u', '--url', default='https://localhost',
            help='Specify the url of the CIMOM (default=https://localhost)')
    parser.add_option('-n', '--namespace', default='root/interop',
            help='Specify the namespace the test runs against (default=root/interop)')
    parser.add_option('', '--user', default='pegasus',
            help='Specify the user name used when connection to the CIMOM (default=pegasus)')
    parser.add_option('', '--password', default='',
            help='Specify the password for the user (default=<empty>)')
    parser.add_option('--verbose', '', action='store_true', default=False,
            help='Show verbose output')

    parser.add_option('-q', '--query', help='Query string for Filter')
    parser.add_option('-g', '--qlang', help='Query Language (default=WQL)', default="WQL")
    parser.add_option('-d', '--dest', help='Destination for the CIM_ListenerDestination')

    parser.add_option('-p', '--provider', help='Name of provider to setup listener for')
    options, arguments = parser.parse_args()

    conn = WBEMConn().conn

    indhandler=None
    indfilter=None
    indsub=None
    try:
        indhandler = _createDest(options.dest, options.namespace)
        indfilter = _createFilter(options.query, options.namespace, querylang=options.qlang)
        indsub = _createSubscription(options.namespace, indhandler, indfilter)

        log.startLogging(sys.stdout)

        site = server.Site(CIMOM())

        reactor.listenTCP(5998, site)
        reactor.listenSSL(5999, site, ServerContextFactory())
        reactor.run()
    finally:
        if indsub:
            conn.DeleteInstance(indsub)
        if indfilter:
            conn.DeleteInstance(indfilter)
        if indhandler:
            conn.DeleteInstance(indhandler)

