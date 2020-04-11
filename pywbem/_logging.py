# Copyright 2017 InovaDevelopment Inc. All Rights Reserved.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

# pylint: disable=line-too-long
"""
*New in pywbem 0.11 and redesigned in pywbem 0.12. Finalized in pywbem 0.13.*


.. _`Pywbem logging overview`:

Pywbem logging overview
^^^^^^^^^^^^^^^^^^^^^^^

The pywbem package implements selected logging using the Python
:mod:`py:logging` facility.
This section describes logging for use of the pywbem package as a WBEM client.
Section :ref:`Logging in the listener` describes logging for use of the pywbem
package as a WBEM listener.

Pywbem logging is used to record information passing between the pywbem client
and WBEM servers but not as a general recorder for errors, state, etc. within
pywbem. In effect it is a trace tool. Pywbem errors are generally passed to
the pywbem API user as Python exceptions rather than being recorded in a log
by a pywbem logger.

Pywbem logging uses two Python :class:`~py:logging.Logger` objects which are
termed `pywbem loggers`:

* API logger (Python logger name: `'pywbem.api'`) - Logs API calls and returns,
  for the :class:`~pywbem.WBEMConnection` methods that drive WBEM operations
  (see :ref:`WBEM operations`). This logs the API parameters and results,
  including CIM objects/exceptions. It also logs the creation of
  :class:`~pywbem.WBEMConnection` objects to capture connection information in
  order to determine the connection to which a particular log record belongs.

* HTTP logger (Python logger name: `'pywbem.http'`) - Logs HTTP requests and
  responses between the pywbem client and WBEM server. This logs the HTTP
  request data and response data including HTTP headers and CIM-XML payload.

Pywbem uses the :attr:`py:logging.DEBUG` logging level for both loggers.

Pywbem adds a null handler to the logger named `'pywbem'`, in order to prevent
the "No handlers could be found for logger ..." warning.
This follows best practices recommended in `Configuring logging for a library
<https://docs.python.org/2/howto/logging.html#configuring-logging-for-a-library>`_
and in several articles, for example in `this article
<http://pieces.openpolitics.com/2012/04/python-logging-best-practices/>`_.
Because this warning is no longer issued on Python 3.4 and higher, pywbem
adds a null handler only on Python 2.7.

Because pywbem logs only at the :attr:`py:logging.DEBUG` logging level, these
log events will not be printed by the Python root logger by default, and
therefore it is not necessary that pywbem attaches a null handler to any of its
loggers.

There are two steps to setting up pywbem logging:

* **Configure Python logging parameters**

  Sets the Python logging parameters for a pywbem logger or its parent loggers,
  such as log handler, message format, and logging level.

  This can be done with Python logging functions or with the functions
  described in :ref:`Logging configuration functions`.

* **Activate WBEM connection(s) for logging and set detail level**

  In order to save the cycles for capturing the possibly large amounts of data
  needed for creating the log records, pywbem logging is inactive by default.
  Logging can be activated for an existing WBEM connection, or for all
  subsequently created WBEM connections.

  Because the pywbem loggers can generate large quantities of information, the
  user can control the quantity of information produced by each pywbem logger
  by setting a detail level for each logger when activating a WBEM connection
  for logging.

  Activation and setting detail levels are pywbem features so it requires using
  the functions described in :ref:`Logging configuration functions`.


.. _`Logging configuration functions`:

Logging configuration functions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The pywbem loggers may be configured and/or WBEM connections may be activated
for logging through the following pywbem functions.

These functions are the only mechanism for setting the detail level of a pywbem
logger and for activating WBEM connection(s) for logging.

* :func:`configure_logger` - Configure the pywbem loggers and optionally
  activate WBEM connections for logging and setting a log detail level.

* :func:`configure_loggers_from_string` - Configure the pywbem loggers and
  optionally activate WBEM connections for logging and setting a log detail
  level, from a log configuration string.

  This is most useful in defining the pywbem logging from a command line tool
  such as pywbemcli so the complete logger configuration can be compressed into
  a single command line string.


.. _`Logging configuration examples`:

Logging configuration examples
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Examples for using :func:`configure_logger` for configuring pywbem loggers and
for activating WBEM connections for logging:

* Example: Configure the `'pywbem.api'` logger with detail level `'summary'`
  and output to stderr, and activate all subsequently created WBEM connections
  for logging::

    configure_logger('api', log_dest='stderr', detail_level='summary',
                     connection=True)

    # All of the following connections will log to stderr with summary output:
    conn1 = WBEMConnection(...)
    conn2 = WBEMConnection(...)

* Example: Configure all pywbem loggers with the default detail level (`'all'`)
  and output to a file, and activate a single existing WBEM connection for
  logging::

    conn = WBEMConnection(...)

    configure_logger('all', log_dest='file', log_filname='my_logfile.log',
                     connection=conn)

Examples for configuring the pywbem loggers using Python logging methods,
and using the pywbem logging configuration functions only for setting the
detail level and for activating WBEM connections for logging:

* Example: Configure the pywbem parent logger (named `'pywbem'`) for logging to
  a rotating file, configure both pywbem loggers for detail level `'summary'`,
  and activate all subsequent WBEM connections for logging::

    import logging
    from logging.handlers import RotatingFileHandler

    logger = logging.getLogger('pywbem')
    handler = RotatingFileHandler("my_log.log", maxBytes=2000, backupCount=10)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # configure without setting log_dest
    configure_logger('api', detail_level='summary', connection=True)

    # All of the following connections will log using the rotating file handler:
    conn1 = WBEMConnection(...)
    conn2 = WBEMConnection(...)

Examples for using :func:`configure_loggers_from_string` for configuring the
pywbem loggers and for activating WBEM connections for logging:

* Example: Configure the `'pywbem.api'` logger with detail level `'summary'`,
  output to stderr, and activate all subsequently created WBEM connections
  for logging::

    configure_loggers_from_string('api=stderr:summary', connection=True)

    # All of the following connections will log:
    conn1 = WBEMConnection(...)
    conn2 = WBEMConnection(...)

* Example: Configure both pywbem loggers with the default detail level
  (`'all'`) and output to the file 'my_log.log', and activate a single existing
  WBEM connection object (conn) for logging::

    conn = WBEMConnection(...)

    configure_loggers_from_string('all=file', log_filname='my_log.log',
                                  connection=conn)


.. _`Log records`:

Log records
^^^^^^^^^^^

The following is an example of log output with detail level `'summary'`, where
`'1-32073'` is the connection identifier::

    2018-03-17 11:39:09,877-pywbem.api.1-32073-Connection:1-32073 WBEMConnection(url='http://localhost', creds=None, default_namespace='root/cimv2')
    2018-03-17 11:41:13,176-pywbem.api.1-32073-Request:1-32073 EnumerateClasses(ClassName=None, DeepInheritance=None, IncludeClassOrigin=None, IncludeQualifiers=None, LocalOnly=None, namespace=None)
    2018-03-17 11:41:13,635-pywbem.api.1-32073-Return:1-32073 EnumerateClasses(list of CIMClass; count=103)

The keywords in each log record (`'Connection'`, `'Request'`, `'Return'` or
`'Exception'`) identify whether the log record is connection data,
API/HTTP request data, API/HTTP response data, or API exception data.

The loggers that actually create the log records are children of the configured
pywbem loggers and are unique for each :class:`~pywbem.WBEMConnection` object.
Their logger names are created from the configured logger names by appending
the connection identifier (:attr:`~pywbem.WBEMConnection.conn_id`).
Thus the names of the loggers that actually create the log records are of the
form: `'pywbem.<api/http>.<conn_id>'`.


.. _`Logging related constants and functions`:

Logging related constants and functions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Note: Due to limitations of the documentation tooling, the following constants
and functions are shown in the ``pywbem._logging`` namespace. However, they
should be accessed via the ``pywbem`` namespace.
"""  # noqa: E501
# pylint: enable=line-too-long

