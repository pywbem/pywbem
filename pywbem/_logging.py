# Copyright 2016 IBM Corp. All Rights Reserved.
#
# (C) Copyright 2004,2006 Hewlett-Packard Development Company, L.P.
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
This package supports logging using the standard Python :mod:`py:logging`
module. The logging support provides two :class:`~py:logging.Logger` objects:

* 'pywbem.api' for user-issued calls to pywbem CIM OperationsAPI functions, at
  the info level. Internal calls to API functions are not logged.

* 'pywbem.http' for http level information, at the info level.

In addition, there may be loggers for pywbem modules with the module name, for
situations like errors or warnings.

All these loggers have a null-handler (see :class:`~py:logging.NullHandler`)
and have no log formatter (see :class:`~py:logging.Formatter`).

As a result, the loggers are silent by default. To turn on logging,
add a log handler (see :meth:`~py:logging.Logger.addHandler`, and
:mod:`py:logging.handlers` for the handlers included with Python) and set the
log level (see :meth:`~py:logging.Logger.setLevel`, and :ref:`py:levels` for
the defined levels).

If you want to change the default log message format, use
:meth:`~py:logging.Handler.setFormatter`. Its ``form`` parameter is a format
string with %-style placeholders for the log record attributes (see Python
section :ref:`py:logrecord-attributes`).

Examples:

* To output the log records for all cim operations to ``stdout`` in a
  particular format, do this:

  ::

      import logging

      handler = logging.StreamHandler()
      format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
      handler.setFormatter(logging.Formatter(format_string))
      logger = getLogger('pywbem.api')
      logger.addHandler(handler)
      logger.setLevel(logging.INFO)

* This example uses the :func:`~py:logging.basicConfig` convenience function
  that sets the same format and level as in the previous example, but for the
  root logger. Therefore, it will output all log records, not just from this
  package:

  ::

      import logging

      format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
      logging.basicConfig(format=format_string, level=logging.DEBUG)
