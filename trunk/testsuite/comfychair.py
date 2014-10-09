#! /usr/bin/env python

# Copyright (C) 2002, 2003 by Martin Pool <mbp@samba.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA

"""comfychair: a Python-based instrument of software torture.

Copyright (C) 2002, 2003 by Martin Pool <mbp@samba.org>

This is a test framework designed for testing programs written in
Python, or (through a fork/exec interface) any other language.

For more information, see the file README.comfychair.

To run a test suite based on ComfyChair, just run it as a program.
"""

import sys
import os
import os.path
import types
import re
import shutil
import traceback
import getopt


class TestCase(object):
    """A base class for tests.  This class defines required functions which
    can optionally be overridden by subclasses.  It also provides some
    utility functions for"""

    def __init__(self):
        self.test_log = ""
        self.background_pids = []
        self._cleanups = []
        self._enter_rundir()
        self._save_environment()
        self.add_cleanup(self.teardown)


    # --------------------------------------------------
    # Save and restore directory
    def _enter_rundir(self):
        self.basedir = os.getcwd()
        self.rundir = os.path.join(self.basedir,
                                   'testtmp',
                                   self.__class__.__name__)
        self.tmpdir = os.path.join(self.rundir, 'tmp')
        # The following logic and also in restore_directory() assumes that
        # tmpdir is a subdirectory of rundir.
        if os.path.isdir(self.rundir):
            shutil.rmtree(self.rundir)
        os.makedirs(self.tmpdir)
        os.chdir(self.rundir)
        self.add_cleanup(self._restore_directory)

    def _restore_directory(self):
        os.chdir(self.basedir)

    # --------------------------------------------------
    # Save and restore environment
    def _save_environment(self):
        self._saved_environ = os.environ.copy()
        self.add_cleanup(self._restore_environment)

    def _restore_environment(self):
        os.environ.clear()
        os.environ.update(self._saved_environ)


    def setup(self):
        """Set up test fixture."""
        pass

    def teardown(self):
        """Tear down test fixture."""
        pass

    def runtest(self):
        """Run the test."""
        pass


    def add_cleanup(self, c):
        """Queue a cleanup to be run when the test is complete."""
        self._cleanups.append(c)


    def fail(self, reason = ""):
        """Say the test failed."""
        raise AssertionError(reason)


    #############################################################
    # Requisition methods

    def require(self, predicate, message):
        """Check a predicate for running this test.

If the predicate value is not true, the test is skipped with a message explaining
why."""
        if not predicate:
            raise NotRunError, message

    def require_root(self):
        """Skip this test unless run by root."""
        self.require(os.getuid() == 0,
                     "must be root to run this test")

    #############################################################
    # Assertion methods

    def assert_(self, expr, reason = ""):
        if not expr:
            raise AssertionError(reason)

    def assert_equal(self, a, b, entity=None):
        """Assert that two values (of any type) are equal

        Inputs:
          a            any type: left value
          b            any type: right value
          entity       string: name of entity whose value is compared

        Raises:
          AssertionError if not equal
        """
        if not a == b:
            raise AssertionError("Values %sare not equal:\n"
                                 "    left  value: %r (%s)\n"
                                 "    right value: %r (%s)" % \
                                 ("of %s " % entity if entity is not None
                                  else "", a, type(a), b, type(b)))

    def assert_notequal(self, a, b, entity=None):
        """Assert that two values (of any type) are not equal

        Inputs:
          a            any type: left value
          b            any type: right value
          entity       string: name of entity whose value is compared

        Raises:
          AssertionError if equal
        """
        if a == b:
            raise AssertionError("Values %sare equal:\n"
                                 "    left  value: %r (%s)\n"
                                 "    right value: %r (%s)" % \
                                 ("of %s " % entity if entity is not None
                                  else "", a, type(a), b, type(b)))

    def assert_re_match(self, pattern, s, entity=None):
        """Assert that a string value matches a particular pattern

        Inputs:
          pattern      string: regular expression
          s            string: string value to be matched
          entity       string: name of entity whose value is compared

        Raises:
          AssertionError if not matched
        """
        if not re.match(pattern, s):
            raise AssertionError("String value %sdoes not match regexp\n"
                                 "     value: %r\n"
                                 "    regexp: %r" % \
                                 ("of %s " % entity if entity is not None
                                  else "", s, pattern))

    def assert_re_search(self, pattern, s, entity=None):
        """Assert that a string value *contains* a particular pattern

        Inputs:
          pattern      string: regular expression
          s            string: string value to be searched
          entity       string: name of entity whose value is compared

        Raises:
          AssertionError if not matched
          """
        if not re.search(pattern, s):
            raise AssertionError("String value %sdoes not contain regexp\n"
                                 "    string: %r\n"
                                 "    regexp: %r" % \
                                 ("of %s " % entity if entity is not None
                                  else "", s, pattern))


    def assert_no_file(self, filename):
        assert not os.path.exists(filename), ("file exists but should not: %s" % filename)


    #############################################################
    # Methods for running programs

    def runcmd_background(self, cmd):
        self.test_log = self.test_log + "Run in background:\n" + `cmd` + "\n"
        pid = os.fork()
        if pid == 0:
            # child
            try:
                os.execvp("/bin/sh", ["/bin/sh", "-c", cmd])
            finally:
                os._exit(127)
        self.test_log = self.test_log + "pid: %d\n" % pid
        return pid


    def runcmd(self, cmd, expectedResult = 0):
        """Run a command, fail if the command returns an unexpected exit
        code.  Return the output produced."""
        rc, output, stderr = self.runcmd_unchecked(cmd)
        if rc != expectedResult:
            raise AssertionError("""command returned %d; expected %s: \"%s\"
stdout:
%s
stderr:
%s""" % (rc, expectedResult, cmd, output, stderr))

        return output, stderr


    def run_captured(self, cmd):
        """Run a command, capturing stdout and stderr.

        Based in part on popen2.py

        Returns (waitstatus, stdout, stderr)."""
        pid = os.fork()
        if pid == 0:
            # child
            try:
                pid = os.getpid()
                openmode = os.O_WRONLY|os.O_CREAT|os.O_TRUNC

                outfd = os.open('%d.out' % pid, openmode, 0666)
                os.dup2(outfd, 1)
                os.close(outfd)

                errfd = os.open('%d.err' % pid, openmode, 0666)
                os.dup2(errfd, 2)
                os.close(errfd)

                if isinstance(cmd, types.StringType):
                    cmd = ['/bin/sh', '-c', cmd]

                os.execvp(cmd[0], cmd)
            finally:
                os._exit(127)
        else:
            # parent
            exited_pid, waitstatus = os.waitpid(pid, 0)
            stdout = open('%d.out' % pid).read()
            stderr = open('%d.err' % pid).read()
            return waitstatus, stdout, stderr


    def runcmd_unchecked(self, cmd, skip_on_noexec = 0):
        """Invoke a command; return (exitcode, stdout, stderr)"""
        waitstatus, stdout, stderr = self.run_captured(cmd)
        assert not os.WIFSIGNALED(waitstatus), \
               ("%s terminated with signal %d" % `cmd`, os.WTERMSIG(waitstatus))
        rc = os.WEXITSTATUS(waitstatus)
        self.test_log = self.test_log + ("""Run command: %s
Wait status: %#x (exit code %d, signal %d)
stdout:
%s
stderr:
%s""" % (cmd, waitstatus, os.WEXITSTATUS(waitstatus), os.WTERMSIG(waitstatus),
         stdout, stderr))
        if skip_on_noexec and rc == 127:
            # Either we could not execute the command or the command
            # returned exit code 127.  According to system(3) we can't
            # tell the difference.
            raise NotRunError, "could not execute %s" % `cmd`
        return rc, stdout, stderr


    def explain_failure(self, exc_info = None):
        print "test_log:"
        print self.test_log


    def log(self, msg):
        """Log a message to the test log.  This message is displayed if
        the test fails, or when the runtests function is invoked with
        the verbose option."""
        self.test_log = self.test_log + msg + "\n"


