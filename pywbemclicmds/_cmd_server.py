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
Click command definition for the server command group which includes
cmds for inspection and management of the objects defined by the pywbem
server class including namespaces, WBEMServer information, and profile
information.
"""
from __future__ import absolute_import

import click
from pywbem import Error, ValueMapping
from .pywbemclicmd import pywbemcli, CMD_OPTS_TXT
from ._common import display_result
from ._common_options import sort_option, add_options


def print_profile_info(org_vm, inst):
    """Print the registered org, name, version for the profile defined by
       inst
    """
    org = org_vm.tovalues(inst['RegisteredOrganization'])
    name = inst['RegisteredName']
    vers = inst['RegisteredVersion']
    print("  %s %s Profile %s" % (org, name, vers))


@pywbemcli.group('server', options_metavar=CMD_OPTS_TXT)
def class_group():
    """
    Command group for server operations.
    """
    pass


@class_group.command('namespaces', options_metavar=CMD_OPTS_TXT)
@add_options(sort_option)
@click.pass_obj
def server_namespaces(context, **options):
    """
    Display the set of namespaces in the current WBEM server
    """
    context.execute_cmd(lambda: cmd_server_namespaces(context, options))


@class_group.command('interop', options_metavar=CMD_OPTS_TXT)
@add_options(sort_option)
@click.pass_obj
def server_interop(context, **options):
    """
    Display the interop namespace name in the WBEM Server.
    """
    context.execute_cmd(lambda: cmd_server_interop(context, options))


@class_group.command('brand', options_metavar=CMD_OPTS_TXT)
@add_options(sort_option)
@click.pass_obj
def server_brand(context, **options):
    """
    Display the interop namespace name in the WBEM Server.
    """
    context.execute_cmd(lambda: cmd_server_brand(context, options))


@class_group.command('info', options_metavar=CMD_OPTS_TXT)
@click.pass_obj
def server_info(context, **options):
    """
    Display the brand information on the current WBEM Server.
    """
    context.execute_cmd(lambda: cmd_server_info(context, options))


@class_group.command('profiles', options_metavar=CMD_OPTS_TXT)
@click.option('-o', '--organization', type=str, required=False,
              help='Filter by the defined organization. (ex. -o DMTF_')
@click.option('-n', '--profilename', type=str, required=False,
              help='Filter by the profile name. (ex. -n Array')
@click.pass_obj
def server_profiles(context, **options):
    """
    Display the brand information on the current WBEM Server.
    """
    context.execute_cmd(lambda: cmd_server_profiles(context, options))

@class_group.command('connection', options_metavar=CMD_OPTS_TXT)
@click.pass_obj
def server_connection(context, **options):
    """
    Display information on the connection used by this server.
    """
    context.execute_cmd(lambda: cmd_server_connection(context))


###############################################################
#         Server cmds
###############################################################
def cmd_server_namespaces(context, options):
    """
    Get the list of namespaces from the current WBEMServer
    """
    ns = context.wbem_server.namespaces
    display_result(ns)


def cmd_server_interop(context, options):
    """
    Get the list of namespaces from the current WBEMServer
    """
    display_result(context.wbem_server.interop_ns)


def cmd_server_brand(context, options):
    """
    Get the list of namespaces from the current WBEMServer
    """
    display_result(context.wbem_server.brand)


def cmd_server_info(context, options):
    """
    Display general overview of info from current WBEMServer
    """

    print("Brand:\n  %s" % context.wbem_server.brand)
    print("Version:\n  %s" % context.wbem_server.version)
    print("Interop namespace:\n  %s" % context.wbem_server.interop_ns)

    print("All namespaces:")
    for ns in context.wbem_server.namespaces:
        print("  %s" % ns)


def cmd_server_profiles(context, options):
    """
    Display general overview of info from current WBEMServer
    """
    found_server_profiles = context.wbem_server.get_selected_profiles(
        options['organization'],
        options['profilename'])

    org_vm = ValueMapping.for_property(context.wbem_server,
                                       context.wbem_server.interop_ns,
                                       'CIM_RegisteredProfile',
                                       'RegisteredOrganization')

    print('Profiles for %s:%s' % (options['organization'],
                                  options['profilename']))
    for inst in found_server_profiles:
        print_profile_info(org_vm, inst)

def cmd_server_connection(context):
    conn = context.conn
    print('url %s: ' %conn.url)
    print('creds %s: ' %conn.creds)
    print('.x509 %s: ' %conn.x509)
    print('verify_callback: %s' %conn.verify_callback)
    print('default_namespace: %s' %conn.default_namespace)
    print('timeout: %s sec.' %conn.timeout)
    print('ca_certs: %s ' % conn.ca_certs)
