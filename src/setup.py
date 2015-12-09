#
# (C) Copyright 2004 Hewlett-Packard Development Company, L.P.
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
# Author: Tim Potter <tpot@hp.com>
#

"""
PyWBEM is a WBEM client and some related utilities, written in pure Python.

A WBEM client allows issuing operations to a WBEM server, using the CIM
operations over HTTP (CIM-XML) protocol defined in the DMTF standards DSP0200
and DSP0201. See http://www.dmtf.org/standards/wbem for information about
WBEM. This is used for all kinds of systems management tasks that are
supported by the system running the WBEM server.
"""

# Package version - Keep in sync with pywbem/__init__.py!
_version = '0.8.0-rc2'

# Control printing of debug messages
DEBUG = False

# Dry-run any OS-level install commands
DRY_RUN = False

import re
import sys
import os
import subprocess
import platform
import shutil

class SetupError(Exception):
    """Exception that causes this setup script to fail."""
    pass

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

    if DEBUG:
        print "Running: %s" % " ".join(command)

    try:
        p = subprocess.Popen(command,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
    except OSError as exc:
        raise SetupError("Cannot execute %s: %s" % (command[0], exc))

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
      * If the command does not return 0, SetupError is raised.
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
        raise SetupError("%s returns rc=%d: %s" % (command[0], rc, msg))

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
            raise SetupError(
"""The required version of setuptools (>=%s) is not available, and can't be
installed while this script is running. Please install the required version
first, using:

    pip install --upgrade setuptools>=%s
""" % (min_version, min_version))

class OSInstaller(object):
    """Support for installing OS-level packages."""

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

    def platform_pkg_name(self, generic_pkg_name):
        """Return the platform-specific package name, given the
        generic package name."""
        try:
            platform_pkg_name = self.PLATFORM_PACKAGES[generic_pkg_name]
        except KeyError:
            raise SetupError("Internal Error: No information about OS-level "\
                "package %s for operating system platform %s" %\
                (generic_pkg_name, self.platform()))
        return platform_pkg_name

    def do_install(self, platform_pkg_name, min_version=None, pkg_brief=None):
        """Install an OS-level package with a specific minimum version.
        None for `min_version` will install the latest available version."""
        # The real code is in the subclass. If this code gets control, there
        # is no subclass that handles this platform.
        if not self.supported():
            self._failed = True
            self._continue = True # we try anyway
            self._reason = "This operating system platform (%s) is not "\
                           "supported for automatic installation of "\
                           "pre-requisites." % self.platform()
            self._manual_packages.append(platform_pkg_name)
            return
        raise NotImplemented

    def is_installed(self, platform_pkg_name, min_version=None):
        """Test whether an OS-level package is installed and has a specific
        minimum version.
        None for `min_version` will test just for being installed, but not for a
        particular version."""
        if not self.supported():
            self._failed = True
            self._continue = True # we try anyway
            self._reason = "This operating system platform (%s) is not "\
                           "supported for automatic installation of "\
                           "pre-requisites." % self.platform()
            self._manual_packages.append(platform_pkg_name)
            return
        raise NotImplemented

    def is_available(self, platform_pkg_name, min_version=None):
        """Test whether an OS-level package is available in the repos, with a
        specific minimum version. It does not matter for this function whether
        the package is already installed.
        None for `min_version` will test just for being available, but not for a
        particular version."""
        if not self.supported():
            self._failed = True
            self._continue = True # we try anyway
            self._reason = "This operating system platform (%s) is not "\
                           "supported for automatic installation of "\
                           "pre-requisites." % self.platform()
            self._manual_packages.append(platform_pkg_name)
            return
        raise NotImplemented

    def install(self, generic_pkg_name, min_version=None, pkg_brief=None):
        """Ensure that an OS-level package is installed with a specific minimum
        version."""
        if not self.supported():
            self._failed = True
            self._continue = True # we try anyway
            self._reason = "This operating system platform (%s) is not "\
                           "supported for automatic installation of "\
                           "pre-requisites." % self.platform()
            self._manual_packages.append(pkg_brief)
            return
        print "Testing for availability of %s..." %  pkg_brief
        platform_pkg_names = self.platform_pkg_name(generic_pkg_name).split()
        for platform_pkg_name in platform_pkg_names:
            if not self.is_installed(platform_pkg_name, min_version):
                self.do_install(platform_pkg_name, min_version, pkg_brief)

class RedhatInstaller(OSInstaller):
    """Installer for Redhat-based distributions (e.g. RHEL, CentOS, Fedora).
    It uses the new dnf installer for Fedora>=22."""

    # The platform-specific package names (may be one or more, in a
    # blank-separated string) for each generic package name.
    PLATFORM_PACKAGES = {
        "pcre-devel": "pcre-devel",
        "openssl-devel": "openssl-devel",
        "libxml2-devel": "libxml2-devel",
        "libxslt-devel": "libxslt-devel",
        "libyaml-devel": "libyaml-devel",
        "pylint": "pylint",
        "swig": "swig",
        "g++": "gcc-c++",
        "git": "git",
    }

    def _installer_cmd(self):
        """Return the installer command."""
        if self._distro == "fedora" and \
            int(platform.linux_distribution()[1]) >= 22:
            return "dnf"
        else:
            return "yum"

    def do_install(self, platform_pkg_name, min_version=None, pkg_brief=None):
        """Install an OS-level package with a specific minimum version.
        None for `min_version` will install the latest available version."""
        if min_version is not None:
            platform_pkg_name += "-%s*" % min_version
        if not self.authorized():
            self._failed = True
            self._continue = False # we know that some packages are missing
            self._reason = "This userid is not authorized to install OS-level "\
                           "packages."
            self._manual_packages.append(pkg_brief)
        else:
            cmd = "sudo %s install -y %s" %\
                 (self._installer_cmd(), platform_pkg_name)
            if DRY_RUN:
                print "Dry-running: %s" % cmd
            else:
                print "Running: %s" % cmd
                shell_check(cmd, display=True)

    def is_installed(self, platform_pkg_name, min_version=None):
        """Test whether an OS-level package is installed and has a specific
        minimum version.
        None for `min_version` will test just for being installed, but not for a
        particular version."""
        cmd = "%s list installed %s" % (self._installer_cmd(), platform_pkg_name)
        rc, out, err = shell(cmd)
        if rc != 0:
            print "Package is not installed: %s" % platform_pkg_name
            return False
        info = out.splitlines()[-1].strip("\n").split()
        if not info[0].startswith(platform_pkg_name+"."):
            raise SetupError("Unexpected output from command '%s':\n%s%s" %\
                (cmd, out, err))
        version = info[1].split("-")[0]
        if min_version is not None:
            version_list = version.split(".")
            min_version_list = min_version.split(".")
            version_sufficient = (version_list >= min_version_list)
            if version_sufficient:
                print "Installed package version is sufficient: "\
                    "%s %s" % (platform_pkg_name, version)
            else:
                print "Installed package version is not sufficient: "\
                    "%s %s" % (platform_pkg_name, version)
            return version_sufficient
        else:
            print "Package is installed (no minimum version was required): "\
                "%s %s" % (platform_pkg_name, version)
            return True

    def is_available(self, platform_pkg_name, min_version=None):
        """Test whether an OS-level package is available in the repos, with a
        specific minimum version. It does not matter for this function whether
        the package is already installed.
        None for `min_version` will test just for being available, but not for a
        particular version."""
        cmd = "%s list %s" % (self._installer_cmd(), platform_pkg_name)
        rc, out, err = shell(cmd)
        if rc != 0:
            print "Package is not available in repositories: %s" %\
                platform_pkg_name
            return False
        info = out.splitlines()[-1].strip("\n").split()
        if not info[0].startswith(platform_pkg_name+"."):
            raise SetupError("Unexpected output from command '%s':\n%s%s" %\
                (cmd, out, err))
        version = info[1].split("-")[0]
        if min_version is not None:
            version_list = version.split(".")
            min_version_list = min_version.split(".")
            version_sufficient = (version_list >= min_version_list)
            if version_sufficient:
                print "Package version in repositories is sufficient: "\
                    "%s %s" % (platform_pkg_name, version)
            else:
                print "Package version in repositories is not sufficient: "\
                    "%s %s" % (platform_pkg_name, version)
            return version_sufficient
        else:
            print "Package is available in repositories (no minimum version "\
                "was required): %s %s" % (platform_pkg_name, version)
            return True

class DebianInstaller(OSInstaller):
    """Installer for Debian-based distributions (e.g. Debian, Ubuntu)."""

    # The platform-specific package names (may be one or more, in a
    # blank-separated string) for each generic package name.
    PLATFORM_PACKAGES = {
        "pcre-devel": "libpcre3 libpcre3-dev",
        "openssl-devel": "libssl-dev",
        "libxml2-devel": "libxml2-dev",
        "libxslt-devel": "libxslt1-dev",
        "libyaml-devel": "libyaml-dev",
        "pylint": "pylint",
        "swig": "swig2.0",
        "g++": "g++",
        "git": "git",
    }

    def do_install(self, platform_pkg_name, min_version=None, pkg_brief=None):
        """Install an OS-level package with a specific minimum version.
        None for `min_version` will install the latest available version."""
        if min_version is not None:
            # apt has no syntax for installing minimum version or later; it
            # only allows for installing the latest sub-version of the latest
            # available version, but if the specified minimum version is older
            # than the latest available version, the package is not going to
            # be available. So all we can do is to assume that the latest
            # version will be sufficient.
            pass
        if not self.authorized():
            self._failed = True
            self._continue = False # we know that some packages are missing
            self._reason = "This userid is not authorized to install OS-level "\
                           "packages."
            self._manual_packages.append(pkg_brief)
        else:
            cmd = "sudo apt-get install -y %s" % platform_pkg_name
            if DRY_RUN:
                print "Dry-running: %s" % cmd
            else:
                print "Running: %s" % cmd
                shell_check(cmd, display=True)

    def is_installed(self, platform_pkg_name, min_version=None):
        """Test whether an OS-level package is installed and has a specific
        minimum version.
        None for `min_version` will test just for being installed, but not for a
        particular version."""
        cmd = "dpkg -s %s" % platform_pkg_name
        rc, out, err = shell(cmd)
        if rc != 0:
            print "Package is not installed: %s" % platform_pkg_name
            return False
        lines = out.splitlines()
        status_line = [line for line in lines if line.startswith("Status:")][0]
        version_line = [line for line in lines if line.startswith("Version:")][0]
        if status_line != "Status: install ok installed":
            raise SetupError("Unexpected status output from command '%s':\n"\
                "%s%s" % (cmd, out, err))
        version = version_line.split()[1].split("-")[0]
        if ":" in version:
            version = version.split(":")[1]
        if min_version is not None:
            version_list = version.split(".")
            min_version_list = min_version.split(".")
            version_sufficient = (version_list >= min_version_list)
            if version_sufficient:
                print "Installed package version is sufficient: "\
                    "%s %s" % (platform_pkg_name, version)
            else:
                print "Installed package version is not sufficient: "\
                    "%s %s" % (platform_pkg_name, version)
            return version_sufficient
        else:
            print "Package is installed (no minimum version was required): "\
                "%s %s" % (platform_pkg_name, version)
            return True

    def is_available(self, platform_pkg_name, min_version=None):
        """Test whether an OS-level package is available in the repos, with a
        specific minimum version. It does not matter for this function whether
        the package is already installed.
        None for `min_version` will test just for being available, but not for a
        particular version."""
        cmd = "apt show %s" % platform_pkg_name
        rc, out, err = shell(cmd)
        if rc != 0:
            print "Package is not available in repositories: %s" %\
                platform_pkg_name
            return False
        lines = out.splitlines()
        version_line = [line for line in lines if line.startswith("Version:")][0]
        version = version_line.split()[1].split("-")[0]
        if min_version is not None:
            version_list = version.split(".")
            min_version_list = min_version.split(".")
            version_sufficient = (version_list >= min_version_list)
            if version_sufficient:
                print "Package version in repositories is sufficient: "\
                    "%s %s" % (platform_pkg_name, version)
            else:
                print "Package version in repositories is not sufficient: "\
                    "%s %s" % (platform_pkg_name, version)
            return version_sufficient
        else:
            print "Package is available in repositories (no minimum version "\
                "was required): %s %s" % (platform_pkg_name, version)
            return True

class SuseInstaller(OSInstaller):
    """Installer for Suse-based distributions (e.g. SLES, openSUSE)."""

    # The platform-specific package names (may be one or more, in a
    # blank-separated string) for each generic package name.
    PLATFORM_PACKAGES = {
        "pcre-devel": "pcre-devel",
        "openssl-devel": "openssl-devel",
        "libxml2-devel": "libxml2-devel",
        "libxslt-devel": "libxslt-devel",
        "libyaml-devel": "libyaml-devel",
        "pylint": "pylint",
        "swig": "swig",
        "g++": "gcc-c++",
        "git": "git",
    }

    def do_install(self, platform_pkg_name, min_version=None, pkg_brief=None):
        """Install an OS-level package with a specific minimum version.
        None for `min_version` will install the latest available version."""
        if min_version is not None:
            # Zypper has no syntax for installing minimum version or later.
            # So all we can do is to assume that the latest version will be
            # sufficient.
            pass
        if not self.authorized():
            self._failed = True
            self._continue = False # we know that some packages are missing
            self._reason = "This userid is not authorized to install OS-level "\
                           "packages."
            self._manual_packages.append(pkg_brief)
        else:
            cmd = "sudo yum zypper -y %s" % platform_pkg_name
            if DRY_RUN:
                print "Dry-running: %s" % cmd
            else:
                print "Running: %s" % cmd
                shell_check(cmd, display=True)

    def is_installed(self, platform_pkg_name, min_version=None):
        """Test whether an OS-level package is installed and has a specific
        minimum version.
        None for `min_version` will test just for being installed, but not for a
        particular version."""
        cmd = "zypper info %s" % platform_pkg_name
        rc, out, err = shell(cmd)
        if rc != 0:
            print "Package is not installed: %s" % platform_pkg_name
            return False
        info = out.splitlines()[-1].strip("\n").split()
        if not info[0].startswith(platform_pkg_name+"."):
            raise SetupError("Unexpected output from command '%s':\n%s%s" %\
                (cmd, out, err))
        version = info[1].split("-")[0]
        print "Package already installed: %s %s" % (platform_pkg_name, version)
        if min_version is not None:
            version_list = version.split(".")
            min_version_list = min_version.split(".")
            version_sufficient = (version_list >= min_version_list)
            if version_sufficient:
                print "Installed package version is sufficient: "\
                    "%s %s" % (platform_pkg_name, version)
            else:
                print "Installed package version is not sufficient: "\
                    "%s %s" % (platform_pkg_name, version)
            return version_sufficient
        else:
            print "Package is installed (no minimum version was required): "\
                "%s %s" % (platform_pkg_name, version)
            return True

    def is_available(self, platform_pkg_name, min_version=None):
        """Test whether an OS-level package is available in the repos, with a
        specific minimum version. It does not matter for this function whether
        the package is already installed.
        None for `min_version` will test just for being available, but not for a
        particular version."""
        cmd = "zypper info %s" % platform_pkg_name
        rc, out, err = shell(cmd)
        # zypper always returns 0, and writes everything to stdout.
        lines = out.splitlines()
        version_lines = [line for line in lines if line.startswith("Version:")]
        if len(version_lines) == 0:
            print "Package is not available in repositories: %s" %\
                platform_pkg_name
            return False
        version_line = version_lines[0]
        version = version_line.split()[1].split("-")[0]
        if min_version is not None:
            version_list = version.split(".")
            min_version_list = min_version.split(".")
            version_sufficient = (version_list >= min_version_list)
            if version_sufficient:
                print "Package version in repositories is sufficient: "\
                    "%s %s" % (platform_pkg_name, version)
            else:
                print "Package version in repositories is not sufficient: "\
                    "%s %s" % (platform_pkg_name, version)
            return version_sufficient
        else:
            print "Package is available in repositories (no minimum version "\
                "was required): %s %s" % (platform_pkg_name, version)
            return True

def install_swig(inst):

    inst.install("g++", "4.4", "GCC C/C++ compiler")

    swig_min_version = "2.0"
    print "Testing for availability of Swig >=%s in PATH..." % swig_min_version
    get_swig = False
    rc, out, err = shell("which swig")
    if rc != 0:
        print "Swig is not available in PATH; need to get Swig"
        get_swig = True
    else:
        print "Swig is available in PATH; testing its version..."
        out = shell_check("swig -version")
        m = re.search(r"^SWIG Version ([0-9\.]+)$", out, re.MULTILINE)
        if m is None:
            raise SetupError("Cannot determine Swig version from output "
                "of 'swig -version':\n%s" % out)
        swig_version = m.group(1)
        if swig_version.split(".") < swig_min_version.split("."):
            print "Installed Swig version is too old: %s; need to get Swig" %\
                swig_version
            get_swig = True
        else:
            print "Installed Swig version is sufficient: %s" % swig_version

    if get_swig:

        print "Testing for availability of Swig >=%s in repositories..." %\
            swig_min_version
        if inst.is_available("swig", swig_min_version):

            inst.do_install("swig", swig_min_version, "Swig")

        else:

            swig_build_version = "2.0.12"
            swig_dir = "swig-%s" % swig_build_version
            swig_tar_file = "swig-%s.tar.gz" % swig_build_version
            swig_install_root = "/usr"

            print "Building Swig from sources, and installing to %s tree..." %\
                swig_install_root

            print "Installing prerequisite OS-level packages for building "\
                "Swig..."
            inst.install("pcre-devel", None,
                "PCRE (Perl Compatible Regular Expressions) development")

            print "Downloading, building and installing Swig version %s..." %\
                swig_build_version

            if os.path.exists(swig_dir):
                print "Removing previously downloaded Swig directory: %s" %\
                    swig_dir
                shutil.rmtree(swig_dir)

            print "Downloading Swig source archive: %s" % swig_tar_file
            shell_check("wget -q -O %s "
              "http://sourceforge.net/projects/swig/files/swig/%s/%s/download"%\
              (swig_tar_file, swig_dir, swig_tar_file), display=True)
            print "Unpacking Swig source archive: %s" % swig_tar_file
            shell_check("tar -xf %s" % swig_tar_file, display=True)

            print "Configuring Swig build process for installing to %s "\
                "tree..." % swig_install_root
            shell_check(["sh", "-c", "cd %s; ./configure --prefix=%s" %\
                (swig_dir, swig_install_root)],
                display=True)

            print "Building Swig..."
            shell_check(["sh", "-c", "cd %s; make swig" % swig_dir],
                display=True)

            print "Installing Swig to %s tree..." % swig_install_root
            shell_check(["sh", "-c", "cd %s; sudo make install" % swig_dir],
                display=True)

            print "Done downloading, building and installing Swig version %s" %\
                swig_build_version

def install_openssl(inst):
    inst.install("openssl-devel", "1.0.1", "OpenSSL development")

def install_git(inst):
    inst.install("git", "1.7", "Git")

def install_xmlxslt(inst):
    inst.install("libxml2-devel", None, "XML development")
    inst.install("libxslt-devel", None, "XSLT development")
    inst.install("libyaml-devel", None, "YAML development")

def install_pylint(inst):
    print "Testing for availability of PyLint in repositories..."
    if inst.is_available("pylint"):
        inst.install("pylint", None, "PyLint")
    else:
        print "Skipping installation of PyLint..."

def install_build_requirements():
    print "Installing Python packages for PyWBEM development..."
    shell_check("pip install -r build-requirements.txt", display=True)

def patch_epydoc():
    import epydoc # Has been installed in install_build_requirements()
    epydoc_target_dir = os.path.dirname(epydoc.__file__)
    epydoc_patch_dir = epydoc_target_dir+"/.epydoc-3.0.1-patches"

    if os.path.exists(epydoc_patch_dir):

        print "Epydoc patch directory exists, assuming Epydoc is already "\
            "patched..."

    else:

        print "Epydoc patch directory does not exist, patching Epydoc..."

        print "Creating Epydoc patch directory %s" % epydoc_patch_dir
        shell_check("mkdir -p %s" % epydoc_patch_dir)

        print "Downloading Epydoc patches into patch directory %s" %\
            epydoc_patch_dir
        shell_check("wget -q -O %s/epydoc-rst.patch "
                    "http://cvs.pld-linux.org/cgi-bin/viewvc.cgi/cvs/packages/epydoc/epydoc-rst.patch?revision=1.1&view=co" %\
                    epydoc_patch_dir, display=True)
        shell_check("wget -q -O %s/epydoc-cons_fields_stripping.patch "
                    "http://cvs.pld-linux.org/cgi-bin/viewvc.cgi/cvs/packages/epydoc/epydoc-cons_fields_stripping.patch?view=co" %\
                    epydoc_patch_dir, display=True)
        shell_check("wget -q -O %s/epydoc-__package__.patch "
                    "http://cvs.pld-linux.org/cgi-bin/viewvc.cgi/cvs/packages/epydoc/epydoc-__package__.patch?revision=1.1&view=co" %\
                    epydoc_patch_dir, display=True)

        print "Applying Epydoc patches to %s" % epydoc_target_dir
        shell_check("patch -N -r %s/epydoc-rst.patch.rej "
                    "-i %s/epydoc-rst.patch "
                    "%s/markup/restructuredtext.py" %\
                    (epydoc_patch_dir, epydoc_patch_dir, epydoc_target_dir),
                    display=True, exp_rc=(0,1))
        shell_check("patch -N -r %s/epydoc-cons_fields_stripping.patch.rej "
                    "-i %s/epydoc-cons_fields_stripping.patch "
                    "%s/markup/restructuredtext.py" %\
                    (epydoc_patch_dir, epydoc_patch_dir, epydoc_target_dir),
                    display=True, exp_rc=(0,1))
        shell_check("patch -N -r %s/epydoc-__package__.patch.rej "
                    "-i %s/epydoc-__package__.patch "
                    "%s/docintrospecter.py" %\
                    (epydoc_patch_dir, epydoc_patch_dir, epydoc_target_dir),
                    display=True, exp_rc=(0,1))

class color:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def main():

    try:

        import_setuptools()
        from setuptools import setup

        inst = OSInstaller().platform_installer()

        if "install" in sys.argv:

            install_swig(inst)
            install_openssl(inst)
            install_git(inst)

            if inst._failed:
                if inst._continue:
                    print \
                      "Cannot install pre-requisites for the 'install' command.\n"\
                      "Reason: %s\n"\
                      "Continuing anyway..." % inst._reason
                else:
                    raise SetupError(
                      "Cannot install pre-requisites for the 'install' command.\n"\
                      "Reason: %s\n"\
                      "Please install the following packages manually, and "\
                      "retry:\n"\
                      "\n"\
                      "    %s" % (inst._reason,
                                  "\n    ".join(inst._manual_packages)))

        if "develop" in sys.argv:

            install_swig(inst)
            install_openssl(inst)
            install_git(inst)
            install_xmlxslt(inst)
            install_pylint(inst)

            if inst._failed:
                if inst._continue:
                    print \
                      "Cannot install pre-requisites for the 'develop' command.\n"\
                      "Reason: %s\n"\
                      "Continuing anyway..." % inst._reason
                else:
                    raise SetupError(
                      "Cannot install pre-requisites for the 'develop' command.\n"\
                      "Reason: %s\n"\
                      "Please install the following packages manually, and "\
                      "retry:\n"\
                      "\n"\
                      "    %s" % (inst._reason,
                                  "\n    ".join(inst._manual_packages)))
            # The following have dependencies on the OS-level packages
            # installed further up.
            install_build_requirements()
            patch_epydoc()

    except SetupError as exc:
        print "%sError: %s%s" % (color.FAIL, exc, color.ENDC)
        return 1

    print "Installing PyWBEM and its Python package prerequisites..."

    args = {
        'name': 'pywbem',
        'author': 'Tim Potter',
        'author_email': 'tpot@hp.com',
        'maintainer': 'Andreas Maier',
        'maintainer_email': 'andreas.r.maier@gmx.de',
        'description': 'A WBEM client and related utilities',
        'long_description': __doc__,
        'platforms': ['any'],
        'url': 'http://pywbem.github.io/pywbem/',
        'version': _version,
        'license': 'LGPL version 2.1, or (at your option) any later version',
        'packages': ['pywbem'],
        'package_data': {
            'pywbem': [
                'NEWS',
                'LICENSE.txt',
            ]
        },
        'scripts': [
            'pywbem/wbemcli.py',
            'pywbem/mof_compiler.py',
        ],
        'install_requires': [
            # These dependencies will be installed as a site package.
            # They are not useable by this setup script, if they are eggs
            # (because their path is added to a .pth file which is parsed only
            # at Python startup time).
            #'M2Crypto>=0.22.6',
            'M2Crypto',
        ],
        # Temporary fix: Use our own fork of M2Crypto with fixes for
        # installation issues. This only seems to work if no version is
        # specified in its install_requires entry.
        'dependency_links': [
            "git+https://github.com/pywbem/m2crypto@amfix2#egg=M2Crypto"
        ],
        'classifiers' : [
            'Development Status :: 6 - Mature',
            'Intended Audience :: Developers',
            'Intended Audience :: System Administrators',
            'License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)',
            'Operating System :: OS Independent',
            'Programming Language :: Python :: 2.6',
            'Programming Language :: Python :: 2.7',
            'Topic :: Software Development :: Libraries :: Python Modules',
            'Topic :: System :: Systems Administration',
        ],
    }
    setup(**args)
    return 0

if __name__ == '__main__':
    sys.exit(main())
