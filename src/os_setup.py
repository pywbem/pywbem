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
# Author: Andreas Maier <andreas.r.maier@gmx.de>
#

"""Extensions to `setuptools` for installation of OS-level packages and
Python packages for development mode.

The `setup.py` commands (in the command line of the script) that are
introduced or extended, are:

* `install_os` - a new command that installs prerequisite OS-level packages
  for the package that specifies it.
  The respective OS-level packages are defined in a new `install_os_requires`
  attribute of the `setup()` function.

* `develop_os` - a new command that installs prerequisite OS-level packages
  for the 'development mode' of the package that specifies it.
  The respective OS-level packages are defined in a new `develop_os_requires`
  attribute of the `setup()` function.

* `develop` - extends the `develop` command introduced by setuptools with
  the ability to install dependent Python packages.
  The respective Python packages are defined in a new `develop_requires`
  attribute of the `setup()` function.

Syntax for the new attributes of the `setup()` function:

* `install_os_requires` and `develop_os_requires`

  These attributes specify the OS-level package names and optionally a version
  requirement for each package. The package names are specific to the system
  as returned by `platform.system()`, and in case of the 'Linux' system, on
  the Linux distribution as returned by `platform.linux_distribution()` (as a
  short name). These attributes can also specify custom functions for handling
  more complex cases.

  The syntax is the same for both attributes. The following example shows the
  syntax:
  
      install_os_requires = {
          'Linux': {                        # system name
              'redhat': [                   # distribution name
                  "python-devel",           # a package without version requirement
                  "openssl-devel>=1.0.1",   # a package with version requirement
                  install_swig,             # a custom function
                  . . .
              ],
              . . .
          },
          . . .
      }

  The syntax for version requirements is:

      <op><version>

  Where:
  * <op> - the comparison operator, one of '<', '<=', '=', '>=', '>'.
  * <version> - the version to be compared against.

  Custom functions must have the following interface:

      def install_swig(command):
          . . .

  Where:

  * `command` - `setuptools.Command` object for the command in whose context
    this function is called.

    These command objects have a number of attributes. Some interesting ones
    are:

    * `command.osinstaller` - the OS installer object to be used if any
      OS-level packages need to be installed or tested for availability. See
      the `OSInstaller` class in this module for details.

    * `command.dry_run` - a boolean flag indicating whether a dry run
      should be done, vs. the real action. This is controlled by the
      `-n`, `--dry-run` command line option of the `setup.py` script.
  
* `develop_requires`

  This attribute has the same syntax as the `install_requires` attribute
  introduced by `setuptools`. It specifies the Python package names and
  optionally a version requirement for each package. The package names are Pypi
  package names. This attribute can also specify custom functions for handling
  more complex cases (like patching an installed package).

  The following example shows the syntax:
  
      develop_requires = [
          "httpretty",                  # a package without version requirement
          "epydoc>=3.0.1",              # a package with version requirement
          patch_epydoc,                 # a custom function
          . . .
      ]

  The syntax of version requirements and the interface of custom functions are
  the same as for the `install_os_requires` attribute, except that the
  `command` parameter does not have an `osinstaller` attribute.
"""

__version__ = "0.1.0"

import sys
import os
import re
import types
import subprocess
import platform
import pip
import optparse

from setuptools import Command, Distribution
from setuptools.command.develop import develop as _develop
from distutils.errors import DistutilsOptionError, DistutilsSetupError

class OsDistribution (Distribution):
    """Setuptools/distutils distribution class for installing OS-level
    packages."""

    def __init__(self, attrs=None):

        # Get 'develop_requires' attribute
        if attrs is not None:
            self.develop_requires = attrs.pop('develop_requires', {})
        elif not hasattr(self, "develop_requires"):
            self.develop_requires = {}
        _assert_requires(self, 'develop_requires',
                         self.develop_requires)

        # Get 'install_os_requires' attribute
        if attrs is not None:
            self.install_os_requires = attrs.pop('install_os_requires', {})
        elif not hasattr(self, "install_os_requires"):
            self.install_os_requires = {}
        _assert_os_requires(self, 'install_os_requires',
                            self.install_os_requires)

        # Get 'develop_os_requires' attribute
        if attrs is not None:
            self.develop_os_requires = attrs.pop('develop_os_requires', {})
        elif not hasattr(self, "develop_os_requires"):
            self.develop_os_requires = {}
        _assert_os_requires(self, 'develop_os_requires',
                            self.develop_os_requires)

        # Distribution is an old-style class in Python 2.6:
        Distribution.__init__(self, attrs)

