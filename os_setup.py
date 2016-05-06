#
#
# (C) Copyright 2015 IBM Corp.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
# Author: Andreas Maier <maiera@de.ibm.com>
#

"""Extensions to `setuptools` for installation of OS packages and
Python packages for development mode.

The `setup.py` commands (in the command line of the script) that are
introduced or extended, are:

* `install_os` - a new command that installs prerequisite OS packages
  for the package that specifies it.
  The respective OS packages are defined in a new `install_os_requires`
  attribute of the `setup()` function.

* `develop_os` - a new command that installs prerequisite OS packages
  for the 'development mode' of the package that specifies it.
  The respective OS packages are defined in a new `develop_os_requires`
  attribute of the `setup()` function.

* `develop` - extends the `develop` command introduced by setuptools with
  the ability to install dependent Python packages.
  The respective Python packages are defined in a new `develop_requires`
  attribute of the `setup()` function.

Syntax for the new attributes of the `setup()` function:

* `install_os_requires` and `develop_os_requires`

  These attributes specify the OS package names and optionally a version
  requirement for each package. The package names are specific to the system
  as returned by `platform.system()`, and in case of the 'Linux' system, on
  the Linux distribution (see `_linux_distribution()`).

  These attributes can also specify custom functions for handling more complex
  cases. At the distribution level, it is possible to refer to the definitions
  for another distribution, in order to avoid repetition.

  The syntax is the same for both attributes. The following example shows the
  syntax:

      install_os_requires =
      {                                     # system dictionary
          'Linux':                          # system dict key is system name
          {                                 # distro dictionary
              'redhat':                     # distro dict key is distro name
              [                             # requirements list
                  "doxygen",                # req: pkg name
                  "openssl-devel>=1.0.1",   # req: pkg with minimum version
                  "pylint>=1.3,<1.4",       # req: pkg with multiple version
                                            # requirements
                  "xyz=2.7",                # req: pkg where any 2.7.x matches
                  "xyz==2.7",               # req: pkg where only 2.7[.0] match
                  "abc"                     # req: pkg only for Python 2
                    if sys.version_info[0] == 2
                    else None,
                  [                         # req: pkg choice where first
                                            # available pkg name is installed;
                                            # each choice item could have a
                                            # version requirement
                      "python-devel34",
                      "python-devel34u"
                  ],
                  install_swig,             # req: custom installer function
                  . . .
              ],
              'centos': 'redhat',           # refer to another distribution
              . . .
          },
          'Windows':                        # System without distro
          [                                 # requirements list
              install_doxygen,              # req: custom installer function
              . . .
          ],
          . . .
      }

  The syntax for version requirements is:

      <op><version>[,<op><version>[,...]]

  Where:
  * <op> - the comparison operator, one of '<', '<=', '=', '==', '>=', '>'.
    For '=', unspecified version components are treated like wildcards.
    This is different from '==', where the version must match exactly,
    and unspecified version components are considered to be 0.
    For the other operators, unspecified version components are considered
    to be 0 (consistent with `pip`).
  * <version> - the version to be compared against.

  Custom installer functions must have the following interface:

      def install_swig(installer, dry_run, verbose):
          . . .

  Where:
  * `installer` - the installer object to be used if any OS packages need to be
    installed or tested for availability. See the `OSInstaller` class in this
    module for details.
  * `dry_run` - a boolean flag indicating whether a dry run should be done, vs.
    the real action. This is controlled by the `-n`, `--dry-run` command line
    option of the `setup.py` script.
  * `verbose` - a boolean flag indicating whether to be verbose vs. quiet when
    printing messages. Verbose mode is on by default, or when the `-v`,
    `--verbose` command line option of the `setup.py` script is specified.
    Verbose mode is off when the `-q`, `--quiet` command line option of the
    `setup.py` script is specified.

* `develop_requires`

  This attribute has the same syntax as the `install_requires` attribute
  introduced by `setuptools`. It specifies the Python package names and
  optionally a version requirement for each package. The package names are Pypi
  package names. This attribute can also specify custom functions for handling
  more complex cases (like patching an installed package).

  The following example shows the syntax:

      develop_requires = [
          "httpretty",                  # a package without version requirement
          "abc=2.7",                    # pkg where any 2.7.x matches
          "abc==2.7",                   # pkg where only 2.7[.0] matches
          "pylint>=1.3,<1.4",           # a package with multiple version reqs
          "epydoc" if sys.version_info[0] == 2 else None,
                                        # a package only for Python 2
          ["xyz34", "xyz34x"],          # list of pkgs to try; each could
                                        # have a version req.
          patch_epydoc,                 # a custom function
          . . .
      ]

  The syntax of version requirements and the interface of custom functions are
  the same as for the `install_os_requires` attribute.
"""

from __future__ import print_function
import sys
import re
import types
import subprocess
import platform
import getpass
from distutils.errors import DistutilsSetupError
from setuptools import Command, Distribution
from setuptools.command.develop import develop as _develop
import pip


# Some types to avoid dependency on "six" package during installation.
if sys.version_info[0] == 2:
    string_types = basestring,
    text_type = unicode
    binary_type = str
else:
    string_types = str,
    text_type = str
    binary_type = bytes


class OsDistribution(Distribution):
    """Setuptools/distutils distribution class for installing OS packages."""

    def __init__(self, attrs=None):

        # Get 'develop_requires' attribute
        if attrs is not None:
            self.develop_requires = attrs.pop('develop_requires', {})
        elif not hasattr(self, "develop_requires"):
            self.develop_requires = {}
        _assert_req_list(self, 'develop_requires',
                         self.develop_requires)

        # Get 'install_os_requires' attribute
        if attrs is not None:
            self.install_os_requires = attrs.pop('install_os_requires', {})
        elif not hasattr(self, "install_os_requires"):
            self.install_os_requires = {}
        _assert_system_dict(self, 'install_os_requires',
                            self.install_os_requires)

        # Get 'develop_os_requires' attribute
        if attrs is not None:
            self.develop_os_requires = attrs.pop('develop_os_requires', {})
        elif not hasattr(self, "develop_os_requires"):
            self.develop_os_requires = {}
        _assert_system_dict(self, 'develop_os_requires',
                            self.develop_os_requires)

        # Distribution is an old-style class in Python 2.6:
        Distribution.__init__(self, attrs)

