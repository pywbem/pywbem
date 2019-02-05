#!/usr/bin/env python

import ctypes

pointer_bits = ctypes.sizeof(ctypes.c_void_p) * 8

print("Bit size of Python environment: {0} bit".format(pointer_bits))
