
.. _`WBEM operation recording`:

WBEM operation recording
------------------------

The WBEM client library API provides the possibility to record the WBEM
operations that are executed on a connection.
WBEM Operation recording uses the classes and subclasses defined in
:ref:`WBEM operation recorders`.

This is disabled by default and can be enabled by adding recorders to a
:class:`~pywbem.WBEMConnection` object with the method
:meth:`~pywbem.WBEMConnection.add_operation_recorder`.

Typical usage scenarios for various operation recorders are the tracing of WBEM
operations, tracing of interactions with a WBEM server, or the generation of
test cases.

Please note that the method of activating operation recorders changed starting
with pywbem 0.11.0 and the addition of a second recorder.  See
:meth:`~pywbem.WBEMConnection.add_operation_recorder` for more information.

This adds the recorder defined in the method call to a list of active recorders
in the :class:`~pywbem.WBEMConnection` object. All active recorders are called
for each WBEM operation on a connection.

A recorder can be  be disabled with
:meth:`~pywbem.BaseOperationRecorder.disable` method and enabled with
:meth:`~pywbem.BaseOperationRecorder.enable` method.

The following example activates the :class:`~pywbem.TestClientRecorder`
recorder for a connection::

    conn = WBEMConnection(...)

    # Add a TestClientRecorder to the connection
    yamlfp = TestClientRecorder.open_file(self.yamlfile, 'a')
    tc_recorder = TestClientRecorder(yamlfp)
    conn.add_operation_recorder(tc_recorder)

    # TestClientRecorder is now active and will record WBEM operations
    # on that connection.
    . . .

    # Disable the TestClientRecorder
    tc_recorder.disable()

Note that the :class:`~pywbem.LogOperationRecorder` is dealt with through
the logging functions described in :ref:`WBEM operation logging`, and should
not be added to a conneciton by pywbem users.

Activated recorders can be computing-wise expensive so it is best not to
activate a recorder unless it is to be used for that specific WBEMConnection.

The :meth:`~pywbem.BaseOperationRecorder.enable` and
:meth:`~pywbem.BaseOperationRecorder.disable` methods simply set
flags to bypass creating the final recorder output so activating and disabling
is still more compute-wise expensive than not activating a recorder at all.


.. _`WBEM operation recorders`:

WBEM operation recorders
^^^^^^^^^^^^^^^^^^^^^^^^

The WBEM client library API includes the abstract base class
:class:`~pywbem.BaseOperationRecorder` from which operation recorders can be
written that perform specific recording tasks.

Users can write their own operation recorder classes based upon the
abstract base class :class:`~pywbem.BaseOperationRecorder`.

The WBEM client library API provides the following operation recorder classes:

======================================== =======================================
Class                                    Purpose
======================================== =======================================
:class:`~pywbem.TestClientRecorder`      Generate test cases for the
                                         `test_client` unit test module.

:class:`~pywbem.LogOperationRecorder`    Generate logs using the Python logging
                                         facility for
                                         :class:`~pywbem.WBEMConnection`
                                         methods that communicate with a
                                         WBEM server.
======================================== =======================================


.. autoclass:: pywbem.BaseOperationRecorder
   :members:

   .. rubric:: Methods

   .. autoautosummary:: pywbem.BaseOperationRecorder
      :methods:
      :nosignatures:

   .. rubric:: Attributes

   .. autoautosummary:: pywbem.BaseOperationRecorder
      :attributes:

   .. rubric:: Details

.. autoclass:: pywbem.OpArgs
   :members:

.. # No autoautosummary on pywbem.OpArgs, because its base class is not documented.

.. autoclass:: pywbem.OpResult
   :members:

.. # No autoautosummary on pywbem.OpResult, because its base class is not documented.

.. autoclass:: pywbem.HttpRequest
   :members:

.. # No autoautosummary on pywbem.HttpRequest, because its base class is not documented.

.. autoclass:: pywbem.HttpResponse
   :members:

.. # No autoautosummary on pywbem.HttpResponse, because its base class is not documented.

.. autoclass:: pywbem.TestClientRecorder
   :members:

   .. rubric:: Methods

   .. autoautosummary:: pywbem.TestClientRecorder
      :methods:
      :nosignatures:

   .. rubric:: Attributes

   .. autoautosummary:: pywbem.TestClientRecorder
      :attributes:

   .. rubric:: Details

.. autoclass:: pywbem.LogOperationRecorder
   :members:

   .. rubric:: Methods

   .. autoautosummary:: pywbem.LogOperationRecorder
      :methods:
      :nosignatures:

   .. rubric:: Attributes

   .. autoautosummary:: pywbem.LogOperationRecorder
      :attributes:

   .. rubric:: Details
