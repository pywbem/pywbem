
.. _`Conversion functions`:

Conversion functions
--------------------

This section describes conversion functions related to :ref:`CIM objects` and
:ref:`CIM data types`:

==============================  ===============================================
Function                        Purpose
==============================  ===============================================
:func:`~pywbem.tocimxml`        Return the CIM-XML representation of a CIM
                                object or CIM data typed value as an
                                :term:`Element` object.
:func:`~pywbem.tocimxmlstr`     Return the CIM-XML representation of a CIM
                                object or CIM data typed value as a
                                :term:`unicode string`.
:func:`~pywbem.tocimobj`        Return a CIM data typed value from a Python
                                value. **Deprecated:** Use
                                :func:`~pywbem.cimvalue` instead.
:func:`~pywbem.cimvalue`        Return a CIM data typed value from a Python
                                value.
:func:`~pywbem.cimtype`         Return the CIM data type name of a CIM data
                                typed value.
:func:`~pywbem.type_from_name`  Return the Python type object for a CIM data
                                type name.
==============================  ===============================================

.. autofunction:: pywbem.tocimxml

.. autofunction:: pywbem.tocimxmlstr

.. autofunction:: pywbem.tocimobj

.. autofunction:: pywbem.cimvalue

.. autofunction:: pywbem.cimtype

.. autofunction:: pywbem.type_from_name
