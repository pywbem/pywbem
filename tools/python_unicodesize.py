#!/usr/bin/env python

import sys

# Method 1: Test whether s.decode() returns surrogate pair or single char
s = b'\\U00010142'
c = s.decode('unicode-escape')
if len(c) == 1:
    size1 = 'wide'
elif len(c) == 2:
    size1 = 'narrow'
else:
    raise AssertionError(
        f"python_unicodesize.py: Length of Unicode character {s} returned from "
        f"s.decode() must be 1 or 2 but is: {len(c)}")

# Method 2: Test whether unichr() fails
try:
    if sys.version_info[0] == 2:
        unichr(65858)  # U+10142
    else:
        chr(65858)  # U+10142
except ValueError:
    size2 = 'narrow'
else:
    size2 = 'wide'

if size1 != size2:
    raise AssertionError(
        "python_unicodesize.py: Different results for unicode size: "
        f"s.decode() method: {size1}, unichr() method: {size2}")

print(f"Unicode size of Python environment: {size1}")
