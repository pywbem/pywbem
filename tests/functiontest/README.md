End-to-end testing for the PyWBEM client
========================================

This directory contains YAML files that are test cases for testing the PyWBEM
client end-to-end.

Each YAML file contains a list of test cases.

The test_client.py test module will iterate through the YAML files in this
directory, and execute each testcase in each file.

Example YAML
------------

The following YAML is an example for one testcase in such a file:

    -
        name: demo1
        description: Demo #1, using GetInstance
        pywbem_request:
            url: http://acme.com:80
            creds:
                - username
                - password
            namespace: root/cimv2
            timeout: 10
            debug: false
            enable_stats: true
            operation:
                pywbem_method: GetInstance
                InstanceName:
                    pywbem_object: CIMInstanceName
                    classname: PyWBEM_Person
                    keybindings:
                        Name: Fritz
                LocalOnly: false
        pywbem_response:
            request_len: 100
            reply_len: 100
            result:
                pywbem_object: CIMInstance
                classname: PyWBEM_Person
                properties:
                    Name: Fritz
                    Address: Fritz Town
                path:
                    pywbem_object: CIMInstanceName
                    classname: PyWBEM_Person
                    namespace: root/cimv2
                    keybindings:
                        Name: Fritz
        http_request:
            verb: POST
            url: http://acme.com:80/cimom
            headers:
                CIMOperation: MethodCall
                CIMMethod: GetInstance
                CIMObject: root/cimv2
            data: >
                <?xml version="1.0" encoding="utf-8" ?>
                <CIM CIMVERSION="2.0" DTDVERSION="2.0">
                  <MESSAGE ID="1001" PROTOCOLVERSION="1.0">
                    <SIMPLEREQ>
                      <IMETHODCALL NAME="GetInstance">
                        <LOCALNAMESPACEPATH>
                          <NAMESPACE NAME="root"/>
                          <NAMESPACE NAME="cimv2"/>
                        </LOCALNAMESPACEPATH>
                        <IPARAMVALUE NAME="InstanceName">
                          <INSTANCENAME CLASSNAME="PyWBEM_Person">
                            <KEYBINDING NAME="Name">
                              <KEYVALUE VALUETYPE="string">Fritz</KEYVALUE>
                            </KEYBINDING>
                          </INSTANCENAME>
                        </IPARAMVALUE>
                        <IPARAMVALUE NAME="LocalOnly">
                          <VALUE>FALSE</VALUE>
                        </IPARAMVALUE>
                      </IMETHODCALL>
                    </SIMPLEREQ>
                  </MESSAGE>
                </CIM>
        http_response:
            status: 200
            headers:
                CIMOperation: MethodResponse
            data: >
                <?xml version="1.0" encoding="utf-8" ?>
                <CIM CIMVERSION="2.0" DTDVERSION="2.0">
                  <MESSAGE ID="1001" PROTOCOLVERSION="1.0">
                    <SIMPLERSP>
                      <IMETHODRESPONSE NAME="GetInstance">
                        <IRETURNVALUE>
                          <INSTANCE CLASSNAME="PyWBEM_Person">
                            <PROPERTY NAME="Name" TYPE="string">
                              <VALUE>Fritz</VALUE>
                            </PROPERTY>
                            <PROPERTY NAME="Address" TYPE="string">
                              <VALUE>Fritz Town</VALUE>
                            </PROPERTY>
                          </INSTANCE>
                        </IRETURNVALUE>
                      </IMETHODRESPONSE>
                    </SIMPLERSP>
                  </MESSAGE>
                </CIM>

Top-level elements
------------------

The top-level elements in the test case YAML are:

* `name`:
  A name for the test case that is used in error messages.

* `description`:
  A short description of the testcase.

* `ignore_python_version`
  A single digit python version (2 or 3) that tells the client code to
  ignore this test for that python version.  Should only be used in rare
  cases where a test is really version dependent. To date the only case
  is in HTTPS timeout processing where python 2 has an issue with mock.

* `ignore_test`
  If this element exists, the test is bypassed.  This is a way to temporarily
  bypass tests that are causing problems without hiding or removing the code.
  It should only be used in rare cases. Please document any use of this
  options. If the command line option to run a single test is set
  this element is ignored.

* `pywbem_request`:
  A specification of the PyWBEM client function to test, and the input
  arguments for its invocation.

* `pywbem_response`:
  A specification of the expected result of the PyWBEM client function that is
  being tested. It is possible to specify expected CIM status codes, other
  Python exceptions, or the resulting object in case of success.

* `http_request`:
  A specification of the expected HTTP request the PyWBEM client produced
  for the client function that is being tested. This includes the first line
  of the HTTP request, any HTTP headers, and the CIM body data (the CIM-XML)

* `http_response`:
  The HTTP response for the PyWBEM client function that will be handed back
  to the client function that is being tested.
  It is possible to specify successful eresponses, error responses, and even
  inconsistent or illegal responses in order to verify how the client handles
  those.

Elements in `pywbem_request` element
------------------------------------

