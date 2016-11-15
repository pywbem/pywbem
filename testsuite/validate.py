#!/usr/bin/env python
#
# (C) Copyright 2004,2005 Hewlett-Packard Development Company, L.P.
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
Validate XML instance data against the CIM-XML DTD.

Can also be invoked as a script for testing purposes, and then validates
XML data specified in standard input.
"""

from __future__ import print_function, absolute_import

import sys
import os
import os.path
from subprocess import Popen, PIPE, STDOUT

from pywbem.cim_obj import _ensure_bytes

DTD_FILE = 'CIM_DTD_V22.dtd'


def validate_xml(data, dtd_directory=None, root_elem=None):
    """
    Validate the provided XML instance data against a CIM-XML DTD, optionally
    requiring a particular XML root element.

    Arguments:

      * `data`: XML instance data to be validated.
      * `dtd_directory`: Directory with the DTD file (see `DTD_FILE` for name).
      * `root_elem`: Name of XML element that is expected as the root element
        in the XML instance data to be validated. None means no checking for
        a particular root element is performed.
    """

    dtd_file = DTD_FILE
    if dtd_directory is not None:
        dtd_file = os.path.join(dtd_directory, DTD_FILE).replace('\\', '/')

    # Make sure the XML data requires the specified root element, if any
    if root_elem is not None:
        data = '<!DOCTYPE %s SYSTEM "%s">\n' % (root_elem, dtd_file) + data
        xmllint_cmd = 'xmllint --valid --noout -'
    else:
        xmllint_cmd = 'xmllint --dtdvalid %s --noout -' % dtd_file

    p = Popen(xmllint_cmd, stdout=PIPE, stderr=STDOUT, stdin=PIPE, shell=True)

    data = _ensure_bytes(data)
    p.stdin.write(data)
    p.stdin.close()

    first_time = True
    for x in p.stdout.readlines():
        if first_time:
            first_time = False
            print("\nOutput from xmllint:")
        sys.stdout.write(x)

    status = p.wait()

    if status != 0:
        return False

    return True


if __name__ == '__main__':
    sys.exit(validate_xml(''.join(sys.stdin.readlines())))
