.. # README file for Pypi

.. # Note: On Pypi, variable substitution with raw content is not enabled, so
.. # we have to specify the package version directly in the links.

.. # begin of customization for the current version
.. |pywbem-version-mn| replace:: 0.16
.. _Readme file on GitHub: https://github.com/pywbem/pywbem/blob/stable_0.16/README.rst
.. _Documentation on RTD: https://pywbem.readthedocs.io/en/stable_0.16/
.. _Change log on RTD: https://pywbem.readthedocs.io/en/stable_0.16/changes.html
.. # end of customization for the current version

Pywbem is a WBEM client, written in pure Python. It supports Python 2 and
Python 3. Pywbem also contains a WBEM indication listener.

A WBEM client allows issuing operations to a WBEM server, using the
`CIM/WBEM standards`_ defined by the DMTF, for the purpose of performing
systems management tasks. A WBEM indication listener is used to wait for
and process notifications emitted by a WBEM server, also for the purpose
of systems management.

CIM/WBEM infrastructure is used for a wide variety of systems management
tasks in the industry.

For more information on pywbem version |pywbem-version-mn|:

* `Readme file on GitHub`_
* `Documentation on RTD`_
* `Change log on RTD`_

.. _CIM/WBEM standards: https://www.dmtf.org/standards/wbem/
