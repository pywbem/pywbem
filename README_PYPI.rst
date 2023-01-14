.. # README file for Pypi

.. # Note: On Pypi, variable substitution with raw content is not enabled, so
.. # we have to specify the package version directly in the links.

.. # begin of customization for the current version
.. |pywbem-version-mn| replace:: 1.6
.. _Readme file on GitHub: https://github.com/pywbem/pywbem/blob/stable_1.6/README.rst
.. _Documentation on RTD: https://pywbem.readthedocs.io/en/stable_1.6/
.. _Change log on RTD: https://pywbem.readthedocs.io/en/stable_1.6/changes.html
.. # end of customization for the current version

Pywbem is a WBEM client and WBEM indication listener and provides related
WBEM client-side functionality. It is written in pure Python and runs on
Python 2 and Python 3.

WBEM is a standardized approach for systems management defined by the
`DMTF <https://www.dmtf.org>`_ that is used in the industry for a wide variety
of systems management tasks. See
`WBEM Standards <https://www.dmtf.org/standards/wbem>`_ for more information.
An important use of this approach is the
`SMI-S <https://www.snia.org/tech_activities/standards/curr_standards/smi>`_
standard defined by `SNIA <https://www.snia.org>`_ for managing storage.

A WBEM client allows issuing operations to a WBEM server for the purpose of
performing systems management tasks. A WBEM indication listener is used to wait
for and process notifications emitted by a WBEM server for the purpose of
systems management.

For more information on pywbem version |pywbem-version-mn|:

* `Readme file on GitHub`_
* `Documentation on RTD`_
* `Change log on RTD`_

.. _CIM/WBEM standards: https://www.dmtf.org/standards/wbem/