def _assert_system_dict(dist, attr, value):
    """Validate the value of the 'install_os_requires' and
    'develop_os_requires' attributes.

    The interface of this function is suitable for the newer setuptools
    'entry_points' concept; see
    https://pythonhosted.org/setuptools/setuptools.html#adding-setup-arguments

    Parameters:
    * dist: Distribution object
    * attr: Attribute name
    * value: Attribute value to be validated
    """
    system_dict = value
    if not isinstance(system_dict, dict):
        raise DistutilsSetupError(
            "'%s' attribute: Value must be a dictionary of systems "\
            "(got type %s)" % (attr, type(system_dict))
        )
    for system in system_dict:
        if not isinstance(system, string_types):
            raise DistutilsSetupError(
                "'%s' attribute: Key in system dictionary must be a string "\
                "(got key %r of type %s)" %\
                (attr, system, type(system))
            )
        system_item = system_dict[system]
        if isinstance(system_item, dict):
            # The packages are specified by distro (e.g. Linux)
            distro_dict = system_item
            for distro in distro_dict:
                if not isinstance(distro, string_types):
                    raise DistutilsSetupError(
                        "'%s' attribute: Key in distribution dictionary must "\
                        "be a string "\
                        "(for system '%s', got key %r of type %s)" %\
                        (attr, system, distro, type(distro))
                    )
                distro_item = distro_dict[distro]
                if isinstance(distro_item, list):
                    # Normal case: the distro specifies a package list
                    req_list = distro_item
                    _assert_req_list(dist, attr, req_list)
                elif isinstance(distro_item, string_types):
                    # The distro refers to another distro
                    referenced_distro = distro_item
                    if not referenced_distro in distro_dict:
                        raise DistutilsSetupError(
                            "'%s' attribute: Referenced distribution does not "\
                            "exist in distribution dictionary "\
                            "(for system '%s' distro '%s', got "\
                            "referenced distro '%s')" %\
                            (attr, system, distro, referenced_distro)
                        )
                else:
                    raise DistutilsSetupError(
                        "Invalid type %s for value in distribution dictionary "\
                        ": %r" %\
                        (type(distro_item), distro_item)
                    )
        elif isinstance(system_item, list):
            # The packages are specified at system level (e.g. Windows)
            req_list = system_item
            _assert_req_list(dist, attr, req_list)
        else:
            raise DistutilsSetupError(
                "'%s' attribute: Value in system dictionary must be "\
                "a dictionary of distributions or a list "\
                "(for system '%s', got type %s)" %\
                (attr, system, type(system_item))
            )

def _assert_req_list(dist, attr, value): # pylint: disable=unused-argument
    """Validate the value of a requirements list (e.g. the 'develop_requires'
    attribute, or the requirement lists for a distro or system in the
    'install_os_requires' attribute).

    The interface of this function is suitable for the newer setuptools
    'entry_points' concept; see
    https://pythonhosted.org/setuptools/setuptools.html#adding-setup-arguments

    Parameters:
    * dist: Distribution object
    * attr: Attribute name
    * value: Attribute value to be validated
    """
    req_list = value
    for req in req_list:
        if isinstance(req, (list, tuple)):
            for single_req in req:
                if not isinstance(single_req, string_types):
                    raise DistutilsSetupError(
                        "'%s' attribute: Requirement list must contain "\
                        "strings (got list item %r of type %s)"%\
                        (attr, single_req, type(single_req))
                    )
        elif not isinstance(req, (string_types, types.FunctionType,
                                  type(None))):
            raise DistutilsSetupError(
                "'%s' attribute: Requirement must be a string, a function, "\
                "or None (got requirement %r of type %s)"%\
                (attr, req, type(req))
            )


class BaseOsCommand(Command):
    """Setuptools/distutils command class; a base class for installing
    OS packages.
    """

    def __init__(self, dist, **kw):
        Command.__init__(self, dist, **kw)
        self.installer = OSInstaller().platform_installer()

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass


class install_os(BaseOsCommand): # pylint: disable=invalid-name
    """Setuptools/distutils command class for installing OS packages
    in 'normal mode', i.e. when the user specifies the 'install_os' command.
    """

    description = "install prerequisite OS packages for this package."

    # List of option tuples:
    #   * long name,
    #   * short name (None if no short name),
    #   * help string.
    user_options = []

    def run(self):
        """Perform the action for this command.

        This function is invoked when the user specifies the 'install_os'
        command.
        """

        if self.verbose:
            print("install_os: Installing prerequisite OS packages for "\
                  "platform: %s" % self.installer.platform)

        self.installer.install_system(
            self.distribution.install_os_requires, self.dry_run, self.verbose)

        if len(self.installer.errors) > 0:
            self.installer.print_errors()
            raise DistutilsSetupError(
                "Errors occurred (see previous messages)"
            )

class develop_os(BaseOsCommand): # pylint: disable=invalid-name
    """Setuptools/distutils command class for installing OS packages for
    'development mode', i.e. when the user specifies the 'develop_os' command.
    """

    description = "install prerequisite OS packages for 'development "\
                  "mode' of this package."

    # List of option tuples:
    #   * long name,
    #   * short name (None if no short name),
    #   * help string.
    user_options = []

    def run(self):
        """Perform the action for this command.

        This function is invoked when the user specifies the 'develop_os'
        command.
        """

        if self.verbose:
            print("develop_os: Installing prerequisite OS packages for "\
                  "platform: %s" % self.installer.platform)

        self.installer.install_system(
            self.distribution.install_os_requires, self.dry_run, self.verbose)
        self.installer.install_system(
            self.distribution.develop_os_requires, self.dry_run, self.verbose)

        if len(self.installer.errors) > 0:
            self.installer.print_errors()
            raise DistutilsSetupError(
                "Errors occurred (see previous messages)"
            )

