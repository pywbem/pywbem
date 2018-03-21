
.. _`Security considerations`:

Security considerations
-----------------------

.. _`Authentication types`:

Authentication types
^^^^^^^^^^^^^^^^^^^^

Authentication is the act of establishing the identity of a user on the
client side to the server, and possibly also of establishing the identity of a
server to the client.

There are two levels of authentication in CIM-XML:

* TLS/SSL level authentication (only when HTTPS is used):

  This kind of authentication is also known as *transport level authentication*.
  It is used during the TLS/SSL handshake protocol, before any HTTP requests
  flow.

  In almost all cases (unless an anonymous cipher is used), this involves
  an :term:`X.509` certificate that is presented by the server (therefore called
  *server certificate*) and that allows the client to establish the identity
  of the server.

  It optionally involves an X.509 certificate that is presented by the client
  (therefore called client certificate) and that allows the server to establish
  the identity of the client or even of the client user, and thus can avoid
  the use of credentials in the HTTP level authentication.

  If a client certificate is used, the authentication scheme at the TLS/SSL
  level is called *2-way authentication* (also known as *client authentication*
  or *mutual SSL authentication*). If a client certificate is not
  used, the authentication scheme is called *1-way authentication* (also known
  as *SSL authentication*).

  Userid/password credentials do not play any role in TLS/SSL level
  authentication.

* HTTP level authentication:

  This kind of authentication is used in HTTP/HTTPS requests and responses (in
  case of HTTPS, after the TLS/SSL handshake protocol has completed).

  In case of *Basic Authentication* and *Digest Authentication* (see
  :term:`RFC2617`), it involves passing credentials (userid and password) via
  the ``Authenticate`` and ``WWW-Authenticate`` HTTP headers. In case of *no
  authentication*, credentials are not passed.

  A client can either provide the ``Authenticate`` header along with a request,
  hoping that the server supports the authentication scheme that was used.

  A client can also omit that header in the request, causing the server to send
  an error response with a ``WWW-Authenticate`` header that tells the client
  which authentication types are supported by the server (also known as a
  *challenge*). The client then repeats the first request with one of the
  supported authentication types.

  HTTP is extensible w.r.t. authentication schemes, and so is CIM-XML.
  However, pywbem only supports Basic Authentication and no authentication.

  X.509 certificates do not play any role in HTTP level authentication.

HTTP/HTTPS knows a third level of authentication by the use of *session
cookies*. CIM-XML does not define how cookies would be used, and pywbem does
not deal with cookies in any way (i.e. it does not pass cookies provided in a
response into the next request).

The following table shows the possible combinations of protocol, TLS/SSL level
and HTTP level authentication schemes, which information items need to be
provided to the WBEM client API, and whether the combination is supported
by pywbem:

======== ========== =========== =========== ============ ======== =========
Protocol SSL auth.  HTTP auth.  Credentials Client cert. CA cert. Supported
======== ========== =========== =========== ============ ======== =========
HTTP     N/A        None        No          No           No       Yes (1)
HTTP     N/A        Basic       Yes         No           No       Yes (2)
HTTP     N/A        Digest      Yes         No           No       No
HTTPS    1-way      None        No          No           Yes (3)  Yes (1)
HTTPS    1-way      Basic       Yes         No           Yes (3)  Yes
HTTPS    1-way      Digest      Yes         No           Yes (3)  No
HTTPS    2-way      None        No          Yes          Yes (3)  Yes (4)
HTTPS    2-way      Basic       Yes         Yes          Yes (3)  Yes
HTTPS    2-way      Digest      Yes         Yes          Yes (3)  No
======== ========== =========== =========== ============ ======== =========

Notes:

(1) This option does not allow a server to establish the identity of the user.
    Its use should be limited to environments where network access is secured.
(2) The use of HTTP Basic Authentication is strongly discouraged, because the
    password is sent unencrypted over the network.
(3) A CA certificate is needed, unless server certificate verification is
    disabled via the `no_verification` parameter (not recommended), or unless
    an anonymous cipher is used for the server certificate (not recommended).
(4) This is the most desirable option from a security perspective, if the
    WBEM server is able to establish the user identity based on the client
    certificate.

