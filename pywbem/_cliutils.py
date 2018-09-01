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
Internal module with utility stuff for command line programs.
"""

from __future__ import print_function, absolute_import

import argparse


class SmartFormatter(argparse.HelpFormatter):
    """Formatter class for `argparse`, that respects newlines in help strings.

    Idea and code from: https://stackoverflow.com/a/22157136

    Usage:
        If an argparse argument help text starts with 'R|', it will be treated
        as a *raw* string that does line formatting on its own by specifying
        newlines appropriately. The string should not exceed 55 characters per
        line. Indentation handling is still applied automatically and does not
        need to be specified within the string.

        Otherwise, the strings are formatted as normal and newlines are
        treated like blanks.

    Limitations:
        It seems this only works for the `help` argument of
        `ArgumentParser.add_argument()`, and not for group descriptions,
        and usage, description, and epilog of ArgumentParser.
    """

    def _split_lines(self, text, width):
        if text.startswith('R|'):
            return text[2:].splitlines()
        return argparse.HelpFormatter._split_lines(self, text, width)
