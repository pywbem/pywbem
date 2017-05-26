"""
Defines click options that are used for multiple subcommands and that have
the same definition throughout the environment.  This allows the characteristics
and help to be defined once and used multiple times.
"""
from __future__ import absolute_import

import click

#
# property_list opetion - Defined here because the option is used in
# multiple places in the command structure.
#
propertylist_option = [                      # pylint: disable=invalid-name
    click.option('-p', '--propertylist', multiple=True, type=str,
                 default=None,
                 help='Define a propertylist for the request. If not included '
                      'a Null property list is defined and the server '
                      'returns all properties. If defines as empty string '
                      'the server returns no properties'
                      ' ex: -p propertyname1 -p propertyname2')]

names_only_option = [                      # pylint: disable=invalid-name
    click.option('-o', '--names_only', is_flag=True, required=False,
                 help='Show only local properties of the class.')]

sort_option = [                            # pylint: disable=invalid-name
    click.option('-s', '--sort', is_flag=True, required=False,
                 help='Sort into alphabetical order by classname.')]

includeclassorigin_option = [            # pylint: disable=invalid-name
    click.option('-c', '--includeclassorigin', is_flag=True,
                 required=False,
                 help='Include classorigin in the result.')]

namespace_option = [                     # pylint: disable=invalid-name
    click.option('-n', '--namespace', type=str,
                 required=False,
                 help='Namespace to use for this operation. If defined that '
                      'namespace overrides the general options namespace')]


def add_options(options):
    """
    Accumulate multiple options into a list. This list can be referenced as
    a click decorator @att_options(name_of_list)

    The list is reversed because of the way click processes options

    Parameters:

      options: list of click.option definitions

    Returns:
        Reversed list

    """
    def _add_options(func):
        """ Reverse options list"""
        for option in reversed(options):
            func = option(func)
        return func
    return _add_options
