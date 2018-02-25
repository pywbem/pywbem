
.. _`WBEM operation recording`:

WBEM operation recording
------------------------

The WBEM client library API provides the possibility to record the WBEM
operations that are executed on a connection.
WBEM Operation recording uses the classes and subclasses defined in
:ref:`WBEM Operation Recorder`.

This is disabled by default and can be enabled by adding recorders to a
WBEMConnection with the method
:meth:`~pywbem.WBEMConnection.add_operation_recorder`.

Typical usage scenarios for various operation recorders are the tracing of WBEM
operations, tracing of interactions with a WBEM server, or the generation of
test cases.

Please note that the method of activating operation recorders changed starting
with pywbem 0.11.0 and the addition of a second recorder.  See
:meth:`~pywbem.WBEMConnection.add_operation_recorder` for more information.

This adds the recorder defined in the method call to a list of active recorders
in WBEMConnection. All active recorders are called for each WBEMConnection
method that sends information to the WBEM server.

A single recorder can be  be disabled with
:meth:`~pywbem.BaseOperationRecorder.disable` method and enabled with
:meth:`~pywbem.BaseOperationRecorder.enable` method.

The logger names for the operations and http loggers must be
defined using  the :class:~pywbem.`PywbemLoggers` class to
define usable loggers because the pywbem loggers include logging attributes in
addition to the standard python logger attributes.  This is done with the
method :meth:`~pywbem.PywbemLoggers.create_logger` which defines one or more
loggers from the input parameters.  There is also a convience method
:meth:`~pywbem.PywbemLoggers.create_loggers` which will define multiple pywbem
logger definitions from a string definition that could be used with command
line tools.

The following example shows defining loggers for both http and operations and
adding activating the LogOperationRecorder in WBEMConnection.

::

    # set the python logger facility to output at the DEBUG level
    logger.setLevel(logging.DEBUG)

    # Define the parameters of the LogOperationRecorder
    # using one of the methods in the PywbemLoggers class
    PywbemLoggers.create_logger('all',
                                log_dest='file',
                                log_detail_level='min'
                                log_filename='test.log')   # define both loggers

    # Create the connection and enable the logger
    conn = WBEMConnection(...)
    conn.add_operation_recorder(LogOperationRecorder())
    # The LogOperationRecorder is now active and writing logs to stderr.

The following example activates and enables both recorders:

::

    # To add both recorders
    logger.setLevel(logging.DEBUG)
    PywbemLoggers.create_logger('log')   # define only the log logger
    conn = WBEMConnection(...)
    log_recorder = LogOperationRecorder()
    conn.add_operation_recorder(log_recorder)
    yamlfp = TestClientRecorder.open_file(self.yamlfile, 'a')
    conn.add_operation_recorder(TestClientRecorder(yamlfp))

    # Both TestClientRecorder and LogOperationRecorder are be
    # active, enabled and recording
    # To change the enabled state of either recorder, use the enabled/disabled
    # methods of the Recorder
    log_recorder.disable()   # disables recording to the log

Activated loggers can be computing-wise expensive so it is best not to activate
either logger unless they are to be used for that specific WBEMConnection.

The :meth:`~pywbemRecorder.BaseOperationRecorder.enable` and
:meth:`~pywbemRecorder.BaseOperationRecorder.disable` methods simply set
flags to bypass creating the final recorder output so activating and disabling
is still more compute-wise expensive than not activating a recorder at all.

The :class:`~pywbem.LogOperationRecorder` is a more complete mechanism than the
:attr:`~pywbem.WBEMConnection.debug` in that it records
information on operations and HTTP interactions with a WBEM server to a
log destination defined through :class:`~pywbem.PywbemLoggers` using the python
logging facility.  This information includes the following:

a. If operations logging is set (the log component == 'ops'):
    1. Records the method input parameters
    2. Records either all or a fixed length of the response values with an
       optional maximum length attribute because this log entry can become
       enormous if it records complete responses.
    3. Records all exceptions

b. If http logging is set (the log component == 'http'):
    1. Records the HTTP attributes and data of the request
    2. Records the HTTP attributes and data of the response with an optional
       max length

d. If the log component = 'all' both operations and http are logged.

In addition to the method and HTTP information, the parameters of each
WBEM connection are also logged including an id so that method logs can be
linked back to the WBEM connection.

The :class:`~pywbem.PywbemLoggers` allows defining loggers to output the logs
to either stderr or a file based on the
:meth:`~pywbem.PywbemLoggers.create_logger`
log_dest parameter.


.. _`WBEM Operation recorder`:

WBEM Operation recorder
^^^^^^^^^^^^^^^^^^^^^^^

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

:class:`~pywbem.LogOperationRecorder`    Generate logs using the python logging
                                         facitlity for
                                         :class:`~pywbem.WBEMConnection`
                                         methods that communicate with a
                                         WBEM server.
======================================== =======================================


.. autoclass:: pywbem.BaseOperationRecorder
   :members:

.. autoclass:: pywbem.OpArgs
   :members:

.. autoclass:: pywbem.OpResult
   :members:

.. autoclass:: pywbem.HttpRequest
   :members:

.. autoclass:: pywbem.HttpResponse
   :members:

.. autoclass:: pywbem.TestClientRecorder
   :members:

.. autoclass:: pywbem.LogOperationRecorder
   :members:
