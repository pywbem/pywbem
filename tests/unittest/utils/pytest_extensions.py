"""
Extensions for pytest module.
"""

from __future__ import absolute_import

import functools
import warnings
from collections import namedtuple
try:
    from inspect import Signature, Parameter
except ImportError:  # py2
    from funcsigs import Signature, Parameter
import pytest

__all__ = ['simplified_test_function', 'ignore_warnings', 'expect_warnings']


# Pytest determines the signature of the test function by unpacking any
# wrapped functions (this is the default of the signature() function it
# uses. We correct this behavior by setting the __signature__ attribute of
# the wrapper function to its correct signature. To do that, we cannot use
# signature() because its follow_wrapped parameter was introduced only in
# Python 3.5. Instead, we build the signature manually.
TESTFUNC_SIGNATURE = Signature(
    parameters=[
        Parameter('desc', Parameter.POSITIONAL_OR_KEYWORD),
        Parameter('kwargs', Parameter.POSITIONAL_OR_KEYWORD),
        Parameter('exp_exc_types', Parameter.POSITIONAL_OR_KEYWORD),
        Parameter('exp_warn_types', Parameter.POSITIONAL_OR_KEYWORD),
        Parameter('condition', Parameter.POSITIONAL_OR_KEYWORD),
    ]
)


def simplified_test_function(test_func):
    """
    A decorator for test functions that simplifies the test function by
    handling a number of things:

    * Skipping the test if the `condition` item in the testcase is `False`,
    * Invoking the Python debugger if the `condition` item in the testcase is
      the string "pdb",
    * Capturing and validating any warnings issued by the test function,
      if the `exp_warn_types` item in the testcase is set,
    * Catching and validating any exceptions raised by the test function,
      if the `exp_exc_types` item in the testcase is set.

    This is a signature-changing decorator. This decorator must be inserted
    after the `pytest.mark.parametrize` decorator so that it is applied
    first (see the example).

    Parameters of the wrapper function returned by this decorator:

    * desc (string): Short testcase description.

    * kwargs (dict): Keyword arguments for the test function.

    * exp_exc_types (Exception or list of Exception): Expected exception types,
      or `None` if no exceptions are expected.

    * exp_warn_types (Warning or list of Warning): Expected warning types,
      or `None` if no warnings are expected.

    * condition (bool or 'pdb'): Boolean condition for running the testcase.
      If it evaluates to `bool(False)`, the testcase will be skipped.
      If it evaluates to `bool(True)`, the testcase will be run.
      The string value 'pdb' will cause the Python pdb debugger to be entered
      before calling the test function.

    Parameters of the test function that is decorated:

    * testcase (testcase_tuple): The testcase, as a named tuple.

    * **kwargs: Keyword arguments for the test function.

    Example::

        TESTCASES_CIMCLASS_EQUAL = [
            # desc, kwargs, exp_exc_types, exp_warn_types, condition
            (
                "Equality with different lexical case of name",
                dict(
                    obj1=CIMClass('CIM_Foo'),
                    obj2=CIMClass('cim_foo'),
                    exp_equal=True,
                ),
                None, None, True
            ),
            # ... more testcases
        ]

        @pytest.mark.parametrize(
            "desc, kwargs, exp_exc_types, exp_warn_types, condition",
            TESTCASES_CIMCLASS_EQUAL)
        @pytest_extensions.simplified_test_function
        def test_CIMClass_equal(testcase, obj1, obj2, exp_equal):

            # The code to be tested
            equal = (obj1 == obj2)

            # Ensure that exceptions raised in the remainder of this function
            # are not mistaken as expected exceptions
            assert testcase.exp_exc_types is None

            # Verify the result
            assert equal == exp_equal
    """

    # A testcase tuple
    testcase_tuple = namedtuple(
        'testcase_tuple',
        ['desc', 'kwargs', 'exp_exc_types', 'exp_warn_types', 'condition']
    )

    def wrapper_func(desc, kwargs, exp_exc_types, exp_warn_types, condition):
        """
        Wrapper function that calls the test function that is decorated.
        """

        if not condition:
            pytest.skip("Condition for test case not met")

        if condition == 'pdb':
            # pylint: disable=import-outside-toplevel
            import pdb

        testcase = testcase_tuple(desc, kwargs, exp_exc_types, exp_warn_types,
                                  condition)

        if exp_warn_types:
            with pytest.warns(exp_warn_types) as rec_warnings:
                if exp_exc_types:
                    with pytest.raises(exp_exc_types):
                        if condition == 'pdb':
                            # pylint: disable=forgotten-debug-statement
                            pdb.set_trace()

                        test_func(testcase, **kwargs)  # expecting an exception

                    ret = None  # Debugging hint
                    # In combination with exceptions, we do not verify warnings
                    # (they could have been issued before or after the
                    # exception).
                else:
                    if condition == 'pdb':
                        # pylint: disable=forgotten-debug-statement
                        pdb.set_trace()

                    test_func(testcase, **kwargs)  # not expecting an exception

                    ret = None  # Debugging hint
                    assert len(rec_warnings) >= 1, \
                        "Expected warning(s) missing: {}".format(exp_warn_types)
        else:
            with pytest.warns(None) as rec_warnings:
                if exp_exc_types:
                    with pytest.raises(exp_exc_types):
                        if condition == 'pdb':
                            # pylint: disable=forgotten-debug-statement
                            pdb.set_trace()

                        test_func(testcase, **kwargs)  # expecting an exception

                    ret = None  # Debugging hint
                else:
                    if condition == 'pdb':
                        # pylint: disable=forgotten-debug-statement
                        pdb.set_trace()

                    test_func(testcase, **kwargs)  # not expecting an exception

                    ret = None  # Debugging hint

                    # Verify that no warnings have occurred
                    if exp_warn_types is None and rec_warnings:
                        lines = []
                        for w in rec_warnings.list:
                            tup = (w.filename, w.lineno, w.category.__name__,
                                   str(w.message))
                            line = "{t[0]}:{t[1]}: {t[2]}: {t[3]}".format(t=tup)
                            if line not in lines:
                                lines.append(line)
                        msg = "Unexpected warnings:\n{}".format(
                            '\n'.join(lines))
                        raise AssertionError(msg)
        return ret

    # Needed because the decorator is signature-changin
    wrapper_func.__signature__ = TESTFUNC_SIGNATURE

    return functools.update_wrapper(wrapper_func, test_func)


