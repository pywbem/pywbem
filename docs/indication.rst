
.. _`WBEM indication listener`:

WBEM indication listener
========================

*New in pywbem 0.9 as experimental and finalized in 0.10.*

The WBEM indication listener API supports creating and managing a thread-based
WBEM listener that waits for indications (i.e. events) emitted by a WBEM
server using the CIM-XML protocol. The API supports registering callback
functions that get called when indications are received by the listener.

See :ref:`WBEM subscription manager` for the API for viewing and managing
subscriptions for indications on a WBEM server.


.. _`WBEMListener`:

WBEMListener
^^^^^^^^^^^^

.. automodule:: pywbem._listener

.. autoclass:: pywbem.WBEMListener
   :members:

   .. rubric:: Methods

   .. autoautosummary:: pywbem.WBEMListener
      :methods:
      :nosignatures:

   .. rubric:: Attributes

   .. autoautosummary:: pywbem.WBEMListener
      :attributes:

   .. rubric:: Details

.. autofunction:: pywbem.callback_interface
