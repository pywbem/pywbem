#!/usr/bin/env python

import sys
import types

import pywbem


def main():

    sym_exclude_list = ['absolute_import']

    datas = []
    functions = []
    classes = []

    for sym_name in sorted(dir(pywbem)):
        sym = getattr(pywbem, sym_name)

        if isinstance(sym, types.ModuleType):
            continue
        if sym_name.startswith('_'):
            continue
        if sym_name in sym_exclude_list:
            continue

        if isinstance(sym, type):
            classes.append(sym_name)
        elif isinstance(sym, types.FunctionType):
            functions.append(sym_name)
        else:
            datas.append(sym_name)

    print("=== Classes ===")
    for name in classes:
        print(name)

    print("=== Functions ===")
    for name in functions:
        print(name)

    print("=== Data items ===")
    for name in datas:
        print(name)

    return 0


if __name__ == '__main__':
    sys.exit(main())
