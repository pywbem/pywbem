"""
Unit test cases for _cim_http.py
"""

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

# Literal form {"blah: 0} faster than dict(blah=0) but same functionality
# pylint: disable=use-dict-literal

# These defaults are defined separately from those in _cim_constants.py to
# ensure that changes of the defaults are caught.
DEFAULT_PORT_HTTP = 5988
DEFAULT_PORT_HTTPS = 5989
DEFAULT_SCHEME = 'http'

# Keep in sync with same value in _cim_http.py
HTTP_CONNECT_TIMEOUT = 9.99

URLLIB3_VERSION = tuple(map(int, urllib3.__version__.split('.')[0:3]))
URLLIB3V2 = URLLIB3_VERSION >= (2, 0, 0)

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
            exp_scheme=f'{DEFAULT_SCHEME}',
            exp_hostport='myhost:5000',
            exp_url=f'{DEFAULT_SCHEME}://myhost:5000',
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
            exp_hostport=f'myhost:{DEFAULT_PORT_HTTPS}',
            exp_url=f'https://myhost:{DEFAULT_PORT_HTTPS}',
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
            exp_hostport=f'myhost:{DEFAULT_PORT_HTTP}',
            exp_url=f'http://myhost:{DEFAULT_PORT_HTTP}',
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
            exp_scheme=f'{DEFAULT_SCHEME}',
            exp_hostport=f'http:{DEFAULT_PORT_HTTP}',
            exp_url=f'{DEFAULT_SCHEME}://http:{DEFAULT_PORT_HTTP}',
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
            exp_scheme=f'{DEFAULT_SCHEME}',
            exp_hostport=f'https:{DEFAULT_PORT_HTTP}',
            exp_url=f'{DEFAULT_SCHEME}://https:{DEFAULT_PORT_HTTP}',
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
            exp_hostport=f'myhost:{DEFAULT_PORT_HTTP}',
            exp_url=f'http://myhost:{DEFAULT_PORT_HTTP}',
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
            exp_hostport=f'myhost:{DEFAULT_PORT_HTTP}',
            exp_url=f'http://myhost:{DEFAULT_PORT_HTTP}',
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
            exp_hostport=f'9.10.11.12:{DEFAULT_PORT_HTTP}',
            exp_url=f'http://9.10.11.12:{DEFAULT_PORT_HTTP}',
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
            exp_scheme=f'{DEFAULT_SCHEME}',
            exp_hostport=f'[2001:db8::7348]:{DEFAULT_PORT_HTTP}',
            exp_url=f'{DEFAULT_SCHEME}://[2001:db8::7348]:{DEFAULT_PORT_HTTP}',
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
            exp_hostport=f'[2001:db8::7348]:{DEFAULT_PORT_HTTP}',
            exp_url=f'http://[2001:db8::7348]:{DEFAULT_PORT_HTTP}',
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
            exp_hostport=f'[2001:db8::7348-1]:{DEFAULT_PORT_HTTP}',
            exp_url=f'http://[2001:db8::7348-1]:{DEFAULT_PORT_HTTP}',
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
            exp_hostport=f'[2001:db8::7348-1]:{DEFAULT_PORT_HTTP}',
            exp_url=f'http://[2001:db8::7348-1]:{DEFAULT_PORT_HTTP}',
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
            exp_hostport=f'[2001:db8::7348-eth1]:{DEFAULT_PORT_HTTP}',
            exp_url=f'http://[2001:db8::7348-eth1]:{DEFAULT_PORT_HTTP}',
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
            exp_hostport=f'[2001:db8::7348-eth1]:{DEFAULT_PORT_HTTP}',
            exp_url=f'http://[2001:db8::7348-eth1]:{DEFAULT_PORT_HTTP}',
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
            exp_scheme=f'{DEFAULT_SCHEME}',
            exp_hostport='[2001:db8::7348]:1234',
            exp_url=f'{DEFAULT_SCHEME}://[2001:db8::7348]:1234',
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
DUMMY_CONN_USING_HTTP = pywbem.WBEMConnection(url='http://dummy')
DUMMY_POOL = urllib3.connectionpool.HTTPConnectionPool('dummy')

# Argument for NewConnectionError which changes first parameter from
# urllib3 version 1.x to urllib3 version 2.0 (from pool to host).
NEW_CONN_ERR_PARM1 = DUMMY_CONN_USING_HTTP if URLLIB3V2 else DUMMY_POOL

