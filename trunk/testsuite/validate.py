#!/usr/bin/python
#
# (C) Copyright 2004,2005 Hewlett-Packard Development Company, L.P.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

# Validate XML input on stdin against the CIM DTD.

# Author: Tim Potter <tpot@hp.com>

import sys, os, string
from subprocess import Popen, PIPE

DTD_FILE = 'CIM_DTD_V22.dtd'

def validate_xml(data, dtd_directory=None):

    # Run xmllint to validate file

    dtd_file = DTD_FILE
    if dtd_directory is not None:
        dtd_file = '%s/%s' % (dtd_directory, DTD_FILE)

    p = Popen('xmllint --dtdvalid %s --noout -' % dtd_file, stdout=PIPE,
              stderr=PIPE, stdin=PIPE, shell=True)

    p.stdin.write(data)
    p.stdin.close()

    [sys.stdout.write(x) for x in p.stdout.readlines()]

    status = p.wait()

    if status != 0:
        return False

    return True

if __name__ == '__main__':

    data = string.join(sys.stdin.readlines(), '')
    sys.exit(validate_xml(data))
