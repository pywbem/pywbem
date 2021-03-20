# -*- coding: utf-8 -*-
#
# (C) Copyright 2018 InovaDevelopment.com
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
# Author: Karl  Schopmeyer <inovadevelopment.com>
#

"""
A conftest.py file is a Python module that is recognized by pytest via its name
and that contains directory-specific pytest hook implementations. See
https://docs.pytest.org/en/latest/writing_plugins.html#local-conftest-plugins.

This particular conftest.py module is responsible for common pytest fixtures
for testing of pywbem_mock
"""

import pytest
from pywbem_mock import FakedWBEMConnection


@pytest.fixture()
def conn():
    """
    Create the FakedWBEMConnection and return it. This includes the
    standard default namespace.
    """
    # pylint: disable=protected-access
    FakedWBEMConnection._reset_logging_config()
    return FakedWBEMConnection()


@pytest.fixture()
def tst_qualifiers_mof():
    """
    Mof string defining qualifier declarations for tests.
    """
    return """
        Qualifier Association : boolean = false,
            Scope(association),
            Flavor(DisableOverride, ToSubclass);

        Qualifier Indication : boolean = false,
            Scope(class, indication),
            Flavor(DisableOverride, ToSubclass);

        Qualifier Abstract : boolean = false,
            Scope(class, association, indication),
            Flavor(EnableOverride, Restricted);

        Qualifier Aggregate : boolean = false,
            Scope(reference),
            Flavor(DisableOverride, ToSubclass);

        Qualifier Description : string = null,
            Scope(any),
            Flavor(EnableOverride, ToSubclass, Translatable);

        Qualifier In : boolean = true,
            Scope(parameter),
            Flavor(DisableOverride, ToSubclass);

        Qualifier Key : boolean = false,
            Scope(property, reference),
            Flavor(DisableOverride, ToSubclass);

        Qualifier Out : boolean = false,
            Scope(parameter),
            Flavor(DisableOverride, ToSubclass);

        Qualifier Override : string = null,
            Scope(property, reference, method),
            Flavor(EnableOverride, Restricted);

        Qualifier Static : boolean = false,
            Scope(property, method),
            Flavor(DisableOverride, ToSubclass);

        Qualifier EmbeddedInstance : string = null,
            Scope(property, method, parameter);
        """
