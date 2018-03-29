
.. _`MOF compiler API`:

MOF compiler API
================

.. automodule:: pywbem.mof_compiler

.. _`MOFCompiler Class`:

MOFCompiler Class
-----------------

.. autoclass:: pywbem.MOFCompiler
   :members:

.. _`Repository connections`:

Repository connections
----------------------

.. autoclass:: pywbem.BaseRepositoryConnection
   :members:

.. autoclass:: pywbem.MOFWBEMConnection
   :members:

.. _`MOF compiler exceptions`:

Exceptions
----------

The MOF compiler API may raise the exceptions that can be raised by the
:ref:`WBEM client library API`, and in addition the
:exc:`~pywbem.MOFParseError` exception.

.. autoclass:: pywbem.MOFParseError
   :members:
