#!/usr/bin/env python

"""Test WBEMListener against an indication generator. This test generates
   a number of indications and confirms that they are all received by the
   listener.

   This test validates the main paths of the listener and that the listener can
   receive large numbers of insdications without duplicates or dropping
   indications.

   It does not validate all of the possible xml options on indications.
"""

from __future__ import absolute_import

import sys
import errno
import logging
from time import time, sleep
import datetime
from random import randint
import pytest
import requests

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import WBEMListener  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name

# Verbosity control:
VERBOSE_SUMMARY = False  # Show summary for each run

RCV_COUNT = 0
RCV_ERRORS = False
LISTENER = None

# Log level to be used. To enable logging, change this constant to the desired
# log level, and add code to set or unset the log level of the root logger
# globally or specifically in each test case.
LOGLEVEL = logging.NOTSET  # NOTSET disables logging

# Name of the log file
LOGFILE = 'test_indicationlistener.log'


def configure_root_logger(logfile):
    """
    Configure the root logger, except for log level
    """
    root_logger = logging.getLogger('')
    hdlr_exists = False
    for hdlr in root_logger.handlers:
        if isinstance(hdlr, logging.FileHandler):
            hdlr_exists = True
    if not hdlr_exists:
        hdlr = logging.FileHandler(logfile)
        hdlr.setFormatter(
            logging.Formatter(
                "%(asctime)s %(thread)s %(name)s %(levelname)s %(message)s"))
        root_logger.addHandler(hdlr)


LOGGER = logging.getLogger('test_indicationlistener')
if LOGLEVEL > logging.NOTSET:
    configure_root_logger(LOGFILE)


