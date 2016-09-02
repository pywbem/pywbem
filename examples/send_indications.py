#!/usr/bin/env python

"""
    Python script to create and send indications to a listener
"""

from __future__ import print_function, absolute_import
import sys
from time import time
import datetime
import argparse as _argparse
from pywbem._cliutils import SmartFormatter as _SmartFormatter
import requests
import re
from random import randint

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

        
def create_indication_data(msg_id, sequence_number, delta_time, protocol_ver):
    data_template = """<?xml version="1.0" encoding="utf-8" ?>
    <CIM CIMVERSION="2.0" DTDVERSION="2.4">
      <MESSAGE ID="%(msg_id)s" PROTOCOLVERSION="%(protocol_ver)s">
        <SIMPLEEXPREQ>
          <EXPMETHODCALL NAME="ExportIndication">
            <EXPPARAMVALUE NAME="NewIndication">
              <INSTANCE CLASSNAME="CIM_AlertIndication">
                <PROPERTY NAME="Severity" TYPE="string">
                  <VALUE>high</VALUE>
                </PROPERTY>
                <PROPERTY NAME="SequenceNumber" TYPE="string">
                  <VALUE>%(sequence_number)s</VALUE>
                </PROPERTY>
                <PROPERTY NAME="DELTA_TIME" TYPE="string">
                  <VALUE>%(delta_time)s</VALUE>
                </PROPERTY>
              </INSTANCE>
            </EXPPARAMVALUE>
          </EXPMETHODCALL>
        </SIMPLEEXPREQ>
      </MESSAGE>
    </CIM>"""

    data = {'sequence_number' : sequence_number, 'delta_time' : delta_time,
            'protocol_ver' : protocol_ver, 'msg_id' : msg_id}
    return data_template%data


def send_indication(url, headers, payload, verbose):

    try:
        response = requests.post(url, headers=headers, data=payload, timeout=4)
    except Exception as ex:
        print('Exception %s' % ex)
        return False

    if verbose:
        print('\nResponse code=%s headers=%s data=%s' % (response.status_code,
                                                         response.headers,
                                                         response.text))

    return True if(response.status_code == 200) else False

def get_args():
    """
        Get the command line arguments. use --help to get info on cmd line
        arguments
    """

    prog = "sendIndications"
    usage = '%(prog)s [options] listener-url'
    desc = 'Send indications to a listener.'
    epilog = """
Examples:
  %s https://127.0.0.1 -p 5000 -u sheldon -p penny

  %s http://[2001:db8::1234-eth0] -(http port 5988 ipv6, zone id eth0)
""" % (prog, prog)

    argparser = _argparse.ArgumentParser(
        prog=prog, usage=usage, description=desc, epilog=epilog,
        add_help=False, formatter_class=_SmartFormatter)

    pos_arggroup = argparser.add_argument_group(
        'Positional arguments')

    pos_arggroup.add_argument(
        'url', metavar='url', nargs='?', default='http://127.0.0.1',
        help='Optional url of listener '
             'If supplied, must be schema+address[:port]. Schema determines ' \
             ' whether http or https are used. Port may be defined in url ' \
             'or with -p option. If not included default port = 5000')

    general_arggroup = argparser.add_argument_group('General options')
    general_arggroup.add_argument(
        '-v', '--verbose', dest='verbose',
        action='store_true', default=False,
        help='Print more messages while processing')

    general_arggroup.add_argument(
        '--listenerPort', '-p', default=5000,
        metavar="port",
        type=int,
        help='Integer argument defines listener port.')
    general_arggroup.add_argument(
        '--count', '-c', default=1,
        metavar='integer',
        type=int,
        help='Integer argument defines number of indications to send.')

    general_arggroup.add_argument(
        '-h', '--help', action='help',
        help='Show this help message and exit')

    security_arggroup = argparser.add_argument_group(
        'Connection security related options',
        'Specify user name and password or certificates and keys')
    security_arggroup.add_argument(
        '--certfile', dest='cert_file', metavar='certfile',
        help='R|Client certificate file for authenticating with the\n' \
             'WBEM server. If option specified the client attempts\n' \
             'to execute mutual authentication.\n'
             'Default: Simple authentication.')
    security_arggroup.add_argument(
        '--keyfile', dest='key_file', metavar='keyfile',
        help='R|Client private key file for authenticating with the\n' \
             'WBEM server. Not required if private key is part of the\n' \
             'certfile option. Not allowed if no certfile option.\n' \
             'Default: No client key file. Client private key should\n' \
             'then be part  of the certfile')

    args = argparser.parse_args()

    if re.match('^http', args.url) is None:
        print('ERROR: url must include schema. received %s' % args.url)
        sys.exit(1)

    if args.verbose:
        print('args %s' % args)

    return args

def main():
    """
    """
    opts = get_args()

    start_time = time()

    full_url = opts.url
    if opts.listenerPort is not None:
        full_url = '%s:%s' % (opts.url, opts.listenerPort)

    if opts.verbose:
        print('full_url=%s' % full_url)

    cim_protocol_version = '1.4'

    headers = {'content-type' : 'application/xml; charset=utf-8',
               'CIMExport' : 'MethodRequest',
               'CIMExportMethod' : 'ExportIndication',
               'Accept-Encoding' : 'Identity',
               'CIMProtocolVersion' : cim_protocol_version}
    # includes accept-encoding because of requests issue.  He supplies it if
    # we don't TOD try None

    delta_time = time() - start_time
    rand_base = randint(1, 1000)
    timer = ElapsedTimer()
    for i in range(opts.count):

        msg_id = '%s' % (i + rand_base)
        payload = create_indication_data(msg_id, i, delta_time,
                                         cim_protocol_version)

        if opts.verbose:
            print('headers=%s\n\npayload=%s' % (headers, payload))

        success = send_indication(full_url, headers, payload, opts.verbose)

        if success:
            if opts.verbose:
                print('sent # %s' % i)
            else:
                if i % 100 == 0:
                    sys.stdout.write('.')
                    sys.stdout.flush()
        else:
            print('Error return from send. Terminating.')
            return
    endtime = timer.elapsed_sec()
    print('Sent %s in %s sec or %.2f ind/sec' % (opts.count, endtime ,
                                               (opts.count/endtime)))

if __name__ == '__main__':
    sys.exit(main())
