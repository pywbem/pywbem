#!/usr/bin/env python
"""
Script that demonstrates the BadStatusLine exception that is caused by
a response message that contains the request message.

The script starts a threaded HTTP server with a response handler that parses
an ID from the request body and sends back a response with the same ID.
The main program has a loop that sends requests to the HTTP server and checks
that the response contains the same ID that was sent.

There is a config variable that controls whether the main program uses the
http.client module or the requests package on the client side. The server
side always uses http.server.HTTPServer.

When the error happens, the script breaks with an AssertionError that shows
the BadStatusLine exception as follows:

When the http.client module is used:

    http.client.BadStatusLine: POST http://localhost:50000 HTTP/1.1

When the requests package is used:

    requests.ConnectionError: ('Connection aborted.',
        BadStatusLine("POST / HTTP/1.1\r\n"))

In both cases, the response contains the status line of the request and also
the headers and the body of the request (the headers and body cannot be
displayed once the error has happened, but this was confirmed through
debugging).

The script must be run multiple times to trigger the error, e.g.:

    rc=0; while [ $rc -eq 0 ]; do ./badstatusline.py; rc=$?; done

Notes:
* Runs only on Python 3.
* Has been simplified from the original pywbem code.
* The original pywbem issue is https://github.com/pywbem/pywbem/issues/2659.
"""

import platform
import re
import logging
import threading
import http.client
import http.server
import socketserver


# If True, the 'requests' package is used for sending the requests.
# If False, the http.client module is used.
USE_REQUESTS = False

# Number of requests to be sent (and responses to expect)
REQUEST_COUNT = 500

# Path name of log file, and log level
LOG_FILE = 'badstatusline.log'
LOG_LEVEL = logging.DEBUG  # logging.NOTSET disables logging

# Port number to use for the threaded HTTP server
HTTP_PORT = 50000


if USE_REQUESTS:
    import requests


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """
    The HTTP server that will run in a thread.
    """
    pass


class RequestHandler(http.server.BaseHTTPRequestHandler):
    """
    The HTTP request handler - will be called in context of the HTTP server
    thread.
    """

    @property
    def logger(self):
        try:
            return self._logger
        except AttributeError:
            self._logger = logging.getLogger('badstatusline.server')
            return self._logger

    def do_POST(self):
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len).decode('utf-8')
        m = re.match(r'request_id=([0-9]+)$', body)
        if m is None:
            self._send_http_response(
                400, body="error=Invalid request body: {!r}".format(body))
        request_id = int(m.group(1))
        self._send_http_response(
            200, body="response_id={}".format(request_id))

    def _send_http_response(self, http_code, body=None, headers=None):
        self.logger.debug(
            "Sending HTTP response with HTTP status %s and body: %r",
            http_code, body)
        reason = http.client.responses.get(http_code, '')
        self.send_response(http_code, reason)  # Logs the send
        self.send_header('Content-Length', str(len(body)))
        if headers is not None:
            for header, value in headers:
                self.send_header(header, value)
        self.end_headers()
        self.wfile.write(body.encode('utf-8'))
        self.logger.debug(
            "Sent HTTP response with HTTP status %s", http_code)

    def do_OPTIONS(self):
        self.invalid_method()

    def do_HEAD(self):
        self.invalid_method()

    def do_GET(self):
        self.invalid_method()

    def do_PUT(self):
        self.invalid_method()

    def do_PATCH(self):
        self.invalid_method()

    def do_DELETE(self):
        self.invalid_method()

    def do_TRACE(self):
        self.invalid_method()

    def do_CONNECT(self):
        self.invalid_method()

    def do_M_POST(self):
        self.invalid_method()

    def invalid_method(self):
        self._send_http_response(405, headers=[('Allow', 'POST')])

    def log_request(self, code='-', size='-'):
        """
        This function is called in
        http.server.BaseHTTPRequestHandler.send_response().
        """
        if isinstance(code, http.server.HTTPStatus):
            code = code.value
        self.log_message("Sending %s response with HTTP status %s",
                         self.command, code)

    def log_error(self, format, *args):
        """
        The http.server.BaseHTTPRequestHandler methods call this method for
        anything that needs to get logged as an error.
        """
        self.logger.error(format, *args)

    def log_message(self, format, *args):
        """
        The http.server.BaseHTTPRequestHandler methods call this method for
        anything that needs to get logged.
        """
        self.logger.info(format, *args)