class develop(_develop): # pylint: disable=invalid-name
    """Setuptools/distutils command class extending the setuptools 'develop'
    command with the ability to process the 'develop_requires' attribute
    of the setup() function.
    """

    def __init__(self, dist, **kw):
        _develop.__init__(self, dist, **kw)
        self.installer = PythonInstaller()

    def run(self):
        """Perform the action for this command.

        This function is invoked when the user specifies the 'develop'
        command.
        """

        _develop.run(self)

        if self.verbose:
            print("develop: Installing prerequisite Python packages")

        self.installer.install_reqlist(
            self.distribution.develop_requires, self.dry_run, self.verbose)

        if len(self.installer.errors) > 0:
            self.installer.print_errors()
            raise DistutilsSetupError(
                "Errors occurred (see previous messages)"
            )


def _linux_distribution():
    """Return the ID of the Linux distribution.

    The Linux distribution is determined by first looking at the ID parameter in
    `/etc/os-release`, and then by looking at the result of
    `platform.linux_distribution()` (which incorrectly returns "debian" on
    Ubuntu 12.04, hence the other test).
    """
    rc, out, _ = shell("grep \"^ID=\" /etc/os-release")
    if rc == 0 and out.startswith("ID="):
        distro = out[3:].strip("\"' \t\n").lower()
        return distro

    rc, out, _ = shell("lsb_release -i -s", ignore_notfound=True)
    if rc == 0:
        distro = out.strip(" \t\n").lower()
        # Fix a few special cases:
        if distro == "redhatenterpriseworkstation":
            distro = "redhat"
        return distro

    distro, _, _ = platform.linux_distribution(
        full_distribution_name=False
    )
    return distro

