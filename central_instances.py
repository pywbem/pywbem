#!/usr/bin/env python

from collections import namedtuple
from collections import defaultdict
import textwrap
import json
import traceback
import datetime
import threading
from operator import itemgetter
import tabulate
import six

import pywbem
from pywbem._nocasedict import NocaseDict
VERBOSE = False
TABLE_FORMAT = 'simple'


# The following dictionary defines the Characteristics of each of the defined
#     profiles from the documentation
# The name element is the Org:Name of the profile. The value components a tuple
# of:
# centralclass
# scoping class
# scoping_path - This must be an iterable of elements
# autonomous. True if Autonomous

# Named tuple to define Central Class, Scoping Class, ScopingPath.
ProfileDef = namedtuple('ProfileDef', ['central_class', 'scoping_class',
                                       'scoping_path', 'autonomous',
                                       'comments'])

# TODO: Most of these varaiables should be within the main and test servers
# methods
# if not empty this is a list of profiles found in the test but not in the
# all_profiles_dict or where the definitions are incomplete in the
# all_profiles_dict
PROFILES_WITH_NO_DEFINITIONS = []

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


def build_server_dict(servers_filename):
    """
    Build the internal dictionary of Servers from the JSON file defined by
    file_name based on the file_name parameter. The returned dictionary
    contains a dictionary for each server with the key = the server name and
    the data from the json file for that data and also a key 'enabled' that is
    set to `True'
    """
    servers = {}
    with open(servers_filename, 'r') as fh:
        try:
            json_dict = json.load(fh)
            try:
                for svr_name, svr_def in six.iteritems(json_dict):
                    servers[svr_name] = svr_def
                    servers[svr_name]['enabled'] = True

            except KeyError as ke:
                raise KeyError("Items missing from json record %s" % ke)
        except ValueError as ve:
            raise ValueError("Invalid json file %s. exception %s" %
                             (servers_filename, ve))
    return servers


def disable_servers(disable_list, servers):
    """
    Make any server names in the disable_list as disables
    """
    for svr in disable_list:
        server = servers[svr]

        servers[svr] = (server[0], server[1], server[2], server[3], False)


def connect(name, url, user, password, default_namespace, debug=None,
            timeout=10):
    """
    Connect and confirm server works by testing for a known class in
    the default namespace
    """
    conn = pywbem.WBEMConnection(url, (user, password),
                                 default_namespace=default_namespace,
                                 no_verification=True,
                                 timeout=timeout)
    if debug:
        conn.debug = True
    try:
        conn.GetClass("CIM_ManagedElement")
        return conn
    except pywbem.Error as er:
        print("Connection Error %s, except=%s" % (name, er))
        return None


def test_server(url, principal, credential):
    """
    Test a single server to determine if it is alive. Connects and gets a
    single class. Returns True if the sever is alive.
    """
    try:
        conn = pywbem.WBEMConnection(url, (principal, credential),
                                     no_verification=True, timeout=10)

        server = pywbem.WBEMServer(conn)
        server.namespaces  # pylint: disable=pointless-statement
        RESULTS.append((url, principal, credential))
    except pywbem.Error as er:
        print('URL %s failed %s' % (url, er))


RESULTS = []


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
        process = threading.Thread(target=test_server,
                                   args=(url, principal, credential))
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
    print("Interop namespace: %s" % server.interop_ns)
    print("Brand: %s" % server.brand)
    print("Version: %s" % server.version)
    print("Namespaces: %s" % server.namespaces)
    print('namespace_classname: %s' % server.namespace_classname)
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


def get_profile_name(org_vm, inst):
    """
    Get the org, name, and version from the profile instance and
    return them as a tuple.
    Returns: tuple of org, name, vers

    Raises:
      TypeError: if invalid property type
      ValueError: If property value outside range
    """
    try:
        org = org_vm.tovalues(inst['RegisteredOrganization'])
        name = inst['RegisteredName']
        vers = inst['RegisteredVersion']
        return org, name, vers
    except TypeError as te:
        print('ORG_VM.TOVALUES FAILED. inst=%s, Exception %s' % (inst, te))
    except ValueError as ve:
        print('ORG_VM.TOVALUES FAILED. inst=%s, Exception %s' % (inst, ve))
    return 'ERR', 'ERR', 'ERR'