"""
from __future__ import absolute_import

import sys
import logging
import six

# from ._constants import API_LOGGER_NAME
API_LOGGER_NAME = 'pywbem.api'

#: Name of logger for operantion call methods and their responses.
#:
LOG_OPS_CALLS_NAME = 'pywbem.ops'

#: Name of logger for http information
#:
LOG_HTTP_NAME = 'pywbem.http'

#: pywbem logger names. The following are the logger names that pywbem
# recognizes.

PYWBEM_LOG_COMPONENTS = ['ops', 'http', 'all']

# possible log output destinations
LOG_DESTINATIONS = ['file', 'stderr', 'none']

LOG_DETAIL_LEVELS = ['all', 'min']

DEFAULT_LOG_DETAIL_LEVEL = 'min'
DEFAULT_LOG_LEVEL = 'debug'

LOG_LEVELS = ['error', 'warning', 'info', 'debug']

__all__ = ['PywbemLoggers', 'LOG_DESTINATIONS', 'LOG_LEVELS',
           'PYWBEM_LOG_COMPONENTS', 'LOG_OPS_CALLS_NAME',
           'LOG_DETAIL_LEVELS', 'DEFAULT_LOG_DETAIL_LEVEL', 'DEFAULT_LOG_LEVEL']


class PywbemLoggers(object):
    """
    Container for pywbem logger information when loggers are created.

    There are two constructors for loggers:
      PywbemLoggers.create_loggers - Creates one or more logger entries in
      this class and also in the python logging class from an input string
      with the format defined in the create_loggers method.
      PywbemLoggers.create_logger - Creates a single logger from a the
      separate attributes.

    """
    loggers = {}

    @classmethod
    def __repr__(cls):
        return 'PywbemLoggers(loggers={s.loggers!r})'.format(s=cls)

    @classmethod
    def reset(cls):
        """Reset the logger dictionary. Used primarily in unittests"""
        cls.loggers = {}

    @classmethod
    def create_loggers(cls, input_str, log_filename=None):
        """
        Create the pywbem loggers defined by the input string in the following
        format and place in a class level dictionary in this class:

        Parameters:
          input_str (:term:`string`) that specifies the logger definitions:
            as follows:

            log_spec[,log_spec]

            log_spec := log_comp['=' [dest][":"[detail_level][":"[log_level]]]]

            where:
                comp (str) must be one of PYWBEM_LOG_COMPONENTS
                log_level (str) must be one of LOG_LEVELS above
                detail_level (str) must be one of LOG_DETAIL_LEVELS
                dest (str) must be one of LOG_DESTINATIONS

          log_filename (:term:`string`)
            Optional string that defines the filename for output of logs
            if the dest type is `file`

        Exceptions:
          ValueError if any of the parameters are invalid
        """
        results = cls._parse_log_specs(input_str)
        for name, value in six.iteritems(results):
            cls.create_logger(name, log_dest=value[0],
                              log_detail_level=value[1],
                              log_level=value[2],
                              log_filename=log_filename)

    @classmethod
    def create_logger(cls, log_component, log_dest='stderr',
                      log_filename=None,
                      log_detail_level='all', log_level='debug'):
        """
        Setup a single named logger with the characteristics defined on input.

        This function can be used to set up all of the named loggers used by
        pywbem.

        Parameters:
          log_compnent (:term:`string`):
           The name of the logger. It must be one of the
           names defined in PYWBEM_LOG_COMPONENTS. Subsequent logging users
           will use this name to reference the parameters of this logger

          log_dest (:term:`string`):
            String defining the destination for this log. It must be one of the
            destinations defined in LOG_DESTINATIONS

          log_filename (:term:`string`):
            Filename to use as logging file if the log destination is `file`.
            Ignored if log destination is not `file`. The default is
            DEFAULT_LOG_FILENAME defined in config.py

          log_detail_level (:term:`string`):
            String defining the level of detail for log output. This is
            optional.
            Not all of the loggers use this attribute.  Thus, the ops and http
            loggers used a defined detail level and always set logging to that
            level.

          log_level (:term:`string`):
            String defining the log level. This is optional.  Not all of the
            loggers use this attribute.  Thus, the ops and http loggers used a
            defined level and always set logging to that level.

        Return:
            None

        Exceptions:
            ValueError - Input cannot be mapped to a defined logger or
            component.
            No named logger is created.
        """
        if log_dest not in LOG_DESTINATIONS:
            raise ValueError('Invalid log destination %s. Not in list %s' %
                             (log_dest, LOG_DESTINATIONS))
        if log_component not in PYWBEM_LOG_COMPONENTS:
            raise ValueError('Invalid log component %s. Not in list %s' %
                             (log_component, PYWBEM_LOG_COMPONENTS))
        if not log_level:
            log_level = DEFAULT_LOG_LEVEL
        if log_level not in LOG_LEVELS:
            raise ValueError('Invalid log level %s. Not in list %s' %
                             (log_level, LOG_LEVELS))

        if not log_detail_level:
            log_detail_level = DEFAULT_LOG_DETAIL_LEVEL
        if log_detail_level not in LOG_DETAIL_LEVELS:
            raise ValueError('Invalid log detail %s. Not in list %s' %
                             (log_detail_level, LOG_DETAIL_LEVELS))

        # If destinations or components is all, recurse for all destinations
        if log_dest == 'all':
            for dest in LOG_DESTINATIONS:
                cls.create_logger(log_component, dest,
                                  log_filename=log_filename,
                                  log_detail_level=log_detail_level,
                                  log_level=log_level)
        elif log_component == 'all':
            for comp in PYWBEM_LOG_COMPONENTS:
                if comp != 'all':
                    cls.create_logger(comp, log_dest=log_dest,
                                      log_filename=log_filename,
                                      log_detail_level=log_detail_level,
                                      log_level=log_level)

        # Otherwise process results of any recursive calls above
        else:
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
                handler = None
                format_string = None

            # set the logger name based on the log_component.
            if log_component == 'http':
                logger_name = LOG_HTTP_NAME
                if log_level is None:
                    log_level = 'debug'
            elif log_component == 'ops':
                logger_name = LOG_OPS_CALLS_NAME
                if log_level is None:
                    log_level = 'debug'
            else:
                raise ValueError('Invalid log_component %s' % log_component)

            # Set the log level based on the log_level input
            level = getattr(logging, log_level.upper(), None)
            # check logging log_level_choices have not changed from expected
            assert isinstance(level, int)
            if level is None:
                raise ValueError('Invalid log level %s specified. Must be one '
                                 'of %s.' % (log_level, LOG_LEVELS))

            # create named logger
            if handler:
                handler.setFormatter(logging.Formatter(format_string))
                logger_ops = logging.getLogger(logger_name)
                logger_ops.addHandler(handler)
                logger_ops.setLevel(level)

            # save the detail level in the dict that is part of this class.
            # All members of this tuple are just viewing except detail
            # that is used by individual loggers
            cls.loggers[logger_name] = (log_detail_level, log_level,
                                        log_dest, log_filename)

    @classmethod
    def get_logger_detail(cls, logger_name):
        """
            Get the name of a logger that has been defined.
        """
        if logger_name in cls.loggers:
            return cls.loggers[logger_name][0]
        return None

    @classmethod
    def get_logger_info(cls, logger_name):
        """Get information about a logger by name"""
        if logger_name in cls.loggers:
            t = cls.loggers[logger_name]
            return 'comp=%s dest %s detail %s log_level %s ' \
                   'file %s' % (logger_name, t[3], t[0], t[2], t[3])
        return('%s not defined' % logger_name)

    @classmethod
    def _parse_log_specs(cls, log_spec_str):
        """
        Parse a complete cmd line log specification that is in the
        format defined in PywbemLoggers.create_logger

          Parameters:
            log_spec_str (:term:`string`) containing the log spec string

          Return:
            Dictionary containing the parsed information where each entry is
            log_comp (detail_level, log_level,  dest)

          Exception:
            ValueError if parse fails
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
            while len(log_values) < 3:
                log_values.append(None)

            if len(log_values) > 3:
                raise ValueError("Invalid log detail. %s too many "
                                 "components."
                                 % log_spec)
            log_specs_dict[log_component] = tuple(log_values)
        return log_specs_dict


def get_logger(name):
    """
    Return a :class:`~py:logging.Logger` object with the specified name.

    A :class:`~py:logging.NullHandler` handler is added to the logger if it
    does not have any handlers yet. This prevents the propagation of log
    requests up the Python logger hierarchy, and therefore causes this package
    to be silent by default.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return logger
