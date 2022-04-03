# Connection and timeout errors

## Behavior of requests and urllib3 packages

This section describes the behavior of "requests" and "urllib3" Python packages
for raising exceptions that are related to connection and timeout errors.

### Details about the test setup

The observations were made with the following versions:
* requests: 2.27.1
* urllib3: 1.26.9
* Python: 3.9.10
* OpenSSL: 1.1.1m
* macOS: 11.6.4
* OpenPegasus container: kschopmeyer/openpegasus-server:0.1.1

The server in the OpenPegasus container provides a CIM method whose execution
duration can be controlled with an input parameter.

The tests were performed with pywbemcli which invokes that method
to trigger timeouts during execution. The 'pegasus' connection that is used
in the commands has the following attributes:

```
$ pywbemcli connection show pegasus
Connection status:
name               value  (state)
-----------------  ----------------------
name               pegasus
server             https://localhost:5989
default-namespace  root/cimv2
user
password
timeout            60
use-pull
pull-max-cnt       1000
verify             False
certfile
keyfile
mock-server
ca-certs
```

The `urllib3.Retry` parameters were changed in the pywbem source code as needed
for a test. This is documented in the respective tests, below.

The pywbem code was instrumented as follows. Lines marked with `+` have been added.

In `pywbem/_cim_http.py`:

```
+def debug_exc(exc):
+    arg_strings = [
+        # "dir(exc)={}".format(dir(exc)),
+        # "dir(exc.request)={}".format(dir(exc.request)),
+        # "dir(exc.response)={}".format(dir(exc.response)),
+    ]
+    for i, arg in enumerate(exc.args):
+        arg_strings.append("arg[{}] ({}) = {}".format(i, type(arg), arg))
+    message = "; ".join(arg_strings)
+    return message

 def wbem_request(. . .):
     . . .
     try:
+        try:
+            print("Debug: pywbem wbem_request: Calling session.post() with timeout=(connect={}, read={}) for {} on {} with {}".
+                  format(HTTP_CONNECT_TIMEOUT, conn.timeout, cimxml_headers[1][1], cimxml_headers[2][1], conn.session.adapters['https://'].max_retries))
             resp = conn.session.post(
                 target_url, data=req_body, headers=req_headers,
                 timeout=(HTTP_CONNECT_TIMEOUT, conn.timeout))
+        except Exception as _exc:
+            print("Debug: pywbem wbem_request: session.post() raised: {}".format(debug_exc(_exc)))
+            raise
     except requests.exceptions.SSLError as exc:
     . . .
```

After doing some initial investigation without that, the urllib3 code was instrumented
with debug code as follows, all in `connectionpool.py`. The added lines are marked with `+`:

```
 def _make_request(. . .):
     """
     . . .
     """

     self.num_requests += 1

     timeout_obj = self._get_timeout(timeout)
     timeout_obj.start_connect()
     conn.timeout = timeout_obj.connect_timeout

+    print("Debug: urllib3 _make_request: Called with timeout={}; using conn.timeout={}".format(timeout, conn.timeout))

     # Trigger any extra validation we need to do.
     try:
+        try:
             self._validate_conn(conn)
+        except Exception as _exc:
+            print("Debug: urllib3 _make_request: _validate_conn() raised {}: {}".format(type(_exc), _exc))
+            raise
     except (SocketTimeout, BaseSSLError) as e:
         # Py2 raises this as a BaseSSLError, Py3 raises it as socket timeout.
         self._raise_timeout(err=e, url=url, timeout_value=conn.timeout)
         raise

     # conn.request() calls http.client.*.request, not the method in
     # urllib3.request. It also calls makefile (recv) on the socket.
     try:
         if chunked:
+            try:
                 conn.request_chunked(method, url, **httplib_request_kw)
+            except Exception as _exc:
+                print("Debug: urllib3 _make_request: conn.request_chunked() raised {}: {}".format(type(_exc), _exc))
+                raise
         else:
+             try:
                 conn.request(method, url, **httplib_request_kw)
+            except Exception as _exc:
+                print("Debug: urllib3 _make_request: conn.request() raised {}: {}".format(type(_exc), _exc))
+                raise
```

### Test case 1: Connection to localhost with non-existing port

In this test case, the OpenPegasus container is stopped, so that the targeted
port 5989 is not handled by any process on the local system.

