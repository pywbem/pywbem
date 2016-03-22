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

"""
PyWBEM is a WBEM client and some related utilities, written in pure Python.

A WBEM client allows issuing operations to a WBEM server, using the CIM
operations over HTTP (CIM-XML) protocol defined in the DMTF standards DSP0200
and DSP0201. See http://www.dmtf.org/standards/wbem for information about
WBEM. This is used for all kinds of systems management tasks that are
supported by the system running the WBEM server.
"""

from __future__ import print_function, absolute_import

import re
import sys
import os
import shutil
from distutils.errors import DistutilsSetupError

# Workaround for Python 2.6 issue https://bugs.python.org/issue15881
# This causes this module to be referenced and prevents the premature
# unloading and subsequent garbage collection causing the error.
if sys.version_info[0:2] == (2, 6):
    try:
        import multiprocessing #pylint: disable=unused-import
    except ImportError:
        pass

import os_setup
from os_setup import shell, shell_check, import_setuptools

# Package version - Keep in sync with pywbem/__init__.py!
_version = '0.9.0.dev0'  # pylint: disable=invalid-name

def install_swig(installer, dry_run, verbose):
    """Custom installer function for `os_setup` module.
    This function makes sure that Swig is installed, either by installing the
    corresponding OS-level package, or by downloading the source and building
    it.

    Parameters: see description of `os_setup` module.
    """

    swig_min_version = "2.0"

    if verbose:
        print("Testing for availability of Swig >=%s in PATH..." %\
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
                print("Installed Swig version is too old: %s; "\
                      "need to get Swig" % swig_version)
            get_swig = True
        else:
            if verbose:
                print("Installed Swig version is sufficient: %s" %\
                      swig_version)

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

        if not installed:

            # Build Swig from its source
            swig_build_version = "2.0.12"
            swig_dir = "swig-%s" % swig_build_version
            swig_tar_file = "swig-%s.tar.gz" % swig_build_version
            swig_install_root = "/usr"

            if verbose:
                print("Installing prerequisite OS-level packages for building "\
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
                    print("Dry-running: Building Swig version %s from "\
                          "downloaded source, and installing to %s tree" %\
                          (swig_build_version, swig_install_root))
            else:
                if verbose:
                    print("Building Swig version %s from "\
                          "downloaded source, and installing to %s tree" %\
                          (swig_build_version, swig_install_root))

                if os.path.exists(swig_dir):
                    if verbose:
                        print("Removing previously downloaded Swig directory: "\
                              "%s" % swig_dir)
                    shutil.rmtree(swig_dir)

                if verbose:
                    print("Downloading Swig source archive: %s" % swig_tar_file)
                shell_check(
                    "wget -q -O %s http://sourceforge.net/projects/swig/files"\
                    "/swig/%s/%s/download" %\
                    (swig_tar_file, swig_dir, swig_tar_file), display=True)
                if verbose:
                    print("Unpacking Swig source archive: %s" % swig_tar_file)
                shell_check("tar -xf %s" % swig_tar_file, display=True)

                if verbose:
                    print("Configuring Swig build process for installing to "\
                          "%s tree..." % swig_install_root)
                shell_check(["sh", "-c", "cd %s; ./configure --prefix=%s" %\
                            (swig_dir, swig_install_root)],
                            display=True)

                if verbose:
                    print("Building Swig...")
                shell_check(["sh", "-c", "cd %s; make swig" % swig_dir],
                            display=True)

                if verbose:
                    print("Installing Swig to %s tree..." % swig_install_root)
                shell_check(["sh", "-c", "cd %s; sudo make install" % swig_dir],
                            display=True)

                if verbose:
                    print("Done downloading, building and installing Swig "\
                          "version %s" % swig_build_version)

def patch_epydoc(installer, dry_run, verbose): # pylint: disable=unused-argument
    """Custom installer function for `os_setup` module.
    This function patches Epydoc 3.0.1 (if not yet done) with the patches from:
    http://cvs.pld-linux.org/cgi-bin/viewvc.cgi/cvs/packages/epydoc/

    Parameters: see description of `os_setup` module.
    """

    if dry_run:
        if verbose:
            print("Dry-running: Patching Epydoc")
    else:
        if verbose:
            print("Patching Epydoc")

        import epydoc
        epydoc_target_dir = os.path.dirname(epydoc.__file__)
        epydoc_patch_dir = epydoc_target_dir+"/epydoc-3.0.1-patches"

        if verbose:
            print("Epydoc patch directory: %s" % epydoc_patch_dir)

        if os.path.exists(epydoc_patch_dir):
            if verbose:
                print("Assuming Epydoc patches have already been applied, "\
                      "because patch directory exists")
        else:
            if verbose:
                print("Downloading Epydoc patches into patch directory: %s" %\
                      epydoc_patch_dir)
            shell_check("mkdir -p %s" % epydoc_patch_dir, display=True)
            shell_check("wget -q -O %s/epydoc-rst.patch "\
                        "http://cvs.pld-linux.org/cgi-bin/viewvc.cgi/cvs/"\
                        "packages/epydoc/epydoc-rst.patch?revision=1.1&"\
                        "view=co" % epydoc_patch_dir, display=True)
            shell_check("wget -q -O %s/epydoc-cons_fields_stripping.patch "\
                        "http://cvs.pld-linux.org/cgi-bin/viewvc.cgi/cvs/"\
                        "packages/epydoc/epydoc-cons_fields_stripping.patch?"\
                        "view=co" % epydoc_patch_dir, display=True)
            shell_check("wget -q -O %s/epydoc-__package__.patch "\
                        "http://cvs.pld-linux.org/cgi-bin/viewvc.cgi/cvs/"\
                        "packages/epydoc/epydoc-__package__.patch?"\
                        "revision=1.1&view=co" % epydoc_patch_dir, display=True)
            if verbose:
                print("Applying Epydoc patches to Epydoc installation "\
                      "directory: %s" % epydoc_target_dir)
            shell_check("patch -N -r %s/epydoc-rst.patch.rej "
                        "-i %s/epydoc-rst.patch "
                        "%s/markup/restructuredtext.py" %\
                        (epydoc_patch_dir, epydoc_patch_dir, epydoc_target_dir),
                        display=True, exp_rc=(0, 1))
            shell_check("patch -N -r %s/epydoc-cons_fields_stripping.patch.rej "
                        "-i %s/epydoc-cons_fields_stripping.patch "
                        "%s/markup/restructuredtext.py" %\
                        (epydoc_patch_dir, epydoc_patch_dir, epydoc_target_dir),
                        display=True, exp_rc=(0, 1))
            shell_check("patch -N -r %s/epydoc-__package__.patch.rej "
                        "-i %s/epydoc-__package__.patch "
                        "%s/docintrospecter.py" %\
                        (epydoc_patch_dir, epydoc_patch_dir, epydoc_target_dir),
                        display=True, exp_rc=(0, 1))

def main():
    """Main function of this script."""

    import_setuptools()
    from setuptools import setup
    from distutils.command.install import install as _install

    class install(_install):
    # pylint: disable=invalid-name,too-few-public-methods

        def run(self):
            pre_install(self.verbose, self.dry_run)
            _install.run(self)

    def pre_install(verbose=False, dry_run=False):

        cmd = "pip install ply"
        if dry_run:
            print("Dry-running: %s" % cmd)
        else:
            print("Running: %s" % cmd)
            shell_check(cmd, display=verbose)

        if dry_run:
            print("Dry-running: MOF Compiler build")
        else:
            print("Running: MOF Compiler build")
            from pywbem import mof_compiler
            mof_compiler._build(verbose)

    py_version_m_n = "%s.%s" % (sys.version_info[0], sys.version_info[1])
    py_version_m = "%s" % sys.version_info[0]

    args = {
        'name': 'pywbem',
        'author': 'Tim Potter',
        'author_email': 'tpot@hp.com',
        'maintainer': 'Andreas Maier',
        'maintainer_email': 'maiera@de.ibm.com',
        'description': 'PyWBEM Client - A WBEM client and related utilities',
        'long_description': __doc__,
        'platforms': ['any'],
        'url': 'http://pywbem.github.io/pywbem/',
        'version': _version,
        'license': 'LGPL version 2.1, or (at your option) any later version',
        'distclass': os_setup.OsDistribution,
        'cmdclass': {
            'install': install,
            'install_os': os_setup.install_os,
            'develop_os': os_setup.develop_os,
            'develop': os_setup.develop,
        },
        'packages': ['pywbem'],
        'package_data': {
            'pywbem': [
                'NEWS',
                'LICENSE.txt',
            ]
        },
        'scripts': [
            'wbemcli',
            'mof_compiler',
        ],
        # TODO: The following uses the master branch of the upstream M2Crypto
        # repo, which as of 2016-02-15 has all necessary fixes. Once ts next
        # version (0.24.0) is released, we can use that version from PyPI
        # again, by removing the following parameter and re-enabling the
        # version requirement on the M2Crypto entry of the 'install_requires'
        # parameter.
        # Note: This only seems to work if no version is specified in its
        # 'install_requires' entry.
        'dependency_links': [
            "git+https://gitlab.com/m2crypto/m2crypto.git@master#egg=M2Crypto"
        ],
        'install_requires': [
            # These dependencies will be installed as a site package.
            # They are not useable by this setup script, if they are eggs
            # (because their path is added to a .pth file which is parsed only
            # at Python startup time).
            'six',
            'ply',
        ],
        'develop_requires' : [
            # Python prereqs for 'develop' command. Handled by os_setup module.
            "pytest>=2.4",
            "pytest-cov",
            # Epydoc does not support Python 3.
            "epydoc==3.0.1" if sys.version_info[0] == 2 else None,
            patch_epydoc if sys.version_info[0] == 2 else None,
            "docutils>=0.12",
            "httpretty",
            "lxml",
            "PyYAML",   # Pypi package name of "yaml" package.
            # Astroid is used by Pylint. Astroid 1.3 and above, and Pylint 1.4
            # and above no longer work with Python 2.6, and have been removed
            # from Pypi in 2/2016 after being available for some time.
            # Therefore, we cannot use Pylint under Python 2.6.
            # Also, Pylint does not support Python 3.
            "astroid" if sys.version_info[0:2] == (2, 7) else None,
            "pylint" if sys.version_info[0:2] == (2, 7) else None,
        ],
        'install_os_requires': {
            # OS-level prereqs for 'install_os' command. Handled by os_setup
            # module.
            'Linux': {
                'redhat': [
                    "openssl-devel>=1.0.1", # for M2Crypto installation
                    "gcc-c++>=4.4",         # for building Swig and for running
                                            #   Swig in M2Crypto install
                    install_swig,           # for running Swig in M2Crypto inst.
                    # Python-devel provides Python.h for Swig run.
                    ["python34-devel", "python34u-devel", "python3-devel"] \
                        if py_version_m_n == "3.4" else \
                    ["python35-devel", "python35u-devel", "python3-devel"] \
                        if py_version_m_n == "3.5" else \
                    "python-devel",
                    "git>=1.7",             # for retrieving fixed M2Crypto
                ],
                'centos': 'redhat',
                'fedora': 'redhat',
                'ubuntu': [
                    "libssl-dev>=1.0.1",
                    "g++>=4.4",
                    install_swig,
                    "python-dev" if py_version_m == "2"
                    else "python%s-dev" % py_version_m,
                    "git>=1.7",
                ],
                'debian': 'ubuntu',
                'suse': [
                    "openssl-devel>=1.0.1",
                    "gcc-c++>=4.4",
                    install_swig,
                    "libpython%s-devel" % py_version_m_n,
                    "git>=1.7",
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
                    "zip",                  # for building distribution archive
                    "unzip",                # for installing distrib. archive
                    "patch",                # for patching Epydoc
                ],
                'centos': 'redhat',
                'fedora': 'redhat',
                'debian': [
                    "libxml2-dev",
                    "libxml2-utils",
                    "libxslt1-dev",
                    "libyaml-dev",
                    "make",
                    "zip",
                    "unzip",
                    "patch",
                ],
                'ubuntu': [
                    "libxml2-dev",
                    "libxml2-utils",
                    "libxslt1-dev",
                    "libyaml-dev",
                    "make",
                    "zip",
                    "unzip",
                    "patch",
                ],
                'suse': [
                    "libxml2-devel",
                    "libxml2",
                    "libxslt-devel",
                    "libyaml-devel",
                    "make",
                    "zip",
                    "unzip",
                    "patch",
                ],
            },
            # TODO: Add support for Windows. Some notes:
            # - install lxml from its binaries at:
            #   http://www.lfd.uci.edu/~gohlke/pythonlibs/#lxml
        },
        'classifiers' : [
            'Development Status :: 6 - Mature',
            'Intended Audience :: Developers',
            'Intended Audience :: System Administrators',
            'License :: OSI Approved :: '\
                'GNU Lesser General Public License v2 or later (LGPLv2+)',
            'Operating System :: OS Independent',
            'Programming Language :: Python :: 2.6',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 3.5',
            'Topic :: Software Development :: Libraries :: Python Modules',
            'Topic :: System :: Systems Administration',
        ],
    }

    if sys.version_info[0] == 2:
        # The 'install_requires' processing in distutils does not tolerate
        # a None value in the list, so we need be truly conditional (instead
        # of adding an entry with None.
        args['install_requires'] += [
            # 'M2Crypto>=0.23',   # Disabled for now, see comment on
            #                     # 'dependency_links'.
            'M2Crypto',
        ]

    setup(**args)
    return 0

if __name__ == '__main__':
    sys.exit(main())
