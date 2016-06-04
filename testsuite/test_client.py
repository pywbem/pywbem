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

* HTTPretty remembers the last request that was sent, so after issuing the
  request, the CIM-XML produced by the PyWBEM client is verified based on that.
"""

from __future__ import print_function, absolute_import

import os
import doctest
import socket
import unittest
import re
import traceback
from collections import namedtuple
import six
import yaml
import httpretty
from httpretty.core import HTTPrettyRequestEmpty
from lxml import etree, doctestcompare
if six.PY2:
    from M2Crypto.Err import SSLError
else:
    from ssl import SSLError

import pywbem
from pywbem.cim_obj import _ensure_unicode

# Directory with the JSON test case files, relative to this script:
TESTCASE_DIR = os.path.join(os.path.dirname(__file__), "test_client")


class ClientTestError(Exception):
    """Exception indicating an issue in the test case definition."""
    pass


def obj(value, tc_name):
    """Create a PyWBEM CIM object or list of CIM Objects from a testcase value.
       If the input value is not a valid type or list of valid types an
       error is raised.
       If the pywbem_object defines a valid type (ex. CIMInstance) or
       list of items where the pywbem_object entry defines a valid type,
       the type is evaluated with the remaining entries in the
       dictionary and returned.

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
        Returns a CIMInstance with the classname, properties, and path defined

    2. boolean object:

        False

        Returns boolean false

    3. list of objects
       A list of objects as defined by 1 above or boolean objects defined
       by 2. A list of corresponding results is returned

       Returns a list of the objects defined by each entry in the list

       See enumerateinstances.yaml for an example of list of instances.
       [] defines a null list

    """
    if isinstance(value, dict):
        if "pywbem_object" in value:
            ctor_name = value["pywbem_object"]
            try:
                ctor_call = getattr(pywbem, ctor_name)
            except AttributeError:
                raise ClientTestError("Error in definition of testcase %s: "\
                                      "Unknown type specified in " \
                                      "'pywbem_object' attribute: %s" % \
                                      (tc_name, ctor_name))
            ctor_args = {}
            for arg_name in value:
                if arg_name == "pywbem_object":
                    continue
                ctor_args[arg_name] = obj(value[arg_name], tc_name)
            obj_ = ctor_call(**ctor_args)
        else:
            obj_ = {}
            for key in value:
                obj_[key] = obj(value[key], tc_name)
    elif isinstance(value, list):
        obj_ = [obj(x, tc_name) for x in value]
    else:
        obj_ = value
    return obj_


def tc_getattr(tc_name, dict_, key, default=-1):
    """ Gets the attribute of a name/value pair defined by key in dictionary
        defined by dict_.
        Get the attribute for the key and if the attribute is list or tuple
        only return the first item. If the attribute is a dictionary
        return the attribute
        If the key is not in the dictionary, return either the provided
        default or -1 if no default provided
    """
    try:
        value = dict_[key]
        if isinstance(value, (list, tuple)):
            value = value[0]
    except (KeyError, IndexError):
        if default != -1:
            return default
        raise ClientTestError("Error in definition of testcase %s: "\
                              "'%s' attribute missing" % (tc_name, key))
    return value

def tc_getattr_list(tc_name, dict_, key, default=-1):
    """ Gets the attribute of a name/value pair defined by key in dictionary
        defined by dict_. The entry may be dictionary, ordinary value or
        a list
        Gets the attribute for the key return it.  Does not test for
        type of the attribute.
        If the key is not in the dictionary, return either the provided
        default or -1 if no default provided

    """
    try:
        value = dict_[key]
    except KeyError:
        if default != -1:
            return default
        raise ClientTestError("Error in definition of testcase %s: "\
                              "'%s' attribute missing" % (tc_name, key))
    return value


def tc_hasattr(dict_, key):
    """Return true if key is in dict_"""
    return key in dict_

class Callback(object):
    """A class with static methods that are HTTPretty callback functions for
    raising expected exceptions at the socket level.

    HTTPretty callback functions follow this interface:

        def my_callback(request, uri, headers):
            ...
            return (status, headers, body)

    Parameters:
      * `request`: string with invoked HTTP method
      * `uri`: string with target URI
      * `headers`: list of strings with HTTP headers of request

    Return value:
      * `status`: numeric with HTP status code for response
      * `headers`: list of strings with HTTP headers for response
      * `body`: response body / payload

    They can also raise an exception, which is passed to the caller of the
    socket send call.
    """

    @staticmethod
    def socket_ssl(request, uri, headers): #pylint: disable=unused-argument
        """HTTPretty callback function that raises an arbitrary
        SSLError."""
        raise SSLError(1, "Arbitrary SSL error.")

    @staticmethod
    def socket_104(request, uri, headers): #pylint: disable=unused-argument
        """HTTPretty callback function that raises socket.error 104."""
        raise socket.error(104, "Connection reset by peer.")

    @staticmethod
    def socket_32(request, uri, headers): #pylint: disable=unused-argument
        """HTTPretty callback function that raises socket.error 32."""
        raise socket.error(32, "Broken pipe.")

class ClientTest(unittest.TestCase):
    """Test case for PyWBEM client testing."""

    def assertXMLEqual(self, s1, s2, entity=None):
        """Assert that the two XML fragments are equal, tolerating the following
        variations:
          * whitespace outside of element content and attribute values.
          * order of attributes.
          * order of certain child elements (see `sort_elements` in this
            function).

        Parameters:
          * s1 and s2 are string representations of an XML fragment. The
            strings may be Unicode strings or UTF-8 encoded byte strings.
            The strings may contain an encoding declaration even when
            they are Unicode strings.

            Note: An encoding declaration is the `encoding` attribute in the
            XML declaration (aka XML processing statement), e.g.:
                <?xml version="1.0" encoding="utf-8" ?>
        """

        # Ensure Unicode strings and remove encoding from XML declaration
        encoding_pattern = re.compile(
            r'^<\?xml +(([a-zA-Z0-9_]+=".*")?) +' +
            r'encoding="utf-8" +(([a-zA-Z0-9_]+=".*")?) *\?>')
        encoding_repl = r'<?xml \1 \3 ?>'
        s1 = re.sub(encoding_pattern, encoding_repl, _ensure_unicode(s1))
        s2 = re.sub(encoding_pattern, encoding_repl, _ensure_unicode(s2))

        parser = etree.XMLParser(remove_blank_text=True)
        x1 = etree.XML(s1, parser=parser)
        x2 = etree.XML(s2, parser=parser)

        # Sort certain elements

        def sort_children(root, sort_elements):
            for tag, attr in sort_elements:
                # elems is a list of elements with this tag name
                elems = root.xpath("//*[local-name() = $tag]", tag=tag)
                if len(elems) > 0:
                    parent = elems[0].getparent()
                    first = None
                    after = None
                    for i in range(0, len(parent)):
                        if parent[i].tag == tag and first is None:
                            first = i
                        if parent[i].tag != tag and first is not None:
                            after = i
                    # The following changes the original XML tree:
                    # The following pylint warning can safely be disabled, see
                    # http://stackoverflow.com/a/25314665
                    # pylint: disable=cell-var-from-loop
                    parent[first:after] = sorted(elems,
                                                 key=lambda e: e.attrib[attr])

        sort_elements = [
            # Sort sibling elements with <first> tag by its <second> attribute
            ("IPARAMVALUE", "NAME"),
            ("PROPERTY", "NAME"),
            ("PARAMETER", "NAME"),
        ]
        sort_children(x1, sort_elements)
        sort_children(x2, sort_elements)

        ns1 = _ensure_unicode(etree.tostring(x1))
        ns2 = _ensure_unicode(etree.tostring(x2))

        checker = doctestcompare.LXMLOutputChecker()
        # This tolerates differences in whitespace and attribute order
        if not checker.check_output(ns1, ns2, 0):
            diff = checker.output_difference(doctest.Example("", ns1), ns2, 0)
            raise AssertionError("XML is not as expected in %s: %s"%\
                                 (entity, diff))

    def test_all(self):
        """This method performs all tests of this script. It iterates through
        the JSON files in the test case directory and processes each of them.
        """

        print("")  # We are in the middle of test runner output

        # We need to work with absolute file paths, because this test may be
        # run from a different directory.
        for basefn in os.listdir(TESTCASE_DIR):
            relfn = os.path.join(TESTCASE_DIR, basefn)
            if relfn.endswith(".yaml"):
                self.runyamlfile(relfn)

    def runyamlfile(self, fn):
        """Read a YAML test case file and process each test case it defines.
        """

        print("Processing YAML file: %s" % os.path.basename(fn))

        with open(fn) as fp:
            testcases = yaml.load(fp)
            for testcase in testcases:
                self.runtestcase(testcase)

    @httpretty.activate
    def runtestcase(self, testcase):
        """Run a single test case."""

        tc_name = tc_getattr("", testcase, "name")
        tc_desc = tc_getattr(tc_name, testcase, "description", None)

        print("Processing test case: %s: %s" % (tc_name, tc_desc))

        httpretty.httpretty.allow_net_connect = False

        pywbem_request = tc_getattr(tc_name, testcase, "pywbem_request")
        exp_http_request = tc_getattr(tc_name, testcase, "http_request", None)
        http_response = tc_getattr(tc_name, testcase, "http_response", None)
        exp_pywbem_response = tc_getattr(tc_name, testcase, "pywbem_response")

        # Setup HTTPretty for one WBEM operation
        if exp_http_request is not None:
            exp_http_exception = tc_getattr(tc_name, http_response,
                                            "exception", None)
            if exp_http_exception is None:
                params = {
                    "body": tc_getattr(tc_name, http_response, "data"),
                    "adding_headers": tc_getattr(tc_name, http_response,
                                                 "headers", None),
                    "status": tc_getattr(tc_name, http_response, "status")
                }
            else:
                callback_name = exp_http_exception
                try:
                    callback_func = getattr(Callback(), callback_name)
                except AttributeError:
                    raise ClientTestError("Error in testcase %s: Unknown "\
                                          "exception callback specified: %s"%\
                                          (tc_name, callback_name))
                params = {
                    "body": callback_func
                }

            method = tc_getattr(tc_name, exp_http_request, "verb")
            uri = tc_getattr(tc_name, exp_http_request, "url")

            httpretty.register_uri(method=method, uri=uri, **params)

        conn = pywbem.WBEMConnection(
            url=tc_getattr(tc_name, pywbem_request, "url"),
            creds=tc_getattr(tc_name, pywbem_request, "creds"),
            default_namespace=tc_getattr(tc_name, pywbem_request, "namespace"),
            timeout=tc_getattr(tc_name, pywbem_request, "timeout"))

        conn.debug = tc_getattr(tc_name, pywbem_request, "debug", False)

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
            raise ClientTestError("Error in definition of testcase %s: "\
                                  "Unknown operation name: %s" %\
                                  (tc_name, op_name))

        # Invoke the PyWBEM operation to be tested
        try:
            result = op_call(**op_args)
            raised_exception = None
        except Exception as exc:
            raised_exception = exc
            stringio = six.StringIO()
            traceback.print_exc(file=stringio)
            raised_traceback_str = stringio.getvalue()
            stringio.close()
            result = None

        # Validate PyWBEM result and exceptions.
        # We validate exceptions before validating the HTTP request, because
        # an exception might have been raised on the way down before the
        # request was actually made.

        exp_exception = tc_getattr(tc_name, exp_pywbem_response,
                                   "exception", None)
        exp_cim_status = tc_getattr(tc_name, exp_pywbem_response,
                                    "cim_status", 0)
        # get the expected result.  This may be either the the definition
        # of a value or cimobject or a list of values or cimobjects or
        # a named tuple of results.
        exp_result = tc_getattr_list(tc_name, exp_pywbem_response, "result",
                                     None)

        exp_pull_result = tc_getattr(tc_name, exp_pywbem_response, "pullresult",
                                     None)

        if exp_pull_result and exp_result:
            raise ClientTestError("Error in definition of testcase %s: "\
                                  "result and pull result attributes "\
                                  "are exclusive.")

        if exp_exception is not None and exp_result is not None:
            raise ClientTestError("Error in definition of testcase %s: "\
                                  "'result' and 'exception' attributes in "\
                                  "'pywbem_result' are not compatible." %\
                                  tc_name)
        if exp_cim_status != 0 and exp_result is not None:
            raise ClientTestError("Error in definition of testcase %s: "\
                                  "'result' and 'cim_status' attributes in "\
                                  "'pywbem_result' are not compatible." %\
                                  tc_name)

        if exp_cim_status != 0:
            exp_exception = 'CIMError'

        if exp_exception is not None:
            if raised_exception is None:
                raise AssertionError("Testcase %s: A %s exception was "\
                                     "expected to be raised by PyWBEM "\
                                     "operation %s, but no exception was "\
                                     "actually raised." %\
                                     (tc_name, exp_exception, op_name))
            elif raised_exception.__class__.__name__ != exp_exception:
                raise AssertionError("Testcase %s: A %s exception was "\
                                     "expected to be raised by PyWBEM "\
                                     "operation %s, but a different "\
                                     "exception was actually raised:\n"\
                                     "%s\n" %\
                                     (tc_name, exp_exception, op_name,
                                      raised_traceback_str))
        else:
            if raised_exception is not None:
                raise AssertionError("Testcase %s: No exception was "\
                                     "expected to be raised by PyWBEM "\
                                     "operation %s, but an exception was "\
                                     "actually raised:\n"\
                                     "%s\n" %\
                                     (tc_name, op_name, raised_traceback_str))

        # Validate HTTP request produced by PyWBEM

        if exp_http_request is not None:
            http_request = httpretty.last_request()
            self.assertTrue(not isinstance(http_request,
                                           HTTPrettyRequestEmpty),
                            "HTTP request is empty")
            exp_verb = tc_getattr(tc_name, exp_http_request, "verb")
            self.assertEqual(http_request.method, exp_verb,
                             "Verb in HTTP request is: %s (expected: %s)" % \
                             (http_request.method, exp_verb))
            exp_headers = tc_getattr(tc_name, exp_http_request, "headers", {})
            for header_name in exp_headers:
                self.assertEqual(http_request.headers[header_name],
                                 exp_headers[header_name],
                                 "Value of %s header in HTTP request is: %s " \
                                 "(expected: %s)" % \
                                 (header_name,
                                  http_request.headers[header_name],
                                  exp_headers[header_name]))
            exp_data = tc_getattr(tc_name, exp_http_request, "data", None)
            self.assertXMLEqual(http_request.body, exp_data,
                                "Unexpected CIM-XML payload in HTTP request")

        # Continue with validating the result

        if isinstance(raised_exception, pywbem.CIMError):
            cim_status = raised_exception.args[0]
        else:
            cim_status = 0
        self.assertEqual(cim_status, exp_cim_status,
                         "WBEMConnection operation CIM status code")

        if exp_result is not None:
            exp_result_obj = obj(exp_result, tc_name)

            # pylint: disable=unidiomatic-typecheck
            if type(result) != type(exp_result_obj):
                print("Details for the following assertion error:")
                print("- Expected result type: %s" % type(exp_result_obj))
                print("- Actual result type: %s" % type(result))
                raise AssertionError("PyWBEM CIM result type is not" \
                                     " as expected.")

            if result != exp_result_obj:
                print("Details for the following assertion error:")
                print("- Expected result: %r" % exp_result_obj)
                print("- Actual result: %r" % result)
                if conn.debug:
                    print("- HTTP response data: %r" % conn.last_raw_reply)
                raise AssertionError("WBEMConnection operation method result " \
                                     "is not as expected.")

        # if this is a pull result, compare the components of expected
        # and actual results.
        elif exp_pull_result is not None:
            exp_pull_result_obj = result_tuple(exp_pull_result, tc_name)

            # Length should be the same
            if len(result) != len(exp_pull_result_obj):
                print("Details for the following assertion error:")
                print("- Expected pull_result tuple size: %s" % \
                      len(exp_pull_result_obj))
                print("- Actual result len: %s" % len(result))
                raise AssertionError("PyWBEM CIM result type is not" \
                                     " as expected.")
            #eos is required result
            if result.eos != exp_pull_result_obj.eos:
                print("Details for the following assertion error:")
                print("- Expected pull result.eos: %r" % \
                      exp_pull_result_obj.eos)
                print("- Actual pull result.eos: %r" % result.eos)
                if conn.debug:
                    print("- HTTP response data: %r" % conn.last_raw_reply)
                raise AssertionError("WBEMConnection operation method result " \
                                     "is not as expected.")

            # context is required result
            if result.context != exp_pull_result_obj.context:
                print("Details for the following assertion error:")
                print("- Expected pull result.context: %r" % \
                    exp_pull_result_obj.context)
                print("- Actual pull result.context: %r" % result.context)
                if conn.debug:
                    print("- HTTP response data: %r" % conn.last_raw_reply)
                raise AssertionError("WBEMConnection operation method result " \
                                     "is not as expected.")

            if "instances" in exp_pull_result:
                if result.instances != exp_pull_result_obj.instances:
                    print("Details for the following assertion error:")
                    print("- Expected pull result: %r" % \
                          exp_pull_result_obj.instances)
                    print("- Actual pull result: %r" % result.instances)
                    if conn.debug:
                        print("- HTTP response data: %r" % conn.last_raw_reply)
                    raise AssertionError("WBEMConnection operation method " \
                                         "result is not as expected.")
            elif "paths" in exp_pull_result:
                if result.paths != exp_pull_result_obj.paths:
                    print("Details for the following assertion error:")
                    print("- Expected pull result: %r" % \
                          exp_pull_result_obj.paths)
                    print("- Actual pull result: %r" % result.paths)
                    if conn.debug:
                        print("- HTTP response data: %r" % conn.last_raw_reply)
                    raise AssertionError("WBEMConnection operation method " \
                                         "result is not as expected.")
            else:
                raise AssertionError("WBEMConnection operation method result " \
                     "is not as expected. No 'instances' " \
                     "or 'paths' component.")
                
            # TODO redo as indexed loop to compare all items.

        else:
            self.assertEqual(result, None, "PyWBEM CIM result")

def result_tuple(value, tc_name):
    """ Process the value (a dictionary) to create a named tuple of
        the components that are part of a pull result.
        Returns the  namedtuple of either
            instance, eos, context
            or
            paths, eos, context
    """

    if isinstance(value, dict):
        # test for both paths and instances.
        objs = None
        result = namedtuple("exp_result", ["instances", "eos", "context"])

        # either path or instances should be in value
        if "instances" in value:
            instances = value["instances"]
            objs = obj(instances, tc_name)
            if 'paths' in value:
                raise AssertionError("WBEMConnection operation method " \
                                     "result is not as expected. Both " \
                                     "'instances' and 'paths' component.")

        elif "paths" in value:
            paths = value["paths"]
            objs = obj(paths, tc_name)
            result = namedtuple("result", ["paths", "eos", "context"])
        else:
            raise AssertionError("WBEMConnection operation method result " \
                                 "is not as expected. No 'instances' " \
                                 "or 'paths' component.")

        return result(objs, value["eos"], value["context"])

    else:
        raise AssertionError("WBEMConnection operation invalid tuple " \
                                 "definition.")


if __name__ == '__main__':
    unittest.main()