from ._utils import _format

__all__ = ['configure_logger', 'configure_loggers_from_string',
           'LOGGER_API_CALLS_NAME', 'LOGGER_HTTP_NAME', 'LOGGER_SIMPLE_NAMES',
           'LOG_DESTINATIONS', 'DEFAULT_LOG_DESTINATION', 'LOG_DETAIL_LEVELS',
           'DEFAULT_LOG_DETAIL_LEVEL']

_CONN = None

#: Name of the pywbem API logger, which logs user-issued calls to and returns
#: from :class:`~pywbem.WBEMConnection` methods that drive WBEM operations.
LOGGER_API_CALLS_NAME = 'pywbem.api'

#: Name of the pywbem HTTP logger, which logs HTTP requests and responses
#: between the pywbem client and WBEM servers.
LOGGER_HTTP_NAME = 'pywbem.http'

#: List of the simple pywbem logger names that the logging configuration
#: functions (see :ref:`Logging configuration functions`) recognize, as
#: follows:
#:
#: * `'api'` - Pywbem API logger (Python logger name: `'pywbem.api'`)
#: * `'http'` - Pywbem HTTP logger (Python logger name: `'pywbem.http'`)
#: * `'all'` - All pywbem loggers
LOGGER_SIMPLE_NAMES = ['api', 'http', 'all']

