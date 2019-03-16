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
Setup script.
"""

import setuptools

setuptools.setup(
    setup_requires=['pbr>=1.10'],

    # Specifying python_requires in setup.cfg would be more logical
    # but requires setuptools>=34.0.0, hence it is specified here.
    # This works with the current minimum versions of
    # setuptools=33.1.1 and pip=9.0.1.
    # !!! Make sure to keep the supported Python versions in sync
    # between setup.py, setup.cfg and pywbem/__init__.py !!!
    python_requires='>=2.6, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*',

    pbr=True)
