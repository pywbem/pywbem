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
Utility functionsto support pywbem_mock.
"""

import sys
import locale

__all__ = []

STDOUT_ENCODING = getattr(sys.stdout, 'encoding', None)
if not STDOUT_ENCODING:
    STDOUT_ENCODING = locale.getpreferredencoding()
if not STDOUT_ENCODING:
    STDOUT_ENCODING = 'utf-8'


def _uprint(dest, text):
    """
    Write text to dest, adding a newline character.

    Text may be a unicode string, or a byte string in UTF-8 encoding.
    It must not be None.

    If dest is None, the text is encoded to a codepage suitable for the current
    stdout and is written to stdout.

    Otherwise, dest must be a file path, and the text is encoded to a UTF-8
    Byte sequence and is appended to the file (opening and closing the file).
    """
    if isinstance(text, str):
        text = text + '\n'
    elif isinstance(text, bytes):
        text = text + b'\n'
    else:
        raise TypeError(
            f"text must be a unicode or byte string, but is {type(text)}")
    if dest is None:
        if isinstance(text, bytes):
            text = text.decode('utf-8')
        sys.stdout.write(text)
    elif isinstance(dest, (str, bytes)):
        if isinstance(text, str):
            kw = {'mode': 'a', 'encoding': 'utf-8'}
        else:
            kw = {'mode': 'ab'}
        with open(dest, **kw) as f:  # pylint: disable=unspecified-encoding
            f.write(text)
    else:
        raise TypeError(
            f"dest must be None or a string, but is {type(text)}")
