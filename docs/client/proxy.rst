
.. _`Proxy support`:

Proxy support
-------------

Since version 1.0, pywbem supports HTTP and SOCKS 5 proxies for connecting to
the WBEM server. This is done by utilizing the proxy support in the
underlying `requests` Python package.

The proxies to be used can be specified using the ``proxies`` init argument
of :class:`~pywbem.WBEMConnection`, or via the environment variables HTTP_PROXY
and HTTPS_PROXY.

If the ``proxies`` init argument is not `None`, it takes precedence over the
environment variables and must be a dictionary with item keys 'http' and
'https'. Each item value specifies the URL of the proxy that is to be used for
the WBEM server protocol specified by the key.

In case of the environment variables, the value of HTTP_PROXY and HTTPS_PROXY
specify the URL of the proxy that is to be used for the http and https
WBEM server protocol, respectively.

If the proxy support is used, the ``url`` init argument of
:class:`~pywbem.WBEMConnection` specifies the connection properties the proxy
uses for connecting to the WBEM server. The ``no_verification``, ``ca_certs``,
and ``x509`` init arguments are also applied to the connection between the proxy
and the WBEM server. The URL of the proxy specified via the ``proxies`` init
argument or via the HTTP_PROXY and HTTPS_PROXY environment variables is what the
pywbem client uses to connect to the proxy.

The following examples show some typical cases and are not exhaustive. For the
full description of what is possible, refer to the `Proxies section`_  in the
documentation of the requests package. In these examples, the proxy URLs are
specified using the ``proxies`` init argument, but they can also be specified
using the HTTP_PROXY and HTTPS_PROXY environment variables.

Use of an HTTP proxy requiring authentication:

.. code-block:: python

    proxies = {
      'http': 'http://user:pass@10.10.1.10:3128',
      'https': 'http://user:pass@10.10.1.10:1080',
    }

    conn = pywbem.WBEMConnection(..., proxies=proxies)

Use of SOCKS proxies requires installing the socks option of the `requests`
Python package:

.. code-block:: bash

    $ pip install requests[socks]

Use of a SOCKS 5 proxy requiring authentication where the DNS resolution for the
WBEM server hostname is done on the client (where pywbem runs):

.. code-block:: python

    proxies = {
      'http': 'socks5://user:pass@10.10.1.10:3128',
      'https': 'socks5://user:pass@10.10.1.10:1080',
    }

    conn = pywbem.WBEMConnection(..., proxies=proxies)

Use of a SOCKS 5 proxy requiring authentication where the DNS resolution for the
WBEM server hostname is done on the proxy:

.. code-block:: python

    proxies = {
      'http': 'socks5h://user:pass@10.10.1.10:3128',
      'https': 'socks5h://user:pass@10.10.1.10:1080',
    }

    conn = pywbem.WBEMConnection(..., proxies=proxies)

.. _Proxies section: https://2.python-requests.org/en/master/user/advanced/#proxies
