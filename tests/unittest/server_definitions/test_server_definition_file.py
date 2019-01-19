"""
Unit test for server_definition_file.py
"""

from __future__ import absolute_import, print_function

import os
import six
import pytest
from testfixtures import TempDirectory

from ..utils.pytest_extensions import simplified_test_function
from tests.end2endtest.utils.server_definition_file import ServerDefinition, \
    ServerDefinitionFile, ServerDefinitionFileError


TESTCASES_SERVER_DEFINITION_INIT = [

    # Testcases for ServerDefinition.__init__()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * init_args: Tuple of positional arguments to ServerDefinition().
    #   * init_kwargs: Dict of keyword arguments to ServerDefinition().
    #   * exp_attrs: Dict with expected ServerDefinition attributes.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Basic parameter checking
    (
        "Order of positional parameters",
        dict(
            init_args=(
                'myserver',
                {
                    'description': 'mydesc',
                    'url': 'https://myserver',
                    'user': 'myuser',
                    'password': 'mypassword',
                    'cert_file': 'mycertfile',
                    'key_file': 'mykeyfile',
                    'ca_certs': 'mycacerts',
                    'no_verification': 'myveri',
                },
            ),
            init_kwargs=dict(),
            exp_attrs={
                'nickname': 'myserver',
                'description': 'mydesc',
                'url': 'https://myserver',
                'user': 'myuser',
                'password': 'mypassword',
                'cert_file': 'mycertfile',
                'key_file': 'mykeyfile',
                'ca_certs': 'mycacerts',
                'no_verification': 'myveri',
            },
        ),
        None, None, True
    ),
    (
        "Names of keyword arguments",
        dict(
            init_args=(),
            init_kwargs=dict(
                nickname='myserver',
                server_dict={
                    'description': 'mydesc',
                    'url': 'https://myserver',
                    'user': 'myuser',
                    'password': 'mypassword',
                    'cert_file': 'mycertfile',
                    'key_file': 'mykeyfile',
                    'ca_certs': 'mycacerts',
                    'no_verification': 'myveri',
                },

            ),
            exp_attrs={
                'nickname': 'myserver',
                'description': 'mydesc',
                'url': 'https://myserver',
                'user': 'myuser',
                'password': 'mypassword',
                'cert_file': 'mycertfile',
                'key_file': 'mykeyfile',
                'ca_certs': 'mycacerts',
                'no_verification': 'myveri',
            },
        ),
        None, None, True
    ),

    # Omitted init parameters
    (
        "Omitted optional parameter: description",
        dict(
            init_args=(),
            init_kwargs=dict(
                nickname='myserver',
                server_dict={
                    'url': 'https://myserver',
                    'user': 'myuser',
                    'password': 'mypassword',
                    'cert_file': 'mycertfile',
                    'key_file': 'mykeyfile',
                    'ca_certs': 'mycacerts',
                    'no_verification': 'myveri',
                },

            ),
            exp_attrs={
                'nickname': 'myserver',
                'description': '',
                'url': 'https://myserver',
                'user': 'myuser',
                'password': 'mypassword',
                'cert_file': 'mycertfile',
                'key_file': 'mykeyfile',
                'ca_certs': 'mycacerts',
                'no_verification': 'myveri',
            },
        ),
        None, None, True
    ),
    (
        "Missing required parameter: url",
        dict(
            init_args=(),
            init_kwargs=dict(
                nickname='myserver',
                server_dict={
                    'description': 'mydesc',
                    'user': 'myuser',
                    'password': 'mypassword',
                    'cert_file': 'mycertfile',
                    'key_file': 'mykeyfile',
                    'ca_certs': 'mycacerts',
                    'no_verification': 'myveri',
                },
            ),
            exp_attrs=None,
        ),
        ServerDefinitionFileError, None, True
    ),
    (
        "Missing required parameter: user",
        dict(
            init_args=(),
            init_kwargs=dict(
                nickname='myserver',
                server_dict={
                    'description': 'mydesc',
                    'url': 'https://myserver',
                    'password': 'mypassword',
                    'cert_file': 'mycertfile',
                    'key_file': 'mykeyfile',
                    'ca_certs': 'mycacerts',
                    'no_verification': 'myveri',
                },
            ),
            exp_attrs=None,
        ),
        ServerDefinitionFileError, None, True
    ),
    (
        "Missing required parameter: password",
        dict(
            init_args=(),
            init_kwargs=dict(
                nickname='myserver',
                server_dict={
                    'description': 'mydesc',
                    'url': 'https://myserver',
                    'user': 'myuser',
                    'cert_file': 'mycertfile',
                    'key_file': 'mykeyfile',
                    'ca_certs': 'mycacerts',
                    'no_verification': 'myveri',
                },
            ),
            exp_attrs=None,
        ),
        ServerDefinitionFileError, None, True
    ),
    (
        "Omitted optional parms: cert_file, key_file, ca_certs, no_verif.",
        dict(
            init_args=(),
            init_kwargs=dict(
                nickname='myserver',
                server_dict={
                    'description': 'mydesc',
                    'url': 'https://myserver',
                    'user': 'myuser',
                    'password': 'mypassword',
                },

            ),
            exp_attrs={
                'nickname': 'myserver',
                'description': 'mydesc',
                'url': 'https://myserver',
                'user': 'myuser',
                'password': 'mypassword',
                'cert_file': None,
                'key_file': None,
                'ca_certs': None,
                'no_verification': True,
            },
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_SERVER_DEFINITION_INIT)
@simplified_test_function
def test_ServerDefinition_init(testcase, init_args, init_kwargs, exp_attrs):
    """
    Test function for ServerDefinition.__init__()
    """

    # The code to be tested
    act_obj = ServerDefinition(*init_args, **init_kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    for attr_name in exp_attrs:
        exp_attr_value = exp_attrs[attr_name]
        assert hasattr(act_obj, attr_name), \
            "Missing attribute {0!r} in returned ServerDefinition object". \
            format(attr_name)
        act_attr_value = getattr(act_obj, attr_name)
        assert act_attr_value == exp_attr_value, \
            "Unexpected value for attribute {0!r}: Expected {1!r}, got {2!r}".\
            format(attr_name, exp_attr_value, act_attr_value)


TESTCASES_SERVER_DEFINITION_FILE_INIT = [

    # Testcases for ServerDefinitionFile.__init__()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * sd_file_data: Content of server definition file whose path is passed
    #     to ServerDefinitionFile().
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Basic syntax and semantic checking
    (
        "Invalid YAML syntax: Mixing list and dict",
        dict(
            sd_file_data="servers:\n"
                         " - foo\n"
                         " bar:\n",
        ),
        ServerDefinitionFileError, None, True
    ),
    (
        "Empty file",
        dict(
            sd_file_data="",
        ),
        ServerDefinitionFileError, None, True
    ),
    (
        "Top level entity is not a dict",
        dict(
            sd_file_data="servers:\n"
                         " - foo\n"
                         " bar:\n",
        ),
        ServerDefinitionFileError, None, True
    ),
    (
        "'servers' item with incorrect type list",
        dict(
            sd_file_data="- servers: {}\n"
                         "- server_groups: {}\n",
        ),
        ServerDefinitionFileError, None, True
    ),
    (
        "Missing 'servers' item",
        dict(
            sd_file_data="server_groups: {}\n",
        ),
        ServerDefinitionFileError, None, True
    ),
    (
        "'servers' item with incorrect type string",
        dict(
            sd_file_data="servers: bla\n"
                         "server_groups: {}\n",
        ),
        ServerDefinitionFileError, None, True
    ),
    (
        "'server_groups' item with incorrect type list",
        dict(
            sd_file_data="servers: {}\n"
                         "server_groups: []\n",
        ),
        ServerDefinitionFileError, None, True
    ),
    (
        "'server_groups' item with incorrect type string",
        dict(
            sd_file_data="servers: {}\n"
                         "server_groups: bla\n",
        ),
        ServerDefinitionFileError, None, True
    ),
    (
        "Server group grp1 with incorrect type string",
        dict(
            sd_file_data="servers:\n"
                         "  srv1:\n"
                         "    url: https://srv1\n"
                         "    user: USER\n"
                         "    password: PASSWORD\n"
                         "server_groups:\n"
                         "  grp1: srv1\n",
        ),
        ServerDefinitionFileError, None, True
    ),
    (
        "Server group grp1 with incorrect type dict",
        dict(
            sd_file_data="servers:\n"
                         "  srv1:\n"
                         "    url: https://srv1\n"
                         "    user: USER\n"
                         "    password: PASSWORD\n"
                         "server_groups:\n"
                         "  grp1:\n"
                         "    srv1: {}\n",
        ),
        ServerDefinitionFileError, None, True
    ),
    (
        "Server group grp1 with one item that has incorrect type dict",
        dict(
            sd_file_data="servers:\n"
                         "  srv1:\n"
                         "    url: https://srv1\n"
                         "    user: USER\n"
                         "    password: PASSWORD\n"
                         "server_groups:\n"
                         "  grp1:\n"
                         "    - srv1:\n",
        ),
        ServerDefinitionFileError, None, True
    ),
    (
        "Server group grp1 with one item that has incorrect type list",
        dict(
            sd_file_data="servers:\n"
                         "  srv1:\n"
                         "    url: https://srv1\n"
                         "    user: USER\n"
                         "    password: PASSWORD\n"
                         "server_groups:\n"
                         "  grp1:\n"
                         "    - []\n",
        ),
        ServerDefinitionFileError, None, True
    ),

    # More semantic errors
    (
        "Server group grp1 with one item srv1 but no servers",
        dict(
            sd_file_data="servers: {}\n"
                         "server_groups:\n"
                         "  grp1:\n"
                         "    - srv1\n",
        ),
        ServerDefinitionFileError, None, True
    ),
    (
        "Server group grp1 with one item srv12 but only server srv1",
        dict(
            sd_file_data="servers: {}\n"
                         "  srv1:\n"
                         "    url: https://srv1\n"
                         "    user: USER\n"
                         "    password: PASSWORD\n"
                         "server_groups:\n"
                         "  grp1:\n"
                         "    - srv12\n",
        ),
        ServerDefinitionFileError, None, True
    ),
    (
        "Server group grp1 with one item srv1 but only server srv12",
        dict(
            sd_file_data="servers: {}\n"
                         "  srv12:\n"
                         "    url: https://srv1\n"
                         "    user: USER\n"
                         "    password: PASSWORD\n"
                         "server_groups:\n"
                         "  grp1:\n"
                         "    - srv1\n",
        ),
        ServerDefinitionFileError, None, True
    ),

    # Valid but trivial server definition files
    (
        "Valid file with no servers and no server groups",
        dict(
            sd_file_data="servers: {}\n"
                         "server_groups: {}\n",
        ),
        None, None, True
    ),
    (
        "Valid file with no servers omitted 'server_groups' item",
        dict(
            sd_file_data="servers: {}\n",
        ),
        None, None, True
    ),

]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_SERVER_DEFINITION_FILE_INIT)
@simplified_test_function
def test_ServerDefinitionFile_init(
        testcase, sd_file_data):
    """
    Test function for ServerDefinitionFile.__init__()
    """

    with TempDirectory() as tmp_dir:

        # Create the server definition file
        fd_filename = 'tmp_server_definition_file.yml'
        sd_filepath = os.path.join(tmp_dir.path, fd_filename)
        if isinstance(sd_file_data, six.text_type):
            sd_file_data = sd_file_data.encode('utf-8')
        tmp_dir.write(fd_filename, sd_file_data)

        # The code to be tested
        ServerDefinitionFile(filepath=sd_filepath)


TESTCASES_SERVER_DEFINITION_FILE_LIST_SERVERS = [

    # Testcases for ServerDefinitionFile.list_servers()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * sd_file_data: Content of server definition file whose path is passed
    #     to ServerDefinitionFile().
    #   * list_nickname: Nickname of server or server group for list_servers()
    #   * exp_sd_nick_list: List with the nickname of the expected
    #     ServerDefinition objects returned by
    #     ServerDefinitionFile.list_servers().
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Error cases
    (
        "Listing non-existing nickname with no servers and no server groups",
        dict(
            sd_file_data="servers: {}\n"
                         "server_groups: {}\n",
            list_nickname='foo',
            exp_sd_nick_list=None,
        ),
        ValueError, None, True
    ),

    # Valid cases
    (
        "Listing single server",
        dict(
            sd_file_data="servers:\n"
                         "  srv1:\n"
                         "    url: https://srv1\n"
                         "    user: USER\n"
                         "    password: PASSWORD\n"
                         "  srv2:\n"
                         "    url: https://srv2\n"
                         "    user: USER\n"
                         "    password: PASSWORD\n"
                         "server_groups:\n"
                         "  grp1:\n"
                         "    - srv1\n"
                         "    - srv2\n",
            list_nickname='srv1',
            exp_sd_nick_list=['srv1'],
        ),
        None, None, True
    ),
    (
        "Listing group with two servers",
        dict(
            sd_file_data="servers:\n"
                         "  srv1:\n"
                         "    url: https://srv1\n"
                         "    user: USER\n"
                         "    password: PASSWORD\n"
                         "  srv2:\n"
                         "    url: https://srv2\n"
                         "    user: USER\n"
                         "    password: PASSWORD\n"
                         "server_groups:\n"
                         "  grp1:\n"
                         "    - srv1\n"
                         "    - srv2\n",
            list_nickname='grp1',
            exp_sd_nick_list=['srv1', 'srv2'],
        ),
        None, None, True
    ),
    (
        "Listing nested group (no duplicates)",
        dict(
            sd_file_data="servers:\n"
                         "  srv1:\n"
                         "    url: https://srv1\n"
                         "    user: USER\n"
                         "    password: PASSWORD\n"
                         "  srv2:\n"
                         "    url: https://srv2\n"
                         "    user: USER\n"
                         "    password: PASSWORD\n"
                         "  srv3:\n"
                         "    url: https://srv3\n"
                         "    user: USER\n"
                         "    password: PASSWORD\n"
                         "server_groups:\n"
                         "  grp1:\n"
                         "    - srv1\n"
                         "    - srv2\n"
                         "  grp2:\n"
                         "    - grp1\n"
                         "    - srv3\n",
            list_nickname='grp2',
            exp_sd_nick_list=['srv1', 'srv2', 'srv3'],
        ),
        None, None, True
    ),
    (
        "Listing nested group with forward ref (no duplicates)",
        dict(
            sd_file_data="servers:\n"
                         "  srv1:\n"
                         "    url: https://srv1\n"
                         "    user: USER\n"
                         "    password: PASSWORD\n"
                         "  srv2:\n"
                         "    url: https://srv2\n"
                         "    user: USER\n"
                         "    password: PASSWORD\n"
                         "  srv3:\n"
                         "    url: https://srv3\n"
                         "    user: USER\n"
                         "    password: PASSWORD\n"
                         "server_groups:\n"
                         "  grp2:\n"
                         "    - grp1\n"
                         "    - srv3\n"
                         "  grp1:\n"
                         "    - srv1\n"
                         "    - srv2\n",
            list_nickname='grp2',
            exp_sd_nick_list=['srv1', 'srv2', 'srv3'],
        ),
        None, None, True
    ),
    (
        "Listing nested group with duplicates in same group",
        dict(
            sd_file_data="servers:\n"
                         "  srv1:\n"
                         "    url: https://srv1\n"
                         "    user: USER\n"
                         "    password: PASSWORD\n"
                         "  srv2:\n"
                         "    url: https://srv2\n"
                         "    user: USER\n"
                         "    password: PASSWORD\n"
                         "  srv3:\n"
                         "    url: https://srv3\n"
                         "    user: USER\n"
                         "    password: PASSWORD\n"
                         "server_groups:\n"
                         "  grp1:\n"
                         "    - srv1\n"
                         "    - srv2\n"
                         "    - srv1\n"
                         "  grp2:\n"
                         "    - grp1\n"
                         "    - srv3\n",
            list_nickname='grp2',
            exp_sd_nick_list=['srv1', 'srv2', 'srv3'],
        ),
        None, None, True
    ),
    (
        "Listing nested group with duplicates at different levels",
        dict(
            sd_file_data="servers:\n"
                         "  srv1:\n"
                         "    url: https://srv1\n"
                         "    user: USER\n"
                         "    password: PASSWORD\n"
                         "  srv2:\n"
                         "    url: https://srv2\n"
                         "    user: USER\n"
                         "    password: PASSWORD\n"
                         "  srv3:\n"
                         "    url: https://srv3\n"
                         "    user: USER\n"
                         "    password: PASSWORD\n"
                         "server_groups:\n"
                         "  grp1:\n"
                         "    - srv1\n"
                         "    - srv2\n"
                         "  grp2:\n"
                         "    - grp1\n"
                         "    - srv1\n"
                         "    - srv3\n",
            list_nickname='grp2',
            exp_sd_nick_list=['srv1', 'srv2', 'srv3'],
        ),
        None, None, True
    ),

]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_SERVER_DEFINITION_FILE_LIST_SERVERS)
@simplified_test_function
def test_ServerDefinitionFile_list_servers(
        testcase, sd_file_data, list_nickname, exp_sd_nick_list):
    """
    Test function for ServerDefinitionFile.list_servers()
    """

    with TempDirectory() as tmp_dir:

        # Create the server definition file
        fd_filename = 'tmp_server_definition_file.yml'
        sd_filepath = os.path.join(tmp_dir.path, fd_filename)
        if isinstance(sd_file_data, six.text_type):
            sd_file_data = sd_file_data.encode('utf-8')
        tmp_dir.write(fd_filename, sd_file_data)

        try:
            sdf = ServerDefinitionFile(filepath=sd_filepath)
        except Exception as exc:
            pytest.fail(
                "Unexpected exception from ServerDefinitionFile(): {0}: {1}".
                format(exc.__class__.__name__, exc))

        # The code to be tested
        sd_list = sdf.list_servers(list_nickname)

        # Ensure that exceptions raised in the remainder of this function
        # are not mistaken as expected exceptions
        assert testcase.exp_exc_types is None

        act_list_servers_len = len(sd_list)
        assert act_list_servers_len == len(exp_sd_nick_list), \
            "Unexpected number of ServerDefinition objects returned from " \
            "list_servers(): Expected nicks {0!r}, got nicks {1!r}". \
            format(exp_sd_nick_list, [sd.nickname for sd in sd_list])

        for i, sd in enumerate(sd_list):
            exp_sd_nick = exp_sd_nick_list[i]
            assert sd.nickname == exp_sd_nick, \
                "Unexpected ServerDefinition object returned from " \
                "list_servers() at position {0}: " \
                "Expected nick {1!r}, got nick {2!r}". \
                format(i, exp_sd_nick, sd.nickname)


TESTCASES_SERVER_DEFINITION_FILE_LIST_ALL_SERVERS = [

    # Testcases for ServerDefinitionFile.list_all_servers()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * sd_file_data: Content of server definition file whose path is passed
    #     to ServerDefinitionFile().
    #   * exp_sd_nick_list: List with the nickname of the expected
    #     ServerDefinition objects returned by
    #     ServerDefinitionFile.list_all_servers().
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Error cases
    (
        "Empty servers and server groups",
        dict(
            sd_file_data="servers: {}\n"
                         "server_groups: {}\n",
            exp_sd_nick_list=[],
        ),
        None, None, True
    ),

    # Valid cases
    (
        "Two servers, no groups",
        dict(
            sd_file_data="servers:\n"
                         "  srv1:\n"
                         "    url: https://srv1\n"
                         "    user: USER\n"
                         "    password: PASSWORD\n"
                         "  srv2:\n"
                         "    url: https://srv2\n"
                         "    user: USER\n"
                         "    password: PASSWORD\n"
                         "server_groups:\n"
                         "  grp1:\n"
                         "    - srv1\n"
                         "    - srv2\n",
            exp_sd_nick_list=['srv1', 'srv2'],
        ),
        None, None, True
    ),
    (
        "Two servers, two groups",
        dict(
            sd_file_data="servers:\n"
                         "  srv1:\n"
                         "    url: https://srv1\n"
                         "    user: USER\n"
                         "    password: PASSWORD\n"
                         "  srv2:\n"
                         "    url: https://srv2\n"
                         "    user: USER\n"
                         "    password: PASSWORD\n"
                         "server_groups:\n"
                         "  grp1:\n"
                         "    - srv1\n"
                         "    - srv2\n"
                         "  grp2:\n"
                         "    - srv2\n",
            exp_sd_nick_list=['srv1', 'srv2'],
        ),
        None, None, True
    ),

]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_SERVER_DEFINITION_FILE_LIST_ALL_SERVERS)
@simplified_test_function
def test_ServerDefinitionFile_list_all_servers(
        testcase, sd_file_data, exp_sd_nick_list):
    """
    Test function for ServerDefinitionFile.list_all_servers()
    """

    with TempDirectory() as tmp_dir:

        # Create the server definition file
        fd_filename = 'tmp_server_definition_file.yml'
        sd_filepath = os.path.join(tmp_dir.path, fd_filename)
        if isinstance(sd_file_data, six.text_type):
            sd_file_data = sd_file_data.encode('utf-8')
        tmp_dir.write(fd_filename, sd_file_data)

        try:
            sdf = ServerDefinitionFile(filepath=sd_filepath)
        except Exception as exc:
            pytest.fail(
                "Unexpected exception from ServerDefinitionFile(): {0}: {1}".
                format(exc.__class__.__name__, exc))

        # The code to be tested
        sd_list = sdf.list_all_servers()

        # Ensure that exceptions raised in the remainder of this function
        # are not mistaken as expected exceptions
        assert testcase.exp_exc_types is None

        act_list_servers_len = len(sd_list)
        assert act_list_servers_len == len(exp_sd_nick_list), \
            "Unexpected number of ServerDefinition objects returned from " \
            "list_all_servers(): Expected nicks {0!r}, got nicks {1!r}". \
            format(exp_sd_nick_list, [sd.nickname for sd in sd_list])

        for i, sd in enumerate(sd_list):
            exp_sd_nick = exp_sd_nick_list[i]
            assert sd.nickname == exp_sd_nick, \
                "Unexpected ServerDefinition object returned from " \
                "list_all_servers() at position {0}: " \
                "Expected nick {1!r}, got nick {2!r}". \
                format(i, exp_sd_nick, sd.nickname)
