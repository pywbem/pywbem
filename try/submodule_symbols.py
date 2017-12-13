#!/usr/bin/env python

import sys
import types
import importlib

import pywbem


def main():

    try:
        version = pywbem.__version__
    except AttributeError:
        try:
            version = pywbem._version
        except AttributeError:
            version = '?'

    with open('try/submodule_symbols_0_12_0.txt') as fp:
        lines = fp.readlines()

    print("Submodule symbols from 0.12.0 that did not exist in version %s:" %
          version)

    new_submods = set()
    for line in lines:
        submod_name, kind, sym_name = line.split()

        try:
            submod = getattr(pywbem, submod_name)
        except AttributeError:
            # submodule not automatically imported when main module imported
            # (e.g. mof_compiler before pywbem 0.10)
            try:
                importlib.import_module('pywbem.%s' % submod_name)
            except ImportError:
                new_submods.add(submod_name)
                continue
            submod = getattr(pywbem, submod_name)

        if not hasattr(submod, sym_name):
            print("  %s.%s (%s)" % (submod_name, sym_name, kind))

    if new_submods:
        print("Submodules that did not exist yet in version %s:" %
              version)
    for name in new_submods:
        print("  %s" % name)

    return 0


if __name__ == '__main__':
    sys.exit(main())
