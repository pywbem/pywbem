#!/usr/bin/env python

"""
Test _listener.py module.
"""

import sys
import re
import logging
import threading
from time import time, sleep
from random import randint
try:
    from types import NoneType
except ImportError:
    # On Python <= 3.9
    NoneType = type(None)
import requests
import pytest

from ...utils import post_bsl
from ...elapsed_timer import ElapsedTimer
from ..utils.pytest_extensions import simplified_test_function, \
    log_entry_exit, get_logger

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import WBEMListener, ListenerPortError, \
    ListenerQueueFullError  # noqa: E402
from pywbem._listener import ExceptionHandlingThread, StoppableThread, \
    ServerThread, CallbackThread  # noqa: E402
from pywbem._utils import _format  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name

# Literal form {"blah: 0} faster than dict(blah=0) but same functionality
# pylint: disable=use-dict-literal

# test variables to allow selectively executing tests.
OK = True
RUN = True
FAIL = False

LOGGER = get_logger(__name__)

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
                max_ind_queue_size=9,
            ),
            exp_attrs=dict(
                host='woot.com',
                http_port=6997,
                https_port=6998,
                certfile='certfile.pem',
                keyfile='keyfile.pem',
                max_ind_queue_size=9

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
                max_ind_queue_size=0,
            ),
            exp_attrs=dict(
                host='woot.com',
                http_port=6997,
                https_port=None,
                certfile=None,
                keyfile=None,
                max_ind_queue_size=0,

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
    (
        "Verify use of direct_call argument",
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
    (
        "Verify valid max_ind_queue_size argument",
        dict(
            init_args=[],
            init_kwargs=dict(
                host='woot.com',
                http_port=None,
                https_port=6998,
                certfile='certfile.pem',
                keyfile='keyfile.pem',
                max_ind_queue_size=1000,
            ),
            exp_attrs=dict(
                host='woot.com',
                http_port=None,
                https_port=6998,
                certfile='certfile.pem',
                keyfile='keyfile.pem',
                max_ind_queue_size=1000,

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
    (
        "Verify failure when providing invalid type max_ind_queue_size",
        dict(
            init_args=[],
            init_kwargs=dict(
                host='woot.com',
                http_port=None,
                https_port=None,
                max_ind_queue_size="fred",
            ),
            exp_attrs=None,
        ),
        ValueError, None, True
    ),
    (
        "Verify failure when providing invalid max_ind_queue_size integer",
        dict(
            init_args=[],
            init_kwargs=dict(
                host='woot.com',
                http_port=None,
                https_port=None,
                max_ind_queue_size=-1,
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
@log_entry_exit
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
@log_entry_exit
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
@log_entry_exit
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


@log_entry_exit
def test_WBEMListener_start_stop():
    """
    Test starting and stopping of the listener.
    """

    host = 'localhost'
    http_port = '50000'  # Intentionally string-typed

    listener = WBEMListener(host, http_port)
    assert listener.http_started is False
    assert listener.https_started is False

    try:
        listener.start()
        assert listener.http_started is True
        assert listener.https_started is False

    finally:
        listener.stop()
        assert listener.http_started is False
        assert listener.https_started is False


@log_entry_exit
def test_WBEMListener_port_in_use():
    """
    Test starting the listener when port is in use by another listener.
    """

    host = 'localhost'

    # Don't use this port in other tests, to be on the safe side
    # as far as port reuse is concerned.
    http_port = '50001'  # Intentionally string-typed

    exp_exc_type = ListenerPortError

    listener1 = WBEMListener(host, http_port)
    listener2 = WBEMListener(host, http_port)

    try:
        listener1.start()
        assert listener1.http_started is True

        try:
            # The code to be tested
            listener2.start()

        except Exception as exc:  # pylint: disable=broad-except
            # e.g. on Linux
            assert isinstance(exc, exp_exc_type)
            assert listener2.http_started is False
        else:
            # e.g. on Windows
            assert listener2.http_started is True

        # Verify that in any case, listener1 is still started
        assert listener1.http_started is True

    finally:
        listener1.stop()
        listener2.stop()


@log_entry_exit
def test_WBEMListener_context_mgr():
    """
    Test starting the listener and automatic closing in a context manager.
    """

    host = 'localhost'

    # Don't use this port in other tests, to be on the safe side
    # as far as port reuse is concerned.
    http_port = '50002'  # Intentionally string-typed

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
    try:
        listener2.start()
        assert listener2.http_started is True
    finally:
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


# Verbosity in test_WBEMListener_send_indications(). If True show summary
# information for each test
VERBOSE_SUMMARY = False

# Global variables used to communicate between the test case function and
# the process_indication_callback() function running in context of the listener
# thread. These must be global, because in Python 2, closure variables
# cannot be modified.
RCV_COUNT = 0
RCV_ERRORS = False
CALLBACK_DELAY = 0


def process_indication_callback(indication, host):
    # pylint: disable=unused-argument
    """
    This callback function gets called by the listener when an indication is
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
    # global CALLBACK_DELAY  # delay in first return from callback

    LOGGER.debug(
        "Callback function called for indication number %s: %r",
        RCV_COUNT, indication.classname)

    # Delay the callback execution. This is set if the test is
    # defined to test for full queue and fail.  It delays each callback the
    # numbr of seconds in CALLBACK_DELAY
    if CALLBACK_DELAY:
        sleep(CALLBACK_DELAY)
        LOGGER.debug(
            "Callback delayed rcv_cnt %s:  delay %s sec.",
            RCV_COUNT, CALLBACK_DELAY)  # FUTURE: remove this.

    try:

        send_count = int(indication.properties['SequenceNumber'].value)
        if send_count != RCV_COUNT:
            print("Error in process_indication_callback(): Assertion error: "
                  "Unexpected SequenceNumber in received indication: "
                  f"got {send_count}, expected {RCV_COUNT}")
            sys.stdout.flush()
            RCV_ERRORS = True

        RCV_COUNT += 1

    except Exception as exc:  # pylint: disable=broad-except
        print(f"Error in process_indication_callback(): "
              f"{exc.__class__.__name__}: {exc}")
        sys.stdout.flush()
        LOGGER.debug(
            "Error in process_indication_callback() %s: %s",
            exc.__class__.__name__, exc)
        RCV_ERRORS = True


WBEMLISTENER_SEND_INDICATIONS_TESTCASES = [
    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * send_count: CIMInstanceName object to be tested.
    #   * max_queue: Max size of queue argument.
    #   * exp_success: Boolan, True if successful completion expected. If
    #     exception expected, set False
    #   * callback_delay - number that defines delay (seconds)) in first
    #     callback execution. Required for tests of queue full.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger
    (
        "Send 1 indication",
        {
            'send_count': 1,
            'max_queue': 0,
            'exp_success': True,
            'callback_delay': 0,
        },
        None, None, OK
    ),
    (
        "Send 10 indications",
        {
            'send_count': 10,
            'max_queue': 0,
            'exp_success': True,
            'callback_delay': 2,

        },
        None, None, OK
    ),
    (
        "Send 100 indications",
        {
            'send_count': 100,
            'max_queue': 0,
            'exp_success': True,
            'callback_delay': 0,

        },
        None, None, OK
    ),
    (
        "Test queue full. Send 5 indications but fail at number 2",
        {
            'send_count': 5,
            'max_queue': 2,
            'exp_success': False,
            'callback_delay': 1,

        },
        None, None, OK
    ),
    (
        "Test queue full. Send 100 indications Full = 200, no fail",
        {
            'send_count': 100,
            'max_queue': 190,
            'exp_success': True,
            'callback_delay': 1,

        },
        None, None, OK
    ),
    (
        "Test queue full. Send 5 indications full=6. No fail",
        {
            'send_count': 5,
            'max_queue': 6,
            'exp_success': False,
            'callback_delay': 1,

        },
        None, None, OK
    ),
    (
        "Test queue full. Send 100 indications, full = 90 but fail at 90",
        {
            'send_count': 100,
            'max_queue': 90,
            'exp_success': False,
            'callback_delay': 1,

        },
        None, None, OK
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    WBEMLISTENER_SEND_INDICATIONS_TESTCASES)
@simplified_test_function
@log_entry_exit
def test_WBEMListener_send_indications(
        testcase, send_count, max_queue, exp_success, callback_delay):
    """
    Test WBEMListener with an indication generator.

    This test sends the number of indications defined by the send_count
    parameter using HTTP. It confirms that they are all received by the
    listener.

    This test validates the main paths of the listener and that the listener
    can receive large numbers of indications without duplicates or dropping
    indications.

    The test generates the indications itself and does not depend on a
    WBEM Server.  Tests in tests/end2end test with indications from
    a WBEM server.

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
    global CALLBACK_DELAY  # pylint: disable=global-statement

    CALLBACK_DELAY = callback_delay

    # Fixes issue #528 where on Windows, localhost adds multisecond delay
    # probably due to hosts table or DNS misconfiguration.
    if sys.platform == 'win32':
        host = '127.0.0.1'
    else:
        host = 'localhost'
    http_port = 50000

    listener = WBEMListener(host, http_port, max_ind_queue_size=max_queue)
    listener.add_callback(process_indication_callback)

    timer = ElapsedTimer()
    stop_indication_sender = False

    try:
        listener.start()
        start_time = time()
        url = f'http://{host}:{http_port}'
        cim_protocol_version = '1.4'
        headers = {
            'Content-Type': 'application/xml; charset=utf-8',
            'CIMExport': 'MethodRequest',
            'CIMExportMethod': 'ExportIndication',
            'Accept-Encoding': 'Identity',
            'CIMProtocolVersion': cim_protocol_version,
        }
        # We include Accept-Encoding because of requests issue.
        # He supplies it if we don't.  TODO: try None

        delta_time = time() - start_time
        random_base = randint(1, 10000)

        RCV_COUNT = 0
        RCV_ERRORS = False
        LOGGER.debug("Sending %s indications", send_count)
        for i in range(send_count):

            if stop_indication_sender:
                LOGGER.debug(
                    "Will stop sending sending indications at number %s", i)
                break

            msg_id = random_base + i
            payload = create_indication_data(msg_id, i, delta_time,
                                             cim_protocol_version)

            LOGGER.debug("Sending indication number %s", i)

            try:
                response = post_bsl(url, headers=headers, data=payload)
            except requests.exceptions.RequestException as exc:
                msg = (f"Sending indication {i} "
                       f"raised {exc.__class__.__name__}: {exc}")
                LOGGER.error(msg)
                # If testing for fail with max_queue, stop sending if
                # exception from sender and do not execute AssertionError
                if max_queue and i >= max_queue:
                    LOGGER.debug("Stop sending indications at number %s: "
                                 "max_queue_size=%s", i, max_queue)
                    break

                new_exec = AssertionError(msg)
                # Disable to see original traceback
                new_exec.__cause__ = None
                raise new_exec

            LOGGER.debug(
                "Received response from sending indication number %s", i)

            if response.status_code != 200:
                msg = (f"Sending indication {i} failed with HTTP "
                       f"status {response.status_code}")
                LOGGER.error(msg)
                # Ignore error if testing for queue full error
                if not stop_indication_sender:
                    raise AssertionError(msg)

        # Indications sent.
        # Confirm that the listener thread has processed all indications. Waits
        # for indication queue to empty.
        # Cancel any callback delays so callbacks just clear queue.
        CALLBACK_DELAY = 0

        # max seconds to wait for queue to empty
        # NOTE: This does not have any short circuit if the callback processor
        # hangs up and does not finish.  It just runs out the timer.
        queue_empty_retries = max((send_count * 5), 30)

        # Wait loop to allow receive queue to empty.
        empty = False
        for i in range(queue_empty_retries):
            sleep(0.2)   # sleep 200 ms to allow callbacks to execute
            if listener.ind_queue_exists():
                qsize = listener.ind_queue_size()
                empty = listener.ind_queue_empty()
            else:
                qsize = None
                empty = None
            LOGGER.debug(
                "Waiting for empty or deinitialized queue: qsize=%s empty=%s "
                "retries=%s", qsize, empty, i)
            if empty is None or empty is True:
                LOGGER.debug("Break from wait loop.")
                break

            LOGGER.debug("Waiting, %s still in queue.",
                         listener.ind_queue_size())

        assert empty is None or empty is True, \
            f"Test failed in wait for indications loop. rcv_count=" \
            f"{RCV_COUNT} still in queue={qsize}"

        # Test for receive error, and correct receive count
        # Ignore rcvd count asserts if exp_success is False.
        if exp_success:
            assert not RCV_ERRORS, \
                f"Errors occurred in process_indication_callback(), as " \
                f" printed to stdout. testcase={testcase}."

            assert send_count == RCV_COUNT, \
                f"Mismatch between total send count {send_count} and " \
                f" receive count {RCV_COUNT}. testcase={testcase}."

    except ListenerQueueFullError as qfe:
        if exp_success:
            LOGGER.debug("ListenerQueueFullError received: %s", qfe)
            assert False, "Unexpxpected ListenerQueueFullError. Test Fail"
        else:
            LOGGER.debug("Expected and received ListenerQueueFullError")
            stop_indication_sender = True
            listener.stop()
            LOGGER.debug("Testcase fail expected result OK, listener closed.")

    finally:

        LOGGER.debug("Start listener.stop")
        listener.stop()
        LOGGER.debug("End listener.stop")

        endtime = timer.elapsed_sec()
        ind_per_sec = send_count / endtime

        msg = (f"SUMMARY: Sent {send_count} indications in {endtime:.2f} sec; "
               f"{ind_per_sec:.2f} ind/sec")

        LOGGER.info(msg)

        if VERBOSE_SUMMARY:
            print(f"\n{msg}")
            sys.stdout.flush()

        # Test that only the main thread exists.
        assert threading.active_count() == 1


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
@log_entry_exit
def test_WBEMListener_incorrect_method(method, exp_status):
    """
    Verify that WBEMListener send fails when an incorrect HTTP method is used.
    """

    host = 'localhost'
    http_port = 50000
    url = f'http://{host}:{http_port}'
    headers = {
        'Content-Type': 'application/xml; charset=utf-8',
        'CIMExport': 'MethodRequest',
        'CIMExportMethod': 'ExportIndication',
        'Accept-Encoding': 'Identity',
        'CIMProtocolVersion': '1.4',
    }

    listener = WBEMListener(host, http_port)

    try:
        listener.add_callback(process_indication_callback)
        listener.start()

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
@log_entry_exit
def test_WBEMListener_incorrect_headers(desc, headers, exp_status, exp_headers):
    # pylint: disable=unused-argument
    """
    Verify that WBEMListener send fails when incorrect HTTP headers are used
    (along with the correct POST method).
    """

    host = 'localhost'
    http_port = 50000
    url = f'http://{host}:{http_port}'
    # headers = copy(headers)

    listener = WBEMListener(host, http_port)

    try:
        listener.add_callback(process_indication_callback)
        listener.start()

        # The code to be tested is running in listener thread
        response = post_bsl(url, headers=headers, data=None)

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
            'CIMErrorDetails': r'DTDVERSION is 1.4, expected 2.x.y',
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
            'CIMErrorDetails': r'PROTOCOLVERSION is 2.4, expected 1.x.y',
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
            'CIMErrorDetails': r'Element .CIM. is missing required '
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
            'CIMErrorDetails': r'Element .MESSAGE. is missing required '
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
            'CIMErrorDetails': r'Element .SIMPLEEXPREQ. is missing required '
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
@log_entry_exit
def test_WBEMListener_incorrect_payload1(
        desc, payload, exp_status, exp_headers):
    # pylint: disable=unused-argument
    """
    Verify that WBEMListener send fails with HTTP error when incorrect HTTP
    payload is used that triggers HTTP errors.
    """

    host = 'localhost'
    http_port = 50000
    url = f'http://{host}:{http_port}'
    headers = {
        'Content-Type': 'application/xml; charset=utf-8',
        'CIMExport': 'MethodRequest',
        'CIMExportMethod': 'ExportIndication',
        'Accept-Encoding': 'Identity',
        'CIMProtocolVersion': '1.4',
    }

    listener = WBEMListener(host, http_port)

    try:
        listener.add_callback(process_indication_callback)
        listener.start()

        # The code to be tested is running in listener thread
        response = post_bsl(url, headers=headers, data=payload)

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
@log_entry_exit
def test_WBEMListener_incorrect_payload2(
        desc, payload, exp_status, exp_headers, exp_payload):
    # pylint: disable=unused-argument
    """
    Verify that WBEMListener send fails with export response indicating error
    when incorrect HTTP payload is used that triggers that.
    """

    host = 'localhost'
    http_port = 50000
    url = f'http://{host}:{http_port}'
    headers = {
        'Content-Type': 'application/xml; charset=utf-8',
        'CIMExport': 'MethodRequest',
        'CIMExportMethod': 'ExportIndication',
        'Accept-Encoding': 'Identity',
        'CIMProtocolVersion': '1.4',
    }

    listener = WBEMListener(host, http_port)

    try:
        listener.add_callback(process_indication_callback)
        listener.start()

        # The code to be tested is running in listener thread
        response = post_bsl(url, headers=headers, data=payload)

        assert response.status_code == exp_status
        for header_name in exp_headers:
            assert header_name in response.headers
            exp_header_pattern = exp_headers[header_name]
            assert re.match(exp_header_pattern, response.headers[header_name])
        act_payload = response.content
        re.match(exp_payload, act_payload, re.MULTILINE)

    finally:
        listener.stop()


# Attribute value in testcase definition indicating not to compare the value
NOCHECK_VALUE = -999

THREAD_INIT_TESTCASES = [
    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * thread_class: Thread class to be tested.
    # * kwargs: Keyword arguments for the Thread class init.
    # * exp_attrs: Expected attributes.
    #   Key: Attribute name. Value: tuple(type, value). value can be
    #   NOCHECK_VALUE to indicate not to check the value.

    (
        "ExceptionHandlingThread",
        ExceptionHandlingThread,
        dict(
            target=None,
            name='foo',
        ),
        dict(
            name=(str, 'foo'),
            exception=(NoneType, None),
        )
    ),
    (
        "StoppableThread",
        StoppableThread,
        dict(
            target=None,
            name='foo',
        ),
        dict(
            name=(str, 'foo'),
            stop_event=(threading.Event, NOCHECK_VALUE),
        )
    ),
    (
        "ServerThread",
        ServerThread,
        dict(
            target=None,
            name='foo',
        ),
        dict(
            name=(str, 'foo'),
            exception=(NoneType, None),
        )
    ),
    (
        "CallbackThread",
        CallbackThread,
        dict(
            target=None,
            name='foo',
        ),
        dict(
            name=(str, 'foo'),
            exception=(NoneType, None),
            stop_event=(threading.Event, NOCHECK_VALUE),
        )
    ),
]


@pytest.mark.parametrize(
    "desc, thread_class, kwargs, exp_attrs",
    THREAD_INIT_TESTCASES)
def test_thread_init(
        desc, thread_class, kwargs, exp_attrs):
    # pylint: disable=unused-argument
    """
    Verify that the thread class shows the expected attributes after init.
    """

    # The code to be tested
    thread = thread_class(**kwargs)

    for name, exp_type_value in exp_attrs.items():
        exp_type, exp_value = exp_type_value
        assert hasattr(thread, name)
        value = getattr(thread, name)
        # pylint: disable=unidiomatic-typecheck)
        assert type(value) == exp_type  # noqa: E721
        if exp_value != NOCHECK_VALUE:
            assert value == exp_value


class StoppableThreadFuncHolder:
    # pylint: disable=too-few-public-methods
    """
    Test support class providing the thread function, that solves the problem
    for the thread function to access the thread to check for the stop
    condition.
    """

    def __init__(self):
        self.thread = None

    def thread_func(self, interval):
        """
        Thread function that regularly checks the thread whether to stop.
        """
        LOGGER.debug("thread_func: Called with interval=%.2f", interval)
        assert self.thread is not None
        while True:
            if self.thread.stopped():
                break
            LOGGER.debug("thread_func: Sleeping for %.2f s", interval)
            sleep(interval)
        LOGGER.debug("thread_func: Returning")


@pytest.mark.parametrize(
    "thread_class",
    [
        StoppableThread,
        CallbackThread,  # derived from StoppableThread
    ]
)
def test_thread_stoppable(thread_class):
    """
    Verify that a StoppableThread is stoppable.
    """
    assert issubclass(thread_class, StoppableThread)

    LOGGER.debug("test_thread_stoppable: Test function called with "
                 "thread_class=%r", thread_class)

    func_holder = StoppableThreadFuncHolder()
    thread_interval = 0.1

    # Create a thread as a daemon thread. This will cause it to be cleaned up
    # when the Python process running pytest terminates.
    thread = thread_class(
        target=func_holder.thread_func,
        kwargs=dict(interval=thread_interval),
        name='foo',
        daemon=True)
    func_holder.thread = thread

    LOGGER.debug("test_thread_stoppable: Starting thread")
    thread.start()

    sleep_time = 3 * thread_interval
    LOGGER.debug("test_thread_stoppable: Sleeping for %.2f s", sleep_time)
    sleep(sleep_time)

    LOGGER.debug("test_thread_stoppable: Stopping thread")
    # The code to be tested
    thread.stop()

    # The code to be tested
    stopped_result = thread.stopped()

    # Verify that stop() has been attempted
    assert stopped_result is True

    # Wait for thread to end
    join_timeout = 2 * sleep_time
    LOGGER.debug("test_thread_stoppable: Waiting for thread to end within "
                 "%.2f s", join_timeout)
    thread.join(join_timeout)

    # Verify that the thread no longer exists
    assert not thread.is_alive()
    LOGGER.debug("test_thread_stoppable: As expected, the thread ended")

    LOGGER.debug("test_thread_stoppable: Test function finished")


class ExcHdlThreadFuncHolder:
    # pylint: disable=too-few-public-methods
    """
    Test support class providing the thread function, that solves the problem
    for the thread function to access the thread to check for the stop
    condition.
    """

    def __init__(self):
        self.thread = None

    def thread_func(self, exc):
        """
        Thread function that raises an exception.
        """
        LOGGER.debug("thread_func: Called with exc=%r", exc)
        assert self.thread is not None

        if exc:
            LOGGER.debug("thread_func: Raising exception %r", exc)
            raise exc

        LOGGER.debug("thread_func: Returning without raising exception")


@pytest.mark.parametrize(
    "exc",
    [
        ValueError("foobar"),
        None,
    ]
)
@pytest.mark.parametrize(
    "thread_class",
    [
        ExceptionHandlingThread,
        ServerThread,  # derived from ExceptionHandlingThread
        CallbackThread,  # derived from ExceptionHandlingThread
    ]
)
def test_thread_exchdl(thread_class, exc):
    """
    Verify that a ExceptionHandlingThread handles exceptions.
    """
    assert issubclass(thread_class, ExceptionHandlingThread)

    LOGGER.debug("test_thread_exchdl: Test function called with "
                 "thread_class=%r, exc=%r", thread_class, exc)

    func_holder = ExcHdlThreadFuncHolder()

    # Create a thread as a daemon thread. This will cause it to be cleaned up
    # when the Python process running pytest terminates.
    thread = thread_class(
        target=func_holder.thread_func,
        kwargs=dict(exc=exc),
        name='foo',
        daemon=True)
    func_holder.thread = thread

    LOGGER.debug("test_thread_exchdl: Starting thread")
    thread.start()

    # Wait for thread to end
    join_timeout = 5
    LOGGER.debug("test_thread_exchdl: Waiting for thread to end within "
                 "%.2f s", join_timeout)

    if exc:

        # Verify that join() raises the specified exception
        with pytest.raises(type(exc)) as exc_info:
            thread.join(join_timeout)
        act_exc = exc_info.value
        assert act_exc == exc
        LOGGER.debug("test_thread_exchdl: As expected, thread.join() raised "
                     "exception %r", exc)

    else:

        # Verify that join() does not raise any exception
        thread.join(join_timeout)
        LOGGER.debug("test_thread_exchdl: As expected, thread.join() did not "
                     "raise an exception")

    # Verify that the thread no longer exists
    assert not thread.is_alive()
    LOGGER.debug("test_thread_exchdl: As expected, the thread ended")

    # Verify that the thread has stored the exception
    assert thread.exception is exc

    LOGGER.debug("test_thread_exchdl: Test function finished")