class BaseInstaller(object):
    """Base class for installing OS packages and Python packages."""

    MSG_PLATFORM_NOT_SUPPORTED = 1
    MSG_USER_NOT_AUTHORIZED = 2
    MSG_PKG_NOT_IN_REPOS = 3

    def __init__(self):
        """
        Instance attributes:

        * errors (dict): The errors collected during the processing of package
          requirements, that cause the program to raise an exception at the end.
          Key (string): Message id (using the class attributes MSG_*).
          Value (string): A list of package requirements (e.g. "abc>=12.0").

        * system (string): The name of this operating system (e.g. Windows,
          Linux).

        * distro (string): The name of this Linux distribution
          (see `_linux_distribution()`), or None if this is not a Linux system.

        * platform (string): A human readable name of this operating system
          platform, that is unique for the combination of system and distro.

        * userid (string): The current userid (the name, not a numeric uid).

        * env (string): The environment into which packages are installed
                        (e.g. "Python", "OS").
        """

        self.errors = dict()

        self.system = platform.system()
        if self.system == "Linux":
            self.distro = _linux_distribution()
            self.platform = self.distro
        else:
            self.distro = None
            self.platform = self.system

        self.userid = getpass.getuser()
        self.env = None


    def do_install(self, pkg_name, version_reqs=None, dry_run=False,
                   reinstall=False):
        """Interface definition: Install an OS or Python package,
        optionally applying version requirements.

        A precondition for this method is that the need to install the package
        has been verified using the `is_installed()` method (considering the
        specified version requirements), and that the availability of the
        package in the respective repositories has been verified using the
        `is_available()` method (also considering the specified version
        requirements).
        TODO: Clarify whether this method needs to obeye version requirements.

        Parameters:
        * pkg_name (string): Name of the package.
        * version_reqs (list): None, or list of zero or more strings that are
          version requirements for the package (e.g. ('>=3.0', '!=3.5')).
        * dry_run (boolean): Display what would happen instead of doing it.
        * reinstall (boolean): Reinstall the package if already installed.

        Returns: Nothing

        Raises:
        * If installation fails, raises a DistutilsSetupError exception.
        """
        raise NotImplementedError

    def is_installed(self, pkg_name, version_reqs=None):
        """Interface definition: Test whether an OS or Python package
        is installed, and optionally satisfies version requirements.

        Parameters:
        * pkg_name (string): Name of the Python package.
        * version_reqs (list): None, or list of zero or more strings that are
          version requirements for the package (e.g. ('>=3.0', '!=3.5')).

        Returns:
        * A tuple of:
          - Boolean indicating whether the package is installed.
          - Boolean indicating whether the package is installed and satisfies
            the version requirements.
          - If the package is installed, its version as a string.
            Otherwise, None.

        Raises:
        * If testing fails, raises a DistutilsSetupError exception.
        """
        raise NotImplementedError

    def is_available(self, pkg_name, version_reqs=None):
        """Interface definition: Test whether an OS or Python package
        is available in the configured repos (for OS packages) or on Pypi (for
        Python packages), and optionally satisfies version requirements.
        It does not matter for this function whether the package is already
        installed.

        Parameters:
        * pkg_name (string): Name of the Python package.
        * version_reqs (list): None, or list of zero or more strings that are
          version requirements for the package (e.g. ('>=3.0', '!=3.5')).

        Returns:
        * A tuple of:
          - Boolean indicating whether the package is available.
          - Boolean indicating whether the package is available and satisfies
            the version requirements.
          - If the package is available, its available versions as a list of
            strings. Otherwise, None.

        Raises:
        * If testing fails, raises a DistutilsSetupError exception.
        """
        raise NotImplementedError

    def ensure_installed(self, pkg_name, version_reqs=None, dry_run=False,
                         verbose=True, ignore=False):
        """Interface definition: Ensure that an OS or Python package
        is installed, and optionally satisfies version requirements.

        Parameters:
        * pkg_name (string): Name of the Python package.
        * version_reqs (list): None, or list of zero or more strings that are
          version requirements for the package (e.g. ('>=3.0', '!=3.5')).
        * dry_run (boolean): Display what would happen instead of doing it.
        * verbose (boolean): Verbose mode. In verbose mode, all messages are
          printed. In quiet mode, only the most important messages are printed.
        * ignore (boolean): Ignore mode. In ignore mode, unavailability of
          the package (considering version requirements, if specified) will
          be ignored.

        Returns:
        * Boolean indicating whether the package is installed and (if
          specified) satisfies the version requirements.

        Raises:
        * If installation fails, raises a DistutilsSetupError exception.
        """
        raise NotImplementedError

    def parse_pkg_req(self, pkg_req):
        """Parse a package requirement string and return a tuple of package name
        and version requirement. This can be used for OS packages and for
        Python packages.

        Parameters:
        * pkg_req: A string specifying the package requirement
          (e.g. 'abc >=1.0,<3.0', or 'def 1.0').

        Returns:
        * tuple of:
          - A string specifying the package name (e.g. 'abc' or 'def')
          - A list with zero or more strings, each specifying a version
            requirement (e.g. ('>=1.0', '<3.0') or ('==1.0',)). If no
            comparison operator was specified, the default operator '==' is
            added, so that each list entry is of the form <op><version>.
        """
        r = r'^([a-zA-Z0-9_\.\-\+]+)'\
            r'((?: *(?:<|<=|==|=| |!=|>|>=)[0-9a-zA-Z_\.\-\+]+)'\
            r'(?: *, *(?:<|<=|==|=||!=|>|>=)[0-9a-zA-Z_\.\-\+]+)*)?$'
        m = re.match(r, pkg_req)
        if m is not None:
            pkg_name = m.group(1)
            req_string = m.group(2)
            req_list = []
            if req_string is not None:
                for req in req_string.split(','):
                    req = req.strip()
                    if len(req) == 0:
                        continue # ignore empty requirements
                    if req[0] not in "<=>!":
                        req = '==' + req # add default operator
                    req_list.append(req)
            return pkg_name, req_list
        else:
            raise DistutilsSetupError(
                "%s package requirement has an invalid syntax: %r" %\
                (self.env, pkg_req)
            )

    def version_matches_req(self, version, req_list=None):
        """Test whether a version matches all version requirements in a list.
        This can be used for OS packages and for Python packages.

        Parameters:
        * version: A string specifying the version to be tested
          (e.g. '1.0.1-rc1')
        * req_list: None, or list of zero or more version requirements, or
          a single version requirement, each being a string of the form
          <op><version> (e.g. '>=1.0').
        """
        if not req_list:
            return True # no requirement -> version always matches

        if not isinstance(req_list, (list, tuple)):
            req_list = list(req_list)

        version_info = version.split(".")
        for req_string in req_list:
            m = re.match(r'^(<|<=|==|=|!=|>|>=)([0-9a-zA-Z_\.\-\+]+)$',
                         req_string)
            if m is None:
                raise DistutilsSetupError(
                    "Version requirement has an invalid syntax: %r" %\
                    req_string
                )
            req_op = m.group(1)
            req_version_info = m.group(2).split(".")
            if len(req_version_info) > len(version_info):
                raise DistutilsSetupError(
                    "Version requirement specifies too many version number "\
                    "components for the actual package: %r" % req_string
                )
            if req_op == '<':
                if not version_info < req_version_info:
                    return False
            elif req_op == '<=':
                if not version_info <= req_version_info:
                    return False
            elif req_op == '==':
                req_version_padded = req_version_info +\
                    [0] * (len(version_info) - len(req_version_info))
                if not version_info == req_version_padded:
                    return False
            elif req_op == '=':
                cmplen = len(req_version_info)
                if not version_info[0:cmplen] == req_version_info[0:cmplen]:
                    return False
            elif req_op == '!=':
                if not version_info != req_version_info:
                    return False
            elif req_op == '>':
                if not version_info > req_version_info:
                    return False
            elif req_op == '>=':
                if not version_info >= req_version_info:
                    return False
            else:
                raise DistutilsSetupError(
                    "Version requirement has an invalid syntax: %r" %\
                    req_string
                )
        return True

    def pkg_req(self, pkg_name, version_reqs):
        """Return a string from package name and list of version requirements.
        """
        req = pkg_name
        if version_reqs:
            req += " " + ", ".join(version_reqs)
        return req

    def record_error(self, pkg_name, version_reqs, msg_id):
        """Record an error. Errors will be queued and at the end will cause
        a DistutilsSetupError to be raised.
        """
        if msg_id not in self.errors:
            self.errors[msg_id] = list()
        if isinstance(pkg_name, (list, tuple)):
            req = str(pkg_name)
        else:
            req = self.pkg_req(pkg_name, version_reqs)
        self.errors[msg_id].append(req)

    def print_errors(self):
        """Print errors from the instance errors list"""
        for msg_id in self.errors:
            pkg_reqs = self.errors[msg_id]
            if msg_id == self.MSG_PLATFORM_NOT_SUPPORTED:
                msg = "Error: This platform (%s) is not supported for "\
                      "installation of %s packages.\n" % \
                      (self.platform, self.env)
                msg += "The following %s packages need to be "\
                       "verified and installed manually, if missing:\n"\
                       "    %s" % \
                       (self.env, "\n    ".join(pkg_reqs))
            elif msg_id == self.MSG_USER_NOT_AUTHORIZED:
                msg = "Error: This user (%s) is not authorized for "\
                      "installation of %s packages.\n" %\
                      (self.userid, self.env)
                msg += "The following %s packages are missing and need "\
                       "to be installed manually:\n"\
                       "    %s" %\
                       (self.env, "\n    ".join(pkg_reqs))
            elif msg_id == self.MSG_PKG_NOT_IN_REPOS:
                msg = "Error: The following %s packages are not in the "\
                      "repositories or do not have a sufficient version "\
                      "there and need to be obtained otherwise:\n"\
                       "    %s" %\
                       (self.env, "\n    ".join(pkg_reqs))
            else:
                raise DistutilsSetupError(
                    "Internal Error: Unexpected message ID: %s" % msg_id
                )
            print(msg)

