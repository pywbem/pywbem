#!/usr/bin/env python
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

# The module docstring is used as the long package description:
"""
Pywbem is a WBEM client, written in pure Python. It supports Python 2 and
Python 3.

A WBEM client allows issuing operations to a WBEM server, using the CIM
operations over HTTP (CIM-XML) protocol defined in the DMTF standards
DSP0200 and DSP0201. The CIM/WBEM infrastructure is used for a wide variety of
systems management tasks supported by systems running WBEM servers.
See http://www.dmtf.org/standards/wbem for more information about WBEM.
"""

from __future__ import print_function, absolute_import

import re
import sys
import os
import shutil
import subprocess
import platform
from distutils.errors import DistutilsSetupError

import os_setup
from os_setup import shell, shell_check, import_setuptools

# Workaround for Python 2.6 issue https://bugs.python.org/issue15881
# This causes this module to be referenced and prevents the premature
# unloading and subsequent garbage collection causing the error.
if sys.version_info[0:2] == (2, 6):
    try:
        # pylint: disable=unused-import
        import multiprocessing  # noqa: E402, F401
    except ImportError:
        pass

if sys.version_info[0] == 2:
    from xmlrpclib import Fault
else:
    from xmlrpc.client import Fault

_VERBOSE = True


def package_version(filename, varname):
    """Return package version string by reading `filename` and retrieving its
       module-global variable `varnam`."""
    _locals = {}
    with open(filename) as fp:
        exec(fp.read(), None, _locals)  # pylint: disable=exec-used
    return _locals[varname]


def _check_get_swig(swig_min_version, verbose):
    """Chewck if Swig is available in the PATH in the right version.
    Returns True if it needs to be installed/updated.
    """
    if verbose:
        print("Testing for availability of Swig >=%s in PATH..." %
              swig_min_version)
    get_swig = False
    rc, out, _ = shell("which swig")
    if rc != 0:
        if verbose:
            print("Swig is not available in PATH; need to get Swig")
        get_swig = True
    else:
        if verbose:
            print("Swig is available in PATH; testing its version...")
        out = shell_check("swig -version")
        m = re.search(r"^SWIG Version ([0-9\.]+)$", out, re.MULTILINE)
        if m is None:
            raise DistutilsSetupError("Cannot determine Swig version from "
                                      "output of 'swig -version':\n%s" % out)
        swig_version = m.group(1)
        if swig_version.split(".") < swig_min_version.split("."):
            if verbose:
                print("Installed Swig version is too old: %s; "
                      "need to get Swig" % swig_version)
            get_swig = True
        else:
            if verbose:
                print("Installed Swig version is sufficient: %s" %
                      swig_version)
    return get_swig


def install_swig(installer, dry_run, verbose):
    """Custom installer function for `os_setup` module.
    This function makes sure that Swig is installed, either by installing the
    corresponding OS-level package, or by downloading the source and building
    it.

    Parameters: see description of `os_setup` module.
    """

    swig_min_version = "2.0"

    get_swig = _check_get_swig(swig_min_version, verbose)

    if get_swig:

        system = installer.system
        distro = installer.distro

        swig_pkg_dict = {
            'Linux': {
                'redhat': "swig",
                'centos': "swig",
                'fedora': "swig",
                'debian': "swig",
                'ubuntu': "swig",
                'linuxmint': "swig",
                'suse': "swig",
            },
        }
        # default if no system/distro specific name is found:
        swig_pkg_name = "swig"
        if system in swig_pkg_dict:
            distro_dict = swig_pkg_dict[system]
            if distro in distro_dict:
                swig_pkg_name = distro_dict[distro]

        swig_version_reqs = [">=%s" % swig_min_version]

        installed = installer.ensure_installed(
            swig_pkg_name, swig_version_reqs, dry_run, verbose,
            ignore=True)

        if installed and _check_get_swig(swig_min_version, verbose):
            # Package was tampered with (e.g. swig command renamed)

            if verbose:
                print("Reinstalling Swig package over existing one...")

            installer.do_install(swig_pkg_name, swig_version_reqs, dry_run,
                                 reinstall=True)

        elif not installed:

            # Build Swig from its source
            swig_build_version = "2.0.12"
            swig_dir = "swig-%s" % swig_build_version
            swig_tar_file = "swig-%s.tar.gz" % swig_build_version
            swig_install_root = "/usr"

            if verbose:
                print("Installing prerequisite OS-level packages for building "
                      "Swig...")

            swig_prereq_pkg_dict = {
                'Linux': {
                    'redhat': [
                        "pcre-devel",
                    ],
                    'centos': [
                        "pcre-devel",
                    ],
                    'fedora': [
                        "pcre-devel",
                    ],
                    'debian': [
                        "libpcre3",
                        "libpcre3-dev",
                    ],
                    'ubuntu': [
                        "libpcre3",
                        "libpcre3-dev",
                    ],
                    'linuxmint': [
                        "libpcre3",
                        "libpcre3-dev",
                    ],
                    'suse': [
                        "pcre-devel",
                    ],
                },
            }
            # default if no system/distro specific name is found:
            swig_prereq_pkg_default = [
                "pcre-devel",
            ]

            swig_prereq_pkg_names = swig_prereq_pkg_default
            if system in swig_prereq_pkg_dict:
                distro_dict = swig_prereq_pkg_dict[system]
                if distro in distro_dict:
                    swig_prereq_pkg_names = distro_dict[distro]
            for swig_prereq_pkg_name in swig_prereq_pkg_names:

                installed = installer.ensure_installed(
                    swig_prereq_pkg_name, None, dry_run, verbose,
                    ignore=False)

            if dry_run:
                if verbose:
                    print("Dry-running: Building Swig version %s from "
                          "downloaded source, and installing to %s tree" %
                          (swig_build_version, swig_install_root))
            else:
                if verbose:
                    print("Building Swig version %s from "
                          "downloaded source, and installing to %s tree" %
                          (swig_build_version, swig_install_root))

                if os.path.exists(swig_dir):
                    if verbose:
                        print("Removing previously downloaded Swig directory: "
                              "%s" % swig_dir)
                    shutil.rmtree(swig_dir)

                if verbose:
                    print("Downloading Swig source archive: %s" % swig_tar_file)
                shell_check(
                    "wget -q -O %s http://sourceforge.net/projects/swig/files"
                    "/swig/%s/%s/download" %
                    (swig_tar_file, swig_dir, swig_tar_file), display=True)
                if verbose:
                    print("Unpacking Swig source archive: %s" % swig_tar_file)
                shell_check("tar -xf %s" % swig_tar_file, display=True)

                if verbose:
                    print("Configuring Swig build process for installing to "
                          "%s tree..." % swig_install_root)
                shell_check(
                    ["sh", "-c", "cd %s; ./configure --prefix=%s" %
                     (swig_dir, swig_install_root)], display=True)

                if verbose:
                    print("Building Swig...")
                shell_check(
                    ["sh", "-c", "cd %s; make swig" % swig_dir], display=True)

                if verbose:
                    print("Installing Swig to %s tree..." % swig_install_root)
                shell_check(
                    ["sh", "-c", "cd %s; sudo make install" % swig_dir],
                    display=True)

                if verbose:
                    print("Done downloading, building and installing Swig "
                          "version %s" % swig_build_version)


def build_moftab(verbose):  # pylint: disable=unused-argument
    """Generate the moftab modules.

    This function is called after the installation of the `pywbem`package
    and its dependencies.
    The modules are generated into the directory where the
    `mof_compiler` module runs from, i.e. the installation target.

    Because the generation depends on the packages `ply`, `six`, and
    `M2Crypto` the build function is invoked in a child Python process,
    which picks up the changed module search path.

    Note that ideally these dependencies would be specified in a
    `setup_requires` keyword, but at this point (setuptools v20), it does
    not work together woth `install_requires`. See setuptools issue #391:
    https://bitbucket.org/pypa/setuptools/issues/391/
    dependencies-listed-in-both-setup_requires
    """
    rc = subprocess.call([sys.executable, 'build_moftab.py'])
    if rc != 0:
        # Because this does not work on pip, the best compromise is to
        # tolerate a failure:
        print("Warning: build_moftab.py failed with rc=%s; the PyWBEM "
              "LEX/YACC table modules may be rebuilt on first use" % rc)


