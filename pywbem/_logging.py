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

"""
**Experimental:** *New in pywbem 0.11 as experimental.*

The pywbem package implements selected logging based on the Python
:mod:`py:logging` facility.

Pywbem logging is used to record information passing between the pywbem client
and WBEM servers but not as a general recorder for errors, state, etc. within
pywbem. Pywbem errors are generally passed to the pywbem API user as
Python exceptions rather than being recorded in a log by a pywbem logger.

Pywbem logging supports multiple :class:`~py:logging.Logger` objects
(named loggers). Two named loggers are used by pywbem:

* ``pywbem.ops`` logs user-issued calls to :class:`~pywbem:WBEMConnection`
  methods that drive WBEM operations (see :ref:`WBEM operations`) and the
  responses before they are passed back to the user. Log entries are created at
  DEBUG log level. This logs the parameters of each request and the results
  including CIMObjects/exceptions in each method repoonse.

* ``pywbem.http`` logs HTTP requests and responses between the pywbem client
  and WBEM server. This logs the http request data and response data including
  http headers and XML payload.


Both of the above loggers create log entries when logging is at the DEBUG log
level.

The user can use Python logger methods to define the handles for either or both
of these loggers. In addition, helper functions are defined in pywbem
to define the characteristics ofthese loggers.

Once the loggers are defined, logging is activated in
:class:`~pywbem.WBEMConnection` with the `enable_logging` parameter which
both activates logging and allows defining the detail level of the log
output.

The following example sets up the operations logger using Python logger
methods to log to stdout::

    logger = logging.getLogger('pywbem.ops')
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    conn.WBEMConnection(... enable_log='all')


The helper functions in _logging are intended to provide tools for
users of pywbem that want one or two line setup for logs as follows:

* :meth:`~pywbem._logging.define_loggers_from_string` defines one or more
  loggers from  a string input that defines the component name and
  characteristics of each logger.  This allows other tools like CLIs that use
  pywbem to create the pywbem known logs with minimal work from command line or
  config file input.

* :meth:`~pywbem._logging.define_logger` defines  one
  logger from parameter inputs that define the component name and
  characteristics of the logger.

Thus to setup loggers that log all of the operations requests and responses
both for http and the APIs either of the following could be use::

    # Log ops to stderr and http to file but only log the first n characters
    # where n is defined by the pywbem variable `DEFAULT_MAX_LOG_ENTRY_SIZE`
    define_logger('ops', 'stderr')
    define_logger('http', 'file', log_filename='mylog.log')
    conn = WBEMConnection(..., enable_log=min)

    # Log everything to stderr and output all of the information
    define_loggers_from_string('all=stderr')
    conn = WBEMConnection(..., enable_log='all')

    # Log only http requests and responses to a file
    define_logger('http', 'file', log_filename='mylog.log')
    conn = WBEMConnection(..., enable_log=min)

The pywbem loggers are based one parameters (log destination)
that determine if the logs for the logger name are created,
and the log destination.

Logging may be define differently for different WBEMConnections by adding
the WBEMConnection id as a part of the logger component.  Thus::

    define_logger('ops', 'stderr')
    define_logger('http', 'file', log_filename='mylog.log')
    conn1 = WBEMConnection(..., enable_log="min")


    logger = logging.getLogger('pywbem.ops.%s' % conn2.conn_id)

    handler = logging.FileHandler('logfilename.log')
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    conn2 = WBEMConnection(..., enable_log='all")


Since logging can generate extensive output, :class:`~pywbem:WBEMConnection`
allows the user to both activate the defined logging and set log output
detail level options for the output logs.

If logging is activated without any loggers being defined the
logging NULLHandler is set for both the operations and http loggers.
"""
from __future__ import absolute_import

import logging

__all__ = ['define_logger', 'define_loggers_from_string',
           'LOG_OPS_CALLS_NAME', 'LOG_HTTP_NAME', 'LOG_COMPONENTS',
           'LOG_DESTINATIONS', 'LOG_DETAIL_LEVELS', 'DEFAULT_LOG_DETAIL_LEVEL',
           'DEFAULT_MAX_LOG_ENTRY_SIZE', 'DEFAULT_LOG_DESTINATION']

#: Name of logger for logging user-issued calls to
#: :class:`~pywbem.WBEMConnection` methods that drive WBEM operations.
LOG_OPS_CALLS_NAME = 'pywbem.ops'

#: Name of logger for HTTP requests and responses between the pywbem client and
#: WBEM servers.
LOG_HTTP_NAME = 'pywbem.http'

#: List of the logger names that the logging configureation helper functions
#: recognize. This allows setting up either logger individually or both to the
#: same destination.
LOG_COMPONENTS = ['ops', 'http', 'all']

#: List of log destinations that the logging configuration helper functions
#: recognize.
LOG_DESTINATIONS = ['file', 'stderr', 'none']

#: List of the log detail strings that the logging configuration helper
#: functions recognize.
LOG_DETAIL_LEVELS = ['all', 'min']

#: Default log detail level string if none is supplied with a call to the
#: :class:`pywbem._logging.PywbemLoggers` methods that configure pywbem named
#: loggers
DEFAULT_LOG_DETAIL_LEVEL = 'all'

#: Default maximum log entry size if none is supplied when creating
#: enabling logging as part of a WBEMConnection.
DEFAULT_MAX_LOG_ENTRY_SIZE = 1000

#: Default log destination if none is defined when named loggers are
#: configured. 'none' means that there is no logging.
DEFAULT_LOG_DESTINATION = 'none'