class PythonInstaller(BaseInstaller):
    """Support for installing Python packages."""

    def __init__(self):
        BaseInstaller.__init__(self)
        self.env = "Python"

    def install_reqlist(self, req_list, dry_run, verbose):
        """
        Install the Python package requirements specified in a requirements
        list.

        Parameters:
            * req_list (iterable): Requirements list (see module description).
            * dry_run (boolean): Display what would happen instead of doing it.
            * verbose (boolean): Verbose mode. In verbose mode, all messages
              are printed. In quiet mode, only the most important messages are
              printed.
        """
        if req_list is not None:
            for req in req_list:
                self.install_req(req, dry_run, verbose)

    def install_req(self, req, dry_run, verbose):
        """
        Install the Python package requirement specified in a requirement.

        Parameters:
            * req: Requirement (see module description).
            * dry_run (boolean): Display what would happen instead of doing it.
            * verbose (boolean): Verbose mode. In verbose mode, all messages
              are printed. In quiet mode, only the most important messages are
              printed.
        """
        if req is None:
            pass # ignore
        elif isinstance(req, types.FunctionType):
            req(self, dry_run, verbose)
        elif isinstance(req, (list, tuple)):  # requirements choice
            if verbose:
                print("Processing Python package requirement choice: %s" % req)
            success = False
            for single_req in req:
                if verbose:
                    print("Processing requirement choice item: %s" %\
                          single_req)
                pkg_name, version_reqs = self.parse_pkg_req(single_req)
                installed = self.ensure_installed(
                    pkg_name, version_reqs, dry_run, verbose, ignore=True)
                if installed:
                    success = True
                    break
            if not success:
                if verbose:
                    print("No package of Python package req choice is "\
                          "available in Pypi: %s" % req)
                self.record_error(req, None, self.MSG_PKG_NOT_IN_REPOS)
        else: # requirements string
            if verbose:
                print("Processing Python package requirement: %s" % req)
            pkg_name, version_reqs = self.parse_pkg_req(req)
            installed = self.ensure_installed(
                pkg_name, version_reqs, dry_run, verbose, ignore=False)

    def do_install(self, pkg_name, version_reqs=None, dry_run=False,
                   reinstall=False):
        """Install a Python package, optionally ensuring that the specified
        version requirements are satisfied.

        For a description of the parameters, return value and exceptions, see
        `BaseInstaller.do_install()`.
        """
        pkg_req = self.pkg_req(pkg_name, version_reqs)
        args = ['install']
        if reinstall:
            args.append('--ignore-installed')
        args.append(pkg_req)
        if dry_run:
            print("Dry-running: pip %s" % ' '.join(args))
        else:
            print("Running: pip %s" % ' '.join(args))
            rc = pip.main(args)
            if rc != 0:
                raise DistutilsSetupError("Pip returns rc=%d" % rc)

    def is_installed(self, pkg_name, version_reqs=None):
        """Test whether a Python package is installed, and optionally satisfies
        the specified version requirements.

        For a description of the parameters, return value and exceptions, see
        `BaseInstaller.is_installed()`.
        """
        cmd = "pip show %s" % pkg_name
        rc, out, _ = shell(cmd)
        if rc == 127:
            raise DistutilsSetupError("Pip command is not available")
        elif rc != 0:
            return (False, False, None)

        lines = out.splitlines()
        version_line = [line for line in lines
                        if line.startswith("Version:")][0]
        version = version_line.split()[1]
        version_sufficient = self.version_matches_req(version, version_reqs) \
                             if version_reqs else True
        return (True, version_sufficient, version)

    def is_available(self, pkg_name, version_reqs=None):
        """Test whether a Python package is available on Pypi, and optionally
        satisfies the specified version requirements.
        It does not matter for this function whether the package is already
        installed.

        For a description of the parameters, return value and exceptions, see
        `BaseInstaller.is_available()`.
        """
        # We use the internal functions of the pip module, because the pip
        # command line does not return version information from Pypi.
        # TODO: This is not supported on older pip versions (e.g. 1.4).
        search_command = pip.commands.search.SearchCommand()
        options, _ = search_command.parse_args([pkg_name])
        pypi_hits = search_command.search(pkg_name, options)
        hits = pip.commands.search.transform_hits(pypi_hits)
        for hit in hits:
            if hit['name'] == pkg_name:
                if not version_reqs:
                    versions = hit['versions']
                else:
                    versions = []
                    for _version in hit['versions']:
                        if self.version_matches_req(_version, version_reqs):
                            versions.append(_version)
                version_sufficient = len(versions) > 0
                return (True, version_sufficient, versions)

        return (False, False, None)

    def ensure_installed(self, pkg_name, version_reqs=None, dry_run=False,
                         verbose=True, ignore=False):
        """Ensure that a Python package is installed, and optionally satisfies
        the specified version requirements.

        For a description of the parameters, return value and exceptions, see
        `BaseInstaller.ensure_installed()`.
        """
        unused_inst, inst_sufficient, inst_version = \
            self.is_installed(pkg_name, version_reqs)

        if inst_sufficient:
            if verbose:
                print("Installed Python package version is sufficient: "\
                      "%s %s" % (pkg_name, inst_version))
            return True

        avail, avail_sufficient, unused_avail_versions = \
            self.is_available(pkg_name, version_reqs)

        if not avail:
            if not ignore:
                if verbose:
                    print("Python package is not available in Pypi: %s" %\
                          (pkg_name,))
                self.record_error(pkg_name, version_reqs,
                                  self.MSG_PKG_NOT_IN_REPOS)
            return False

        if not avail_sufficient:
            if not ignore:
                if verbose:
                    print("Python package is available in Pypi, but its "\
                          "versions are not sufficient: %s" %\
                          (pkg_name,))
                self.record_error(pkg_name, version_reqs,
                                  self.MSG_PKG_NOT_IN_REPOS)
            return False

        self.do_install(pkg_name, version_reqs, dry_run)
        return True


