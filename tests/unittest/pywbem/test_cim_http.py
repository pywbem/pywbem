"""
Unit test cases for _cim_http.py
"""

from __future__ import absolute_import

import re
import requests
import urllib3
import pytest

from ..utils.pytest_extensions import simplified_test_function

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import _cim_http, MissingKeybindingsWarning  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


# These defaults are defined separately from those in _cim_constants.py to
# ensure that changes of the defaults are caught.
DEFAULT_PORT_HTTP = 5988
DEFAULT_PORT_HTTPS = 5989
DEFAULT_SCHEME = 'http'


TESTCASES_PARSE_URL = [

    # Testcases for _cim_http.parse_url()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * func_kwargs: input arguments to the function that is tested
    #   * exp_scheme: expected returned scheme, or None
    #   * exp_hostport: expected returned hostname, or None
    #   * exp_url: expected returned url, or None
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Default for allow_defaults argument is True",
        dict(
            func_kwargs=dict(
                url='myhost:5000',
                # allow_defaults defaults to True
            ),
            exp_scheme='http',
            exp_hostport='myhost:5000',
            exp_url='http://myhost:5000',
        ),
        None, None, True
    ),
    (
        "Invalid URL: empty string",
        dict(
            func_kwargs=dict(
                url='',
                allow_defaults=True,
            ),
            exp_scheme=None,
            exp_hostport=None,
            exp_url=None,
        ),
        ValueError, None, True
    ),
    (
        "Invalid URL: slash",
        dict(
            func_kwargs=dict(
                url='/',
                allow_defaults=True,
            ),
            exp_scheme=None,
            exp_hostport=None,
            exp_url=None,
        ),
        ValueError, None, True
    ),
    (
        "Applying default scheme raises ValueError when not allowed",
        dict(
            func_kwargs=dict(
                url='myhost:5000',
                allow_defaults=False,
            ),
            exp_scheme=None,
            exp_hostport=None,
            exp_url=None,
        ),
        ValueError, None, True
    ),
    (
        "Applying default scheme succeeds when allowed",
        dict(
            func_kwargs=dict(
                url='myhost:5000',
                allow_defaults=True,
            ),
            exp_scheme='{scheme}'.format(scheme=DEFAULT_SCHEME),
            exp_hostport='myhost:5000',
            exp_url='{scheme}://myhost:5000'.format(scheme=DEFAULT_SCHEME),
        ),
        None, None, True
    ),
    (
        "Applying default port for HTTPS raises ValueError when not allowed",
        dict(
            func_kwargs=dict(
                url='https://myhost',
                allow_defaults=False,
            ),
            exp_scheme=None,
            exp_hostport=None,
            exp_url=None,
        ),
        ValueError, None, True
    ),
    (
        "Applying default port for HTTPS succeeds when allowed",
        dict(
            func_kwargs=dict(
                url='https://myhost',
                allow_defaults=True,
            ),
            exp_scheme='https',
            exp_hostport='myhost:{port}'.format(port=DEFAULT_PORT_HTTPS),
            exp_url='https://myhost:{port}'.format(port=DEFAULT_PORT_HTTPS),
        ),
        None, None, True
    ),
    (
        "Applying default port for HTTP raises ValueError when not allowed",
        dict(
            func_kwargs=dict(
                url='http://myhost',
                allow_defaults=False,
            ),
            exp_scheme=None,
            exp_hostport=None,
            exp_url=None,
        ),
        ValueError, None, True
    ),
    (
        "Applying default port for HTTP succeeds when allowed",
        dict(
            func_kwargs=dict(
                url='http://myhost',
                allow_defaults=True,
            ),
            exp_scheme='http',
            exp_hostport='myhost:{port}'.format(port=DEFAULT_PORT_HTTP),
            exp_url='http://myhost:{port}'.format(port=DEFAULT_PORT_HTTP),
        ),
        None, None, True
    ),
    (
        "Unsupported scheme raises ValueError",
        dict(
            func_kwargs=dict(
                url='httpx://myhost',
                allow_defaults=True,
            ),
            exp_scheme=None,
            exp_hostport=None,
            exp_url=None,
        ),
        ValueError, None, True
    ),
    (
        "Invalid port number raises ValueError",
        dict(
            func_kwargs=dict(
                url='http://myhost:123x',
                allow_defaults=True,
            ),
            exp_scheme=None,
            exp_hostport=None,
            exp_url=None,
        ),
        ValueError, None, True
    ),
    (
        "Hostname http without scheme or port",
        dict(
            func_kwargs=dict(
                url='http',
                allow_defaults=True,
            ),
            exp_scheme='{scheme}'.format(scheme=DEFAULT_SCHEME),
            exp_hostport='http:{port}'.format(port=DEFAULT_PORT_HTTP),
            exp_url='{scheme}://http:{port}'.
            format(scheme=DEFAULT_SCHEME, port=DEFAULT_PORT_HTTP),
        ),
        None, None, True
    ),
    (
        "Hostname https without scheme or port",
        dict(
            func_kwargs=dict(
                url='https',
                allow_defaults=True,
            ),
            exp_scheme='{scheme}'.format(scheme=DEFAULT_SCHEME),
            exp_hostport='https:{port}'.format(port=DEFAULT_PORT_HTTP),
            exp_url='{scheme}://https:{port}'.
            format(scheme=DEFAULT_SCHEME, port=DEFAULT_PORT_HTTP),
        ),
        None, None, True
    ),
    (
        "Hostname with port and trailing slash",
        dict(
            func_kwargs=dict(
                url='http://myhost:5000/',
                allow_defaults=True,
            ),
            exp_scheme='http',
            exp_hostport='myhost:5000',
            exp_url='http://myhost:5000',
        ),
        None, None, True
    ),
    (
        "Hostname with port and trailing path segment",
        dict(
            func_kwargs=dict(
                url='http://myhost:5000/segment',
                allow_defaults=True,
            ),
            exp_scheme='http',
            exp_hostport='myhost:5000',
            exp_url='http://myhost:5000',
        ),
        None, None, True
    ),
    (
        "Hostname without port and with trailing slash",
        dict(
            func_kwargs=dict(
                url='http://myhost/',
                allow_defaults=True,
            ),
            exp_scheme='http',
            exp_hostport='myhost:{port}'.format(port=DEFAULT_PORT_HTTP),
            exp_url='http://myhost:{port}'.format(port=DEFAULT_PORT_HTTP),
        ),
        None, None, True
    ),
    (
        "Hostname without port and with trailing slash",
        dict(
            func_kwargs=dict(
                url='http://myhost/segment',
                allow_defaults=True,
            ),
            exp_scheme='http',
            exp_hostport='myhost:{port}'.format(port=DEFAULT_PORT_HTTP),
            exp_url='http://myhost:{port}'.format(port=DEFAULT_PORT_HTTP),
        ),
        None, None, True
    ),
    (
        "Upper case scheme HTTP",
        dict(
            func_kwargs=dict(
                url='HTTP://myhost:5000',
                allow_defaults=True,
            ),
            exp_scheme='http',
            exp_hostport='myhost:5000',
            exp_url='http://myhost:5000',
        ),
        None, None, True
    ),
    (
        "Upper case scheme HTTPS",
        dict(
            func_kwargs=dict(
                url='HTTPS://myhost:5000',
                allow_defaults=True,
            ),
            exp_scheme='https',
            exp_hostport='myhost:5000',
            exp_url='https://myhost:5000',
        ),
        None, None, True
    ),
    (
        "IPv4 address with port",
        dict(
            func_kwargs=dict(
                url='http://9.10.11.12',
                allow_defaults=True,
            ),
            exp_scheme='http',
            exp_hostport='9.10.11.12:{port}'.format(port=DEFAULT_PORT_HTTP),
            exp_url='http://9.10.11.12:{port}'.format(port=DEFAULT_PORT_HTTP),
        ),
        None, None, True
    ),
    (
        "IPv6 address in URI format without scheme, zone index or port",
        dict(
            func_kwargs=dict(
                url='[2001:db8::7348]',
                allow_defaults=True,
            ),
            exp_scheme='{scheme}'.format(scheme=DEFAULT_SCHEME),
            exp_hostport='[2001:db8::7348]:{port}'.
            format(port=DEFAULT_PORT_HTTP),
            exp_url='{scheme}://[2001:db8::7348]:{port}'.
            format(scheme=DEFAULT_SCHEME, port=DEFAULT_PORT_HTTP),
        ),
        None, None, True
    ),
    (
        "IPv6 address in URI format without zone index and without port",
        dict(
            func_kwargs=dict(
                url='http://[2001:db8::7348]',
                allow_defaults=True,
            ),
            exp_scheme='http',
            exp_hostport='[2001:db8::7348]:{port}'.
            format(port=DEFAULT_PORT_HTTP),
            exp_url='http://[2001:db8::7348]:{port}'.
            format(port=DEFAULT_PORT_HTTP),
        ),
        None, None, True
    ),
    (
        "IPv6 address in URI format with numeric zone index delimited with % "
        "and without port",
        dict(
            func_kwargs=dict(
                url='http://[2001:db8::7348%1]',
                allow_defaults=True,
            ),
            exp_scheme='http',
            exp_hostport='[2001:db8::7348-1]:{port}'.
            format(port=DEFAULT_PORT_HTTP),
            exp_url='http://[2001:db8::7348-1]:{port}'.
            format(port=DEFAULT_PORT_HTTP),
        ),
        None, None, True
    ),
    (
        "IPv6 address in URI format with numeric zone index delimited with - "
        "and without port",
        dict(
            func_kwargs=dict(
                url='http://[2001:db8::7348-1]',
                allow_defaults=True,
            ),
            exp_scheme='http',
            exp_hostport='[2001:db8::7348-1]:{port}'.
            format(port=DEFAULT_PORT_HTTP),
            exp_url='http://[2001:db8::7348-1]:{port}'.
            format(port=DEFAULT_PORT_HTTP),
        ),
        None, None, True
    ),
    (
        "IPv6 address in URI format with string zone index delimited with % "
        "and without port",
        dict(
            func_kwargs=dict(
                url='http://[2001:db8::7348%eth1]',
                allow_defaults=True,
            ),
            exp_scheme='http',
            exp_hostport='[2001:db8::7348-eth1]:{port}'.
            format(port=DEFAULT_PORT_HTTP),
            exp_url='http://[2001:db8::7348-eth1]:{port}'.
            format(port=DEFAULT_PORT_HTTP),
        ),
        None, None, True
    ),
    (
        "IPv6 address in URI format with string zone index delimited with - "
        "and without port",
        dict(
            func_kwargs=dict(
                url='http://[2001:db8::7348-eth1]',
                allow_defaults=True,
            ),
            exp_scheme='http',
            exp_hostport='[2001:db8::7348-eth1]:{port}'.
            format(port=DEFAULT_PORT_HTTP),
            exp_url='http://[2001:db8::7348-eth1]:{port}'.
            format(port=DEFAULT_PORT_HTTP),
        ),
        None, None, True
    ),
    (
        "IPv6 address in URI format without zone index and with port",
        dict(
            func_kwargs=dict(
                url='http://[2001:db8::7348]:1234',
                allow_defaults=True,
            ),
            exp_scheme='http',
            exp_hostport='[2001:db8::7348]:1234',
            exp_url='http://[2001:db8::7348]:1234',
        ),
        None, None, True
    ),
    (
        "IPv6 address in URI format with numeric zone index delimited with % "
        "and with port",
        dict(
            func_kwargs=dict(
                url='http://[2001:db8::7348%1]:1234',
                allow_defaults=True,
            ),
            exp_scheme='http',
            exp_hostport='[2001:db8::7348-1]:1234',
            exp_url='http://[2001:db8::7348-1]:1234',
        ),
        None, None, True
    ),
    (
        "IPv6 address in URI format with numeric zone index delimited with - "
        "and with port",
        dict(
            func_kwargs=dict(
                url='http://[2001:db8::7348-1]:1234',
                allow_defaults=True,
            ),
            exp_scheme='http',
            exp_hostport='[2001:db8::7348-1]:1234',
            exp_url='http://[2001:db8::7348-1]:1234',
        ),
        None, None, True
    ),
    (
        "IPv6 address in URI format with string zone index delimited with % "
        "and with port",
        dict(
            func_kwargs=dict(
                url='http://[2001:db8::7348%eth1]:1234',
                allow_defaults=True,
            ),
            exp_scheme='http',
            exp_hostport='[2001:db8::7348-eth1]:1234',
            exp_url='http://[2001:db8::7348-eth1]:1234',
        ),
        None, None, True
    ),
    (
        "IPv6 address in URI format with string zone index delimited with - "
        "and with port",
        dict(
            func_kwargs=dict(
                url='http://[2001:db8::7348-eth1]:1234',
                allow_defaults=True,
            ),
            exp_scheme='http',
            exp_hostport='[2001:db8::7348-eth1]:1234',
            exp_url='http://[2001:db8::7348-eth1]:1234',
        ),
        None, None, True
    ),
    (
        "IPv6 address in (invalid but tolerated) text format without "
        "scheme and without zone index and with port",
        dict(
            func_kwargs=dict(
                url='2001:db8::7348:1234',
                allow_defaults=True,
            ),
            exp_scheme='{scheme}'.format(scheme=DEFAULT_SCHEME),
            exp_hostport='[2001:db8::7348]:1234',
            exp_url='{scheme}://[2001:db8::7348]:1234'.
            format(scheme=DEFAULT_SCHEME),
        ),
        None, None, True
    ),
    (
        "IPv6 address in (invalid but tolerated) text format "
        "without zone index and with port",
        dict(
            func_kwargs=dict(
                url='http://2001:db8::7348:1234',
                allow_defaults=True,
            ),
            exp_scheme='http',
            exp_hostport='[2001:db8::7348]:1234',
            exp_url='http://[2001:db8::7348]:1234',
        ),
        None, None, True
    ),
    (
        "IPv6 address in (invalid but tolerated) text format "
        "with numeric zone index delimted with % and with port",
        dict(
            func_kwargs=dict(
                url='http://2001:db8::7348%1:1234',
                allow_defaults=True,
            ),
            exp_scheme='http',
            exp_hostport='[2001:db8::7348-1]:1234',
            exp_url='http://[2001:db8::7348-1]:1234',
        ),
        None, None, True
    ),
    (
        "IPv6 address in (invalid but tolerated) text format "
        "with string zone index delimted with % and with port",
        dict(
            func_kwargs=dict(
                url='http://2001:db8::7348%eth1:1234',
                allow_defaults=True,
            ),
            exp_scheme='http',
            exp_hostport='[2001:db8::7348-eth1]:1234',
            exp_url='http://[2001:db8::7348-eth1]:1234',
        ),
        None, None, True
    ),
    (
        "IPv6 address in URI format with IPv4 portion, without zone index "
        "and with port",
        dict(
            func_kwargs=dict(
                url='http://[::ffff.9.10.11.12]:1234',
                allow_defaults=True,
            ),
            exp_scheme='http',
            exp_hostport='[::ffff.9.10.11.12]:1234',
            exp_url='http://[::ffff.9.10.11.12]:1234',
        ),
        None, None, True
    ),
    (
        "IPv6 address in URI format with IPv4 portion, with numeric zone index "
        "delimited with % and with port",
        dict(
            func_kwargs=dict(
                url='http://[::ffff.9.10.11.12%1]:1234',
                allow_defaults=True,
            ),
            exp_scheme='http',
            exp_hostport='[::ffff.9.10.11.12-1]:1234',
            exp_url='http://[::ffff.9.10.11.12-1]:1234',
        ),
        None, None, True
    ),
    (
        "IPv6 address in URI format with IPv4 portion, with numeric zone index "
        "delimited with - and with port",
        dict(
            func_kwargs=dict(
                url='http://[::ffff.9.10.11.12-1]:1234',
                allow_defaults=True,
            ),
            exp_scheme='http',
            exp_hostport='[::ffff.9.10.11.12-1]:1234',
            exp_url='http://[::ffff.9.10.11.12-1]:1234',
        ),
        None, None, True
    ),
    (
        "IPv6 address in URI format with IPv4 portion, with string zone index "
        "delimited with % and with port",
        dict(
            func_kwargs=dict(
                url='http://[::ffff.9.10.11.12%eth1]:1234',
                allow_defaults=True,
            ),
            exp_scheme='http',
            exp_hostport='[::ffff.9.10.11.12-eth1]:1234',
            exp_url='http://[::ffff.9.10.11.12-eth1]:1234',
        ),
        None, None, True
    ),
    (
        "IPv6 address in URI format with IPv4 portion, with string zone index "
        "delimited with - and with port",
        dict(
            func_kwargs=dict(
                url='http://[::ffff.9.10.11.12-eth1]:1234',
                allow_defaults=True,
            ),
            exp_scheme='http',
            exp_hostport='[::ffff.9.10.11.12-eth1]:1234',
            exp_url='http://[::ffff.9.10.11.12-eth1]:1234',
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_PARSE_URL)
@simplified_test_function
def test_parse_url(
        testcase, func_kwargs, exp_scheme, exp_hostport, exp_url):
    """
    Test function for _cim_http.parse_url()
    """

    # The code to be tested
    act_scheme, act_hostport, act_url = _cim_http.parse_url(**func_kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    # Verify the result
    assert act_scheme == exp_scheme
    assert act_hostport == exp_hostport
    assert act_url == exp_url


DUMMY_CONN_USING_HTTPS = pywbem.WBEMConnection('https://dummy')
DUMMY_CONN_USING_HTTP = pywbem.WBEMConnection('http://dummy')
DUMMY_POOL = urllib3.connectionpool.HTTPConnectionPool('dummy')


TESTCASES_REQUEST_EXC_MESSAGE = [

    # Testcases for _cim_http.request_exc_message()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * func_kwargs: input arguments to the function that is tested
    #   * exp_pattern: pattern for the expected message, or None
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Requests exception with no args",
        dict(
            func_kwargs=dict(
                exc=requests.exceptions.RequestException(),
                conn=DUMMY_CONN_USING_HTTP,
            ),
            exp_pattern='^$',
        ),
        None, None, True
    ),
    (
        "Requests exception with empty message",
        dict(
            func_kwargs=dict(
                exc=requests.exceptions.RequestException(''),
                conn=DUMMY_CONN_USING_HTTP,
            ),
            exp_pattern='^$',
        ),
        None, None, True
    ),
    (
        "Requests exception with simple message",
        dict(
            func_kwargs=dict(
                exc=requests.exceptions.RequestException('bla'),
                conn=DUMMY_CONN_USING_HTTP,
            ),
            exp_pattern='^bla$',
        ),
        None, None, True
    ),
    (
        "Requests exception with simple message and HTTPS connection",
        dict(
            func_kwargs=dict(
                exc=requests.exceptions.RequestException('bla'),
                conn=DUMMY_CONN_USING_HTTPS,
            ),
            exp_pattern='^bla; OpenSSL version used: ',
        ),
        None, None, True
    ),
    (
        "Requests exception with attached MaxRetryError exception with "
        "underlying HTTPError exception",
        dict(
            func_kwargs=dict(
                exc=requests.exceptions.RequestException(
                    urllib3.exceptions.MaxRetryError(
                        pool=DUMMY_POOL,
                        url='http://dummy',
                        reason=urllib3.exceptions.HTTPError('bla'))),
                conn=DUMMY_CONN_USING_HTTP,
            ),
            exp_pattern='^bla$',
        ),
        None, None, True
    ),
    (
        "Requests exception with attached HTTPError exception",
        dict(
            func_kwargs=dict(
                exc=requests.exceptions.RequestException(
                    urllib3.exceptions.HTTPError('bla')),
                conn=DUMMY_CONN_USING_HTTP,
            ),
            exp_pattern='^bla$',
        ),
        None, None, True
    ),
    (
        "Requests exception with message type 1 that gets simplified",
        dict(
            func_kwargs=dict(
                exc=requests.exceptions.RequestException(
                    "(<foo>, 'bla')"
                ),
                conn=DUMMY_CONN_USING_HTTP,
            ),
            exp_pattern='^bla$',
        ),
        None, None, True
    ),
    (
        "Requests exception with message type 2 that gets simplified",
        dict(
            func_kwargs=dict(
                exc=requests.exceptions.RequestException(
                    "<foo>: bla"
                ),
                conn=DUMMY_CONN_USING_HTTP,
            ),
            exp_pattern='^bla$',
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUEST_EXC_MESSAGE)
@simplified_test_function
def test_request_exc_message(testcase, func_kwargs, exp_pattern):
    """
    Test function for _cim_http.request_exc_message()
    """

    # The code to be tested
    act_message = _cim_http.request_exc_message(**func_kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    # Verify the result
    assert re.search(exp_pattern, act_message)


# TODO: Add unit tests for _cim_http.wbem_request(). It is already tested to
# some extent in the function tests, but adding unit tests would still be good.


TESTCASES_MAX_REPR = [

    # Testcases for _cim_http.max_repr()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * func_kwargs: input arguments to the function that is tested
    #   * exp_repr: expected repr result, or None
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Input text None",
        dict(
            func_kwargs=dict(
                text=None,
                max_len=20,
            ),
            exp_repr='None',
        ),
        None, None, True
    ),
    (
        "Input text shorter than max_len by much",
        dict(
            func_kwargs=dict(
                text='abc def',
                max_len=20,
            ),
            exp_repr="'abc def'",
        ),
        None, None, True
    ),
    (
        "Input text shorter than max_len by 1",
        dict(
            func_kwargs=dict(
                text='abc def',
                max_len=8,
            ),
            exp_repr="'abc def'",
        ),
        None, None, True
    ),
    (
        "Input text equal to max_len",
        dict(
            func_kwargs=dict(
                text='abc def',
                max_len=7,
            ),
            exp_repr="'abc def'",
        ),
        None, None, True
    ),
    (
        "Input text longer than max_len by 1",
        dict(
            func_kwargs=dict(
                text='abc def',
                max_len=6,
            ),
            exp_repr="'abc de'...",
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_MAX_REPR)
@simplified_test_function
def test_max_repr(testcase, func_kwargs, exp_repr):
    """
    Test function for _cim_http.max_repr()
    """

    # The code to be tested
    act_repr = _cim_http.max_repr(**func_kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    # Verify the result
    assert act_repr == exp_repr


TESTCASES_GET_CIMOBJECT_HEADER = [

    # Testcases for _cim_http.get_cimobject_header()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * obj: input object for get_cimobject_header()
    #   * exp_result: expected result of get_cimobject_header(), or None
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Input object is text",
        dict(
            obj='abc',
            exp_result='abc',
        ),
        None, None, True
    ),
    (
        "Input object is CIMClassName without namespace",
        dict(
            obj=pywbem.CIMClassName('C1'),
            exp_result=':C1',
        ),
        None, None, True
    ),
    (
        "Input object is CIMClassName with namespace",
        dict(
            obj=pywbem.CIMClassName('C1', namespace='ns'),
            exp_result='ns:C1',
        ),
        None, None, True
    ),
    (
        "Input object is CIMInstanceName without namespace and no keys",
        dict(
            obj=pywbem.CIMInstanceName('C1'),
            exp_result=':C1',
        ),
        None, MissingKeybindingsWarning, True
    ),
    (
        "Input object is CIMInstanceName with namespace and no keys",
        dict(
            obj=pywbem.CIMInstanceName('C1', namespace='ns'),
            exp_result='ns:C1',
        ),
        None, MissingKeybindingsWarning, True
    ),
    (
        "Input object is CIMInstanceName with namespace and one key",
        dict(
            obj=pywbem.CIMInstanceName('C1', namespace='ns',
                                       keybindings=dict(K1='v1')),
            exp_result='ns:C1.K1="v1"',
        ),
        None, None, True
    ),
    (
        "Input object is CIMInstanceName with namespace and two keys",
        dict(
            obj=pywbem.CIMInstanceName(
                'C1', namespace='ns',
                keybindings=[('K1', 'v1'), ('K2', 'v2')]),
            exp_result='ns:C1.K1="v1",K2="v2"',
        ),
        None, None, True
    ),
    (
        "Input object has unsupported type CIMClass",
        dict(
            obj=pywbem.CIMClass('C1'),
            exp_result=None,
        ),
        TypeError, None, True
    ),
    (
        "Input object has unsupported type CIMInstance",
        dict(
            obj=pywbem.CIMInstance('C1'),
            exp_result=None,
        ),
        TypeError, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_GET_CIMOBJECT_HEADER)
@simplified_test_function
def test_get_cimobject_header(testcase, obj, exp_result):
    """
    Test function for _cim_http.get_cimobject_header()
    """

    # The code to be tested
    act_result = _cim_http.get_cimobject_header(obj)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    # Verify the result
    assert act_result == exp_result
