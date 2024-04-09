"""
End2end tests of operation timeout from a test class in the
OpenPegasus WBEM server.

"""

from __future__ import absolute_import, print_function

import re

import datetime

from .utils.pytest_extensions import skip_if_unsupported_capability

# Note: The wbem_connection fixture uses the es_server fixture, and
# due to the way py.test searches for fixtures, it also must be imported.
# pylint: disable=unused-import,wrong-import-order, relative-beyond-top-level
from .utils.pytest_extensions import wbem_connection  # noqa: F401
from pytest_easy_server import es_server  # noqa: F401
from .utils.pytest_extensions import default_namespace  # noqa: F401
# pylint: enable=unused-import,wrong-import-order, relative-beyond-top-level

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
# pylint: disable=relative-beyond-top-level, disable=redefined-builtin
from ..utils import import_installed

pywbem = import_installed('pywbem')
from pywbem import Uint32, CIMError, ConnectionError, CIMClassName, \
    TimeoutError  # noqa: E402 pylint: disable=redefined-builtin
# pylint: enable=relative-beyond-top-level, enable=redefined-buitin
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name

# Identity of the OpenPegasus namespace, class, and method that implements
# the delayed response. NOTE: This is only available on OpenPegasus version
# 2.15+ available from github.
NAMESPACE = 'test/testprovider'
TESTCLASS = 'Test_CLITestProviderClass'
TESTMETHOD = 'delayedMethodResponse'


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


def run_timeout_test(conn, timeout, response_delay, timeout_exp):
    """
    Test a single timeout, expected response_delay and timeout_exp boolean
    Tests for correct response type (good response if the delay is
    less than the timeout and timeout exception if the delay is greater
    than the timeout.
    """
    opttimer = ElapsedTimer()
    conn.timeout = timeout
    try:
        # Confirm server working with a simple request.
        conn.GetClass('CIM_ManagedElement')
        assert conn.timeout == timeout
        class_path = CIMClassName(TESTCLASS, namespace=NAMESPACE)
        result = conn.InvokeMethod(TESTMETHOD, class_path,
                                   [('delayInSeconds', Uint32(response_delay))])

        assert result[0] == Uint32(0)
        assert result[1]['delayInSeconds'] == response_delay

        execution_time = opttimer.elapsed_sec()

        assert not timeout_exp, 'Timeout expected but not rcvd., Fail: ' \
            'url={}, conn.timeout={}, timeout={}, response delay exp={}, '  \
            'execution time={}'.format(conn.url, conn.timeout, timeout,
                                       response_delay, execution_time)

    # ConnectionError exception: If this does not include in the response
    # message the text string, "Read timed out" the test fails.
    # If it does include that string the timeout is processed. See issue # 3075
    # Timeout returns this message text:
    # "HTTPConnectionPool(host='localhost', port=15988): Read timed out. "
    # #(read timeout=4)"
    except ConnectionError as ce:
        execution_time = opttimer.elapsed_sec()

        if re.search(r'^HTTPS?ConnectionPool(.*)Read timed out. (.*)$',
                     ce.args[0]):
            time_diff = abs(execution_time - timeout)
            assert timeout_exp, 'Timeout not expected: url={}, ' \
                'conn.timeout={}, ' \
                'timeout={}, response_delay_exp={}, execution time={}'. \
                format(conn.url, conn.timeout, timeout, response_delay,
                       execution_time)
            assert time_diff <= 1, 'Timeout Time - response delay diff to ' \
                'great, Failed: url={}, timeout={}, response delay exp={}, ' \
                'execution time={} exp - act diff={}, exception={}'. \
                format(conn.url, timeout, response_delay, execution_time,
                       time_diff, ce)

        else:
            assert False, 'ConnectionError Fail: url={}, conn.timeout={}, '  \
                'timeout={}, response_delay={}, execution time={}, '  \
                'exception={}'. \
                format(conn.url, conn.timeout, timeout, response_delay,
                       execution_time, ce)

    # This exception tests against expected result. It terminates the
    # test if the timeout is not expected or time difference between
    # response delay and timeout is too great.
    except TimeoutError as te:
        execution_time = opttimer.elapsed_sec()
        time_diff = abs(execution_time - timeout)
        assert timeout_exp, 'Timeout not expected: url={}, ' \
            'conn.timeout={}, ' \
            'timeout={}, response_delay_exp={}, execution time={}'. \
            format(conn.url, conn.timeout, timeout, response_delay,
                   execution_time)
        assert time_diff <= 1, 'Timeout Time - response delay diff to great, ' \
            'Failed: url={}, timeout={}, response delay exp={}, ' \
            'execution time={} exp - act diff={}, exception={}'. \
            format(conn.url, timeout, response_delay, execution_time,
                   time_diff, te)

    # Any CIMError
    except CIMError as ce:
        execution_time = opttimer.elapsed_sec()
        time_diff = abs(execution_time - timeout)
        assert not timeout_exp, 'CIMError exception: url={}, ' \
            'conn.timeout={}, timeout={}, response_delay_exp={}, ' \
            'execution time={} exception={}'. \
            format(conn.url, conn.timeout, timeout, response_delay,
                   execution_time, ce)


def test_timeouts(wbem_connection):  # noqa: F811
    # pylint: disable=redefined-outer-name
    """
    Test indication subscription to a container and reception of indications
    from the container.
    """
    skip_if_unsupported_capability(wbem_connection, 'interop')

    # Table of tests. Each entry is:
    #    timeout (sec), response_delay(sec), bool(time_out_expected flag)
    timeout_tests = [{'timeout': 8,
                      'response_delay': 4,
                      'timeout_exp': False},
                     {'timeout': 4,
                      'response_delay': 8,
                      'timeout_exp': True}, ]
    for kwargs in timeout_tests:
        run_timeout_test(wbem_connection, **kwargs)