def _assert_requires(dist, attr, value):
    """Validate the value of the 'develop_requires' attribute.

    The interface of this function is suitable for the newer setuptools
    'entry_points' concept; see
    https://pythonhosted.org/setuptools/setuptools.html#adding-setup-arguments

    Parameters:
    * dist: Distribution object
    * attr: Attribute name
    * value: Attribute value to be validated
    """
    req_list = value
    if not isinstance(req_list, list):
        raise DistutilsSetupError(
            "'%s' attribute: Value must be a list "\
            "(got type %s)" %\
            (attr, type(req_list))
        )
    for req in req_list:
        if not isinstance(req, (basestring, types.FunctionType)):
            raise DistutilsSetupError(
                "'%s' attribute: Requirement must be a string or a function "\
                "(got requirement %r of type %s)"%\
                (attr, req, type(req))
            )

def _assert_os_requires(dist, attr, value):
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
    for systemname in system_dict:
        if not isinstance(systemname, basestring):
            raise DistutilsSetupError(
                "'%s' attribute: Key in system dictionary must be "\
                "a string "\
                "(got key %r of type %s)" %\
                (attr, systemname, type(systemname))
            )
        distro_dict = system_dict[systemname]
        if not isinstance(distro_dict, dict):
            raise DistutilsSetupError(
                "'%s' attribute: Value in system dictionary must be "\
                "a dictionary of distributions "\
                "(for system %s, got type %s)" %\
                (attr, systemname, type(distro_dict))
            )
        for distroname in distro_dict:
            if not isinstance(distroname, basestring):
                raise DistutilsSetupError(
                    "'%s' attribute: Key in distribution dictionary must be "\
                    "a string "\
                    "(for system %s, got key %r of type %s)" %\
                    (attr, systemname, distroname, type(distroname))
                )
            req_list = distro_dict[distroname]
            if not isinstance(req_list, list):
                raise DistutilsSetupError(
                    "'%s' attribute: Value in distribution dictionary must be "\
                    "a list "\
                    "(for system %s, distro %s, got type %s)" %\
                    (attr, systemname, distroname, type(req_list))
                )
            for req in req_list:
                if not isinstance(req, (basestring, types.FunctionType)):
                    raise DistutilsSetupError(
                        "'%s' attribute: Requirement must be "\
                        "a string or a function "\
                        "(for system %s, distro %s, got requirement %r "\
                        "of type %s)"%\
                        (attr, systemname, distroname, req, type(req))
                    )

class BaseOsCommand (Command):
    """Setuptools/distutils command class; a base class for installing
    OS-level packages.
    """

    def __init__(self, dist, **kw):
        Command.__init__(self, dist, **kw)
        self.osinstaller = OSInstaller().platform_installer()

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run_os_system_dict(self, system_dict):
        if system_dict is not None:
            system = self.osinstaller.system()
            distro = self.osinstaller.distro()
            print "Installing prerequisite OS-level packages for "\
                  "system %s, distro %s" % (system, distro)
            if system in system_dict:
                distro_dict = system_dict[system]
                if distro in distro_dict:
                    req_list = distro_dict[distro]
                    if req_list is not None:
                        self.run_os_req_list(req_list)

    def run_os_req_list(self, req_list):
        for req in req_list:
            if isinstance(req, types.FunctionType):
                req(self)
            else: # requirements string
                req = req.strip()
                print "Processing OS-level package "\
                      "requirement: %s" % req
                m = re.match(
                  r'^([a-zA-Z0-9_\.\-\+]+)'\
                  '( *(<|<=|=|>|>=) *([0-9a-zA-Z_\.\-\+]+))?$',
                  req)
                if m is not None:
                    pkg_name = m.group(1)
                    version_req = m.group(2)
                    self.osinstaller.ensure_installed(
                        pkg_name, version_req, self.dry_run)
                else:
                    raise DistutilsSetupError(
                        "OS-level package requirement for "\
                        "system %s, distro %s has invalid "\
                        "syntax: %r" %\
                        (system, distro, req)
                    )
        if self.osinstaller._failed:
            if self.osinstaller._continue:
                print \
                  "Cannot install prerequisite OS-level "\
                  "packages: %s\n"\
                  "Continuing anyway..." %\
                  self.osinstaller._reason
            else:
                raise DistutilsSetupError(
                  "Cannot install prerequisite OS-level "\
                  "packages: %s\n"\
                  "Please install the following packages "\
                  "manually, and retry:\n"\
                  "\n"\
                  "    %s" %\
                  (self.osinstaller._reason,
                   "\n    ".join(
                     self.osinstaller._manual_packages)))

class install_os (BaseOsCommand):
    """Setuptools/distutils command class for installing OS-level packages
    in 'normal mode', i.e. when the user specifies the 'install_os' command.
    """

    description = "install prerequisite OS-level packages for this package."

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
        self.run_os_system_dict(self.distribution.install_os_requires)

class develop_os (BaseOsCommand):
    """Setuptools/distutils command class for installing OS-level packages for
    'development mode', i.e. when the user specifies the 'develop_os' command.
    """

    description = "install prerequisite OS-level packages for 'development "\
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
        self.run_os_system_dict(self.distribution.install_os_requires)
        self.run_os_system_dict(self.distribution.develop_os_requires)

class develop (_develop):
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
        req_list = self.distribution.develop_requires
        for req in req_list:
            if isinstance(req, types.FunctionType):
                req(self)
            else: # requirements string
                req = req.strip()
                print "Processing Python package requirement: %s" % req
                pkg_name, version_req = self.installer.parse_pkg_req(req)
                self.installer.ensure_installed(
                    pkg_name, version_req, self.dry_run)

        _develop.run(self)

class BaseInstaller (object):
    """Base class for installing OS-level packages and Python packages."""

    def install(self, pkg_name, version_req=None, dry_run=False):
        """Interface definition: Install an OS-level or Python package,
        optionally applying  a version requirement.

        Parameters:
        * pkg_name (string): Name of the package.
        * version_req (string): Version requirement for the package
          (e.g. '>=3.0').
        * dry_run (boolean): Display what would happen instead of doing it.

        Raises:
        * If installation fails, raises a DistutilsSetupError exception.
        """
        raise NotImplemented

    def is_installed(self, pkg_name, version_req=None):
        """Interface definition: Test whether an OS-level or Python package
        is installed, and optionally satisfies a version requirement.

        Parameters:
        * pkg_name (string): Name of the Python package.
        * version_req (string): Version requirement for the package
          (e.g. '>=3.0').

        Returns:
        * If a package version that satisfies the requirement is installed, its
          version is returned as a string. Otherwise, False is returned.
        """
        raise NotImplemented

    def is_available(self, pkg_name, version_req=None):
        """Interface definition: Test whether an OS-level or Python package
        is available in the repos (for OS-level packages) or on Pypi (for
        Python packages), and optionally satisfies a version requirement.
        It does not matter for this function whether the package is already
        installed.

        Parameters:
        * pkg_name (string): Name of the Python package.
        * version_req (string): Version requirement for the package
          (e.g. '>=3.0').

        Returns:
        * If a package version that satisfies the requirement is available, its
          version is returned as a string. Otherwise, False is returned.
        """
        raise NotImplemented

    def ensure_installed(self, pkg_name, version_req=None, dry_run=False):
        """Interface definition: Ensure that an OS-level or Python package
        is installed, and optionally satisfies a version requirement.

        Parameters:
        * pkg_name (string): Name of the Python package.
        * version_req (string): Version requirement for the package
          (e.g. '>=3.0').
        * dry_run (boolean): Display what would happen instead of doing it.

        Raises:
        * If installation fails, raises a DistutilsSetupError exception.
        """
        raise NotImplemented

    def parse_pkg_req(self, pkg_req):
        """Parse a package requirement string and return a tuple of package name
        and version requirement. This can be used for OS-level packages and for
        Python packages.

        Parameters:
        * pkg_req: A string specifying the package requirement (e.g. 'abc>=1.0')

        Returns:
        * tuple of:
          - A string specifying the package name (e.g. 'abc')
          - A string specifying the version requirement (e.g. '>=1.0'). Empty
            string, if no version requirement was specified.
        """
        m = re.match(
          r'^([0-9a-zA-Z_\.\-\+]+)( *(<|<=|=||>|>=) *([0-9a-zA-Z_\.\-\+]+))?$',
          pkg_req)
        if m is not None:
            pkg_name = m.group(1)
            pkg_version_req = m.group(2)
            return pkg_name, pkg_version_req
        else:
            raise DistutilsSetupError(
                "Package requirement has an invalid syntax: %r" % pkg_req
            )

    def version_matches_req(self, version, version_req=None):
        """Test whether a version matches a version requirement.

        Parameters:
        * version: A string specifying the version to be tested
          (e.g. '1.0.1-rc1')
        * version_req: A string specifying a version requirement (e.g. '>=1.0')
        """
        if version_req:
            version_info = version.split(".")
            version_req = version_req.strip()
            m = re.match(
              r'^(<|<=|=||>|>=) *([0-9a-zA-Z_\.\-\+]+)$',
              version_req)
            if m is not None:
                req_op = m.group(1)
                req_version = m.group(2)
                req_version_info = req_version.split(".")
                if req_op == '<':
                    return version_info < req_version_info
                elif req_op == '<=':
                    return version_info <= req_version_info
                elif req_op == '=' or req_op == '':
                    return version_info == req_version_info
                elif req_op == '>':
                    return version_info > req_version_info
                elif req_op == '>=':
                    return version_info >= req_version_info
                else:
                    raise DistutilsSetupError(
                        "Version requirement has an invalid syntax: %r" %\
                        version_req
                    )
            else:
                raise DistutilsSetupError(
                    "Version requirement has an invalid syntax: %r" %\
                    version_req
                )
        else:
            return True # no requirement -> version always matches

