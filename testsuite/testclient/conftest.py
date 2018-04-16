"""
Module for running the testclient .yaml test cases.
"""

import doctest
import socket
import pytest
import re
import traceback
import threading
from collections import namedtuple
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
import yaml
import yamlordereddictloader
import httpretty
from httpretty.core import HTTPrettyRequestEmpty, fakesock
from lxml import etree, doctestcompare
import six
import pywbem
from pywbem._utils import _ensure_unicode
from pywbem._nocasedict import NocaseDict


class ExcThread(threading.Thread):
    """
    Thread that catches an exception and passes it to the creator
    in the Thread.join() method.
    """

    def run(self):
        self.exc = None
        try:
            threading.Thread.run(self)
        except Exception:
            import sys
            self.exc = sys.exc_info()

    def join(self, *args, **kwargs):
        threading.Thread.join(self, *args, **kwargs)
        if self.exc:
            six.reraise(*self.exc)


def patched_makefile(self, mode='r', bufsize=-1):
    """Returns this fake socket's own StringIO buffer.

    If there is an entry associated with the socket, the file
    descriptor gets filled in with the entry data before being
    returned.
    """
    self._mode = mode
    self._bufsize = bufsize

    if self._entry:
        # The patched version uses ExcThread instead of Thread
        t = ExcThread(
            target=self._entry.fill_filekind, args=(self.fd,)
        )
        t.start()
        if self.timeout == socket._GLOBAL_DEFAULT_TIMEOUT:
            timeout = None
        else:
            timeout = self.timeout
        t.join(timeout)
        if t.isAlive():
            raise socket.timeout

    return self.fd


# Monkey-patching httpretty to pass exception raised in callbacks
# back to the caller.
fakesock.socket.makefile = patched_makefile


def pytest_collect_file(parent, path):
    """
    py.test hook that is called for a directory to collect its test files.
    """
    if path.ext == ".yaml":
        return YamlFile(path, parent)


class YamlFile(pytest.File):
    """
    py.test test case collector class that parses a testclient .yaml file and
    yields its test cases.
    """

    def collect(self):
        with self.fspath.open(encoding='utf-8') as fp:
            filepath = self.fspath.relto(self.parent.fspath)
            testcases = yaml.load(fp, Loader=yamlordereddictloader.Loader)
            for i, testcase in enumerate(testcases):
                try:
                    tc_name = testcase['name']
                except KeyError:
                    raise ClientTestError("Test case #%s does not have a "
                                          "'name' attribute" % i + 1)
                yield YamlItem(tc_name, self, testcase, filepath)


class YamlItem(pytest.Item):
    """
    py.test test case collector class that runs the test on a single test case.
    """

    def __init__(self, name, parent, testcase, filepath):
        super(YamlItem, self).__init__(name, parent)
        self.testcase = testcase
        self.filepath = filepath

    def tc_name(self):
        """
        Return test case name.
        """
        name = self.testcase.get('name', 'unknown')
        return name

    def runtest(self):
        runtestcase(self.testcase)

    def repr_failure(self, excinfo):
        """
        Called when self.runtest() raises an exception, to provide details
        about the failure.
        """
        exc = excinfo.value
        if isinstance(exc, ClientTestFailure):
            return "Failure running test case: %s" % exc
        elif isinstance(exc, ClientTestError):
            return "Error in definition of test case: %s" % exc
        else:
            return "Error: %s" % exc

    def reportinfo(self):
        return self.fspath, 0, "%s in %s" % (self.name, self.filepath)


class ClientTestError(Exception):
    """Exception indicating an error in the test case definition."""
    pass


class ClientTestFailure(Exception):
    """Exception indicating a failure when running a test case."""
    pass


def show_diff(conn, expected, actual, display_text):
    """Display the actual and expected data"""

    print("Details for the following assertion error:")
    print("- Expected result %s: %s" % (display_text, expected))
    print("- Actual result %s: %s" % (display_text, actual))
    if conn is not None and conn.debug:
        print("- HTTP response data: %r" % conn.last_raw_reply)


