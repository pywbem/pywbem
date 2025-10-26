#!/usr/bin/env python

"""
Test listener. When started this code creates a WBEMListener on the
address/ports defined by the input parameters.  This listener displays any
indications received.
"""

import sys
import os
import time
import code
import logging
import threading
import argparse
# Conditional support of readline module - it is not available on some platforms
try:
    import readline
except ImportError:
    readline = None

import pywbem

# Dictionary to count indications received by host
RECEIVED_INDICATION_DICT = {}
COUNTER_LOCK = threading.Lock()

# Other globals
listener = None  # pylint: disable=invalid-name
sleep = None  # pylint: disable=invalid-name

# Defaults for the command line
DEFAULT_HOST = "localhost"
DEFAULT_HTTP_PORT = 5000
DEFAULT_HTTPS_PORT = None
DEFAULT_SLEEP = 0
DEFAULT_MAX_QUEUE_SIZE = 5

DEFAULT_LOG_LEVEL = logging.INFO


def parse_args(prog):
    """
    Create an argument parser and parse the command line arguments.
    """

    usage = "%(prog)s [options] [HOST]"
    desc = ("Start a WBEM listener and provide an interactive Python console "
            "for issuing operations against it.")
    epilog = ("Note: For creating a self-signed certificate file with private "
              "key inside, issue:\n"
              "  openssl req -new -x509 -keyout server.pem -out server.pem "
              "-days 365 -nodes")

    parser = argparse.ArgumentParser(
        prog=prog, usage=usage, description=desc, epilog=epilog, add_help=True,
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
        "host", metavar="HOST", nargs='?', default=DEFAULT_HOST,
        help="The host for which indications are accepted by the listener:\n"
        "  - a specific host name or host IP address on the local computer:\n"
        "    only indications addressed to that host will be accepted.\n"
        "  - a wildcard address (0.0.0.0 (IPv4) or :: (IPv6))) or the empty"
        " string:\n"
        "    the listener will accept indications addressed to any network"
        " address.\n"
        f"Default: {DEFAULT_HOST}")

    parser.add_argument(
        "--http-port", type=int, default=DEFAULT_HTTP_PORT,
        help="Enables the listener thread for HTTP on this port. "
        f"Default: {DEFAULT_HTTP_PORT}")

    parser.add_argument(
        "--https-port", type=int, default=DEFAULT_HTTPS_PORT,
        help="Enables the listener thread for HTTPS on this port. "
        f"Default: {DEFAULT_HTTPS_PORT}")

    parser.add_argument(
        "--max-queue-size", type=int, default=DEFAULT_MAX_QUEUE_SIZE,
        help="Maximum size of the indication delivery queue of the listener. "
        f"Default: {DEFAULT_MAX_QUEUE_SIZE}")

    parser.add_argument(
        "--certfile", type=str, default=None,
        help="Certificate file for HTTPS. Required, if HTTPS is used.")

    parser.add_argument(
        "--keyfile", type=str, default=None,
        help="Key file for HTTPS. Required, if HTTPS is used.")

    parser.add_argument(
        "--sleep", type=int, default=DEFAULT_SLEEP,
        help="Sleep time in seconds when receiving an indication. "
        f"Default: {DEFAULT_SLEEP}")

    args = parser.parse_args()
    return args


def process_indication(indication, host):
    """
    This function gets called when an indication is received.
    """
    with COUNTER_LOCK:
        if host in RECEIVED_INDICATION_DICT:
            RECEIVED_INDICATION_DICT[host] += 1
        else:
            RECEIVED_INDICATION_DICT[host] = 1

    print("process_indication: Processing CIM indication "
          f"(counters: {RECEIVED_INDICATION_DICT}):\n"
          f"host={host}\n"
          f"{indication.tomof()}")
    if sleep > 0:
        print(f"process_indication: Sleeping for {sleep} s")
        time.sleep(sleep)


def counters(reset=None):
    """
    Show counters of indications received.
    If reset is True, reset the counters.
    """
    for host, count in RECEIVED_INDICATION_DICT.items():
        print(f"Host {host} received {count} indications")

    if reset:
        for host in RECEIVED_INDICATION_DICT:
            RECEIVED_INDICATION_DICT[host] = 0
        print("Counters have been reset to 0")


def main():
    """
    Main function gets input parameters, sets up listener and starts the
    listener.
    """
    global listener  # pylint: disable=global-statement
    global sleep  # pylint: disable=global-statement

    args = parse_args(sys.argv[0])

    log_level = DEFAULT_LOG_LEVEL
    logging.basicConfig(stream=sys.stderr, level=log_level,
                        format="%(asctime)s %(levelname)s: %(message)s")

    host = args.host
    http_port = args.http_port
    https_port = args.https_port

    # These parameters are intentionally not checked in order to be able to
    # test how WBEMListener handles them when missing.
    certfile = args.certfile
    keyfile = args.keyfile

    max_queue_size = args.max_queue_size
    sleep = args.sleep

    print("WBEMListener parameters:")
    print(f"  host={host}")
    print(f"  http_port={http_port}")
    print(f"  https_port={https_port}")
    print(f"  certfile={certfile}")
    print(f"  keyfile={keyfile}")
    print(f"  max_ind_queue_size={max_queue_size}")
    print(f"Sleep time when processing indications: {sleep} s")
    print(f"Log level (to stderr): {logging.getLevelName(log_level)}")
    print("")

    print("Creating WBEMListener instance.")
    listener = pywbem.WBEMListener(host=host,
                                   http_port=http_port,
                                   https_port=https_port,
                                   certfile=certfile,
                                   keyfile=keyfile,
                                   max_ind_queue_size=max_queue_size)

    print("Adding callback: process_indication")
    listener.add_callback(process_indication)

    print("Starting WBEM listener.")
    try:
        listener.start()
    except pywbem.ListenerError as exc:
        print(f"Error: {exc}")
        return 1

    # Determine file path of history file
    home_dir = '.'
    if 'HOME' in os.environ:
        home_dir = os.environ['HOME']  # Linux
    elif 'HOMEPATH' in os.environ:
        home_dir = os.environ['HOMEPATH']  # Windows
    histfile = f'{home_dir}/.listen_history'

    # Read previous command line history
    if readline:
        try:
            readline.read_history_file(histfile)
        except FileNotFoundError:
            pass

    # Start Python console and interact
    banner = """
This Python console displays any indications received by this listener.

Some variables and functions:

* listener: WBEMListener instance that has been started.
* help(listener): Display help for using listener instance.
* sleep: Sleep time in seconds when receiving an indication (can be set).
* counters(): Display indication counters.
* counters(reset=True): Display and reset indication counters.
* listener.logger.setLevel(logging.DEBUG): Change log level.

Ctrl-D: Exit this console.
"""
    i = code.InteractiveConsole(globals())
    i.interact(banner)

    # Save command line history
    if readline:
        readline.write_history_file(histfile)

    print("Stopping listener")
    listener.stop()

    return 0


if __name__ == '__main__':
    sys.exit(main())
