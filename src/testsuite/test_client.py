#!/usr/bin/env python
"""
Test the complete PyWBEM client.

Approach:

* The HTTPretty package is used to intercept the client communication at the
  socket level. It catches PyWBEM requests going out and produces corresponding
  responses coming back in.

* Because HTTPretty seems to be able to register only one response for a
  particular URL, each test case can perform only one WBEM request and in its
  setup the test case needs to register the desired response for that request
  with HTTPretty.

* The testcases then performs the request at the PyWBEM client API, and
  verifies the response also at the level of the PyWBEM client API.

* HTTPretty remembers the lest request that was sent, so after issuing the
  request, the CIM-XML produced by the PyWBEM client is verified based on that.
"""

import httpretty
import yaml
import os
import inspect
from lxml import etree

import comfychair
from comfychair import main, TestCase
import pywbem

# Directory with the JSON test case files, relative to the comfychair module:
TESTCASE_DIR = "test_client"


class ClientTestError(Exception):
    """Exception indicating an issue in the test case definition."""
    pass


def obj(value, tc_name):
    """Create a PyWBEM CIM object from a testcase value.

    Examples for a testcase value (JSON object / Python dict):

    1. CIMInstance object:

        {
            "pywbem_object": "CIMInstance",
            "classname": "PyWBEM_Person",
            "properties": {
                "Name": "Fritz",
                "Address": "Fritz Town"
            },
            "path": {
                "pywbem_object": "CIMInstanceName",
                "classname": "PyWBEM_Person",
                "namespace": "root/cimv2",
                "keybindings": {
                    "Name": "Fritz"
                }
            }
        }

    2. boolean object:

        False

    """

    if isinstance(value, dict) and "pywbem_object" in value:
        ctor_name = value["pywbem_object"]
        try:
            ctor_call = getattr(pywbem, ctor_name)
        except AttributeError as exc:
            raise ClientTestError("Error in test case %s: Unknown type "\
                                  "specified in 'pywbem_object' attribute: %s"%\
                                  (tc_name, ctor_name))
        ctor_args = {}
        for arg_name in value:
            if arg_name == "pywbem_object":
                continue
            ctor_args[arg_name] = obj(value[arg_name], tc_name)
        obj_ = ctor_call(**ctor_args)
    else:
        obj_ = value
    return obj_


def tc_getattr(tc_name, dict_, key, default=-1):
    try:
        value = dict_[key]
    except KeyError as exc:
        if default != -1:
            return default
        raise ClientTestError("Error in test case %s: '%s' attribute missing"%\
                              (tc_name, key))
    return value


def tc_hasattr(dict_, key):
    return key in dict_