```
$ pywbemcli --timeout 15 -n pegasus class invokemethod Test_CLITestProviderClass delayedMethodResponse -p delayInSeconds=20 -n test/TestProvider

Debug: pywbem wbem_request: Calling session.post() with timeout=(connect=9.5, read=15) for GetClass on test/TestProvider with
  Retry(total=None, connect=2, read=0, redirect=5, status=0)

Debug: urllib3 _make_request: Called with timeout=Timeout(connect=9.5, read=15, total=None); using conn.timeout=9.5
Debug: urllib3 _make_request: _validate_conn() raised <class 'urllib3.exceptions.NewConnectionError'>: <urllib3.connection.HTTPSConnection object at
  0x10aa7c400>: Failed to establish a new connection: [Errno 61] Connection refused

Debug: urllib3 _make_request: Called with timeout=Timeout(connect=9.5, read=15, total=None); using conn.timeout=9.5
Debug: urllib3 _make_request: _validate_conn() raised <class 'urllib3.exceptions.NewConnectionError'>: <urllib3.connection.HTTPSConnection object at
  0x10aa7c430>: Failed to establish a new connection: [Errno 61] Connection refused

Debug: urllib3 _make_request: Called with timeout=Timeout(connect=9.5, read=15, total=None); using conn.timeout=9.5
Debug: urllib3 _make_request: _validate_conn() raised <class 'urllib3.exceptions.NewConnectionError'>: <urllib3.connection.HTTPSConnection object at
  0x10aa7c7c0>: Failed to establish a new connection: [Errno 61] Connection refused

Debug: pywbem wbem_request: session.post() raised: exception: <class 'requests.exceptions.ConnectionError'>;
  arg[0] (<class 'urllib3.exceptions.MaxRetryError'>) = HTTPSConnectionPool(host='localhost', port=5989): Max retries exceeded with url: /cimom
  (Caused by NewConnectionError('<urllib3.connection.HTTPSConnection object at 0x10aa7c7c0>: Failed to establish a new connection: [Errno 61]
  Connection refused'))

Error: ConnectionError: Failed to establish a new connection: [Errno 61] Connection refused; OpenSSL version used: OpenSSL 1.1.1m  14 Dec 2021
```

The Error message shown at the end already contains some improvements from the original code.

To verify the overall duration until an error was returned, a small measurement series was performed with different values for
`HTTP_CONNECT_RETRIES` (setting the `connect` attribute of `urllib3.Retry`) and `HTTP_TOTAL_RETRIES` (setting the `total` attribute of
`urllib3.Retry`):

With backoff_factor=0.1 and timeout=(connect=9.5, read=15):

| total   | connect | duration [sec] | # _make_request |
| -------:| -------:| --------------:| ---------------:|
|       2 |       2 |            1.1 |               3 |
|       3 |       3 |            1.2 |               4 |
|       4 |       4 |            2.2 |               5 |
|       5 |       5 |            3.8 |               6 |
|       6 |       6 |            6.8 |               7 |
|       7 |       7 |           13.5 |               8 |
|       8 |       8 |           26.1 |               9 |
|       9 |       9 |           52.0 |              10 |
|      10 |      10 |          103.0 |              11 |
|       2 |      10 |            1.1 |               3 |
|    None |      10 |          102.8 |              11 |

With backoff_factor=0.2 and timeout=(connect=9.5, read=15):

| total   | connect | duration [sec] | # _make_request |
| -------:| -------:| --------------:| ---------------:|
|       2 |       2 |            1.4 |               3 |
|       3 |       3 |            2.1 |               4 |
|       4 |       4 |            3.8 |               5 |
|       5 |       5 |            6.6 |               6 |
|       6 |       6 |           14.1 |               7 |
|       7 |       7 |           25.8 |               8 |

Observations:

* The `urllib3.exceptions.MaxRetryError` exception is represented as `args[0]` of the `requests.exceptions.ConnectionError`
  exception raised by from requests's `session.post()`. That exception is caused by a `urllib3.exceptions.NewConnectionError`.

* For small numbers of retries, the exception is raised quicker than the connection timeout of 10 sec (specified
  at the level of the requests HTTPS adapter). This means that connection timeout does not play a role in this case.

* Retries on connections are in fact performed and are controlled by the `connect` attribute of `urllib3.Retry`.
  The duration between retries increases based on the backoff algorithm and that is controlled by the
  `backoff_factor` attribute of `urllib3.Retry`, just as documented in urllib3.

* The `total` attribute of `urllib3.Retry` does in fact override the `connect` attribute if not `None`, and does
  not override it if `None`, just as documented in urllib3.

### Test case 2: Connection to localhost with paused server

In this test case, the OpenPegasus container is started and then paused. Apparently that allows the TLS connection
to port 5989 until some point, but the server cannot do any processing.

