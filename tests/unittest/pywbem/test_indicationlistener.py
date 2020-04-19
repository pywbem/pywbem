#!/usr/bin/env python

"""
Test _listener.py module.
"""

from __future__ import absolute_import

import sys
import errno
import re
import logging
from time import time
import datetime
from random import randint
import requests
import pytest

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
from ..utils.pytest_extensions import simplified_test_function
pywbem = import_installed('pywbem')  # noqa: E402
from pywbem import WBEMListener
from pywbem._utils import _format
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
    r = repr(obj)

    assert re.match(r'^WBEMListener\(', r)

    exp_host_str = _format('_host={0!A}', obj.host)
    assert exp_host_str in r

    exp_http_port_str = _format('_http_port={0!A}', obj.http_port)
    assert exp_http_port_str in r

    exp_https_port_str = _format('_https_port={0!A}', obj.https_port)
    assert exp_https_port_str in r

    exp_certfile_str = _format('_certfile={0!A}', obj.certfile)
    assert exp_certfile_str in r

    exp_keyfile_str = _format('_keyfile={0!A}', obj.keyfile)
    assert exp_keyfile_str in r

    exp_logger_str = _format('_logger={0!A}', obj.logger)
    assert exp_logger_str in r


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


# Verbosity in test_WBEMListener_send_indications()
VERBOSE_DETAILS = False  # Show indications sent and received
VERBOSE_SUMMARY = False  # Show summary for each run

# Global variables used in test_WBEMListener_send_indications()
# to communicate between testcase sending the indications and listener thread
# processing the received indications.
RCV_COUNT = 0
RCV_FAIL = False


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


def send_indication(url, headers, payload):
    """
    Send a single indication using Python requests.

    Raises:
      exceptions from request package
      AssertionError: if HTTP response status from sending is not 200
    """

    response = requests.post(url, headers=headers, data=payload, timeout=4)
    #  May raise request exceptions

    if VERBOSE_DETAILS:
        print("\nTestcase received response from sending indication:")
        print("  status_code={}".format(response.status_code))
        print("  headers={}".format(response.headers))
        print("  payload={}".format(response.text))
        sys.stdout.flush()

    if response.status_code != 200:
        raise AssertionError(
            "Sending the indication failed with HTTP status {}: response={!r}".
            format(response.status_code, response))


def process_indication(indication, host):
    """
    This function gets called when an indication is received.
    It receives each indication on a separate thread so the only communication
    with the rest of the program is RCV_COUNT which it increments for each
    received indication

    It tests the received indication sequence number against the RCV_COUNT
    which should catch and indication duplication or missing since the counters
    would no longer match.

    NOTE: Since this function is called in context of the listener thread,
    it does not report assertion failures by means of raising exceptions,
    but by printing a message and setting RCV_FAIL=True.
    """

    global RCV_COUNT  # pylint: disable=global-statement
    global RCV_FAIL  # pylint: disable=global-statement

    counter = indication.properties['SequenceNumber'].value
    if int(counter) != RCV_COUNT:
        RCV_FAIL = True
        print("ERROR in SequenceNumber in received indication: "
              "actual={}, expected={}".format(counter, RCV_COUNT))
        sys.stdout.flush()

    if VERBOSE_DETAILS:
        print("\nListener received indication #{} with:".format(counter))
        print("  host={}".format(host))
        print("  indication(as MOF)={}".format(indication.tomof().strip('\n')))
        sys.stdout.flush()

    RCV_COUNT += 1


@pytest.mark.parametrize(
    "send_count",
    [1, 10, 100]  # Disabled 1000 because in some environments it takes 30min
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

    global RCV_COUNT  # pylint: disable=global-statement
    global RCV_FAIL  # pylint: disable=global-statement

    host = 'localhost'
    http_port = 50000

    logging.basicConfig(stream=sys.stderr, level=logging.WARNING,
                        format='%(levelname)s: %(message)s')

    listener = WBEMListener(host, http_port)
    listener.add_callback(process_indication)
    listener.start()

    try:

        start_time = time()
        full_url = 'http://{}:{}'.format(host, http_port)
        cim_protocol_version = '1.4'
        headers = {'content-type': 'application/xml; charset=utf-8',
                   'CIMExport': 'MethodRequest',
                   'CIMExportMethod': 'ExportIndication',
                   'Accept-Encoding': 'Identity',
                   'CIMProtocolVersion': cim_protocol_version}
        # We include accept-encoding because of requests issue.
        # He supplies it if we don't.  TODO try None

        delta_time = time() - start_time
        random_base = randint(1, 10000)
        timer = ElapsedTimer()

        RCV_FAIL = False
        RCV_COUNT = 0

        for i in range(send_count):

            msg_id = random_base + i
            payload = create_indication_data(msg_id, i, delta_time,
                                             cim_protocol_version)

            if VERBOSE_DETAILS:
                print("\nTestcase sending indication #{} with:".format(i))
                print("  headers={}".format(headers))
                print("  payload={}".format(payload))
                sys.stdout.flush()

            send_indication(full_url, headers, payload)

            if VERBOSE_DETAILS:
                print("\nTestcase done sending indication #{}".format(i))
                sys.stdout.flush()

        endtime = timer.elapsed_sec()

        if VERBOSE_SUMMARY:
            print("\nSent {} indications in {} sec or {:.2f} ind/sec".
                  format(send_count, endtime, (send_count / endtime)))
            sys.stdout.flush()

        assert send_count == RCV_COUNT, \
            "Mismatch between send cound {} and receive count {}". \
            format(send_count, RCV_COUNT)
        assert not RCV_FAIL, "Error detected in received indication"

    finally:
        listener.stop()