class ElapsedTimer(object):
    """
        Set up elapsed time timer. Calculates time between initiation
        and access.
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


def create_indication_data(msg_id, sequence_number, delta_time, protocol_ver):
    """Create a test indication from the template and input attributes"""

    data_template = """<?xml version="1.0" encoding="utf-8" ?>
    <CIM CIMVERSION="2.0" DTDVERSION="2.4">
      <MESSAGE ID="%(msg_id)s" PROTOCOLVERSION="%(protocol_ver)s">
        <SIMPLEEXPREQ>
          <EXPMETHODCALL NAME="ExportIndication">
            <EXPPARAMVALUE NAME="NewIndication">
              <INSTANCE CLASSNAME="CIM_AlertIndication">
                <PROPERTY NAME="Severity" TYPE="string">
                  <VALUE>high</VALUE>
                </PROPERTY>
                <PROPERTY NAME="SequenceNumber" TYPE="string">
                  <VALUE>%(sequence_number)s</VALUE>
                </PROPERTY>
                <PROPERTY NAME="DELTA_TIME" TYPE="string">
                  <VALUE>%(delta_time)s</VALUE>
                </PROPERTY>
              </INSTANCE>
            </EXPPARAMVALUE>
          </EXPMETHODCALL>
        </SIMPLEEXPREQ>
      </MESSAGE>
    </CIM>"""

    data = {'sequence_number': sequence_number, 'delta_time': delta_time,
            'protocol_ver': protocol_ver, 'msg_id': msg_id}
    return data_template % data


def _process_indication(indication, host):
    # pylint: disable=unused-argument
    """
    This function gets called when an indication is received.
    It receives each indication on a separate thread so the only communication
    with the rest of the program is RCV_COUNT which it increments for each
    received indication

    It tests the received indication sequence number against the RCV_COUNT
    which should catch and indication duplication or missing since the counters
    would no longer match.

    NOTE: Since this is a standalone function, it does not do an assert fail
    if there is a mismatch.
    """

    # Note: Global variables that are modified must be declared global
    global RCV_COUNT  # pylint: disable=global-statement
    global RCV_ERRORS  # pylint: disable=global-statement

    LOGGER.debug(
        "Callback function called for indication #%s: %r",
        RCV_COUNT, indication.classname)

    try:

        send_count = int(indication.properties['SequenceNumber'].value)
        if send_count != RCV_COUNT:
            print("Error in process_indication(): Assertion error: "
                  "Unexpected SequenceNumber in received indication #{}: "
                  "got {}, expected {}".
                  format(RCV_COUNT, send_count, RCV_COUNT))
            sys.stdout.flush()
            RCV_ERRORS = True

        RCV_COUNT += 1

    except Exception as exc:  # pylint: disable=broad-except
        print("Error in process_indication(): {}: {}".
              format(exc.__class__.__name__, exc))
        sys.stdout.flush()
        RCV_ERRORS = True


class TestIndications(object):
    """
    Create a WBEMListener and starts the listener. Note that it resets the
    received indication counter (RCV_COUNT) so that there is an accurate
    count of indications actually received.
    """

    @staticmethod
    def createlistener(host, http_port=None, https_port=None,
                       certfile=None, keyfile=None):
        """
        Create and start a listener based on host, ports, etc.
        """
        global RCV_COUNT  # pylint: disable=global-statement
        global LISTENER  # pylint: disable=global-statement
        global RCV_ERRORS  # pylint: disable=global-statement
        RCV_ERRORS = False  # pylint: disable=global-statement

        RCV_COUNT = 0
        LISTENER = WBEMListener(host=host,
                                http_port=http_port,
                                https_port=https_port,
                                certfile=certfile,
                                keyfile=keyfile)
        LISTENER.add_callback(_process_indication)
        LISTENER.start()

    # pylint: disable=unused-argument
    def send_indications(self, send_count, http_port):
        """
        Send the number of indications defined by the send_count attribute
        using the specified listener HTTP port.

        Creates the listener, starts the listener, creates the
        indication XML and adds sequence number and time to the
        indication instance and sends that instance using requests.
        The indication instance is modified for each indication count so
        that each carries its own sequence number.
        """

        # pylint: disable=global-variable-not-assigned
        global RCV_ERRORS  # pylint: disable=global-statement
        RCV_ERRORS = False
        host = 'localhost'
        try:
            self.createlistener(host, http_port)

            start_time = time()

            full_url = 'http://%s:%s' % (host, http_port)

            cim_protocol_version = '1.4'

            headers = {'content-type': 'application/xml; charset=utf-8',
                       'CIMExport': 'MethodRequest',
                       'CIMExportMethod': 'ExportIndication',
                       'Accept-Encoding': 'Identity',
                       'CIMProtocolVersion': cim_protocol_version}
            # We include accept-encoding because of requests issue.
            # He supplies it if we don't.  TODO try None

            delta_time = time() - start_time
            rand_base = randint(1, 10000)
            timer = ElapsedTimer()
            for i in range(send_count):

                msg_id = '%s' % (i + rand_base)
                payload = create_indication_data(msg_id, i, delta_time,
                                                 cim_protocol_version)

                LOGGER.debug("Testcase sending indication #%s", i)

                try:
                    response = requests.post(
                        full_url, headers=headers, data=payload, timeout=4)
                except requests.exceptions.RequestException as exc:
                    msg = ("Testcase sending indication #{} raised {}: {}".
                           format(i, exc.__class__.__name__, exc))
                    LOGGER.error(msg)
                    new_exc = AssertionError(msg)
                    new_exc.__cause__ = None  # Disable to see original tracebck
                    raise new_exc

                LOGGER.debug("Testcase received response from sending "
                             "indication #%s", i)

                if response.status_code != 200:
                    msg = ("Testcase sending indication #{} failed with HTTP "
                           "status {}".format(i, response.status_code))
                    LOGGER.error(msg)
                    raise AssertionError(msg)

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
            LISTENER.stop()

    @pytest.mark.parametrize(
        "send_count",
        [10, 100]  # 1000 in some environments takes 30 min
    )
    def test_send(self, send_count):
        """Test with sending N indications"""

        # Enable logging for this test function
        if LOGLEVEL > logging.NOTSET:
            logging.getLogger('').setLevel(LOGLEVEL)

        self.send_indications(send_count, 50000)

        # Disable logging for this test function
        if LOGLEVEL > logging.NOTSET:
            logging.getLogger('').setLevel(logging.NOTSET)

    def test_attrs(self):
        # pylint: disable=no-self-use
        """
        Test WBEMListener attributes.
        """

        host = 'localhost'
        http_port = '50000'  # as a string
        exp_http_port = 50000  # as an integer

        listener = WBEMListener(host, http_port)
        assert listener.host == host
        assert listener.http_port == exp_http_port
        assert listener.https_port is None
        assert listener.certfile is None
        assert listener.keyfile is None
        assert isinstance(listener.logger, logging.Logger)
        assert listener.http_started is False
        assert listener.https_started is False

    def test_start_stop(self):
        # pylint: disable=no-self-use
        """
        Test starting and stopping of the the listener.
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

    def test_port_in_use(self):
        # pylint: disable=no-self-use
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

    def test_context_mgr(self):
        # pylint: disable=no-self-use
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
