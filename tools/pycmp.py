#!/usr/bin/env python
#
# Author: Andreas Maier
#
# Tool that compares the symbols in the external API of two versions of a
# Python package.
# Invoke with --help for usage.

import sys
import argparse
import os
import fnmatch
import importlib
import re
import types
from pprint import pprint

ARGS = None
MYNAME=sys.argv[0]

def main():
    global ARGS

    parser = argparse.ArgumentParser(
        prog=MYNAME,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        usage=f"{MYNAME} [-h|--help] [options] olddir newdir",
        description=
"""
Compare the symbols in the external API of two versions of a Python package,
and print a report to stdout.

Package directories can be specified with relative or absolute path, and must
specify the package directory (inside of which there is the __init__.py file
for the package).
""",
        epilog=
f"""
example:
  {MYNAME} ../v1.0/foo foo
    Compare the foo package version in ../v1.0/foo with the version in ./foo.
""")

    parser.add_argument("olddir", type=str,
                        help="path name of old package directory")
    parser.add_argument("newdir", type=str,
                        help="path name of new package directory")
    parser.add_argument("-f", "--full", dest='full', action='store_true',
                        help="list symbols of added or removed modules")
    parser.add_argument("-d", "--debug", dest='debug', action='store_true',
                        help="debug mode")
    parser.set_defaults(debug=False)
    parser.add_argument("-o", "--others", dest='others', action='store_true',
                        help="report symbol changes also when imported from other packages")
    parser.set_defaults(others=False)
    parser.add_argument("-i", "--imported", dest='imported', action='store_true',
                        help="report symbol changes also when imported from other modules of this package")
    parser.set_defaults(imported=False)
    parser.add_argument("-e", "--exported", dest='exported', action='store_true',
                        help="report symbol changes also for exported symbols (in __all__)")
    parser.set_defaults(exported=False)
    ARGS = parser.parse_args()

    rc = compare_package_dirs(ARGS.olddir, ARGS.newdir)
    return rc

def compare_package_dirs(old_pkgdir, new_pkgdir):

    old_pkgname = abs_modulename(old_pkgdir, old_pkgdir)
    new_pkgname = abs_modulename(new_pkgdir, new_pkgdir)
    if old_pkgname != new_pkgname:
        print(f"Error: Package names are not the same: {old_pkgname} / {new_pkgname}")
        return 1
    pkgname = old_pkgname

    print(f"Comparing public symbols of Python package: {pkgname}")
    print(f"    Old package directory: {old_pkgdir}")
    print(f"    New package directory: {new_pkgdir}")
    print("")
    print("This report covers the following kinds of symbols:")
    print(f"    Non-public symbols:                                                      {False}")
    print(f"    Symbols of added or removed modules (-f option):                         {bool(ARGS.full)}")
    print(f"    Symbols imported from other packages (-o option):                        {bool(ARGS.others)}")
    print(f"    Symbols imported from other modules of this package (-i option):         {bool(ARGS.imported)}")
    print(f"    Symbols exported from this package (in __all__) (-e option):             {bool(ARGS.exported)}")

    if ARGS.debug:
        print("Debug: Gathering information about modules in old package")
    old_modinfos = get_modinfos(old_pkgdir)
    if ARGS.debug:
        print("Debug: Gathering information about modules in new package")
    new_modinfos = get_modinfos(new_pkgdir)

    old_modnames = old_modinfos.keys()
    new_modnames = new_modinfos.keys()

    #print("Debug: Old module infos:")
    #pprint(old_modinfos)
    #print("Debug: New module infos:")
    #pprint(new_modinfos)

    added_modnames = set(new_modnames) - set(old_modnames)
    removed_modnames = set(old_modnames) - set(new_modnames)
    same_modnames = set(new_modnames).intersection(set(old_modnames))

    print("\nModule changes:")

    for mn in sorted(added_modnames):
        print(f"    Added module: {mn}")
        if ARGS.full:
            modinfo = new_modinfos[mn]
            syminfos = modinfo['syminfos']
            for sn in sorted(syminfos):
                si = syminfos[sn]
                print(f"        Symbol: {si['name']} ({si['typename']}, {si['modname']})")

    for mn in sorted(removed_modnames):
        print(f"    Removed module: {mn}")
        if ARGS.full:
            modinfo = old_modinfos[mn]
            syminfos = modinfo['syminfos']
            for sn in sorted(syminfos):
                si = syminfos[sn]
                print(f"        Symbol: {si['name']} ({si['typename']}, {si['modname']})")

    for mn in sorted(same_modnames):
        compare_modules(old_modinfos[mn], new_modinfos[mn], pkgname)

    return 0

