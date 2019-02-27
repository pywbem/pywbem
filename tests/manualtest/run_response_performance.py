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

# Dictionary
XML_DICTIONARY = {}

PROFILE_DUMP_MAIN_NAME = 'cprofilerstats'
PROFILE_DUMP_SUFFIX = '.profile'
PROFILE_DUMP_NAME = PROFILE_DUMP_MAIN_NAME + PROFILE_DUMP_SUFFIX


STDOUT_ENCODING = getattr(_sys.stdout, 'encoding', None)
if not STDOUT_ENCODING:
    STDOUT_ENCODING = locale.getpreferredencoding()
if not STDOUT_ENCODING:
    STDOUT_ENCODING = 'utf-8'


def _uprint(dest, text):
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
            with codecs.open(dest, **open_kwargs) as f:
                f.write(text)
        else:
            with open(dest, **open_kwargs) as f:
                f.write(text)
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
    pass


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

    global AVG_OBJ_SIZE
    AVG_OBJ_SIZE = sum(obj_size) / len(obj_size)

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

    return xml


def execute_test_code(xml_string, profiler):
    """
    The test code to be executed.
    """
    if profiler:
        profiler.enable()

    tt_ = tupletree.xml_to_tupletree_sax(xml_string, "TestData")
    tp = tupleparse.TupleParser()
    tp.parse_cim(tt_)

    if profiler:
        profiler.disable()


def execute_with_time(xml_string, profiler):
    # desc reserved for future tests.
    """
    Start time measurement and execute the test code.

     desc reserved for future tests.
    """
    start_time = time.time()

    execute_test_code(xml_string, profiler)

    execution_time = time.time() - start_time
    return execution_time


def execute_raw_tests(params, profiler=None):
    """
    Execute the parse test for all of the input parameters defined in
    args. This allows multiple tests to be executed
    We want to reduce this to the minimum code since everything here is
    profiled
    """
    table_rows = []
    for response_size in params.response_size:
        for response_count in params.response_count:
            key = key = "%s:%s" % (response_count, response_size)
            xml = XML_DICTIONARY[key]
            execution_time = execute_with_time(xml, profiler=profiler)
            row = (response_size,
                   int(len(xml) / response_count),
                   response_count,
                   execution_time)
            table_rows.append(row)
    return table_rows


def execute_cprofile_tests(params, dest):
    """
    Execute the parse test for all of the input parameters. The cProfiler
    allows the profiling to be enabled and disabled so the profiler object
    is passed on to the execution component
    """

    pr = cProfile.Profile()

    table_rows = execute_raw_tests(params, profiler=pr)

    # Output statistics
    ps = pstats.Stats(pr, stream=_sys.stdout)

    try:
        ps.dump_stats(PROFILE_DUMP_NAME)
    except Exception as ex:
        print('cProfiler dump stats exception %s %s. Ignored' %
              (ex.__class__.__name__, ex))
    ps.strip_dirs()
    ps.sort_stats("tottime", "ncalls")

    try:
        ps.print_stats(20)
    except Exception as ex:
        print('cProfiler print_stats exception %s %s. Ignored' %
              (ex.__class__.__name__, ex))

    if dest:
        with open(dest, 'w') as stream:
            stats = pstats.Stats(dest, stream=stream)
            stats.print_stats(20)

    return table_rows


def execute_pyinstrument_tests(params, dest):
    """Execute the parse test for all of the input parameters in args.
    Since this profiler has no enable or disable concept the profiler
    must be enabled for the complete test and the results output
    At the end of the test, the profiler results are printed
    """
    table_rows = []
    profiler = Profiler()
    profiler.start()

    table_rows = execute_raw_tests(params)

    profiler.stop()
    _uprint(None, profiler.output_text(unicode=True, color=True))

    if dest:
        _uprint(dest, profiler.output_text(unicode=True, color=True))
    return table_rows


def execute_individual_tests(args):
    """
    Execute the test with separate trace for each test.  This  creates
    a Params object for each set of response_size and response_count so
    that  tests can be executed completely individually.
    """
    for response_size in args.response_size:
        for response_count in args.response_count:
            # Create new Params with a single set of values from args
            params = Params(args)
            params.response_size = [response_size]
            params.response_count = [response_count]

            # modify the dump file name for each individual  test
            # suffixes the name with the response_size and response_count
            global PROFILE_DUMP_NAME
            PROFILE_DUMP_NAME = "%s_%s_%s%s" % (PROFILE_DUMP_MAIN_NAME,
                                                response_size, response_count,
                                                PROFILE_DUMP_SUFFIX)
            dt = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = "perf_%s_%s_%s_%s.log" % (dt, args.profiler, response_count,
                                             response_size)
            execute_tests(params, dest=dest)


