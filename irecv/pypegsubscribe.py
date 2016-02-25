#!/usr/bin/python
#
# Simple indication receiver using Twisted Python.  HTTP post requests
# are listened for on port 5988 and port 5899 using SSL.
#
# Requires Twisted Python and
#

import sys
import pywbem
import optparse
import time
from OpenSSL import SSL
from twisted.internet import ssl, reactor
from twisted.python import log
from twisted.web import server, resource
from socket import getfqdn

_g_verbose=False
_g_options=None

class WBEMConn:
    _shared_state = {}
    conn = None

    def __init__(self, options=None):
        # Borgness
        self.__dict__ = WBEMConn._shared_state

        if options:
            self.conn = pywbem.WBEMConnection(
                    options.url,
                    (options.user, options.password),
                    default_namespace = options.namespace)

class CIMListener(resource.Resource):

    isLeaf = 1

    def render_POST(self, request):

        for line in request.content.readlines():
            print(line)

        return ''


class ServerContextFactory:
    def getContext(self):
        """Create an SSL context with a dodgy certificate."""
        ctx = SSL.Context(SSL.SSLv23_METHOD)
        ctx.use_certificate_file('server.pem')
        ctx.use_privatekey_file('server.pem')
        return ctx


class PyPegSubscribe:
    '''
    Subscription manager for indications on OpenPegasus
    Allows:
      creating subscriptions (including filters and handlers)
      listing subscriptions, filters, handlers
      cleaning up (deleting) subscriptions, filters, handlers
      listening to active subscriptions
    '''
    def __init__(self, conn):
        self._conn=conn

    def createFilter(self,
                      query,
                      ns,
                      in_name=None):
        name = in_name or 'cimfilter%d'%time.time()
        filterinst=pywbem.CIMInstance('CIM_IndicationFilter')
        filterinst['CreationClassName']='CIM_IndicationFilter'
        filterinst['SystemCreationClassName']='CIM_ComputerSystem'
        filterinst['SystemName']=getfqdn()
        filterinst['Name']=name
        filterinst['Query']=query
        filterinst['QueryLanguage']='WQL'
        cop = pywbem.CIMInstanceName('CIM_IndicationFilter')
        cop.keybindings = { 'CreationClassName':'CIM_IndicationFilter',
                            'SystemCreationClassName':'CIM_ComputerSystem',
                            'SystemName':getfqdn(),
                            'Name':name }
        cop.namespace=ns
        filterinst.path = cop
        filtercop = self._conn.CreateInstance(filterinst)
        return filtercop

    def createDest(self,
                    destination,
                    ns,
                    in_name=None):
        name = in_name or 'cimlistener%d'%time.time()
        destinst=pywbem.CIMInstance('CIM_ListenerDestinationCIMXML')
        destinst['CreationClassName']='CIM_ListenerDestinationCIMXML'
        destinst['SystemCreationClassName']='CIM_ComputerSystem'
        destinst['SystemName']=getfqdn()
        destinst['Name']=name
        destinst['Destination']=destination
        cop = pywbem.CIMInstanceName('CIM_ListenerDestinationCIMXML')
        cop.keybindings = { 'CreationClassName':'CIM_ListenerDestinationCIMXML',
                            'SystemCreationClassName':'CIM_ComputerSystem',
                            'SystemName':getfqdn(),
                            'Name':name }
        cop.namespace=ns
        destinst.path = cop
        destcop = self._conn.CreateInstance(destinst)
        return destcop

    def createSubscription(self,
                            handler,
                            indfilter,
                            ns):
        subinst=pywbem.CIMInstance('CIM_IndicationSubscription')
        subinst['Filter']=indfilter
        subinst['Handler']=indhandler
        cop = pywbem.CIMInstanceName('CIM_IndicationSubscription')
        cop.keybindings = { 'Filter':indfilter,
                            'Handler':indhandler }
        cop.namespace=ns
        subinst.path = cop
        subcop = self._conn.CreateInstance(subinst)
        return subcop

    def listObjects(self, cn):
        insts = self._conn.EnumerateInstances(cn)
        print("======== Instances of class: %s ========" % cn)
        for inst in insts:
            print("  >>>  %s" % inst.path)
            if not _g_options.pathonly:
                for key in inst.properties.keys():
                    if inst.properties[key].value is not None:
                        print("       > %s : %s" %\
                              (key, inst.properties[key].value))

    def listFilters(self):
        self.listObjects('CIM_IndicationFilter')

    def listHandlers(self):
        self.listObjects('CIM_ListenerDestination')

    def listSubs(self):
        self.listObjects('CIM_IndicationSubscription')

    def getObjects(self, cn):
        objects=[]
        insts = self._conn.EnumerateInstances(cn)
        objects.append(insts)

    def getFilters(self):
        return self.getObjects('CIM_IndicationFilter')

    def getHandlers(self):
        return self.getObjects('CIM_ListenerDestination')

    def getSubs(self):
        return self.getObjects('CIM_IndicationSubscription')

    def cleanupAll(self, ns):
        classnames=['CIM_IndicationSubscription',
                    'CIM_IndicationFilter',
                    'CIM_ListenerDestinationCIMXML',
                    'CIM_IndicationHandlerCIMXML']
        for cn in classnames:
            print("***Cleaning up instances of: %s" % cn)
            cops = self._conn.EnumerateInstanceNames(cn, namespace=ns)
            for cop in cops:
                print("   > %s" % cop)
                self._conn.DeleteInstance(cop)