class Listener(object):
    """
    A listener that supports starting and stopping the HTTP server thread.
    """

    def __init__(self, host, http_port, logger):
        self.host = host
        self.http_port = int(http_port)
        self.http_server = None  # ThreadedHTTPServer for HTTP
        self.http_thread = None  # Thread for HTTP
        self.logger = logger

    def start(self):
        """
        Start the HTTP server thread, if not running.
        """
        if not self.http_server:
            self.logger.info("Starting threaded HTTP server on port %s",
                             self.http_port)

            server = ThreadedHTTPServer((self.host, self.http_port),
                                        RequestHandler)

            # Make our logger available to the HTTP server thread
            server.listener_logger = self.logger

            thread = threading.Thread(target=server.serve_forever)
            thread.daemon = True  # Exit server thread upon main thread exit
            self.http_server = server
            self.http_thread = thread
            thread.start()

            self.logger.info("Started threaded HTTP server on port %s",
                             self.http_port)

    def stop(self):
        """
        Stop the HTTP server thread, if running.
        """
        if self.http_server:
            self.logger.info("Stopping threaded HTTP server")
            self.http_server.shutdown()
            self.http_server.server_close()
            self.http_server = None
            self.http_thread = None
            self.logger.info("Stopped threaded HTTP server")


def post(host, http_port, request_id, logger):
    """
    Post a single request with a request ID, wait for the response, and upon
    success return the response ID.
    """

    logger.debug("Sending request with request_id=%s", request_id)

    url = 'http://{}:{}'.format(host, http_port)
    headers = {}
    body = 'request_id={}\n'.format(request_id)

    if USE_REQUESTS:
        try:
            response = requests.post(url, headers=headers, data=body, timeout=4)
        except requests.exceptions.RequestException as exc:
            msg = ("requests.post() for request_id={} raised {}: {}".
                   format(request_id, exc.__class__.__name__, exc))
            logger.error(msg)
            raise AssertionError(msg)
        response_body = response.text
        response_status = response.status_code
    else:
        conn = http.client.HTTPConnection(host, http_port, timeout=4)
        try:
            conn.request('POST', url, body=body, headers=headers)
        except Exception as exc:
            msg = ("http.client conn.request() for request_id={} "
                   "raised {}: {}".
                   format(request_id, exc.__class__.__name__, exc))
            logger.error(msg)
            raise AssertionError(msg)
        try:
            response = conn.getresponse()
        except Exception as exc:
            msg = ("http.client conn.getresponse() for request_id={} "
                   "raised {}: {}".
                   format(request_id, exc.__class__.__name__, exc))
            logger.error(msg)
            raise AssertionError(msg)
        response_body = response.read().decode('utf-8')
        response_status = response.status

    if response_status != 200:
        msg = ("Received unexpected HTTP status in response for request with "
               "request_id={}: HTTP status: {}, body={}".
               format(request_id, response_status, response_body))
        logger.error(msg)
        raise AssertionError(msg)

    m = re.match(r'response_id=([0-9]+)$', response_body)
    if m is None:
        msg = ("Received unexpected format in body of successful response "
               "for request with request_id={}: body={}".
               format(request_id, response_body))
        logger.error(msg)
        raise AssertionError(msg)

    response_id = int(m.group(1))
    logger.debug(
        "Received successful response with response_id=%s for request "
        "with request_id=%s",
        response_id, request_id)

    return response_id


def main():
    """
    Main function that starts the listener and sends requests with increasing
    IDs to it, and verifies that the response has the same ID.
    """

    package = 'requests' if USE_REQUESTS else 'http.client'

    print("Using '{}' package on {} {} with {} requests".
          format(package, platform.python_implementation(),
                 platform.python_version(),
                 REQUEST_COUNT))

    if LOG_LEVEL > logging.NOTSET:
        logging.basicConfig(
            filename=LOG_FILE,
            filemode='w',
            format='%(asctime)s %(threadName)-10s %(levelname)-5s %(name)s: '
            '%(message)s',
            level=LOG_LEVEL)

    host = 'localhost'
    logger = logging.getLogger('badstatusline.main')

    listener = Listener(host, HTTP_PORT, logger)
    listener.start()
    try:
        for i in range(REQUEST_COUNT):
            request_id = i
            response_id = post(host, HTTP_PORT, request_id, logger)
            assert request_id == response_id
    finally:
        listener.stop()


if __name__ == '__main__':
    main()
