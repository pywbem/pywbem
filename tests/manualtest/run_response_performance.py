#!/usr/bin/env python
"""
Test cases for tupletree module and Unicode/XML check functions.
"""

from __future__ import absolute_import, print_function

import sys as _sys
import os as _os
import time
import argparse as _argparse
import datetime
import pstats
import cProfile
import locale
from tabulate import tabulate
from pyinstrument import Profiler
import six


from pywbem import tupletree, tupleparse
from pywbem._cliutils import SmartFormatter as _SmartFormatter

if six.PY2:
    import codecs  # pylint: disable=wrong-import-order

# default input arguments.  These are small so a user who
# just calls the code does not fall into long run.
DEFAULT_RESPONSE_SIZE = [100, 1000]
DEFAULT_RESPONSE_COUNT = [100, 1000]
DEFAULT_TOP_N_ROWS = 20
DEFAULT_RUNID = 'default'


PROFILE_OUT_PREFIX = 'perf'
PROFILE_DUMP_SUFFIX = 'profile'
PROFILE_LOG_SUFFIX = 'out'


STDOUT_ENCODING = getattr(_sys.stdout, 'encoding', None)
if not STDOUT_ENCODING:
    STDOUT_ENCODING = locale.getpreferredencoding()
if not STDOUT_ENCODING:
    STDOUT_ENCODING = 'utf-8'


def _uprint(dest, text):  # pylint: disable=too-many-branches
    """
    Write text to dest, adding a newline character.

    Text may be a unicode string, or a byte string in UTF-8 encoding.
    It must not be None.

    If dest is None, the text is encoded to a codepage suitable for the current
    stdout and is written to stdout.

    Otherwise, dest must be a file path, and the text is encoded to a UTF-8
    Byte sequence and is appended to the file (opening and closing the file).
    """
    if isinstance(text, six.text_type):
        text = text + u'\n'
    elif isinstance(text, six.binary_type):
        text = text + b'\n'
    else:
        raise TypeError(
            "text must be a unicode or byte string, but is {0}".
            format(type(text)))
    if dest is None:
        if six.PY2:
            # On py2, stdout.write() requires byte strings
            if isinstance(text, six.text_type):
                text = text.encode(STDOUT_ENCODING, 'replace')
        else:
            # On py3, stdout.write() requires unicode strings
            if isinstance(text, six.binary_type):
                text = text.decode('utf-8')
        _sys.stdout.write(text)

    elif isinstance(dest, (six.text_type, six.binary_type)):
        if isinstance(text, six.text_type):
            open_kwargs = dict(mode='a', encoding='utf-8')
        else:
            open_kwargs = dict(mode='ab')
        if six.PY2:
            # Open with codecs to be able to set text mode
            with codecs.open(dest, **open_kwargs) as fn:
                fn.write(text)
        else:
            with open(dest, **open_kwargs) as fn:
                fn.write(text)
    else:
        raise TypeError(
            "dest must be None or a string, but is {0}".
            format(type(text)))


