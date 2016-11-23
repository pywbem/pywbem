#!/usr/bin/env python
"""
    Test compatibility when changing *args and **kwargs to named args.
"""

import sys


def func_old_args(a, b=None, *args):  # pylint: disable=invalid-name
    """Old function, defined with *args."""

    # We extract a specific optional parameter from *args
    try:
        c = args[0]
    except IndexError:
        c = None

    return a, b, c


def func_old_kwargs(a, b=None, **kwargs):  # pylint: disable=invalid-name
    """Old function, defined with **kwargs."""

    # We extract a specific optional parameter from **kwargs
    try:
        c = kwargs['c']
    except KeyError:
        c = None

    return a, b, c


def func_new(a, b=None, c=None):  # pylint: disable=invalid-name
    """New function, replacing any of the old functions."""

    return a, b, c


def test_func_args(func_args):
    """Examine all possible ways to invoke a function defined with *args."""

    a, b, c = func_args(1)
    assert (a, b, c) == (1, None, None)

    a, b, c = func_args(1, 2)
    assert (a, b, c) == (1, 2, None)

    a, b, c = func_args(1, 2, 3)
    assert (a, b, c) == (1, 2, 3)

    lis = [3, ]
    a, b, c = func_args(1, 2, *lis)
    assert (a, b, c) == (1, 2, 3)

    # The list can even be used for the named args:

    lis = [2, 3]
    a, b, c = func_args(1, *lis)
    assert (a, b, c) == (1, 2, 3)

    lis = [1, 2, 3]
    a, b, c = func_args(*lis)
    assert (a, b, c) == (1, 2, 3)


def test_func_kwargs(func_kwargs):
    """Examine all possible ways to invoke a function defined with **kwargs."""

    a, b, c = func_kwargs(1)
    assert (a, b, c) == (1, None, None)

    a, b, c = func_kwargs(1, 2)
    assert (a, b, c) == (1, 2, None)

    a, b, c = func_kwargs(1, 2, c=3)
    assert (a, b, c) == (1, 2, 3)

    dic = dict(c=3)
    a, b, c = func_kwargs(1, 2, **dic)
    assert (a, b, c) == (1, 2, 3)

    # The dict can even be used for the named args:

    dic = dict(b=2, c=3)
    a, b, c = func_kwargs(1, **dic)
    assert (a, b, c) == (1, 2, 3)

    dic = dict(a=1, b=2, c=3)
    a, b, c = func_kwargs(**dic)
    assert (a, b, c) == (1, 2, 3)


def main():
    """Main function calls the test functs"""

    print("Python version %s" % sys.version)

    print("Testing compatibility for function defined with *args")
    test_func_args(func_old_args)
    test_func_args(func_new)

    print("Testing compatibility for function defined with **kwargs")
    test_func_kwargs(func_old_kwargs)
    test_func_kwargs(func_new)

    print("All tests successful - we can change *args and **kwargs to' \
          ' named args.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