class OSInstaller(BaseInstaller):
    """Base class for installing OS packages."""

    def __init__(self):
        """Initialize this installer with information about the current
        operating system platform.
        """
        BaseInstaller.__init__(self)
        self.env = "OS"

        # Supported installers, by operating system platform
        self.installers = {
            "redhat": YumInstaller,
            "centos": YumInstaller,
            "fedora": YumInstaller,
            "debian": AptInstaller,
            "ubuntu": AptInstaller,
            "suse": ZypperInstaller,
        }

    def platform_installer(self):
        """Create and return an installer for this operating system platform."""
        try:
            platform_installer = self.installers[self.platform]
            return platform_installer()
        except KeyError:
            return self # limited function, i.e. it cannot install

    def supported(self):
        """Determine whether this operating system platform is supported for
        installation of OS packages."""
        return self.platform in self.installers

    def authorized(self):
        """Determine whether the current userid is authorized to install
        OS packages."""
        if self.system == "Linux":
            # TODO: Using sudo may ask for the sudo password. Find a better
            #       way of testing for authorization to install packages.
            #rc, _, _ = shell("sudo echo ok")
            #authorized = (rc == 0)
            authorized = True # For now...
        else:
            authorized = True
        return authorized

    def install_system(self, system_dict, dry_run, verbose):
        """
        Install the OS package requirements specified in a system dictionary,
        for the current system and distro.

        Parameters:
            * system_dict: System dictionary (see module description).
            * dry_run (boolean): Display what would happen instead of doing it.
            * verbose (boolean): Verbose mode. In verbose mode, all messages
              are printed. In quiet mode, only the most important messages are
              printed.
        """
        if system_dict is not None:
            system = self.system
            distro = self.distro
            if system in system_dict:
                system_item = system_dict[system]
                if isinstance(system_item, dict):
                    # The packages are specified by distro (e.g. Linux)
                    distro_dict = system_item
                    self.install_distro(distro, distro_dict, dry_run, verbose)
                elif isinstance(system_item, list):
                    # The packages are specified at system level (e.g. Windows)
                    req_list = system_item
                    self.install_reqlist(req_list, dry_run, verbose)
                else:
                    raise DistutilsSetupError(
                        "Invalid type %s for system entry: %r" %\
                        (type(system_item), system_item)
                    )

    def install_distro(self, distro, distro_dict, dry_run, verbose):
        """
        Install the OS package requirements specified in a distro dictionary,
        for the specified distro.

        Parameters:
            * distro (string): Distro ID (key in distro_dict).
            * distro_dict: Distro dictionary (see module description).
            * dry_run (boolean): Display what would happen instead of doing it.
            * verbose (boolean): Verbose mode. In verbose mode, all messages
              are printed. In quiet mode, only the most important messages are
              printed.
        """
        if distro in distro_dict:
            distro_item = distro_dict[distro]
            if isinstance(distro_item, list):
                # Normal case: the distro specifies a package list
                req_list = distro_item
                self.install_reqlist(req_list, dry_run, verbose)
            elif isinstance(distro_item, string_types):
                # The distro refers to another distro
                distro = distro_item
                self.install_distro(distro, distro_dict, dry_run, verbose)
            else:
                raise DistutilsSetupError(
                    "Invalid type %s for distro entry: %r" %\
                    (type(distro_item), distro_item)
                )

    def install_reqlist(self, req_list, dry_run, verbose):
        """
        Install the OS package requirements specified in a requirements list.

        Parameters:
            * req_list (iterable): Requirements list (see module description).
            * dry_run (boolean): Display what would happen instead of doing it.
            * verbose (boolean): Verbose mode. In verbose mode, all messages
              are printed. In quiet mode, only the most important messages are
              printed.
        """
        if req_list is not None:
            for req in req_list:
                self.install_req(req, dry_run, verbose)

    def install_req(self, req, dry_run, verbose):
        """
        Install the OS package requirement specified in a requirement.

        Parameters:
            * req: Requirement (see module description).
            * dry_run (boolean): Display what would happen instead of doing it.
            * verbose (boolean): Verbose mode. In verbose mode, all messages
              are printed. In quiet mode, only the most important messages are
              printed.
        """
        if req is None:
            pass # ignore
        elif isinstance(req, types.FunctionType):
            req(self, dry_run, verbose)
        elif isinstance(req, (list, tuple)):  # requirements choice
            if verbose:
                print("Processing OS package requirement choice: %s" % req)
            success = False
            for single_req in req:
                if verbose:
                    print("Processing requirement choice item: %s" %\
                          single_req)
                pkg_name, version_reqs = self.parse_pkg_req(single_req)
                installed = self.ensure_installed(
                    pkg_name, version_reqs, dry_run, verbose, ignore=True)
                if installed:
                    success = True
                    break
            if not success:
                if verbose:
                    print("No package of OS package req choice is "\
                          "available in the repos: %s" % req)
                self.record_error(req, None, self.MSG_PKG_NOT_IN_REPOS)
        else: # requirements string
            if verbose:
                print("Processing OS package requirement: %s" % req)
            pkg_name, version_reqs = self.parse_pkg_req(req)
            installed = self.ensure_installed(
                pkg_name, version_reqs, dry_run, verbose, ignore=False)

    def do_install(self, pkg_name, version_reqs=None, dry_run=False,
                   reinstall=False):
        """Install an OS package, optionally ensuring that the specified
        version requirements are satisfied.

        For a description of the parameters, return value and exceptions, see
        `BaseInstaller.do_install()`.
        """
        # The real code is in the subclass. If this code gets control, this
        # platform is not supported.
        self.record_error(pkg_name, version_reqs,
                          self.MSG_PLATFORM_NOT_SUPPORTED)

    def is_installed(self, pkg_name, version_reqs=None):
        """Test whether an OS package is installed, and optionally
        satisfies the specified version requirements.

        For a description of the parameters, return value and exceptions, see
        `BaseInstaller.is_installed()`.
        """
        # The real code is in the subclass. If this code gets control, there
        # is no subclass that handles this platform.
        self.record_error(pkg_name, version_reqs,
                          self.MSG_PLATFORM_NOT_SUPPORTED)
        return (False, False, None)

    def is_available(self, pkg_name, version_reqs=None):
        """Test whether an OS package is available in the repos, and
        optionally satisfies the specified version requirements.
        It does not matter for this function whether the package is already
        installed.

        For a description of the parameters, return value and exceptions, see
        `BaseInstaller.is_available()`.
        """
        # The real code is in the subclass. If this code gets control, there
        # is no subclass that handles this platform.
        self.record_error(pkg_name, version_reqs,
                          self.MSG_PLATFORM_NOT_SUPPORTED)
        return (False, False, None)

    def ensure_installed(self, pkg_name, version_reqs=None, dry_run=False,
                         verbose=True, ignore=False):
        """Ensure that an OS package is installed, and optionally
        satisfies the specified version requirements.

        For a description of the parameters, return value and exceptions, see
        `BaseInstaller.ensure_installed()`.
        """

        if not self.authorized():
            self.record_error(pkg_name, version_reqs,
                              self.MSG_USER_NOT_AUTHORIZED)
            return False

        if not self.supported():
            self.record_error(pkg_name, version_reqs,
                              self.MSG_PLATFORM_NOT_SUPPORTED)
            return False

        unused_inst, inst_sufficient, inst_version = \
            self.is_installed(pkg_name, version_reqs)

        if inst_sufficient:
            if verbose:
                print("Installed OS package version is sufficient: "\
                      "%s %s" % (pkg_name, inst_version))
            return True

        avail, avail_sufficient, unused_avail_versions = \
            self.is_available(pkg_name, version_reqs)

        if not avail:
            if not ignore:
                if verbose:
                    print("OS package is not available in repos: %s" %\
                          (pkg_name,))
                self.record_error(pkg_name, version_reqs,
                                  self.MSG_PKG_NOT_IN_REPOS)
            return False

        if not avail_sufficient:
            if not ignore:
                if verbose:
                    print("OS package is available in repos, but its "\
                          "versions are not sufficient: %s" %\
                          (pkg_name,))
                self.record_error(pkg_name, version_reqs,
                                  self.MSG_PKG_NOT_IN_REPOS)
            return False

        self.do_install(pkg_name, version_reqs, dry_run)
        return True


