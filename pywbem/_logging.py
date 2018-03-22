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
**Experimental:** *New in pywbem 0.11 as experimental.*

The pywbem package implements selected logging based on the Python
:mod:`py:logging` facility.

Pywbem logging is used to record information passing between the pywbem client
and WBEM servers but not as a general recorder for errors, state, etc. within
pywbem. In effect it is a trace tool. Pywbem errors are generally passed to
the pywbem API user as Python exceptions rather than being recorded in a log
by a pywbem logger.

Pywbem logging defines two :class:`~py:logging.Logger` objects
(named loggers):

* ``pywbem.api`` - logs user-issued calls to :class:`~pywbem.WBEMConnection`
  methods that drive WBEM operations (see :ref:`WBEM operations`) and the
  responses before they are passed back to the user. Log entries are defined at
  DEBUG log level. This logs the parameters of each request and the results
  including CIMObjects/exceptions in each method repoonse.

* ``pywbem.http`` - logs HTTP requests and responses between the pywbem client
  and WBEM server. This logs the http request data and response data including
  http headers and XML payload.

The above logger names create log entries when  is configured, logging is at
the DEBUG log level and logging is activated for one or more WBEMConnections.

There are three parts to configuration of the pywbem loggers:

* **Configure the loggers** - This sets the Python logging parameters that
  control the logger and its output (handler, etc.) and may be
  done by either Python logging methods or methods within
  :class:`~pywbem.WBEMConnection`.

