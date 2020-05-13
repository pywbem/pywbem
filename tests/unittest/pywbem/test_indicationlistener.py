#!/usr/bin/env python

"""
Test _listener.py module.
"""

from __future__ import absolute_import

import sys
import errno
import re
import logging
from time import time, sleep
import datetime
from random import randint
import requests
import pytest

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
from ..utils.pytest_extensions import simplified_test_function
pywbem = import_installed('pywbem')
from pywbem import WBEMListener  # noqa: E402
from pywbem._utils import _format  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


class ElapsedTimer(object):
    """
    Elapsed time timer.

    Calculates elapsed time between initiation/reset and access.
    """

    def __init__(self):
        """ Initiate the object with current time"""
        self.start_time = datetime.datetime.now()

    def reset(self):
        """ Reset the start time for the timer"""
        self.start_time = datetime.datetime.now()

    def elapsed_ms(self):
        """ Get the elapsed time in milliseconds. returns floating
            point representation of elapsed time in seconds.
        """
        dt = datetime.datetime.now() - self.start_time
        return ((dt.days * 24 * 3600) + dt.seconds) * 1000 + \
            dt.microseconds / 1000.0

    def elapsed_sec(self):
        """ get the elapsed time in seconds. Returns floating
            point representation of time in seconds
        """
        return self.elapsed_ms() / 1000