if __name__ == '__main__':
    parser = optparse.OptionParser()
    '''
    parser.add_option('--level',
            '-l',
            action='store',
            type='int',
            dest='dbglevel',
            help='Indicate the level of debugging statements to display (default=2)',
            default=2)
    '''
    parser.add_option('--verbose', '', action='store_true', default=False,
            help='Show verbose output')

    parser.add_option('', '--createsub',  action='store_true', default=False,
            help='Create Subscription, including necessary filter and handler... requires --query and --dest')
    parser.add_option('', '--listensub', action='store_true', default=False,
            help='Listen, using existing subscription.  ')
    parser.add_option('--cleanall', action='store_true', default=False,
            help='Delete all filters, handlers, and subscriptions')
    parser.add_option('', '--listfilters', action='store_true', default=False,
            help='List Current Filters')
    parser.add_option('', '--listhandlers', action='store_true', default=False,
            help='List Current Handlers')
    parser.add_option('', '--listsubs', action='store_true', default=False,
            help='List Current Subscriptions')
    parser.add_option('', '--listall', action='store_true', default=False,
            help='List Current Filters, Handlers, and Subscriptions')
    parser.add_option('', '--pathonly', action='store_true', default=False,
            help='When listing Current Filters, Handlers, and Subscriptions, list the path only')

    parser.add_option('-u', '--url', default='https://localhost',
            help='Specify the url of the CIMOM (default=https://localhost)')
    parser.add_option('-n', '--namespace', default='root/cimv2',
            help='Specify the namespace the test runs against (default=root/cimv2)')
    parser.add_option('--user', default='pegasus',
            help='Specify the user name used when connection to the CIMOM (default=pegasus)')
    parser.add_option('--password', default='',
            help='Specify the password for the user (default=<empty>)')
    parser.add_option('-q', '--query',
            help='Query string for Filter.  Required for --createsub')
    parser.add_option('-d', '--dest',
            help='Destination for the CIM_ListenerDestination.  Required for --createsub')
    parser.add_option('', '--nolisten', action='store_true', default=False,
            help='When creating a subscription, don\'t start a listener')
    parser.add_option('--httpPort', default='5998', help='Port to listen on for http.  Valid for --createsub and --listensub')
    parser.add_option('--httpsPort', default='5999', help='Port to listen on for https.  Valid for --createsub and --listensub')


    options, arguments = parser.parse_args()
    _g_options=options
    _g_verbose=options.verbose

    conn = WBEMConn(options).conn

    subs2cleanup = []
    paths2cleanup = []

    sub = PyPegSubscribe(conn)

    if options.createsub:
        indhandler = sub.createDest(options.dest, options.namespace)
        indfilter = sub.createFilter(options.query, options.namespace)
        indsub = sub.createSubscription(indhandler, indfilter, options.namespace)

        if not options.nolisten:
            paths2cleanup.append(indhandler)
            paths2cleanup.append(indfilter)
            subs2cleanup.append(indsub)

            log.startLogging(sys.stdout)

            site = server.Site(CIMListener())

            reactor.listenTCP(int(options.httpPort), site)
            reactor.listenSSL(int(options.httpsPort), site, ServerContextFactory())
            reactor.run()

            for sub in subs2cleanup:
                conn.DeleteInstance(sub)
            for path in paths2cleanup:
                conn.DeleteInstance(path)
    elif options.cleanall:
        sub.cleanupAll(options.namespace)
    elif options.listfilters:
        sub.listFilters()
    elif options.listhandlers:
        sub.listHandlers()
    elif options.listsubs:
        sub.listSubs()
    elif options.listall:
        sub.listFilters()
        sub.listHandlers()
        sub.listSubs()

