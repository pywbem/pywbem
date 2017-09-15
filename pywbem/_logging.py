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
The pywbem package implements selected logging based on the Python
:mod:`py:logging` facility.

Pywbem logging is used as a tool to record information passing between
the pywbem client and WBEM servers but not as a general recorder for errors,
state, etc. within pywbem. Pywbem errors are generally passed to the pywbem API
user as python exceptions rather than being recorded in a log by a pywbem
logger.

Pywbem logging supports multiple :class:`~py:logging.Logger` objects
(named loggers). Two named loggers are defined in this code and used
by pywbem:

* ``pywbem.ops`` logs user-issued calls to pywbem WBEMConnection methods that
  drive WBEM operations (see :ref:`WBEM operations`). Log
  entries are created at INFO log level. This logs the parameters of each
  request and the CIMObjects/exceptions in each method repoonse.

* ``pywbem.http`` logs HTTP requests and responses between the pywbem client
  and WBEM servers, at the info level. This logs the http request data and
  response data. This named logger is also defined to create log entries when
  logging is at the INFO log level.

To output log records for one of the defined named loggers, either
:meth:`~pywbem.PywbemLoggers.create_loggers` or the
:meth:`~pywbem.PywbemLoggers.create_logger` should be used to define the
characteristics of the named logger.

* :meth:`~pywbem.PywbemLoggers.create_loggers` creates one or more loggers from
  a string input that defines the component name and characteristics of each
  logger.  This allows other tools like CLIs that use pywbem to create the
  pywbem known logs with minimal work from command line or config file input.

* :meth:`~pywbem.PywbemLoggers.create_logger` creates one or more loggers from
  parameter inputs that define the component name and characteristics of each
  logger.

These functions save the logger definitions in the PywbemLoggers class that
is used by the logging functions in the recorder so trying to create the named
loggers independently of this code may cause issues.

The pywbem loggers are based on two parameters (log destination, log detail)
that determine if the logs for the logger name are created,
how much information is inserted, and the log destination.  This
extends the python logging facility to include the log_detail parameter which
defines whether all the information defined or only a limited size is output.
This is used with pywbem because the logs on operation and http responses can be
very large.

