"""
Demonstrate issue https://github.com/pywbem/pywbem/issues/2383

The code works on Python 2.7 and 3.4 and higher 3.x.
The issue happens only on Python 3.8.5 on macOS.
"""

from time import sleep
import logging
import threading
import requests
import pytest
from six.moves import BaseHTTPServer
from six.moves import socketserver
from six.moves import http_client

# Show log messages by changing this to DEBUG
LOGLEVEL = logging.NOTSET
LOGFILE = 'listener.log'

LOGGER = logging.getLogger('demo_listener')
ROOT_LOGGER = logging.getLogger('')

if LOGLEVEL > logging.NOTSET:
    ROOT_LOGGER.setLevel(LOGLEVEL)
    hdlr = logging.FileHandler(LOGFILE)
    hdlr.setFormatter(logging.Formatter(
        "%(asctime)s %(thread)s %(name)s %(levelname)s %(message)s"))
    ROOT_LOGGER.addHandler(hdlr)


class ThreadedHTTPServer(socketserver.ThreadingMixIn,
                         BaseHTTPServer.HTTPServer):
    pass


class DemoListenerRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    def do_POST(self):
        """
        Send a dummy response back to the requester.
        """
        resp_body = b'<dummy_reponse/>'
        http_code = 200
        self.send_response(http_code, http_client.responses.get(http_code, ''))
        self.send_header("Content-Type", "application/xml; charset=utf-8")
        self.send_header("Content-Length", str(len(resp_body)))
        self.end_headers()
        self.wfile.write(resp_body)

    def log_message(self, format, *args):
        """
        The :class:`~py3:http.server.BaseHTTPRequestHandler` methods call this
        method for anything that needs to get logged.

        We override it in order to log at the DEBUG level, instead of writing
        to stderr as the default implementation does.
        """
        LOGGER.debug(format, *args)


class DemoListener(object):
    """
    A listener for demonstration purposes, that supports starting and stopping
    a thread that listens for HTTP messages. HTTPS support and other
    functionality has been removed for simplicity.
    """

    def __init__(self, host, http_port=None):
        self.host = host
        self.http_port = http_port  # Must be int
        self._http_server = None  # ThreadedHTTPServer for HTTP
        self._http_thread = None  # Thread for HTTP

    def start(self):
        if not self._http_server:
            LOGGER.debug("Starting threaded HTTP server")
            server = ThreadedHTTPServer((self.host, self.http_port),
                                        DemoListenerRequestHandler)
            thread = threading.Thread(target=server.serve_forever)
            thread.daemon = True  # Exit server thread upon main thread exit
            self._http_server = server
            self._http_thread = thread
            thread.start()

    def stop(self):
        if self._http_server:
            LOGGER.debug("Stopping threaded HTTP server")
            self._http_server.shutdown()
            self._http_server.server_close()
            self._http_server = None
            self._http_thread = None


@pytest.mark.parametrize(
    "send_count, repetition",
    [(10, i) for i in range(0, 10)] +
    [(100, i) for i in range(0, 10)]
)
def test_send(send_count, repetition):
    LOGGER.debug("======== test_send called with send_count={}, repetition={}".
                 format(send_count, repetition))
    host = 'localhost'
    http_port = 50000
    try:
        listener = DemoListener(host=host, http_port=http_port)
        listener.start()
        url = 'http://{}:{}'.format(host, http_port)
        headers = {
            "Content-Type": "application/xml; charset=utf-8",
        }
        payload = b'<dummy_request/>'
        for i in range(send_count):
            LOGGER.debug("Sending request #{}".format(i))
            try:
                response = requests.post(
                    url, headers=headers, data=payload, timeout=4)
            except requests.exceptions.RequestException as exc:
                new_exc = AssertionError(
                    "Sending request #{} raised {}: {}".
                    format(i, exc.__class__.__name__, exc))
                new_exc.__cause__ = None
                LOGGER.error(str(new_exc))
                raise new_exc
            assert response.status_code == 200, \
                "Sending request #{} resulted in HTTP status {}". \
                format(i, response.status_code)
        sleep(0.1)
    finally:
        listener.stop()
