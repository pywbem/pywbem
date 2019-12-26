#!/usr/bin/env python

"""Exercise routines in cim_http"""

from __future__ import absolute_import

import unittest

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
pywbem = import_installed('pywbem')  # noqa: E402
from pywbem import cim_http
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


class Parse_url(unittest.TestCase):  # pylint: disable=invalid-name
    """
    Test the parse_url() function.
    """

    def _run_single(self, url, exp_scheme, exp_hostport, exp_url):
        '''
        Test function for single invocation of parse_url() and
        allow_defaults attribute =True(default)
        '''

        scheme, hostport, url2 = cim_http.parse_url(url, allow_defaults=True)

        if exp_scheme is None:
            raise AssertionError(
                "Expected exception did not happen for url={!r}; "
                "parse_url() returned scheme={!r}, hostport={!r}, url={!r}".
                format(url, scheme, hostport, url2))

        self.assertEqual(scheme, exp_scheme,
                         "Unexpected scheme: %r, expected: %r" %
                         (scheme, exp_scheme))
        self.assertEqual(hostport, exp_hostport,
                         "Unexpected hostport: %r, expected: %r" %
                         (hostport, exp_hostport))
        self.assertEqual(url2, exp_url,
                         "Unexpected url: %r, expected: %r" %
                         (url2, exp_url))

    def _run_single_defaults_false(
            self, url, exp_scheme, exp_hostport, exp_url):
        '''
        Test function for single invocation of parse_url() with the default
        attribute set false
        '''

        scheme, hostport, url2 = cim_http.parse_url(url, allow_defaults=False)

        if exp_scheme is None:
            raise AssertionError(
                "Expected exception did not happen for url={!r}; "
                "parse_url() returned scheme={!r}, hostport={!r}, url={!r}".
                format(url, scheme, hostport, url2))

        self.assertEqual(scheme, exp_scheme,
                         "Unexpected scheme: %r, expected: %r" %
                         (scheme, exp_scheme))
        self.assertEqual(hostport, exp_hostport,
                         "Unexpected hostport: %r, expected: %r" %
                         (hostport, exp_hostport))
        self.assertEqual(url2, exp_url,
                         "Unexpected url: %r, expected: %r" %
                         (url2, exp_url))

    def test_all(self):
        '''
        Run all tests for parse_url().
        '''

        # Keep these defaults in sync with those in cim_constants
        default_port_http = 5988
        default_port_https = 5989
        default_scheme = 'http'

        self._run_single("http://my.host.com",
                         "http",
                         "my.host.com:{port}".
                         format(port=default_port_http),
                         "http://my.host.com:{port}".
                         format(port=default_port_http))

        self._run_single("https://my.host.com/",
                         "https",
                         "my.host.com:{port}".
                         format(port=default_port_https),
                         "https://my.host.com:{port}".
                         format(port=default_port_https))

        self._run_single("my.host.com",
                         default_scheme,
                         "my.host.com:{port}".
                         format(port=default_port_http),
                         "{scheme}://my.host.com:{port}".
                         format(scheme=default_scheme, port=default_port_http))

        self._run_single("http.com",
                         default_scheme,
                         "http.com:{port}".
                         format(port=default_port_http),
                         "{scheme}://http.com:{port}".
                         format(scheme=default_scheme, port=default_port_http))

        self._run_single("http.com/",
                         default_scheme,
                         "http.com:{port}".
                         format(port=default_port_http),
                         "{scheme}://http.com:{port}".
                         format(scheme=default_scheme, port=default_port_http))

        self._run_single("http.com/path.segment.com",
                         default_scheme,
                         "http.com:{port}".
                         format(port=default_port_http),
                         "{scheme}://http.com:{port}".
                         format(scheme=default_scheme, port=default_port_http))

        self._run_single("http.com//path.segment.com",
                         default_scheme,
                         "http.com:{port}".
                         format(port=default_port_http),
                         "{scheme}://http.com:{port}".
                         format(scheme=default_scheme, port=default_port_http))

        self._run_single("http://my.host.com:1234",
                         "http",
                         "my.host.com:1234",
                         "http://my.host.com:1234")

        self._run_single("http://my.host.com:1234/",
                         "http",
                         "my.host.com:1234",
                         "http://my.host.com:1234")

        self._run_single("http://my.host.com:1234/path/segment",
                         "http",
                         "my.host.com:1234",
                         "http://my.host.com:1234")

        self._run_single("http://9.10.11.12:1234",
                         "http",
                         "9.10.11.12:1234",
                         "http://9.10.11.12:1234")

        self._run_single("my.host.com:1234",
                         default_scheme,
                         "my.host.com:1234",
                         "{scheme}://my.host.com:1234".
                         format(scheme=default_scheme))

        self._run_single("my.host.com:1234/",
                         default_scheme,
                         "my.host.com:1234",
                         "{scheme}://my.host.com:1234".
                         format(scheme=default_scheme))

        self._run_single("9.10.11.12/",
                         default_scheme,
                         "9.10.11.12:{port}".
                         format(port=default_port_http),
                         "{scheme}://9.10.11.12:{port}".
                         format(scheme=default_scheme, port=default_port_http))

        self._run_single("HTTP://my.host.com",
                         "http",
                         "my.host.com:{port}".
                         format(port=default_port_http),
                         "http://my.host.com:{port}".
                         format(port=default_port_http))

        self._run_single("HTTPS://my.host.com",
                         "https",
                         "my.host.com:{port}".
                         format(port=default_port_https),
                         "https://my.host.com:{port}".
                         format(port=default_port_https))

        self._run_single("http://[2001:db8::7348]",
                         "http",
                         "[2001:db8::7348]:{port}".
                         format(port=default_port_http),
                         "http://[2001:db8::7348]:{port}".
                         format(port=default_port_http))

        self._run_single("http://[2001:db8::7348-1]",
                         "http",
                         "[2001:db8::7348-1]:{port}".
                         format(port=default_port_http),
                         "http://[2001:db8::7348-1]:{port}".
                         format(port=default_port_http))

        self._run_single("http://[2001:db8::7348-eth1]",
                         "http",
                         "[2001:db8::7348-eth1]:{port}".
                         format(port=default_port_http),
                         "http://[2001:db8::7348-eth1]:{port}".
                         format(port=default_port_http))

        self._run_single("http://[2001:db8::7348-eth1]:5900",
                         "http",
                         "[2001:db8::7348-eth1]:5900",
                         "http://[2001:db8::7348-eth1]:5900")

        # Toleration of (incorrect) IPv6 URI format supported by PyWBEM:
        # Must specify port; zone index must be specified with % if used

        self._run_single("http://2001:db8::7348:1234",
                         "http",
                         "[2001:db8::7348]:1234",
                         "http://[2001:db8::7348]:1234")

        self._run_single("http://2001:db8::7348%eth0:1234",
                         "http",
                         "[2001:db8::7348-eth0]:1234",
                         "http://[2001:db8::7348-eth0]:1234")

        self._run_single("http://2001:db8::7348%1:1234",
                         "http",
                         "[2001:db8::7348-1]:1234",
                         "http://[2001:db8::7348-1]:1234")

        self._run_single("https://[2001:db8::7348]/",
                         "https",
                         "[2001:db8::7348]:{port}".
                         format(port=default_port_https),
                         "https://[2001:db8::7348]:{port}".
                         format(port=default_port_https))

        self._run_single("http://[2001:db8::7348]:1234",
                         "http",
                         "[2001:db8::7348]:1234",
                         "http://[2001:db8::7348]:1234")

        self._run_single("https://[::ffff.9.10.11.12]:1234/",
                         "https",
                         "[::ffff.9.10.11.12]:1234",
                         "https://[::ffff.9.10.11.12]:1234")

        self._run_single("https://[::ffff.9.10.11.12-0]:1234/",
                         "https",
                         "[::ffff.9.10.11.12-0]:1234",
                         "https://[::ffff.9.10.11.12-0]:1234")

        self._run_single("https://[::ffff.9.10.11.12-eth0]:1234/",
                         "https",
                         "[::ffff.9.10.11.12-eth0]:1234",
                         "https://[::ffff.9.10.11.12-eth0]:1234")

        self._run_single("[2001:db8::7348]",
                         default_scheme,
                         "[2001:db8::7348]:{port}".
                         format(port=default_port_http),
                         "{scheme}://[2001:db8::7348]:{port}".
                         format(scheme=default_scheme, port=default_port_http))

        self._run_single("[2001:db8::7348]/",
                         default_scheme,
                         "[2001:db8::7348]:{port}".
                         format(port=default_port_http),
                         "{scheme}://[2001:db8::7348]:{port}".
                         format(scheme=default_scheme, port=default_port_http))

        self._run_single("[2001:db8::7348]/-eth0",
                         default_scheme,
                         "[2001:db8::7348]:{port}".
                         format(port=default_port_http),
                         "{scheme}://[2001:db8::7348]:{port}".
                         format(scheme=default_scheme, port=default_port_http))

        self._run_single("http://:1234",
                         "http",
                         "[:1234]:{port}".
                         format(port=default_port_http),
                         "http://[:1234]:{port}".
                         format(port=default_port_http))

        try:
            self._run_single("httpsx://[2001:db8::7348-eth1]:5900",
                             None, None, None)
            self.fail('Unsupported scheme: Expecting exception')
        except ValueError as exc:
            assert "Unsupported scheme" in str(exc)

        try:
            self._run_single("",
                             None, None, None)
            self.fail('Invalid URL: Expecting exception')
        except ValueError as exc:
            assert "Invalid URL" in str(exc)

        try:
            self._run_single("/",
                             None, None, None)
            self.fail('Invalid URL: Expecting exception')
        except ValueError as exc:
            assert "Invalid URL" in str(exc)

        try:
            self._run_single("blah://my.host.com:5988",
                             None, None, None)
            self.fail('Unsupported scheme: Expecting exception')
        except ValueError as exc:
            assert "Unsupported scheme" in str(exc)

        try:
            self._run_single("https://[2001:db8::7348-eth1]:59x0",
                             None, None, None)
            self.fail('Invalid port number: Expecting exception')
        except ValueError as exc:
            assert "Invalid port number" in str(exc)

        try:
            self._run_single("http://my.host.com:5a98",
                             None, None, None)
            self.fail('Invalid port: Expecting exception')
        except ValueError as exc:
            assert "Invalid port" in str(exc)

    def test_all_no_defaults(self):
        """ Test urls agains parse_url with allow_defaults=False"""

        # The following tests expect good return
        self._run_single_defaults_false("http://my.host.com:5988",
                                        "http",
                                        "my.host.com:5988",
                                        "http://my.host.com:5988")

        self._run_single_defaults_false("https://my.host.com:5989",
                                        "https",
                                        "my.host.com:5989",
                                        "https://my.host.com:5989")

        self._run_single_defaults_false("HTTP://my.host.com:50000",
                                        "http",
                                        "my.host.com:50000",
                                        "http://my.host.com:50000")

        self._run_single_defaults_false("HTTPS://my.host.com:49000",
                                        "https",
                                        "my.host.com:49000",
                                        "https://my.host.com:49000")

        self._run_single_defaults_false("http://[2001:db8::7348-eth1]:5900",
                                        "http",
                                        "[2001:db8::7348-eth1]:5900",
                                        "http://[2001:db8::7348-eth1]:5900")

        self._run_single_defaults_false("https://[2001:db8::7348-eth1]:5901",
                                        "https",
                                        "[2001:db8::7348-eth1]:5901",
                                        "https://[2001:db8::7348-eth1]:5901")

        # The following tests expect errors

        try:
            self._run_single_defaults_false("my.host.com:5988",
                                            None, None, None)
            self.fail('Scheme component missing: Expecting exception')
        except ValueError as exc:
            assert "Scheme component missing" in str(exc)

        try:
            self._run_single_defaults_false("http://my.host.com",
                                            None, None, None)
            self.fail('Port component missing: Expecting exception')
        except ValueError as exc:
            assert "Port component missing" in str(exc)

        try:
            self._run_single_defaults_false("[2001:db8::7348-eth1]:5900",
                                            None, None, None)
            self.fail('Scheme component missing: Expecting exception')
        except ValueError as exc:
            assert "Scheme component missing" in str(exc)

        try:
            self._run_single_defaults_false("://[2001:db8::7348-eth1]:5900",
                                            None, None, None)
            self.fail('Scheme component missing: Expecting exception')
        except ValueError as exc:
            assert "Scheme component missing" in str(exc)

        try:
            self._run_single_defaults_false("https://[2001:db8::7348-eth1]",
                                            None, None, None)
            self.fail('Port component missing: Expecting exception')
        except ValueError as exc:
            assert "Port component missing" in str(exc)

        try:
            self._run_single_defaults_false("https://2001:db8::7348-eth1",
                                            None, None, None)
            self.fail('Port component missing: Expecting exception')
        except ValueError as exc:
            assert "Port component missing" in str(exc)


if __name__ == '__main__':
    unittest.main()