def compare_modules(old_modinfo, new_modinfo, pkgname):

    mod_name = old_modinfo['name']

    old_syminfos = {}
    for sym in old_modinfo['syminfos']:
        si = old_modinfo['syminfos'][sym]
        sym_modname = si['modname']
        sym_pkgname = None if sym_modname is None else sym_modname.split('.')[0]
        exclude_reason = None
        if exclude(si):
            exclude_reason = EXCLUDE_REASON
        elif sym_pkgname is not None and sym_pkgname != pkgname and not ARGS.others:
            # None means unknown package origin, so we are not sure and don't exclude it
            exclude_reason = f"imported from other package {sym_pkgname}"
        elif sym_modname is not None and sym_modname != mod_name and not ARGS.imported:
            # None means unknown package origin, so we are not sure and don't exclude it
            exclude_reason = f"imported from other module {sym_modname} of this package"
        if not exclude_reason:
            old_syminfos[sym] = si
        else:
            if ARGS.debug:
                print(f"Debug: Excluding symbol {sym} defined in old module "
                      f"{mod_name} because: {exclude_reason}")

    new_syminfos = {}
    for sym in new_modinfo['syminfos']:
        si = new_modinfo['syminfos'][sym]
        sym_modname = si['modname']
        sym_pkgname = None if sym_modname is None else sym_modname.split('.')[0]
        exclude_reason = None
        if exclude(si):
            exclude_reason = EXCLUDE_REASON
        elif sym_pkgname is not None and sym_pkgname != pkgname and not ARGS.others:
            # None means unknown package origin, so we are not sure and don't exclude it
            exclude_reason = f"imported from other package {sym_pkgname}"
        elif sym_modname is not None and sym_modname != mod_name and not ARGS.imported:
            # None means unknown package origin, so we are not sure and don't exclude it
            exclude_reason = f"imported from other module {sym_modname} of this package"
        if not exclude_reason:
            new_syminfos[sym] = si
        else:
            if ARGS.debug:
                print(f"Debug: Excluding symbol {sym} defined in new module "
                      f"{mod_name} because: {exclude_reason}")

    added_symbols = set(new_syminfos.keys()) - set(old_syminfos.keys())
    removed_symbols = set(old_syminfos.keys()) - set(new_syminfos.keys())

    old_exp_syminfos = {}
    for sym in old_syminfos:
        if old_syminfos[sym]['exported']:
            old_exp_syminfos[sym] = old_syminfos[sym]

    new_exp_syminfos = {}
    for sym in new_syminfos:
        if new_syminfos[sym]['exported']:
            new_exp_syminfos[sym] = new_syminfos[sym]

    added_exp_symbols = set(new_exp_syminfos.keys()) - set(old_exp_syminfos.keys())
    removed_exp_symbols = set(old_exp_syminfos.keys()) - set(new_exp_syminfos.keys())

    have_report = len(added_symbols) + len(removed_symbols) > 0
    if ARGS.exported and not have_report:
        have_report = len(added_exp_symbols) + len(removed_exp_symbols) > 0
    if have_report:
        print(f"\nDifferences for module: {mod_name}")

    def where(sym_modname, our_modname):
        if sym_modname == our_modname:
            return 'defined here'
        if sym_modname is None:
            return 'unknown origin'
        return f"imported from {sym_modname}"

    for sym in sorted(added_symbols):
        si = new_syminfos[sym]
        print(f"    Added   symbol: {sym:30} ({si['typename']}, "
              f"{where(si['modname'], mod_name)})")

    for sym in sorted(removed_symbols):
        si = old_syminfos[sym]
        print(f"    Removed symbol: {sym:30} ({si['typename']}, "
              f"{where(si['modname'], mod_name)})")

    if ARGS.exported:
        for sym in sorted(added_exp_symbols):
            si = new_syminfos[sym]
            print(f"    Added   exported symbol: {sym:30} ({si['typename']}, "
                  f"{where(si['modname'], mod_name)})")

        for sym in sorted(removed_exp_symbols):
            si = old_syminfos[sym]
            print(f"    Removed exported symbol: {sym:30} ({si['typename']}, "
                  f"{where(si['modname'], mod_name)})")

