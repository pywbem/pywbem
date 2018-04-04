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
**Experimental:** *New in pywbem 0.11 and redesigned in pywbem 0.12 as
experimental.*


.. _`Pywbem logging overview`:

Pywbem logging overview
^^^^^^^^^^^^^^^^^^^^^^^

The pywbem package implements selected logging using the Python
:mod:`py:logging` facility.

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

These pywbem loggers output log records when they are configured and activated.
The pywbem loggers log at the :attr:`py:logging.DEBUG` logging level.

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

* :meth:`~pywbem.WBEMConnection.configure_logger` - Configure the pywbem
  loggers and optionally activate WBEM connections for logging and setting a
  log detail level.

* :func:`configure_loggers_from_string` - Configure the pywbem loggers and
  optionally activate WBEM connections for logging and setting a log detail
  level, from a log configuration string.

  This is most useful in defining the pywbem logging from a command line tool
  such as pywbemcli so the complete logger configuration can be compressed into
  a single command line string.


.. _`Logging configuration examples`:

Logging configuration examples
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Examples for using :meth:`~pywbem.WBEMConnection.configure_logger` for
configuring pywbem loggers and for activating WBEM connections for logging:

* Example: Configure the `'pywbem.api'` logger with detail level `'summary'`
  and output to stderr, and activate all subsequently created WBEM connections
  for logging::

    WBEMConnection.configure_logger('api',
                                    log_dest='stderr',
                                    detail_level='summary',
                                    connection=True)

    # All of the following connections will log:
    conn1 = WBEMConnection(...)
    conn2 = WBEMConnection(...)

* Example: Configure all pywbem loggers with the default detail level (`'all'`)
  and output to a file, and activate a single existing WBEM connection for
  logging::

    conn = WBEMConnection()

    WBEMConnection.configure_logger('all',
                                    log_dest='file', log_filname='xxx.log',
                                    connection=conn)

Examples for configuring the pywbem loggers using Python logging methods,
and using the pywbem logging configuration functions only for setting the
detail level and for activating WBEM connections for logging:

* Example: Configure the Python root logger for logging to a file, configure
  both pywbem loggers for detail level `'all'`, and activate an existing WBEM
  connection for logging::

    import logging

    # This configures the Python root logger
    logging.basicConfig(filename='example.log', level=logging.DEBUG)

    conn = WBEMConnection(...)

    WBEMConnection.configure_logger('all',
                                    detail_level='all',
                                    connection=conn)

  TODO: This configures the pywbem loggers with a null handler and thus
  does not propagate up to the Python root logger. Clarify whether this
  approach actually works.

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

    WBEMConnection.configure_logger('api',
                                    detail_level='summary',
                                    connection=True)

    # All of the following connections will log:
    conn1 = WBEMConnection(...)
    conn2 = WBEMConnection(...)

Examples for using :func:`configure_loggers_from_string` for configuring the
pywbem loggers and for activating WBEM connections for logging:

* Example: Configure the `'pywbem.api'` logger with detail level `'summary'`
  and output to stderr, and activate all subsequently created WBEM connections
  for logging::

    configure_loggers_from_string('api=stderr:summary',
                                  connection=True)

    # All of the following connections will log:
    conn1 = WBEMConnection(...)
    conn2 = WBEMConnection(...)

* Example: Configure both pywbem loggers with the default detail level
  (`'all'`) and output to a file, and activate a single existing WBEM
  connection for logging::

    conn = WBEMConnection()

    configure_loggers_from_string('all=file', log_filname='xxx.log',
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

# NOTE: cannot use from pywbem import WBEMConnection because it is circular
# import.
import pywbem.cim_operations

__all__ = ['configure_loggers_from_string',
           'LOGGER_API_CALLS_NAME', 'LOGGER_HTTP_NAME', 'LOGGER_SIMPLE_NAMES',
           'LOG_DESTINATIONS', 'DEFAULT_LOG_DESTINATION', 'LOG_DETAIL_LEVELS',
           'DEFAULT_LOG_DETAIL_LEVEL']

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
#: * `'stderr'` - Log to the standard error stream of the Python process
#: * `'file'` - Log to a file (requires filename to be specified)
#: * `'none'` - Log to the Python null handler (i.e. suppress logging)
LOG_DESTINATIONS = ['stderr', 'file', 'none']

#: Default log destination if not supplied to the logging configuration
#: functions.
DEFAULT_LOG_DESTINATION = 'none'

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


def configure_loggers_from_string(log_configuration_str, log_filename=None,
                                  connection=None):
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

        If it is a :class:`py:bool`, all subsequently created
        :class:`~pywbem.WBEMConnection` objects will be affected:
        If `True`, future connections will be activated for logging and the
        detail level for each pywbem logger will be set on the connections.

        If it is a :class:`~pywbem.WBEMConnection` object, logging will be
        activated for that WBEM connection only and the specified detail level
        will be set for the affected pywbem loggers on the connection.

        If `None`, no WBEM connection will be activated for logging.

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
        try:
            spec_split = log_spec.split("=", 1)
        except ValueError:
            raise ValueError('Log spec %s invalid. Contains too many '
                             ' components' % log_spec)
        if len(spec_split) == 1:
            simple_log_name = spec_split[0]
            log_values = []
        elif len(spec_split) == 2:
            simple_log_name = spec_split[0]
            log_values = spec_split[1].split(':')
        else:
            raise ValueError("Log component name required in %s" % log_spec)

        # cvt empty strings to None
        if log_values is None:
            log_values = [None, None]
        else:
            # expand to full size if not all values supplied
            while len(log_values) < 2:
                log_values.append(None)

        if simple_log_name not in LOGGER_SIMPLE_NAMES:
            raise ValueError('Log string %s invalid. Log name %s not a valid '
                             'pywbem logger name. Must be one of %s' %
                             (log_configuration_str, simple_log_name,
                              LOGGER_SIMPLE_NAMES))

        detail_level = log_values[1]
        # try to set as integer
        if detail_level:
            try:
                detail_level = int(detail_level)
            except ValueError:
                pass

        pywbem.WBEMConnection.configure_logger(
            simple_log_name,
            log_dest=log_values[0],
            detail_level=detail_level,
            log_filename=log_filename,
            connection=connection)
