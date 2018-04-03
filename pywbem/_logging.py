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
**Experimental:** *New in pywbem 0.1.1 and redesigned in pywbem 0.12 as*
                  *experimental.*

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

Pywbem logging defines two Python :class:`~py:logging.Logger` objects
(named loggers):

* ``pywbem.api`` - Logs user-issued calls to :class:`~pywbem.WBEMConnection`
  methods that drive WBEM operations (see :ref:`WBEM operations`) and their
  responses before they are passed back to the user. This logs the parameters
  of each request and the results including CIM objects/exceptions in each
  method response. It also logs the creation of the
  :class:`~pywbem.WBEMConnection` object to capture connection information.

* ``pywbem.http`` - Logs HTTP requests and responses between the pywbem client
  and WBEM server. This logs the http request data and response data including
  http headers and XML payload.

The above loggers output log records when they are configured and
activated. The pywbem loggers log at the DEBUG log level.

There are three components to configuration of the pywbem loggers:

* **Configure Python logger names** - Sets the Python logger parameters
  (logging handlers, message formats, etc.). Either Python logging
  methods or methods defined in :ref:`Logging configuration methods` may be
  used to configure the loggers. By default, the two pywbem loggers have null
  handlers (see logging.NullHandler) configured so that logging is not
  propagated up the Python logger hierarchy

* **Set the log record detail level for pywbem loggers(Optional)** - Because
  pywbem loggerss can generate large quantities of information, they allow
  the user to control the quantity of information in each log record (i.e. all
  data, summary information, or data to a maximum log length).  This is a pywbem
  feature so it can only be configured using the pywbem methods defined in
  :ref:`Logging configuration methods`.

* **Activate the pywbem loggers** - A pywbem logger is activated to
  actually output log records when any of the WBEMConnection methods that
  communicate with a WBEM server are executed for that WBEMConnection object.
  Activation is controlled by a parameter of the methods defined in
  :ref:`Logging configuration methods`.

.. _`Logging configuration methods`:

Logging configuration methods
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The pywbem loggers may be configured through the following pywbem methods. These
methods must be used to set the log detail_level and activate the loggers.

  * :meth:`~pywbem.WBEMConnection.configure_logger` - Configures and
    optionally activates one or both loggers. If the logger name is 'all'
    it acts on both loggers.

  * :func:`configure_loggers_from_string` - Allows configuring and
    activating the pywbem loggers from a single formatted string that defines
    logger names, log destination, and detail level. This is most
    useful in defining the loggers from a command line tool such as pywbemcli
    so the complete logger configuration can be compressed into a single
    command line string.

.. _`Logging configuration examples`:

Logging configuration examples
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Configure and activate loggers with
:meth:`~pywbem.WBEMConnection.configure_logger`.

* Configure the "pywbem.api" logger for summary information output to a file
  and activate that logger for all subsequently created
  :class:`~pywbem.WBEMConnection` objects::

    WBEMConnection.configure_logger('api', dest='stderr',
                                    detail_level='summary',
                                    connection=True)
    conn = WBEMConnection()  # logs WBEMConnection api calls and responses

* Configure and activate a single :class:`~pywbem.WBEMConnection` object logger
  for output of summary information for both "pywbem.api" and "pywbem.http"::

    conn = WBEMConnection()
    WBEMConnection.configure_logger('all', dest='file', log_filname='xxx.log',
                                        connection=conn)

Configure pywbem logging using Python logging methods.

* Configure a single pywbem connection with standard Python logger methods by
  defining the root logger with basicConfig::

    # Set basic logging configuration (i.e root level logger)
    import logging
    logging.basicConfig(filename='example.log',level=logging.DEBUG)
    conn = WBEMConnection(...)

    # Define the detail_level and WBEMConnection object to activate.
    WBEMConnection.configure_logger('all', detail_level='all', connection=conn)


* Configure the `pywbem` logger with a RotatingFileHandler for all
  subsequent WBEMConnections using Python methods to configure the logger.
  This defines the configuration for both `pywbem.api` and `pywbem.http`
  loggers::

    from logging.handlers import RotatingFileHandler
    # define logger handler for `pywbem`, parent for pywbem.http and pywbem.api
    logger = logging.getLogger('pywbem')
    handler = logging.handlers.RotatingFileHandler("my_log.log", maxBytes=2000,
                                                   backupCount=10)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # configure detail_level and connection so all WBEMConnection objects
    # are activated.
    WBEMConnection.configure_logger('api', detail_level='summary',
                                    connection=True)

    # All of the following connections do api call and response logging with
    # summary information.
    conn1 = WBEMConnection.WBEMConnection(...)
    conn2 = WBEMConnection.WBEMConnection(...)

Configure and activate loggers using :func:`configure_loggers_from_string`.

* Log everything to stderr and output all of the information using the
  pywbem method that configures the loggers from a string::

    configure_loggers_from_string('all=stderr:summary', connection=True)
    conn = WBEMConnection()

* Log api calls and responses summary information to stderr::

    configure_loggers_from_string('api=stderr:summary,http=summary',
                               connection=True)
    conn = WBEMConnection(...)

