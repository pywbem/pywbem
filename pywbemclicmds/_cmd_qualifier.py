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
#
"""
Click Command definition for the qualifer command group which includes
cmds for get and enumerate for CIM qualifier types.
"""

from __future__ import absolute_import

import click
from pywbem import Error
from .pywbemclicmd import pywbemcli, CMD_OPTS_TXT
from ._common import display_result
from ._common_options import sort_option, namespace_option, add_options


@pywbemcli.group('qualifier', options_metavar=CMD_OPTS_TXT)
def qualifier_group():
    """
    Command group for qualifier declaration subcommands.

    Includes the capability to get and enumerate qualifier declarations.

    This does not provide the capability to create or delete CIM
    QualifierDeclarations
    """
    pass


@qualifier_group.command('get', options_metavar=CMD_OPTS_TXT)
@click.argument('NAME', type=str, metavar='NAME', required=True,)
@add_options(namespace_option)
@click.pass_obj
def qualifier_get(context, name, **options):
    """
    Display a single CIMQualifierDeclaration for the defined namespace.
    """
    context.execute_cmd(lambda: cmd_qualifier_get(context, name, options))


@qualifier_group.command('enumerate', options_metavar=CMD_OPTS_TXT)
@add_options(sort_option)
@add_options(namespace_option)
@click.pass_obj
def qualifier_enumerate(context, **options):
    """
    Enumerate CIMQualifierDeclaractions for the defined namespace.
    """
    context.execute_cmd(lambda: cmd_qualifier_enumerate(context, options))


####################################################################
#   Qualifier declaration command processing functions
#####################################################################
def cmd_qualifier_get(context, name, options):
    """
    Execute the command for get qualifier and display result
    """
    try:
        if context.verbose:
            print('get qualifier name: %s ' % (name))

        result = context.conn.GetQualifier(name,
                                           namespace=options['namespace'])
        display_result(result)
    except Error as er:
        raise click.ClickException("%s: %s" % (er.__class__.__name__, er))


def cmd_qualifier_enumerate(context, options):
    """
    Execute the command for enumerate qualifiers and desplay the result.
    """
    try:
        result = context.conn.EnumerateQualifiers(
            namespace=options['namespace'])
        display_result(result)
    except Error as er:
        raise click.ClickException("%s: %s" % (er.__class__.__name__, er))