def str_tuple(tuple_):
    """
    Prepare a tuple or NonType for output.

    This gets around issues of type failure when trying to
    print tuples.

    Returns str rep of tuple on None if tuple_ is None
    """
    return 'NoneType' if tuple_ is None else '%s' % (tuple_,)


def obj(value, tc_name):
    """
    Create a PyWBEM CIM object or list of CIM Objects from a testcase value.

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
                raise ClientTestError("Unknown type specified in "
                                      "'pywbem_object' attribute: %s" %
                                      ctor_name)
            ctor_args = OrderedDict()
            for arg_name in value:
                if arg_name == "pywbem_object":
                    continue
                ctor_args[arg_name] = obj(value[arg_name], tc_name)
            obj_ = ctor_call(**ctor_args)
        else:
            obj_ = OrderedDict()
            for key in value:
                obj_[key] = obj(value[key], tc_name)
    elif isinstance(value, list):
        obj_ = [obj(x, tc_name) for x in value]
    else:
        obj_ = value
    return obj_


def tc_getattr(tc_name, dict_, key, default=-1):
    """
    Gets the attribute of a name/value pair defined by key in dictionary
    defined by dict_.

    Get the attribute for the key and if the attribute is list or tuple
    only return the first item. If the attribute is a dictionary
    return the attribute

    If the key is not in the dictionary, return the provided default or
    raise an error if no default provided.
    """

    try:
        value = dict_[key]
        if isinstance(value, (list, tuple)):
            value = value[0]
    except (KeyError, IndexError, TypeError):
        if default != -1:
            return default
        raise ClientTestError("%r attribute missing" % key)
    return value


def tc_getattr_list(tc_name, dict_, key, default=-1):
    """
    Gets the attribute of a name/value pair defined by key in dictionary
    defined by dict_. The entry may be dictionary, ordinary value or
    a list

    Gets the attribute for the key return it.  Does not test for
    type of the attribute.

    If the key is not in the dictionary, return the provided default or
    raise an error if no default provided.
    """

    try:
        value = dict_[key]
    except KeyError:
        if default != -1:
            return default
        raise ClientTestError("%r attribute missing" % key)
    return value


def tc_hasattr(dict_, key):
    """Return true if key is in dict_"""
    return key in dict_


class Callback(object):
    """
    A class with static methods that are HTTPretty callback functions for
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
      * `status`: numeric with HTTP status code for response
      * `headers`: list of strings with HTTP headers for response
      * `body`: response body / payload

    They can also raise an exception, which is passed to the caller of the
    socket send call.
    """

    @staticmethod
    def socket_104(request, uri, headers):  # pylint: disable=unused-argument
        """HTTPretty callback function that raises socket.error 104."""
        raise socket.error(104, "Connection reset by peer.")

    @staticmethod
    def socket_32(request, uri, headers):  # pylint: disable=unused-argument
        """HTTPretty callback function that raises socket.error 32."""
        raise socket.error(32, "Broken pipe.")

    @staticmethod
    def socket_timeout(request, uri, headers):
        # pylint: disable=unused-argument
        """HTTPretty callback function that raises socket.timeout error.
           The socket.timeout is just a string, no status.
        """
        raise socket.timeout("Socket timeout.")


def xml_embed(tree_elem):
    """
    Embed the CIM-XML representation of a CIM object.

    This is done by converting the XML tree representing the CIM object into a
    single XML element whose character text is the embedded representation,
    which has some special XML characters (defined in DSP0201) replaced with
    their character entity references (= XML escape sequences).

    Parameters:
      tree_elem (etree.Element):
        XML tree of the CIM-XML representation of the CIM object that is to
        be embedded.

    Returns:
      string: The embedded CIM-XML representation of the CIM object.
    """
    return xml_escape(etree.tostring(tree_elem))


def xml_escape(s):  # pylint: disable=invalid-name
    """
    Return the XML-escaped input string.
    """
    if isinstance(str, six.text_type):
        s = s.replace(u"&", u"&amp;")
        s = s.replace(u"<", u"&lt;")
        s = s.replace(u">", u"&gt;")
        s = s.replace(u"\"", u"&quot;")
        s = s.replace(u"'", u"&apos;")
    else:
        s = s.replace(b"&", b"&amp;")
        s = s.replace(b"<", b"&lt;")
        s = s.replace(b">", b"&gt;")
        s = s.replace(b"\"", b"&quot;")
        s = s.replace(b"'", b"&apos;")
    return s


def xml_unembed(emb_str):
    """
    Unembed the CIM-XML representation of a CIM object.

    This is done by converting an XML element whose character text is the
    embedded representation, into an XML tree representing the CIM object,
    whereby the character entity references (= XML escape sequences) of
    some special XML characters (defined in DSP0201) are replaced with
    their characters.

    Parameters:
      emb_str (string):
        The embedded CIM-XML representation of the CIM object that is to be
        unembedded.

    Returns:
      etree.Element:
        XML tree of the CIM-XML representation of the CIM object.
    """
    parser = etree.XMLParser(remove_blank_text=True)
    return etree.XML(xml_unescape(emb_str), parser=parser)


def xml_unescape(s):  # pylint: disable=invalid-name
    """
    Return the XML-unescaped input string.
    """
    if isinstance(s, six.text_type):
        s = s.replace(u"&lt;", u"<")
        s = s.replace(u"&gt;", u">")
        s = s.replace(u"&quot;", u"\"")
        s = s.replace(u"&apos;", u"'")
        s = s.replace(u"&amp;", u"&")
    else:
        s = s.replace(b"&lt;", b"<")
        s = s.replace(b"&gt;", b">")
        s = s.replace(b"&quot;", b"\"")
        s = s.replace(b"&apos;", b"'")
        s = s.replace(b"&amp;", b"&")
    return s


def assertXMLEqual(s_act, s_exp, entity=None):
    """
    Assert that the two XML fragments are equal, tolerating the following
    variations:
      * whitespace outside of element content and attribute values.
      * order of attributes.
      * order of certain child elements (see `sort_elements` in this
        function).

    Parameters:
      * s_act and s_exp are string representations of an XML fragment. The
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
    s_act = re.sub(encoding_pattern, encoding_repl, _ensure_unicode(s_act))
    s_exp = re.sub(encoding_pattern, encoding_repl, _ensure_unicode(s_exp))

    parser = etree.XMLParser(remove_blank_text=True)
    x_act = etree.XML(s_act, parser=parser)
    x_exp = etree.XML(s_exp, parser=parser)

    def sort_embedded(root, sort_elements):
        """
        Helper function for `sort_children()`, in support of embedded
        objects. This function invokes sort_children() on each embedded
        object in `root`, after unembedding the embedded object.

        Parameters:
          root (etree.Element):
            XML tree of the CIM-XML representation of the CIM element that
            contains an embedded CIM object (e.g. the CIM element may be
            an INSTANCE XML element and one of its PROPERTY child elements
            has a value that is an embedded CIM instance).
        """
        emb_elems = root.xpath("//*[@EmbeddedObject or @EMBEDDEDOBJECT]"
                               "/*[local-name() = 'VALUE' or "
                               "local-name() = 'VALUE.ARRAY']")
        for emb_elem in emb_elems:
            elem = xml_unembed(emb_elem.text)
            sort_children(elem, sort_elements)
            emb_elem.text = xml_embed(elem)

    def sort_children(root, sort_elements):
        """
        Sort certain elements in the `root` parameter to facilitate
        comparison of two XML documents.

        In addition, make sure this is also applied to any embedded
        objects (in their unembedded state).
        """
        sort_embedded(root, sort_elements)
        for tag, attr in sort_elements:
            # elems is a list of elements with this tag name
            elems = root.xpath("//*[local-name() = $tag]", tag=tag)
            if elems:
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
        ("PROPERTY.ARRAY", "NAME"),
        ("PARAMETER", "NAME"),
        ("KEYBINDING", "NAME"),
    ]
    sort_children(x_act, sort_elements)
    sort_children(x_exp, sort_elements)

    ns_act = _ensure_unicode(etree.tostring(x_act))
    ns_exp = _ensure_unicode(etree.tostring(x_exp))

    checker = doctestcompare.LXMLOutputChecker()

    # This tolerates differences in whitespace and attribute order
    if not checker.check_output(ns_act, ns_exp, 0):
        diff = checker.output_difference(doctest.Example("", ns_exp),
                                         ns_act, 0)
        raise AssertionError("XML is not as expected in %s: %s" %
                             (entity, diff))


