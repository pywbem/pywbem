#
# Proposed interface for a WBEM listener.
#

import sys
import pywbem
import optparse
import time
from socket import getfqdn

from twisted.web.resource import Resource
from twisted.web.server import Site

from OpenSSL import SSL
from twisted.internet import ssl, reactor
from twisted.python import log
from recordclass import recordclass

_g_verbose=False
_g_options=None

DEFAULT_LISTENER_PORT_HTTP = 5988
DEFAULT_LISTENER_PORT_HTTPS = 5989


class WBEMListener(object):
    """
    A WBEM listener, supporting the CIM-XML protocol for CIM indications.

    It supports starting and stopping a WBEM listener thread.
    The WBEM listener thread is an HTTP/HTTPS server that listens for CIM-XML
    export messages containing the CIM indications from one or more WBEM
    servers.

    It also supports the management of subscriptions for CIM indications
    from one or more WBEM servers, including the creation and deletion of
    the necessary listener, filter and subscription instances in the WBEM
    servers.
    """

    ServerInfo = recordclass('ServerInfo', ['conn', 'interop_ns'])

    def __init__(self, host, http_port=DEFAULT_LISTENER_PORT_HTTP,
                 https_port=DEFAULT_LISTENER_PORT_HTTPS):
        """
        Parameters:

          host (string):
            IP address or host name to be used as the listener destination
            by any WBEM servers to reach this listener.

          http_port (string or integer):
            Port to be used for listening via HTTP.

            `None` means not to set up a port for HTTP.

          https_port (string or integer):
            Port to be used for listening via HTTPS.

            `None` means not to set up a port for HTTPS.
        """

        self.host = host

        if isinstance(http_port, six.integer_types):
            self.http_port = int(http_port)  # Convert Python 2 long to int 
        elif isinstance(http_port, six.string_types):
            self.http_port = int(http_port)
        elif http_port is None:
            self.http_port = http_port
        else:
            raise TypeError("Invalid type for http_port: %s" % \
                            type(http_port))

        if isinstance(https_port, six.integer_types):
            self.https_port = int(https_port)  # Convert Python 2 long to int 
        elif isinstance(https_port, six.string_types):
            self.https_port = int(https_port)
        elif https_port is None:
            self.https_port = https_port
        else:
            raise TypeError("Invalid type for https_port: %s" % \
                            type(https_port))

        self._server_infos = {}


    def start(self):
        """
        Start the WBEM listener thread.

        Once the WBEM listener thread is up and running, return.
        """

        subs2cleanup = []
        paths2cleanup = []

        indhandler = self.createDest(options.dest, options.namespace)
        indfilter = self.createFilter(options.query, options.namespace)
        indsub = self.createSubscription(indhandler, indfilter, options.namespace)

        paths2cleanup.append(indhandler)
        paths2cleanup.append(indfilter)
        subs2cleanup.append(indsub)

        # TODO: Logging
        #log.startLogging(sys.stdout)

        site = Site(_WBEMListenerResource())

        if self.http_port:
            reactor.listenTCP(self.http_port, site)
        if self.https_port:
            reactor.listenSSL(self.https_port, site,
                              _HTTPSServerContextFactory())
        reactor.run()

        # XXX
        #for sub in subs2cleanup:
        #    conn.DeleteInstance(sub)
        #for path in paths2cleanup:
        #    conn.DeleteInstance(path)

    def stop(self):
        """Stop the WBEM listener thread."""
        raise NotImplementedError  # TODO: Implement

    def add_server(self, conn, interop_ns=None):
        """
        Add a WBEM server to this listener and register with the WBEM server by
        creating a CIM_IndicationListener instance for this listener in its
        Interop namespace.

        Parameters:

          conn (pywbem.WBEMConnection):
            Connection to the WBEM server.

          interop_ns (string):
            Name of the Interop namespace to be used on the WBEM server.

            `None` causes the Interop namespace to be determined automatically,
            using :meth:`determine_interop_namespace`.
        """
        server_info = ServerInfo(conn=conn)
        if interop_ns is None:
            interop_ns = self.determine_interop_namespace(conn)
        server_info.interop_ns = interop_ns
        server_key = conn.url
        self._server_infos[server_key] = server_info
        self.create_destination(conn, self.host, interop_ns):

    def determine_interop_namespace(self, conn):
        """
        Determine the name of the Interop namespace of a WBEM server, by
        communicating with it.

        Parameters:

          conn (pywbem.WBEMConnection):
            Connection to the WBEM server.

        Returns:
          A string

        Raises:
          * Any exceptions that can be raised by pywbem.WBEMConnection.
          * TODO: A special exception indicating interop namespace not found?
        """
        # TODO: implement
        return 'interop'

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

    def create_destination(self, conn, destination, ns, name=None):
        if name is None:
            name = 'cimlistener%d' % time.time()
        destinst = pywbem.CIMInstance('CIM_ListenerDestinationCIMXML')
        destinst['CreationClassName'] = 'CIM_ListenerDestinationCIMXML'
        destinst['SystemCreationClassName'] = 'CIM_ComputerSystem'
        destinst['SystemName'] = getfqdn()
        destinst['Name'] = name
        destinst['Destination'] = destination
        cop = pywbem.CIMInstanceName('CIM_ListenerDestinationCIMXML')
        cop.keybindings = { 'CreationClassName':'CIM_ListenerDestinationCIMXML',
                            'SystemCreationClassName':'CIM_ComputerSystem',
                            'SystemName':getfqdn(),
                            'Name':name }
        cop.namespace = ns
        destinst.path = cop
        destcop = conn.CreateInstance(destinst)
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


class _WBEMListenerResource(Resource):

    def render_POST(self, request):
        """
        Will be called for each POST to the WBEM listener. It handles
        the CIM-XML export message.
        """

        # TODO: Change this to pass the indication to subscribers
        for line in request.content.readlines():
            print(line)

        return ''


class _HTTPSServerContextFactory:

    def getContext(self):
        """Create an SSL context with a dodgy certificate."""
        ctx = SSL.Context(SSL.SSLv23_METHOD)
        ctx.use_certificate_file('server.pem')
        ctx.use_privatekey_file('server.pem')
        return ctx


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