def get_full_profile_name_str(org_vm, profile_inst):
    """
    Return the org, name, version as a string org:name:version
    """
    try:
        name_tuple = get_profile_name(org_vm, profile_inst)
    except Exception as ex:  # pylint: disable=broad-except
        print('GET_FULL_PROFILE_NAME exception %sm tuple=%r inst=%s' %
              (ex, name_tuple, profile_inst))
        return("UNKNOWN")
    return "%s:%s:%s" % (name_tuple[0], name_tuple[1], name_tuple[2])


def profile_organdname_str(org_vm, profile_inst):
    """
    Return the organization and name of a profile as a string
    org:name.  The version component is not part of this name
    """
    name_tuple = get_profile_name(org_vm, profile_inst)
    return "%s:%s" % (name_tuple[0], name_tuple[1])


def print_profile_name(org_vm, profile_instance):
    """
    Print information on a profile defined by profile_instance.

    Parameters:

      org_vm: The value mapping for CIMRegisterdProfile and
          RegisteredOrganization so that the value and not value mapping
          is displayed.

      profile_instance: instance of a profile to be printed
    """
    print("  %s %s Profile %s" % get_profile_name(org_vm, profile_instance))


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
                                     get_full_profile_name_str(org_vm, inst)))
        else:
            names.append(get_full_profile_name_str(org_vm, inst))
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