The code that executes the loggers call the function get_logger(..) to get a
logger from a defined logger name.  If that logger has not yet been defined
in PywbemLoggers, an entry will be added with the default parameters.
"""
from __future__ import absolute_import

import logging
import six

__all__ = ['PywbemLoggers', 'LOG_DESTINATIONS', 'LOG_COMPONENTS',
           'LOG_OPS_CALLS_NAME', 'LOG_DETAIL_LEVELS', 'DEFAULT_LOG_DESTINATION',
           'MAX_LOG_ENTRY_SIZE']

#: Name of logger for logging user-issued calls to pywbem WBEMConnection
#: methods functions that drive WBEM operations.
LOG_OPS_CALLS_NAME = 'pywbem.ops'

#: Name of logger for HTTP requests and responses between the pywbem client and
#: WBEM servers.
LOG_HTTP_NAME = 'pywbem.http'

#: List of the logger names that class:`pywbem.PywbemLoggers` recognizes:
LOG_COMPONENTS = ['ops', 'http', 'all']

#: List of log destinations that :class:`pywbem.PywbemLoggers`
#: recognizes.
LOG_DESTINATIONS = ['file', 'stderr', 'none']

#: list of the log detail strings that :class:`pywbem.PywbemLoggers` recognizes.
LOG_DETAIL_LEVELS = ['all', 'min']

#: Default log detail level string if none is supplied with a call to the
#: :class:`pywbem.PywbemLoggers` methods that configure pywbem named loggers
DEFAULT_LOG_DETAIL_LEVEL = 'min'

#: Maximum log entry size. An integer that sets the maximum size of each log
#: entry if the log_detail_level attribute is set to 'min' is set.
MAX_LOG_ENTRY_SIZE = 1000

#: DEFAULT log destination is none is defined when named loggers are
#: configured. 'none' means that there is no logging.
DEFAULT_LOG_DESTINATION = 'none'


class MetaPywbemLoggers(type):
    """
    This metaclass allows the definition of __str__ and __repr__ at the
    class level in the subclass.
    **Experimental:** The logging support is experimental for this release.
    """
    loggers = {}

    def __str__(cls):
        return 'PywbemLoggers(loggers={s.loggers!r})'.format(s=cls)

    def __repr__(cls):
        return 'PywbemLoggers({s.loggers!r})'.format(s=cls)


# pylint: disable=no-init
class PywbemLoggers(six.with_metaclass(MetaPywbemLoggers)):
    """
    Container for pywbem logger information when loggers are created. This
    class is a singleton, there is only one set of data for a pywbem
    instantiation.  Its goal is to defined named loggers from data input and
    too record information about these named loggers in a dictionary for
    use by the log functions

    This is defined with only class level object and methods as an
    easy way to create a singleton. However, at least in python 2.6, you
    cannot make some magic methods work (ex.__getItem__)

    There are two constructors for loggers:

      :meth:`~pywbem.PywbemLoggers.create_loggers` - Creates one or more logger
      entries in this class and also in the python logging class from an input
      string with the format defined in the create_loggers method below.

      :meth:`~pywbem.PywbemLoggers.create_logger` - Creates a single logger
      from the separate pywbem logging parameters supplied with the method.

    **Experimental:** The logging support is experimental for this release.
    """

    @classmethod
    def create_loggers(cls, input_str, log_filename=None):
        # pylint: disable=line-too-long
        """
        Create the pywbem loggers defined by the input string in the following
        syntax and place the logger definitions in the class level dictionary
        in this class.

        Parameters:
          input_str (:term:`string`) that specifies the logger definitions:
            as follows:

            ``log_specs`` := ``log_spec`` [, ``log_spec`` ]

            ``log_spec`` := ``log_comp`` ['=' [ ``dest`` ][":"[ ``detail_level`` ]]]]

            where:
                ``log_comp``: Must be one of strings in the :data:`~pywbem._logging.LOG_COMPONENTS` list.

                ``detail_level``: Must be one of strings in the :data:`~pywbem._logging.LOG_DETAIL_LEVELS` list.

                ``dest``: Must be one of strings in the :data:`~pywbem._logging.LOG_DESTINATIONS` list.

          log_filename (:term:`string`)
            Optional string that defines the filename for output of logs
            if the dest type is `file`

        Exceptions:
          ValueError - Generated if the syntax of the input string is invalid
          or any of the components is not one of allowed strings.

        Examples:
            ``ops=stderr:min``    # set cim operations logger

            ``http=file:``        # set http logger to send to file

            ``all=file:all``      # Set all loggers to default log destination
        """  # noqa: E501
        # pylint: enable=line-too-long

        results = cls._parse_log_specs(input_str)
        for name, value in six.iteritems(results):
            cls.create_logger(name, log_dest=value[0],
                              log_detail_level=value[1],
                              log_filename=log_filename)

    @classmethod
    def create_logger(cls, log_component, log_dest=DEFAULT_LOG_DESTINATION,
                      log_filename=DEFAULT_LOG_DESTINATION,
                      log_detail_level=DEFAULT_LOG_DETAIL_LEVEL):
        """
        Create the logger defined by the input parameters and place the result
        in a class level dictionary in this class.

        This function can be used to set up all of the named loggers used by
        pywbem.

        Parameters:
          log_component (:term:`string`):
           The name of the logger. It must be one of the
           names defined in LOG_COMPONENTS. Used to create the logger name by
           prepending with the logger name prefix ``pywbem.``.

          log_dest (:term:`string`):
            String defining the destination for this log. It must be one of the
            destinations defined in LOG_DESTINATIONS or None. If the value is
            ``none`` the null logger is created.

          log_filename (:term:`string`):
            Filename to use as logging file if the log destination is `file`.
            Ignored if log destination is not `file`. If value is None and
            this is a ``file`` log, ValueError is raised.

          log_detail_level (:term:`string`):
            String defining the level of detail for log output. This is
            optional. The default is defined in DEFAULT_LOG_DETAIL_LEVEL.

        Exceptions:
            ValueError - Input contains an invalid log destination, log level,
            or log detail level. No named logger is configured.
        """
        if log_component == 'all':
            for comp in LOG_COMPONENTS:
                if comp != 'all':
                    cls.create_logger(comp, log_dest=log_dest,
                                      log_filename=log_filename,
                                      log_detail_level=log_detail_level)

        # Otherwise process results of any recursive calls above
        else:
            if log_dest not in LOG_DESTINATIONS:
                raise ValueError('Invalid log destination %s. valid log '
                                 'destinations are: %s' %
                                 (log_dest, LOG_DESTINATIONS))
            if log_component not in LOG_COMPONENTS:
                raise ValueError('Invalid log component %s. Valid log '
                                 'components are: %s' %
                                 (log_component, LOG_COMPONENTS))
            if not log_detail_level:
                log_detail_level = DEFAULT_LOG_DETAIL_LEVEL
            if log_detail_level not in LOG_DETAIL_LEVELS:
                raise ValueError('Invalid log detail %s. Valid Log detail '
                                 'levels are %s' %
                                 (log_detail_level, LOG_DETAIL_LEVELS))

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
            if log_component == 'http':
                logger_name = LOG_HTTP_NAME
            elif log_component == 'ops':
                logger_name = LOG_OPS_CALLS_NAME
            else:
                raise ValueError('Invalid log_component %s' % log_component)

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

            # save the detail level in the dict that is part of this class.
            # All members of this tuple are just for information.
            cls.loggers[logger_name] = (log_detail_level,
                                        log_dest,
                                        log_filename)

    @classmethod
    def get_logger_info(cls, logger_name):
        """
        Get information about a logger by name.

        Parameters:
           logger_name(:term:`string`)
              The pywbem logger name (ex. pywbem.ops)

        Returns:
           Tuple with the following information in the tuple:
           (log_detail_level, log_level, log_dest, log_filename)
           or 'None' if the logger has not been defined to PywbemLoggers
        """
        return cls.loggers.get(logger_name, None)

    @classmethod
    def _parse_log_specs(cls, log_spec_str):
        """
        Parse a complete cmd line log specification that is in the
        format defined in PywbemLoggers.create_logger

          Parameters:
            log_spec_str (:term:`string`) containing the log spec string

          Return:
            Dictionary containing the parsed information where each entry is
            log_comp (detail_level, dest)

          Exception:
            ValueError The parsing of the input string failed.
        """
        log_specs_dict = dict()
        log_specs = log_spec_str.split(',')
        for log_spec in log_specs:
            try:
                log_component, log_data = log_spec.split("=", 1)
            except ValueError:
                log_component = log_spec
                log_data = ''

            log_values = log_data.split(":")

            if not log_component:
                raise ValueError("Log component name required in %s" % log_spec)

            # cvt empty strings to None
            log_values = [None if x == '' else x for x in log_values]
            # expand to full size if not all values supplied
            while len(log_values) < 2:
                log_values.append(None)

            if len(log_values) > 2:
                raise ValueError("Invalid log detail. %s too many "
                                 "components."
                                 % log_spec)
            log_specs_dict[log_component] = tuple(log_values)
        return log_specs_dict


def get_logger(logger_name):
    """
    Return a :class:`~py:logging.Logger` object with the specified name.

    A logger is defined in :class:`~pywbem.PywbemLogger` if it does not
    already exist. This creates a logger with a log_component and the default
    properties defined for :meth:`~pywbem.PywbemLogger.create_logger`.

    This prevents the propagation of log requests up the Python logger
    hierarchy, and therefore causes this package to be silent by default.

    Parameters
        logger_name(:term:`string`)
            Name of the logger which must be one of the named defined in
            pywbem for loggers used by pywbem.  These names are structured
            as prefix . <log_component>

    Returns:
        logger defined by logger name

    Exceptions:
        ValueError if the name is not one of the valid pywbem loggers.

    **Experimental:** The logging support is experimental for this release.
    """
    if PywbemLoggers.get_logger_info(logger_name) is None:
        # pylint: disable=unused-variable
        log_prefix, log_comp = logger_name.split('.')
        # create PywbemLogger with default values
        PywbemLoggers.create_logger(log_comp)
    return logging.getLogger(logger_name)