class NotRunError(Exception):
    """Raised if a test must be skipped because of missing resources"""
    def __init__(self, value = None):
        self.value = value


def _report_error(case, debugger):
    """Ask the test case to explain failure, and optionally run a debugger

    Input:
      case         TestCase instance
      debugger     if true, a debugger function to be applied to the traceback
"""
    ex = sys.exc_info()
    print "-----------------------------------------------------------------"
    if ex:
        traceback.print_exc(file=sys.stdout)
    if case is not None: # can happen with exception in constructor
        case.explain_failure()
    print "-----------------------------------------------------------------"

    if debugger:
        tb = ex[2]
        debugger(tb)


def runtests(test_list, verbose = 0, debugger = None, quiet = 0):
    """Run a series of tests.

    Inputs:
      test_list    sequence of TestCase classes
      verbose      print more information as testing proceeds
      debugger     debugger object to be applied to errors

    Returns:
      unix return code: 0 for success, 1 for failures, 2 for test failure
    """
    ret = 0
    for test_class in test_list:
        print "%-30s" % _test_name(test_class),
        # flush now so that long running tests are easier to follow
        sys.stdout.flush()

        obj = None
        try:
            try: # run test and show result
                obj = test_class()
                obj.setup()
                obj.runtest()
                print "OK"
            except KeyboardInterrupt:
                print "INTERRUPT"
                if not quiet:
                    _report_error(obj, debugger)
                ret = 2
                break
            except NotRunError, msg:
                print "NOTRUN, %s" % msg.value
            except:
                print "FAIL"
                if not quiet:
                    _report_error(obj, debugger)
                ret = 1
        finally:
            while obj and obj._cleanups:
                try:
                    apply(obj._cleanups.pop())
                except KeyboardInterrupt:
                    print "interrupted during teardown"
                    _report_error(obj, debugger)
                    ret = 2
                    break
                except:
                    print "error during teardown"
                    if not quiet:
                        _report_error(obj, debugger)
                    ret = 1
        # Display log file if we're verbose
        if ret == 0 and verbose:
            obj.explain_failure()

    return ret