def show_profiles(name, server, org_vm, include_classnames=False):
    """
    Create a table of info about the profiles based on getting the
    references, etc. both in the dependent and antecedent direction.

    The resulting table is printed.
    """
    rows = []
    for profile_inst in server.profiles:
        org, pname, ver = get_profile_name(org_vm, profile_inst)
        profile_name = '%s:%s:%s' % (org, pname, ver)
        deps = get_associated_profile_names(
            profile_inst.path, "dependent", org_vm, server,
            include_classnames=False)
        dep_refs = get_references(profile_inst.path, "antecedent",
                                  profile_name, server)
        ants = get_associated_profile_names(
            profile_inst.path, "antecedent", org_vm, server,
            include_classnames=False)
        ant_refs = get_references(profile_inst.path, "dependent",
                                  profile_name, server)

        # get unique class names
        dep_ref_clns = set([ref.classname for ref in dep_refs])
        ant_ref_clns = set([ref.classname for ref in ant_refs])
        row = (org, pname, ver,
               fold_list(deps),
               fold_list(list(dep_ref_clns)),
               fold_list(ants),
               fold_list(list(ant_ref_clns)))
        rows.append(row)

        # append this server to the  dict of servers for this profile
        SERVERS_FOR_PROFILE[profile_name].append(name)

    title = 'Advertised profiles for %s showing Profiles associations' \
        'Dependencies are Associators, AssocClass=CIM_ReferencedProfile' \
        'This table shows the results for ' % name
    headers = ['Org', 'Registered Name', 'Version',
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


def count_ref_assoc(svr_name, server, profile_insts, org_vm):
    """
    Get dict of counts of associator returns for ResultRole == Dependent and
    ResultRole == Antecedent for profiles in list.
    Returns a dictionary where keys are profile name and value are a tuple of
    the number of associator instances for each of the AssociatorName calls.
    """

    assoc_dict = {}
    for profile_inst in profile_insts:
        deps_count, ants_count = get_assoc_count(server, profile_inst)
        profile_name = get_full_profile_name_str(org_vm, profile_inst)

        assoc_dict[profile_name] = (deps_count, ants_count)

    title = 'Display antecedent and dependent counts for possible ' \
        'autonomous profiles.\nDisplays the number of instances  returned ' \
        'by\nAssociators request on profile for possible autonomous profiles'
    rows = [(key, value[0], value[1]) for key, value in assoc_dict.items()]

    print_table(title, ['profile', 'Dependent\nCount', 'Antecedent\nCount'],
                rows, sort_columns=0)

    # add rows to the global list for table of
    g_rows = [(svr_name, key, value[0], value[1])
              for key, value in assoc_dict.items()]
    ASSOC_PROPERTY_COUNTS.extend(g_rows)
    return assoc_dict


def determine_reference_direction(svr_name, server, org_vm,
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
    assoc_dict = count_ref_assoc(svr_name, server, prof_list, org_vm)

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
                         (svr_name, server, prof_list, assoc_dict))

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
                SVR_DIRECTION[svr_name] = "undefined"
                raise ValueError('Name: %s; Server=%s; Cannot determine '
                                 'possible CIM_ReferencedProfile direction\n'
                                 '%s', (svr_name, possible_top_profiles))

    dir_type = 'dmtf' if not zero_count_pos else 'snia'
    if VERBOSE:
        print('DIR_TYPE=%s' % (dir_type))

    SVR_DIRECTION[svr_name] = dir_type

    return dir_type


def test_get_central_instances(name, server, all_profiles_dict, org_vm,
                               reference_direction='dmtf'):
    """Test get central instances"""
    good_rtns = []
    error_rtns = []

    for inst in server.profiles:
        try:
            org, pname, version = get_profile_name(org_vm, inst)

            prof = "%s:%s" % (org, pname)
            if prof not in all_profiles_dict:
                PROFILES_WITH_NO_DEFINITIONS.append(prof)
                continue

            prof_def = all_profiles_dict[prof]
            print('%s: PROFILE get_central_instances: %s inst.path=%s\n   '
                  'central_class=%s,scoping_class=%s, scoping_path=%s' %
                  (name, prof, inst.path, prof_def.central_class,
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
                good_rtns.append((prof, central_paths))

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
                        good_rtns.append((prof, central_paths))
                    else:
                        print('INVALID_SCOPING_PATH %s %s %s' % (
                            prof_def.scoping_class, prof_def.central_class,
                            prof_def.scoping_path))
                        PROFILES_WITH_NO_DEFINITIONS.append(prof)
                else:
                    PROFILES_WITH_NO_DEFINITIONS.append(prof)

        except ValueError as ve:
            print("ValueError: %s: %s:%s:%s\n  inst_path %s\n   exception %s" %
                  (name, org, pname, version, inst.path, ve))
            if VERBOSE:
                if server.conn.debug:
                    print('LAST_REQUEST\n%s' % server.conn.last_request)
                    print('LAST_REPLY\n%s' % server.conn.last_reply)
            error_rtns.append((prof, ve))
        except pywbem.Error as er:
            print("pywbem.Error: %s: %s:%s:%s\n  inst_path=%s\n   "
                  "server=%s\n   Exception=%s"
                  % (name, org, pname, version, inst.path, server, er))
            if VERBOSE:
                if server.conn.debug:
                    print('LAST_REQUEST\n%s' % server.conn.last_request)
                    print('LAST_REPLY\n%s' % server.conn.last_reply)
            error_rtns.append((prof, er))

    print('%s: Successful_Profiles=%s Error=%s\n' % (name, len(good_rtns),
                                                     len(error_rtns)))

    title = '%s: Successful returns from get_central_instances' % name
    headers = ['Profile', 'Rtn Paths']
    rows = []
    for data in good_rtns:
        # TODO str(p) to fold_path(str(p), 20)
        paths_str = '\n'.join([str(p) for p in data[1]])
        rows.append([data[0], paths_str])
    print_table(title, headers, rows)

    title = '%s: Error returns from get_central_instances' % name
    headers = ['Profile', 'Error rtn']
    rows = [[data[0], textwrap.fill(str(data[1]), 80)] for data in error_rtns]
    print_table(title, headers, rows, sort_columns=0)

    # set the data into the lists for display at end of the test
    GET_CENTRAL_INST_ERRS[name] = error_rtns
    GET_CENTRAL_INST_ROWS.append([name, len(server.profiles), len(good_rtns),
                                  len(error_rtns)])


def show_registeredprofile_insts(server):
    """
    Output the mof for the registered profiles
    """
    for inst in server.profiles:
        print(inst.tomof())


def show_cimreferencedprofile_insts(server):
    """
    Display the cimreferenced profile instances
    """
    try:
        insts = server.conn.EnumerateInstances("CIM_ReferencedProfile",
                                               namespace=server.interop_ns)
        print('INSTANCES OF CIM_ReferencedProfile')
        for inst in insts:
            print(inst.tomof())
    except pywbem.Error as er:
        print('CIM_ReferencedProfile failed for conn=%s\nexception=%s'
              % (server, er))


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
            row = [get_full_profile_name_str(org_vm, dep),
                   inst.classname,
                   get_full_profile_name_str(org_vm, ant)]
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


def get_profiles_in_svr(server_name, server, all_profiles_dict, org_vm,
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
        profile_org_name = profile_organdname_str(org_vm, profile_inst)
        if profile_org_name in all_profiles_dict:
            profiles_in_dict.append(profile_inst)
        else:
            if add_error_list:
                print('PROFILES_WITH_NO_DEFINITIONS svr=%s:  %s' %
                      (server_name, profile_org_name))
                PROFILES_WITH_NO_DEFINITIONS.append(profile_org_name)
    return profiles_in_dict


def test_profile_direction(server_name, server, all_profiles_dict, org_vm):
    """
    This is the test function for determine_reference_direction. It
    Defines the set of possible autonomous profiles from profile_dict,
    calls determine_reference_direction and displays the results of
    the test.
    """
    profiles_in_dict = get_profiles_in_svr(server_name, server,
                                           all_profiles_dict,
                                           org_vm)
    possible_aut_profiles = []

    for profile_inst in profiles_in_dict:
        profile_org_name = profile_organdname_str(org_vm, profile_inst)
        if all_profiles_dict[profile_org_name].autonomous:
            possible_aut_profiles.append(profile_inst)

    possible_names = [get_profile_name(org_vm, inst)
                      for inst in possible_aut_profiles]
    cim_ref_direction = None
    name_strs = ["%s:%s:%s" % (name_tuple[0], name_tuple[1], name_tuple[2])
                 for name_tuple in possible_names]
    print('POSSIBLE_AUTO_PROFILES %s: %s' % (server_name, name_strs))

    try:
        cim_ref_direction = determine_reference_direction(
            server_name,
            server, org_vm,
            possible_autonomous_profiles=possible_aut_profiles)
    except Exception as ex:  # pylint: disable=broad-except
        print('ERROR: determine_reference_direction failed: Exception=%s' % ex)
        return

    prop_names = ['Antecedent', 'Dependent']
    if cim_ref_direction == 'snia':
        prop_names.reverse()
    print('%s defines CIM_ReferencedProfile as "%s":\n'
          '   %s = Referenced/Component Profile,\n'
          '   %s = Referencing/Autonomous Profile' % (server_name,
                                                      cim_ref_direction,
                                                      prop_names[0],
                                                      prop_names[1]))

    return cim_ref_direction


def run_server_tests(server_name, server, all_profiles_dict, st,
                     test_direction=None, tests=None):
    """Execute tests on the server connection defined by server
    """
    print('Start tests for %s' % server_name)
    # Set up the org_vm for this server.
    org_vm = pywbem.ValueMapping.for_property(
        server, server.interop_ns,
        'CIM_RegisteredProfile',
        'RegisteredOrganization')

    if not tests or 'Overview' in tests:
        overview(server_name, server)

    # if not tests or 'Profiles' in tests:
        # show_profiles(server_name, server, org_vm, include_classnames=True)

    # print('TIME AFTER SHOW PROFILES %s' % st.elapsed_time())

    if not tests or 'ProfileRefs' in tests:
        show_cimreferencedprofile_insts(server)
        show_registeredprofile_insts(server)

    try:
        show_cimreferences(server_name, server, org_vm)
    except Exception as ex:  # pylint: disable=broad-except
        print(traceback.format_exc())
        print("SHOW_CIMREF exception %s" % ex)

    print('TIME AFTER SHOW_CIMREFERENCES %s' % st.elapsed_time())

    # Determine profiles for this server not in all_profiles_dict and put
    # into global list for display at end of run
    try:
        get_profiles_in_svr(server_name, server, all_profiles_dict,
                            org_vm, add_error_list=True)
    except Exception as ex:
        print('Exception  in get_profiles_in_svr %s' % ex)
        raise

    print('TIME AFTER get_profiles_in_svr %s' % st.elapsed_time())

    if not test_direction:
        try:
            cim_ref_direction = test_profile_direction(server_name, server,
                                                       all_profiles_dict,
                                                       org_vm)
        except Exception as ex:
            print('Exception  in cim_ref_direction %s' % ex)
            raise
    else:
        cim_ref_direction = test_direction

    print('TIME AFTER test_profile_direction %s' % st.elapsed_time())

    if not tests or 'CentralInsts' in tests:
        test_get_central_instances(server_name, server, all_profiles_dict,
                                   org_vm,
                                   reference_direction=cim_ref_direction)
    print('TIME AFTER test_get_central_instances %s' % st.elapsed_time())


def load_all_profiles_dictionary(filename):
    with open(filename, 'r') as fp:
        load_data_dict = json.load(fp)

    profiles_dict = {}
    for key, data in load_data_dict.items():
        values = ProfileDef(data["central_class"],
                            data["scoping_class"],
                            data["scoping_path"],
                            data['autonomous'],
                            data['comments'])
        profiles_dict[key] = values
    return profiles_dict


def main():
    "Main function"
    tests_start_time = ElapsedTimer()

    print('Central_instances test verison 0.9.0')

    all_profiles_dict = load_all_profiles_dictionary('profiledictionary.json')

    # Use this list to enable only selected servers for testing by including
    # there names in the list
    # , 'Fujitsu' 'EMC1', 'EMC3',  'Pure_Storage' 'NetApp'
    enable_servers_list = []

    # Use this list to bypass testing selected servers.  This speeds up the
    # tests because some servers in the test group are failed and there is
    # no need to even contact them. Each attempt to contact a failed server
    # costs some time in the test.
    # Disable the following servers since they appear to be down from earlier
    # tests
    # disable_list = ['NetApp/LSI', 'HP/3PARData', 'Hewlett_Packard1',
    #                'Hewlett_Packard4', 'Dot_Hill', 'Dot_Hill1', 'EMC',
    #                'Hitachi_Data_Systems2', 'Cisco', 'Hitachi_Data_Systems']
    disable_list = []

    failed_list = []

    # Variable that determines if we execute the test direction code or just
    # use the direction defined in the variable.  If None, the test_diredction
    # code is executed.  If 'snia' or 'dmtf' that is the assumed direction when
    # the get_central_instances test is executed.
    test_direction = None

    # Get servers from
    servers = build_server_dict("pywbemcliservers.json")
    disable_servers(disable_list, servers)

    # Test results for each server. Contains a dictionary for each server
    # with  'result' = (<Result_string>, time),
    #       'server' = WBEMServer object instance
    server_results = {}

    for svr_name in servers:
        st = ElapsedTimer()  # start time for this server test
        # Test for Enable List. If list has entries, only test servers whose
        # names are in this list.  Allows testing subset of the servers
        server_results[svr_name] = {}
        if not enable_servers_list or svr_name in enable_servers_list:
            pass
        else:
            print('\n============Name=%s; Not Enabled sec=%s tot=%s======'
                  % (svr_name, st.elapsed_time(),
                     tests_start_time.elapsed_time()))
            server_results[svr_name]['result'] = ("Not Enabled",
                                                  st.elapsed_time())
            continue

        if not servers[svr_name]['enabled']:
            print('\n============Name=%s; skipped  sec=%s tot=%s========='
                  % (svr_name, st.elapsed_time(),
                     tests_start_time.elapsed_time()))
            server_results[svr_name]['result'] = ("Skipped", st.elapsed_time())

        else:
            url = servers[svr_name]["server_url"]
            user = servers[svr_name]["user"]
            password = servers[svr_name]["password"]
            default_namespace = servers[svr_name]['default_namespace']
            print('==============='
                  'name=%s, Connected: url=%s default_namespace=%s sec=%s '
                  'tot=%s=========' %
                  (svr_name, url, default_namespace, st.elapsed_time(),
                   tests_start_time.elapsed_time()))
            conn = connect(svr_name, url, user, password, default_namespace,
                           debug=True)
            if conn:
                print('Connected: name=%s url=%s default_ns=%s' %
                      (svr_name, url, default_namespace))
                server = pywbem.WBEMServer(conn)
                server_results[svr_name]['server'] = server
                try:
                    run_server_tests(svr_name, server, all_profiles_dict, st,
                                     test_direction=test_direction)
                except Exception as ex:  # pylint: disable=broad-except
                    print('Test exception %s, Exception %s' % (svr_name, ex))
                    print(traceback.format_exc())
                    server_results[svr_name]['result'] = ("Failed",
                                                          st.elapsed_time())
                    continue

                server_results[svr_name]['result'] = \
                    ("Passed", st.elapsed_time())

            else:
                print('SERVER TESTS FAILED: name=%s, connect failed' % svr_name)
                failed_list.append(svr_name)
                server_results[svr_name]['result'] = ("CONN Failed",
                                                      st.elapsed_time())
    print('\n\n=========================================================\n')
    print('=========test Results Summary total test time=%s===========' %
          tests_start_time.elapsed_time())

    title = 'Servers processed and general result. The ? in results are for ' \
            'servers that did not connect or failed so that brand, etc not ' \
            'known'
    headers = ['Name', 'Url', 'Default_namespace', 'Enabled', 'Result', 'dir',
               'Time', 'brand', 'version', 'interop', 'namespaces']
    rows = []
    for name, server in servers.items():
        # specifically does not show serveruser and pw and 2.
        if name in server_results and 'server' in server_results[name]:
            server_obj = server_results[name]['server']
            brand = server_obj.brand
            version = server_obj.version
            interop = server_obj.interop_ns
            namespaces = server_obj.namespaces
            url = server_obj.conn.url
            default_namespace = server_obj.conn.default_namespace
        else:
            brand = "?"
            version = "?"
            interop = "?"
            namespaces = "?"
            url = "?"
            default_namespace = "?"

        rows.append((name,
                     url,  # url
                     default_namespace,  # default_namespace
                     server['enabled'],  # Enabled
                     server_results[name]['result'][0],  # result
                     SVR_DIRECTION.get(name, "Unknown"),  # determine_direction
                     server_results[name]['result'][1],  # completion time
                     fold_string(brand, 18),
                     version,
                     interop,
                     fold_list(namespaces, 30)))

    print_table(title, headers, rows, sort_columns=0)

    print('\nFAILED_Servers(Servers failing connect and not tested):\n[%s]' %
          fold_list(failed_list, 60))

    if PROFILES_WITH_NO_DEFINITIONS:
        title = 'Missing or incomplete profile definitions. Lists profiles\n' \
                'found in the servers but not in our all_profiles_dict or ' \
                'with\nincomplete defintions.'
        print('\n%s' % title)
        for prof_name in set(PROFILES_WITH_NO_DEFINITIONS):
            if prof_name in all_profiles_dict:
                prof_def = all_profiles_dict[prof_name]
                print('  %s incomplete definition. CentralClass=%s, '
                      'ScopingClass=%s, scoping_path=%s' %
                      (prof_name, prof_def.central_class,
                       prof_def.scoping_class,
                       prof_def.scoping_path))
            else:
                print('Profile %s not defined in allprofiles_dict' % prof_name)

        for prof_name in set(PROFILES_WITH_NO_DEFINITIONS):
            if prof_name not in all_profiles_dict:
                print('    "%s": ProfileDef("", "", None, False),' % prof_name)

    rows = []
    for profile, servers in SERVERS_FOR_PROFILE.items():
        rows.append([profile, fold_list(servers, 60)])
    print_table('Servers for each profile', ['Profile', 'Servers'], rows,
                sort_columns=0)

    title = 'Table of Profile characteristics (i.e. all_profiles_dict)'
    headers = ['Profile, ' 'Central Class', 'Scoping Class', 'Scoping_path',
               'Autonomous', 'comments']
    rows = []
    for name, prof_def in all_profiles_dict.items():
        rows.append([name, prof_def.central_class, prof_def.scoping_class,
                     prof_def.scoping_path, prof_def.autonomous,
                     prof_def.comments])
    print_table(title, headers, rows, sort_columns=0)

    title = 'Summary of Assoc counts for all servers. Displays\n' \
            'the number of returns for the request ' \
            ' Associators(obj_path, ResultRole=<xxxx>,\n' \
            '            ResultClass="CIM_ReferencedProfile")\n' \
            '                where <xxxx> is "Dependent" and "Antecedent".\n' \
            'The list of servers searched is the list of possible autonomous ' \
            'servers.'
    headers = ['Server Name', 'profile', 'Dependent\nCount',
               'Antecedent\nCount']

    print_table(title, headers, ASSOC_PROPERTY_COUNTS, sort_columns=[0, 1])

    title = 'Summary of good/error get_central instance rtns for each server.' \
            'Excludes servers that did not pass the direction test and '
            'profiles that have no definition.'
    headers = ['Server Name', 'Profiles', 'Good rtns', 'Error rtns']
    print_table(title, headers, GET_CENTRAL_INST_ROWS, sort_columns=0)

    title = 'GET_CENTRAL_INSTANCE ERRORS. List of all Error returns from ' \
            'get_central_instances test'
    rows = []
    for svr_name, errors in GET_CENTRAL_INST_ERRS.items():
        for data in errors:
            rows.append([svr_name, data[0], textwrap.fill(str(data[1]), 60)])
    print_table(title, headers, rows, sort_columns=0)

    print('============== FINISHED  ===========')


if __name__ == '__main__':
    main()
