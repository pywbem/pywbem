"""
Encapsulation of WBEM server definition file defining WBEM servers for pywbem
end2end tests.
"""

from __future__ import absolute_import

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
import errno
import yaml
import yamlordereddictloader

SERVER_FILE = 'server_file.yml'
SERVER_EXAMPLE_FILE = 'server_file_example.yml'


class ServerDefinitionFileError(Exception):
    """
    An error in the WBEM server definition file.
    """
    pass


class ServerDefinitionFile(object):
    """
    Encapsulation of the WBEM server definition file.
    """

    def __init__(self, filename=SERVER_FILE):
        self._filename = filename
        self._servers = OrderedDict()
        self._server_groups = OrderedDict()
        self._load_file()

    def _load_file(self):
        try:
            with open(self._filename) as fp:
                try:
                    data = yaml.load(fp, Loader=yamlordereddictloader.Loader)
                except (yaml.parser.ParserError,
                        yaml.scanner.ScannerError) as exc:
                    raise ServerDefinitionFileError(
                        "Invalid YAML syntax in WBEM server definition file "
                        "{0!r}: {1} {2}".
                        format(self._filename, exc.__class__.__name__,
                               exc))
        except IOError as exc:
            if exc.errno == errno.ENOENT:
                raise ServerDefinitionFileError(
                    "The WBEM server definition file {0!r} was not found; "
                    "copy it from {1!r}".
                    format(self._filename, SERVER_EXAMPLE_FILE))
            else:
                raise
        else:
            if data is None:
                raise ServerDefinitionFileError(
                    "The WBEM server definition file {0!r} is empty".
                    format(self._filename))
            if not isinstance(data, OrderedDict):
                raise ServerDefinitionFileError(
                    "The WBEM server definition file {0!r} must contain a "
                    "dictionary at the top level, but contains {1}".
                    format(self._filename, type(data)))
            servers = data.get('servers', None)
            if servers is None:
                raise ServerDefinitionFileError(
                    "The WBEM server definition file {0!r} does not define a "
                    "'servers' item, but items: {1}".
                    format(self._filename, data.keys()))
            if not isinstance(servers, OrderedDict):
                raise ServerDefinitionFileError(
                    "The 'servers' item in WBEM server definition file "
                    "{0!r} must be a dictionary, but is {1}".
                    format(self._filename, type(servers)))
            self._servers.update(servers)
            server_groups = data.get('server_groups', OrderedDict())
            if not isinstance(server_groups, OrderedDict):
                raise ServerDefinitionFileError(
                    "The 'server_groups' item in WBEM server definition file "
                    "{0!r} must be a dictionary, but is {1}".
                    format(self._filename, type(server_groups)))
            for sg_nick in server_groups:
                server_group = server_groups[sg_nick]
                if not isinstance(server_group, list):
                    raise ServerDefinitionFileError(
                        "Server group {0!r} in WBEM server definition file "
                        "{1!r} must be a list, but is {2}".
                        format(sg_nick, self._filename, type(server_group)))
                for srv_nick in server_group:
                    if not isinstance(srv_nick, str):
                        raise ServerDefinitionFileError(
                            "Server {0!r} in server group {1!r} in WBEM "
                            "server definition file {2!r} must be a string, "
                            "but is {3}".
                            format(srv_nick, sg_nick, self._filename,
                                   type(srv_nick)))
                    if srv_nick not in self._servers:
                        raise ServerDefinitionFileError(
                            "Server group {0!r} in WBEM server definition "
                            "file {1!r} references an unknown server {2!r}".
                            format(sg_nick, self._filename, srv_nick))
            self._server_groups.update(server_groups)

    @property
    def filename(self):
        """
        Path name of the WBEM server definition file.
        """
        return self._filename

    def get_server(self, nickname):
        """
        Return a `ServerDefinition` object for the server with the specified
        nickname.
        """
        try:
            server_dict = self._servers[nickname]
        except KeyError:
            raise ValueError(
                "Server nickname {0!r} not found in WBEM server definition "
                "file {1!r}".
                format(nickname, self._filename))
        return ServerDefinition(nickname, server_dict)

    def iter_servers(self, nickname):
        """
        Iterate through the servers of the server group with the specified
        nickname, or the single server with the specified nickname, and yield
        a `ServerDefinition` object for each server.
        """
        if nickname in self._servers:
            yield self.get_server(nickname)
        elif nickname in self._server_groups:
            for srv_nickname in self._server_groups[nickname]:
                # The server definition file parsing has already ensured that
                # the group only specifies existing server nicknames.
                yield self.get_server(srv_nickname)
        else:
            raise ValueError(
                "Server group or server nickname {0!r} not found in WBEM "
                "server definition file {1!r}".
                format(nickname, self._filename))


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

    def _required_attr(self, server_dict, attr_name, nickname):
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
            "no_verification={s.no_verification!r})". \
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
