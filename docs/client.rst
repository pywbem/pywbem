
.. _`WBEM client library API`:

WBEM client library API
=======================

.. automodule:: pywbem

.. _`WBEM operations`:

WBEM operations
---------------

.. automodule:: pywbem.cim_operations

.. autoclass:: pywbem.WBEMConnection
   :members:
   :special-members: __str__, __repr__

.. # TODO: Requesting all members (by means of :members: without a list
.. # of members) causes the internal methods imethodcall() and methodcall()
.. # also to be generated. However, specifying a list of members in order
.. # to exclude these two methods causes the special members also not to be
.. # shown. It seems the least evil at this point to have both shown,
.. # and to document that the two low-level functions are not part of the
.. # external API.
.. # List of members to specify for :members: (once it works):
.. #         EnumerateInstanceNames, EnumerateInstances, GetInstance,
.. #         ModifyInstance, CreateInstance, DeleteInstance, AssociatorNames,
.. #         Associators, ReferenceNames, References, InvokeMethod,
.. #         ExecQuery, EnumerateClassNames, EnumerateClasses, GetClass,
.. #         ModifyClass, CreateClass, DeleteClass, EnumerateQualifiers,
.. #         GetQualifier, SetQualifier, DeleteQualifier

.. _`CIM objects`:

CIM objects
-----------

.. automodule:: pywbem.cim_obj

CIMInstanceName
^^^^^^^^^^^^^^^

.. autoclass:: pywbem.CIMInstanceName
   :members:
   :special-members: __str__, __repr__

CIMInstance
^^^^^^^^^^^

.. autoclass:: pywbem.CIMInstance
   :members:
   :special-members: __str__, __repr__

CIMClassName
^^^^^^^^^^^^

.. autoclass:: pywbem.CIMClassName
   :members:
   :special-members: __str__, __repr__

CIMClass
^^^^^^^^

.. autoclass:: pywbem.CIMClass
   :members:
   :special-members: __str__, __repr__

CIMProperty
^^^^^^^^^^^

.. autoclass:: pywbem.CIMProperty
   :members:
   :special-members: __str__, __repr__

CIMMethod
^^^^^^^^^

.. autoclass:: pywbem.CIMMethod
   :members:
   :special-members: __str__, __repr__

CIMParameter
^^^^^^^^^^^^

.. autoclass:: pywbem.CIMParameter
   :members:
   :special-members: __str__, __repr__

CIMQualifier
^^^^^^^^^^^^

.. autoclass:: pywbem.CIMQualifier
   :members:
   :special-members: __str__, __repr__

CIMQualifierDeclaration
^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: pywbem.CIMQualifierDeclaration
   :members:
   :special-members: __str__, __repr__

Conversion functions
^^^^^^^^^^^^^^^^^^^^

This section describes conversion functions that may be useful for purposes
such as debugging.

.. autofunction:: pywbem.tocimxml

.. autofunction:: pywbem.tocimxmlstr

.. autofunction:: pywbem.tocimobj

.. _`CIM data types`:

CIM data types
--------------

.. automodule:: pywbem.cim_types

.. autoclass:: pywbem.CIMType
   :members:
   :special-members: __repr__

.. autoclass:: pywbem.CIMDateTime
   :members:
   :special-members: __str__, __repr__

.. autoclass:: pywbem.MinutesFromUTC
   :members:

.. autoclass:: pywbem.CIMInt
   :members:

.. autoclass:: pywbem.Uint8
   :members:

.. autoclass:: pywbem.Sint8
   :members:

.. autoclass:: pywbem.Uint16
   :members:

.. autoclass:: pywbem.Sint16
   :members:

.. autoclass:: pywbem.Uint32
   :members:

.. autoclass:: pywbem.Sint32
   :members:

.. autoclass:: pywbem.Uint64
   :members:

.. autoclass:: pywbem.Sint64
   :members:

.. autoclass:: pywbem.CIMFloat
   :members:

.. autoclass:: pywbem.Real32
   :members:

.. autoclass:: pywbem.Real64
   :members:

.. _`CIM status codes`:

CIM status codes
----------------

.. automodule:: pywbem.cim_constants
   :members:

.. _`Exceptions`:

Exceptions
----------

.. automodule:: pywbem.exceptions

.. autoclass:: pywbem.Error

.. autoclass:: pywbem.ConnectionError

.. autoclass:: pywbem.AuthError

.. autoclass:: pywbem.TimeoutError

.. autoclass:: pywbem.ParseError

.. autoclass:: pywbem.CIMError
   :members:
   :special-members: __str__