#: List of log destinations that the logging configuration functions
#: recognize, as follows:
#:
#: * `'file'` - Log to a file (requires filename to be specified). The file
#:   logger appends to the logger file defined by filename.
#: * `'stderr'` - Log to the standard error stream of the Python process
LOG_DESTINATIONS = ['file', 'stderr']

#: Default log destination if not supplied to the logging configuration
#: functions.
DEFAULT_LOG_DESTINATION = 'file'

#: Default path name of the log file to be used when logging to a file.
DEFAULT_LOG_FILENAME = 'pywbem.log'

#: List of the log detail levels that the logging configuration functions
#: recognize, as follows:
#:
#: * `'all'` - All of the data available is output. Generally this is
#:   the ``repr()`` output of the objects in the requests and responses.
#:
#: * `'paths'` - For the API logger, for operations that return CIM classes
#:   or CIM instances, only their path component is output as a WBEM URI
#:   string. Otherwise, all of the data available is output.
#:
#: * `'summary'` - Only summary information is output. For the API logger this
#:   is primarily the count and type of objects returned. For the HTTP logger
#:   the HTTP header information is output.
LOG_DETAIL_LEVELS = ['all', 'paths', 'summary']

#: Default log detail level if not supplied to the logging configuration
#: functions.
DEFAULT_LOG_DETAIL_LEVEL = 'all'


def configure_logger(simple_name, log_dest=None,
                     detail_level=DEFAULT_LOG_DETAIL_LEVEL,
                     log_filename=DEFAULT_LOG_FILENAME,
                     connection=None, propagate=False):
    # pylint: disable=line-too-long
    """
    Configure the pywbem loggers and optionally activate WBEM connections
    for logging and setting a log detail level.

    Parameters:

      simple_name (:term:`string`):
        Simple name (ex. `'api'`) of the single pywbem logger this method
        should affect, or `'all'` to affect all pywbem loggers.

        Must be one of the strings in
        :data:`~pywbem._logging.LOGGER_SIMPLE_NAMES`.

      log_dest (:term:`string`):
        Log destination for the affected pywbem loggers, controlling the
        configuration of its Python logging parameters (log handler,
        message format, and log level).

        If it is a :term:`string`, it must be one of the strings in
        :data:`~pywbem._logging.LOG_DESTINATIONS` and the Python logging
        parameters of the loggers will be configured accordingly for their
        log handler, message format, and with a logging level of
        :attr:`py:logging.DEBUG`.

        If `None`, the Python logging parameters of the loggers will not be
        changed.

      detail_level (:term:`string` or :class:`int` or `None`):
        Detail level for the data in each log record that is generated by
        the affected pywbem loggers.

        If it is a :term:`string`, it must be one of the strings in
        :data:`~pywbem._logging.LOG_DETAIL_LEVELS` and the loggers will
        be configured for the corresponding detail level.

        If it is an :class:`int`, it defines the maximum size of the log
        records created and the loggers will be configured to output all
        available information up to that size.

        If `None`, the detail level configuration will not be changed.

      log_filename (:term:`string`):
        Path name of the log file (required if the log destination is
        `'file'`; otherwise ignored).

      connection (:class:`~pywbem.WBEMConnection` or :class:`py:bool` or `None`):
        WBEM connection(s) that should be affected for activation and for
        setting the detail level.

        If it is a :class:`py:bool`, the information for activating logging
        and for the detail level of the affected loggers will be stored for
        use by subsequently created :class:`~pywbem.WBEMConnection` objects.
        A value of `True` will store the information to activate the
        connections for logging, and will add the detail level for the
        logger(s).
        A value of `False` will reset the stored information for future
        connections to be deactivated with no detail levels specified.

        If it is a :class:`~pywbem.WBEMConnection` object, logging will be
        activated for that WBEM connection only and the specified detail
        level will be set for the affected pywbem loggers on the
        connection.

        If `None`, no WBEM connection will be activated for logging.

      propagate (:class:`py:bool`): Flag controlling whether the
        affected pywbem logger should propagate log events to its
        parent loggers.

    Raises:

      ValueError: Invalid input parameters (loggers remain unchanged).
    """  # noqa: E501
    # pylint: enable=line-too-long

    global _CONN  # pylint: disable=global-statement
    if _CONN is None:
        # pylint: disable=import-outside-toplevel
        from . import WBEMConnection
        _CONN = WBEMConnection

    _CONN._configure_logger(  # pylint: disable=protected-access
        simple_name,
        log_dest=log_dest,
        detail_level=detail_level,
        log_filename=log_filename,
        connection=connection,
        propagate=propagate)


