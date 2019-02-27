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
import six
from tabulate import tabulate
from pyinstrument import Profiler

from pywbem import tupletree, tupleparse
from pywbem._cliutils import SmartFormatter as _SmartFormatter

# default input arguments.  These are small so a user who
# just calls the code does not fall into long run.
DEFAULT_RESPONSE_SIZE = [100, 1000]
DEFAULT_RESPONSE_COUNT = [100, 1000]


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

    # print("XML len %s\n%s" % (len(xml), xml))
    return xml


def execute_test_code(xml_string):
    """
    The test code to be executed.
    """
    tt_ = tupletree.xml_to_tupletree_sax(xml_string, "TestData")
    tp = tupleparse.TupleParser()
    tp.parse_cim(tt_)


def test_parse(desc, xml_string, condition):
    # pylint: disable=no-self-use. desc reserved for future tests.
    """
    Test xml_to_tupletree_sax() and tupleparse with input string. If condition
    is not True the test is bypassed.

     desc reserved for future tests.
    """

    if not condition:
        print("Condition for test case not met")
        return

    assert isinstance(xml_string, six.text_type)

    start_time = time.time()

    execute_test_code(xml_string)

    execution_time = time.time() - start_time
    return execution_time, len(xml_string)


def execute_raw_tests(args):
    """Execute the parse test for all of the input parameters."""
    table_rows = []
    for response_size in args.response_size:
        for response_count in args.response_count:
            rtn, size = test_parse('', create_xml(response_count,
                                   response_size),
                                   True)
            row = (response_size,
                   int(size / response_count),
                   response_count,
                   rtn)
            table_rows.append(row)
    return table_rows


def execute_cprofile_tests(args):
    """Execute the parse test for all of the input parameters."""

    pr = cProfile.Profile()
    pr.enable()  # this is the profiling section
    table_rows = execute_raw_tests(args)
    pr.disable()
    ps = pstats.Stats(pr, stream=_sys.stdout)
    ps.dump_stats("cprofilerstats.profile")
    ps.strip_dirs()
    ps.sort_stats("tottime", "ncalls")
    ps.print_stats(20)

    return table_rows


def execute_pyinstrument_tests(args):
    """Execute the parse test for all of the input parameters."""
    table_rows = []
    profiler = Profiler()
    profiler.start()

    table_rows = execute_raw_tests(args)

    profiler.stop()
    print(profiler.output_text(unicode=True, color=True))
    return table_rows


def execute_tests(args):
    """Execute the test associated with profiletype input argument."""
    if args.profiletype == 'none':
        return execute_raw_tests(args)
    elif args.profiletype == 'stack':
        return execute_pyinstrument_tests(args)
    elif args.profiletype == 'table':
        return execute_cprofile_tests(args)
    else:
        print('profiletype arg {0} invalid. Should never occur'.format(
              args.profiletype))
        raise RuntimeError('profiletype arg %s invalid. '
                           'Should never occur' % args.profiletype)


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

If the stack or table profiletype definitons are supplied it executes the
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
        '-p', '--profiletype',
        dest='profiletype', choices=['none', 'stack', 'table'],
        action='store', default='none',
        help='R|Defines the profile code used for the test.\n'
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

    general_arggroup = argparser.add_argument_group(
        'General options')

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


def main():
    """
        Parse arguments, execute tests defined by the arguments, and
        display results.
    """
    args = parse_args()

    table_rows = execute_tests(args)

    header = ["Exp Response\nSize Bytes",
              "Act Response\nSize (Bytes)",
              "Response\nCount",
              "Parse time\nsec.)"]
    print('Results: profile={0} response_counts={1}\n   response-sizes={2} {3}'.
          format(args.profiletype, args.response_count, args.response_size,
                 datetime.datetime.now()))
    print(tabulate(table_rows, header, tablefmt="grid"))


if __name__ == '__main__':
    main()