class PythonInstaller (BaseInstaller):
    """Support for installing Python packages."""

    def install(self, pkg_name, version_req=None, dry_run=False):
        """Install a Python package, optionally applying  a version
        requirement.

        Parameters:
        * pkg_name (string): Name of the package.
        * version_req (string): Version requirement for the package
          (e.g. '>=3.0').
        * dry_run (boolean): Display what would happen instead of doing it.

        Raises:
        * If installation fails, raises a DistutilsSetupError exception.
        """
        pkg_req = pkg_name + (version_req or "")
        if dry_run:
            print "Dry-running: pip install %s" % pkg_req
            return 0
        else:
            print "Running: pip install %s" % pkg_req
            rc = pip.main(['install', pkg_req])
            if rc != 0:
                raise DistutilsSetupError(
                    "Pip returns rc=%d" % rc
                )
            return rc

    def is_installed(self, pkg_name, version_req=None):
        """Test whether a Python package is installed, and optionally satisfies
        a version requirement.

        Parameters:
        * pkg_name (string): Name of the package.
        * version_req (string): Version requirement for the package
          (e.g. '>=3.0').

        Returns:
        * If a package version that satisfies the requirement is installed, its
          version is returned as a string. Otherwise, False is returned.
        """
        info = list(pip.commands.show.search_packages_info([pkg_name]))
        # TODO: Implement support for version requirement
        installed = len(info) > 0
        # TODO: Return installed version, or False
        return installed

    def is_available(self, pkg_name, version_req=None):
        """Test whether a Python package is available on Pypi, and optionally
        satisfies a version requirement.
        It does not matter for this function whether the package is already
        installed.

        Parameters:
        * pkg_name (string): Name of the package.
        * version_req (string): Version requirement for the package
          (e.g. '>=3.0').

        Returns:
        * If a package version that satisfies the requirement is available, its
          version is returned as a string. Otherwise, False is returned.
        """
        search_command = pip.commands.search.SearchCommand()
        options, args = search_command.parse_args([pkg_name])
        pypi_hits = search_command.search(pkg_name, options)
        hits = pip.commands.search.transform_hits(pypi_hits)
        for hit in hits:
            if hit['name'] == pkg_name:
                for available_version in hit['versions']:
                    if self.version_matches_req(available_version, version_req):
                        return available_version
        return False

    def ensure_installed(self, pkg_name, version_req=None, dry_run=False):
        """Ensure that a Python package is installed, and optionally satisfies
        a version requirement.

        Parameters:
        * pkg_name (string): Name of the package.
        * version_req (string): Version requirement for the package
          (e.g. '>=3.0').
        * dry_run (boolean): Display what would happen instead of doing it.

        Raises:
        * If installation fails, raises a DistutilsSetupError exception.
        """
        pkg_req = pkg_name + (version_req or "")
        if not self.is_installed(pkg_name, version_req):
            self.install(pkg_name, version_req, dry_run)