def execute_tests(params, dest=None):
    """Execute the test associated with profiler input argument."""

    # build a dictionary of xml responses for the test. The removes this
    # from any possible profile tests.
    global XML_DICTIONARY
    XML_DICTIONARY = {}
    for response_size in params.response_size:
        for response_count in params.response_count:
            xml = create_xml(response_count, response_size)
            key = "%s:%s" % (response_count, response_size)
            XML_DICTIONARY[key] = xml

    if params.profiler == 'none':
        table_rows = execute_raw_tests(params, dest)
    elif params.profiler == 'pyinst':
        table_rows = execute_pyinstrument_tests(params, dest)
    elif params.profiler == 'cprofile':
        table_rows = execute_cprofile_tests(params, dest)
    else:
        print('profiler arg {0} invalid. Should never occur'.format(
              params.profiler))
        raise RuntimeError('profiler arg %s invalid. '
                           'Should never occur' % params.profiler)

    header = ["Exp Response\nSize Bytes",
              "Act Response\nSize (Bytes)",
              "Response\nCount",
              "Parse time\nsec.)"]
    title = 'Results: profile={0}, response_counts={1},\n   ' \
            'response-sizes={2}, {3}'.format(params.profiler,
                                             params.response_count,
                                             params.response_size,
                                             datetime.datetime.now())
    table = tabulate(table_rows, header, tablefmt="grid")

    if params.log:
        if not dest:
            dt = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = "perf_%s_%s.log" % (dt, params.profiler)

        _uprint(dest, title)
        _uprint(dest, table)


def parse_args():
    """
    Parse the input arguments and return the args dictionary
    """
    prog = _os.path.basename(_sys.argv[0])
    usage = '%(prog)s [options]'
    # pylint: disable=line-too-long
    desc = """
Provide performance information on the TupleParse class.  This  is a development
test to be used to improve this code and reduce the XML response execution
time.

It creates the XML for an EnumerateInstances response with the number of
instances and the approximate XML size of each instance defined by the input
arguments.  It then executes the parsing sequence (tupletree, tupleparse)
against this xml,records the execution time.

If the stack or table profiler definitons are supplied it executes the
profile for all of the tests and displays the profile results before outputting
the execution time for each test.

NOTE: Running with a profiler heavily affects the runtime.
"""
    epilog = """
Examples:
  %s

     Execute a minimal test with default input arguments and display time to
     execute.

  %s  -p stack --response-count 10000 20000 --response-size 100 1000

     Execute the test with response counts of 10,000 and 20,000 and for response
     sizes of 500 and 1000 bytes using pyinstrument to generate and output
     a profile of the operation.
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
             '   * `stack` uses pyinstrument uses a statistical \n'
             '     capture, and displays a tree of the python stack\n'
             '     execution times.\n'
             '   * `table` uses cProfile and generates a table of\n'
             '     counts.\n'
             '   * `none` runs without profiler.\n'
             ' Default: %s' % "none")

    tests_arggroup.add_argument(
        '-c', '--response-count', dest='response_count', nargs='+',
        metavar='int', type=int,
        action='store', default=DEFAULT_RESPONSE_COUNT,
        help='R|The number of instances that will be returned for each\n'
             'test in the form for each test. May be multiple \n'
             'integers. The test will be executed for each value\n'
             'defined. The format is:\n'
             '  -r 1000 10000 100000\n'
             'Default: %s' % DEFAULT_RESPONSE_COUNT)

    tests_arggroup.add_argument(
        '-s', '--response-size', dest='response_size', nargs='+',
        metavar='int', type=int,
        action='store', default=DEFAULT_RESPONSE_SIZE,
        help='R|The response sizes that will be tested. This defines\n'
             'the size of the XML for each pbject in the response\n'
             'in bytes. May be multiple integers. the test will be\n'
             'executed for each value provided. The format is:\n'
             '   -R 100 200 300\n'
             'Default: %s' % DEFAULT_RESPONSE_SIZE)

    tests_arggroup.add_argument(
        '-i', '--individual', dest='individual',
        action='store_true', default=False,
        help='Run each of the response_count, response_size tests as a '
             'completely individual test, with separate profile and separate '
             'output table.')

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

    return args


class Params(object):  # pylint: disable=too-few-public-methods
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

    def __repr__(self):
        return "Params(response_size={0} response_count={1} profile={2} " \
               " verbose={3}, log={4})".format(self.response_size,
                                               self.response_count,
                                               self.profiler,
                                               self.verbose,
                                               self.log)


def main():
    """
        Parse arguments, execute tests defined by the arguments, and
        display results.
    """
    args = parse_args()

    params = Params(args)

    if args.individual:
        execute_individual_tests(args)
    else:
        execute_tests(params)


if __name__ == '__main__':
    main()