def configure_loggers_from_string(log_configuration_str,
                                  log_filename=DEFAULT_LOG_FILENAME,
                                  connection=None, propagate=False):
    # pylint: disable=line-too-long
    """
    Configure the pywbem loggers and optionally activate WBEM connections for
    logging and setting a log detail level, from a log configuration string.

    This is most useful in defining the loggers from a command line tool such
    as pywbemcli so the complete logger configuration can be compressed into a
    single command line string.

    Parameters:

      log_configuration_str (:term:`string`): The log configuration string, in
        the following format::

            log_specs := log_spec [ ',' log_spec ]
            log_spec := logger_simple_name [ '=' [ log_dest ] [ ":" [ detail_level ]]]]

        where:

        * ``logger_simple_name``: Simple logger name. Must be one of the
          strings in the :data:`~pywbem._logging.LOGGER_SIMPLE_NAMES` list.
        * ``log_dest``: Log destination. Must be one of the strings in the
          :data:`~pywbem._logging.LOG_DESTINATIONS` list. Default is
          :data:`~pywbem._logging.DEFAULT_LOG_DESTINATION`.
        * ``detail_level``: Log detail level. Must be one of the strings in the
          :data:`~pywbem._logging.LOG_DETAIL_LEVELS` list. Default is
          :data:`~pywbem._logging.DEFAULT_LOG_DETAIL_LEVEL`.

      log_filename (:term:`string`):
        Path name of the log file (required if any log destination is
        `'file'`; otherwise ignored).

      connection (:class:`~pywbem.WBEMConnection` or :class:`py:bool` or `None`):
        WBEM connection(s) that should be affected for activation and for
        setting the detail level.

        If it is a :class:`py:bool`, the information for activating logging
        and for the detail level of the affected loggers will be stored for
        use by subsequently created :class:`~pywbem.WBEMConnection` objects.
        A value of `True` will store the information to activate the
        connections for logging, and will add the detail level for the
        logger(s).
        A value of `False` will reset the stored information for future
        connections to be deactivated with no detail levels specified.

        If it is a :class:`~pywbem.WBEMConnection` object, logging will be
        activated for that WBEM connection only and the specified detail level
        will be set for the affected pywbem loggers on the connection.

        If `None`, no WBEM connection will be activated for logging.

      propagate (:class:`py:bool`): Flag controlling whether the
        affected pywbem logger should propagate log events to its
        parent loggers.

    Raises:

      ValueError: Invalid input parameters (loggers remain unchanged).

    Examples for `log_configuration_str`::

        'api=stderr:summary'    # Set 'pywbem.api' logger to stderr output with
                                # summary detail level.

        'http=file'             # Set 'pywbem.http' logger to file output with
                                # default detail level.

        'api=stderr:summary'    # Set 'pywbem.api' logger to file output with
                                # summary output level.

        'all=file:1000'         # Set both pywbem loggers to file output with
                                # a maximum of 1000 characters per log record.

        'api=stderr,http=file'  # Set 'pywbem.api' logger to stderr output and
                                # 'pywbem.http' logger to file output, both
                                # with default detail level.
    """  # noqa: E501
    # pylint: enable=line-too-long

    log_specs = log_configuration_str.split(',')
    for log_spec in log_specs:
        spec_split = log_spec.strip('=').split("=")
        simple_name = spec_split[0]
        if not simple_name:
            raise ValueError(
                _format("Simple logger name missing in log spec: {0}",
                        log_spec))
        if len(spec_split) == 1:
            log_dest = DEFAULT_LOG_DESTINATION
            detail_level = DEFAULT_LOG_DETAIL_LEVEL
        elif len(spec_split) == 2:
            val_split = spec_split[1].strip(':').split(':')
            log_dest = val_split[0] or None
            if len(val_split) == 1:
                detail_level = DEFAULT_LOG_DETAIL_LEVEL
            elif len(val_split) == 2:
                detail_level = val_split[1] or None
            else:  # len(val_split) > 2
                raise ValueError(
                    _format("Too many components separated by : in log spec: "
                            "{0}", log_spec))
        else:  # len(spec_split) > 2:
            raise ValueError(
                _format("Too many components separated by = in log spec: "
                        "{0}", log_spec))

        # Convert to integer, if possible
        if detail_level:
            try:
                detail_level = int(detail_level)
            except ValueError:
                pass

        configure_logger(
            simple_name,
            log_dest=log_dest,
            detail_level=detail_level,
            log_filename=log_filename,
            connection=connection,
            propagate=propagate)
