#!/usr/bin/env python

"""
    Python script to create and send indications to a listener. Allows sending
    either http or https requests.  Note that the verify is forced to
    false for this version so that certificates or keys are not required.
"""

from __future__ import print_function, absolute_import
import sys
from time import time
import datetime
import argparse as _argparse
import re
from random import randint
from pywbem._cliutils import SmartFormatter as _SmartFormatter
import requests
# The following disables the urllib3 InsecureRequestWarning that gets
# generated for every send when server cert verification is disabled.
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
import xml.etree.ElementTree as ET
import json

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


def create_indication_data(msg_id, sequence_number, source_id, delta_time, \
                           protocol_ver):
    '''
    Create a singled indication XML from the template and the included
    sequence_number, delta_time, and protocol_ver

    Returns the completed indication XML
    '''

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
                <PROPERTY NAME="SourceId" TYPE="string">
                  <VALUE>%(source_id)s</VALUE>
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

    data = {'sequence_number' : sequence_number, 'source_id' : source_id,
            'delta_time' : delta_time, 'protocol_ver' : protocol_ver,
            'msg_id' : msg_id}
    return data_template%data


def send_indication(url, headers, payload, verbose, verify=None, keyfile=None,
                    timeout=4):
    '''
    Send indication using requests module.

    Parameters:

    url(:term:`string):
      listener url including scheme, host name, port

    headers:
      All headers for the request

    pyload:
       XML payload containing the indication

    verbose:
      Flag for verbose responses

    verify:
      Either False or file of cert for verification of host. Note that
      this combination is unique to the requests module in place of using
      a no_verification flag.

    keyfile:
      None if there is no client verification or either a single
      file containing the cert amd private key file or a pair of files
      containing both (key, cert)
    
    Returns:

      True if response code = 200. Otherwise False
    '''

    try:
        response = requests.post(url, headers=headers, data=payload,
                                 timeout=timeout,
                                 verify=verify)

    except Exception as ex:
        print('Exception %s' % ex)
        return False

    # validate response status code and xml
    if verbose or response.status_code != 200:
        print('\nResponse code=%s headers=%s data=%s' % (response.status_code,
                                                         response.headers,
                                                         response.text))
    root = ET.fromstring(response.text)
    if (root.tag != 'CIM') or (root.attrib['CIMVERSION'] != '2.0') \
                           or (root.attrib['DTDVERSION'] != '2.4'):

        print('Invalid XML\nResponse code=%s headers=%s data=%s' % \
            (response.status_code, response.headers, response.text))
        return False
    for child in root:
        if child.tag != 'MESSAGE' or child.attrib['PROTOCOLVERSION'] != '1.4':
            print('Invalid child\nResponse code=%s headers=%s data=%s' % \
                  (response.status_code, response.headers, response.text))
            return False

    return True if(response.status_code == 200) else False

def get_args():
    """
        Get the command line arguments. use --help to get info on cmd line
        arguments
    """

    prog = "sendIndications"
    usage = '%(prog)s [options] listener-url'
    desc = 'Send indications to a listener. Verify set to False'
    epilog = """
Examples:
  %s https://127.0.0.1 -p 5001
  %s http://localhost:5000
  %s http://[2001:db8::1234-eth0] -(http port 5988 ipv6, zone id eth0)
""" % (prog, prog, prog)

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
        '--listenerPort', '-p', default=None,
        metavar="port",
        type=int,
        help='Integer argument defines listener port.')
    general_arggroup.add_argument(
        '--deliver', '-d', default=1,
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
        '--certfile', '-c', dest='cert_file', metavar='certfile',
        help='R|Client certificate file for authenticating with the\n' \
             'WBEM listener. If option specified the client attempts\n' \
             'to execute server authentication.\n'
             'Default: None so that there is no verification of server cert.')
    security_arggroup.add_argument(
        '--keyfile', '-k', dest='key_file', metavar='keyfile',
        help='R|Client private key file for authenticating with the\n' \
             'WBEM listener. Specify as a single file (containing private ' \
             ' key and certificate or a tuple of key and certificate files')

    args = argparser.parse_args()

    if re.match('^http', args.url) is None:
        print('ERROR: url must include schema. received %s' % args.url)
        sys.exit(1)

    if args.verbose:
        print('args: %s' % args)

    return args, argparser

def main():
    """ Get arguments from get_args and create/send the number
        of indications defined.  Each indication is created from a
        template.
    """
    opts, argparser = get_args()

    start_time = time()

    url = opts.url
    if re.search(r":([0-9]+)$", opts.url):
        if opts.listenerPort is not None:
            argparser.error('Simultaneous url with port and -p port option '
                            'invalid')
    else:
        if opts.listenerPort is None:
            url = '%s:%s' % (opts.url, 5000)
        else:
            url = '%s:%s' % (opts.url, opts.listenerPort)

    if opts.verbose:
        print('url=%s' % url)

    cim_protocol_version = '1.4'

    # requests module combines the verification flag and certfile attribute
    # If verify=False, there is no verification of the server cert. If
    # verify=<file_name or dir name> it is the directory of the cert to
    # use for verification.
    verification = False if opts.cert_file is None else opts.cert_file

    headers = {'content-type' : 'application/xml; charset=utf-8',
               'CIMExport' : 'MethodRequest',
               'CIMExportMethod' : 'ExportIndication',
               'Accept-Encoding' : 'Identity',
               'CIMProtocolVersion' : cim_protocol_version}
    # includes accept-encoding because of requests issue.  He supplies it if
    # we don't TODO try None

    delta_time = time() - start_time
    rand_base = randint(1, 1000)
    timer = ElapsedTimer()
    source_id = 'send_indications.py'
    for i in range(opts.deliver):

        msg_id = '%s' % (i + rand_base)
        payload = create_indication_data(msg_id, i, source_id, delta_time,
                                         cim_protocol_version)

        if opts.verbose:
            print('headers=%s\n\npayload=%s' % (headers, payload))

        success = send_indication(url, headers, payload, opts.verbose,
                                  verify=verification)

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
    print('Sent %s in %s sec or %.2f ind/sec' % (opts.deliver, endtime,
                                                 (opts.deliver/endtime)))

if __name__ == '__main__':
    sys.exit(main())