```
$ pywbemcli --timeout 15 -n pegasus class invokemethod Test_CLITestProviderClass delayedMethodResponse -p delayInSeconds=20 -n test/TestProvider

Debug: pywbem wbem_request: Calling session.post() with timeout=(connect=9.5, read=15) for GetClass on test/TestProvider with
  Retry(total=None, connect=2, read=0, redirect=5, status=0)

Debug: urllib3 _make_request: Called with timeout=Timeout(connect=9.5, read=15, total=None); using conn.timeout=9.5
Debug: urllib3 _make_request: _validate_conn() raised <class 'socket.timeout'>: _ssl.c:1112: The handshake operation timed out

Debug: pywbem wbem_request: session.post() raised: exception: <class 'requests.exceptions.ConnectionError'>;
  arg[0] (<class 'urllib3.exceptions.MaxRetryError'>) = HTTPSConnectionPool(host='localhost', port=5989): Max retries exceeded with url: /cimom
  (Caused by ReadTimeoutError("HTTPSConnectionPool(host='localhost', port=5989): Read timed out. (read timeout=9.5)"))

Error: ConnectionError: Read timed out. (read timeout=9.5); OpenSSL version used: OpenSSL 1.1.1m  14 Dec 2021
```

The Error message shown at the end already contains some improvements from the original code.

With backoff_factor=0.1, total=None and timeout=(connect=9.5, read=15):

| connect | read    | duration [sec] | # _make_request |
| -------:| -------:| --------------:| ---------------:|
|       2 |       1 |           20.5 |               2 |
|       3 |       1 |           20.7 |               2 |
|       2 |       2 |           31.2 |               3 |
|       2 |       3 |           41.7 |               4 |

Observations:

* The `urllib3.exceptions.MaxRetryError` exception is represented as `args[0]` of the `requests.exceptions.ConnectionError`
  exception raised by from requests's `session.post()`. That exception is caused by a `urllib3.exceptions.ReadTimeoutError`.
  The configured connect timeout of 9.5 sec is reported in the `ReadTimeoutError` exception.

* urllib3 re-raises the `socket.timeout` error it gets, as `ReadTimeoutError`.
  I have reported this urllib3 behavior as https://github.com/urllib3/urllib3/issues/2591.

* The timeout that is used between the retries is the configured connect timeout (10 sec), which is ok because this
  is a connection issue ("The handshake operation timed out").

* The retries that are used are the read retries. The connect retries do not influence the duration
  until the exception. That is a problem, and is also mentioned in the urllib3 issue I created.

### Test case 3: Connection to localhost with running server and operation that times out

In this test case, the OpenPegasus container is started so that it handles requests properly.

```
$ pywbemcli --timeout 15 -n pegasus class invokemethod Test_CLITestProviderClass delayedMethodResponse -p delayInSeconds=20 -n test/TestProvider

Debug: pywbem wbem_request: Calling session.post() with timeout=(connect=9.5, read=15) for GetClass on test/TestProvider with
  Retry(total=None, connect=2, read=0, redirect=5, status=0)

Debug: urllib3 _make_request: Called with timeout=Timeout(connect=9.5, read=15, total=None); using conn.timeout=9.5

Debug: pywbem wbem_request: Calling session.post() with timeout=(connect=9.5, read=15) for delayedMethodResponse on
  test/TestProvider:Test_CLITestProviderClass with Retry(total=None, connect=2, read=0, redirect=5, status=0)

Debug: urllib3 _make_request: Called with timeout=Timeout(connect=9.5, read=15, total=None); using conn.timeout=9.5
Debug: urllib3 _make_request: conn.getresponse() raised <class 'socket.timeout'>: The read operation timed out

Debug: pywbem wbem_request: session.post() raised: exception: <class 'requests.exceptions.ConnectionError'>;
  arg[0] (<class 'urllib3.exceptions.MaxRetryError'>) = HTTPSConnectionPool(host='localhost', port=5989): Max retries exceeded with url: /cimom
  (Caused by ReadTimeoutError("HTTPSConnectionPool(host='localhost', port=5989): Read timed out. (read timeout=15)"))

Error: TimeoutError: Read timed out. (read timeout=15); OpenSSL version used: OpenSSL 1.1.1m  14 Dec 2021
```

The Error message shown at the end already contains some improvements from the original code.

With backoff_factor=0.1, total=None and timeout=(connect=9.5, read=15):

| connect | read    | duration [sec] | # _make_request |
| -------:| -------:| --------------:| ---------------:|
|       2 |       0 |           15.9 |               1 |
|       2 |       1 |           30.8 |               2 |
|       2 |       2 |           45.9 |               3 |

Observations:

* The `urllib3.exceptions.MaxRetryError` exception is represented as `args[0]` of the `requests.exceptions.ConnectionError`
  exception raised by from requests's `session.post()`. That exception is caused by a `urllib3.exceptions.ReadTimeoutError`.
  The configured read timeout of 15 sec is reported in the `ReadTimeoutError` exception.

* Retries are performed and are controlled by the `read` attribute of `urllib3.Retry`.
  The duration between retries is determined by the read timeout of 15 sec that is set on the
  requests adapter for HTTPS.

### Test case 4: Connection to localhost with running server and server stopped while waiting for operation response