* `url`, `creds`, `namespace`, `timeout`:
  The same-named arguments of pywbem.WBEMConnection()

* `debug`:
  Boolean indicating whether the PyWBEM client enables debug mode.

* `enable_stats`:
  Boolean indicating whether the PyWBEM client enables gathering statistical
  information on operations.

* `operation`:
  A specification of the WBEMConnection method (= CIM operation) to be
  invoked. Its child elements are:

  * `pywbem_method`:
    Name of the Python method of pywbem.WBEMConnection as a string
    (e.g. "GetInstance").

  * arguments for that Python method. Each element has the argument's name.

    If its Python type is boolean, string, or numerical, the element's
    value is directly the desired argument value.

    Otherwise, the element has child elements that specify how the Python
    object is constructed, as follows:

    * `pywbem_object`:
      Name of the Python type to construct (i.e. the constructor), as a string.
      (e.g. "CIMInstanceName").

    * arguments for that constructor. Each element has the argument's name. This
      can be nested at arbitraty depth, see the description of the arguments one
      level up.

Elements in `pywbem_response` element
-------------------------------------

* `cim_status`:
  The numerical expected CIM status code of the operation.
  This is optional; if not specified, it defaults to 0 (=Success).

* `exception`:
  The name of the Python exception that is expectd to be raised.
  This is optional; if not specified, it defaults to None (=no exception is
  raised).

* `request_len`:
  Defines expected length of the request. If this element exists, the
  value is tested against the last_req_len field of the connection. If not
  specified the test is bypassed.

* `reply_len`:
  Defines expected length of the response. If this element exists, the
  value is tested against the last_reply_len field of the connection. If not
  specified the test is bypassed.

* `result`:
  A specification of the expected result (= return value) of the operation,
  implying that the operation succeeded when this is not the result to one
  of the pull operations (Open..., Pull...). Use the `pullresult` element to
  define the results of the pull operations.

  If the Python type of the result is boolean, string, or numerical, the
  element's value is directly the desired argument value.

  Otherwise, the element has child elements that specify how the Python
  object is constructed, as follows:

  * `pywbem_object`:
    Name of the Python type to construct (i.e. the constructor), as a string.
    (e.g. "CIMInstanceName").

  * arguments for that constructor. Each element has the argument's name. This
    can be nested at arbitraty depth, see the description of the arguments one
    level up.

* `pullresult`:
  A specification of the expected result (=return values) of the operation
  implying that the operation succeeded for any of the pull operation requests.
  This is required because, unlike the original operations, the pull operations
  return a tuple of information for every response including (context for the
  enumeration session, end_of_sequence indicator, and the array of instances
  that were included in the response by the server).

  The return is a named tuple with the  element names defined as follows:
  TBD

  The subelements of pullresult are:

  * `context` Specified either as a string or `null` if no context is to
    be returned to the user

  * `eos` Boolean `True` or `False` indicating whether this was the
    final response of an enumeration session. To be correct the `context`
    must be `null` if the `eos` is `True`.

  * `instances` or `paths` depending on whether instances or instance names
    are being returned. The chile element to this element specifies the
    Python object to be constructed in the same manner as the child elements
    of `result`.

Elements in `http_request` element
------------------------------------

* `verb`:
  The expected HTTP verb / method the PyWBEM client issues (e.g. "POST").

* `url`:
  The expected URL the PyWBEM client targets the HTTP request to
  (e.g. "http://acme.com:80/cimom").
  Note that this is the url specified as an argument to pywbem.WBEMConnection,
  appended with "/cimom".

* `headers`:
  The expected HTTP header fields in the HTTP request. Only the onese specified
  here are verified, others may be present and will not be verified.

  The name of the element is the header field name, and its value is the
  header field value. Header field names are treated case insensitively.

* `data`:
  The expected CIM-XML payload of the request. When comparing the actual CIM-XML
  to the expected CIM-XML, whitespace in between XML elements (tags) and
  attributes are being ignored.

Elements in `http_response` element
-------------------------------------

* `exception`:
  The specification of an expected exception at the socket level, during sending
  of the HTTP request, by specifying the name of the static method of the
  `test_client.CallBack` class.

  This is optional; if not specified, it defaults to None (=no exception is
  raised). If specified, the other elements will be ignored.

  The following method names can be specified:

  * `socket_ssl`
    A `socket.sslerror` exception with arbitrary error code.

  * `socket_104`
    A `socket.error` exception with error code 104.

  * `socket_32`
    A `socket.error` exception with error code 32.

* `status`:
  The numerical HTTP status in the HTTP response handed back to the PyWBEM
  client (e.g. 200).

* `headers`:
  The HTTP header fields in the HTTP response handed back to the PyWBEM
  client.

  TBD: Does HTTPretty have any standard header fields it adds?

  The name of the element is the header field name, and its value is the
  header field value. Header field names are treated case insensitively.

* `data`:
  The CIM-XML payload in the HTTP response handed back to the PyWBEM
  client. The CIm-XML is handed back as resulting from the specified
  YAML, including any whitespace.
