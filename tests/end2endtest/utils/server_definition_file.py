"""
Encapsulation of WBEM server definition file defining WBEM servers for pywbem
end2end tests.
"""

from __future__ import absolute_import

import os
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
import errno
import yaml
import yamlordereddictloader

SDF_DIR = os.path.join('tests', 'server_definitions')

DEFAULT_SERVER_FILE = os.path.join(SDF_DIR, 'server_definition_file.yml')
EXAMPLE_SERVER_FILE = os.path.join(SDF_DIR,
                                   'example_server_definition_file.yml')


class ServerDefinitionFileError(Exception):
    """
    An error in the WBEM server definition file.
    """
    pass


class ServerDefinitionFile(object):
    """
    Encapsulation of the WBEM server definition file.
    """

    def __init__(self, filepath=DEFAULT_SERVER_FILE):
        self._filepath = filepath
        self._servers = OrderedDict()
        self._server_groups = OrderedDict()
        self._load_file()

    def _load_file(self):
        """Load the yaml file."""
        try:
            with open(self._filepath) as fp:
                try:
                    data = yaml.load(fp, Loader=yamlordereddictloader.Loader)
                except (yaml.parser.ParserError,
                        yaml.scanner.ScannerError) as exc:
                    raise ServerDefinitionFileError(
                        "Invalid YAML syntax in WBEM server definition file "
                        "{0!r}: {1} {2}".
                        format(self._filepath, exc.__class__.__name__,
                               exc))
        except IOError as exc:
            if exc.errno == errno.ENOENT:  # pylint: disable=no-else-raise
                raise ServerDefinitionFileError(
                    "The WBEM server definition file {0!r} was not found; "
                    "copy it from {1!r}".
                    format(self._filepath, EXAMPLE_SERVER_FILE))
            else:
                raise
        else:
            if data is None:
                raise ServerDefinitionFileError(
                    "The WBEM server definition file {0!r} is empty".
                    format(self._filepath))
            if not isinstance(data, OrderedDict):
                raise ServerDefinitionFileError(
                    "The WBEM server definition file {0!r} must contain a "
                    "dictionary at the top level, but contains {1}".
                    format(self._filepath, type(data)))

            if 'servers' not in data:
                raise ServerDefinitionFileError(
                    "The WBEM server definition file {0!r} does not define a "
                    "'servers' item, but items: {1}".
                    format(self._filepath, data.keys()))
            servers = data.get('servers')
            if not isinstance(servers, OrderedDict):
                raise ServerDefinitionFileError(
                    "'servers' in WBEM server definition file {0!r} "
                    "must be a dictionary, but is a {1}".
                    format(self._filepath, type(servers)))
            self._servers.update(servers)

            server_groups = data.get('server_groups', OrderedDict())
            if not isinstance(server_groups, OrderedDict):
                raise ServerDefinitionFileError(
                    "'server_groups' in WBEM server definition file {0!r} "
                    "must be a dictionary, but is a {1}".
                    format(self._filepath, type(server_groups)))
            for sg_nick in server_groups:
                visited_sg_nicks = list()
                self._check_sg(sg_nick, server_groups, servers,
                               visited_sg_nicks)
            self._server_groups.update(server_groups)

    def _check_sg(self, sg_nick, server_groups, servers, visited_sg_nicks):
        """Check server groups for nicknames"""
        visited_sg_nicks.append(sg_nick)
        server_group = server_groups[sg_nick]
        if not isinstance(server_group, list):
            raise ServerDefinitionFileError(
                "Server group {0!r} in WBEM server definition file {1!r} "
                "must be a list, but is a {2}".
                format(sg_nick, self._filepath, type(server_group)))
        for nick in server_group:
            if nick in visited_sg_nicks:
                raise ServerDefinitionFileError(
                    "Circular reference: Server group {0!r} in WBEM server "
                    "definition file {1!r} contains server group {2!r}, which "
                    "directly or indirectly contains server group {0!r}".
                    format(sg_nick, self._filepath, nick))
            if not isinstance(nick, str):
                raise ServerDefinitionFileError(
                    "Item {0!r} in server group {1!r} in WBEM server "
                    "definition file {2!r} must be a string, but is a {3}".
                    format(nick, sg_nick, self._filepath, type(nick)))
            if nick in server_groups:
                self._check_sg(nick, server_groups, servers, visited_sg_nicks)
            elif nick not in servers:
                raise ServerDefinitionFileError(
                    "Item {0!r} in server group {1!r} in WBEM server "
                    "definition file {2!r} is not a known server or server "
                    "group".
                    format(nick, sg_nick, self._filepath))

    @property
    def filename(self):
        """
        Path name of the WBEM server definition file.
        """
        return self._filepath

    def get_server(self, nickname):
        """
        Return a `ServerDefinition` object for the server with the specified
        nickname.
        """
        try:
            server_dict = self._servers[nickname]
        except KeyError:
            raise ValueError(
                "Server with nickname {0!r} not found in WBEM server "
                "definition file {1!r}".
                format(nickname, self._filepath))
        return ServerDefinition(nickname, server_dict)

    def list_servers(self, nickname):
        """
        Return a list of `ServerDefinition` objects for the servers in the
        server group with the specified nickname, or the single server with
        the specified nickname.
        """
        if nickname in self._servers:
            return [self.get_server(nickname)]

        if nickname in self._server_groups:  # pylint: disable no-else-return
            sd_list = list()  # of ServerDefinition objects
            sd_nick_list = list()  # of server nicknames
            for item_nick in self._server_groups[nickname]:
                for sd in self.list_servers(item_nick):
                    if sd.nickname not in sd_nick_list:
                        sd_list.append(sd)
                        sd_nick_list.append(sd.nickname)
            return sd_list
        else:
            raise ValueError(
                "Server group or server with nickname {0!r} not found in WBEM "
                "server definition file {1!r}".
                format(nickname, self._filepath))

    def list_all_servers(self):
        """
        Return a list of all servers in the WBEM server definition file.
        """
        return [self.get_server(nickname) for nickname in self._servers]