class ignore_warnings(warnings.catch_warnings):
    # pylint: disable=invalid-name,too-few-public-methods
    """
    Context manager that ignores the specified warning categories in its body.

    The current warnings filters are saved upon entry and restored upon exit
    of the context manager.
    """

    def __init__(self, categories=None):
        """
        Parameters:

            categories:
                The warning class(es) that are to be ignored.
                Must be a single class, a list/tuple of classes, or None.
                The classes must be subclasses of Warning.
        """
        super(ignore_warnings, self).__init__()
        if categories is None:
            categories = []
        elif not isinstance(categories, (list, tuple)):
            categories = [categories]
        for category in categories:
            assert issubclass(category, Warning)
        self.categories = categories

    def __enter__(self):
        ret = super(ignore_warnings, self).__enter__()  # saves current filters
        for category in self.categories:
            warnings.simplefilter('ignore', category=category)
        return ret


def expect_warnings(testcase, warnings):
    # pylint: disable=redefined-outer-name
    """
    Return whether a particular warning or one or more from a list of warnings
    is expected in the testcase.
    """
    if testcase.exp_warn_types is None:
        return False
    exp_warnings = testcase.exp_warn_types
    if not isinstance(exp_warnings, (tuple, list)):
        exp_warnings = [exp_warnings]
    if not isinstance(warnings, (tuple, list)):
        warnings = [warnings]
    return any(w in warnings for w in exp_warnings)
