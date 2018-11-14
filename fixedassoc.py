#!/usr/bin/env python

from collections import namedtuple
import json
import datetime
from operator import itemgetter
import textwrap
import tabulate
import six
import pywbem

VERBOSE = True

TABLE_FORMAT = 'simple'

# summary info on profiles, etc. for each server. A row is added for each
# server tested.
GET_CENTRAL_INST_ROWS = []

# results dictionary for Central instance error.
GET_CENTRAL_INST_ERRS = {}

# Global set of rows to create a table of the assoc property  counts for all
# servers.
ASSOC_PROPERTY_COUNTS = []

ProfileDef = namedtuple('ProfileDef', ['central_class', 'scoping_class',
                                       'scoping_path', 'autonomous',
                                       'comments'])



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


class TestServers(object):
    """
    Loads server definitions with filters to allow enabling and disabling
    the servers in the test with method to return just enabled servers

    """
    def __init__(self, filename, ignore_names=None, enable_names=None):
        """
        Read

          Parameters (:term:`string`):
             Name of the JSON file from which the servers information is read

             ignore_names ():
                List of server names that are to be ignored. The constructor
                removes these from the list of names loaded

        """
        print('ig %s en %s res %s' % (ignore_names, enable_names, (ignore_names and enable_names)))
        if ignore_names and enable_names:
            ValueError("ignore_names and enable_names are mutually exclusive")
        self._filename = filename

        if isinstance(enable_names, six.string_types):
            self._enable_names = [_enable_names]
        else:
            self._enable_names = enable_names
        if isinstance(enable_names, six.string_types):
            self._ignore_names = [ignore_names]
        else:
            self._ignore_names = ignore_names

        self._servers = {}

        self.build_server_dict()

        self.filter_dict()

    def __str__(self):
        """
        Return a short string representation of the instance of the class,
        for human consumption.
        """
        return "TestServers(Len=%s)" % len(self)

    def __repr__(self):
        """
        Return a string representation of the instance of the class,
        that is suitable for debugging.
        """
        return "TestServers(Len=%s)" % len(self)

    def __contains__(self, key):
        return key in self._servers

    def __getitem__(self, key):
        return self._servers[key]

    def __delitem__(self, key):
        del self._servers[key]

    def __len__(self):
        return len(self._servers)

    def __iter__(self):
        return six.iterkeys(self._servers)

    def enabled(self):
        """
        Returns a dictionary of the server definitions for servers that are
        enabled.  The keys are the names and the value for each key is the
        dictionary of information from the server definition in the input file.
        """
        d = {}
        for name in self._servers:
            if self._servers[name]['enabled']:
                d[name] = self._servers[name]['server_def']
        return d

    def values(self):
        """
        Return a copied list of the server_def of this TestServers
        instance.
        """
        return [v.value for v in self._servers.values()]

    def items(self):
        """
        Return a copied list of the server names and values
        of TestClass instance.
        """
        return [(key, v.value) for key, v in self._servers.items()]

    def filter_dict(self):
        """
        Filter the server list based on the ignore and filter lists
        """
        # set enable flag to False if in ignore_names
        if self._ignore_names:
            for name in self._servers:
                if name in self._ignore_names:
                    self._servers[name]['enabled'] = False

        # set enable flag to False if not in enable_names
        if self._enable_names:
            for name in self._servers:
                if name not in self._enable_names:
                    self._servers[name]['enabled'] = False

    def build_server_dict(self):
        """
        Build the internal dictionary of Servers from the JSON file defined by
        file_name based on the file_name parameter
        """

        with open(self._filename, 'r') as fh:
            try:
                json_dict = json.load(fh)
                try:
                    for svr_name, svr_def in six.iteritems(json_dict):
                        self._servers[svr_name] = {}
                        self._servers[svr_name]['server_def'] = svr_def
                        self._servers[svr_name]['enabled'] = True

                except KeyError as ke:
                    raise KeyError('Items missing from json record %s in '
                                   'servers file "%s"' % (ke, self._filename))
            except ValueError as ve:
                raise ValueError("Invalid json file %s. exception %s" %
                                 (self._filename, ve))

    def display(self):

        title = 'Servers processed and general result. The ? in results are ' \
                'for servers that did not connect or failed so that brand, ' \
                'etc not known.'
        #headers = ['Name', 'Url', 'Default_namespace', 'Enabled', 'Result',
        #           'dir', 'Time', 'brand', 'version', 'interop', 'namespaces']

        headers = ['Name', 'Url', 'Default_namespace', 'Enabled',
                   'brand', 'version', 'interop', 'namespaces']
        rows = []
        for name, server in self._servers.items():
            # specifically does not show server[1] and 2. They are user and pw
            if 'server_obj' in server:
                brand = server['server_obj'].brand
                version = server['server_obj'].version
                interop = server['server_obj'].interop
                namespaces = server['server_obj'].namespaces
            else:
                brand = "?"
                version = "?"
                interop = "?"
                namespaces = "?"
            rows.append((name,
                         server['server_def']["server_url"],
                         server['server_def']["default_namespace"],
                         server['enabled'],
                         #server_results[name][0],  # result
                         #SVR_DIRECTION.get(name, "Unknown"),  # determine_direction
                         #server_results[name][1],  # results
                         fold_string(brand, 18),
                         version,
                         interop,
                         fold_list(namespaces, 30)))

        print_table(title, headers, rows, sort_columns=0)

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