def define_loggers_from_string(log_spec_str, log_filename=None):
    # pylint: disable=line-too-long
    """
    Create the pywbem loggers defined by the input string in the following
    syntax and place the logger definitions in the class level dictionary
    in this class.

    Parameters:

      input_str (:term:`string`): Specifies the logger definitions
        as follows:

        ``log_specs`` := ``log_spec`` [, ``log_spec`` ]

        ``log_spec`` := ``log_comp`` ['=' [ ``dest`` ]]]

        where:

        * ``log_comp``: Must be one of strings in the
          :data:`~pywbem._logging.LOG_COMPONENTS` list.

      log_filename (:term:`string`)
        Optional string that defines the filename for output of logs
        if the dest type is `file`

    Raises:

      ValueError: Generated if the syntax of the input string is invalid
        or any of the components is not one of allowed strings.

    Examples::

        ops=stderr    # set cim operations logger

        http=file     # set http logger to send to file

        all=file      # Set all loggers to output to a file
    """  # noqa: E501

    log_specs = log_spec_str.split(',')
    for log_spec in log_specs:
        try:
            spec_split = log_spec.split("=", 1)
        except ValueError:
            raise ValueError('Log spec %s invalid. Contains too many '
                             ' components' % log_spec)
        if len(spec_split) == 1:
            log_component = spec_split[0]
            log_dest = ''
        elif len(spec_split) == 2:
            log_component = spec_split[0]
            log_dest = spec_split[1]
        else:
            raise ValueError("Log component name required in %s" % log_spec)

        # cvt empty strings to None
        log_dest = 'none' if log_dest == '' else log_dest
        define_logger(log_component, log_dest=log_dest,
                      log_filename=log_filename)


def define_logger(log_component, log_dest=DEFAULT_LOG_DESTINATION,
                  log_filename=DEFAULT_LOG_DESTINATION):
    """
    This is a helper function to define a single pywbem logger with the
    logger name defined by log_component
    Create create the logger with the name defined by log_component and with
    the parameters defined by log_dest and log-filename.

    This function can be used to set up all of the named loggers used by
    pywbem.

    This function sets up the logger name, and a formatter and also defines
    the log destination.

    Parameters:

      log_component (:term:`string`):
        The name of the logger. It must be one of the
        names defined in :data:`~pywbem._logging.LOG_COMPONENTS`.
        Used to create the logger name by prepending with the logger name
        prefix ``pywbem.``.  The log_component may include a suffix component
        to uniquely identify a logger. This is identified with  a period
        between the log_component name and the suffix. Normally this is
        used to define a logger specifically for a selected connection and
        the suffix is the conn_id of the WBEMConnection.

      log_dest (:term:`string`):
        String defining the destination for this log. It must be one of the
        destinations defined in :data:`~pywbem._logging.LOG_DESTINATIONS`
        or `None`. If the value is the string ``none``, the null logger is
        created.

      log_filename (:term:`string`):
        Filename to use as logging file if the log destination is `file`.
        Ignored if log destination is not `file`. If value is `None` and
        this is a ``file`` log, ValueError is raised.

    Raises:

      ValueError: Input contains an invalid log destination, log level,
        or log detail level. No named logger is configured.
    """
    if log_component == 'all':
        for comp in LOG_COMPONENTS:
            if comp != 'all':
                define_logger(comp, log_dest=log_dest,
                              log_filename=log_filename)

    # Otherwise process results of any recursive calls above
    else:
        if log_dest not in LOG_DESTINATIONS:
            raise ValueError('Invalid log destination "%s". valid log '
                             'destinations are: %s' %
                             (log_dest, LOG_DESTINATIONS))

        if '.' in log_component:
            log_name, log_suffix = log_component.split('.', 1)
        else:
            log_suffix = ''
            log_name = log_component

        if log_name not in LOG_COMPONENTS:
            raise ValueError('Invalid log component "%s". Valid log '
                             'components are: %s' %
                             (log_component, LOG_COMPONENTS))

        if log_dest == 'stderr':
            handler = logging.StreamHandler()
            format_string = '%(asctime)s-%(name)s-%(message)s'
        elif log_dest == 'file':
            if not log_filename:
                raise ValueError('Filename required if log destination '
                                 'is "file"')
            handler = logging.FileHandler(log_filename)
            format_string = '%(asctime)s-%(name)s-%(message)s'
        else:
            assert(log_dest == 'none')
            handler = logging.NullHandler()
            format_string = None

        # set the logger name based on the log_component.
        if log_name == 'http':
            logger_name = LOG_HTTP_NAME
        elif log_name == 'ops':
            logger_name = LOG_OPS_CALLS_NAME
        else:
            raise ValueError('Invalid log_component %s' % log_name)

        if log_suffix:
            logger_name = '%s.%s' % (logger_name, log_suffix)

        # create named logger. We allow only a single handler for
        # any logger so must remove any existing handler before adding
        #
        if handler:
            handler.setFormatter(logging.Formatter(format_string))
            logger = logging.getLogger(logger_name)
            for hdlr in logger.handlers:
                logger.removeHandler(hdlr)
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)


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
        as prefix . <log_component>

    Returns:

      :class:`~py:logging.Logger`: Logger defined by logger name.

    Raises:

      ValueError: The name is not one of the valid pywbem loggers.
    """
    logger = logging.getLogger(logger_name)
    if logger_name != '' and not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return logger