class ClientTest(TestCase):
    """Test case for PyWBEM client testing."""

    def assert_xml_equal(self, s1, s2):
        """s1 and s2 are string representations of XML.
        This function asserts that the two XML strings are equal,
        tolerating the usual XML variations:
          * whitespace between elements and attributes.
        """
        parser = etree.XMLParser(remove_blank_text=True)

        x1 = etree.XML(s1, parser=parser)
        ns1 = etree.tostring(x1)
        x2 = etree.XML(s2, parser=parser)
        ns2 = etree.tostring(x2)

        return self.assert_equal(ns1, ns2)

    def runtest(self):
        """This method is called by comfychair when running this test.
        It iterates through the JSON files in the test case directory and
        processes each of them.
        """
        # We need to work with absolute file paths, because this test may be
        # run from a different directory.
        tc_absdir = os.path.join(os.path.dirname(inspect.getfile(comfychair)),
                                 TESTCASE_DIR)
        for fn in os.listdir(tc_absdir):
            absfn = os.path.join(tc_absdir, fn)
            if fn.endswith(".yaml"):
                self.runyamlfile(absfn)

    def runyamlfile(self, fn):
        """Read a YAML test case file and process each test case it defines.
        """
        with open(fn) as fp:
            testcases = yaml.load(fp)
            for testcase in testcases:
                self.runtestcase(testcase)

    @httpretty.activate
    def runtestcase(self, testcase):
        """Run a single test case."""

        tc_name = tc_getattr("", testcase, "name")
        tc_desc = tc_getattr(tc_name, testcase, "description", None)

        pywbem_request = tc_getattr(tc_name, testcase, "pywbem_request")
        exp_http_request = tc_getattr(tc_name, testcase, "http_request")
        http_response = tc_getattr(tc_name, testcase, "http_response")
        exp_pywbem_response = tc_getattr(tc_name, testcase,
                                         "pywbem_response")

        # Setup HTTPretty for one WBEM operation
        httpretty.register_uri(
            method=tc_getattr(tc_name, exp_http_request, "verb"),
            uri=tc_getattr(tc_name, exp_http_request, "url"),
            body=tc_getattr(tc_name, http_response, "data"),
            adding_headers=tc_getattr(tc_name, http_response, "headers",
                                      None),
            status=tc_getattr(tc_name, http_response, "status"))

        conn = pywbem.WBEMConnection(
            url=tc_getattr(tc_name, pywbem_request, "url"),
            creds=tc_getattr(tc_name, pywbem_request, "creds"),
            default_namespace=tc_getattr(tc_name, pywbem_request,
                                         "namespace"),
            timeout=tc_getattr(tc_name, pywbem_request, "timeout"))

        op = tc_getattr(tc_name, pywbem_request, "operation")
        # Example:
        #  "operation": {
        #      "pywbem_method": "GetInstance",
        #      "InstanceName": {
        #          "pywbem_object": "CIMInstanceName",
        #          "classname": "PyWBEM_Person",
        #          "keybindings": {
        #              "Name": "Fritz"
        #          }
        #      },
        #      "LocalOnly": False
        #  }

        op_name = tc_getattr(tc_name, op, "pywbem_method")
        op_args = {}
        for arg_name in op:
            if arg_name == "pywbem_method":
                continue
            op_args[arg_name] = obj(op[arg_name], tc_name)
        try:
            op_call = getattr(conn, op_name)
        except AttributeError as exc:
            raise ClientTestError("Error in testcase %s: Unknown "\
                                  "operation name: %s" %\
                                  (tc_name, op_name))

        # Invoke the PyWBEM operation to be tested
        try:
            result = op_call(**op_args)
            raised_exception = None
        except Exception as exc:
            raised_exception = exc
            result = None

        # Validate HTTP request produced by PyWBEM

        http_request = httpretty.last_request()
        exp_verb = tc_getattr(tc_name, exp_http_request, "verb")
        self.assert_equal(http_request.method, exp_verb)
        exp_headers = tc_getattr(tc_name, exp_http_request, "headers", {})
        for header_name in exp_headers:
            self.assert_equal(http_request.headers[header_name],
                              exp_headers[header_name])
        # TBD: Add support for tolerating differences in CIM-XML:
        # - Order of sibling elements of same name
        # - Whitespace between elements
        exp_data = tc_getattr(tc_name, exp_http_request, "data", None)
        self.assert_xml_equal(http_request.body, exp_data)

        # Validate PyWBEM result

        exp_exception = tc_getattr(tc_name, exp_pywbem_response,
                                   "exception", None)
        exp_cim_status = tc_getattr(tc_name, exp_pywbem_response,
                                    "cim_status", 0)
        exp_result = tc_getattr(tc_name, exp_pywbem_response, "result",
                                None)
        if exp_exception is not None and exp_result is not None:
            raise ClientTestError("Error in testcase %s: 'result' and "\
                                  "'exception' attributes in "\
                                  "'pywbem_result' are not compatible." %\
                                  tc_name)
        if exp_cim_status != 0 and exp_result is not None:
            raise ClientTestError("Error in testcase %s: 'result' and "\
                                  "'cim_status' attributes in "\
                                  "'pywbem_result' are not compatible." %\
                                  tc_name)

        if exp_exception is not None:
            self.assert_notequal(raised_exception, None)
            raised_exception_name = raised_exception.__class__.__name__
            self.assert_equal(raised_exception_name, exp_exception)
        else:
            self.assert_equal(raised_exception, None)

        if isinstance(raised_exception, pywbem.CIMError):
            cim_status, cim_description, _ = raised_exception
        else:
            cim_status = 0
        self.assert_equal(cim_status, exp_cim_status)

        if exp_result is not None:
            self.assert_equal(result, obj(exp_result, tc_name))
        else:
            self.assert_equal(result, None)


tests = [ # pylint: disable=invalid-name
    ClientTest
]

if __name__ == '__main__':
    main(tests)