class YumInstaller(OSInstaller):
    """Installer for yum (or dnf) tool (e.g. RHEL, CentOS, Fedora).
    It uses the new dnf installer, if available in PATH (e.g. for Fedora 22)."""

    def __init__(self):
        OSInstaller.__init__(self)
        rc, _, _ = shell("which dnf")
        if rc == 0:
            self.installer_cmd = "dnf"
        else:
            self.installer_cmd = "yum"

    def do_install(self, pkg_name, version_reqs=None, dry_run=False,
                   reinstall=False):
        """Install an OS package, optionally ensuring that the specified
        version requirements are satisfied.

        For a description of the parameters, return value and exceptions, see
        `BaseInstaller.do_install()`.
        """
        subcmd = 'reinstall' if reinstall else 'install'
        cmd = "sudo %s %s -y %s" % (self.installer_cmd, subcmd, pkg_name)
        if dry_run:
            print("Dry-running: %s" % cmd)
        else:
            print("Running: %s" % cmd)
            shell_check(cmd, display=True)

    def is_installed(self, pkg_name, version_reqs=None):
        """Test whether an OS package is installed, and optionally
        satisfies the specified version requirements.

        For a description of the parameters, return value and exceptions, see
        `BaseInstaller.is_installed()`.
        """
        cmd = "%s list installed %s" % (self.installer_cmd, pkg_name)
        rc, out, err = shell(cmd)
        if rc != 0:
            return (False, False, None)

        info = out.splitlines()[-1].strip("\n").split()
        if not info[0].startswith(pkg_name+"."):
            raise DistutilsSetupError(
                "Unexpected output from command '%s':\n%s%s" %\
                (cmd, out, err))
        version = info[1].split("-")[0]
        version_sufficient = self.version_matches_req(version, version_reqs) \
                             if version_reqs else True
        return (True, version_sufficient, version)

    def is_available(self, pkg_name, version_reqs=None):
        """Test whether an OS package is available in the repos, and
        optionally satisfies the specified version requirements.
        It does not matter for this function whether the package is already
        installed.

        For a description of the parameters, return value and exceptions, see
        `BaseInstaller.is_available()`.
        """
        cmd = "%s list %s" % (self.installer_cmd, pkg_name)
        rc, out, err = shell(cmd)
        if rc != 0:
            return (False, False, None)

        info = out.splitlines()[-1].strip("\n").split()
        if not info[0].startswith(pkg_name+"."):
            raise DistutilsSetupError(
                "Unexpected output from command '%s':\n%s%s" %\
                (cmd, out, err))
        version = info[1].split("-")[0]
        version_sufficient = self.version_matches_req(version, version_reqs) \
                             if version_reqs else True
        return (True, version_sufficient, [version])

class AptInstaller(OSInstaller):
    """Installer for apt tool (e.g. Debian, Ubuntu)."""

    def __init__(self):
        OSInstaller.__init__(self)

    def do_install(self, pkg_name, version_reqs=None, dry_run=False,
                   reinstall=False):
        """Install an OS package, optionally ensuring that the specified
        version requirements are satisfied.

        For a description of the parameters, return value and exceptions, see
        `BaseInstaller.do_install()`.
        """
        reinstall_opt = '--reinstall' if reinstall else ''
        cmd = "sudo apt-get install -y %s %s" % (reinstall_opt, pkg_name)
        if dry_run:
            print("Dry-running: %s" % cmd)
        else:
            print("Running: %s" % cmd)
            shell_check(cmd, display=True)

    def is_installed(self, pkg_name, version_reqs=None):
        """Test whether an OS package is installed, and optionally
        satisfies the specified version requirements.

        For a description of the parameters, return value and exceptions, see
        `BaseInstaller.is_installed()`.
        """
        cmd = "dpkg -s %s" % pkg_name
        rc, out, err = shell(cmd)
        if rc != 0:
            return (False, False, None)

        lines = out.splitlines()
        status_line = [line for line in lines if line.startswith("Status:")][0]
        version_line = [line for line in lines
                        if line.startswith("Version:")][0]
        if status_line != "Status: install ok installed":
            raise DistutilsSetupError(
                "Unexpected status output from command '%s':\n"\
                "%s%s" % (cmd, out, err))
        version = version_line.split()[1].split("-")[0]
        if ":" in version:
            version = version.split(":")[1]
            # TODO: Add support for epoch number in the version
        version_sufficient = self.version_matches_req(version, version_reqs) \
                             if version_reqs else True
        return (True, version_sufficient, version)

    def is_available(self, pkg_name, version_reqs=None):
        """Test whether an OS package is available in the repos, and
        optionally satisfies a version requirement.
        It does not matter for this function whether the package is already
        installed.

        For a description of the parameters, return value and exceptions, see
        `BaseInstaller.is_available()`.
        """
        cmd = "apt show %s" % pkg_name
        rc, out, _ = shell(cmd)
        if rc != 0:
            return (False, False, None)

        lines = out.splitlines()
        version_line = [line for line in lines
                        if line.startswith("Version:")][0]
        version = version_line.split()[1].split("-")[0]
        version_sufficient = self.version_matches_req(version, version_reqs) \
                             if version_reqs else True
        return (True, version_sufficient, [version])

