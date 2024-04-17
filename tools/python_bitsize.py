#!/usr/bin/env python

import ctypes

pointer_bits = ctypes.sizeof(ctypes.c_void_p) * 8

print(f"Bit size of Python environment: {pointer_bits} bit")