EXCLUDE_REASON = "non-public symbol"
def exclude(syminfo):

    sym = syminfo['name']
    if re.match(r'^__.+__$', sym): # special symbols
        return False
    if re.match(r'^__?.*', sym): # non-public symbols
        return True
    return False

def get_modinfos(pkgdir):

    mod_files = rglob(pkgdir, "*.py")
    pkgpath = os.path.abspath(pkgdir)
    pkgparentpath = os.path.dirname(pkgpath)

    pkgname = abs_modulename(pkgdir, pkgdir)
    unload_modules(pkgname)

    if pkgpath not in sys.path:
        if ARGS.debug:
            print(f"Debug: Inserting package dir into module search path: {pkgpath}")
        sys.path.insert(0, pkgpath)
    else:
        if ARGS.debug:
            print(f"Debug: Package dir is already in module search path: {pkgpath}")
        pass
    if pkgparentpath not in sys.path:
        if ARGS.debug:
            print(f"Debug: Inserting parent package dir into module search path: {pkgparentpath}")
        sys.path.insert(0, pkgparentpath)
    else:
        if ARGS.debug:
            print(f"Debug: Parent package dir is already in module search path: {pkgparentpath}")
        pass

    use_exec = True

    modinfos = {}

    for mod_file in mod_files:

        if ARGS.debug:
            print(f"Debug: Processing file: {mod_file}")

        rel_modname = rel_modulename(mod_file, pkgdir)
        abs_modname = abs_modulename(mod_file, pkgdir)

        if use_exec:

            module_import(abs_modname)
            mod_obj = sys.modules[abs_modname]
            mi = get_modinfos_from_mod_obj(mod_obj, abs_modname, mod_file)
            #if ARGS.debug:
            #    print("Debug: Got module infos:")
            #    pprint(mi)
            modinfos.update(mi)

            ## Not needed, because the normal import already determines
            ## wildcard information.
            #wc_sym_dict = wildcard_import(abs_modname)
            #if ARGS.debug:
            #    print(f"Debug: Got symbols: {sorted(wc_sym_dict.keys())!r}")
            #wc_mi = get_modinfos_from_sym_dict(wc_sym_dict, abs_modname, mod_file)
            #if ARGS.debug:
            #    print("Debug: Got module infos:")
            #    pprint(wc_mi)
            #modinfos.update(wc_mi)

        else:
            try:
                if rel_modname == '.':
                    if ARGS.debug:
                        print(f"Debug: Importing absolute module {abs_modname}" )
                    mod_obj = importlib.import_module(abs_modname)
                else:
                    if ARGS.debug:
                        print(f"Debug: Importing relative module {rel_modname} within package {pkgname}")
                    mod_obj = importlib.import_module(rel_modname, pkgname)
            except ImportError as exc:
                if ARGS.debug:
                    print(f"Debug: Import failed (retrying): {exc}")
                try:
                    if ARGS.debug:
                        print(f"Debug: Importing absolute module {abs_modname}")
                    mod_obj = importlib.import_module(abs_modname)
                except ImportError as exc:
                    print(f"Error: Import failed (aborting): {exc}")
                    print("Loaded modules in package namespace:")
                    pprint([mod for mod in sorted(sys.modules.keys())
                            if mod == pkgname or mod.startswith(pkgname+'.')
                           ])
                    print("Module search path:")
                    pprint(sys.path)
                    raise

            assert abs_modname in sys.modules, \
                f"module {abs_modname} is not in sys.modules after import"

            modinfos = get_modinfos_from_mod_obj(mod_obj, abs_modname, mod_file)

            del mod_obj # unload by garbage collection
            #del sys.modules[abs_modname] # this goes too far, probably

    if ARGS.debug:
        print(f"Debug: Removing package dir from module search path: {pkgpath}")
    sys.path.remove(pkgpath)
    if ARGS.debug:
        print(f"Debug: Removing parent package dir from module search path: {pkgparentpath}")
    sys.path.remove(pkgparentpath)

    return modinfos

