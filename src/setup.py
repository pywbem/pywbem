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
_version = '0.8.0rc4'

import re
import sys
import os
import shutil

import os_setup
from os_setup import shell, shell_check, import_setuptools

def install_swig(command):
    """Make sure Swig is installed, either by installing the corresponding
    OS-level package, or by downloading the source and building it.

    Parameters:
    * command: setuptools.Command object for the command in whose context
      this function is called.
    """
    inst = command.installer
    dry_run = command.dry_run

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

        system = inst.system
        distro = inst.distro

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

        swig_version_req = ">=%s" % swig_min_version

        if inst.is_available(swig_pkg_name, swig_version_req):

            # Install Swig as a package
            inst.install(swig_pkg_name, swig_version_req, dry_run)

        else:

            # Build Swig from its source
            swig_build_version = "2.0.12"
            swig_dir = "swig-%s" % swig_build_version
            swig_tar_file = "swig-%s.tar.gz" % swig_build_version
            swig_install_root = "/usr"

            print "Installing prerequisite OS-level packages for building "\
                "Swig..."

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
                inst.ensure_installed(swig_prereq_pkg_name, None, dry_run)

            if dry_run:
                print "Dry-running: Building Swig version %s from "\
                    "downloaded source, and installing to %s tree" %i\
                    (swig_build_version, swig_install_root)
            else:
                print "Building Swig version %s from "\
                    "downloaded source, and installing to %s tree" %i\
                    (swig_build_version, swig_install_root)

                if os.path.exists(swig_dir):
                    print "Removing previously downloaded Swig directory: %s" %\
                        swig_dir
                    shutil.rmtree(swig_dir)

                print "Downloading Swig source archive: %s" % swig_tar_file
                shell_check(
                    "wget -q -O %s http://sourceforge.net/projects/swig/files"\
                    "/swig/%s/%s/download" %\
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

                print "Done downloading, building and installing Swig "\
                    "version %s" % swig_build_version

def patch_epydoc(command):
    """
    Patch Epydoc 3.0.1 (if not yet done) with the patches from:
    http://cvs.pld-linux.org/cgi-bin/viewvc.cgi/cvs/packages/epydoc/

    Parameters:
    * command: setuptools.Command object for the command in whose context
      this function is called.
    """
    # Find the active version of Epydoc

    if command.dry_run:
        print "Dry-running: Patching Epydoc"
    else:
        print "Patching Epydoc"

        import epydoc
        epydoc_target_dir = os.path.dirname(epydoc.__file__)
        epydoc_patch_dir = epydoc_target_dir+"/epydoc-3.0.1-patches"

        print "Epydoc patch directory: %s" % epydoc_patch_dir

        if os.path.exists(epydoc_patch_dir):
            print "Assuming Epydoc patches have already been applied, because "\
                "patch directory exists"
        else:
            print "Downloading Epydoc patches into patch directory: %s" %\
                epydoc_patch_dir
            shell_check("mkdir -p %s" % epydoc_patch_dir)
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
            print "Applying Epydoc patches to Epydoc installation directory: "\
                "%s" % epydoc_target_dir
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

def main():

    import_setuptools()
    from setuptools import setup

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
        'distclass': os_setup.OsDistribution,
        'cmdclass': {
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
            'pywbem/wbemcli.py',
            'pywbem/mof_compiler.py',
        ],
        # TODO: Finalize this temporary fix: Use our own fork of M2Crypto with
        # fixes for installation issues. This only seems to work if no version
        # is specified in its install_requires entry.
        'dependency_links': [
            "git+https://github.com/pywbem/m2crypto@amfix2#egg=M2Crypto"
        ],
        'install_requires': [
            # These dependencies will be installed as a site package.
            # They are not useable by this setup script, if they are eggs
            # (because their path is added to a .pth file which is parsed only
            # at Python startup time).
            #'M2Crypto>=0.22.6',
            'M2Crypto',
        ],
        'develop_requires' : [
            # Python prereqs for 'develop' command. Handled by os_setup module.
            "epydoc>=3.0.1",
            patch_epydoc,
            "docutils>=0.12",
            "httpretty",
            "lxml",
            "pyyaml",
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
                    "python-devel",         # to get Python.h for Swig run
                    "git>=1.7",             # for retrieving fixed M2Crypto
                ],
                'centos': 'redhat',
                'fedora': 'redhat',
                'debian': [
                    "libssl-dev>=1.0.1",
                    "g++>=4.4",
                    install_swig,
                    "python2.7-dev",
                    "git>=1.7",
                ],
                'ubuntu': [                 
                    "libssl-dev>=1.0.1",
                    "g++>=4.4",
                    install_swig,
                    "python2.7-dev",
                    "git>=1.7",
                ],
                'suse': [
                    "openssl-devel>=1.0.1",
                    "gcc-c++>=4.4",
                    install_swig,
                    "libpython2.7-devel",
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
                    "libxslt-devel",        # for installing Python lxml pkg
                    "libyaml-devel",        # for installing Python pyyaml pkg
                    "make",                 # PyWBEM has a makefile
                    "zip",                  # for building distribution archive
                    "unzip",                # for installing distrib. archive
                    "patch",                # for patching Epydoc
                    "pylint>=1.3",          # for make check
                ],
                'centos': 'redhat',
                'fedora': 'redhat',
                'debian': [
                    "libxml2-dev",
                    "libxslt1-dev",
                    "libyaml-dev",
                    "make",
                    "zip",
                    "unzip",
                    "patch",
                    "pylint>=1.1",          # TODO: This is a compromise; more
                                            # ideally, the Python pylint
                                            # package would be used.
                ],
                'ubuntu': [
                    "libxml2-dev",
                    "libxslt1-dev",
                    "libyaml-dev",
                    "make",
                    "zip",
                    "unzip",
                    "patch",
                    "pylint>=0.25",         # TODO: This is a compromise; more
                                            # ideally, the Python pylint
                                            # package would be used.
                ],
                'suse': [
                    "libxml2-devel",
                    "libxslt-devel",
                    "libyaml-devel",
                    "make",
                    "zip",
                    "unzip",
                    "patch",
                    "pylint>=1.3",
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
            'Topic :: Software Development :: Libraries :: Python Modules',
            'Topic :: System :: Systems Administration',
        ],
    }
    setup(**args)
    return 0

if __name__ == '__main__':
    sys.exit(main())
