#!/usr/bin/env python
#
# (C) Copyright 2004 Hewlett-Packard Development Company, L.P.
# Copyright 2017 IBM Corp.
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

"""
Setup script for pywbem project.
"""

import sys
import os
import re
import setuptools
from distutils import log


def get_version(version_file):
    """
    Execute the specified version file and return the value of the __version__
    global variable that is set in the version file.

    Note: Make sure the version file does not depend on any packages in the
    requirements list of this package (otherwise it cannot be executed in
    a fresh Python environment).
    """
    with open(version_file, 'r') as fp:
        version_source = fp.read()
    _globals = {}
    exec(version_source, _globals)  # pylint: disable=exec-used
    return _globals['__version__']


def get_requirements(requirements_file):
    """
    Parse the specified requirements file and return a list of its non-empty,
    non-comment lines. The returned lines are without any trailing newline
    characters.
    """
    with open(requirements_file, 'r') as fp:
        lines = fp.readlines()
    reqs = []
    for line in lines:
        line = line.strip('\n')
        if not line.startswith('#') and line != '':
            reqs.append(line)
    return reqs


def read_file(a_file):
    """
    Read the specified file and return its content as one string.
    """
    with open(a_file, 'r') as fp:
        content = fp.read()
    return content


class PytestCommand(setuptools.Command):
    """
    Base class for setup.py commands for executing tests for this package
    using pytest.

    Note on the class name: Because distutils.dist._show_help() shows the class
    name for the setup.py command name instead of invoking get_command_name(),
    the classes that get registered as commands must have the command name.
    """

    description = None  # Set by subclass
    my_test_dirs = None  # Set by subclass

    user_options = [
        (
            'pytest-options=',  # '=' indicates it requires an argument
            None,  # no short option
            "additional options for pytest, as one argument"
        ),
    ]

    def initialize_options(self):
        self.test_opts = None
        self.test_dirs = None
        self.pytest_options = None

    def finalize_options(self):
        self.test_opts = [
            '--color=yes',
            '-s',
            '-W', 'default',
            '-W', 'ignore::PendingDeprecationWarning',
        ]
        if sys.version_info[0] == 3:
            self.test_opts.extend([
                '-W', 'ignore::ResourceWarning',
            ])
        self.test_dirs = self.my_test_dirs

    def run(self):
        import pytest  # deferred import so install does not depend on it
        args = self.test_opts
        if self.pytest_options:
            args.extend(self.pytest_options.split(' '))
        args.extend(self.test_dirs)
        if self.dry_run:
            self.announce("Dry-run: pytest {}".format(' '.join(args)),
                          level=log.INFO)
            return 0
        else:
            self.announce("pytest {}".format(' '.join(args)),
                          level=log.INFO)
            rc = pytest.main(args)
            return rc


class test(PytestCommand):
    """
    Setup.py command for executing unit and function tests.
    """
    description = "pywbem: Run unit and function tests using pytest"
    my_test_dirs = ['tests/unittest', 'tests/functiontest']


class leaktest(PytestCommand):
    """
    Setup.py command for executing leak tests.
    """
    description = "pywbem: Run leak tests using pytest"
    my_test_dirs = ['tests/leaktest']


class end2endtest(PytestCommand):
    """
    Setup.py command for executing end2end tests.
    """
    description = "pywbem: Run end2end tests using pytest"
    my_test_dirs = ['tests/end2endtest']

    def finalize_options(self):
        PytestCommand.finalize_options(self)  # old-style class
        self.test_opts.extend([
            '-v', '--tb=short',
        ])


# pylint: disable=invalid-name
requirements = get_requirements('requirements.txt')
install_requires = [req for req in requirements
                    if req and not re.match(r'[^:]+://', req)]
dependency_links = [req for req in requirements
                    if req and re.match(r'[^:]+://', req)]

test_requirements = get_requirements('test-requirements.txt')

package_version = get_version(os.path.join('pywbem', '_version.py'))

# Docs on setup():
# * https://docs.python.org/2.7/distutils/apiref.html?
#   highlight=setup#distutils.core.setup
# * https://setuptools.readthedocs.io/en/latest/setuptools.html#
#   new-and-changed-setup-keywords
setuptools.setup(
    name='pywbem',
    version=package_version,
    packages=[
        'pywbem',
        'pywbem_mock'
    ],
    include_package_data=True,  # Includes MANIFEST.in files into sdist (only)
    scripts=[
        'mof_compiler', 'mof_compiler.bat'
    ],
    install_requires=install_requires,
    dependency_links=dependency_links,
    extras_require={
        "test": test_requirements,
    },
    cmdclass={
        'test': test,
        'leaktest': leaktest,
        'end2endtest': end2endtest,
    },
    description='pywbem - A WBEM client',
    long_description=read_file('README_PYPI.rst'),
    long_description_content_type='text/x-rst',
    license='LGPL version 2.1, or (at your option) any later version',
    author='Tim Potter',
    author_email='tpot@hp.com',
    maintainer='Andreas Maier, Karl Schopmeyer',
    maintainer_email='maiera@de.ibm.com, k.schopmeyer@swbell.net',
    url='https://pywbem.github.io/pywbem/',
    project_urls={
        'Bug Tracker': 'https://github.com/pywbem/pywbem/issues',
        'Documentation': 'https://pywbem.readthedocs.io/en/latest/',
        'Source Code': 'https://github.com/pywbem/pywbem',
    },

    options={'bdist_wheel': {'universal': True}},
    zip_safe=True,  # This package can safely be installed from a zip file
    platforms='any',

    # Keep these Python versions in sync with pywbem/__init__.py
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: '
        'GNU Lesser General Public License v2 or later (LGPLv2+)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Systems Administration',
    ]
)