@httpretty.activate
def runtestcase(testcase):
    """Run a single test case."""

    tc_name = tc_getattr("", testcase, "name")
    # tc_desc = tc_getattr(tc_name, testcase, "description", None)
    tc_ignore = tc_getattr(tc_name, testcase, "ignore_python_version", None)
    tc_ignore_test = tc_getattr(tc_name, testcase, "ignore_test", None)

    # Determine if this test case should be skipped
    if tc_ignore_test is not None:
        pytest.skip("Test case has 'ignore_test' set")
        return
    if six.PY2 and tc_ignore == 2 or six.PY3 and tc_ignore == 3:
        pytest.skip("Test case has 'ignore_python_version' set")
        return

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
                raise ClientTestError("Unknown exception callback: %s" %
                                      callback_name)
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
        timeout=tc_getattr(tc_name, pywbem_request, "timeout"),
        stats_enabled=tc_getattr(tc_name, pywbem_request, "stats-enabled",
                                 False))

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
    op_args = OrderedDict()
    for arg_name in op:
        if arg_name == "pywbem_method":
            continue
        op_args[arg_name] = obj(op[arg_name], tc_name)
    try:
        op_call = getattr(conn, op_name)

    except AttributeError as exc:
        raise ClientTestError("Unknown operation name: %s" % op_name)

    # Invoke the PyWBEM operation to be tested
    try:
        result = op_call(**op_args)
        raised_exception = None

    except Exception as exc:      # pylint: disable=broad-except
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

    # get the optional expected request and reply sizes if specified. The
    # default is None if not specified
    exp_request_len = tc_getattr_list(tc_name, exp_pywbem_response,
                                      "request_len", None)
    exp_reply_len = tc_getattr_list(tc_name, exp_pywbem_response,
                                    "reply_len", None)
    # get the expected result.  This may be either the the definition
    # of a value or cimobject or a list of values or cimobjects or
    # a named tuple of results.
    exp_result = tc_getattr_list(tc_name, exp_pywbem_response,
                                 "result", None)

    exp_pull_result = tc_getattr(tc_name, exp_pywbem_response,
                                 "pullresult", None)

    if exp_pull_result and exp_result:
        raise ClientTestError("Result and pull result attributes are are not "
                              "compatible.")

    if exp_exception is not None and exp_result is not None:
        raise ClientTestError("The 'result' and 'exception' attributes in "
                              "'pywbem_result' are not compatible.")
    if exp_cim_status != 0 and exp_result is not None:
        raise ClientTestError("The 'result' and 'cim_status' attributes in "
                              "'pywbem_result' are not compatible.")

    if exp_cim_status != 0:
        exp_exception = 'CIMError'

    if exp_exception is not None:
        if raised_exception is None:
            raise AssertionError("Testcase %s: A %s exception was "
                                 "expected to be raised by PyWBEM "
                                 "operation %s, but no exception was "
                                 "actually raised." %
                                 (tc_name, exp_exception, op_name))
        elif raised_exception.__class__.__name__ != exp_exception:
            raise AssertionError("Testcase %s: A %s exception was "
                                 "expected to be raised by PyWBEM "
                                 "operation %s, but a different "
                                 "exception was actually raised:\n"
                                 "%s\n" %
                                 (tc_name, exp_exception, op_name,
                                  raised_traceback_str))
    else:
        if raised_exception is not None:
            raise AssertionError("Testcase %s: No exception was "
                                 "expected to be raised by PyWBEM "
                                 "operation %s, but an exception was "
                                 "actually raised:\n"
                                 "%s\n" %
                                 (tc_name, op_name, raised_traceback_str))

    # Validate HTTP request produced by PyWBEM

    if exp_http_request is not None:
        http_request = httpretty.last_request()
        assert not isinstance(http_request, HTTPrettyRequestEmpty), \
            "HTTP request is empty"
        exp_verb = tc_getattr(tc_name, exp_http_request, "verb")
        assert http_request.method == exp_verb
        exp_headers = tc_getattr(tc_name, exp_http_request, "headers", {})
        for header_name in exp_headers:
            act_header = http_request.headers[header_name]
            exp_header = exp_headers[header_name]
            assert act_header == exp_header, \
                "Value of %s header in HTTP request is: %s " \
                "(expected: %s)" % (header_name, act_header, exp_header)
        exp_data = tc_getattr(tc_name, exp_http_request, "data", None)
        assertXMLEqual(http_request.body, exp_data,
                       "Unexpected CIM-XML payload in HTTP request")
    if exp_request_len is not None:
        assert exp_request_len == conn.last_request_len

        if conn.stats_enabled:
            snapshot = conn.statistics.snapshot()
            assert len(snapshot) == 1  # one operation; one stat

            for name, stats in snapshot:  # pylint: disable=unused-variable
                stat = stats
            assert stat.count == 1
            assert stat.min_request_len == stat.max_request_len
            assert stat.min_request_len == exp_request_len

    if exp_reply_len is not None:
        assert exp_reply_len == conn.last_reply_len, \
            "Reply lengths do not match. exp %s rcvd %s" % \
            (exp_reply_len, conn.last_reply_len)

        if conn.stats_enabled:
            snapshot = conn.statistics.snapshot()
            assert len(snapshot) == 1  # one operation; one stat

            for name, stats in snapshot:
                stat = stats
            assert stat.count == 1, "Expected a single statistic"
            assert stat.min_reply_len == stat.max_reply_len
            assert stat.min_reply_len == exp_reply_len

    # Continue with validating the result

    if isinstance(raised_exception, pywbem.CIMError):
        cim_status = raised_exception.args[0]
    else:
        cim_status = 0
    assert cim_status == exp_cim_status, \
        "Error in WBEMConnection operation CIM status code. " \
        "Expected %s; received %s" % \
        (exp_cim_status, cim_status)

    # Returns either exp_result or exp_pull_result
    if exp_result is not None:
        exp_result_obj = obj(exp_result, tc_name)

        # The testcase can only specify lists but not tuples, so we
        # tolerate tuple/list mismatches:
        act_type = type(result)
        if act_type == tuple:
            act_type = list
        exp_type = type(exp_result_obj)
        # pylint: disable=unidiomatic-typecheck
        if act_type != exp_type:
            show_diff(None, type(exp_result_obj), type(result), 'type')
            raise AssertionError("PyWBEM CIM result type is not"
                                 " as expected.")

        # The testcase can only specify dicts but not NocaseDicts, so we
        # tolerate such mismatches (in case of InvokeMethod):
        if isinstance(exp_result_obj, list) and \
           len(exp_result_obj) == 2 and \
           isinstance(exp_result_obj[1], dict):
            _exp_result_obj = (
                exp_result_obj[0],
                NocaseDict(exp_result_obj[1])
            )
        else:
            _exp_result_obj = exp_result_obj

        # If result items are tuple, convert to lists. This is for
        # class ref and assoc results.
        if isinstance(result, list) and \
                result and isinstance(result[0], tuple):
            _result = []
            for item in result:
                if isinstance(item, tuple):
                    _result.append(list(item))
                else:
                    _result.append(item)
        else:
            _result = result

        if _result != _exp_result_obj:
            # TODO 2016/07 AM: Improve the presentation of the difference
            show_diff(conn, repr(exp_result_obj), repr(_result), 'data')
            raise AssertionError("WBEMConnection operation method result "
                                 "is not as expected.")

    # if this is a pull result, compare the components of expected
    # and actual results. Pull results return a tuple
    elif exp_pull_result is not None:
        exp_pull_result_obj = result_tuple(exp_pull_result, tc_name)

        # Result length should be the same as expected result
        if len(result) != len(exp_pull_result_obj):
            show_diff(conn, len(conn, exp_pull_result_obj), len(result),
                      'tuple size')
            raise AssertionError("PyWBEM CIM result type is not"
                                 " as expected.")
        # eos is required result
        if result.eos != exp_pull_result_obj.eos:
            show_diff(conn, exp_pull_result_obj.eos, result.eos,
                      'result.eos')
            raise AssertionError("WBEMConnection operation method result "
                                 "is not as expected.")

        # Context is required result
        # NOTE: pyaml does not natively support tuples. It supports very
        #   simple tuples but only with single objects and in block mode.
        exp_context = tuple(exp_pull_result_obj.context) \
            if exp_pull_result_obj.context \
            else None
        if result.context != exp_context:
            show_diff(conn, repr(str_tuple(exp_context)),
                      repr(str_tuple(result.context)), 'result.context')
            raise AssertionError("WBEMConnection operation method result "
                                 "is not as expected.")

        if "instances" in exp_pull_result:
            _result = result.instances
            _exp_result = exp_pull_result_obj.instances
        elif "paths" in exp_pull_result:
            _result = result.paths
            _exp_result = exp_pull_result_obj.paths
        else:
            raise AssertionError("WBEMConnection operation method result "
                                 "is not as expected. No 'instances' "
                                 "or 'paths' component.")

        if _result != _exp_result:
            # TODO 2016/07 AM: Improve the presentation of the diff.
            show_diff(conn, repr(_exp_result), repr(_result), 'result data')
            raise AssertionError("WBEMConnection operation method "
                                 "result is not as expected.")

        # TODO redo as indexed loop to compare all items.

    else:
        assert result is None, \
            "PyWBEM CIM result is not None: %s" % repr(result)