class ZypperInstaller(OSInstaller):
    """Installer for zypper tool (e.g. SLES, openSUSE)."""

    def __init__(self):
        OSInstaller.__init__(self)

    def do_install(self, pkg_name, version_reqs=None, dry_run=False,
                   reinstall=False):
        """Install an OS package, optionally ensuring that the specified
        version requirements are satisfied.

        For a description of the parameters, return value and exceptions, see
        `BaseInstaller.do_install()`.
        """
        reinstall_opt = '-f' if reinstall else ''
        cmd = "sudo zypper -y %s %s" % (reinstall_opt, pkg_name)
        if dry_run:
            print("Dry-running: %s" % cmd)
        else:
            print("Running: %s" % cmd)
            shell_check(cmd, display=True)

    def is_installed(self, pkg_name, version_reqs=None):
        """Test whether an OS package is installed, and optionally
        satisfies the specified version requirements.

        For a description of the parameters, return value and exceptions, see
        `BaseInstaller.is_installed()`.
        """
        cmd = "zypper info %s" % pkg_name
        rc, out, err = shell(cmd)
        if rc != 0:
            return (False, False, None)

        info = out.splitlines()[-1].strip("\n").split()
        if not info[0].startswith(pkg_name+"."):
            raise DistutilsSetupError(
                "Unexpected output from command '%s':\n%s%s" %\
                (cmd, out, err))
        version = info[1].split("-")[0]
        version_sufficient = self.version_matches_req(version, version_reqs) \
                             if version_reqs else True
        return (True, version_sufficient, version)

    def is_available(self, pkg_name, version_reqs=None):
        """Test whether an OS package is available in the repos, and
        optionally satisfies the specified version requirements.
        It does not matter for this function whether the package is already
        installed.

        For a description of the parameters, return value and exceptions, see
        `BaseInstaller.is_available()`.
        """
        cmd = "zypper info %s" % pkg_name
        _, out, _ = shell(cmd)
        # zypper always returns 0, and writes everything to stdout.
        lines = out.splitlines()
        version_lines = [line for line in lines if line.startswith("Version:")]
        if len(version_lines) == 0:
            return (False, False, None)

        version_line = version_lines[0]
        version = version_line.split()[1].split("-")[0]
        version_sufficient = self.version_matches_req(version, version_reqs) \
                             if version_reqs else True
        return (True, version_sufficient, [version])

def shell(command, display=False, ignore_notfound=False):
    """Execute a shell command and return its return code, stdout and stderr.

    Note that the simpler to use subprocess.check_output() requires
    Python 2.7, but we want to support Python 2.6 as well.

    Parameters:
      * command: string or list of strings with the command and its parameters.
      * display: boolean indicating whether the command output will be printed.
      * ignore_notfound: boolean indicating that command not found should be
        ignored. If the command is not found and this argument is True, the
        return code will be 10002 and stdout/stderr will be empty.

    Returns:
      * a tuple of:
        - return code of the command, as a number
        - stdout of the command, as a string
        - stderr of the command, as a string

    Raises:
      * If the command is not found, OSError is raised.
    """

    if isinstance(command, string_types):
        cmd_parts = command.split(" ")
    else:  # already a list
        cmd_parts = command

    encoded_cmd_parts = [part.encode("utf-8")
                         if isinstance(part, text_type)
                         else part for part in cmd_parts]
    try:
        p = subprocess.Popen(encoded_cmd_parts,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
    except OSError as exc:
        if exc.errno == 2 and ignore_notfound:
            return 10002, "", ""
        else:
            raise DistutilsSetupError(
                "Cannot execute %s: %s" % (cmd_parts[0], exc))

    if isinstance(stdout, binary_type):
        stdout = stdout.decode("utf-8")
    if isinstance(stderr, binary_type):
        stderr = stderr.decode("utf-8")

    # TODO: Add support for printing while command executes, like with 'tee'
    if display:
        if stdout != "":
            print(stdout)
        if stderr != "":
            print(stderr)

    return p.returncode, stdout, stderr

def shell_check(command, display=False, exp_rc=0):
    """Execute a shell command, check if its return code is 0, and if not,
    raise an exception.

    Parameters:
      * command: string or list of strings with the command and its parameters.
      * display: boolean indicating whether the command stdout will be printed.
      * rc: number or list of numbers indicating the allowable return codes.

    Returns:
      * stdout of the command, if it returns 0.

    Raises:
      * If the command is not found, OSError is raised.
      * If the command does not return 0, DistutilsSetupError is raised.
    """

    if isinstance(command, string_types):
        command = command.split(" ")

    if isinstance(exp_rc, int):
        exp_rc = [exp_rc]

    rc, out, err = shell(command, display)
    if rc not in exp_rc:
        err = err.strip(" ").strip("\n")
        out = out.strip(" ").strip("\n")
        if err != "":
            msg = err
        else:
            msg = out
        raise DistutilsSetupError(
            "%s returns rc=%d: %s" % (command[0], rc, msg))

    return out

def import_setuptools(min_version="12.0"):
    """Import the `setuptools` package.

    If it is not previously installed, or if it is installed but does not have
    the at least the specified minimum version, it is downloaded from PyPI
    and installed into the current Python environment (system or virtual
    environment), replacing a possibly existing version.

    This function requires ez_setup.py to be in the current directory or ini
    the Python module path.

    As of 10/2014, this article is a good overview on the various distribution
    packages for Python: http://stackoverflow.com/a/14753678.

    Parameters:
      * min_version: (string) The minimum required version of `setuptools`,
        e.g. "17.0".
    """

    try:
        import setuptools
    except ImportError:
        # Download and install from PyPI.
        import ez_setup
        ez_setup.use_setuptools(version=min_version)
        import setuptools
    else:
        if setuptools.__version__.split(".") < min_version.split("."):
            raise DistutilsSetupError(
                "The required version of setuptools (>=%s) is not available, "\
                "and can't be\n"\
                "installed while this script is running. Please install the "\
                "required version\n"\
                "first, using:\n"\
                "\n"\
                "    pip install --upgrade 'setuptools>=%s'\n" %\
                (min_version, min_version)
            )