The keywords in the log record: ()'Connection', 'Request', 'Return' or
'Exception') identify whether the log record is connection data,
api/http request data, api/http response data, or an api exception data.

The logger names that create log entries are uniquely identified by appending
(:attr:`~pywbem.WBEMConnection.conn_id`)  to the configured logger names so that
different logger names exist for each :class:~pywbem.WBEMConnection object.
Thus the logger record names are of the form `pywbem.<api/http>.conn_id`.

The following is an example of log output configuration with detail_level =
'summary' where `1-32073` is the connection identifier.

    2018-03-17 11:39:09,877-pywbem.api.1-32073-Connection:1-32073 WBEMConnection(url='http://localhost', creds=None, default_namespace='root/cimv2')
    2018-03-17 11:41:13,176-pywbem.api.1-32073-Request:1-32073 EnumerateClasses(ClassName=None, DeepInheritance=None, IncludeClassOrigin=None, IncludeQualifiers=None, LocalOnly=None, namespace=None)
    2018-03-17 11:41:13,635-pywbem.api.1-32073-Return:1-32073 EnumerateClasses(list of CIMClass; count=103)

"""   # noqa: E501
# pylint: enable=line-too-long

# NOTE: cannot use from pywbem import WBEMConnection because it is circular
# import.
import pywbem.cim_operations

__all__ = ['configure_loggers_from_string',
           'LOGGER_API_CALLS_NAME', 'LOGGER_HTTP_NAME', 'LOGGER_SIMPLE_NAMES',
           'LOG_DESTINATIONS', 'DEFAULT_LOG_DETAIL_LEVEL',
           'DEFAULT_LOG_DESTINATION', 'LOG_DETAIL_LEVELS']

#: Name of logger for logging user-issued calls to
#: :class:`~pywbem.WBEMConnection` methods that drive WBEM operations.
LOGGER_API_CALLS_NAME = 'pywbem.api'

#: Name of logger for HTTP requests and responses between the pywbem client and
#: WBEM servers.
LOGGER_HTTP_NAME = 'pywbem.http'

#: List of the logger names that the logging configuration helper functions
#: recognize. This allows setting up loggers individually or all to the
#: same destination.
LOGGER_SIMPLE_NAMES = ['api', 'http', 'all']

#: List of log destinations that the logging configuration helper functions
#: recognize.
LOG_DESTINATIONS = ['file', 'stderr', 'none']

#: List of the log detail strings that the logging configuration helper
#: functions recognizes when formatting log records.
#:
#:  * `all` - All of the data available is output. Generally this is
#:    the repr of the objects in the request or response
#:
#:  * `summary` - Only summary information is output. For api responses this
#:    is primarily the count and type of objects returned. For http logs
#:    the HTTP header information is output.
#:
#:  * `paths` - For api responses that include CIMInstanceName or CIMClassName
#:    objects(paths components in the objects) only the string representation
#:    of the path components is output.  Otherwise the complete object
#:    representations are logged.
LOG_DETAIL_LEVELS = ['all', 'paths', 'summary']

#: Default log detail level string if none is supplied with a call to the
#: :class:`pywbem._logging.PywbemLoggers` methods that configure pywbem named
#: loggers
DEFAULT_LOG_DETAIL_LEVEL = 'all'

#: Default log destination if none is defined when named loggers are
#: configured. 'none' means that there is no logging.
DEFAULT_LOG_DESTINATION = 'none'


def configure_loggers_from_string(log_configuration_str, log_filename=None,
                                  connection=None):
    # pylint: disable=line-too-long
    """
    Configure the pywbem loggers from a log configuration string, and
    optionally activate the loggers. This allows defining the complete pywbem
    logger configuration from a single string.

    Parameters:

      log_configuration_str (:term:`string`): Specifies the logger configuration
        with the following formats::

            log_specs := log_spec [, log_spec ]
            log_spec := log_name ['=' [ dest ][":"[ detail_level ]]]]
            where:
                log_name: Simplified name for the logger. Must be one of strings in the :data:`~pywbem._logging.LOG_SIMPLE_NAMES` list.
                dest: Must be one of strings in the :data:`~pywbem._logging.LOG_DESTINATIONS` list.
                detail_level: Must be one of strings in the :data:`~pywbem._logging.LOG_DETAIL_LEVELS` list.

      log_filename (:term:`string`)
        String that defines the filename for output of logs
        if the dest type is `file`. If dest type is not `file` this parameter
        is ignored.

    Raises:

      ValueError: Generated if the syntax of the input string is invalid.

    Examples::

        api=stderr:summary    # set  "pywbem.api" logger for summary display to
                              # stderr with summary level output

        http=file             # set "pywbem.http" logger to output to file
                              # with default detail_level.

        api=stderr:summary    # set  "pywbem.api" logger to output to file
                              # with summary output level.

        all=file:1000         # Set both loggers to output to a file with
                              # maximum of 1000 characters per log record

        api=stderr,http=file  # log "pywbem.api" logger to output  to stderr
                              # and "pywbem.http" to output a file
    """  # noqa: E501

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