TESTCASES_WBEMLISTENER_INIT = [

    # Testcases for WBEMListener.__init__()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * init_args: Tuple of positional arguments to WBEMListener().
    #   * init_kwargs: Dict of keyword arguments to WBEMListener().
    #   * exp_attrs: Dict of expected attributes of resulting object.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Success cases
    (
        "Verify order of positional arguments",
        dict(
            init_args=[
                'woot.com',
                6997,
                6998,
                'certfile.pem',
                'keyfile.pem',
            ],
            init_kwargs={},
            exp_attrs=dict(
                host='woot.com',
                http_port=6997,
                https_port=6998,
                certfile='certfile.pem',
                keyfile='keyfile.pem',
            ),
        ),
        None, None, True
    ),
    (
        "Verify names of keyword arguments",
        dict(
            init_args=[],
            init_kwargs=dict(
                host='woot.com',
                http_port=6997,
                https_port=6998,
                certfile='certfile.pem',
                keyfile='keyfile.pem',
            ),
            exp_attrs=dict(
                host='woot.com',
                http_port=6997,
                https_port=6998,
                certfile='certfile.pem',
                keyfile='keyfile.pem',
            ),
        ),
        None, None, True
    ),
    (
        "Verify minimal arguments for success with http_port as integer",
        dict(
            init_args=[],
            init_kwargs=dict(
                host='woot.com',
                http_port=6997,
            ),
            exp_attrs=dict(
                host='woot.com',
                http_port=6997,
                https_port=None,
                certfile=None,
                keyfile=None,
            ),
        ),
        None, None, True
    ),
    (
        "Verify minimal arguments for success with http_port as string",
        dict(
            init_args=[],
            init_kwargs=dict(
                host='woot.com',
                http_port='6997',
            ),
            exp_attrs=dict(
                host='woot.com',
                http_port=6997,
                https_port=None,
                certfile=None,
                keyfile=None,
            ),
        ),
        None, None, True
    ),
    (
        "Verify full arguments for success with http_port",
        dict(
            init_args=[],
            init_kwargs=dict(
                host='woot.com',
                http_port=6997,
                https_port=None,
                certfile=None,
                keyfile=None,
            ),
            exp_attrs=dict(
                host='woot.com',
                http_port=6997,
                https_port=None,
                certfile=None,
                keyfile=None,
            ),
        ),
        None, None, True
    ),
    (
        "Verify minimal arguments for success with https_port as integer",
        dict(
            init_args=[],
            init_kwargs=dict(
                host='woot.com',
                https_port=6998,
                certfile='certfile.pem',
                keyfile='keyfile.pem',
            ),
            exp_attrs=dict(
                host='woot.com',
                http_port=None,
                https_port=6998,
                certfile='certfile.pem',
                keyfile='keyfile.pem',
            ),
        ),
        None, None, True
    ),
    (
        "Verify minimal arguments for success with https_port as string",
        dict(
            init_args=[],
            init_kwargs=dict(
                host='woot.com',
                https_port='6998',
                certfile='certfile.pem',
                keyfile='keyfile.pem',
            ),
            exp_attrs=dict(
                host='woot.com',
                http_port=None,
                https_port=6998,
                certfile='certfile.pem',
                keyfile='keyfile.pem',
            ),
        ),
        None, None, True
    ),
    (
        "Verify full arguments for success with https_port",
        dict(
            init_args=[],
            init_kwargs=dict(
                host='woot.com',
                http_port=None,
                https_port=6998,
                certfile='certfile.pem',
                keyfile='keyfile.pem',
            ),
            exp_attrs=dict(
                host='woot.com',
                http_port=None,
                https_port=6998,
                certfile='certfile.pem',
                keyfile='keyfile.pem',
            ),
        ),
        None, None, True
    ),

    # Failure cases
    (
        "Verify failure when providing invalid type for http_port",
        dict(
            init_args=[],
            init_kwargs=dict(
                host='woot.com',
                http_port=12.1,
            ),
            exp_attrs=None,
        ),
        TypeError, None, True
    ),
    (
        "Verify failure when providing invalid type for https_port",
        dict(
            init_args=[],
            init_kwargs=dict(
                host='woot.com',
                https_port=12.1,
                certfile='certfile.pem',
                keyfile='keyfile.pem',
            ),
            exp_attrs=None,
        ),
        TypeError, None, True
    ),
    (
        "Verify failure when providing no certfile with https_port",
        dict(
            init_args=[],
            init_kwargs=dict(
                host='woot.com',
                https_port=6998,
                certfile=None,
                keyfile='keyfile.pem',
            ),
            exp_attrs=None,
        ),
        ValueError, None, True
    ),
    (
        "Verify failure when providing no keyfile with https_port",
        dict(
            init_args=[],
            init_kwargs=dict(
                host='woot.com',
                https_port=6998,
                certfile='certfile.pem',
                keyfile=None,
            ),
            exp_attrs=None,
        ),
        ValueError, None, True
    ),
    (
        "Verify failure when providing no port",
        dict(
            init_args=[],
            init_kwargs=dict(
                host='woot.com',
                http_port=None,
                https_port=None,
            ),
            exp_attrs=None,
        ),
        ValueError, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_WBEMLISTENER_INIT)
@simplified_test_function
def test_WBEMListener_init(testcase, init_args, init_kwargs, exp_attrs):
    """
    Test function for WBEMListener.__init__()
    """

    # The code to be tested
    obj = WBEMListener(*init_args, **init_kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    # Verify specified expected attributes
    for attr_name in exp_attrs:
        exp_attr = exp_attrs[attr_name]
        act_attr = getattr(obj, attr_name)
        assert act_attr == exp_attr
        assert isinstance(act_attr, type(exp_attr))

    # Verify attributes not set via init arguments

    assert isinstance(obj.logger, logging.Logger)
    assert re.match(r'pywbem\.listener\.', obj.logger.name)

    assert obj.http_started is False
    assert obj.https_started is False


TESTCASES_WBEMLISTENER_STR = [

    # Testcases for WBEMListener.__str__() / str()

    # Each list item is a testcase tuple with these items:
    # * obj: WBEMListener object to be tested.

    (
        WBEMListener(
            host='woot.com',
            http_port=6997,
            https_port=6998,
            certfile='certfile.pem',
            keyfile='keyfile.pem')
    ),
]


@pytest.mark.parametrize(
    "obj",
    TESTCASES_WBEMLISTENER_STR)
def test_WBEMListener_str(obj):
    """
    Test function for WBEMListener.__str__() / str()
    """

    # The code to be tested
    result = str(obj)

    assert re.match(r'^WBEMListener\(', result)

    exp_host_str = _format('_host={0!A}', obj.host)
    assert exp_host_str in result

    exp_http_port_str = _format('_http_port={0!A}', obj.http_port)
    assert exp_http_port_str in result

    exp_https_port_str = _format('_https_port={0!A}', obj.https_port)
    assert exp_https_port_str in result


TESTCASES_WBEMLISTENER_REPR = [

    # Testcases for WBEMListener.__repr__() / repr()

    # Each list item is a testcase tuple with these items:
    # * obj: WBEMListener object to be tested.

    (
        WBEMListener(
            host='woot.com',
            http_port=6997,
            https_port=6998,
            certfile='certfile.pem',
            keyfile='keyfile.pem')
    ),
]


@pytest.mark.parametrize(
    "obj",
    TESTCASES_WBEMLISTENER_REPR)
def test_WBEMListener_repr(obj):
    """
    Test function for WBEMListener.__repr__() / repr()
    """

    # The code to be tested
    result = repr(obj)

    assert re.match(r'^WBEMListener\(', result)

    exp_host_str = _format('_host={0!A}', obj.host)
    assert exp_host_str in result

    exp_http_port_str = _format('_http_port={0!A}', obj.http_port)
    assert exp_http_port_str in result

    exp_https_port_str = _format('_https_port={0!A}', obj.https_port)
    assert exp_https_port_str in result

    exp_certfile_str = _format('_certfile={0!A}', obj.certfile)
    assert exp_certfile_str in result

    exp_keyfile_str = _format('_keyfile={0!A}', obj.keyfile)
    assert exp_keyfile_str in result

    exp_logger_str = _format('_logger={0!A}', obj.logger)
    assert exp_logger_str in result


def test_WBEMListener_start_stop():
    """
    Test starting and stopping of the listener.
    """

    host = 'localhost'
    http_port = '50000'

    listener = WBEMListener(host, http_port)
    assert listener.http_started is False
    assert listener.https_started is False

    listener.start()
    assert listener.http_started is True
    assert listener.https_started is False

    listener.stop()
    assert listener.http_started is False
    assert listener.https_started is False


def test_WBEMListener_port_in_use():
    """
    Test starting the listener when port is in use by another listener.
    """

    host = 'localhost'

    # Don't use this port in other tests, to be on the safe side
    # as far as port reuse is concerned.
    http_port = '59999'

    exp_exc_type = OSError

    listener1 = WBEMListener(host, http_port)
    listener1.start()
    assert listener1.http_started is True

    listener2 = WBEMListener(host, http_port)

    try:

        # The code to be tested
        listener2.start()

    except Exception as exc:  # pylint: disable=broad-except
        # e.g. on Linux
        assert isinstance(exc, exp_exc_type)
        assert getattr(exc, 'errno', None) == errno.EADDRINUSE
        assert listener2.http_started is False
    else:
        # e.g. on Windows
        assert listener2.http_started is True

    # Verify that in any case, listener1 is still started
    assert listener1.http_started is True

    listener1.stop()  # cleanup
    listener2.stop()  # cleanup (for cases where it started)


def test_WBEMListener_context_mgr():
    """
    Test starting the listener and automatic closing in a context manager.
    """

    host = 'localhost'

    # Don't use this port in other tests, to be on the safe side
    # as far as port reuse is concerned.
    http_port = '59998'

    # The code to be tested (is the context manager)
    with WBEMListener(host, http_port) as listener1:

        # Verify that CM enter returns the listener
        assert isinstance(listener1, WBEMListener)

        listener1.start()
        assert listener1.http_started is True

    # Verify that CM exit stops the listener
    assert listener1.http_started is False

    # Verify that the TCP/IP port can be used again
    listener2 = WBEMListener(host, http_port)
    listener2.start()
    assert listener2.http_started is True
    listener2.stop()


def create_indication_data(msg_id, sequence_number, delta_time, protocol_ver):
    """
    Create a test indication from the template and input attributes.
    """

    data_template = """<?xml version="1.0" encoding="utf-8" ?>
    <CIM CIMVERSION="2.0" DTDVERSION="2.4">
      <MESSAGE ID="{msg_id}" PROTOCOLVERSION="{protocol_ver}">
        <SIMPLEEXPREQ>
          <EXPMETHODCALL NAME="ExportIndication">
            <EXPPARAMVALUE NAME="NewIndication">
              <INSTANCE CLASSNAME="CIM_AlertIndication">
                <PROPERTY NAME="Severity" TYPE="string">
                  <VALUE>high</VALUE>
                </PROPERTY>
                <PROPERTY NAME="SequenceNumber" TYPE="string">
                  <VALUE>{sequence_number}</VALUE>
                </PROPERTY>
                <PROPERTY NAME="DELTA_TIME" TYPE="string">
                  <VALUE>{delta_time}</VALUE>
                </PROPERTY>
              </INSTANCE>
            </EXPPARAMVALUE>
          </EXPMETHODCALL>
        </SIMPLEEXPREQ>
      </MESSAGE>
    </CIM>"""

    return data_template.format(
        sequence_number=sequence_number, delta_time=delta_time,
        protocol_ver=protocol_ver, msg_id=msg_id)


# Verbosity in test_WBEMListener_send_indications()
VERBOSE_DETAILS = False  # Show indications sent and received
VERBOSE_SUMMARY = False  # Show summary for each run

# Global variables used to communicate between the test case function and
# the process_indication() function running in context of the listener
# thread. These must be global, because in Python 2, closure variables
# cannot be modified.
RCV_COUNT = 0
RCV_ERRORS = False


def process_indication(indication, host):
    """
    This function gets called by the listener when an indication is
    received.

    It tests the received indication sequence number against the RCV_COUNT
    which should catch any duplicated or missing indication, since the
    counters would no longer match in such cases.

    This function is invoked in context of the listener thread. Therefore,
    it is defined as a local function in order to be able to use the
    variables from its outer function, specifically the RCV_COUNT and
    RCV_ERRORS variables.

    For the same reason, this function does not report assertion failures
    by means of raising exceptions, but by printing a message and setting
    RCV_ERRORS to an error message, so the test function can check it and
    raise assertion errors.
    """

    # Note: Global variables that are modified must be declared global
    global RCV_COUNT  # pylint: disable=global-statement
    global RCV_ERRORS  # pylint: disable=global-statement

    try:
        if VERBOSE_DETAILS:
            print("\nListener received indication with:")
            print("  host={}".format(host))
            print("  indication(as MOF)={}".
                  format(indication.tomof().strip('\n')))
            sys.stdout.flush()

        send_count = int(indication.properties['SequenceNumber'].value)
        if send_count != RCV_COUNT:
            print("Error in process_indication(): Assertion error: "
                  "Unexpected SequenceNumber in received indication: "
                  "got {}, expected {}".format(send_count, RCV_COUNT))
            sys.stdout.flush()
            RCV_ERRORS = True

        RCV_COUNT += 1

    except Exception as exc:  # pylint: disable=broad-except
        print("Error in process_indication(): {}: {}".
              format(exc.__class__.__name__, exc))
        sys.stdout.flush()
        RCV_ERRORS = True


@pytest.mark.parametrize(
    "send_count",
    [1, 10, 100]  # 1000 in some environments takes 30 min
)
def test_WBEMListener_send_indications(send_count):
    """
    Test WBEMListener with an indication generator.

    This test sends the number of indications defined by the send_count
    parameter using HTTP. It confirms that they are all received by the
    listener.

    This test validates the main paths of the listener and that the listener can
    receive large numbers of indications without duplicates or dropping
    indications.

    It does not validate all of the possible xml options on indications.

    Creates the listener, starts the listener, creates the indication XML and
    adds sequence number and time to the indication instance and sends that
    instance using requests.

    The indication instance is modified for each indication count so that each
    carries its own sequence number.
    """

    # Note: Global variables that are modified must be declared global
    global RCV_COUNT  # pylint: disable=global-statement
    global RCV_ERRORS  # pylint: disable=global-statement

    host = 'localhost'
    http_port = 50000

    logging.basicConfig(stream=sys.stderr, level=logging.WARNING,
                        format='%(levelname)s: %(message)s')

    listener = WBEMListener(host, http_port)
    listener.add_callback(process_indication)
    listener.start()

    try:

        start_time = time()
        url = 'http://{}:{}'.format(host, http_port)
        cim_protocol_version = '1.4'
        headers = {
            'Content-Type': 'application/xml; charset=utf-8',
            'CIMExport': 'MethodRequest',
            'CIMExportMethod': 'ExportIndication',
            'Accept-Encoding': 'Identity',
            'CIMProtocolVersion': cim_protocol_version,
        }
        # We include Accept-Encoding because of requests issue.
        # He supplies it if we don't.  TODO try None

        delta_time = time() - start_time
        random_base = randint(1, 10000)
        timer = ElapsedTimer()

        RCV_COUNT = 0
        RCV_ERRORS = False

        for i in range(send_count):

            msg_id = random_base + i
            payload = create_indication_data(msg_id, i, delta_time,
                                             cim_protocol_version)

            if VERBOSE_DETAILS:
                print("\nTestcase sending indication #{} with:".format(i))
                print("  url={}".format(url))
                print("  headers={}".format(headers))
                print("  payload={}".format(payload))
                sys.stdout.flush()

            response = requests.post(url, headers=headers, data=payload,
                                     timeout=4)

            if VERBOSE_DETAILS:
                print("\nTestcase received response from sending indication:")
                print("  status_code={}".format(response.status_code))
                print("  headers={}".format(response.headers))
                print("  payload={}".format(response.text))
                sys.stdout.flush()

            if response.status_code != 200:
                raise AssertionError(
                    "Sending the indication failed with HTTP status {}: "
                    "response={!r}".format(response.status_code, response))

            if VERBOSE_DETAILS:
                print("\nTestcase done sending indication #{}".format(i))
                sys.stdout.flush()

        endtime = timer.elapsed_sec()

        # Make sure the listener thread has processed all indications
        sleep(1)

        if VERBOSE_SUMMARY:
            print("\nSent {} indications in {} sec or {:.2f} ind/sec".
                  format(send_count, endtime, (send_count / endtime)))
            sys.stdout.flush()

        assert not RCV_ERRORS, \
            "Errors occurred in process_indication(), as printed to stdout"

        assert send_count == RCV_COUNT, \
            "Mismatch between total send count {} and receive count {}". \
            format(send_count, RCV_COUNT)

    finally:
        listener.stop()


@pytest.mark.parametrize(
    "method, exp_status", [
        ('OPTIONS', 405),
        ('HEAD', 405),
        ('GET', 405),
        ('PUT', 405),
        ('PATCH', 405),
        ('DELETE', 405),
        ('TRACE', 405),
        ('CONNECT', 405),
        ('M_POST', 405),
    ])
def test_WBEMListener_incorrect_method(method, exp_status):
    """
    Verify that WBEMListener send fails when an incorrect HTTP method is used.
    """

    host = 'localhost'
    http_port = 50000
    url = 'http://{}:{}'.format(host, http_port)
    headers = {
        'Content-Type': 'application/xml; charset=utf-8',
        'CIMExport': 'MethodRequest',
        'CIMExportMethod': 'ExportIndication',
        'Accept-Encoding': 'Identity',
        'CIMProtocolVersion': '1.4',
    }

    listener = WBEMListener(host, http_port)
    listener.add_callback(process_indication)
    listener.start()

    try:

        # The code to be tested is running in listener thread
        response = requests.request(method, url, headers=headers, timeout=4)

        assert response.status_code == exp_status

    finally:
        listener.stop()


WBEMLISTENER_INCORRECT_HEADERS_TESTCASES = [
    (
        "Invalid Accept-Charset header",
        {
            'Content-Type': 'application/xml',
            'Accept-Charset': 'ASCII',
            'CIMExport': 'MethodRequest',
            'CIMExportMethod': 'ExportIndication',
            'Accept-Encoding': 'Identity',
            'CIMProtocolVersion': '1.4',
        },
        406,
        {
            'CIMErrorDetails': r'Invalid Accept-Charset header .*',
            'CIMError': r'header-mismatch',
            'CIMExport': r'MethodResponse',
        }
    ),
    (
        "Invalid Accept-Encoding header",
        {
            'Content-Type': 'application/xml',
            'CIMExport': 'MethodRequest',
            'CIMExportMethod': 'ExportIndication',
            'Accept-Encoding': 'foo',
            'CIMProtocolVersion': '1.4',
        },
        406,
        {
            'CIMErrorDetails': r'Invalid Accept-Encoding header .*',
            'CIMError': r'header-mismatch',
            'CIMExport': r'MethodResponse',
        }
    ),
    (
        "Accept-Range header not permitted",
        {
            'Content-Type': 'application/xml',
            'Accept-Range': 'foo',
            'CIMExport': 'MethodRequest',
            'CIMExportMethod': 'ExportIndication',
            'Accept-Encoding': 'Identity',
            'CIMProtocolVersion': '1.4',
        },
        406,
        {
            'CIMErrorDetails': r'Accept-Range header is not permitted .*',
            'CIMError': r'header-mismatch',
            'CIMExport': r'MethodResponse',
        }
    ),
    (
        "Missing Content-Type header",
        {
            'CIMExport': 'MethodRequest',
            'CIMExportMethod': 'ExportIndication',
            'Accept-Encoding': 'Identity',
            'CIMProtocolVersion': '1.4',
        },
        406,
        {
            'CIMErrorDetails': r'Content-Type header is required',
            'CIMError': r'header-mismatch',
            'CIMExport': r'MethodResponse',
        }
    ),
    (
        "Invalid Content-Type header",
        {
            'Content-Type': 'foo_application/xml',
            'CIMExport': 'MethodRequest',
            'CIMExportMethod': 'ExportIndication',
            'Accept-Encoding': 'Identity',
            'CIMProtocolVersion': '1.4',
        },
        406,
        {
            'CIMErrorDetails': r'Invalid Content-Type header .*',
            'CIMError': r'header-mismatch',
            'CIMExport': r'MethodResponse',
        }
    ),
    (
        "Invalid Content-Encoding header",
        {
            'Content-Type': 'application/xml',
            'Content-Encoding': 'foo',
            'CIMExport': 'MethodRequest',
            'CIMExportMethod': 'ExportIndication',
            'Accept-Encoding': 'Identity',
            'CIMProtocolVersion': '1.4',
        },
        406,
        {
            'CIMErrorDetails': r'Invalid Content-Encoding header .*',
            'CIMError': r'header-mismatch',
            'CIMExport': r'MethodResponse',
        }
    ),
]


@pytest.mark.parametrize(
    "desc, headers, exp_status, exp_headers",
    WBEMLISTENER_INCORRECT_HEADERS_TESTCASES)
def test_WBEMListener_incorrect_headers(desc, headers, exp_status, exp_headers):
    # pylint: disable=unused-argument
    """
    Verify that WBEMListener send fails when incorrect HTTP headers are used
    (along with the correct POST method).
    """

    host = 'localhost'
    http_port = 50000
    url = 'http://{}:{}'.format(host, http_port)
    # headers = copy(headers)

    listener = WBEMListener(host, http_port)
    listener.add_callback(process_indication)
    listener.start()

    try:

        # The code to be tested is running in listener thread
        response = requests.post(url, headers=headers, timeout=4)

        assert response.status_code == exp_status
        for header_name in exp_headers:
            assert header_name in response.headers
            exp_header_pattern = exp_headers[header_name]
            assert re.match(exp_header_pattern, response.headers[header_name])

    finally:
        listener.stop()


WBEMLISTENER_INCORRECT_PAYLOAD1_TESTCASES = [
    (
        "Ill-formed XML in payload",
        """<?xml version="1.0" encoding="utf-8" ?>
        <CIM CIMVERSION="2.0" DTDVERSION="2.4">""",
        400,
        {
            'CIMErrorDetails': r'XML parsing error .*',
            'CIMError': r'request-not-well-formed',
            'CIMExport': r'MethodResponse',
        }
    ),
    (
        "Unsupported DTD version (DTDVERSION in CIM element)",
        """<?xml version="1.0" encoding="utf-8" ?>
        <CIM CIMVERSION="2.0" DTDVERSION="1.4">
          <MESSAGE ID="42" PROTOCOLVERSION="1.4">
            <SIMPLEEXPREQ>
              <EXPMETHODCALL NAME="ExportIndication">
              </EXPMETHODCALL>
            </SIMPLEEXPREQ>
          </MESSAGE>
        </CIM>""",
        400,
        {
            'CIMErrorDetails': r'DTD version 1.4 not supported.*',
            'CIMError': r'unsupported-dtd-version',
            'CIMExport': r'MethodResponse',
        }
    ),
    (
        "Unsupported protocol version (PROTOCOLVERSION in MESSAGE element)",
        """<?xml version="1.0" encoding="utf-8" ?>
        <CIM CIMVERSION="2.0" DTDVERSION="2.4">
          <MESSAGE ID="42" PROTOCOLVERSION="2.4">
            <SIMPLEEXPREQ>
              <EXPMETHODCALL NAME="ExportIndication">
              </EXPMETHODCALL>
            </SIMPLEEXPREQ>
          </MESSAGE>
        </CIM>""",
        400,
        {
            'CIMErrorDetails': r'Protocol version 2.4 not supported.*',
            'CIMError': r'unsupported-protocol-version',
            'CIMExport': r'MethodResponse',
        }
    ),
    (
        "CIM-XML: Missing MESSAGE element",
        """<?xml version="1.0" encoding="utf-8" ?>
        <CIM CIMVERSION="2.0" DTDVERSION="2.4">
        </CIM>""",
        400,
        {
            'CIMErrorDetails': r'Element .CIM. missing required '
                               r'child element .*.MESSAGE..*',
            'CIMError': r'request-not-well-formed',
            'CIMExport': r'MethodResponse',
        }
    ),
    (
        "CIM-XML: Missing SIMPLEEXPREQ element",
        """<?xml version="1.0" encoding="utf-8" ?>
        <CIM CIMVERSION="2.0" DTDVERSION="2.4">
          <MESSAGE ID="42" PROTOCOLVERSION="1.4">
          </MESSAGE>
        </CIM>""",
        400,
        {
            'CIMErrorDetails': r'Element .MESSAGE. missing required '
                               r'child element .*.SIMPLEEXPREQ..*',
            'CIMError': r'request-not-well-formed',
            'CIMExport': r'MethodResponse',
        }
    ),
    (
        "CIM-XML: Missing EXPMETHODCALL element",
        """<?xml version="1.0" encoding="utf-8" ?>
        <CIM CIMVERSION="2.0" DTDVERSION="2.4">
          <MESSAGE ID="42" PROTOCOLVERSION="1.4">
            <SIMPLEEXPREQ>
            </SIMPLEEXPREQ>
          </MESSAGE>
        </CIM>""",
        400,
        {
            'CIMErrorDetails': r'Element .SIMPLEEXPREQ. missing required '
                               r'child element .*.EXPMETHODCALL..*',
            'CIMError': r'request-not-well-formed',
            'CIMExport': r'MethodResponse',
        }
    ),
    (
        "CIM-XML: Invalid parameter type in ExportIndication export request",
        """<?xml version="1.0" encoding="utf-8" ?>
        <CIM CIMVERSION="2.0" DTDVERSION="2.4">
          <MESSAGE ID="42" PROTOCOLVERSION="1.4">
            <SIMPLEEXPREQ>
              <EXPMETHODCALL NAME="ExportIndication">
                <EXPPARAMVALUE NAME="NewIndication">
                  <INSTANCENAME CLASSNAME="CIM_AlertIndication">
                  </INSTANCENAME>
                </EXPPARAMVALUE>
              </EXPMETHODCALL>
            </SIMPLEEXPREQ>
          </MESSAGE>
        </CIM>""",
        400,
        {
            'CIMErrorDetails': r'Element .EXPPARAMVALUE. has invalid child '
                               r'element.*INSTANCENAME.*',
            'CIMError': r'request-not-well-formed',
            'CIMExport': r'MethodResponse',
        }
    ),
]


@pytest.mark.parametrize(
    "desc, payload, exp_status, exp_headers",
    WBEMLISTENER_INCORRECT_PAYLOAD1_TESTCASES)
def test_WBEMListener_incorrect_payload1(
        desc, payload, exp_status, exp_headers):
    # pylint: disable=unused-argument
    """
    Verify that WBEMListener send fails with HTTP error when incorrect HTTP
    payload is used that triggers HTTP errors.
    """

    host = 'localhost'
    http_port = 50000
    url = 'http://{}:{}'.format(host, http_port)
    headers = {
        'Content-Type': 'application/xml; charset=utf-8',
        'CIMExport': 'MethodRequest',
        'CIMExportMethod': 'ExportIndication',
        'Accept-Encoding': 'Identity',
        'CIMProtocolVersion': '1.4',
    }

    listener = WBEMListener(host, http_port)
    listener.add_callback(process_indication)
    listener.start()

    try:

        # The code to be tested is running in listener thread
        response = requests.post(url, headers=headers, data=payload, timeout=4)

        assert response.status_code == exp_status
        for header_name in exp_headers:
            assert header_name in response.headers
            exp_header_pattern = exp_headers[header_name]
            assert re.match(exp_header_pattern, response.headers[header_name])

    finally:
        listener.stop()


WBEMLISTENER_INCORRECT_PAYLOAD2_TESTCASES = [
    (
        "Unsupported export method in export request",
        """<?xml version="1.0" encoding="utf-8" ?>
        <CIM CIMVERSION="2.0" DTDVERSION="2.4">
          <MESSAGE ID="42" PROTOCOLVERSION="1.4">
            <SIMPLEEXPREQ>
              <EXPMETHODCALL NAME="fooExportIndication">
              </EXPMETHODCALL>
            </SIMPLEEXPREQ>
          </MESSAGE>
        </CIM>""",
        200,
        {
            'CIMExport': r'MethodResponse',
        },
        b'<?xml version="1.0" encoding="utf-8" ?>\n'
        b'<CIM CIMVERSION="2.0" DTDVERSION="2.4">'
        b'<MESSAGE ID="42" PROTOCOLVERSION="1.4">'
        b'<SIMPLEEXPRSP>'
        b'<EXPMETHODRESPONSE NAME="fooExportIndication">'
        b'<ERROR CODE="7" DESCRIPTION="Unknown export method: '
        b'\'fooExportIndication\'"/>'
        b'</EXPMETHODRESPONSE>'
        b'</SIMPLEEXPRSP>'
        b'</MESSAGE>'
        b'</CIM>'
    ),
    (
        "No parameters in ExportIndication export request",
        """<?xml version="1.0" encoding="utf-8" ?>
        <CIM CIMVERSION="2.0" DTDVERSION="2.4">
          <MESSAGE ID="42" PROTOCOLVERSION="1.4">
            <SIMPLEEXPREQ>
              <EXPMETHODCALL NAME="ExportIndication">
              </EXPMETHODCALL>
            </SIMPLEEXPREQ>
          </MESSAGE>
        </CIM>""",
        200,
        {
            'CIMExport': r'MethodResponse',
        },
        b'<?xml version="1.0" encoding="utf-8" ?>\n'
        b'<CIM CIMVERSION="2.0" DTDVERSION="2.4">'
        b'<MESSAGE ID="42" PROTOCOLVERSION="1.4">'
        b'<SIMPLEEXPRSP>'
        b'<EXPMETHODRESPONSE NAME="ExportIndication">'
        b'<ERROR CODE="7" DESCRIPTION="Expecting one parameter '
        b'NewIndication.*"/>'
        b'</EXPMETHODRESPONSE>'
        b'</SIMPLEEXPRSP>'
        b'</MESSAGE>'
        b'</CIM>'
    ),
    (
        "Two parameters in ExportIndication export request",
        """<?xml version="1.0" encoding="utf-8" ?>
        <CIM CIMVERSION="2.0" DTDVERSION="2.4">
          <MESSAGE ID="42" PROTOCOLVERSION="1.4">
            <SIMPLEEXPREQ>
              <EXPMETHODCALL NAME="ExportIndication">
                <EXPPARAMVALUE NAME="NewIndication">
                  <INSTANCE CLASSNAME="CIM_AlertIndication">
                  </INSTANCE>
                </EXPPARAMVALUE>
                <EXPPARAMVALUE NAME="foo">
                  <INSTANCE CLASSNAME="CIM_AlertIndication">
                  </INSTANCE>
                </EXPPARAMVALUE>
              </EXPMETHODCALL>
            </SIMPLEEXPREQ>
          </MESSAGE>
        </CIM>""",
        200,
        {
            'CIMExport': r'MethodResponse',
        },
        b'<?xml version="1.0" encoding="utf-8" ?>\n'
        b'<CIM CIMVERSION="2.0" DTDVERSION="2.4">'
        b'<MESSAGE ID="42" PROTOCOLVERSION="1.4">'
        b'<SIMPLEEXPRSP>'
        b'<EXPMETHODRESPONSE NAME="ExportIndication">'
        b'<ERROR CODE="7" DESCRIPTION="Expecting one parameter '
        b'NewIndication.*"/>'
        b'</EXPMETHODRESPONSE>'
        b'</SIMPLEEXPRSP>'
        b'</MESSAGE>'
        b'</CIM>'
    ),
    (
        "Invalid parameter name in ExportIndication export request",
        """<?xml version="1.0" encoding="utf-8" ?>
        <CIM CIMVERSION="2.0" DTDVERSION="2.4">
          <MESSAGE ID="42" PROTOCOLVERSION="1.4">
            <SIMPLEEXPREQ>
              <EXPMETHODCALL NAME="ExportIndication">
                <EXPPARAMVALUE NAME="fooNewIndication">
                  <INSTANCE CLASSNAME="CIM_AlertIndication">
                  </INSTANCE>
                </EXPPARAMVALUE>
              </EXPMETHODCALL>
            </SIMPLEEXPREQ>
          </MESSAGE>
        </CIM>""",
        200,
        {
            'CIMExport': r'MethodResponse',
        },
        b'<?xml version="1.0" encoding="utf-8" ?>\n'
        b'<CIM CIMVERSION="2.0" DTDVERSION="2.4">'
        b'<MESSAGE ID="42" PROTOCOLVERSION="1.4">'
        b'<SIMPLEEXPRSP>'
        b'<EXPMETHODRESPONSE NAME="ExportIndication">'
        b'<ERROR CODE="7" DESCRIPTION="Expecting one parameter '
        b'NewIndication.*"/>'
        b'</EXPMETHODRESPONSE>'
        b'</SIMPLEEXPRSP>'
        b'</MESSAGE>'
        b'</CIM>'
    ),
]


@pytest.mark.parametrize(
    "desc, payload, exp_status, exp_headers, exp_payload",
    WBEMLISTENER_INCORRECT_PAYLOAD2_TESTCASES)
def test_WBEMListener_incorrect_payload2(
        desc, payload, exp_status, exp_headers, exp_payload):
    # pylint: disable=unused-argument
    """
    Verify that WBEMListener send fails with export response indicating error
    when incorrect HTTP payload is used that triggers that.
    """

    host = 'localhost'
    http_port = 50000
    url = 'http://{}:{}'.format(host, http_port)
    headers = {
        'Content-Type': 'application/xml; charset=utf-8',
        'CIMExport': 'MethodRequest',
        'CIMExportMethod': 'ExportIndication',
        'Accept-Encoding': 'Identity',
        'CIMProtocolVersion': '1.4',
    }

    listener = WBEMListener(host, http_port)
    listener.add_callback(process_indication)
    listener.start()

    try:

        # The code to be tested is running in listener thread
        response = requests.post(url, headers=headers, data=payload, timeout=4)

        assert response.status_code == exp_status
        for header_name in exp_headers:
            assert header_name in response.headers
            exp_header_pattern = exp_headers[header_name]
            assert re.match(exp_header_pattern, response.headers[header_name])
        act_payload = response.content
        re.match(exp_payload, act_payload, re.MULTILINE)

    finally:
        listener.stop()
