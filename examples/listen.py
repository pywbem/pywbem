#!/usr/bin/env python

''' Test listener. When started this code creates a WBEMListener on the
    address/ports defined by the input parameters.  This listener
    displays any indications received as log entries.
'''

import sys as _sys
import os as _os
import code as _code
import errno as _errno
import logging as _logging
import threading
# Conditional support of readline module
try:
    import readline as _readline
    _HAVE_READLINE = True
except ImportError as arg:
    _HAVE_READLINE = False

import pywbem

# For creating a self-signed certificate file with private key inside, issue:
#    openssl req -new -x509 -keyout server.pem -out server.pem -days 365 -nodes

RECEIVED_INDICATION_COUNT = 0
COUNTER_LOCK = threading.Lock()

#pylint: disable=invalid-name
listener = None

def _process_indication(indication, host):
    '''This function gets called when an indication is received.'''

    global RECEIVED_INDICATION_COUNT
    COUNTER_LOCK.acquire()
    RECEIVED_INDICATION_COUNT += 1
    COUNTER_LOCK.release()

    listener.logger.info("Consumed CIM indication #%s: host=%s\n%s",
                         RECEIVED_INDICATION_COUNT, host, indication.tomof())

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
    global RECEIVED_INDICATION_COUNT
    print('Received %s indications' % RECEIVED_INDICATION_COUNT)
    if reset:
        RECEIVED_INDICATION_COUNT = 0
        print('count reset to 0')


def _main():
    ''' Main function gets input parameters, sets up listener and starts
        the listener
    '''
    global listener

    if len(_sys.argv) < 2 or _sys.argv[1] == '--help':
        print("Usage: %s host http_port [https_port certfile keyfile]" % \
              _sys.argv[0])
        _sys.exit(2)

    _logging.basicConfig(stream=_sys.stderr, level=_logging.INFO,
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
This Python console displays any indications received by this listener.

listener: WBEMListener instance that has been started.
help(listener): Display help for using listener instance.
status() : display number of indications received. status(reset=True) to reset
           counter
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