def result_tuple(value, tc_name):
    """
    Process the value (a dictionary) to create a named tuple of
    the components that are part of a pull result.

    Returns the  namedtuple of either
        instance, eos, context
    or
        paths, eos, context

    For openqueryinstances it returns a named tuple with 4 elements
    in place of 3
    """
    if isinstance(value, dict):
        # test for both paths and instances.
        objs = None
        if "query_result_class" in value:
            result = namedtuple("exp_result", ["instances", "eos", "context",
                                               "query_result_class"])
        else:
            result = namedtuple("exp_result", ["instances", "eos", "context"])

        # either path or instances should be in value
        if "instances" in value:
            # instances = value["instances"]
            objs = obj(value["instances"], tc_name)
            if 'paths' in value:
                raise AssertionError("WBEMConnection operation method "
                                     "result is not as expected. Both "
                                     "'instances' and 'paths' component.")
        elif "paths" in value:
            # paths = value["paths"]
            objs = obj(value["paths"], tc_name)
            result = namedtuple("result", ["paths", "eos", "context"])
        else:
            raise AssertionError("WBEMConnection operation method result "
                                 "is not as expected. No 'instances' "
                                 "or 'paths' component.")

        # if query_result_class in value, add it to result
        if "query_result_class" in value:
            return result(objs, value["eos"], value["context"],
                          value["query_result_class"])
        return result(objs, value["eos"], value["context"])

    else:
        raise AssertionError("WBEMConnection operation invalid tuple "
                             "definition.")
