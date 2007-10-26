#!/usr/bin/python
#
# (C) Copyright 2004 Hewlett-Packard Development Company, L.P.
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

# Validate XML input on stdin against the CIM DTD.  We use some
# trickyness in the added DOCTYPE tag to allow us to validate document
# fragments.

# Author: Tim Potter <tpot@hp.com>
# Author: Martin Pool <mbp@hp.com>

import sys, string, pyRXP
from optparse import OptionParser

def validate_xml(xml, toplevel, include):
    """Add a DOCTYPE tag - yuck.  I wonder why all the XML generated
    by Pegasus doesn't have one?"""

    # Special kludge: add a DOCTYPE tag after the first line, which is the
    # XML version.  Ew, yuck.
    
    line1, rest = xml.split('\n', 1)

    fixed = (line1 +
             ('<!DOCTYPE %s SYSTEM "%s/CIM_DTD_V211.dtd">\n' % 
              (toplevel, include))
             + rest)

    pyRXP.Parser().parse(fixed)


if __name__ == '__main__':
    try:
        # OptionParser rocks, although is only present in Python 2.3
        parser = OptionParser()
        parser.add_option('-t', '--toplevel', type='string', dest='toplevel',
                          metavar='TAG', default='CIM',
                          help='Specify toplevel document tag')
        parser.add_option('-I', '--include', type='string', dest='include',
                          metavar='DIR', default='.',
                          help='Path to include DTD file')

        options, args = parser.parse_args()

        validate_xml(sys.stdin.read(), options.toplevel, options.include)
    except pyRXP.error, arg:
        print arg
        sys.exit(1)
        