def compare_paths(act_paths, exp_paths):
    """Test method to compare lists of CIMInstancePaths"""

    assert len(act_paths) == len(exp_paths), \
        'COMPARE FAILED on lengths %s != %s' % (len(act_paths), len(exp_paths))
    act_x = [p.to_wbem_uri('canonical') for p in act_paths]
    exp_x = [p.to_wbem_uri('canonical') for p in exp_paths]
    assert act_x.sort() == exp_x.sort(), \
        'Path Compare differed\n%r\n%r' % (act_x, exp_x)


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


def count_associators(server):
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
    # Create dict with:
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


def determine_cimrefrence_direction(svr_name, server,
                                    possible_autonomous_profiles=None,
                                    possible_component_profiles=None):
    """
    Determine CIM_ReferenceProfile Antecedent/Dependent direction from
    server data and a list of known autonomous and/or component profiles.

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
                #print('DETERMINED_TYPE v0 %s %s' % (ppath, t[0]))
            elif ppath in v1_dict:
                v1_paths.append(ppath)
                #print('DETERMINED_TYPE v1 %s %s' % (ppath, t[1]))
        if v0_paths and not v1_paths:
            dir_type = t[0]
        elif v1_paths and not v0_paths:
            dir_type = t[1]
        elif not v0_paths and not v1_paths:
            dir_type = None
        else:
            ps = 'possible %s' % ('autonomous' if autonomous else 'component')
            print('ERROR VALERR %s\n%s:%s\n%s: %s' % (ps, t[0], v0_paths, t[1], v1_paths))
            raise ValueError("Cannot determine type. "
                             "determine_cimrefrence_direction shows "
                             "conflicts in %s profile list. %s; %s\n%s; %s" %
                             (ps, t[0], v0_paths, t[1], v1_paths))
        return dir_type

    #print('POSSIBLE_AUTONOMOUS_PROFILES:\n%s' % possible_autonomous_profiles)
    if not possible_autonomous_profiles and not possible_component_profiles:
        raise ValueError("Either possible_autonomous_profiles or "
                         "possible_component_profiles must have a value")
    assoc_dict = count_associators(server)
    # returns dictionary where key is profile name and value is dict of
    # ant: dep: with value count

    # Reduce to dictionary where ant/dep are 0 and non-zero, i.e. top and bottom
    new_dict = {}
    for key, value in assoc_dict.items():
        if (not value['dep'] and value['ant']) or (value['dep']
                                                   and not value['ant']):
            new_dict[key] = (value['dep'], value['ant'])
            if not value['dep'] and not value['ant']:
                print('ERROR key %s value %s' % (key, value))

    # print('NEW_DICT %s' % new_dict)
    # create a dictionary with entry for each new_dict itme that has data in
    # one of the value items.
    v0_dict = {key: value for key, value in new_dict.items() if value[0]}
    v1_dict = {key: value for key, value in new_dict.items() if value[1]}
    #print('V0_DICT %s' % v0_dict)
    #print('V1_DICT %s' % v1_dict)
    #print('POSSIBLE_AUTONOMOUS_PROFILES %s' % possible_autonomous_profiles)

    auto_dir_type = _determine_type(possible_autonomous_profiles, v0_dict,
                                    v1_dict, True)
    comp_dir_type = _determine_type(possible_component_profiles, v0_dict,
                                    v1_dict, False)

    #print('AUTO_DIR %s %s' % (auto_dir_type, comp_dir_type))
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
    print('RAISE VALERR %s %s' % (auto_dir_type, comp_dir_type))
    raise ValueError('Name: %s; Cannot determine '
                     'possible CIM_ReferencedProfile direction. '
                     'Autonomous and componentTests do not match. '
                     'auto_dir_type=%s, '
                     'comp_dir_type=%s\nServer=%s; ' %
                     (svr_name, auto_dir_type, comp_dir_type, server))


def show_count_associators(svr_name, server, org_vm):
    """
    Display results of count_associators(...)). Generates a table showing the
    results of the call. This is just a  test tool.
    """
    d_assoc = count_associators(server)

    svr_profiles_dict = {prof.path: prof for prof in server.profiles}

    headers = ('profile', 'ants', 'deps')
    rows = []

    assoc_dict = {}
    for prof_key, values in d_assoc.items():
        profile_name = get_full_profile_name_str(org_vm,
                                                 svr_profiles_dict[prof_key])
        assoc_dict[profile_name] = (values['ant'], values['dep'])

    rows = []
    title = 'Display antecedent and dependent counts for possible ' \
        'autonomous profiles.\nDisplays the number of instances  returned ' \
        'by\nAssociators request on profile for possible autonomous profiles'
    headers = ('profile', 'Dependent\nCount', 'Antecedent\nCount')
    for profile_name, value in assoc_dict.items():
        rows.append((profile_name, value[0], value[1]))

    print_table(title, headers, rows, sort_columns=[0])

    g_rows = [(svr_name, key, value[0], value[1])
              for key, value in assoc_dict.items()]
    ASSOC_PROPERTY_COUNTS.extend(g_rows)


def load_profile_dictionary(filename):
    """
    Load the json file defined by filename into a python dictionary and
    return the dictionary
    """
    with open(filename, 'r') as fp:
        load_data_dict = json.load(fp)

    profile_dict = {}
    for key, data in load_data_dict.items():
        values = ProfileDef(data["central_class"],
                            data["scoping_class"],
                            data["scoping_path"],
                            data['autonomous'],
                            data['comments'])
        profile_dict[key] = values
    return profile_dict


PROFILES_WITH_NO_DEFINITIONS = []


def get_profiles_in_svr(server_name, server, all_profile_dict, org_vm,
                        add_error_list=False):
    """
    Returns list of profiles in the profile_dict and in the defined server.
    If add_error_list is True, it also adds profiles not found to
    PROFILES_WITH_NO_DEFINITIONS.
    """
    profiles_in_svr = []
    for profile_inst in server.profiles:
        profile_org_name = profile_organdname_str(org_vm, profile_inst)
        if profile_org_name in all_profile_dict:
            profiles_in_svr.append(profile_inst)
        else:
            if add_error_list:
                print('PROFILES_WITH_NO_DEFINITIONS svr=%s:  %s' %
                      (server_name, profile_org_name))
                PROFILES_WITH_NO_DEFINITIONS.append(profile_org_name)
    return profiles_in_svr


def possible_target_profiles(server_name, server, all_profiles_dict,
                             org_vm, autonomous=True, output='path'):
    """
    Get list of possible autonomous or component profiles based on the list
    of all profiles and the list of profiles in the defined server.

    Returns list of *paths or insts, or profile names depending on the value
    of the output parameter.
    """

    profiles_in_svr = get_profiles_in_svr(server_name, server,
                                          all_profiles_dict,
                                          org_vm)
    # list of possible autonomous profiles for testing
    possible_profiles = []

    for profile_inst in profiles_in_svr:
        profile_org_name = profile_organdname_str(org_vm, profile_inst)
        if autonomous:
            if all_profiles_dict[profile_org_name].autonomous:
                possible_profiles.append(profile_inst)
        else:
            if not all_profiles_dict[profile_org_name].autonomous:
                possible_profiles.append(profile_inst)

    if output == 'path':
        possible_profiles = [inst.path for inst in possible_profiles]
    elif output == 'name':
        possible_profiles = [get_full_profile_name_str(org_vm, inst)
                             for inst in possible_profiles]

    return possible_profiles


def test_get_central_instances(name, server, profile_dict, org_vm,
                               direction='dmtf'):
    """Test get central instances"""
    good_rtns = []
    error_rtns = []
    # account for the direction parameter
    if direction == 'dmtf':
        dmtf_dir = True
    elif direction == 'snia':
        dmtf_dir = False
    else:
        print('ERROR: direction parameter must be "dmtf" or  "snia". '
              'Parameter is "%s"' % direction)
        return

    for inst in server.profiles:
        try:
            org, pname, version = get_profile_name(org_vm, inst)

            prof = "%s:%s" % (org, pname)
            if prof not in profile_dict:
                PROFILES_WITH_NO_DEFINITIONS.append(prof)
                continue

            prof_def = profile_dict[prof]
            print('%s: PROFILE get_central_class: %s inst.path=%s\n   '
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
                        scoping_path=prof_def.scoping_path)
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
                                dmtf_reference_direction=dmtf_dir)
                        except pywbem.Error as er:
                            print('GET_CENTRAL_INSTANCES Exception %s:%s' %
                                  (er.__class__.__name__, er))
                            if server.conn.debug:
                                print('LAST_REQUEST\n%s' %
                                      server.conn.last_request)
                                print('LAST_REPLY\n%s' % server.conn.last_reply)
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

def main():

    enable_servers_list = ['EMC3']  # , 'Fujitsu' 'EMC1', 'EMC3',
    #  'Pure_Storage' Brocade1, 'NetApp' 'NetApp1'

    test_results = []

    # servers = build_server_dict("pywbemcliservers.json")

    servers = TestServers("pywbemcliservers.json",
                          ignore_names=None,
                          enable_names=['EMC3'])

    print('SERVERS %s' % servers)

    # dictionary for servers that do connect
    server_general_info = {}

    all_profiles_dict = load_profile_dictionary('profiledictionary.json')

    for svr_name, svr_def in servers.enabled().items():

        st = ElapsedTimer()  # start time for this server test

        url = svr_def["server_url"]
        user = svr_def["user"]
        password = svr_def["password"]
        default_namespace = svr_def["default_namespace"]
        print('=============== Connect '
              'name=%s, url=%s default_namespace=%s sec=%s =='
              '=============' %
              (svr_name, url, default_namespace, st.elapsed_time()))
        conn = connect(svr_name, url, user, password, default_namespace,
                       debug=True)
        if conn:
            print('============Connected: name=%s url=%s default_ns=%s' %
                  (svr_name, url, default_namespace))

            server = pywbem.WBEMServer(conn)
            server_general_info[svr_name] = server
            org_vm = pywbem.ValueMapping.for_property(
                server, server.interop_ns,
                'CIM_RegisteredProfile',
                'RegisteredOrganization')

            print("POSSIBLE_TARGET_AUTONOMOUS_PROFILES=%s" %
                  possible_target_profiles(svr_name,
                                           server,
                                           all_profiles_dict,
                                           org_vm,
                                           autonomous=True,
                                           output='name'))

            auto_paths = possible_target_profiles(svr_name,
                                                  server,
                                                  all_profiles_dict,
                                                  org_vm,
                                                  autonomous=True,
                                                  output='path')
            comp_paths = possible_target_profiles(svr_name,
                                                  server,
                                                  all_profiles_dict,
                                                  org_vm,
                                                  autonomous=False,
                                                  output='path')

            show_count_associators(svr_name, server, org_vm)
            cim_ref_direction = None
            ps = None
            try:
                for pp in auto_paths:
                    try:
                        print('CALL DETERMINE %s' % pp)
                        dir1 = determine_cimrefrence_direction(
                            svr_name,
                            server,
                            possible_autonomous_profiles=[pp],
                            possible_component_profiles=None)
                        print('AUTOSVR=%s DIR=%s' % (svr_name, dir1))
                        if dir1:
                            ps = 'OUTPUT %s %s' % (dir1, pp)
                        else:
                            ps = 'NONE RTND %s' % pp
                    except Exception as ex:
                        print('DETERMINE_DIR FAILED exception=%s' % ex)
                    try:
                        dir2 = determine_cimrefrence_direction(
                            svr_name,
                            server,
                            possible_autonomous_profiles=None,
                            possible_component_profiles=comp_paths)
                        print('COMPSVR=%s DIR=%s' % (svr_name, dir2))
                    except Exception as ex:
                        print('DETERMINE_DIR2 FAILED exception=%s' % ex)
                    try:
                        dir3 = determine_cimrefrence_direction(
                            svr_name,
                            server,
                            possible_autonomous_profiles=auto_paths,
                            possible_component_profiles=comp_paths)
                        print('BOTHSVR=%s DIR=%s' % (svr_name, dir3))
                    except Exception as ex:
                        print('DETERMINE_DIR3 FAILED exception=%s' % ex)

                if dir1 == dir2 == dir3:
                    ps = 'PASSED %s' % dir1
                    cim_ref_direction = dir1
                else:
                    ps = 'FAILED  Results inconsistend. ' \
                         'dir1 %s dir2 %s dir3 %s' % (dir1, dir2, dir3)

                test_results.append('%s %s time=%s' % (svr_name, ps,
                                                       st.elapsed_time()))
                if cim_ref_direction:
                    test_get_central_instances(
                        svr_name, server, all_profiles_dict,
                        org_vm, direction=cim_ref_direction)

            except Exception as ex:
                test_results.append('%s FAILED(Exception %s) time=%s' %
                                    (svr_name, ex, st.elapsed_time()))
                continue


    print('===============SUMMARY RESULTS time %s' % st.elapsed_time())

    print('DIRECTION TEST RESULTS')
    for item in test_results:
        print(item)

    title = 'Summary of good/error get_central instance rtns for each server.' \
            'Excludes servers that did not pass the direction test'
    headers = ['Server Name', 'Profiles', 'Good rtns', 'Error rtns']
    print_table(title, headers, GET_CENTRAL_INST_ROWS, sort_columns=0)

    title = 'GET_CENTRAL_INSTANCE ERRORS. List of all Error returns from ' \
            'get_central_instances test'
    rows = []
    for svr_name, errors in GET_CENTRAL_INST_ERRS.items():
        for data in errors:
            rows.append([svr_name, data[0], textwrap.fill(str(data[1]), 60)])
    print_table(title, headers, rows, sort_columns=0)

    title = 'Table of Profile characteristics (i.e. profile_dict)'
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
    print("")


if __name__ == '__main__':
    main()
