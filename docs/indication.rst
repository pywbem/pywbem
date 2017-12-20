
.. _`WBEM indication API`:

WBEM indication API
===================

*New in pywbem 0.9 as experimental and finalized in 0.10.*

The WBEM indication API supports subscription for and receiving of CIM
indications.

This chapter has the following sections:

* :ref:`WBEMListener` - The :class:`~pywbem.WBEMListener` class provides a
  thread-based WBEM listener service for receiving indications.

* :ref:`WBEMSubscriptionManager` - The :class:`~pywbem.WBEMSubscriptionManager`
  class provides for managing subscriptions for indications.


.. _`WBEMListener`:

WBEMListener
^^^^^^^^^^^^

.. automodule:: pywbem._listener

.. autoclass:: pywbem.WBEMListener
   :members:

.. autofunction:: pywbem.callback_interface


.. _`WBEMSubscriptionManager`:

WBEMSubscriptionManager
^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: pywbem._subscription_manager

.. autoclass:: pywbem.WBEMSubscriptionManager
   :members:

