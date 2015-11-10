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
A pure-Python library for performing operations using the WBEM
management protocol.
"""

# Package version - Keep in sync with pywbem/__init__.py!
_version = '0.8.0-dev'

# Control printing of debug messages
DEBUG = False

import re
import sys
import os
import subprocess
import platform
import shutil

class SetupError(Exception):
    """Exception that causes this setup script to fail."""
    pass

def shell(command):
    """Execute a shell command and return its return code, stdout and stderr.

    Note that the simpler to use subprocess.check_output() requires
    Python 2.7, but we want to support Python 2.6 as well.

    Parameters:

      * command: string or list of strings with the command and its parameters.

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

    rc, out, err = shell(command)
    if rc not in exp_rc:
        err = err.strip(" ").strip("\n")
        out = out.strip(" ").strip("\n")
        if err != "":
            msg = err
        else:
            msg = out
        raise SetupError("%s returns rc=%d: %s" % (command[0], rc, msg))
    else:
        if display:
            if out != "":
                print out
            if err != "":
                print err
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


# Translation of package names, using RedHat package names as key
PACKAGE_NAMES = {
    "redhat": {
        "pcre-devel": "pcre-devel",
        "openssl-devel": "openssl-devel",
        "libxml2-devel": "libxml2-devel",
        "libxslt-devel": "libxslt-devel",
        "pylint": "pylint",
    },
    "fedora": {
        "pcre-devel": "pcre-devel",
        "openssl-devel": "openssl-devel",
        "libxml2-devel": "libxml2-devel",
        "libxslt-devel": "libxslt-devel",
        "pylint": "pylint",
    },
    "centos": {
        "pcre-devel": "pcre-devel",
        "openssl-devel": "openssl-devel",
        "libxml2-devel": "libxml2-devel",
        "libxslt-devel": "libxslt-devel",
        "pylint": "pylint",
    },
    "debian": {
        "pcre-devel": "libpcre3 libpcre3-dev",
        "openssl-devel": "libssl-dev",
        "libxml2-devel": "libxml2-dev",
        "libxslt-devel": "libxslt1-dev",
        "pylint": "pylint",
    },
    "ubuntu": {
        "pcre-devel": "libpcre3 libpcre3-dev",
        "openssl-devel": "libssl-dev",
        "libxml2-devel": "libxml2-dev",
        "libxslt-devel": "libxslt1-dev",
        "pylint": "pylint",
    },
    "suse": {
        "pcre-devel": "pcre-devel",
        "openssl-devel": "openssl-devel",
        "libxml2-devel": "libxml2-devel",
        "libxslt-devel": "libxslt-devel",
        "pylint": "pylint",
    },
}

def install_os_package(pkg_name):
    """Install an OS-level package.

    Parameters:

      * package: (string) Name of the package on RedHat-based systems. The
        name is translated to whatever it is on other systems (Debian-based,
        SUSE-based).
    """

    def _install(pkg_name, pkg_install_cmd):
        print "Installing package: %s" % pkg_name
        shell_check(pkg_install_cmd, display=True)

    def _pkg_name(pkg_name, dist_name):
        try:
            dist_pkg_name = PACKAGE_NAMES[dist_name]
        except KeyError:
            raise SetupError("Cannot install OS-level package %s; "
                "unsupported distribution %s" % (pkg_name, dist_name))
        try:
            pkg_name = dist_pkg_name[pkg_name]
        except KeyError:
            raise SetupError("Cannot install OS-level package %s; "
                "package name is unknown for distribution %s" % (pkg_name, dist_name))
        return pkg_name

    dist_name = platform.linux_distribution(full_distribution_name=False)[0].lower()
    pkg_name = _pkg_name(pkg_name, dist_name)
    if dist_name in ("redhat", "fedora", "centos"):
        _install(pkg_name, "sudo yum install -y %s" % pkg_name)
    elif dist_name in ("debian", "ubuntu"):
        _install(pkg_name, "sudo apt-get install -y %s" % pkg_name)
    elif dist_name in ("suse",):
        _install(pkg_name, "sudo zypper install -y %s" % pkg_name)
    else:
        raise SetupError("Cannot install OS-level package %s; "
            "unsupported distribution %s" % (pkg_name, dist_name))

def install_swig():
    """Make sure that Swig is available in the PATH with at least version 2.0.
    That is the version required for installing M2Crypto.

    If not available with that version, download source of Swig 2.0 and build
    it."""

    print "Testing for availability if Swig in PATH..."
    build_swig = False
    rc, out, err = shell("which swig")
    if rc != 0:
        print "Swig is not available in PATH; installing Swig"
        build_swig = True
    else:
        print "Testing for version of Swig..."
        out = shell_check("swig -version")
        m = re.search(r"^SWIG Version ([0-9\.]+)$", out, re.MULTILINE)
        if m is None:
            raise SetupError("Cannot determine Swig version from output "
                "of 'swig -version':\n%s" % out)
        swig_version = m.group(1)
        if swig_version.split(".")[0:2] < [2,0]:
            print "Installed Swig version %s is too old; updating Swig" % swig_version
            build_swig = True
        else:
            print "Installed Swig version %s is sufficient" % swig_version

    if build_swig:

        swig_version = "2.0.12"
        swig_dir = "swig-%s" % swig_version
        swig_tar_file = "swig-%s.tar.gz" % swig_version

        print "Installing prerequisite OS-level packages for building Swig..."
        install_os_package("pcre-devel")

        print "Downloading, building and installing Swig version %s..." % swig_version

        if os.path.exists(swig_dir):
            print "Removing previously downloaded Swig directory: %s" % swig_dir
            shutil.rmtree(swig_dir)

        print "Downloading Swig source archive: %s" % swig_tar_file
        shell_check("wget -q -O %s "
            "http://sourceforge.net/projects/swig/files/swig/%s/%s/download" %\
            (swig_tar_file, swig_dir, swig_tar_file), display=True)
        print "Unpacking Swig source archive: %s" % swig_tar_file
        shell_check("tar -xf %s" % swig_tar_file, display=True)

        print "Configuring Swig build process for installing to system (/usr)..."
        shell_check(["sh", "-c", "cd %s; ./configure --prefix=/usr" % swig_dir], display=True)

        print "Building Swig..."
        shell_check(["sh", "-c", "cd %s; make swig" % swig_dir], display=True)

        print "Installing Swig to system (/usr)..."
        shell_check(["sh", "-c", "cd %s; sudo make install" % swig_dir], display=True)

        print "Done downloading, building and installing Swig version %s" % swig_version

def install_openssl():
    """Make sure that the OpenSSL development package is installed.
    That package is required for installing M2Crypto.

    If not installed yet, install it, dependent on the operating system.
    """

    print "Installing prerequisite OS-level packages for installing M2Crypto..."
    install_os_package("openssl-devel")

def install_xmlxslt():
    """Install the XML/XSLT development packages."""

    print "Installing prerequisite OS-level packages for XML/XSLT development..."
    install_os_package("libxml2-devel")
    install_os_package("libxslt-devel")

def install_build_requirements():
    """Install Python packages for PyWBEM development."""

    print "Installing Python packages for PyWBEM development..."
    shell_check("pip install -r build-requirements.txt", display=True)

def patch_epydoc():
    """Apply patches to Epydoc."""

    print "Patching Epydoc..."

    epydoc_patch_dir = "epydoc-3.0.1-patches"

    import epydoc # Has been installed in install_build_requirements()
    epydoc_target_dir = os.path.dirname(epydoc.__file__)

    if os.path.exists(epydoc_patch_dir):
        print "Removing previously downloaded Epydoc patch directory %s" %\
              epydoc_patch_dir
        shutil.rmtree(epydoc_patch_dir)

    print "Creating Epydoc patch directory %s" % epydoc_patch_dir
    shell_check("mkdir -p %s" % epydoc_patch_dir)

    print "Downloading Epydoc patches into patch directory %s" % epydoc_patch_dir
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

def install_pylint():
    """Install the PyLint package."""

    print "Installing prerequisite OS-level packages for PyLint..."
    install_os_package("pylint")

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

        if "install" in sys.argv:
            install_swig()
            install_openssl()

        if "develop" in sys.argv:
            install_swig()
            install_openssl()
            install_xmlxslt() # probably needed for some installations of lxml
            install_build_requirements()
            patch_epydoc()
            install_pylint()

    except SetupError as exc:
        print "%sError: %s%s" % (color.FAIL, exc, color.ENDC)
        return 1

    args = {
        'name': 'pywbem',
        'author': 'Tim Potter',
        'author_email': 'tpot@hp.com',
        'description': 'Python WBEM client library',
        'long_description': __doc__,
        'platforms': ['any'],
        'url': 'https://github.com/pywbem/pywbem',
        'version': _version,
        'license': 'LGPLv2',
        'packages': ['pywbem'],
        'package_data': {
            'pywbem': [
                'docs/*',
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
            # They are not useable by this setup script, if they are eggs (because
            # their path is added to a .pth file which is parsed only at Python
            # startup time).
            #'M2Crypto>=0.22.6',
            'M2Crypto',
        ],
        # Temporary fix: Use our own fork of M2Crypto with fixes for installation issues.
        # This only seems to work if no version is specified in its install_requires entry.
        'dependency_links': [
            "git+https://github.com/pywbem/m2crypto@amfix2#egg=M2Crypto"
        ],
        'classifiers' : [
            'Development Status :: 4 - Beta',
            'Intended Audience :: Developers',
            'Intended Audience :: System Administrators',
            'License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)',
            'Operating System :: POSIX :: Linux',
            'Operating System :: Microsoft :: Windows',
            'Programming Language :: Python',
            'Programming Language :: Python :: 2.6',
            'Programming Language :: Python :: 2.7',
            'Topic :: Software Development',
            'Topic :: System :: Systems Administration',
        ],
    }
    setup(**args)
    return 0

if __name__ == '__main__':
    sys.exit(main())
