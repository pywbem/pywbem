#!/usr/bin/env python
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
This is a script that executes a number of tests on servers defined in
a file of servers to test the characteristics of the servers themselves
and the pybem algorithms for the get_central_instances() method. It
gets the servers for which tests are to be executed from a file, allows the
user to select particular servers, and then executes all of the defined tests
and display methods or just those selected on the command line.

Output is sent to stdout.

It is not publically supported but to be used as apywbem project internal test
tool.

NOTE: Since this is a development support tool, in includes an import that
is not part of the pywbem install imports (tabulate).  This package must
be manually  imported for this script to execute correctly
"""
from __future__ import absolute_import, print_function

import sys
import os
import argparse as _argparse
from collections import namedtuple
from collections import defaultdict
import textwrap
import threading
import datetime
import traceback
import yaml
from operator import itemgetter
try:
    import tabulate
except ImportError as ie:
    raise ImportError('tabulate is not part of pywbem install and must be '
                      'manually installed: %s' % ie)
import six

import pywbem
from pywbem._nocasedict import NocaseDict
from pywbem._cliutils import SmartFormatter as _SmartFormatter
from pywbem import __version__

from tests.end2endtest.utils.server_definition_file import \
    ServerDefinitionFile

VERBOSE = False
TABLE_FORMAT = 'simple'

SERVER_FILE = 'server_file.yml'
SERVER_EXAMPLE_FILE = 'server_file_example.yml'

SCRIPT_DIR = os.path.dirname(__file__)

# Named tuple to define Central Class, Scoping Class, ScopingPath.
ProfileDef = namedtuple('ProfileDef', ['central_class', 'scoping_class',
                                       'scoping_path', 'type',
                                       'comments'])

# TODO: Most of these varaiables should be within the main and test servers
# methods
# if not empty this is a list of profiles found in the test but not in the
# all_profiles_dict or where the definitions are incomplete in the
# all_profiles_dict
PROFILES_WITH_NO_DEFINITIONS = defaultdict(list)

SERVERS_FOR_PROFILE = defaultdict(list)

# summary info on profiles, etc. for each server. A row is added for each
# server tested.
GET_CENTRAL_INST_ROWS = []

# results dictionary for Central instance error.
GET_CENTRAL_INST_ERRS = {}

# Global set of rows to create a table of the assoc property  counts for all
# servers.
ASSOC_PROPERTY_COUNTS = []

# Results of the direction test for each server.  This dictionary has
# server name as key and the string defining the direction for CIM_Referenced
# profile as the value for each server tested.
SVR_DIRECTION = {}

# results from the fast test for direction.
FAST_TEST_RESULTS = []

PROD_TEST_RESULTS = []

SDF_DIR = os.path.join('tests', 'server_definitions')

DEFAULT_SERVER_FILE = os.path.join(SDF_DIR, 'server_definition_file.yml')


class _WbemcliCustomFormatter(_SmartFormatter,
                              _argparse.RawDescriptionHelpFormatter):
    """
    Define a custom Formatter to allow formatting help and epilog.

    argparse formatter specifically allows multiple inheritance for the
    formatter customization and actually recommends this in a discussion
    in one of the issues:

        https://bugs.python.org/issue13023

    Also recommended in a StackOverflow discussion:

    https://stackoverflow.com/questions/18462610/argumentparser-epilog-and-description-formatting-in-conjunction-with-argumentdef
    """
    pass


class ElapsedTimer(object):
    """
        Set up elapsed time timer. Calculates time between initiation
        and access.
    """
    def __init__(self):
        """ Initiate the object with current time"""
        self.start_time = datetime.datetime.now()

    def reset(self):
        """ Reset the start time for the timer"""
        self.start_time = datetime.datetime.now()

    def elapsed_ms(self):
        """ Get the elapsed time in milliseconds. returns floating
            point representation of elapsed time in seconds.
        """
        dt = datetime.datetime.now() - self.start_time
        return ((dt.days * 24 * 3600) + dt.seconds) * 1000  \
            + dt.microseconds / 1000.0

    def elapsed_sec(self):
        """ get the elapsed time in seconds. Returns floating
            point representation of time in seconds
        """
        return self.elapsed_ms() / 1000

    def elapsed_time(self):
        """
        Return elapsed time as min:sec:ms.  The .split separates out the
        millisecond
        """
        td = (datetime.datetime.now() - self.start_time)

        sec = td.seconds
        ms = int(td.microseconds / 1000)
        return '{:02}:{:02}.{:03}'.format(sec % 3600 // 60, sec % 60, ms)


def print_table(title, headers, rows, sort_columns=None):
    """
    Print a table of rows with headers using tabulate.

      Parameters:

        title (:term: string):
          String that will be output before the Table.

        headers (list or tuple):
          List of strings that defines the header for each row.  Each string
          in this list may be multiline by inserting EOL in the string

        rows (iterable of iterables)
            The outer iterable is the rows. The inner iterables are the colums
            for each row

        args (int or list of int that defines sort)
            Defines the cols that will be sorted. If int, it defines the column
            that will be sorted. If list of int, the sort is in sort order of
            cols in the list (i.e. minor sorts to the left, major sorts to the
            right)
    """
    if sort_columns is not None:
        if isinstance(sort_columns, int):
            rows = sorted(rows, key=itemgetter(sort_columns))
        elif isinstance(sort_columns, (list, tuple)):
            rows = sorted(rows, key=itemgetter(*sort_columns))
        else:
            assert False, "Sort_columns must be int or list/tuple of int"

    if title:
        print('\n%s:' % title)
    else:
        print('')

    print(tabulate.tabulate(rows, headers, tablefmt='simple'))
    print('')


def fold_list(input_list, max_width=None):
    """
    Fold the entries in input_list. If max_width is not None, fold only if it
    is longer than max_width. Otherwise fold each entry.
    """
    if not input_list:
        return ""
    if not isinstance(input_list[0], six.string_types):
        input_list = [str(item) for item in input_list]

    if max_width:
        mystr = ", ".join(input_list)
        return fold_string(mystr, max_width)

    return "\n".join(input_list)


def fold_string(input_string, max_width):
    """
    Fold a string within a maximum width.

      Parameters:

        input_string:
          The string of data to go into the cell
        max_width:
          Maximum width of cell.  Data is folded into multiple lines to
          fit into this width.

      Return:
          String representing the folded string
    """
    new_string = input_string
    if isinstance(input_string, six.string_types):
        if max_width < len(input_string):
            # use textwrap to fold the string
            new_string = textwrap.fill(input_string, max_width)

    return new_string


def get_profile_name(org_vm, profile_inst):
    """
    Get the org, name, and version from the profile instance and
    return them as a tuple.
    Returns: tuple of org, name, vers

    Raises:
      TypeError: if invalid property type
      ValueError: If property value outside range
    """
    try:
        org = org_vm.tovalues(profile_inst['RegisteredOrganization'])
        name = profile_inst['RegisteredName']
        vers = profile_inst['RegisteredVersion']
        return org, name, vers

    except TypeError as te:
        print('ORG_VM.TOVALUES FAILED. inst=%s, Exception %s' %
              (profile_inst, te))
    except ValueError as ve:
        print('ORG_VM.TOVALUES FAILED. inst=%s, Exception %s' %
              (profile_inst, ve))
    return 'ERR', 'ERR', 'ERR'


def profile_name(org_vm, profile_inst, short=False):
    """
    Return Org, Profile, Version as a string from the properties in the
    profile instance.  The returned form is the form Org:Name:Version or
    Org:Name if the optional argument short is TRUE
    """
    try:
        name_tuple = get_profile_name(org_vm, profile_inst)
    except Exception as ex:  # pylint: disable=broad-except
        print('GET_FULL_PROFILE_NAME exception %sm tuple=%r inst=%s' %
              (ex, name_tuple, profile_inst))
        return("UNKNOWN")
    if short:
        return "%s:%s" % (name_tuple[0], name_tuple[1])

    return "%s:%s:%s" % (name_tuple[0], name_tuple[1], name_tuple[2])


def path_wo_ns(obj):
    """
    Return path of an instance or instance path without host or namespace.
    Creates copy of the object so the original is not changed.
    """
    if isinstance(obj, pywbem.CIMInstance):
        path = obj.path.copy()
    elif isinstance(obj, pywbem.CIMInstanceName):
        path = obj.copy()
    else:
        assert False

    path.host = None
    path.namespace = None
    return path


class ServerDefinitionFile2(ServerDefinitionFile):
    """
    Encapsulation of the WBEM server definition file.
    This extends ServerDefinitionFile by using a different implementation
    of list_servers that expands the capability slightly of this method.
    """

    def __init__(self, filepath=DEFAULT_SERVER_FILE):
        super(ServerDefinitionFile2, self).__init__(filepath=filepath)

    def list_servers(self, nicknames=None):
        """
        Iterate through the servers of the server group with the specified
        nicknames, or the single server with the specified nickname, and yield
        a `ServerDefinition` object for each server.

        nicknames may be: None, string defining a nickname or list of nicknames
        """
        if not nicknames:
            return self.list_all_servers()

        if isinstance(nicknames, six.string_types):
            nicknames = [nicknames]

        sd_list = []
        sd_nick_list = []
        for nickname in nicknames:
            if nickname in self._servers:
                sd_list.append(self.get_server(nickname))
            elif nickname in self._server_groups:
                for item_nick in self._server_groups[nickname]:
                    for sd in self.list_servers(item_nick):
                        if sd.nickname not in sd_nick_list:
                            sd_nick_list.append(sd.nickname)
                            sd_list.append(sd)
            else:
                raise ValueError(
                    "Server group or server nickname {0!r} not found in WBEM "
                    "server definition file {1!r}".
                    format(nickname, self._filepath))
        return sd_list


def connect(nickname, server_def, debug=None, timeout=10):
    """
    Connect and confirm server works by testing for a known class in
    the default namespace or if there is no default namespace defined,
    in all the possible interop namespaces.

    returns a WBEMConnection object or None if the connection fails.
    """
    url = server_def.url
    conn = pywbem.WBEMConnection(
        url,
        (server_def.user, server_def.password),
        default_namespace=server_def.implementation_namespace,
        no_verification=server_def.no_verification,
        timeout=timeout)
    if debug:
        conn.debug = True

    ns = server_def.implementation_namespace if \
        server_def.implementation_namespace \
        else 'interop'
    try:
        conn.GetQualifier('Association', namespace=ns)
        return conn
    except pywbem.ConnectionError as exc:
        print("Test server {0} at {1!r} cannot be reached. {2}: {3}".
              format(nickname, url, exc.__class__.__name__, exc))
        return None
    except pywbem.AuthError as exc:
        print("Test server {0} at {1!r} cannot be authenticated with. "
              "{2}: {3}". format(nickname, url,
                                 exc.__class__.__name__, exc))
        return None
    except pywbem.CIMError as ce:
        if ce.status_code == pywbem.CIM_ERR_NAMESPACE_NOT_FOUND or \
                ce.status.code == pywbem.CIM_ERR_NOT_FOUND:
            return conn
        else:
            return None
    except pywbem.Error as exc:
        print("Test server {0} at {1!r} returned exception. {2}: {3}".
              format(nickname, url, exc.__class__.__name__, exc))
    return None


RESULTS = []


def test_server(url, principal, credential, no_verification, timeout=10):
    """
    Test a single server to determine if it is alive. Connects and gets a
    single class. Returns True if the sever is alive.
    """
    try:
        conn = pywbem.WBEMConnection(url, (principal, credential),
                                     no_verification=no_verification,
                                     timeout=timeout)

        server = pywbem.WBEMServer(conn)
        server.namespaces  # pylint: disable=pointless-statement
        RESULTS.append((url, principal, credential))
    except pywbem.Error as er:
        print('URL %s failed %s' % (url, er))


# TODO possibly  activate this in the future.  It parallelizes the location
# of live servers saving test time.  The other alternative would be to
# just paralize the whole test and that might be a lot of work.
def test_live_servers(servers):
    """
    Test for live servers. gets list of all servers and returns list of
    live servers. This just weeds out the dead servers from the test. This is
    a threaded test so whole test should not take longer than a single
    timeout.

    Input is list of tuples where each tuple is url, credential,
    """
    live_servers = []
    threads_ = []

    for server in servers:
        url = server[0]
        principal = server[1]
        credential = server[1]
        no_verification = True
        timeout = 10
        process = threading.Thread(target=test_server,
                                   args=(url, principal, credential,
                                         no_verification, timeout))
        threads_.append(process)

    for process in threads_:
        process.start()

    for process in threads_:
        process.join()

    for result in RESULTS:
        servers.append(result)

    return live_servers


def overview(name, server):
    """
    Overview of the server as seen through the properties of the server
    class.
    """
    print('%s OVERVIEW' % name)
    print("  Interop namespace: %s" % server.interop_ns)
    print("  Brand: %s" % server.brand)
    print("  Version: %s" % server.version)
    print("  Namespaces: %s" % ", ".join(server.namespaces))
    print('  namespace_classname: %s' % server.namespace_classname)
    if VERBOSE:
        print('cimom_inst:\n%s' % server.cimom_inst.tomof())
        print('server__str__: %s' % server)
        print('server__repr__: %r' % server)
        try:
            insts = server.conn.EnumerateInstances('CIM_Namespace',
                                                   namespace=server.interop_ns)
            print('%s: Instances of CIM_Namespace' % name)
            for inst in insts:
                print('%r' % inst)
        except pywbem.Error as er:
            print('ERROR: %s: Enum CIM_Namespace failed %s' % (name, er))

        try:
            insts = server.conn.EnumerateInstances('__Namespace',
                                                   namespace=server.interop_ns)
            print('%s: Instances of __Namespace' % name)
            for inst in insts:
                print('%r' % inst)
        except pywbem.Error as er:
            print('ERROR: %s: Enum __Namespace failed %s' % (name, er))


def get_associated_profiles(profile_path, result_role, server):
    """
    Get the associated CIM_ReferencedProfile (i.e. the Reference) for the
    profile defined by profile_path.  This allows the ResultRolefor the
    association to be set as part of the call to either "Dependent" or
    "Antecedent".
    """
    associated_profiles = server.conn.Associators(
        ObjectName=profile_path,
        AssocClass="CIM_ReferencedProfile",
        ResultRole=result_role)
    if VERBOSE:
        print('GET_ASSICIATED_PROFILES path=%r, result_role=%s\nReturns %s' %
              (profile_path, result_role, associated_profiles))
        if server.conn.debug:
            print('LAST_REQUEST\n%s' % server.conn.last_request)
            print('LAST_REPLY\n%s' % server.conn.last_reply)
    return associated_profiles


def get_associated_profile_names(profile_path, result_role, org_vm, server,
                                 include_classnames=False):
    """
    Get the Associated profiles and return the string names (org:name:version)
    for each profile as a list.
    """
    insts = get_associated_profiles(profile_path, result_role, server)
    names = []
    for inst in insts:
        if include_classnames:
            names.append("(%s)%s" % (inst.classname,
                                     profile_name(org_vm, inst)))
        else:
            names.append(profile_name(org_vm, inst))
    return names


def get_references(profile_path, role, profile_name, server):
    """
    Get display and return the References for the path provided, ResultClass
    CIM_ReferencedProfile, and the role provided.
    """
    references_for_profile = server.conn.References(
        ObjectName=profile_path,
        ResultClass="CIM_ReferencedProfile",
        Role=role)

    if VERBOSE:
        print('References for profile=%s, path=%s, ResultClass='
              'CIM_ReferencedProfile, Role=%s' % (profile_name, profile_path,
                                                  role))
        for ref in references_for_profile:
            print('Reference for %s get_role=%s cn=%s\n   antecedent=%s\n   '
                  'dependent=%s' % (profile_name, role, ref.classname,
                                    ref['Antecedent'], ref['Dependent']))

    return references_for_profile


def show_profiles(name, server, org_vm):
    """
    Create a table of info about the profiles based on getting the
    references, etc. both in the dependent and antecedent direction.

    The resulting table is printed.
    """
    rows = []
    for profile_inst in server.profiles:
        pn = profile_name(org_vm, profile_inst)
        deps = get_associated_profile_names(
            profile_inst.path, "dependent", org_vm, server,
            include_classnames=False)
        dep_refs = get_references(profile_inst.path, "antecedent", pn, server)
        ants = get_associated_profile_names(
            profile_inst.path, "antecedent", org_vm, server,
            include_classnames=False)
        ant_refs = get_references(profile_inst.path, "dependent",
                                  profile_name, server)

        # get unique class names
        dep_ref_clns = set([ref.classname for ref in dep_refs])
        ant_ref_clns = set([ref.classname for ref in ant_refs])
        row = (pn,
               fold_list(deps),
               fold_list(list(dep_ref_clns)),
               fold_list(ants),
               fold_list(list(ant_ref_clns)))
        rows.append(row)

        # append this server to the  dict of servers for this profile
        SERVERS_FOR_PROFILE[profile_name].append(name)

    title = '%s: Advertised profiles showing Profiles associations' \
        'Dependencies are Associators, AssocClass=CIM_ReferencedProfile' \
        'This table shows the results for ' % name
    headers = ['Profile',
               'Assoc CIMReferencedProfile\nResultRole\nDependent',
               'Ref classes References\nRole=Dependent',
               'Assoc CIMReferencedProfile\nResultRole\nAntecedent',
               'Ref classesReferences\nRole=Dependent']
    print_table(title, headers, rows, sort_columns=[1, 0])


def fold_path(path, width=30):
    """
    Fold a string form of a path so that each element is on separate line
    """
    assert isinstance(path, six.string_types)
    if len(path) > width:
        path.replace(".", ".\n    ")
    return path


def count_ref_associators(nickname, server, profile_insts, org_vm):
    """
    Get dict of counts of associator returns for ResultRole == Dependent and
    ResultRole == Antecedent for profiles in list.  This method counts by
    executing repeated AssociationName calls on CIM_ReferencedProfile for each
    profile instance in profile_insts with the result Role set to Dependent and
    then Antecedent to get the count of objects returned.

    Returns a dictionary where keys are profile name and value are a tuple of
    the number of associator instances for each of the AssociatorName calls.

    NOTE: This can take a long time because it executes 2 server requests for
    each profile in profile_insts.
    """
    def get_assoc_count(server, profile_inst):
        """
        Execute Associator names with ResultRole as 'Dependent' and then as
        'Antecedent' and return the count of associations returned for each
        operation
        """
        deps = server.conn.AssociatorNames(
            ObjectName=profile_inst.path,
            AssocClass="CIM_ReferencedProfile",
            ResultRole='Dependent')

        ants = server.conn.AssociatorNames(
            ObjectName=profile_inst.path,
            AssocClass="CIM_ReferencedProfile",
            ResultRole='Antecedent')
        return (len(deps), len(ants))

    assoc_dict = {}
    for profile_inst in profile_insts:
        deps_count, ants_count = get_assoc_count(server, profile_inst)
        pn = profile_name(org_vm, profile_inst)
        assoc_dict[pn] = (deps_count, ants_count)

    title = 'Display antecedent and dependent counts for possible ' \
        'autonomous profiles using slow algorithm.\n' \
        'Displays the number of instances  returned by\n' \
        'Associators request on profile for possible autonomous profiles'
    rows = [(key, value[0], value[1]) for key, value in assoc_dict.items()]

    print_table(title, ['profile', 'Dependent\nCount', 'Antecedent\nCount'],
                rows, sort_columns=0)

    # add rows to the global list for table of
    g_rows = [(nickname, key, value[0], value[1])
              for key, value in assoc_dict.items()]
    ASSOC_PROPERTY_COUNTS.extend(g_rows)
    return assoc_dict


def determine_reference_direction_slow(nickname, server, org_vm,
                                       possible_autonomous_profiles=None):
    """
    Determine the antecedent/dependent direction for the CIM_ReferencedProfile
    class for this server by testing possible autonomous top level profiles for
    their direction. This method may be required because there is an
    issue between implementations in the usage  of the dependent and antecedent
    reference properties. Typically SNIA profiles defined them with:

        Antecedent = referenced profile = component profile
        Dependent = referencing profile = autonomous profile

    and many SMI implementations defined them with:

        Antecedent = autonomous profile
        Dependent = component (= sub) profile

    This method processes the CIM_RegisteredProfiles associatorNames
    witht ResultRole set to 'Dependent' and then to 'Antecedent'to find any
    profile returns associations for one of the ResultRole settings but not
    the other. If such an association can be found, that determines the
    implementation of the antecedent/dependent direction.


      parameters:

        server:

        org_vm:

        possible_autonomous_profiles (instances of CIM_profile):
          list of autonomous profiles that are possible.

      Returns:
        If a direction is found it returns a string defining that direction.
        'dmtf' means that is is the direction defined by dmtf. 'snia' means
        it is the direction defined by 'snia'. None means that the algorithm
        could not figure out the direction

    """
    # Get list of possible autonomous profiles or use all server profiles
    # as basis. However, extending to use all server profiles really does not
    # work because you cannot tell which are top level autonomous profiles and
    # which are component profiles with no referenced subprofiles.
    if possible_autonomous_profiles:
        prof_list = possible_autonomous_profiles
    else:
        prof_list = server.profiles

    # This function executes associator names calls for each profile and
    # captures the result in a dictionary where the key is the profile name and
    # the value is a tuple of the count of names returned for each associators
    # call both for the call with ResultRole='Dependent and
    # ResultRole='Antecedent'.
    assoc_dict = count_ref_associators(nickname, server, prof_list, org_vm)

    # find profiles with either ant or dep == 0 and the other != 0
    possible_top_profiles = []
    for key, value in assoc_dict.items():
        # Look for entries in the dictionary returned by count_ref_assoc
        # that have combination of 0 in one entry and non-zero in the other
        # i.e.
        if (not value[0] and value[1]) or (value[0] and not value[1]):
            possible_top_profiles.append((key, value))

    if not possible_top_profiles:
        raise ValueError('Name=%s;, Server:\n  %s]nwith list of possible '
                         'profiles\n  %s '
                         'could not find any possible top level autonomous '
                         'profiles.\nassoc_dict=%s' %
                         (nickname, server, prof_list, assoc_dict))

    # Test that all possibles autonomous profiles have the zero entry
    # (No associations) in the same position (dependent or antecedent). This
    # means that these are all top level autonomous profiles.
    # Note that I am not sure about autonomous profiles not being top
    # level but apparently SNIA sllows profiles that are autonomous
    # and may also component.
    zero_count_pos = None
    for key, value in possible_top_profiles:
        if not zero_count_pos:
            if not value[0]:
                zero_count_pos = 0
            elif not value[1]:
                zero_count_pos = 1
        else:
            if value[zero_count_pos]:
                SVR_DIRECTION[nickname] = "undefined"
                raise ValueError('Name: %s; Server=%s; Cannot determine '
                                 'possible CIM_ReferencedProfile direction\n'
                                 '%s', (nickname, possible_top_profiles))

    dir_type = 'dmtf' if not zero_count_pos else 'snia'
    if VERBOSE:
        print('DIR_TYPE=%s' % (dir_type))

    SVR_DIRECTION[nickname] = dir_type

    return dir_type


def fast_count_associators(server):
    """
    Create count of associators for CIM_ReferencedProfile using the
    antecedent and dependent reference properties as ResultRole for each profile
    defined in server.profiles and return a dictionary of the count. This
    code does a shortcut in executing EnumerateInstances to get
    CIM_ReferencedProfile and processing the association locally.

    Returns
      Dictionary where the keys are the profile names and the value for
      each key is a dictionary with two keys ('dep' and 'ant')
      and the value is the count of associator paths when the key value is
      used as the ResultRole

    """

    try:
        ref_insts = server.conn.EnumerateInstances("CIM_ReferencedProfile",
                                                   namespace=server.interop_ns)
        # Remove host from responses since the host causes confusion
        # with the enum of registered profile. Enums do not return host but
        # the associator properties contain host
        for ref_inst in ref_insts:
            for prop in ref_inst.values():
                prop.host = None

    except pywbem.Error as er:
        print('CIM_ReferencedProfile failed for conn=%s\nexception=%s'
              % (server, er))
        raise
    # Create dict with the following characteristics:
    #   key = associator source object path
    #   value = {'dep' : count of associations,
    #            'ant' : count of associations}
    #   where: an association is a reference property that does not have same
    #         value as the source object path but for which the source object
    #         path is the value of one of the properties
    association_dict = {}

    # We are counting too many.   Have same properties for class and subclass
    # but  appear to count that one twice. Looks like we need one more piece.
    # for each.  If association_dict[profile_key] not in some list

    for profile in server.profiles:
        profile_key = profile.path
        ant_dict = {}
        dep_dict = {}
        for ref_inst in ref_insts:
            # These dictionaries insure that there are no duplicates in
            # the result. Some servers duplicate the references in subclasses.
            if profile_key not in association_dict:
                association_dict[profile_key] = {'dep': 0, 'ant': 0}
            ant = ref_inst['antecedent']
            dep = ref_inst['dependent']
            if profile_key != ant and profile_key != dep:
                continue
            if dep != profile_key:
                if dep not in dep_dict:
                    dep_dict[dep] = True
                    association_dict[profile_key]['dep'] += 1
            if ant != profile_key:
                if ant not in ant_dict:
                    ant_dict[ant] = True
                    association_dict[profile_key]['ant'] += 1
    return association_dict


def determine_reference_direction_fast(nickname, server,
                                       possible_autonomous_profiles=None,
                                       possible_component_profiles=None):
    """
    Determine CIM_ReferenceProfile Antecedent/Dependent direction from
    server data and a list of known autonomous and/or component profiles
    using the algorithm defined for the _server. This is the prototype for
    the code that was reimplemented in pywbem.

      Parameters:
        org_vm

        possible_autonomous_profiles ()
    """

    def _determine_type(profilepaths, v0_dict, v1_dict, autonomous):
        """
        Determine type from data in the two dictionaries and the profile_list.
        Returns string defining type ('snia' or 'dmtf'). Returns None if
        the profile list is None or None of the profilepaths exist in either
        v0_dict or v1_dict
        """
        if not profilepaths:
            return None
        t = ['snia', 'dmtf']
        if not autonomous:
            t.reverse()
        dir_type = None
        v0_paths = []
        v1_paths = []
        for ppath in profilepaths:
            if ppath in v0_dict:
                v0_paths.append(ppath)
                if VERBOSE:
                    print('DETERMINED_TYPE v0 %s %s' % (ppath, t[0]))
            elif ppath in v1_dict:
                v1_paths.append(ppath)
                if VERBOSE:
                    print('DETERMINED_TYPE v1 %s %s' % (ppath, t[1]))
        if v0_paths and not v1_paths:
            dir_type = t[0]
        elif v1_paths and not v0_paths:
            dir_type = t[1]
        elif not v0_paths and not v1_paths:
            dir_type = None
        else:
            ps = 'possible %s' % ('autonomous' if autonomous else 'component')
            print('ERROR VALUERROR %s\n%s:%s\n%s: %s' % (ps, t[0], v0_paths,
                                                         t[1], v1_paths))
            raise ValueError("Cannot determine type. "
                             "determine_cimrefrence_direction shows "
                             "conflicts in %s profile list. %s; %s\n%s; %s" %
                             (ps, t[0], v0_paths, t[1], v1_paths))
        return dir_type

    if VERBOSE:
        print('POSSIBLE_AUTONOMOUS_PROFILES:\n%s' %
              possible_autonomous_profiles)
    if not possible_autonomous_profiles and not possible_component_profiles:
        raise ValueError("Either possible_autonomous_profiles or "
                         "possible_component_profiles must have a value")
    assoc_dict = fast_count_associators(server)
    # returns dictionary where key is profile name and value is dict of
    # ant: dep: with value count

    # Reduce to dictionary where ant/dep are 0 and non-zero, i.e. top and bottom
    new_dict = {}
    for key, value in assoc_dict.items():
        if (not value['dep'] and value['ant']) \
                or (value['dep'] and not value['ant']):
            new_dict[key] = (value['dep'], value['ant'])
            if not value['dep'] and not value['ant']:
                print('ERROR key %s value %s' % (key, value))

    # print('NEW_DICT %s' % new_dict)
    # create a dictionary with entry for each new_dict itme that has data in
    # one of the value items.
    v0_dict = {key: value for key, value in new_dict.items() if value[0]}
    v1_dict = {key: value for key, value in new_dict.items() if value[1]}
    if VERBOSE:
        print('V0_DICT %s' % v0_dict)
        print('V1_DICT %s' % v1_dict)
        print('POSSIBLE_AUTONOMOUS_PROFILES %s' % possible_autonomous_profiles)

    auto_dir_type = _determine_type(possible_autonomous_profiles, v0_dict,
                                    v1_dict, True)
    comp_dir_type = _determine_type(possible_component_profiles, v0_dict,
                                    v1_dict, False)

    if VERBOSE:
        print('AUTO_DIR %s %s' % (auto_dir_type, comp_dir_type))
    if auto_dir_type and comp_dir_type:
        if auto_dir_type == comp_dir_type:
            return auto_dir_type

    elif not auto_dir_type and not comp_dir_type:
        return None

    else:
        if auto_dir_type:
            return auto_dir_type
        elif comp_dir_type:
            return comp_dir_type
    if VERBOSE:
        print('RAISE VALUERR %s %s' % (auto_dir_type, comp_dir_type))
    raise ValueError('Name: %s; Cannot determine '
                     'possible CIM_ReferencedProfile direction. '
                     'Autonomous and componentTests do not match. '
                     'auto_dir_type=%s, '
                     'comp_dir_type=%s\nServer=%s; ' %
                     (nickname, auto_dir_type, comp_dir_type, server))


def show_count_associators(nickname, server, org_vm):
    """
    Display results of fast_count_associators(...)). Generates a table showing
    the results of the call. This is just a  test tool.
    """
    d_assoc = fast_count_associators(server)

    svr_profiles_dict = {prof.path: prof for prof in server.profiles}

    headers = ('profile', 'ants', 'deps')
    rows = []

    assoc_dict = {}
    for prof_key, values in d_assoc.items():
        pn = profile_name(org_vm, svr_profiles_dict[prof_key])
        assoc_dict[pn] = (values['ant'], values['dep'])

    rows = []
    title = 'Display antecedent and dependent counts for possible ' \
        'autonomous and component profiles using fast method.\nDisplays the ' \
        'number of instances returned by\nAssociators request on profile for ' \
        'possible autonomous profiles. Algorithm is to enumerate ' \
        'ReferencedProfile and count Dependents/Antecedents with target path'
    headers = ('profile', 'Dependent\nCount', 'Antecedent\nCount')
    for pn, value in assoc_dict.items():
        rows.append((pn, value[1], value[0]))

    print_table(title, headers, rows, sort_columns=[0])

    g_rows = [(nickname, key, value[0], value[1])
              for key, value in assoc_dict.items()]
    ASSOC_PROPERTY_COUNTS.extend(g_rows)


def test_get_central_instances(nickname, server, all_profiles_dict, org_vm,
                               reference_direction='dmtf'):
    """Test get central instances"""
    good_rtns = []
    error_rtns = []

    for inst in server.profiles:
        try:
            prof = profile_name(org_vm, inst, short=True)
            prof_long = profile_name(org_vm, inst)
            if prof not in all_profiles_dict:
                PROFILES_WITH_NO_DEFINITIONS[nickname] = prof
                continue

            prof_def = all_profiles_dict[prof]
            print('%s: PROFILE get_central_instances: %s inst.path=%s\n   '
                  'central_class=%s,scoping_class=%s, scoping_path=%s' %
                  (nickname, prof_long, inst.path, prof_def.central_class,
                   prof_def.scoping_class, prof_def.scoping_path))

            # If profile has ElementConformsToProfile, ignore other
            # definition parameters
            ci_paths = server.conn.AssociatorNames(
                ObjectName=inst.path,
                AssocClass="CIM_ElementConformsToProfile",
                ResultRole="ManagedElement")
            if ci_paths:
                try:
                    central_paths = server.get_central_instances(
                        inst.path,
                        central_class=prof_def.central_class,
                        scoping_class=prof_def.scoping_class,
                        scoping_path=prof_def.scoping_path,
                        reference_direction=reference_direction)
                except pywbem.Error as er:
                    print('GET_CENTRAL_INSTANCES Exception %s:%s' %
                          (er.__class__.__name__, er))
                    if server.conn.debug:
                        print('LAST_REQUEST\n%s' % server.conn.last_request)
                        print('LAST_REPLY\n%s' % server.conn.last_reply)
                    continue

                for path in central_paths:
                    path.host = None
                    path.namespace = None
                good_rtns.append((prof_long, central_paths))

            # Otherwise test only if definition complete. Note this
            # code requires the direction param
            else:
                # Test that central class and scoping class are defined. Also
                # test scoping path. If None, this is an error, unless
                # central and scoping classes are the same
                if prof_def.scoping_class and prof_def.central_class:
                    if prof_def.scoping_class.lower() == \
                            prof_def.central_class.lower() or \
                            prof_def.scoping_path:
                        try:
                            central_paths = server.get_central_instances(
                                inst.path,
                                central_class=prof_def.central_class,
                                scoping_class=prof_def.scoping_class,
                                scoping_path=prof_def.scoping_path,
                                reference_direction=reference_direction)
                        except pywbem.Error as er:
                            print('GET_CENTRAL_INSTANCES Exception %s:%s' %
                                  (er.__class__.__name__, er))
                            if server.conn.debug:
                                print('LAST_REQUEST\n%s' %
                                      server.conn.last_request)
                                print('LAST_REPLY\n%s' %
                                      server.conn.last_raw_reply)
                            continue
                        for path in central_paths:
                            path.host = None
                            path.namespace = None
                        good_rtns.append((prof_long, central_paths))
                    else:
                        print('INVALID_SCOPING_PATH %s %s %s' % (
                            prof_def.scoping_class, prof_def.central_class,
                            prof_def.scoping_path))
                        PROFILES_WITH_NO_DEFINITIONS[nickname] = prof
                else:
                    PROFILES_WITH_NO_DEFINITIONS[nickname] = prof

        except ValueError as ve:
            print("ValueError: %s: %s\n  inst_path %s\n   exception %s" %
                  (nickname, profile_name(org_vm, inst), inst.path, ve))
            if VERBOSE:
                if server.conn.debug:
                    print('LAST_REQUEST\n%s' % server.conn.last_request)
                    print('LAST_REPLY\n%s' % server.conn.last_reply)
            error_rtns.append((prof_long, ve))
        except pywbem.Error as er:
            print("pywbem.Error: %s: %s\n  inst_path=%s\n   "
                  "server=%s\n   Exception=%s"
                  % (nickname, profile_name(org_vm, inst, short=True),
                     inst.path, server, er))
            if VERBOSE:
                if server.conn.debug:
                    print('LAST_REQUEST\n%s' % server.conn.last_request)
                    print('LAST_REPLY\n%s' % server.conn.last_reply)
            error_rtns.append((prof_long, er))

    print('%s: Successful_Profiles=%s Error=%s\n' % (nickname, len(good_rtns),
                                                     len(error_rtns)))

    title = '%s: Successful returns from get_central_instances' % nickname
    headers = ['Profile', 'Rtn Paths']
    rows = []
    for data in good_rtns:
        # TODO str(p) to fold_path(str(p), 20)
        paths_str = '\n'.join([str(p) for p in data[1]])
        rows.append([data[0], paths_str])
    print_table(title, headers, rows)

    title = '%s: Error returns from get_central_instances' % nickname
    headers = ['Profile', 'Error rtn']
    rows = [[data[0], textwrap.fill(str(data[1]), 80)] for data in error_rtns]
    print_table(title, headers, rows, sort_columns=0)

    # set the data into the lists for display at end of the test
    GET_CENTRAL_INST_ERRS[nickname] = error_rtns
    GET_CENTRAL_INST_ROWS.append([nickname, len(server.profiles),
                                  len(good_rtns), len(error_rtns)])


def show_instances(server, cim_class):
    """
    Display the instances of the CIM_Class defined by cim_class. If the
    namespace is None, use the interop namespace. Search all namespaces for
    instances except for CIM_RegisteredProfile
    """
    if cim_class == 'CIM_RegisteredProfile':
        for inst in server.profiles:
            print(inst.tomof())
        return

    for ns in server.namespaces:
        try:
            insts = server.conn.EnumerateInstances(cim_class, namespace=ns)
            if len(insts):
                print('INSTANCES OF %s ns=%s' % (cim_class, ns))
                for inst in insts:
                    print(inst.tomof())
        except pywbem.Error as er:
            if er.status_code != pywbem.CIM_ERR_INVALID_CLASS:
                print('%s namespace %s Enumerate failed for conn=%s\n'
                      'exception=%s'
                      % (cim_class, ns, server, er))


def show_cimreferences(server_name, server, org_vm):
    """
    Show info about the CIM_ReferencedProfile instances.
    Goal. Clearly show what the various refs look like by using profile
    names for the antecedent and dependent rather than instances.
    """
    try:
        ref_insts = server.conn.EnumerateInstances("CIM_ReferencedProfile",
                                                   namespace=server.interop_ns)

        prof_insts = server.conn.EnumerateInstances("CIM_RegisteredProfile",
                                                    namespace=server.interop_ns)
    except pywbem.Error as er:
        print('CIM_ReferencedProfile failed for conn=%s\nexception=%s'
              % (server, er))
        raise

    # create dictionary of registered profiles with path as key
    profile_dict = NocaseDict()
    for inst in prof_insts:
        profile_dict[str(path_wo_ns(inst))] = inst

    # The output table should look like the following:
    # DEP prof name,  CIM_Ref Subclass, ANT name
    rows = []
    # TODO clean up the try blocks, etc. after we run the complete
    # set of servers.
    for inst in ref_insts:
        try:
            dep_path = inst.get('Dependent')
            ant_path = inst.get('Antecedent')
        except Exception as ex:  # pylint: disable=broad-except
            print('Exception get properties %s in %s' % (ex, inst))
            row = ["Unknown", inst.classname, "Unknown"]
            rows.append(row)
            continue

        try:
            dep = profile_dict[str(path_wo_ns(dep_path))]
        except Exception as ex:  # pylint: disable=broad-except
            print('Exception %s get from profile_dict:  '
                  'Dependent reference in ReferencedProfiles "%s" does '
                  'not match any registered profile instance.\nReference '
                  'instance:\n%s' %
                  (ex, str(path_wo_ns(dep_path)), inst.tomof()))
            row = ["Unknown", inst.classname, "Unknown"]
            rows.append(row)
            continue
        try:
            ant = profile_dict[str(path_wo_ns(ant_path))]
        except Exception as ex:  # pylint: disable=broad-except
            print('Exception get from profile_dict %s. '
                  'Antecedent reference in ReferencedProfiles "%s" does '
                  'not match any registered profile instance.\n'
                  'Reference instance:\n%s' %
                  (ex, str(path_wo_ns(ant_path)), inst.tomof()))
            row = ["Unknown", inst.classname, "Unknown"]
            rows.append(row)
            continue

        try:
            row = [profile_name(org_vm, dep),
                   inst.classname,
                   profile_name(org_vm, ant)]
        except Exception as ex:  # pylint: disable=broad-except
            print('Exception row create %s ' % ex)
            row = ["Unknown", inst.classname, "Unknown"]
        rows.append(row)

    title = '%s: Simplified table of CIM_References with ref class name ' \
            'and profile names' % server_name
    headers = ['Dependent\nProfile Name', 'CIM_Reference\nClass',
               'Antecedent\nProfile Name']
    print_table(title, headers, rows, sort_columns=1)

    # TODO: The following has become a duplicate of the above.
    # Probably drop this.
    if VERBOSE:
        rows = []
        for inst in ref_insts:
            dep_path = inst.get('Dependent')
            ant_path = inst.get('Antecedent')

            dep = profile_dict[str(dep_path)]
            ant = profile_dict[str(ant_path)]
            row = [str(path_wo_ns(dep)),
                   inst.classname,
                   str(path_wo_ns(ant))]
            rows.append(row)

        title = '%s: Table of reference insts' % server_name
        headers = ['Dependent Profile', 'Ref Class', 'Antecedent Profile']
        print_table(title, headers, rows, sort_columns=1)


def get_profiles_in_svr(nickname, server, all_profiles_dict, org_vm,
                        add_error_list=False):
    """
    Test all profiles in server.profiles to determine if profile is in
    the all_profiles_dict.

    Returns list of profiles in the profile_dict and in the defined server.
    If add_error_list is True, it also adds profiles not found to
    PROFILES_WITH_NO_DEFINITIONS.
    """
    profiles_in_dict = []
    for profile_inst in server.profiles:
        pn = profile_name(org_vm, profile_inst, short=True)
        if pn in all_profiles_dict:
            profiles_in_dict.append(profile_inst)
        else:
            if add_error_list:
                print('PROFILES_WITH_NO_DEFINITIONS svr=%s:  %s' %
                      (nickname, pn))
                PROFILES_WITH_NO_DEFINITIONS[nickname] = pn
    return profiles_in_dict


def test_reference_direction_slow(nickname, server, all_profiles_dict,
                                  org_vm):
    """
    This is the test function for determine_reference_direction. It
    Defines the set of possible autonomous profiles from profile_dict,
    calls determine_reference_direction and displays the results of
    the test.
    """
    # TODO: The following is covered by the function possible_target_profiles.
    # Use that method
    profiles_in_dict = get_profiles_in_svr(nickname, server,
                                           all_profiles_dict,
                                           org_vm)
    possible_aut_profiles = []
    for profile_inst in profiles_in_dict:
        profile_org_name = profile_name(org_vm, profile_inst, short=True)
        if all_profiles_dict[profile_org_name].type == 'autonomous':
            possible_aut_profiles.append(profile_inst)

    possible_names = [profile_name(org_vm, inst)
                      for inst in possible_aut_profiles]
    print('POSSIBLE_AUTONOMOUS_PROFILES %s: %s' % (nickname,
                                                   possible_names))

    ref_direction = None
    try:
        ref_direction = determine_reference_direction_slow(
            nickname,
            server, org_vm,
            possible_autonomous_profiles=possible_aut_profiles)
    except Exception as ex:  # pylint: disable=broad-except
        print('ERROR: determine_reference_direction failed: Exception=%s' % ex)
        return

    prop_names = ['Antecedent', 'Dependent']
    if ref_direction == 'snia':
        prop_names.reverse()
    print('%s defines CIM_ReferencedProfile using slow method as "%s":\n'
          '   %s = Referenced/Component Profile,\n'
          '   %s = Referencing/Autonomous Profile' % (nickname,
                                                      ref_direction,
                                                      prop_names[0],
                                                      prop_names[1]))

    return ref_direction


def possible_target_profiles(nickname, server, all_profiles_dict,
                             org_vm, autonomous=True, output='path'):
    """
    Get list of possible autonomous or component profiles based on the list
    of all profiles and the list of profiles in the defined server.

    Returns list of *paths or insts, or profile names depending on the value
    of the output parameter.
    """
    assert output in ['path', 'name']
    profiles_in_svr = get_profiles_in_svr(nickname, server,
                                          all_profiles_dict,
                                          org_vm)
    # list of possible autonomous profiles for testing
    possible_profiles = []

    for profile_inst in profiles_in_svr:
        profile_org_name = profile_name(org_vm, profile_inst, short=True)
        if autonomous:
            if all_profiles_dict[profile_org_name].type == 'autonomous':
                possible_profiles.append(profile_inst)
        else:
            if not all_profiles_dict[profile_org_name].type == 'component':
                possible_profiles.append(profile_inst)

    if output == 'path':
        possible_profiles = [inst.path for inst in possible_profiles]
    elif output == 'name':
        possible_profiles = [profile_name(org_vm, inst)
                             for inst in possible_profiles]

    return possible_profiles


def test_reference_direction_fast(nickname, server, all_profiles_dict,
                                  org_vm, st):
    """
    Test the reference direction using a faster algorithm. This uses an
    algorithm that attemts to test with both autonomous and component
    profiles and tries to run the test with combinations of them.

    The algorithm also only makes a single call to the server and analyzes
    the resultin instances of CIM_ReferencedProfile to determine direction.

    """
    print('TEST WITH FAST PATH ALGORITHM')
    print("POSSIBLE_TARGET_AUTONOMOUS_PROFILES=%s" %
          possible_target_profiles(nickname, server, all_profiles_dict,
                                   org_vm, autonomous=True, output='name'))

    auto_paths = possible_target_profiles(nickname, server,
                                          all_profiles_dict, org_vm,
                                          autonomous=True, output='path')
    comp_paths = possible_target_profiles(nickname, server,
                                          all_profiles_dict, org_vm,
                                          autonomous=False, output='path')

    show_count_associators(nickname, server, org_vm)
    tst_ref_direction = None
    ps = None
    try:
        dir_auto = None
        dir_comp = None
        dir_both = None
        try:
            print('CALL DETERMINE_DIR FAST for Autonomous only %s' % auto_paths)
            dir_auto = determine_reference_direction_fast(
                nickname,
                server,
                possible_autonomous_profiles=auto_paths,
                possible_component_profiles=None)
            print('AUTO SVR=%s DIR=%s' % (nickname, dir_auto))
        except Exception as ex:
            print('DETERMINE_DIR FAST FAILED exception=%s' % ex)

        print('CALL DETERMINE_DIR FAST for component only %s' %
              [str(p) for p in comp_paths])
        try:
            dir_comp = determine_reference_direction_fast(
                nickname, server,
                possible_autonomous_profiles=None,
                possible_component_profiles=comp_paths)
            print('COMP SVR=%s DIR=%s' % (nickname, dir_comp))
        except Exception as ex:
            print('DETERMINE_DIR FAST FAILED exception=%s' % ex)

        print('CALL DETERMINE_DIR FAST for both autonomous and component')
        try:
            dir_both = determine_reference_direction_fast(
                nickname,
                server,
                possible_autonomous_profiles=auto_paths,
                possible_component_profiles=comp_paths)
            print('%s: DETERMINE_DIR FAST BOTH DIR=%s' % (nickname,
                                                          dir_both))
        except Exception as ex:
            print('%s: DETERMINE_DIR FAST FAILED exception=%s' % (nickname, ex))
            return None

        if dir_auto == dir_comp == dir_both:
            ps = '%s: DETERMINE_DIR FAST PASSED  ref_direction %s' % (nickname,
                                                                      dir_auto)
            tst_ref_direction = dir_auto
        else:
            ps = '%s: DETERMINE_DIR FAST FAILED  Results inconsistent.\n' \
                 'Autonomous Only=%s ComponentOnly=%s Both=%s' % \
                 (nickname, dir_auto, dir_comp, dir_both)

        FAST_TEST_RESULTS.append((nickname, ps, st.elapsed_time()))
        return tst_ref_direction

    except Exception as ex:
        FAST_TEST_RESULTS.append((nickname, ex, st.elapsed_time()))
        return None


def test_reference_direction_prod(nickname, server, all_profiles_dict,
                                  org_vm, st):
    """
    Test the reference direction using the code in WBEMServer. This uses an
    algorithm similar to the fast_reference_direction prototype.

    The algorithm also only makes a single call to the server and analyzes
    the resultin instances of CIM_ReferencedProfile to determine direction.

    """
    print('TEST WITH PROD SERVER PATH ALGORITHM')
    auto_paths = possible_target_profiles(nickname, server,
                                          all_profiles_dict, org_vm,
                                          autonomous=True, output='path')
    comp_paths = possible_target_profiles(nickname, server,
                                          all_profiles_dict, org_vm,
                                          autonomous=False, output='path')

    # This just shows what the fast algorithm defines as the associators.

    show_count_associators(nickname, server, org_vm)

    tst_ref_direction = None
    ps = None
    dir_auto = None
    dir_comp = None
    dir_both = None
    try:
        try:
            print('CALL DETERMINE PROD for Autonomous only %s' % auto_paths)
            dir_auto = server.determine_reference_direction(
                possible_autonomous_profiles=auto_paths,
                possible_component_profiles=None)
            print('RESULT_DETERMINE_AUTOONLY=%s DIR=%s' % (nickname, dir_auto))
        except Exception as ex:
            print('DETERMINE_DIR AUTOONLY FAILED exception=%s' % ex)

        print('CALL DETERMINE PROD for component only %s' %
              [str(p) for p in comp_paths])
        try:
            dir_comp = server.determine_reference_direction(
                possible_autonomous_profiles=None,
                possible_component_profiles=comp_paths)
            print('RESULT_DETERMINE_COMPONLY=%s DIR=%s' % (nickname, dir_comp))
        except Exception as ex:
            print('DETERMINE_DIR_COMPONLY FAILED exception=%s' % ex)

        print('CALL DETERMINE PROD for both autonomous and component')
        try:
            dir_both = server.determine_reference_direction(
                possible_autonomous_profiles=auto_paths,
                possible_component_profiles=comp_paths)
            print('RESULT_DETERMINE_BOTH=%s DIR=%s' % (nickname, dir_both))
        except Exception as ex:
            print('DETERMINE_DIR_BOTH FAILED exception=%s' % ex)

        if dir_auto == dir_comp == dir_both:
            if dir_auto is None:
                ps = ('FAILED', dir_auto)
                tst_ref_direction = dir_auto
            else:
                ps = ('PASSED', dir_auto)
                tst_ref_direction = dir_auto
        else:
            ps = ('FAILED', 'Results inconsistent.\n'
                  'Autonomous Only=%s ComponentOnly=%s Both=%s' %
                  (dir_auto, dir_comp, dir_both))
            tst_ref_direction = None

        PROD_TEST_RESULTS.append([nickname, ps, st.elapsed_time()])
        print('PROD_TEST_RESULTS1 %r' % PROD_TEST_RESULTS)
        return tst_ref_direction

    except Exception as ex:
        PROD_TEST_RESULTS.append([nickname, ('FAILED', ex), st.elapsed_time()])
        return None


def show_tree(nickname, server, org_vm, reference_direction='snia'):
    """
    sShow a tree view of the registered profiles using the ECTP and
    referencedprofile associations to define the tree.  Starts with SMI-S
    if it iexists
    """
    scoping_result_role = "Dependent" if reference_direction == 'snia' \
        else "Antecedent"
    profiles = server.profiles

    reg_profiles = {}
    for profile in profiles:
        reg_profiles[profile.path.to_wbem_uri(format="canonical")] = profile

    # defines element to subelement
    tree_dict = defaultdict(list)

    for profile in profiles:
        paths = server.conn.AssociatorNames(
            profile.path,
            AssocClass='CIM_ElementConformsToProfile',
            ResultClass="CIM_RegisteredProfile",
            ResultRole="ManagedElement")
        if paths:
            print('%s: associators ELEMENTCONFORMSTO %s' %
                  (nickname, profile.path.to_wbem_uri(format="canonical")))
            for path in paths:
                print("  %s" % path)
        profile.path.host = None
        profile_path_str = profile.path.to_wbem_uri(format="canonical")
        for path in paths:
            tree_dict[profile_path_str].append(
                path.to_wbem_uri(format="canonical"))

        # Go down one level on the profile side, to the scoping profile
        referenced_profile_paths = server.conn.AssociatorNames(
            ObjectName=profile.path,
            AssocClass="CIM_ReferencedProfile",
            ResultRole=scoping_result_role)
        if referenced_profile_paths:
            print('%s AssocNames CIM_ReferencedProfile %s' %
                  (nickname, profile.path.to_wbem_uri(format="canonical")))

            for path in referenced_profile_paths:
                print("  %s" % path.to_wbem_uri(format="canonical"))

            for path in referenced_profile_paths:
                path.host = None
            tree_dict[profile_path_str].append(
                path.to_wbem_uri(format="canonical"))

    for key, values in tree_dict.items():
        print('%s\n  %s' % (key, "\n  ".join(values)))

    name_dict = {}
    for key, values in tree_dict.items():
        prof = reg_profiles[key]
        pn = profile_name(org_vm, prof)
        pvalues = []
        for value in values:
            profx = reg_profiles[value]
            pvalues.append(profile_name(org_vm, profx))
        name_dict[pn] = pvalues
    for key, values in name_dict.items():
        print('%s\n  %s' % (key, "\n  ".join(values)))


def run_server_tests(nickname, server, all_profiles_dict, st,
                     test_direction=None, tests=None):
    """
    Execute tests on the server connection defined by server with the name
    server_name
    """
    # Set up the org_vm for this RegisteredOrganization property for server.
    org_vm = pywbem.ValueMapping.for_property(
        server, server.interop_ns,
        'CIM_RegisteredProfile',
        'RegisteredOrganization')

    if not tests or 'overview' in tests:
        overview(nickname, server)

    if not tests or 'profiles' in tests:
        show_profiles(nickname, server, org_vm)

    if not tests or 'tree' in tests:
        show_tree(nickname, server, org_vm)

    # print('TIME AFTER SHOW PROFILES %s' % st.elapsed_time())

    if not tests or 'insts' in tests:
        show_instances(server, 'CIM_RegisteredProfile')
        show_instances(server, "CIM_ReferencedProfile")
        show_instances(server, "CIM_ElementConformsToProfile")

        try:
            show_cimreferences(nickname, server, org_vm)
        except Exception as ex:  # pylint: disable=broad-except
            print(traceback.format_exc())
            print("SHOW_CIMREF exception %s" % ex)

    print('TIME AFTER SHOW_CIMREFERENCES %s' % st.elapsed_time())

    # Determine profiles for this server not in all_profiles_dict and put
    # into global list for display at end of run
    try:
        get_profiles_in_svr(nickname, server, all_profiles_dict,
                            org_vm, add_error_list=True)
    except Exception as ex:
        print('Exception  in get_profiles_in_svr %s' % ex)
        raise

    print('TIME AFTER get_profiles_in_svr %s' % st.elapsed_time())

    # execute the server reference_direction tests.  This test with
    # 3 algorithms to determine if we are getting consistent results
    if not test_direction:
        stx = ElapsedTimer()
        try:
            ref_dir_slow = test_reference_direction_slow(nickname, server,
                                                         all_profiles_dict,
                                                         org_vm)
            print('TIME test_profile_direction_slow %s' % stx.elapsed_time())

        except Exception as ex:
            print('Exception  in tst_ref_direction %s' % ex)
            raise

        stx = ElapsedTimer()
        try:
            ref_dir_fast = test_reference_direction_fast(nickname, server,
                                                         all_profiles_dict,
                                                         org_vm, st)
            print('TIME test_profile_direction_fast %s' % stx.elapsed_time())

        except Exception as ex:
            print('Exception  in tst_ref_direction_fast %s' % ex)
            raise

        stx = ElapsedTimer()
        try:
            ref_dir_prod = test_reference_direction_prod(nickname, server,
                                                         all_profiles_dict,
                                                         org_vm, st)
            print('TIME test_profile_direction_prod%s' % stx.elapsed_time())

        except Exception as ex:
            print('Exception  in tst_ref_direction_fast %s' % ex)
            raise

        if ref_dir_slow == ref_dir_fast and ref_dir_fast == ref_dir_prod:
            print('Server %s: DETERMINE_DIRECTION ALGORITHMS match' %
                  nickname)
            reference_direction = ref_dir_fast
        else:
            print('Server %s: ERROR: DETERMINE_DIRECTION ALGORITHMS differ '
                  'slow=%s fast=%s prod=%s' %
                  (nickname, ref_dir_slow, ref_dir_fast, ref_dir_prod))
            reference_direction = ref_dir_fast

    else:
        reference_direction = test_direction

    if not tests or 'centralinsts' in tests:
        test_get_central_instances(nickname, server, all_profiles_dict,
                                   org_vm,
                                   reference_direction=reference_direction)
    print('TIME AFTER test_get_central_instances %s' % st.elapsed_time())


def load_profiles_definitions(filename):
    """
    Load the registered profiles defined in the file filename.  This is a
    yml file that defines the basic characteristics of each profile with the
    following variables:

    It produces a dictionary that can be accessed with the a string that
    defines the profile organization and name in the form <org>:<profile name>
    },
    """
    with open(filename, 'r') as fp:
        profile_definitions = yaml.load(fp)

    # assume profile definitions are case insensitive
    profiles_dict = NocaseDict()
    for profile in profile_definitions:
        value = ProfileDef(profile["central_class"],
                           profile["scoping_class"],
                           profile["scoping_path"],
                           profile['type'],
                           profile['doc'])
        key = "%s:%s" % (profile["registered_org"], profile["registered_name"])

        profiles_dict[key] = value
    return profiles_dict


def display_servers(server_definitions_filename):
    """
    display the defined servers information as a table.
    """
    servers = ServerDefinitionFile2(server_definitions_filename)

    title = 'List of all servers that can be tested'

    headers = ['Name', 'Url', 'Default_namespace']
    rows = []
    for server in servers.list_all_servers():
        # specifically does not show server user and pw
        rows.append((server.nickname,
                     server.url,
                     server.default_namespace))

    print_table(title, headers, rows, sort_columns=0)


def run_tests(server_definitions_filename, servers_list,
              test_direction, all_profiles_definitions_filepath, test_list):
    """"
    Run the tests on the servers defined in server_definitions_filename using
    the enable_servers_list to control specific servers to
    test.
    """
    tests_start_time = ElapsedTimer()

    all_profiles_dict = load_profiles_definitions(
        all_profiles_definitions_filepath)

    servers = ServerDefinitionFile2(server_definitions_filename)

    # Dictionary of results includes subdicts for each server and
    # result and server_obj and

    server_results = {}

    for server_data in servers.list_servers(servers_list):
        nickname = server_data.nickname
        server_results[nickname] = {}
        st = ElapsedTimer()  # start time for this server test
        server_results[nickname]['result'] = ("unknown", st.elapsed_time())

        print('==============='
              '%s: Connect: url=%s default_namespace=%s sec=%s '
              'tot=%s=========' %
              (nickname, server_data.url, server_data.implementation_namespace,
               st.elapsed_time(), tests_start_time.elapsed_time()))
        conn = connect(nickname, server_data, debug=True)

        if not conn:
            print('%s: SERVER TEST FAILED: connect failed' % nickname)
            server_results[nickname]['result'] = ("CONN Failed",
                                                  st.elapsed_time())
            continue

        print('%s: Connected:' % nickname)
        server = pywbem.WBEMServer(conn)
        try:
            run_server_tests(nickname, server, all_profiles_dict, st,
                             test_direction=test_direction,
                             tests=test_list)
            result = "Passed"

        except Exception as ex:  # pylint: disable=broad-except
            print('Test exception %s, Exception %s' % (nickname, ex))
            print(traceback.format_exc())
            result = "Failed"

        server_results[nickname]['result'] = (result, st.elapsed_time())
        server_results[nickname]['server_obj'] = server

    #
    # The remainder of this method is the post test report generation
    #

    print('\n\n=========================================================\n')
    print('=========test Results Summary total test time=%s===========' %
          tests_start_time.elapsed_time())

    title = 'Servers processed and general result. The ? in results are for ' \
            'servers that did not connect or failed so that brand, etc not ' \
            'known'
    headers = ['Name', 'Url', 'Default_namespace', 'Result', 'dir',
               'Time', 'brand', 'version', 'interop', 'namespaces']
    rows = []

    for server_data in servers.list_servers(servers_list):
        # specifically does not show serveruser and pw and 2.
        nickname = server_data.nickname
        if 'server_obj' in server_results[nickname]:
            server_obj = server_results[nickname]['server_obj']
            brand = server_obj.brand
            version = server_obj.version
            interop = server_obj.interop_ns
            namespaces = server_obj.namespaces
            url = server_obj.conn.url
            default_namespace = server_obj.conn.default_namespace
        else:
            url = server_data.url
            default_namespace = server_data.default_namespace
            brand = ""
            version = ""
            interop = ""
            namespaces = ""
        rows.append((nickname,
                     url,  # url
                     default_namespace,  # default_namespace
                     # server_data.enabled,  # Enabled
                     server_results[nickname]['result'][0],  # result
                     SVR_DIRECTION.get(nickname, "Unknown"),  # define_direction
                     server_results[nickname]['result'][1],  # completion time
                     fold_string(brand, 18),
                     version,
                     interop,
                     fold_list(namespaces, 30)))

    print_table(title, headers, rows, sort_columns=0)

    if PROFILES_WITH_NO_DEFINITIONS:
        title = 'Missing or incomplete profile definitions. Lists profiles\n' \
                'found in the servers but not in our all_profiles_dict or ' \
                'with\nincomplete definitions.'
        print('\n%s' % title)
        for nickname, profile_names in PROFILES_WITH_NO_DEFINITIONS.items():
            for prof_name in profile_names:
                if prof_name in all_profiles_dict:
                    prof_def = all_profiles_dict[prof_name]
                    print('%s:  %s incomplete definition. CentralClass=%s, '
                          'ScopingClass=%s, scoping_path=%s' %
                          (nickname, prof_name, prof_def.central_class,
                           prof_def.scoping_class,
                           prof_def.scoping_path))
                else:
                    print('%s: Profile %s not defined in %s' %
                          (nickname, prof_name,
                           all_profiles_definitions_filepath))

    if SERVERS_FOR_PROFILE:
        rows = []
        for profile, servers in SERVERS_FOR_PROFILE.items():
            rows.append([profile, fold_list(servers, 60)])
        print_table('Servers for each profile', ['Profile', 'Servers'], rows,
                    sort_columns=0)

    title = 'Table of Profile characteristics (i.e. all_profiles_dict)'
    headers = ['Profile, ' 'Central Class', 'Scoping Class', 'Scoping_path',
               'type', 'comments']
    rows = []
    for name, prof_def in all_profiles_dict.items():
        rows.append([name, prof_def.central_class, prof_def.scoping_class,
                     prof_def.scoping_path, prof_def.type,
                     prof_def.comments])
    print_table(title, headers, rows, sort_columns=0)

    if ASSOC_PROPERTY_COUNTS:
        title = 'Summary of Assoc counts for all servers, slow algorithm.\n' \
                'Displays the number of returns for the request ' \
                ' Associators(obj_path, ResultRole=<xxxx>,\n' \
                '         ResultClass="CIM_ReferencedProfile")\n' \
                '           where <xxxx> is "Dependent" and "Antecedent".\n' \
                'The list of servers searched is the list of possible ' \
                'autonomous servers.'
        headers = ['Server Name', 'profile', 'Dependent\nCount',
                   'Antecedent\nCount']

        print_table(title, headers, ASSOC_PROPERTY_COUNTS, sort_columns=[0, 1])

    title = 'Ordered by col 1'
    print_table(title, headers, ASSOC_PROPERTY_COUNTS, sort_columns=[1, 0])

    if FAST_TEST_RESULTS:
        title = "FAST DIRECTION TEST RESULTS"
        headers = ("server", 'Result', "time")
        print_table(title, headers, FAST_TEST_RESULTS)

    if PROD_TEST_RESULTS:
        title = "PRODUCTION DIRECTION TEST RESULTS"
        headers = ("server", 'Result', 'Comment', "Time")
        rows = []
        for item in PROD_TEST_RESULTS:
            rows.append([item[0], item[1][0], item[1][1], item[2]])
        print_table(title, headers, PROD_TEST_RESULTS)

    if GET_CENTRAL_INST_ROWS:
        title = 'Summary of good/error get_central instance rtns for each ' \
                'server. Excludes servers that did not pass the direction ' \
                'test and profiles that have no definition.'
        headers = ['Server Name', 'Profiles', 'Good rtns', 'Error rtns']
        print_table(title, headers, GET_CENTRAL_INST_ROWS, sort_columns=0)

    if GET_CENTRAL_INST_ERRS:
        title = 'GET_CENTRAL_INSTANCE ERRORS. List of all Error returns from ' \
                'get_central_instances test'
        rows = []
        for nickname, errors in GET_CENTRAL_INST_ERRS.items():
            for data in errors:
                rows.append([nickname, data[0],
                             textwrap.fill(str(data[1]), 60)])
        print_table(title, headers, rows, sort_columns=0)
    print("")

    print('============== FINISHED  ===========')


def parse_args(args, default_server_definitions_path,
               default_profile_definitions_path):
    """
    Parse the command line arguments and return the args dictionary
    """
    prog = os.path.basename(sys.argv[0])
    usage = '%(prog)s [options] server'
    desc = """