def get_modinfos_from_mod_obj(mod_obj, abs_modname, mod_file):
    if not isinstance(mod_obj, types.ModuleType):
        raise TypeError("mod_obj parameter must be a module object.")
    sym_dict = mod_obj.__dict__
    return get_modinfos_from_sym_dict(sym_dict, abs_modname, mod_file)

def get_modinfos_from_sym_dict(sym_dict, abs_modname, mod_file):

    if not isinstance(sym_dict, dict):
        raise TypeError("sym_dict parameter must be a dict object.")

    all_symbols = sym_dict.keys()
    exp_symbols = sym_dict.get('__all__', all_symbols)

    unexpected_symbols = set(exp_symbols) - set(all_symbols)
    assert len(unexpected_symbols) == 0, \
        f"module %s has unexpected exported symbols: {sorted(unexpected_symbols)!r}"

    modinfos = {}
    mi = {}
    mi['name'] = abs_modname
    mi['file'] = mod_file
    syminfos = {}
    for sym in all_symbols:
        si = {}
        si['name'] = sym
        sym_obj = sym_dict[sym]
        if isinstance(sym_obj, types.ClassType):
            tn = 'old-style class'
        elif not hasattr(sym_obj, '__module__'):
            # e.g. tuple
            tn = type(sym_obj).__name__
        elif sym_obj.__module__ == '__builtin__':
            tn = type(sym_obj).__name__
        elif isinstance(sym_obj, types.TypeType):
            tn = 'new-style class'
        else:
            tn = type(sym_obj).__name__
        si['typename'] = tn
        si['modname'] = getattr(sym_obj, '__module__', None)
        si['exported'] = bool(sym in exp_symbols)
        syminfos[sym] = si
    mi['syminfos'] = syminfos
    modinfos[abs_modname] = mi

    return modinfos

def module_import(_wci_modname):
    _wci_stmt = f'import {_wci_modname}'
    if ARGS.debug:
        print(f"Debug: Importing module: {_wci_modname}")
    exec(_wci_stmt)
    imported = locals()
    del imported['_wci_modname']
    del imported['_wci_stmt']
    return imported

def wildcard_import(_wci_modname):
    _wci_stmt = f'from {_wci_modname} import *'
    if ARGS.debug:
        print(f"Debug: Importing * from module: {_wci_modname}")
    exec(_wci_stmt)
    imported = locals()
    del imported['_wci_modname']
    del imported['_wci_stmt']
    return imported

def unload_modules(pkgname):
    removals = []
    for modname in sys.modules:
        if modname == pkgname or modname.startswith(pkgname+'.'):
            removals.append(modname)
    for modname in removals:
        if ARGS.debug:
            print(f"Debug: Removing module from loaded modules: {modname}")
        del sys.modules[modname]

def abs_modulename(mod_file, pkgdir):
    mod_name = os.path.splitext(os.path.relpath(mod_file, os.path.dirname(pkgdir)))[0].replace(os.sep, '.')
    mod_name_parts = mod_name.split('.')
    if mod_name_parts[-1] == '__init__':
        mod_name = '.'.join(mod_name_parts[0:-1])
    return mod_name

def rel_modulename(mod_file, pkgdir):
    mod_name = os.path.splitext(os.path.relpath(mod_file, pkgdir))[0].replace(os.sep, '.')
    mod_name_parts = mod_name.split('.')
    if mod_name_parts[-1] == '__init__':
        mod_name = '.'.join(mod_name_parts[0:-1])
    mod_name = '.' + mod_name
    return mod_name

def rglob(path='.', pattern='*'):
    matches = []
    for root, dirnames, filenames in os.walk(path):
        for filename in fnmatch.filter(filenames, pattern):
            matches.append(os.path.join(root, filename))
    return matches

if __name__ == '__main__':
    sys.exit(main())
