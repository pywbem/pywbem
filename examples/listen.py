#!/usr/bin/env python

''' Test listener. When started this code creates a WBEMListener on the
    address/ports defined by the input parameters.  This listener
    displays any indications received as log entries.
'''

import sys as _sys
import os as _os
import code as _code
import errno as _errno
import logging
import threading
# Conditional support of readline module
try:
    import readline as _readline
    _HAVE_READLINE = True
except ImportError as arg:
    _HAVE_READLINE = False
import six

import pywbem

# For creating a self-signed certificate file with private key inside, issue:
#    openssl req -new -x509 -keyout server.pem -out server.pem -days 365 -nodes

# Dictionary to count indications received by host
RECEIVED_INDICATION_DICT = {}
COUNTER_LOCK = threading.Lock()

#pylint: disable=invalid-name
listener = None

def _process_indication(indication, host):
    '''This function gets called when an indication is received.'''

    global RECEIVED_INDICATION_DICT
    COUNTER_LOCK.acquire()
    if host in RECEIVED_INDICATION_DICT:
        RECEIVED_INDICATION_DICT[host] += 1
    else:
        RECEIVED_INDICATION_DICT[host] = 1
    COUNTER_LOCK.release()

    listener.logger.info("Consumed CIM indication #%s: host=%s\n%s",
                         RECEIVED_INDICATION_DICT, host, indication.tomof())

def _get_argv(index, default=None):
    ''' get the argv input argument defined by index. Return the default
        attribute if that argument does not exist
    '''
    return _sys.argv[index] if len(_sys.argv) > index else default


def status(reset=None):
    '''
        Show status of indications received. If optional reset attribute
        is True, reset the counter.
    '''
    global RECEIVED_INDICATION_DICT
    for host, count in six.iteritems(RECEIVED_INDICATION_DICT):
        print('Host %s Received %s indications' % (host, count))
        
    if reset:
        for host in RECEIVED_INDICATION_DICT:
            RECEIVED_INDICATION_DICT[host] = 0
            print('Host %s Reset: Received %s indications' %
                  (host, RECEIVED_INDICATION_DICT[host]))
        print('counts reset to 0')


def _main():
    ''' Main function gets input parameters, sets up listener and starts
        the listener
    '''
    global listener

    if len(_sys.argv) < 2 or _sys.argv[1] == '--help':
        print("Usage: %s host http_port [https_port certfile keyfile]" % \
              _sys.argv[0])
        _sys.exit(2)

    logging.basicConfig(stream=_sys.stderr, level=logging.INFO,
                        format='%(asctime)s %(levelname)s: %(message)s')

    host = _get_argv(1)
    http_port = _get_argv(2)
    https_port = _get_argv(3)
    certfile = _get_argv(4)
    keyfile = _get_argv(5)

    listener = pywbem.WBEMListener(host=host,
                                   http_port=http_port,
                                   https_port=https_port,
                                   certfile=certfile,
                                   keyfile=keyfile)

    listener.add_callback(_process_indication)
    listener.start()


    banner = """
WBEM listener started on host %s (HTTP port: %s, HTTPS port: %s).
This Python console displays any indications received by this listener as
logger outputs (Level=INFO) to the console by default.

listener: WBEMListener instance that has been started.

help(listener): Display help for using listener instance.

status() : Display count of indications received; status(reset=True) to reset
           counters

Modify logger characteristics through listener.logger:
     (ex. listener.logger.setLevel(logging.ERROR))

Ctrl-d to exit
""" % (host, http_port, https_port)

    # Determine file path of history file
    home_dir = '.'
    if 'HOME' in _os.environ:
        home_dir = _os.environ['HOME'] # Linux
    elif 'HOMEPATH' in _os.environ:
        home_dir = _os.environ['HOMEPATH'] # Windows
    histfile = '%s/.listen_history' % home_dir

    # Read previous command line history
    if _HAVE_READLINE:
        NotFoundError = getattr(__builtins__, 'FileNotFoundError', IOError)
        try:
            _readline.read_history_file(histfile)
        except NotFoundError as exc:
            if exc.errno != _errno.ENOENT:
                raise

    # Interact
    i = _code.InteractiveConsole(globals())
    i.interact(banner)

    # Save command line history
    if _HAVE_READLINE:
        _readline.write_history_file(histfile)

    return 0

if __name__ == '__main__':
    _sys.exit(_main())