In this test case, the OpenPegasus container is started so that it handles requests properly.
While the pywbemcli command is running, the OpenPegasus container is stopped. Since this takes several seconds,
the operation duration and the operation timeout have been increased.

```
$ pywbemcli --timeout 35 -n pegasus class invokemethod Test_CLITestProviderClass delayedMethodResponse -p delayInSeconds=40 -n test/TestProvider

Debug: pywbem wbem_request: Calling session.post() with timeout=(connect=9.5, read=35) for GetClass on test/TestProvider with
  Retry(total=None, connect=2, read=0, redirect=5, status=0)

Debug: urllib3 _make_request: Called with timeout=Timeout(connect=9.5, read=35, total=None); using conn.timeout=9.5

Debug: pywbem wbem_request: Calling session.post() with timeout=(connect=9.5, read=35) for delayedMethodResponse on
  test/TestProvider:Test_CLITestProviderClass with Retry(total=None, connect=2, read=0, redirect=5, status=0)

Debug: urllib3 _make_request: Called with timeout=Timeout(connect=9.5, read=35, total=None); using conn.timeout=9.5

--> docker container stopped while waiting for the operation response
```

The Error message shown at the end already contains some improvements from the original code.

From here on, different errors may be raised:

For read retry 0:

```
Debug: urllib3 _make_request: conn.getresponse() raised <class 'http.client.RemoteDisconnected'>: Remote end closed connection without response

Debug: pywbem wbem_request: session.post() raised: exception: <class 'requests.exceptions.ConnectionError'>;
  arg[0] (<class 'urllib3.exceptions.MaxRetryError'>) = HTTPSConnectionPool(host='localhost', port=5989): Max retries exceeded with url: /cimom
  (Caused by ProtocolError('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')))

Error: ConnectionError: Connection aborted.', RemoteDisconnected('Remote end closed connection without response'); OpenSSL version used: OpenSSL 1.1.1m  14 Dec 2021
```

For read retry 1:

```
Debug: urllib3 _make_request: conn.getresponse() raised <class 'http.client.RemoteDisconnected'>: Remote end closed connection without response

Debug: urllib3 _make_request: Called with timeout=Timeout(connect=9.5, read=35, total=None); using conn.timeout=9.5
Debug: urllib3 _make_request: _validate_conn() raised <class 'ssl.SSLEOFError'>: EOF occurred in violation of protocol (_ssl.c:1129)

Debug: pywbem wbem_request: session.post() raised: exception: <class 'requests.exceptions.SSLError'>;
  arg[0] (<class 'urllib3.exceptions.MaxRetryError'>) = HTTPSConnectionPool(host='localhost', port=5989): Max retries exceeded with url: /cimom
  (Caused by SSLError(SSLEOFError(8, 'EOF occurred in violation of protocol (_ssl.c:1129)')))

/Users/maiera/PycharmProjects/pywbem/pywbem/pywbem/_cim_http.py:349: UserWarning: Unknown urllib3 exception SSLError is re-raised as ConnectionError
  warnings.warn(

Error: ConnectionError: SSLEOFError(8, 'EOF occurred in violation of protocol (_ssl.c:1129)'); OpenSSL version used: OpenSSL 1.1.1m  14 Dec 2021
```

Observations:

* A read retry hides the originally raised meaningful exception `ProtocolError`, and causes the not so meaningful exception
  `SSLError` to be surfaced.

## Summary of new pywbem exception message transformations

This summarizes how pywbem maps requests and urllib3 exceptions to its own exceptions, after the redesign:

* any requests exception with urllib3.exceptions.MaxRetryError:
  - as pywbem.ConnectionError with CIM specific message, if caused by ReadTimeoutError with WBEMConnection timeout
  - as pywbem.TimeoutError with CIM specific message, if caused by ReadTimeoutError with other timeout
  - as pywbem.ConnectionError with original message, if caused by NewConnectionError
  - as pywbem.ConnectionError with original message, if caused by ProtocolError
  - as pywbem.ConnectionError with original message, otherwise

* requests.exceptions.SSLError:
  - as pywbem.ConnectionError with original message, amended by OpenSSL version

* requests.exceptions.ReadTimeout:
  - as pywbem.TimeoutError with original message

* requests.exceptions.RetryError:
  - as pywbem.TimeoutError with original message

* otherwise:
  - as pywbem.ConnectionError with original message

## Summary of new exception messages in the testcases shown above

* Test case 1:
  `ConnectionError: Failed to establish a new connection: [Errno 61] Connection refused`

* Test case 2:
  `ConnectionError: Could not send request to {url} within 10 sec`

* Test case 3:
  `TimeoutError: No response received from {url} within {timeout} sec`

* Test case 4:
  `ConnectionError: Connection aborted.', RemoteDisconnected('Remote end closed connection without response')`
