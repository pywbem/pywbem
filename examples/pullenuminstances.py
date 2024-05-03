#!/usr/bin/env python

"""
    Example of using Pull Operations to retrieve instances from a
    WBEM Server. This example allows either simplistic command line
    input with a fixed number of parameters or defaults to internal
    definitions if incorrect number of  cmd line arguments are supplied.

    It:
        Creates a connection
        Opens an enumeration session with OpenEnumerateInstances
        Executes a pull loop until the result.eos =True
        Displays overall statistics on the returns
    It also displays the results of the open and each pull in detail
"""


import sys
import datetime
from pywbem import WBEMConnection, CIMError, Error

# Default connection attributes. Used if not all arguments are
# supplied on the command line.
USERNAME = 'blah'
PASSWORD = 'blah'
TEST_CLASS = 'CIM_ComputerSystem'
TEST_NAMESPACE = 'root/cimv2'
SERVER_URL = 'http://localhost'

class ElapsedTimer:
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


def execute_request(conn, classname, max_open, max_pull):
    """
        Enumerate instances defined by the function's
        classname argument using the OpenEnumerateInstances and
        PullInstancesWithPath.

        * classname - Classname for the enumeration.

        * max_open - defines the maximum number of instances
          for the server to return for the open

        *max_pull defines the maximum number of instances for the
          WBEM server to return for each pull operation.

        Displays results of each open or pull operation including
        size, return parameters, and time to execute.

        Any exception exits the function.
    """
    start = ElapsedTimer()
    result = conn.OpenEnumerateInstances(classname,
                                         MaxObjectCount=max_open)


    print(f'open rtn eos={result.eos} context={result.context}, '
          f'count={len(result.instances)} time={start.elapsed_ms()} ms')

    # save instances since we reuse result
    insts = result.instances

    # loop to make pull requests until end_of_sequence received.
    pull_count = 0
    while not result.eos:
        pull_count += 1
        op_start = ElapsedTimer()
        result = conn.PullInstancesWithPath(result.context,
                                            MaxObjectCount=max_pull)

        insts.extend(result.instances)

        print(f'pull rtn eos={result.eos} context={result.context}, '
              f'insts={len(result.instances)} time={op_start.elapsed_ms()} ms')


    print(f'Result instance count={len(insts)} pull count={pull_count} '
          f'time={start.elapsed_sec():.2f} sec')
    return insts

def main():
    """
        Get arguments and call the execution function
    """

    # if less than required arguments, use the defaults
    if len(sys.argv) < 8:
        print(f"Usage: {sys.argv[0]} server_url username password namespace "
              "classname max_open, max_pull")
        server_url = SERVER_URL
        username = USERNAME
        password = PASSWORD
        namespace = TEST_NAMESPACE
        classname = TEST_CLASS
        max_open = 0
        max_pull = 100
    else:
        server_url = sys.argv[1]
        username = sys.argv[2]
        password = sys.argv[3]
        namespace = sys.argv[4]
        classname = sys.argv[5]
        max_open = sys.argv[6]
        max_pull = sys.argv[7]

    print(f'Parameters: server_url={server_url}\n username={username}\n '
          f'namespace={namespace}\n classname={classname}\n '
          f'max_open={max_open},\n max_pull={max_pull}')

    # connect to the server
    conn = WBEMConnection(server_url, (username, password),
                          default_namespace=namespace,
                          no_verification=True)

    #Call method to execute the enumeration sequence and return instances
    try:
        instances = execute_request(conn, classname, max_open, max_pull)

        # print the resulting instances
        for instance in instances:
            print(f'\npath={instance.path}\n{instance.tomof()}')

    # handle exceptions
    except CIMError as ce:
        print(f'Operation Failed: CIMError: code={ce.status_code_name}, '
              f'Description={ce.status_description}')
        sys.exit(1)
    except Error as err:
        print (f"Operation failed: {err}")
        sys.exit(1)

    return 0

if __name__ == '__main__':
    sys.exit(main())
