#!/usr/bin/python
#
# Simple indication receiver using Twisted Python.  HTTP post requests
# are listened for on port 5988 and port 5899 using SSL.
#
# Requires Twisted Python and 
#

import sys
from twisted.internet import reactor
from twisted.web import server, resource

class CIMOM(resource.Resource):

    isLeaf = 1

    def render_POST(self, request):

        for line in request.content.readlines():
            print line

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

log.startLogging(sys.stdout)

site = server.Site(CIMOM())

reactor.listenTCP(5988, site)
reactor.listenSSL(5989, site, ServerContextFactory())
reactor.run()