* **Set the `detail_level` for pywbem logging** - Because pywbem logs can
  generate large quantities of information, pywbem allows the user to control
  the quantity of information in each log.  This is a pywbem feature so it
  can only be configured by the pywbem :class:`~pywbem.WBEMConnection`
  methods and :func:define_loggers_from_string` that configure pywbem loggers.
  The detail levels options are defined in :data:`LOG_DETAIL_LEVELS`

* **Activate the pywbem loggers** - A pywbem logger is activated when it is
  connected to one or more WBEMConnections so that log records will be generated
  when any of the WBEMConnection methods that communicates with a WBEM server
  is executed for that WBEMConnection. Pywbem separates the configuration
  of the loggers from activation to allow logger configuration by either pywbem
  methods or standard Python logging methods. Activation is controlled by
  the `connection` parameter of :meth:`~pywbem.WBEMConnection.configure_logger`
  or :func:`define_loggers_from_string`.

These loggers are only active for a :class:`~pywbem.WBEMConnection` object when:

* A logger in the Python logger name hiearchy higher than or equal to the
  pywbem loggers (ex `pywbem` or root) is defined before the the logger is
  attached to :class:`~pywbem.WBEMConnection` object with one of the
  :class:`~pywbem.WBEMConnection` methods.
  Configuring the loggers through standard Python logger handler methods
  does not activate these loggers since the logger is not linked to a
  :class:`~pywbem.WBEMConnection` object.

* The logger is activated by linking it to a :class:`~pywbem.WBEMConnection`
  object using the `connection` parameter of the configure... method.

* The pywbem loggers may be configured through any of the following
  pywbem methods. These methods configure and optionally activate each of the
  loggers:

  * :meth:`~pywbem.WBEMConnection.configure_logger` which configures and
    optionally activates one or more of the loggers that log user-issued calls
    to :class:~pywbem.WBEMConnection methods that drive WBEM operations and
    pywbem http requests and responses.

  * :func:`define_loggers_from_string` which allows configuring and activating
    the pywbem loggers from a single formatted string. This is most useful
    in defining the loggers from a command line tool such as pywbemcli. Thus,
    for example, the following string could be used to configure and activate
    both loggers::

        api=file:summary,http=stderr:all

The following examples define several different logger configuration options:

Configure a single pywbem connection with standard Python logger methods by
defining the root logger with basicConfig::

    # Set basic logging configuration (i.e root level logger)
    import logging
    logging.basicConfig(filename='example.log',level=logging.DEBUG)
    conn = WBEMConnection(...)

    # Define the detail_level and WBEMConnection object ot activate.
    WBEMConnection.configure_all_loggers(detail_level='all', connection=conn)

Set up configuration to enable the api logger for all subsequent WBEMConnections
using Python methods to configure the loggers so all `pywbem` loggers are
configured::

    # Define logger for pywbem
    logger = logging.getLogger('pywbem')
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # configure detail_level and set connection so all WBEMConnection objects
    # are activated.
    WBEMConnection.configure_api_logger(detail_level='summary', connection=True)

    # All of the following connections do api call and response logging with
    # summary information.
    WBEMConnection.WBEMConnection(...)
    WBEMConnection.WBEMConnection(...)


Configure the api logger for summary information output using only pywbem
methods to configure the logger::

    WBEMConnection.configure_api_logger(dest='stderr',
                                        detail_level='summary',
                                        connection=True)

    conn = WBEMConnection()

Configure just a single WBEMConnection for output of summary information::

    conn = WBEMConnection()
    WBEMConnection.configure_api_logger(dest='file', log_filname='xxx.log',
                                        connection=conn)

Log everything to stderr and output all of the information using the
pywbem method that configures the loggers from a string::

    define_loggers_from_string('all=stderr':summary', connection=True)
    conn = WBEMConnection()

or::

    define_loggers_from_string('api=stderr':summary,http=summary',
                               connection=True)
    conn = WBEMConnection()

Log only http requests and responses including all infomration in the
requests and responses to a file::

    define_logger('http', 'file', log_filename='mylog.log')
    conn = WBEMConnection(..., enable_log='all')

The logger names themselves are uniquely identified with an id string for
each WBEMconnection (:attr:`~pywbem.WBEMConnection.conn_id`). For example, the
log records may look like the following for log configuration with
detail_level = 'summary'::

    2018-03-17 11:39:09,877-pywbem.api.1-32073-Connection:1-32073 WBEMConnection(url='http://localhost', creds=None, default_namespace='root/cimv2')
    2018-03-17 11:41:13,176-pywbem.api.1-32073-Request:1-32073 EnumerateClasses(ClassName=None, DeepInheritance=None, IncludeClassOrigin=None, IncludeQualifiers=None, LocalOnly=None, namespace=None)
    2018-03-17 11:41:13,635-pywbem.api.1-32073-Return:1-32073 EnumerateClasses(list of CIMClass; count=103)

"""   # noqa: E501
# pylint: enable=line-too-long

import logging

# NOTE: cannot use from pywbem import WBEMConnection because it is circular
# import.
import pywbem

__all__ = ['define_loggers_from_string',
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
#:
#:  * :class:`py:int` - All of the available data is formatted up to the size
#:    defined. by the integer value for each log record.  This option applies
#:    to all of the logs generated.
LOG_DETAIL_LEVELS = ['all', 'paths', 'summary']

#: Default log detail level string if none is supplied with a call to the
#: :class:`pywbem._logging.PywbemLoggers` methods that configure pywbem named
#: loggers
DEFAULT_LOG_DETAIL_LEVEL = 'all'

#: Default log destination if none is defined when named loggers are
#: configured. 'none' means that there is no logging.
DEFAULT_LOG_DESTINATION = 'none'


def define_loggers_from_string(log_config_str, log_filename=None,
                               connection=None):
    # pylint: disable=line-too-long
    """
    Configure the pywbem loggers defined by the input string in the syntax
    documented with the `log_config_str`. This configures the defined logger
    name with the destination and detail_level parameters defined by the dest
    and detail level components of the string.

    Parameters:

      log_config_str (:term:`string`): Specifies the logger definitions
        with the following formats::

            log_specs := log_spec [, log_spec ]
            log_spec := log_name ['=' [ dest ][":"[ detail_level ]]]]
            where:
                log_name: Must be one of strings in the :data:`~pywbem._logging.LOG_SIMPLE_NAMES` list.
                dest: Must be one of strings in the :data:`~pywbem._logging.LOG_DESTINATIONS` list.
                detail_level: Must be one of strings in the :data:`~pywbem._logging.LOG_DETAIL_LEVELS` list.

      log_filename (:term:`string`)
        Optional string that defines the filename for output of logs
        if the dest type is `file`

    Raises:

      ValueError: Generated if the syntax of the input string is invalid
        or any of the components is not one of allowed strings.

    Examples::

        api=stderr:summary    # set cim operations logger for summary display

        http=file             # set http logger to send to file

        all=file:1000         # Set all loggers to output to a file with
                              # maximum of 1000 characters per log record

        api=stderr,http=file  # log api calls to stderr and http requests and
                              # responses to a file
    """  # noqa: E501

    log_specs = log_config_str.split(',')
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
                             (log_config_str, simple_log_name,
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
            detail_level=log_values[1],
            log_filename=log_filename,
            connection=connection)


def get_logger(logger_name):
    """
    **Experimental:** *New in pywbem 0.11 as experimental.*

    Return a :class:`~py:logging.Logger` object with the specified name.

    A :class:`~py:logging.NullHandler` handler is added to the logger if it
    does not have any handlers yet and if it is not the Python root logger.
    This prevents the propagation of log requests up the Python logger
    hierarchy, and therefore causes this package to be silent by default.

    This prevents the propagation of log requests up the Python logger
    hierarchy, and therefore causes this package to be silent by default.

    Parameters

      logger_name (:term:`string`):
        Name of the logger which must be one of the named defined in
        pywbem for loggers used by pywbem.  These names are structured
        as prefix . <log_name>

    Returns:

      :class:`~py:logging.Logger`: Logger defined by logger name.

    Raises:

      ValueError: The name is not one of the valid pywbem loggers.
    """
    logger = logging.getLogger(logger_name)
    if logger_name != '' and not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return logger