TESTCASES_PYWBEM_REQUESTS_EXCEPTION = [

    # Testcases for _cim_http.pywbem_requests_exception() and
    # _cim_http.pywbem_urllib3_exception()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * func_kwargs: input arguments to the function that is tested
    #   * exp_exc_type: Type of the expected returned exception
    #   * exp_pattern: pattern for the message in the expected returned exc.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "RequestException with empty message",
        dict(
            func_kwargs=dict(
                exc=requests.exceptions.RequestException(''),
                conn=DUMMY_CONN_USING_HTTP,
            ),
            exp_exc_type=pywbem.ConnectionError,
            exp_pattern='^$',
        ),
        None, None, True
    ),
    (
        "RequestException with simple message",
        dict(
            func_kwargs=dict(
                exc=requests.exceptions.RequestException('bla'),
                conn=DUMMY_CONN_USING_HTTP,
            ),
            exp_exc_type=pywbem.ConnectionError,
            exp_pattern='^bla$',
        ),
        None, None, True
    ),
    (
        "RequestException with simple message and HTTPS connection",
        dict(
            func_kwargs=dict(
                exc=requests.exceptions.RequestException('bla'),
                conn=DUMMY_CONN_USING_HTTPS,
            ),
            exp_exc_type=pywbem.ConnectionError,
            exp_pattern='^bla$',
        ),
        None, None, True
    ),
    (
        "SSLError with simple message and HTTPS connection",
        dict(
            func_kwargs=dict(
                exc=requests.exceptions.SSLError('bla'),
                conn=DUMMY_CONN_USING_HTTPS,
            ),
            exp_exc_type=pywbem.ConnectionError,
            exp_pattern='^bla; OpenSSL version used: .*$',
        ),
        None, None, True
    ),
    (
        "ConnectionError with simple message",
        dict(
            func_kwargs=dict(
                exc=requests.exceptions.ConnectionError('bla'),
                conn=DUMMY_CONN_USING_HTTP,
            ),
            exp_exc_type=pywbem.ConnectionError,
            exp_pattern='^bla$',
        ),
        None, None, True
    ),
    (
        "ReadTimeout with simple message",
        dict(
            func_kwargs=dict(
                exc=requests.exceptions.ReadTimeout('bla'),
                conn=DUMMY_CONN_USING_HTTP,
            ),
            exp_exc_type=pywbem.TimeoutError,
            exp_pattern='^bla$',
        ),
        None, None, True
    ),
    (
        "RetryError with simple message",
        dict(
            func_kwargs=dict(
                exc=requests.exceptions.RetryError('bla'),
                conn=DUMMY_CONN_USING_HTTP,
            ),
            exp_exc_type=pywbem.TimeoutError,
            exp_pattern='^bla$',
        ),
        None, None, True
    ),
    (
        "ConnectionError with MaxRetryError with ProtocolError "
        "with simple message with single quotes",
        dict(
            func_kwargs=dict(
                exc=requests.exceptions.ConnectionError(
                    urllib3.exceptions.MaxRetryError(
                        pool=DUMMY_POOL,
                        url='http://dummy',
                        reason=urllib3.exceptions.ProtocolError("foo'bla"))),
                conn=DUMMY_CONN_USING_HTTP,
            ),
            exp_exc_type=pywbem.ConnectionError,
            exp_pattern="^foo'bla$",
        ),
        None, None, True
    ),
    (
        "ConnectionError with MaxRetryError with ProtocolError "
        "with simple message with double quotes",
        dict(
            func_kwargs=dict(
                exc=requests.exceptions.ConnectionError(
                    urllib3.exceptions.MaxRetryError(
                        pool=DUMMY_POOL,
                        url='http://dummy',
                        reason=urllib3.exceptions.ProtocolError('foo"bla'))),
                conn=DUMMY_CONN_USING_HTTP,
            ),
            exp_exc_type=pywbem.ConnectionError,
            exp_pattern='^foo"bla$',
        ),
        None, None, True
    ),
    (
        "ConnectionError with MaxRetryError with ReadTimeoutError "
        "with simple message",
        dict(
            func_kwargs=dict(
                exc=requests.exceptions.ConnectionError(
                    urllib3.exceptions.MaxRetryError(
                        pool=DUMMY_POOL,
                        url='http://dummy',
                        reason=urllib3.exceptions.ReadTimeoutError(
                            pool=DUMMY_POOL,
                            url='http://dummy',
                            message="bla"))),
                conn=DUMMY_CONN_USING_HTTP,
            ),
            exp_exc_type=pywbem.TimeoutError,
            exp_pattern="^bla$",
        ),
        None, None, True
    ),
    (
        "ConnectionError with MaxRetryError with ReadTimeoutError "
        "with standard message with the connect timeout",
        dict(
            func_kwargs=dict(
                exc=requests.exceptions.ConnectionError(
                    urllib3.exceptions.MaxRetryError(
                        pool=DUMMY_POOL,
                        url='http://dummy',
                        reason=urllib3.exceptions.ReadTimeoutError(
                            pool=DUMMY_POOL,
                            url='http://dummy',
                            message="Read timed out. (read timeout="
                            f"{HTTP_CONNECT_TIMEOUT})"))),
                conn=DUMMY_CONN_USING_HTTP,
            ),
            exp_exc_type=pywbem.ConnectionError,
            exp_pattern="^Could not send request to http://dummy:5988 "
            "within 10 sec$",
        ),
        None, None, True
    ),
    (
        "ConnectionError with MaxRetryError with ReadTimeoutError "
        "with standard message with value other than the connect timeout",
        dict(
            func_kwargs=dict(
                exc=requests.exceptions.ConnectionError(
                    urllib3.exceptions.MaxRetryError(
                        pool=DUMMY_POOL,
                        url='http://dummy',
                        reason=urllib3.exceptions.ReadTimeoutError(
                            pool=DUMMY_POOL,
                            url='http://dummy',
                            message="Read timed out. (read timeout=30)"))),
                conn=DUMMY_CONN_USING_HTTP,
            ),
            exp_exc_type=pywbem.TimeoutError,
            exp_pattern="^No response received from http://dummy:5988 "
            "within 30 sec$",
        ),
        None, None, True
    ),
    (
        "ConnectionError with MaxRetryError with NewConnectionError "
        "with simple message",
        dict(
            func_kwargs=dict(
                exc=requests.exceptions.ConnectionError(
                    urllib3.exceptions.MaxRetryError(
                        pool=DUMMY_POOL,
                        url='http://dummy',
                        reason=urllib3.exceptions.NewConnectionError(
                            NEW_CONN_ERR_PARM1,
                            message="bla"))),
                conn=DUMMY_CONN_USING_HTTP,
            ),
            exp_exc_type=pywbem.ConnectionError,
            exp_pattern="^bla$"
        ),
        None, None, True
    ),
    (
        "ConnectionError with MaxRetryError with HTTPError "
        "with simple message",
        dict(
            func_kwargs=dict(
                exc=requests.exceptions.ConnectionError(
                    urllib3.exceptions.MaxRetryError(
                        pool=DUMMY_POOL,
                        url='http://dummy',
                        reason=urllib3.exceptions.HTTPError("bla"))),
                conn=DUMMY_CONN_USING_HTTP,
            ),
            exp_exc_type=pywbem.ConnectionError,
            exp_pattern="^bla$",
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_PYWBEM_REQUESTS_EXCEPTION)
@simplified_test_function
def test_pywbem_requests_exception(
        testcase, func_kwargs, exp_exc_type, exp_pattern):
    """
    Test function for _cim_http.pywbem_requests_exception() and
    _cim_http.pywbem_urllib3_exception() (called indirectly)
    """

    # The code to be tested
    act_exc = _cim_http.pywbem_requests_exception(**func_kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    act_message = str(act_exc)

    # Verify the result
    # pylint: disable=unidiomatic-typecheck,line-too-long
    assert type(act_exc) == exp_exc_type, \
        "Unexpected exception type:\n" \
        "  Actual type: {}\n" \
        "  Expected type: {}\n" \
        "  Actual message: {}\n" \
        "  Expected message pattern: {}\n". \
        format(type(act_exc), exp_exc_type, act_message, exp_pattern)  # noqa: E721,E501
    assert re.search(exp_pattern, act_message), \
        "Unexpected exception message:\n" \
        "  Actual: {}\n" \
        "  Expected pattern: {}\n". \
        format(act_message, exp_pattern)


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
