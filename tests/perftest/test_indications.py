#!/usr/bin/env python

"""
Measure performance of sending indications to the pywbem listener.
"""

from __future__ import absolute_import

import sys
from time import sleep
import statistics
import requests
import pytest

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ..utils import import_installed, post_bsl
from ..elapsed_timer import ElapsedTimer
pywbem = import_installed('pywbem')
from pywbem import WBEMListener  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


def create_indication_data(msg_id, sequence_number, protocol_ver):
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
              </INSTANCE>
            </EXPPARAMVALUE>
          </EXPMETHODCALL>
        </SIMPLEEXPREQ>
      </MESSAGE>
    </CIM>"""

    return data_template.format(
        sequence_number=sequence_number,
        protocol_ver=protocol_ver, msg_id=msg_id)


# Global variables used to communicate between the test case function and
# the process_indication() function running in context of the listener
# thread. These must be global, because in Python 2, closure variables
# cannot be modified.
RCV_COUNT = 0
RCV_ERRORS = False


def process_indication(indication, host):
    # pylint: disable=unused-argument
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


def send_indications(host, http_port, send_count):
    """
    Send a number of indications and return the elapsed time for that.
    """

    # Note: Global variables that are modified must be declared global
    global RCV_COUNT  # pylint: disable=global-statement
    global RCV_ERRORS  # pylint: disable=global-statement

    url = 'http://{}:{}'.format(host, http_port)
    cim_protocol_version = '1.4'
    headers = {
        'Content-Type': 'application/xml; charset=utf-8',
        'CIMExport': 'MethodRequest',
        'CIMExportMethod': 'ExportIndication',
        'Accept-Encoding': 'Identity',
        'CIMProtocolVersion': cim_protocol_version,
    }

    timer = ElapsedTimer()

    RCV_COUNT = 0
    RCV_ERRORS = False

    for i in range(send_count):

        msg_id = i
        payload = create_indication_data(msg_id, i, cim_protocol_version)

        try:
            response = post_bsl(url, headers=headers, data=payload)
        except requests.exceptions.RequestException as exc:
            msg = ("Testcase sending indication #{} raised {}: {}".
                   format(i, exc.__class__.__name__, exc))
            new_exc = AssertionError(msg)
            new_exc.__cause__ = None  # Disable to see original traceback
            raise new_exc

        if response.status_code != 200:
            msg = ("Testcase sending indication #{} failed with HTTP "
                   "status {}".format(i, response.status_code))
            raise AssertionError(msg)

    endtime = timer.elapsed_sec()

    # Give the listener thread some time to process all indications
    sleep(0.5)

    assert not RCV_ERRORS, \
        "Errors occurred in process_indication(), as printed to stdout"

    assert send_count == RCV_COUNT, \
        "Mismatch between total send count {} and receive count {}". \
        format(send_count, RCV_COUNT)

    return endtime


@pytest.mark.parametrize(
    "send_count",
    [1, 2, 3, 4, 5, 10, 100, 200, 300, 400, 500]
)
def test_WBEMListener_send_indications(send_count):
    """
    Test performance of sending indications to the pywbem.WBEMListener.
    """

    if send_count > 100 and sys.platform == 'win32':
        pytest.skip("Skipping test due to lengthy elapsed time")

    host = 'localhost'
    http_port = 50000

    listener = WBEMListener(host, http_port)
    listener.add_callback(process_indication)
    listener.start()

    # Warm up
    send_indications(host, http_port, 10)

    repetitions = 5
    try:
        times = []
        for _ in range(0, repetitions):
            time = send_indications(host, http_port, send_count)
            times.append(time)
        mean_time = statistics.mean(times)
        stdev_time = statistics.stdev(times)
        mean_rate = send_count / mean_time

        print("\nSent {} indications ({} repetitions): mean: {:.3f} s, "
              "stdev: {:.3f} s, mean rate: {:.0f} ind/s".
              format(send_count, repetitions, mean_time, stdev_time, mean_rate))
        sys.stdout.flush()

    finally:
        listener.stop()

        # Give some time to free up the port
        sleep(1.0)
