#!/usr/bin/env python

import sys as _sys
import os as _os
import code as _code
import six as _six
import errno as _errno
import logging as _logging
# Conditional support of readline module
try:
    import readline as _readline
    _HAVE_READLINE = True
except ImportError as arg:
    _HAVE_READLINE = False

import pywbem

# For creating a self-signed certificate file with private key inside, issue:
#    openssl req -new -x509 -keyout server.pem -out server.pem -days 365 -nodes

def _process_indication(indication, host):
    '''This function gets called when an indication is received.'''
    print("Received indication from %s:\n%s" % (host, indication.tomof()))

def _get_argv(index, default=None):
    return _sys.argv[index] if len(_sys.argv) > index else default

listener = None

def _main():
    global listener

    if len(_sys.argv) < 2:
        print("Usage: %s host http_port [https_port certfile keyfile]" % \
              _sys.argv[0])
        _sys.exit(2)

    _logging.basicConfig(stream=_sys.stderr, level=_logging.WARNING)

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
        try:
            _readline.read_history_file(histfile)
        except IOError as exc:
            if exc.args[0] != _errno.ENOENT:
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
