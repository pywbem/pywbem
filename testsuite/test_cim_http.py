#!/usr/bin/env python

"""Exercise routines in cim_http"""

from __future__ import absolute_import

import unittest

from pywbem import cim_http


class Parse_url(unittest.TestCase):  # pylint: disable=invalid-name
    """
    Test the parse_url() function.
    """

    def _run_single(self, url, exp_host, exp_port, exp_ssl):
        '''
        Test function for single invocation of parse_url() and
        allow_defaults attribute =True(default)
        '''

        host, port, ssl = cim_http.parse_url(url)

        self.assertEqual(host, exp_host,
                         "Unexpected host: %r, expected: %r" %
                         (host, exp_host))
        self.assertEqual(port, exp_port,
                         "Unexpected port: %r, expected: %r" %
                         (port, exp_port))
        self.assertEqual(ssl, exp_ssl,
                         "Unexpected ssl: %r, expected: %r" %
                         (ssl, exp_ssl))

    def _run_single_defaults_false(self, url, exp_host, exp_port, exp_ssl):
        '''
        Test function for single invocation of parse_url() with the default
        attribute set false
        '''

        host, port, ssl = cim_http.parse_url(url, allow_defaults=False)

        self.assertEqual(host, exp_host,
                         "Unexpected host: %r, expected: %r" %
                         (host, exp_host))
        self.assertEqual(port, exp_port,
                         "Unexpected port: %r, expected: %r" %
                         (port, exp_port))
        self.assertEqual(ssl, exp_ssl,
                         "Unexpected ssl: %r, expected: %r" %
                         (ssl, exp_ssl))

    def test_all(self):
        '''
        Run all tests for parse_url().
        '''

        # Keep these defaults in sync with those in cim_http.parse_url()
        default_port_http = 5988
        default_port_https = 5989
        default_ssl = False

        self._run_single("http://my.host.com",
                         "my.host.com",
                         default_port_http,
                         False)

        self._run_single("https://my.host.com/",
                         "my.host.com",
                         default_port_https,
                         True)

        self._run_single("my.host.com",
                         "my.host.com",
                         default_port_http,
                         default_ssl)

        self._run_single("http.com",
                         "http.com",
                         default_port_http,
                         default_ssl)

        self._run_single("http.com/",
                         "http.com",
                         default_port_http,
                         default_ssl)

        self._run_single("http.com/path.segment.com",
                         "http.com",
                         default_port_http,
                         default_ssl)

        self._run_single("http.com//path.segment.com",
                         "http.com",
                         default_port_http,
                         default_ssl)

        self._run_single("http://my.host.com:1234",
                         "my.host.com",
                         1234,
                         False)

        self._run_single("http://my.host.com:1234/",
                         "my.host.com",
                         1234,
                         False)

        self._run_single("http://my.host.com:1234/path/segment",
                         "my.host.com",
                         1234,
                         False)

        self._run_single("http://9.10.11.12:1234",
                         "9.10.11.12",
                         1234,
                         False)

        self._run_single("my.host.com:1234",
                         "my.host.com",
                         1234,
                         default_ssl)

        self._run_single("my.host.com:1234/",
                         "my.host.com",
                         1234,
                         default_ssl)

        self._run_single("9.10.11.12/",
                         "9.10.11.12",
                         default_port_http,
                         default_ssl)

        self._run_single("HTTP://my.host.com",
                         "my.host.com",
                         default_port_http,
                         False)

        self._run_single("HTTPS://my.host.com",
                         "my.host.com",
                         default_port_https,
                         True)

        self._run_single("http://[2001:db8::7348]",
                         "2001:db8::7348",
                         default_port_http,
                         False)

        self._run_single("http://[2001:db8::7348-1]",
                         "2001:db8::7348%1",
                         default_port_http,
                         False)

        self._run_single("http://[2001:db8::7348-eth1]",
                         "2001:db8::7348%eth1",
                         default_port_http,
                         False)

        self._run_single("http://[2001:db8::7348-eth1]:5900",
                         "2001:db8::7348%eth1",
                         5900,
                         False)

        # Toleration of (incorrect) IPv6 URI format supported by PyWBEM:
        # Must specify port; zone index must be specified with % if used

        self._run_single("http://2001:db8::7348:1234",
                         "2001:db8::7348",
                         1234,
                         False)

        self._run_single("http://2001:db8::7348%eth0:1234",
                         "2001:db8::7348%eth0",
                         1234,
                         False)

        self._run_single("http://2001:db8::7348%1:1234",
                         "2001:db8::7348%1",
                         1234,
                         False)

        self._run_single("https://[2001:db8::7348]/",
                         "2001:db8::7348",
                         default_port_https,
                         True)

        self._run_single("http://[2001:db8::7348]:1234",
                         "2001:db8::7348",
                         1234,
                         False)

        self._run_single("https://[::ffff.9.10.11.12]:1234/",
                         "::ffff.9.10.11.12",
                         1234,
                         True)

        self._run_single("https://[::ffff.9.10.11.12-0]:1234/",
                         "::ffff.9.10.11.12%0",
                         1234,
                         True)

        self._run_single("https://[::ffff.9.10.11.12-eth0]:1234/",
                         "::ffff.9.10.11.12%eth0",
                         1234,
                         True)

        self._run_single("[2001:db8::7348]",
                         "2001:db8::7348",
                         default_port_http,
                         default_ssl)

        self._run_single("[2001:db8::7348]/",
                         "2001:db8::7348",
                         default_port_http,
                         default_ssl)

        self._run_single("[2001:db8::7348]/-eth0",
                         "2001:db8::7348",
                         default_port_http,
                         default_ssl)

    def test_all_no_defaults(self):
        """ Test urls agains parse_url with allow_defaults=False"""

        # The following tests expect good return
        self._run_single_defaults_false("http://my.host.com:5988",
                                        "my.host.com",
                                        5988,
                                        False)

        self._run_single_defaults_false("https://my.host.com:5989",
                                        "my.host.com",
                                        5989,
                                        True)

        self._run_single("HTTP://my.host.com:50000",
                         "my.host.com",
                         50000,
                         False)

        self._run_single("HTTPS://my.host.com:49000",
                         "my.host.com",
                         49000,
                         True)

        self._run_single("http://[2001:db8::7348-eth1]:5900",
                         "2001:db8::7348%eth1",
                         5900,
                         False)

        self._run_single("https://[2001:db8::7348-eth1]:5901",
                         "2001:db8::7348%eth1",
                         5901,
                         True)

        # The following tests expect errors
        try:
            self._run_single_defaults_false("my.host.com:5988",
                                            "my.host.com:5988",
                                            5988,
                                            False)
            self.fail('No Scheme: Expecting exception')
        except ValueError:
            pass

        try:
            self._run_single_defaults_false("http://my.host.com",
                                            "my.host.com",
                                            5988,
                                            False)
            self.fail('No port: Expecting exception')
        except ValueError:
            pass

        try:
            self._run_single_defaults_false("blah://my.host.com:5988",
                                            "my.host.com",
                                            5988,
                                            False)
            self.fail('Invalid Scheme: Expecting exception')
        except ValueError:
            pass

        try:
            self._run_single_defaults_false("http://my.host.com:5a98",
                                            "my.host.com",
                                            5988,
                                            False)
            self.fail('Invalid Port: Expecting exception')
        except ValueError:
            pass

        try:
            self._run_single_defaults_false("[2001:db8::7348-eth1]:5900",
                                            "2001:db8::7348%eth1",
                                            5900,
                                            False)
            self.fail('Invalid Scheme: Expecting exception')
        except ValueError:
            pass

        try:
            self._run_single_defaults_false("://[2001:db8::7348-eth1]:5900",
                                            "2001:db8::7348%eth1",
                                            5900,
                                            False)
            self.fail('Invalid Scheme: Expecting exception')
        except ValueError:
            pass

        try:
            self._run_single_defaults_false(
                "httpsx://[2001:db8::7348-eth1]:5900",
                "2001:db8::7348%eth1",
                5900,
                False)
            self.fail('Invalid Scheme: Expecting exception')
        except ValueError:
            pass

        try:
            self._run_single_defaults_false(
                "https://[2001:db8::7348-eth1]",
                "2001:db8::7348%eth1",
                5900,
                False)
            self.fail('No Port: Expecting exception')
        except ValueError:
            pass

        try:
            self._run_single_defaults_false(
                "https://2001:db8::7348-eth1",
                "2001:db8::7348%eth1",
                5900,
                False)
            self.fail('No Port: Expecting exception')
        except ValueError:
            pass

        try:
            self._run_single_defaults_false(
                "httpsx://[2001:db8::7348-eth1]:59x0",
                "2001:db8::7348%eth1",
                5900,
                False)
            self.fail('Invalid Port: Expecting exception')
        except ValueError:
            pass


if __name__ == '__main__':
    unittest.main()