class _PywbemCustomFormatter(_SmartFormatter,
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
    pass  # pylint: disable=unnecessary-pass


TEMPLATE = u"""\n<VALUE.NAMEDINSTANCE>
<INSTANCENAME CLASSNAME="TST_ResponseStressTestCxx">
  <KEYBINDING NAME="Id"><KEYVALUE VALUETYPE="string">{0}</KEYVALUE>
    </KEYBINDING></INSTANCENAME><INSTANCE CLASSNAME="PERFTEST_Class" >
  <PROPERTY NAME="Id" TYPE="string"><VALUE>{0}</VALUE></PROPERTY>
  <PROPERTY NAME="SequenceNumber"  TYPE="uint64"><VALUE>{0}</VALUE></PROPERTY>
  <PROPERTY NAME="S1"  TYPE="string"><VALUE>{2}</VALUE></PROPERTY>
  <PROPERTY.ARRAY NAME="A1" TYPE="string">
    <VALUE.ARRAY>
        {3}
    </VALUE.ARRAY>
  </PROPERTY.ARRAY>
</INSTANCE></VALUE.NAMEDINSTANCE>
"""
AVG_OBJ_SIZE = 0


def build_xml_obj(number, size):
    """
        Builds a single XML object
    """
    if size > 700:
        pattern = "abcdefghighjklmnopqrstuvwxyz01234567890"
    else:
        pattern = 'ab'

    # compute sizes for the s1_value and a1_value that will create an xml
    # of about the size defined by size

    # NOTE: This creates a minimum XML size of about 600 bytes just with the
    # overhead
    fill_size = size - len(TEMPLATE)
    if fill_size <= 0:
        fill_repeat = 1
    else:
        fill_repeat = int((fill_size / len(pattern)) / 2)

    s1_value = pattern * fill_repeat
    a1_value = "<VALUE>{0}</VALUE>\n".format(pattern) * fill_repeat

    return TEMPLATE.format(number, pattern, s1_value, a1_value)


AVG_RESPONSE_SIZE = 0


def create_xml_objs(count, size):
    """
    Create the set of CIMInstances XML that will go into the test XML
    """
    obj_size = []
    objstr = ""
    for number in range(0, count):
        obj = build_xml_obj(number, size)
        obj_size.append(len(obj))
        objstr += obj
    global AVG_RESPONSE_SIZE
    AVG_RESPONSE_SIZE = sum(obj_size) / len(obj_size)

    return objstr


def create_xml(count=1000, size=100):
    """
    Create the xml response message
    """
    xml = u'<?xml version="1.0" encoding="utf-8" ?>' \
          '<CIM CIMVERSION="2.0" DTDVERSION="2.0">' \
          '<MESSAGE ID="1001" PROTOCOLVERSION="1.0"><SIMPLERSP>' \
          '<IMETHODRESPONSE NAME="EnumerateInstances"><IRETURNVALUE>'

    xml += create_xml_objs(count=count, size=size)

    xml += '\n</IRETURNVALUE></IMETHODRESPONSE></SIMPLERSP></MESSAGE></CIM>'

    return xml, AVG_RESPONSE_SIZE


def execute_test_code(xml_string, profiler):
    """
    The test code to be executed. If a profiler is defined it is enabled
    just before the test code is executed and disabled just after the
    code is executed.
    """
    if profiler:
        if isinstance(profiler, cProfile.Profile):
            profiler.enable()
        elif isinstance(profiler, Profiler):
            profiler.start()

    # The code to be tested
    tt_ = tupletree.xml_to_tupletree_sax(xml_string, "TestData")
    tp = tupleparse.TupleParser()
    tp.parse_cim(tt_)

    if profiler:
        if isinstance(profiler, cProfile.Profile):
            profiler.disable()
        elif isinstance(profiler, Profiler):
            profiler.stop()


def execute_with_time(xml_string, profiler):
    # desc reserved for future tests.
    """
    Start time measurement and execute the test code.

    Returns the execution time
    """
    start_time = time.time()

    execute_test_code(xml_string, profiler)

    return time.time() - start_time


class ExecuteTests(object):
    # pylint: disable=too-few-public-methods, too-many-instance-attributes
    """
    Params class contains args parameters but lets us create new parameters
    or modify the existing paramete values.  argparse does not allow modifing
    created argument values.
    """
    def __init__(self, args):
        self.response_size = args.response_size
        self.response_count = args.response_count
        self.profiler = args.profiler
        self.verbose = args.verbose
        self.log = args.log
        self.runid = args.runid or DEFAULT_RUNID
        # insure no blanks in the text
        self.runid.replace(" ", "-")
        self.tbl_output_format = 'simple'

        self.file_datetime = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        # set logfile name if log option set. If the individual
        # option set, this will be modified
        if self.log:
            self.logfile = "{0}_{1}_{2}_{3}.{4}".format(
                PROFILE_OUT_PREFIX,
                self.runid,
                self.profiler,
                self.file_datetime,
                PROFILE_LOG_SUFFIX)
        else:
            self.logfile = None

        # define a dumpfile for the cprofile save.
        self.dumpfilename = "{0}_{1}_{2}_{3}.{4}".format(
            PROFILE_OUT_PREFIX,
            self.runid,
            self.profiler,
            self.file_datetime,
            PROFILE_DUMP_SUFFIX)

        # number of lines to display for cprofile output
        self.top_n_rows = args.top_n_rows

        # The following describes the columns in the cprofile output.
        # ncalls - how many times the function/method has been called (in case
        # the same function/method is being called recursively then ncalls has
        # two values eg. 120/20, where the first is the true number of calls,
        # while the second is the number of direct calls)

        # tottime - the total time in seconds excluding the time of other
        # functions/methods

        # percall - average time to execute function (per call)

        # cumtime - the total time in seconds includes the times of other
        # functions it calls

        self.cprofilesort = ["tottime", "ncalls"]

    def __repr__(self):
        return "ExecuteTests(runid={0}, response_size={1} response_count={2} " \
               "profiler={3} verbose={4}, log={5}, file_datetime={6}, " \
               "logfile={7}, dumpfilename={8}, top_n_rows={9}, " \
               "cprofilesort={10})".format(
                   self.runid,
                   self.response_size,
                   self.response_count,
                   self.profiler,
                   self.verbose,
                   self.log,
                   self.file_datetime,
                   self.logfile,
                   self.dumpfilename,
                   self.top_n_rows,
                   self.cprofilesort)

    def execute_raw_tests(self, profiler=None):
        """
        Execute the parse test for all of the input parameters defined in in
        self.response_count and self.response_size. This allows multiple tests
        to be executed
        """
        table_rows = []
        for response_size in self.response_size:
            for response_count in self.response_count:
                xml, avg_resp_size = create_xml(response_count, response_size)
                execution_time = execute_with_time(xml, profiler=profiler)
                row = (response_size,
                       int(avg_resp_size),
                       response_count,
                       len(xml),
                       "{0:5.2f}".format(execution_time),
                       int(response_count / execution_time))
                table_rows.append(row)
        return table_rows

    def execute_cprofile_tests(self):
        """
        Execute the parse test for all of the input parameters. The cProfiler
        allows the profiling to be enabled and disabled so the profiler object
        is passed on to the execution component
        """

        profiler = cProfile.Profile()

        table_rows = self.execute_raw_tests(profiler=profiler)

        # Define stats output.
        ps = pstats.Stats(profiler, stream=_sys.stdout)

        try:
            ps.dump_stats(self.dumpfilename)
        except Exception as ex:  # pylint: disable=broad-except
            print('cProfiler dump stats exception %s %s. Ignored' %
                  (ex.__class__.__name__, ex))

        # modify stats for display and output to stdout
        ps.strip_dirs()
        ps.sort_stats(*self.cprofilesort)
        ps.print_stats(self.top_n_rows)

        # if dest defined, output to file defined by dest
        if self.logfile:
            with open(self.logfile, 'w') as stream:
                ps = pstats.Stats(profiler, stream=stream)
                ps.strip_dirs()
                ps.sort_stats(*self.cprofilesort)
                ps.print_stats(self.top_n_rows)

        return table_rows

    def execute_pyinstrument_tests(self):
        """Execute the parse test for all of the input parameters in args.
        Since this profiler has no enable or disable concept the profiler
        must be enabled for the complete test and the results output
        At the end of the test, the profiler results are printed
        """
        table_rows = []
        profiler = Profiler()

        table_rows = self.execute_raw_tests(profiler)

        _uprint(None, profiler.output_text(unicode=True, color=True))
        if self.logfile:
            _uprint(self.logfile, profiler.output_text(unicode=True,
                                                       color=True))
        return table_rows

    def execute_tests(self):
        """Execute the test associated with profiler input argument."""

        if self.profiler == 'none':
            table_rows = self.execute_raw_tests()
        elif self.profiler == 'pyinst':
            table_rows = self.execute_pyinstrument_tests()
        elif self.profiler == 'cprofile':
            table_rows = self.execute_cprofile_tests()
        else:
            raise RuntimeError('profiler arg %s invalid. '
                               'Should never occur' % self.profiler)

        # build and output results report
        header = ["Exp inst\nsize",
                  "Act inst\nsize",
                  "Response\nCount",
                  "XML\nsize",
                  "Parse time\nsec.",
                  "Instances\nper sec"]
        title = 'Results: profile={0}, response_counts={1},\n   ' \
                'response-sizes={2}, runid={3} {4}'.format(self.profiler,
                                                           self.response_count,
                                                           self.response_size,
                                                           self.runid,
                                                           self.file_datetime)
        table = tabulate(table_rows, header, tablefmt=self.tbl_output_format)

        # print statistics to terminal
        print("")
        _uprint(None, title)
        _uprint(None, table)

        # print statistics to log file
        if self.logfile:
            _uprint(self.logfile, title)
            _uprint(self.logfile, table)


def execute_individual_tests(args):
    """
    Execute the test with separate trace for each test.  This  creates
    a Params object for each set of response_size and response_count so
    that  tests can be executed completely individually.
    """
    # create a params object
    tests = ExecuteTests(args)

    # modify the test specific variables of the params and execute the test
    # with each
    for response_size in args.response_size:
        for response_count in args.response_count:
            # define a dump file name for each execution
            tests.response_count = [response_count]
            tests.response_size = [response_size]
            tests.dumpfilename = "{0}_{1}_{2}_{3}_{4}_{5}.{6}".format(
                PROFILE_OUT_PREFIX,
                tests.runid,
                args.profiler,
                tests.file_datetime,
                response_count,
                response_size,
                PROFILE_DUMP_SUFFIX)

            # If a log destination is defined modify the dump file name
            # for each individual  test suffixes the name with the
            # response_size and response_count
            if args.log:
                tests.logfile = "{0}_{1}_{2}_{3}_{4}_{5}.{6}".format(
                    PROFILE_OUT_PREFIX,
                    tests.runid,
                    args.profiler,
                    tests.file_datetime,
                    response_count,
                    response_size,
                    PROFILE_LOG_SUFFIX)

            tests.execute_tests()


def parse_args():
    """
    Parse the input arguments and return the args dictionary
    """
    prog = _os.path.basename(_sys.argv[0])
    usage = '%(prog)s [options]'
    # pylint: disable=line-too-long
    desc = """
This script provide performance information on the TupleParse class.  This  is
a development test to be used to improve this code and reduce the XML response
execution time.

It creates XML for an EnumerateInstances response with the number of
instances (response-count) and the approximate XML size of each instance
(response-size) defined by the input arguments.  It then executes the parsing
sequence (tupletree, tupleparse) against this xml,records the execution time.

The input arguments for response count and response size may each specify
multiple values (ex --response-count 100 100 1000). In this case tests are
executed for all variations of each of the arguments.

If a profiler is specified (--profiler input parameter) it executes the
profile for all of the tests and displays the profile results before outputting
the execution time for each test.

NOTE: Running with a profiler heavily affects the runtime.
"""
    epilog = """
Examples:
  %s

     Execute a minimal test with default input arguments and display time to
     execute. It does not use either of the profilers.

  %s  -p cprofile --response-count 10000 20000 --response-size 100 1000

     Execute the test for all combinations of response counts of 10,000 and
     20,000 and for response sizes of 500 and 1000 bytes using cprofile
     profiler to generate and output a profile of the operation.
""" % (prog, prog)  # noqa: E501
# pylint: enable=line-too-long

    argparser = _argparse.ArgumentParser(
        prog=prog, usage=usage, description=desc, epilog=epilog,
        add_help=False, formatter_class=_PywbemCustomFormatter)

    tests_arggroup = argparser.add_argument_group(
        'Test related options',
        'Specify parameters of the test')

    tests_arggroup.add_argument(
        '-p', '--profiler',
        dest='profiler', choices=['none', 'pyinst', 'cprofile'],
        action='store', default='none',
        help='R|Defines the profile package used for the test.\n'
             '   * `pyinst` uses pyinstrument uses a statistical \n'
             '     capture, and displays a tree of the python stack\n'
             '     execution times.\n'
             '   * `cprofile` uses cProfile and generates a table of\n'
             '     counts.\n'
             '   * `none` runs without profiler.\n'
             ' Default: %s' % "none")

    tests_arggroup.add_argument(
        '-c', '--response-count', dest='response_count', nargs='+',
        metavar='ints', type=int,
        action='store', default=DEFAULT_RESPONSE_COUNT,
        help='R|The number of instances that will be returned for each\n'
             'test in the form for each test. May be multiple \n'
             'integers. The test will be executed for each\n'
             'response-size and each value defined. The format is:\n'
             '   -c 1000 10000 100000\n'
             'Default: %s' % DEFAULT_RESPONSE_COUNT)

    tests_arggroup.add_argument(
        '-s', '--response-size', dest='response_size', nargs='+',
        metavar='ints', type=int,
        action='store', default=DEFAULT_RESPONSE_SIZE,
        help='R|The response sizes that will be tested. This defines\n'
             'the size of the XML for each object in the response\n'
             'in bytes. May be multiple integers. the test will be\n'
             'executed for the combination of each response-count\n'
             'and each value provided. The format is:\n'
             '   -s 100 200 300\n'
             'Default: %s' % DEFAULT_RESPONSE_SIZE)

    tests_arggroup.add_argument(
        '-n', '--top-n-rows', dest='top_n_rows',
        metavar='int', type=int,
        action='store', default=DEFAULT_TOP_N_ROWS,
        help='R|The number of rows of profile data for the cprofile\n'
             'display. This is the top n tottime results.\n'
             'Default: %s' % DEFAULT_TOP_N_ROWS)

    tests_arggroup.add_argument(
        '-r', '--runid', dest='runid',
        metavar='text', type=str,
        action='store', default=DEFAULT_RUNID,
        help='R|A string that is concatenated into each filename\n'
             'created by the script.\n'
             'Default: %s' % DEFAULT_RUNID)

    tests_arggroup.add_argument(
        '-i', '--individual', dest='individual',
        action='store_true', default=False,
        help='Run each of the response_count/response_size tests as a '
             'completely individual test with separate profile and separate '
             'output displays and log files.')

    general_arggroup = argparser.add_argument_group(
        'General options')

    general_arggroup.add_argument(
        '-l', '--log', dest='log',
        action='store_true', default=False,
        help='Log the trace for each either the complete execution or each '
             'test if --individual set to a log file.')

    general_arggroup.add_argument(
        '-v', '--verbose', dest='verbose',
        action='store_true', default=False,
        help='Print more messages while processing. Displays detailed counts'
             'for each pull operation.')
    general_arggroup.add_argument(
        '-h', '--help', action='help',
        help='Show this help message and exit')

    args = argparser.parse_args()

    if args.top_n_rows <= 0:
        argparser.error("top-n-rows must be postive integer. "
                        "{0} not allowed".format(args.top_n_rows))

    return args


def main():
    """
        Parse arguments, execute tests defined by the arguments, and
        display results.
    """
    args = parse_args()

    print('Starting profiler={0}, response-count={1} response-size={2} '
          'runid={3} log={4}'.format(args.profiler, args.response_count,
                                     args.response_size, args.runid,
                                     args.log))

    if args.individual:
        execute_individual_tests(args)
    else:
        tests = ExecuteTests(args)
        tests.execute_tests()


if __name__ == '__main__':
    main()
