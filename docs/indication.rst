
.. _`WBEM indication API`:

WBEM indication API
===================

The WBEM indication API supports subscription for and receiving of CIM
indications.

This chapter has the following sections:

* :ref:`WBEMListener` - The :class:`~pywbem.WBEMListener` class provides a
  thread-based WBEM listener service for receiving indications.

* :ref:`WBEMSubscriptionManager` - The :class:`~pywbem.WBEMSubscriptionManager`
  class provides for managing subscriptions for indications.

.. note::

   At this point, the WBEM indication API is experimental.


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