class OSInstaller (BaseInstaller):
    """Base class for installing OS-level packages."""

    def __init__(self):
        """Initialize this installer with information about the current
        operating system platform."""

        # Operating system name (e.g. "Windows", "Linux")
        self._system = platform.system()

        # Linux distribution name, using the short names returned by
        # platform.linux_distribution()
        self._distro = None

        # Name of operating system platform (_system or _distro)
        self._platform = self._system

        if self._system == "Linux":
            self._distro = platform.linux_distribution(
                               full_distribution_name=False)[0].lower()
            self._platform = self._distro

        # Supported installers, by operating system platform
        self._installers = {
            "redhat": RedhatInstaller,
            "centos": RedhatInstaller,
            "fedora": RedhatInstaller,
            "debian": DebianInstaller,
            "ubuntu": DebianInstaller,
            "suse": SuseInstaller,
        }

        # Failure indicators
        self._failed = False
        self._reason = None
        self._continue = False

        # List of OS-level packages to be installed manually, if
        # automatic installation is not possible.
        self._manual_packages = []

    def platform_installer(self):
        """Create and return an installer for this operating system platform."""
        try:
            platform_installer = self._installers[self._platform]
            return platform_installer()
        except KeyError:
            return self # limited function, i.e. it cannot install

    def platform(self):
        """Return the name of this operating system platform."""
        return self._platform

    def system(self):
        """Return the name of this operating system (e.g. Windows, Linux)."""
        return self._system

    def distro(self):
        """Return the name of this Linux distribution, or None if this is not a
        Linux operating system."""
        return self._distro

    def supported(self):
        """Determine whether this operating system platform is supported for
        installation of OS-level packages."""
        return self._platform in self._installers

    def authorized(self):
        """Determine whether the current userid is authorized to install
        OS-level packages."""
        if self._system == "Linux":
            rc, _, _ = shell("sudo -v") # this may ask for a password
            authorized = (rc == 0)
        else:
            authorized = True
        return authorized

    def install(self, pkg_name, version_req=None, dry_run=False):
        """Install an OS-level package, optionally applying a version
        requirement.

        Parameters:
        * pkg_name (string): Name of the package.
        * version_req (string): Version requirement for the package
          (e.g. '>=3.0').
        * dry_run (boolean): Display what would happen instead of doing it.

        Raises:
        * If installation fails, raises a DistutilsSetupError exception.
        """

        # The real code is in the subclass. If this code gets control, there
        # is no subclass that handles this platform.
        pkg_req = pkg_name + (version_req or "")
        if not self.supported():
            self._failed = True
            self._continue = True # we try anyway
            self._reason = "This operating system platform (%s) is not "\
                           "supported for automatic installation of "\
                           "OS-level pre-requisites." % self.platform()
            self._manual_packages.append(pkg_req)
            return
        raise NotImplemented

    def is_installed(self, pkg_name, version_req=None):
        """Test whether an OS-level package is installed, and optionally
        satisfies a version requirement.

        Parameters:
        * pkg_name (string): Name of the package.
        * version_req (string): Version requirement for the package
          (e.g. '>=3.0').

        Returns:
        * Boolean indicating whether the package is installed.
        """

        # The real code is in the subclass. If this code gets control, there
        # is no subclass that handles this platform.
        pkg_req = pkg_name + (version_req or "")
        if not self.supported():
            self._failed = True
            self._continue = True # we try anyway
            self._reason = "This operating system platform (%s) is not "\
                           "supported for automatic installation of "\
                           "OS-level pre-requisites." % self.platform()
            self._manual_packages.append(pkg_req)
            return
        raise NotImplemented

    def is_available(self, pkg_name, version_req=None):
        """Test whether an OS-level package is available in the repos, and
        optionally satisfies a version requirement.
        It does not matter for this function whether the package is already
        installed.

        Parameters:
        * pkg_name (string): Name of the package.
        * version_req (string): Version requirement for the package
          (e.g. '>=3.0').

        Returns:
        * If a package version that satisfies the requirement is available, its
          version is returned as a string. Otherwise, False is returned.
        """

        # The real code is in the subclass. If this code gets control, there
        # is no subclass that handles this platform.
        pkg_req = pkg_name + (version_req or "")
        if not self.supported():
            self._failed = True
            self._continue = True # we try anyway
            self._reason = "This operating system platform (%s) is not "\
                           "supported for automatic installation of "\
                           "OS-level pre-requisites." % self.platform()
            self._manual_packages.append(pkg_req)
            return
        raise NotImplemented

    def ensure_installed(self, pkg_name, version_req=None, dry_run=False):
        """Ensure that an OS-level package is installed, and optionally
        satisfies a version requirement.

        Parameters:
        * pkg_name (string): Name of the package.
        * version_req (string): Version requirement for the package
          (e.g. '>=3.0').
        * dry_run (boolean): Display what would happen instead of doing it.

        Raises:
        * If installation fails, raises a DistutilsSetupError exception.
        """

        # The real code is in the subclass. If this code gets control, there
        # is no subclass that handles this platform.
        pkg_req = pkg_name + (version_req or "")
        if not self.supported():
            self._failed = True
            self._continue = True # we try anyway
            self._reason = "This operating system platform (%s) is not "\
                           "supported for automatic installation of "\
                           "OS-level pre-requisites." % self.platform()
            self._manual_packages.append(pkg_req)
            return
        if not self.is_installed(pkg_name, version_req):
            self.install(pkg_name, version_req, dry_run)

