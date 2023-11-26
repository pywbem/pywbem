
.. _`WBEM operations`:

WBEM operations
---------------

.. automodule:: pywbem._cim_operations

..index:: pair: libraries; WBEMConnection library

WBEMConnection
^^^^^^^^^^^^^^

.. # The following directive excludes the operation recorder related internal
.. # attributes and methods from the documentation.

.. autoclass:: pywbem.WBEMConnection
    :members:
    :special-members:
    :exclude-members: __init__,__weakref__,add_operation_recorder,operation_recorder_reset,operation_recorder_stage_pywbem_args,operation_recorder_stage_result,operation_recorders,operation_recorder_enabled
    :autosummary:
    :autosummary-inherited-members:

.. autoclass:: pywbem.IterQueryInstancesReturn
    :members:
    :special-members:
    :exclude-members: __init__,__weakref__
    :autosummary:
    :autosummary-inherited-members:
