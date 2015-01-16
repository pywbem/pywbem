#
# Exercise routines in cim_http.
#

import comfychair

from pywbem import cim_http


class Parse_url(comfychair.TestCase):
    """
    Test the parse_url() function.
    """

    def setup(self):
        return

    def runtest_single(self, url, exp_host, exp_port, exp_ssl):
        '''
        Test function for single invocation of parse_url()
        '''

        host, port, ssl = cim_http.parse_url(url)

        self.assert_equal(host, exp_host,
                          "Unexpected host: %r, expected: %r" % (host, exp_host))
        self.assert_equal(port, exp_port,
                          "Unexpected port: %r, expected: %r" % (port, exp_port))
        self.assert_equal(ssl, exp_ssl,
                          "Unexpected ssl: %r, expected: %r" % (ssl, exp_ssl))


    def runtest(self):
        '''
        Run all tests for parse_url().
        '''

        # Keep these defaults in sync with those in cim_http.parse_url()
        default_port_http  = 5988
        default_port_https = 5989
        default_ssl = False

        self.runtest_single("http://my.host.com",
                            "my.host.com",
                            default_port_http,
                            False)

        self.runtest_single("https://my.host.com/",
                            "my.host.com",
                            default_port_https,
                            True)

        self.runtest_single("my.host.com",
                            "my.host.com",
                            default_port_http,
                            default_ssl)

        self.runtest_single("http.com",
                            "http.com",
                            default_port_http,
                            default_ssl)

        self.runtest_single("http.com/",
                            "http.com",
                            default_port_http,
                            default_ssl)

        self.runtest_single("http.com/path.segment.com",
                            "http.com",
                            default_port_http,
                            default_ssl)

        self.runtest_single("http.com//path.segment.com",
                            "http.com",
                            default_port_http,
                            default_ssl)

        self.runtest_single("http://my.host.com:1234",
                            "my.host.com",
                            1234,
                            False)

        self.runtest_single("http://my.host.com:1234/",
                            "my.host.com",
                            1234,
                            False)

        self.runtest_single("http://my.host.com:1234/path/segment",
                            "my.host.com",
                            1234,
                            False)

        self.runtest_single("http://9.10.11.12:1234",
                            "9.10.11.12",
                            1234,
                            False)

        self.runtest_single("my.host.com:1234",
                            "my.host.com",
                            1234,
                            default_ssl)

        self.runtest_single("my.host.com:1234/",
                            "my.host.com",
                            1234,
                            default_ssl)

        self.runtest_single("9.10.11.12/",
                            "9.10.11.12",
                            default_port_http,
                            default_ssl)

        self.runtest_single("HTTP://my.host.com",
                            "my.host.com",
                            default_port_http,
                            False)

        self.runtest_single("HTTPS://my.host.com",
                            "my.host.com",
                            default_port_https,
                            True)

        self.runtest_single("http://[2001:db8::7348]",
                            "2001:db8::7348",
                            default_port_http,
                            False)

        self.runtest_single("http://[2001:db8::7348-1]",
                            "2001:db8::7348%1",
                            default_port_http,
                            False)

        self.runtest_single("http://[2001:db8::7348-eth1]",
                            "2001:db8::7348%eth1",
                            default_port_http,
                            False)

        # Toleration of (incorrect) IPv6 URI format supported by PyWBEM:
        # Must specify port; zone index must be specified with % if used

        self.runtest_single("http://2001:db8::7348:1234",
                            "2001:db8::7348",
                            1234,
                            False)

        self.runtest_single("http://2001:db8::7348%eth0:1234",
                            "2001:db8::7348%eth0",
                            1234,
                            False)

        self.runtest_single("http://2001:db8::7348%1:1234",
                            "2001:db8::7348%1",
                            1234,
                            False)

        self.runtest_single("https://[2001:db8::7348]/",
                            "2001:db8::7348",
                            default_port_https,
                            True)

        self.runtest_single("http://[2001:db8::7348]:1234",
                            "2001:db8::7348",
                            1234,
                            False)

        self.runtest_single("https://[::ffff.9.10.11.12]:1234/",
                            "::ffff.9.10.11.12",
                            1234,
                            True)

        self.runtest_single("https://[::ffff.9.10.11.12-0]:1234/",
                            "::ffff.9.10.11.12%0",
                            1234,
                            True)

        self.runtest_single("https://[::ffff.9.10.11.12-eth0]:1234/",
                            "::ffff.9.10.11.12%eth0",
                            1234,
                            True)

        self.runtest_single("[2001:db8::7348]",
                            "2001:db8::7348",
                            default_port_http,
                            default_ssl)

        self.runtest_single("[2001:db8::7348]/",
                            "2001:db8::7348",
                            default_port_http,
                            default_ssl)

        self.runtest_single("[2001:db8::7348]/-eth0",
                            "2001:db8::7348",
                            default_port_http,
                            default_ssl)


#################################################################
# Main function
#################################################################

tests = [
    Parse_url,                        # parse_url()
]

if __name__ == '__main__':
    comfychair.main(tests)