class RedhatInstaller (OSInstaller):
    """Installer for Redhat-based distributions (e.g. RHEL, CentOS, Fedora).
    It uses the new dnf installer for Fedora>=22."""

    def _installer_cmd(self):
        """Return the installer command."""
        if self._distro == "fedora" and \
            int(platform.linux_distribution()[1]) >= 22:
            return "dnf"
        else:
            return "yum"

    def install(self, pkg_name, version_req=None, dry_run=False):
        """Install an OS-level package, optionally applying a version
        requirement.

        Parameters:
        * pkg_name (string): Name of the package.
        * version_req (string): Version requirement for the package
          (e.g. '>=3.0').
        * dry_run (boolean): Display what would happen instead of doing it.

        Raises:
        * If installation fails, raises a DistutilsSetupError exception.
        """
        pkg_req = pkg_name + (version_req or "")
        if not self.authorized():
            self._failed = True
            self._continue = False # we know that some packages are missing
            self._reason = "This userid is not authorized to install OS-level "\
                           "packages."
            self._manual_packages.append(pkg_req)
        elif not self.is_available(pkg_name, version_req, display=False):
            self._failed = True
            self._continue = True
            self._reason = "OS-level package not available in repositories"
            self._manual_packages.append(pkg_req)
        else:
            cmd = "sudo %s install -y %s" %\
                 (self._installer_cmd(), pkg_name)
            if dry_run:
                print "Dry-running: %s" % cmd
            else:
                print "Running: %s" % cmd
                shell_check(cmd, display=True)

    def is_installed(self, pkg_name, version_req=None):
        """Test whether an OS-level package is installed, and optionally
        satisfies a version requirement.

        Parameters:
        * pkg_name (string): Name of the package.
        * version_req (string): Version requirement for the package
          (e.g. '>=3.0').

        Returns:
        * Boolean indicating whether the package is installed.
        """
        cmd = "%s list installed %s" % (self._installer_cmd(), pkg_name)
        rc, out, err = shell(cmd)
        if rc != 0:
            print "Package is not installed: %s" % pkg_name
            return False
        info = out.splitlines()[-1].strip("\n").split()
        if not info[0].startswith(pkg_name+"."):
            raise DistutilsSetupError(
                "Unexpected output from command '%s':\n%s%s" %\
                (cmd, out, err))
        version = info[1].split("-")[0]
        if version_req is not None:
            version_sufficient = self.version_matches_req(
                version, version_req)
            if version_sufficient:
                print "Installed package version is sufficient: "\
                    "%s %s" % (pkg_name, version)
            else:
                print "Installed package version is not sufficient: "\
                    "%s %s" % (pkg_name, version)
            return version_sufficient
        else:
            print "Installed package version is sufficient: "\
                "%s %s" % (pkg_name, version)
            return True

    def is_available(self, pkg_name, version_req=None, display=True):
        """Test whether an OS-level package is available in the repos, and
        optionally satisfies a version requirement.
        It does not matter for this function whether the package is already
        installed.

        Parameters:
        * pkg_name (string): Name of the package.
        * version_req (string): Version requirement for the package
          (e.g. '>=3.0').
        * display (boolean): Print messages.

        Returns:
        * If a package version that satisfies the requirement is available, its
          version is returned as a string. Otherwise, False is returned.
        """
        cmd = "%s list %s" % (self._installer_cmd(), pkg_name)
        rc, out, err = shell(cmd)
        if rc != 0:
            if display:
                print "Package is not available in repositories: %s" %\
                    pkg_name
            return False
        info = out.splitlines()[-1].strip("\n").split()
        if not info[0].startswith(pkg_name+"."):
            raise DistutilsSetupError(
                "Unexpected output from command '%s':\n%s%s" %\
                (cmd, out, err))
        version = info[1].split("-")[0]
        if version_req is not None:
            version_sufficient = self.version_matches_req(
                version, version_req)
            if display:
                if version_sufficient:
                    print "Package version available in repositories is "\
                        "sufficient: %s %s" % (pkg_name, version)
                else:
                    print "Package version available in repositories is "\
                        "not sufficient: %s %s" % (pkg_name, version)
            return version_sufficient
        else:
            if display:
                print "Package version available in repositories is "\
                    "sufficient: %s %s" % (pkg_name, version)
            return True

class DebianInstaller (OSInstaller):
    """Installer for Debian-based distributions (e.g. Debian, Ubuntu)."""

    def install(self, pkg_name, version_req=None, dry_run=False):
        """Install an OS-level package, optionally applying a version
        requirement.

        Parameters:
        * pkg_name (string): Name of the package.
        * version_req (string): Version requirement for the package
          (e.g. '>=3.0').
        * dry_run (boolean): Display what would happen instead of doing it.

        Raises:
        * If installation fails, raises a DistutilsSetupError exception.
        """
        pkg_req = pkg_name + (version_req or "")
        if not self.authorized():
            self._failed = True
            self._continue = False # we know that some packages are missing
            self._reason = "This userid is not authorized to install OS-level "\
                           "packages."
            self._manual_packages.append(pkg_req)
        elif not self.is_available(pkg_name, version_req, display=False):
            self._failed = True
            self._continue = True
            self._reason = "OS-level package not available in repositories"
            self._manual_packages.append(pkg_req)
        else:
            cmd = "sudo apt-get install -y %s" % pkg_name
            if dry_run:
                print "Dry-running: %s" % cmd
            else:
                print "Running: %s" % cmd
                shell_check(cmd, display=True)

    def is_installed(self, pkg_name, version_req=None):
        """Test whether an OS-level package is installed, and optionally
        satisfies a version requirement.

        Parameters:
        * pkg_name (string): Name of the package.
        * version_req (string): Version requirement for the package
          (e.g. '>=3.0').

        Returns:
        * Boolean indicating whether the package is installed.
        """
        cmd = "dpkg -s %s" % pkg_name
        rc, out, err = shell(cmd)
        if rc != 0:
            print "Package is not installed: %s" % pkg_name
            return False
        lines = out.splitlines()
        status_line = [line for line in lines if line.startswith("Status:")][0]
        version_line = [line for line in lines if line.startswith("Version:")][0]
        if status_line != "Status: install ok installed":
            raise DistutilsSetupError(
                "Unexpected status output from command '%s':\n"\
                "%s%s" % (cmd, out, err))
        version = version_line.split()[1].split("-")[0]
        if ":" in version:
            version = version.split(":")[1]
            # TODO: Add support for epoch number in the version
        if version_req is not None:
            version_sufficient = self.version_matches_req(
                version, version_req)
            if version_sufficient:
                print "Installed package version is sufficient: "\
                    "%s %s" % (pkg_name, version)
            else:
                print "Installed package version is not sufficient: "\
                    "%s %s" % (pkg_name, version)
            return version_sufficient
        else:
            print "Installed package version is sufficient: "\
                "%s %s" % (pkg_name, version)
            return True

    def is_available(self, pkg_name, version_req=None, display=True):
        """Test whether an OS-level package is available in the repos, and
        optionally satisfies a version requirement.
        It does not matter for this function whether the package is already
        installed.

        Parameters:
        * pkg_name (string): Name of the package.
        * version_req (string): Version requirement for the package
          (e.g. '>=3.0').
        * display (boolean): Print messages.

        Returns:
        * If a package version that satisfies the requirement is available, its
          version is returned as a string. Otherwise, False is returned.
        """
        cmd = "apt show %s" % pkg_name
        rc, out, err = shell(cmd)
        if rc != 0:
            if display:
                print "Package is not available in repositories: %s" %\
                    pkg_name
            return False
        lines = out.splitlines()
        version_line = [line for line in lines if line.startswith("Version:")][0]
        version = version_line.split()[1].split("-")[0]
        if version_req is not None:
            version_sufficient = self.version_matches_req(
                version, version_req)
            if display:
                if version_sufficient:
                    print "Package version available in repositories is "\
                        "sufficient: %s %s" % (pkg_name, version)
                else:
                    print "Package version available in repositories is "\
                        "not sufficient: %s %s" % (pkg_name, version)
            return version_sufficient
        else:
            if display:
                print "Package version available in repositories is "\
                    "sufficient: %s %s" % (pkg_name, version)
            return True

