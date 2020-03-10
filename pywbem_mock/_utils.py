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

from __future__ import absolute_import, print_function

import locale
import sys
import six

if six.PY2:
    import codecs  # pylint: disable=wrong-import-order

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
    if isinstance(text, six.text_type):
        text = text + u'\n'
    elif isinstance(text, six.binary_type):
        text = text + b'\n'
    else:
        raise TypeError(
            "text must be a unicode or byte string, but is {0}".
            format(type(text)))
    if dest is None:
        if six.PY2:
            # On py2, stdout.write() requires byte strings
            if isinstance(text, six.text_type):
                text = text.encode(STDOUT_ENCODING, 'replace')
        else:
            # On py3, stdout.write() requires unicode strings
            if isinstance(text, six.binary_type):
                text = text.decode('utf-8')
        sys.stdout.write(text)
    elif isinstance(dest, (six.text_type, six.binary_type)):
        if isinstance(text, six.text_type):
            open_kwargs = dict(mode='a', encoding='utf-8')
        else:
            open_kwargs = dict(mode='ab')
        if six.PY2:
            # Open with codecs to be able to set text mode
            with codecs.open(dest, **open_kwargs) as f:
                f.write(text)
        else:
            with open(dest, **open_kwargs) as f:
                f.write(text)
    else:
        raise TypeError(
            "dest must be None or a string, but is {0}".
            format(type(text)))