class ServerDefinition(object):
    """
    Encapsulation of a WBEM server definition (e.g. from a WBEM server
    definition file).
    """

    def __init__(self, nickname, server_dict):
        self._nickname = nickname
        self._description = server_dict.get('description', '')
        self._url = self._required_attr(server_dict, 'url', nickname)
        self._user = self._required_attr(server_dict, 'user', nickname)
        self._password = self._required_attr(server_dict, 'password', nickname)
        self._cert_file = server_dict.get('cert_file', None)
        self._key_file = server_dict.get('key_file', None)
        self._ca_certs = server_dict.get('ca_certs', None)
        self._no_verification = server_dict.get('no_verification', True)
        self._implementation_namespace = server_dict.get(
            'implementation_namespace', None)

    def _required_attr(self, server_dict, attr_name, nickname):
        # pylint: disable=no-self-use
        """Return the sever_dict attribute or a KeyError"""
        try:
            return server_dict[attr_name]
        except KeyError:
            raise ServerDefinitionFileError(
                "Required server attribute is missing in definition of server "
                "{0}: {1}".format(nickname, attr_name))

    def __repr__(self):
        return "ServerDefinition(" \
            "nickname={s.nickname!r}, " \
            "description={s.description!r}, " \
            "url={s.url!r}, " \
            "user={s.user!r}, " \
            "password=..., " \
            "cert_file={s.cert_file!r}, " \
            "key_file={s.key_file!r}, " \
            "ca_certs={s.ca_certs!r}, " \
            "no_verification={s.no_verification!r}) " \
            "implementation_namespace={s.implementation_namespace!r})". \
            format(s=self)

    @property
    def nickname(self):
        """
        Nickname of the WBEM server.
        """
        return self._nickname

    @property
    def description(self):
        """
        Short description of the WBEM server.
        """
        return self._description

    @property
    def url(self):
        """
        URL of the WBEM server.

        For details see url parameter of pywbem.WBEMConnections().
        """
        return self._url

    @property
    def user(self):
        """
        User for logging on to the WBEM server.
        """
        return self._user

    @property
    def password(self):
        """
        Password of that user.
        """
        return self._password

    @property
    def cert_file(self):
        """
        Path name of file containing X.509 client certificate to be presented
        to server, or `None` for not presenting a client certificate to the
        server.
        """
        return self._cert_file

    @property
    def key_file(self):
        """
        Path name of file containing X.509 private key of the client
        certificate, or `None` for not presenting a client certificate to the
        server.
        """
        return self._key_file

    @property
    def ca_certs(self):
        """
        Path name of CA certificate file or path name of directory containing
        CA certificate files to be used for verifying the returned server
        certificate, or `None` for using the pywbem default locations.
        """
        return self._ca_certs

    @property
    def no_verification(self):
        """
        Boolean controlling whether the returned server certificate is to be
        verified.
        """
        return self._no_verification

    @property
    def implementation_namespace(self):
        """
        Boolean containing the default namespace or None if no default
        namespace was defined..
        """
        return self._implementation_namespace