class SuseInstaller (OSInstaller):
    """Installer for Suse-based distributions (e.g. SLES, openSUSE)."""

    def install(self, pkg_name, version_req=None, dry_run=False):
        """Install an OS-level package, optionally applying a version
        requirement.

        Parameters:
        * pkg_name (string): Name of the package.
        * version_req (string): Version requirement for the package
          (e.g. '>=3.0').
        * dry_run (boolean): Display what would happen instead of doing it.

        Raises:
        * If installation fails, raises a DistutilsSetupError exception.
        """
        pkg_req = pkg_name + (version_req or "")
        if not self.authorized():
            self._failed = True
            self._continue = False # we know that some packages are missing
            self._reason = "This userid is not authorized to install OS-level "\
                           "packages."
            self._manual_packages.append(pkg_req)
        elif not self.is_available(pkg_name, version_req, display=False):
            self._failed = True
            self._continue = True
            self._reason = "OS-level package not available in repositories"
            self._manual_packages.append(pkg_req)
        else:
            cmd = "sudo yum zypper -y %s" % pkg_name
            if dry_run:
                print "Dry-running: %s" % cmd
            else:
                print "Running: %s" % cmd
                shell_check(cmd, display=True)

    def is_installed(self, pkg_name, version_req=None):
        """Test whether an OS-level package is installed, and optionally
        satisfies a version requirement.

        Parameters:
        * pkg_name (string): Name of the package.
        * version_req (string): Version requirement for the package
          (e.g. '>=3.0').

        Returns:
        * Boolean indicating whether the package is installed.
        """
        cmd = "zypper info %s" % pkg_name
        rc, out, err = shell(cmd)
        if rc != 0:
            print "Package is not installed: %s" % pkg_name
            return False
        info = out.splitlines()[-1].strip("\n").split()
        if not info[0].startswith(pkg_name+"."):
            raise DistutilsSetupError(
                "Unexpected output from command '%s':\n%s%s" %\
                (cmd, out, err))
        version = info[1].split("-")[0]
        if version_req is not None:
            version_sufficient = self.version_matches_req(
                version, version_req)
            if version_sufficient:
                print "Installed package version is sufficient: "\
                    "%s %s" % (pkg_name, version)
            else:
                print "Installed package version is not sufficient: "\
                    "%s %s" % (pkg_name, version)
            return version_sufficient
        else:
            print "Installed package version is sufficient: "\
                "%s %s" % (pkg_name, version)
            return True

    def is_available(self, pkg_name, version_req=None, display=True):
        """Test whether an OS-level package is available in the repos, and
        optionally satisfies a version requirement.
        It does not matter for this function whether the package is already
        installed.

        Parameters:
        * pkg_name (string): Name of the package.
        * version_req (string): Version requirement for the package
          (e.g. '>=3.0').
        * display (boolean): Print messages.

        Returns:
        * If a package version that satisfies the requirement is available, its
          version is returned as a string. Otherwise, False is returned.
        """
        cmd = "zypper info %s" % pkg_name
        rc, out, err = shell(cmd)
        # zypper always returns 0, and writes everything to stdout.
        lines = out.splitlines()
        version_lines = [line for line in lines if line.startswith("Version:")]
        if len(version_lines) == 0:
            if display:
                print "Package is not available in repositories: %s" %\
                    pkg_name
            return False
        version_line = version_lines[0]
        version = version_line.split()[1].split("-")[0]
        if version_req is not None:
            version_sufficient = self.version_matches_req(
                version, version_req)
            if display:
                if version_sufficient:
                    print "Package version available in repositories is "\
                        "sufficient: %s %s" % (pkg_name, version)
                else:
                    print "Package version available in repositories is "\
                        "not sufficient: %s %s" % (pkg_name, version)
            return version_sufficient
        else:
            if display:
                print "Package version available in repositories is "\
                    "sufficient: %s %s" % (pkg_name, version)
            return True

def shell(command, display=False):
    """Execute a shell command and return its return code, stdout and stderr.

    Note that the simpler to use subprocess.check_output() requires
    Python 2.7, but we want to support Python 2.6 as well.

    Parameters:

      * command: string or list of strings with the command and its parameters.
      * display: boolean indicating whether the command output will be printed.

    Returns:

      * a tuple of:
        - return code of the command, as a number
        - stdout of the command, as a string
        - stderr of the command, as a string

    Exceptions:

      * If the command is not found, OSError is raised.
    """

    if isinstance(command, basestring):
        command = command.split(" ")

    try:
        p = subprocess.Popen(command,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
    except OSError as exc:
        raise DistutilsSetupError(
            "Cannot execute %s: %s" % (command[0], exc))

    # TODO: Add support for printing while command executes, like with 'tee'
    if display:
        if stdout != "":
            print stdout
        if stderr != "":
            print stderr

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

    Exceptions:

      * If the command is not found, OSError is raised.
      * If the command does not return 0, DistutilsSetupError is raised.
    """

    if isinstance(command, basestring):
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
"""The required version of setuptools (>=%s) is not available, and can't be
installed while this script is running. Please install the required version
first, using:

    pip install --upgrade setuptools>=%s
""" % (min_version, min_version))