Test script for testing get_central_instances method. This script executes
a number of tests and displays against a set of servers defined in the
test file

"""
    epilog = """
Examples:
  %s Fujitsu -v 3

  %s -v 1`
""" % (prog, prog)

    argparser = _argparse.ArgumentParser(
        prog=prog, usage=usage, description=desc, epilog=epilog,
        add_help=False, formatter_class=_WbemcliCustomFormatter)

    pos_arggroup = argparser.add_argument_group(
        'Positional arguments')
    pos_arggroup.add_argument(
        'servers', metavar='servers', nargs='*', type=str,
        default=['default'],
        help='R|Define by nickname zero or more specific servers to\n'
             'test. If  no servers are specified, the default\n'
             'group is tested. If there is no default group defined,\n'
             'all servers are tested.')

    general_arggroup = argparser.add_argument_group(
        'General options')

    general_arggroup.add_argument(
        '-l', '--list_servers', dest='list_servers',
        action='store_true',
        default=False,
        help='List servers nicknames defined by the servers arguement. If '
             'there are no servers defined by the servers argument, list '
             'the servers defined by the group "default". If there is no '
             'default group. list all servers')

    general_arggroup.add_argument(
        '--tests', dest='tests', default=None, nargs='*',
        choices=['overview', 'tree', 'profiles', 'insts', 'centralinsts'],
        help='List the tests to be executed. Default  is all tests')

    general_arggroup.add_argument(
        '-d', '--direction', dest='direction', default=None,
        choices=['dmtf', 'snia'],
        help='Define a particular reference direction for the test. If this '
             'is not specified, the direction algorithm is used, all of them.')

    general_arggroup.add_argument(
        '--serversfile', dest='servers_file', metavar='serversfile',
        default=default_server_definitions_path,
        help='R|The file path for the JSON file that defines the servers\n'
             'to be tested\n'
             'Default: %(default)s')

    general_arggroup.add_argument(
        '--profilesfile', dest='profiles_file', metavar='profilesfile',
        default=default_profile_definitions_path,
        help='R|The file path for the file that defines the\n'
             'characteristics of known profiles.\n'
             'Default: %(default)s')

    general_arggroup.add_argument(
        '-v', '--verbosity', dest='verbosity', type=int,
        default=0,
        help='Increment the output verbosity as integer from 0 t0 3')
    general_arggroup.add_argument(
        '-V', '--version', action='version', version='%(prog)s ' + __version__,
        help='Display script version and exit.')

    general_arggroup.add_argument(
        '-h', '--help', action='help',
        help='Show this help message and exit')

    args = argparser.parse_args()

    return args


if __name__ == '__main__':
    default_profile_definitions_path = os.path.join(os.path.join(
        'tests', 'profiles'), 'profiles.yml')

    args = parse_args(sys.argv[0],
                      DEFAULT_SERVER_FILE,
                      default_profile_definitions_path)

    if args.verbosity > 2:
        print('ARGS=%s' % args)

    if args.list_servers:
        display_servers(args.servers_file)
        sys.exit(0)

    run_tests(args.servers_file, args.servers, args.direction,
              args.profiles_file, args.tests)