def _test_name(test_class):
    """Return a human-readable name for a test class.
    """
    try:
        return test_class.__name__
    except:
        return `test_class`


def print_help():
    """Help for people running tests"""
    print """%s: software test suite based on ComfyChair

usage:
    To run all tests, just run this program.  To run particular tests,
    list them on the command line.

options:
    --help              show usage message
    --list              list available tests
    --verbose, -v       show more information while running tests
    --post-mortem, -p   enter Python debugger on error
""" % sys.argv[0]


def print_list(test_list):
    """Show list of available tests"""
    for test_class in test_list:
        print "    %s" % _test_name(test_class)


def main(tests, extra_tests=[]):
    """Main entry point for test suites based on ComfyChair.

    inputs:
      tests       Sequence of TestCase subclasses to be run by default.
      extra_tests Sequence of TestCase subclasses that are available but
                  not run by default.

Test suites should contain this boilerplate:

    if __name__ == '__main__':
        comfychair.main(tests)

This function handles standard options such as --help and --list, and
by default runs all tests in the suggested order.

Calls sys.exit() on completion.
"""
    opt_verbose = 0
    opt_quiet = 0
    debugger = None

    opts, args = getopt.getopt(sys.argv[1:], 'pvq',
                               ['help', 'list', 'verbose', 'post-mortem',
                                'quiet'])

    for opt, opt_arg in opts:
        if opt == '--help':
            print_help()
            return
        elif opt == '--list':
            print_list(tests + extra_tests)
            return
        elif opt == '--verbose' or opt == '-v':
            opt_verbose = 1
        elif opt == '--post-mortem' or opt == '-p':
            import pdb
            debugger = pdb.post_mortem
        elif opt == '--quiet' or opt == '-q':
            if not opt_verbose:
                opt_quiet = 1

    if args:
        all_tests = tests + extra_tests
        by_name = {}
        for t in all_tests:
            by_name[_test_name(t)] = t
        which_tests = []
        for name in args:
            which_tests.append(by_name[name])
    else:
        which_tests = tests

    sys.exit(runtests(which_tests, verbose=opt_verbose,
                      debugger=debugger, quiet=opt_quiet))

if __name__ == '__main__':
    print __doc__
