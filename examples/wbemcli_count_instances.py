"""
    Pywbem wbemcli scriptlet that counts classes and instances in a WBEMServer.

    This class explored the complete server and retrieve all
    namespaces, then all classes, then all instances for each class and
    displays the results.

    It includes an ignore list that ignores selected classes and another that
    will ignore selected namespaces.
"""
from collections import defaultdict
import six

from pywbem import WBEMServer, CIMError, ConnectionError, \
    TimeoutError

# Create the server and save in global SERVER
print('Find total classes and instances for all namespaces:\n')

SERVER = WBEMServer(CONN)

# The following are classes where for some reason the enumerateinstancenanes
# fails in the test version of Pegasus. Typically they cause significant
# failures if queried, i.e kills pegasus. The classes in this list are ignored
# during the scan.
peg_ignore_list = ['PG_User', 'CWS_DirectoryContainsFile_CXX',
                   'PG_Authorization',
                   'TestCMPI_Fail_2', 'TestCMPI_Fail_3', 'TestCMPI_Fail_4',
                   'TST_FaultyInstance', 'CIM_Error',
                   'CIM_InstMethodCall', 'PG_InstMethodIndication',
                   'CIM_Indication', 'CIM_InstIndication', 'PG_EmbeddedError']

# Any namespaces in this list are ignored.
ignore_namespaces_list = []

# list of ignored classes including namespaces
ignored_classes = []
# list of failed classes including namespace
failed_classes = []

# count of total ignored classes, instances, and failures.
total_classes = 0
total_instances = 0
total_errors = 0

table_print_format = '%9s %11s %-30s %5s'

# prepare and print table header with column names
max_ns_len = 20
table_hdr = table_print_format % ('# classes',
                                  '# instances',
                                  'namespace/classname',
                                  '# Errors')
print(table_hdr)
print('=' * len(table_hdr))

# filter namespaces to be ignored
namespaces = [ns
              for ns in sorted(SERVER.namespaces)
              if ns not in ignore_namespaces_list]

# set max namespace length for output table
max_ns_len2 = len(max(namespaces, key=len)) + 5

for ns in namespaces:
    classnames = ecn(ns=ns, di=True)
    ns_error_count = 0
    # this accumulates instance counts across the namespace
    # key is classname, value is total instance count
    inst_dict = defaultdict(int)
    assoc_d = {}

    # build filtered classname list
    classnames = [classname
                  for classname in classnames
                  if classname not in peg_ignore_list]

    for classname in classnames:
        cl = gc(classname, ns=ns)
        assoc_d[classname] = True if 'Association' in cl.qualifiers else False

        try:
            instnames = ein(ns=ns, cn=classname)
            for instname in instnames:
                # filter to count only instances in this class, not subclasses
                if instname.classname == classname:
                    inst_dict[classname] += 1
                    total_instances += len(instnames)
        except CIMError as ce:
            failed_classes.append((classname, ns, ce))
            ns_error_count += 1
        except TimeoutError as te:
            print('Timeout Error ns: %s class: %s err: %s. Quitting' %
                  (ns, classname, te))
            quit(2)
        except ConnectionError as ce:
            print('Connection Error ns: %s class: %s err: %s. Quitting' %
                  (ns, classname, ce))
            quit(2)
        except Exception as exc:
            ns_error_count += 1
            print('Exception error ns %s class %s, err %s. Quitting' %
                  (ns, classname, exc))
            quit(3)

    # display results for this namespace
    print(table_print_format %
          (len(classnames), sum(six.itervalues(inst_dict)), ns, ns_error_count))

    # display the counts per instance. Note that this is NOT the same
    # as ein returns but the instance count for this class alone.
    for classname, inst_count in six.iteritems(inst_dict):
        if inst_count != 0:
            assoc_flag = '(*)' if assoc_d[classname] else "   "
            classname = '%s %s' % (classname, assoc_flag)
            print('%9s %11s %-30s %5s' % ("", inst_count, classname, ""))

        total_classes += len(classnames)
    total_errors += ns_error_count

print('=' * len(table_hdr))
print(table_print_format %
      (len(SERVER.namespaces), total_classes, '', total_errors))

if ignored_classes:
    print('List of classes ignored:')
    for cn in ignored_classes:
        print('  %s' % cn)

if failed_classes:
    print('List of classes That failed with CIMError exception:')
    for item in failed_classes:
        print('  %s:%s, err %s' % (item[0], item[1], item[2].status_code_name))

print('Success. Quit Scriplet. Quiting wbemcli')
quit()