The protocol and authentication types that can be used on a connection to a
WBEM server are set by the user when creating the
:class:`~pywbem.WBEMConnection` object:

* The scheme of the URL in the `url` parameter controls whether the HTTP or
  HTTPS protocol is used.
* The `cred` parameter may specify credentials (userid/password). If specified,
  pywbem uses them for Basic Authentication at the HTTP level. Pywbem provides
  an ``Authenticate`` HTTP header on each request, and also handles server
  challenges transparently to the user of the WBEM client API, by retrying the
  original request.
* The `x509` parameter may specify an X.509 client certificate and key. If
  specified, pywbem uses 2-way authentication; otherwise it uses 1-way
  authentication at the TLS/SSL level.
* The `ca_certs` parameter may specify the location of X.509 CA certificates
  that are used to validate the X.509 server certificate returned by the WBEM
  server. If not specified, pywbem assumes default locations for these
  certificates (see :attr:`~pywbem.cim_http.DEFAULT_CA_CERT_PATHS`).

It is important to understand which side actually makes decisions about
security-related parameters: The client only decides whether HTTP or HTTPS is
used, and whether the server certificate is verified. The server decides
everything else: Which HTTP authentication scheme is used (None, Basic,
Digest), whether an X.509 client certificate is requested from the client and
if so, whether it tolerates a client not providing one. In addition, when HTTPS
is used, the client proposes cipher suites it supports, and the server picks
one of them.

Therefore, the `cred` and `x509` parameters do not control the authentication
scheme that is actually used, but merely prepare pywbem to deal with whatever
authentication scheme the WBEM server elects to use.

WBEM servers typically support corresponding configuration parameters.

.. _`Verification of the X.509 server certificate`:

Verification of the X.509 server certificate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When using HTTPS, the TLS/SSL handshake protocol requires that the server always
returns an :term:`X.509` server certificate to the client (unless anonymous
ciphers are used, which is not recommended).

Pywbem performs the following verifications on the server certificate returned
by the WBEM server:

* Validation of the server certificate against the CA certificates specified in
  the `ca_certs` parameter. This is done by the TLS/SSL components used by
  pywbem.
* Validation of the server certificate's expiration date, based on the system
  clock. This is done by the TLS/SSL components used by pywbem.
* Validation of the hostname, by comparing the Subject attribute of the server
  certificate with the hostname specified in the `url` parameter.
  This is done by pywbem itself.
* Calling the validation function specified in the `verify_callback` parameter,
  if any, and looking at its validation result.

If any of these validations fails, the WBEM operation methods of the
:class:`~pywbem.WBEMConnection` object raise a :exc:`pywbem.AuthError`.

If verification was disabled via the `no_verification` parameter, none of these
validations of the server certificate happens.

.. _`Use of X.509 client certificates`:

Use of X.509 client certificates
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When using HTTPS, the TLS/SSL handshake protocol provides the option for the
client to present an X.509 certificate to the server (therefore called client
certificate).

This procedure is initiated by the server, by requesting that the client
present a client certificate. If the client does not have one (for example,
because the `x509` parameter was not specified in pywbem), it must send an
empty list of certificates to the server. Depending on the server
configuration, the server may or may not accept an empty list. If a client
certificate is presented, the server must validate it.

The server can support to accept the user identity specified in the client
certificate as the user's identity, and refrain from sending HTTP challenges
that request credentials.

.. _`Authentication errors`:

Authentication errors
^^^^^^^^^^^^^^^^^^^^^

The operation methods of :class:`~pywbem.WBEMConnection` raise
:exc:`pywbem.AuthError` in any of these situations:

* When client side verification of the X.509 server certificate fails.

* When the WBEM server returns HTTP status 401 "Unauthorized" and the
  retries in the client are exhausted. The server typically returns
  that status in any of these situations:

  - no authorization information provided by client
  - wrong HTTP authentication scheme used by client
  - authentication failed
  - user is not authorized to access resource

.. _`Default CA certificate paths`:

Default CA certificate paths
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. autodata:: pywbem.cim_http.DEFAULT_CA_CERT_PATHS
