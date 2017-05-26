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
Click command definition for the pywbemcli command, the top level command for
the pywbemcli click tool
"""
from __future__ import absolute_import

import re
from click_repl import repl
import click
# import click_spinner
from pywbem import WBEMConnection, CIMInstanceName, WBEMServer
from ._common import remote_connection

__all__ = ['pywbemcli']


# uses -h  and --help rather than just --help
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
# Display of options in usage line
GENERAL_OPTIONS_METAVAR = '[GENERAL-OPTIONS]'
CMD_OPTS_TXT = '[COMMAND-OPTIONS]'

DEFAULT_OUTPUT_FORMAT = 'mof'
DEFAULT_NAMESPACE = 'root/cimv2'

# TODO how can we express that we want output to be summary or full
# TODO express system default in the help.
# TODO fix up all of the system/config default options.

@click.group(invoke_without_command=True,
             options_metavar=GENERAL_OPTIONS_METAVAR)
@click.option('-s', '--server', type=str, envvar='WBEM_SERVER',
              help="Hostname or IP address of the WBEMServer "
                   "(Default: WBEM_SERVER environment variable).")
@click.option('-d', '--default_namespace', type=str, envvar='WBEM_NAMESPACE',
              help="Default Namespace to use in the target WBEMServer if no "
                   "namespace is defined in the subcommand"
                   "(Default: WBEM_NAMESPACE environment variable or "
                   "pywbemcli default TODO).")
@click.option('-u', '--user', type=str, envvar='WBEM_USER',
              help="Username for the WBEM Server "
                   "(Default: WBEM_USER environment variable).")
@click.option('-p', '--password', type=str, envvar='WBEM_PASSWORD',
              help="Password for the WBEM Server "
                   "(Default: WBEM_PASSWORD environment variable).")
@click.option('-t', '--timeout', type=str, envvar='WBEM_TIMEOUT',
              help="Operation timeout for the WBEM Server "
                   "(Default: WBEM_TIMEOUT environment variable).")
@click.option('-n', '--noverify', type=str, is_flag=True,
              help='If set, client does not verify server certificate.')
@click.option('-k', '--certfile', type=str, envvar='WBEM_CERTFILE',
              help="Server certfile. Not used if noverify set"
                   "(Default: WBEM_KEYFILE environment variable).")
@click.option('-k', '--keyfile', type=str, envvar='WBEM_KEYFILE',
              help="Client private key file"
                   "(Default: WBEM_KEYFILE environment variable).")
@click.option('-o', '--output-format',
              type=click.Choice(['mof', 'xml', 'table', 'csv', 'text']),
              help='Output format (Default: {of}).'
              .format(of=DEFAULT_OUTPUT_FORMAT))
@click.option('-v', '--verbose', type=str, is_flag=True,
              help='Display extra information about the processing.')
@click.version_option(help="Show the version of this command and exit.")
@click.pass_context
def pywbemcli(ctx, server, default_namespace, user, password, timeout, noverify,
         certfile, keyfile, output_format, verbose, conn=None,
         wbem_server=None):
    """
    Command line browser for WBEM Servers. This cli tool implements the
    CIM/XML client APIs as defined in pywbem to make requests to a WBEM
    server.    

    The options shown above that can also be specified on any of the
    (sub-)commands.
    """
    # TODO add for noverify, etc.
    if ctx.obj is None:
        # We are in command mode or are processing the command line options in
        # interactive mode.
        # We apply the documented option defaults.
        if output_format is None:
            output_format = DEFAULT_OUTPUT_FORMAT
        if default_namespace is None:
            default_namespace = DEFAULT_NAMESPACE
        # TODO force noverify for now.
        noverify = True
    else:
        # Processing an interactive command.
        # Apply the option defaults from the command line options.
        if server is None:
            server = ctx.obj.server            
        if default_namespace is None:
            default_namespace = ctx.obj.default_namespace
        if user is None:
            user = ctx.obj.user
        if password is None:
            password = ctx.obj.password
        if timeout is None:
            timeout = ctx.obj.timeout
        if output_format is None:
            output_format = ctx.obj.output_format
        if conn is None:
            conn = ctx.obj.conn
        if wbem_server is None:
            wbem_server = ctx.obj.wbem_server


    # Create a command context for each command: An interactive command has
    # its own command context different from the command context for the
    # command line.
    ctx.obj = Context(ctx, server, default_namespace, user, password, timeout,
                      noverify, certfile, keyfile, output_format, verbose, conn,
                      wbem_server)

    # Invoke default command
    if ctx.invoked_subcommand is None:
        repl(ctx)


class Context(object):
    """
        Manage the click context object
    """

    def __init__(self, ctx, server, default_namespace, user, password, timeout,
                 noverify, certfile, keyfile, output_format, verbose, conn,
                 wbem_server):
        self._server = server
        self._default_namespace = default_namespace
        self._user = user
        self._password = password
        self._timeout = timeout
        self._noverify = noverify
        self._certfile = certfile
        self._keyfile = keyfile
        self._output_format = output_format
        self._verbose = verbose
        self._conn = conn
        self._wbem_server = wbem_server
        # self._spinner = click_spinner.Spinner()

    @property
    def server(self):
        """
        :term:`string`: Hostname or IP address of the HMC.
        """
        return self._server

    @property
    def user(self):
        """
        :term:`string`: Userid on the HMC.
        """
        return self._user

    @property
    def output_format(self):
        """
        :term:`string`: Output format to be used.
        """
        return self._output_format

    @property
    def default_namespace(self):
        """
        bool: Namespace to be used as default  or requests.
        """
        return self._default_namespace

    @property
    def timeout(self):
        """
        bool: Namespace to be used for requests.
        """
        return self._timeout

    @property
    def conn(self):
        """
        bool: WBEMConnection to be used for requests.
        """
        return self._conn
    @property
    def wbem_server(self):
        """
        bool: WBEMServer to be used for requests.
        """
        return self._wbem_server

    @property
    def password(self):
        """
        :term:`string`: password to be used instead of logging on, or `None`.
        """
        return self._password

    # @property
    # def spinner(self):
    #    """
    #    :class:`~click_spinner.Spinner` object.
    #    """
    #    return self._spinner

    def execute_cmd(self, cmd):
        """
        Call the cmd executor defined by cmd with the spinner
        """
        if self._conn is None:
            if self._server is None:
                raise click.ClickException("No WBEM Server defined")
            # TODO expand this
            self._conn = remote_connection(self.server, self.default_namespace,
                                            user=None,
                                            password=None)
            self._wbem_server = WBEMServer(self.conn)
        # self.spinner.start()
        try:
            cmd()
        finally:
            # self.spinner.stop()
            pass

    @property
    def verbose(self):
        """
        :class:`~click_spinner.Spinner` object.
        """
        return self._verbose