def main():
    """Main function of this script."""

    import_setuptools()
    from setuptools import setup
    from setuptools.command.build_py import build_py as _build_py

    class build_py(_build_py):
        # pylint: disable=invalid-name,too-few-public-methods
        """Custom command that extends the setuptools `build_py` command,
        which prepares the Python files before they are being installed.
        This command is used by `setup.py install` and `pip install`.

        We use this only to pick up the verbosity level.
        """
        def run(self):
            global _VERBOSE  # pylint: disable=global-statement
            _VERBOSE = self.verbose
            _build_py.run(self)

    py_version_m_n = "%s.%s" % (sys.version_info[0], sys.version_info[1])
    py_version_m = "%s" % sys.version_info[0]

    pkg_version = package_version("pywbem/_version.py", "__version__")

    args = {
        'name': 'pywbem',
        'author': 'Tim Potter',
        'author_email': 'tpot@hp.com',
        'maintainer': 'Andreas Maier',
        'maintainer_email': 'maiera@de.ibm.com',
        'description': 'pywbem - A WBEM client',
        'long_description': __doc__,
        'platforms': ['any'],
        'url': 'http://pywbem.github.io/pywbem/',
        'version': pkg_version,
        'license': 'LGPL version 2.1, or (at your option) any later version',
        'distclass': os_setup.OsDistribution,
        'cmdclass': {
            'build_py': build_py,
            'install_os': os_setup.install_os,
            'develop_os': os_setup.develop_os,
            'develop': os_setup.develop,
        },
        'packages': ['pywbem'],
        'package_data': {
            'pywbem': [
                'NEWS.md',
                'LICENSE.txt',
            ]
        },
        'scripts': [
            'wbemcli',
            'wbemcli.py',
            'mof_compiler',
            'wbemcli.bat',
            'mof_compiler.bat',
        ],
        'install_requires': [
            # These dependencies will be installed as a site package.
            # They are not useable by this setup script, if they are eggs
            # (because their path is added to a .pth file which is parsed only
            # at Python startup time).
            'six',
            'ply',
            # The PyYAML package contains the "yaml" Python package. yaml is
            # needed by the pywbem._recorder module.
            'PyYAML',
        ],
        'develop_requires': [
            # Wheel may not be installed in every system Python.
            'wheel',
            # Python prereqs for 'develop' command. Handled by os_setup module.
            "pytest>=2.4",
            "pytest-cov",
            "Sphinx>=1.3",
            # Pinning GitPython to 2.0.8 max, due to its use of unittest.case
            # which is not available on Python 2.6.
            # TODO: Track resolution of GitPython issue #540:
            #       https://github.com/gitpython-developers/GitPython/issues/540
            "GitPython==2.0.8",
            "sphinx-git",
            "httpretty",
            "lxml",
            # Astroid is used by Pylint. Astroid 1.3 and above, and Pylint 1.4
            # and above no longer work with Python 2.6, and have been removed
            # from Pypi in 2/2016 after being available for some time.
            # Therefore, we cannot use Pylint under Python 2.6.
            # Also, Pylint does not support Python 3.
            "astroid" if sys.version_info[0:2] == (2, 7) else None,
            "pylint" if sys.version_info[0:2] == (2, 7) else None,
            "mock",
            'flake8',
            "pbr",  # needed by mock
            "twine",  # needed for upload to Pypi
        ],
        'install_os_requires': {
            # OS-level prereqs for 'install_os' command. Handled by os_setup
            # module.
            'Linux': {
                'redhat': [
                    "openssl-devel>=1.0.1",  # for M2Crypto installation
                    "gcc-c++>=4.4",         # for building Swig and for running
                                            #   Swig in M2Crypto install
                    install_swig,           # for running Swig in M2Crypto inst.
                    # Python-devel provides Python.h for Swig run.
                    # The following assumes we have python34, not python34u
                    "python34-devel" if py_version_m_n == "3.4" else \
                    "python35-devel" if py_version_m_n == "3.5" else \
                    "python-devel",
                ],
                'centos': 'redhat',
                'fedora': 'redhat',
                'ubuntu': [
                    "libssl-dev>=1.0.1",
                    "g++>=4.4",
                    install_swig,
                    "python-dev" if py_version_m == "2"
                    else "python%s-dev" % py_version_m,
                ],
                'debian': 'ubuntu',
                'linuxmint': 'ubuntu',
                'suse': [
                    "openssl-devel>=1.0.1",
                    "gcc-c++>=4.4",
                    install_swig,
                    "libpython%s-devel" % py_version_m_n,
                ],
            },
            # TODO: Add support for Windows.
        },
        'develop_os_requires': {
            # OS-level prereqs for 'develop_os' command, in addition to those
            # defined in 'install_os_requires'. Handled by os_setup module.
            'Linux': {
                'redhat': [
                    "libxml2-devel",        # for installing Python lxml pkg
                    "libxml2",              # for installing xmllint command
                    "libxslt-devel",        # for installing Python lxml pkg
                    "libyaml-devel",        # for installing Python pyyaml pkg
                    "make",                 # PyWBEM has a makefile
                    "tar",                  # for distribution archive
                    "git",                  # used by GitPython
                ],
                'centos': 'redhat',
                'fedora': 'redhat',
                'debian': [
                    "libxml2-dev",
                    "libxml2-utils",
                    "libxslt1-dev",
                    "libyaml-dev",
                    "make",
                    "tar",
                    "git",
                ],
                'ubuntu': [
                    "libxml2-dev",
                    "libxml2-utils",
                    "libxslt1-dev",
                    "libyaml-dev",
                    "make",
                    "tar",
                    "git",
                ],
                'linuxmint': [
                    "libxml2-dev",
                    "libxml2-utils",
                    "libxslt1-dev",
                    "libyaml-dev",
                    "make",
                    "tar",
                    "git",
                ],
                'suse': [
                    "libxml2-devel",
                    "libxml2",
                    "libxslt-devel",
                    "libyaml-devel",
                    "make",
                    "tar",
                    "git",
                ],
            },
            # TODO: Add support for Windows. Some notes:
            # - install lxml from its binaries at:
            #   http://www.lfd.uci.edu/~gohlke/pythonlibs/#lxml
        },
        'classifiers': [
            'Development Status :: 5 - Production/Stable',
            'Intended Audience :: Developers',
            'Intended Audience :: System Administrators',
            'License :: OSI Approved :: '\
            'GNU Lesser General Public License v2 or later (LGPLv2+)',
            'Operating System :: OS Independent',
            'Programming Language :: Python :: 2',
            'Programming Language :: Python :: 2.6',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 3.5',
            'Topic :: Software Development :: Libraries :: Python Modules',
            'Topic :: System :: Systems Administration',
        ],
    }

    _ON_RTD = os.environ.get('READTHEDOCS', None) == 'True'

    if sys.version_info[0] == 2 and not _ON_RTD:
        # RTD does not have Swig so we cannot install M2Crypto.

        # The 'install_requires' processing in distutils does not tolerate
        # a None value in the list, so we need be truly conditional (instead
        # of adding an entry with None).
        if platform.system() == 'Windows':
            if platform.architecture()[0] == '64bit':
                m2crypto_req = 'M2CryptoWin64>=0.21'
            else:
                m2crypto_req = 'M2CryptoWin32>=0.21'
        else:
            m2crypto_req = 'M2Crypto>=0.24'
        args['install_requires'].append(m2crypto_req)

    # The ordereddict package is a backport of collections.OrderedDict
    # to Python 2.6. OrderedDict is needed by the GitPython package
    # since its 2.0.3 version (but only from 2.0.5 on it is used
    # correctly, and only from 2.0.6 on does it work on Python 2.6).
    # GitPython is needed by sphinx-git. OrderedDict is also needed
    # by the pywbem._recorder module.
    if sys.version_info[0:2] == (2, 6):
        args['install_requires'].append('ordereddict')

    # The following retry logic attempts to handle the frequent xmlrpc
    # errors that recently (9/2016) have shown up with Pypi.
    tries = 2
    while True:
        tries -= 1
        try:
            setup(**args)
        except Fault as exc:
            if tries > 0:
                print("Warning: Retrying setup() because %s was raised: %s" %
                      (exc.__class__.__name__, exc))
                continue
            else:
                raise
        else:
            break

    if 'install' in sys.argv or 'develop' in sys.argv:
        build_moftab(_VERBOSE)

    return 0


if __name__ == '__main__':
    sys.exit(main())
