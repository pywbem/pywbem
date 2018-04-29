"""
Extensions for pytest module.
"""

from __future__ import absolute_import

import pytest
from decorator import decorator


__all__ = ['test_function']


@decorator
def test_function(test_func, desc, kwargs, exp_exc_types, exp_warn_types,
                  condition):
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

    This is a signature-preserving decorator: The wrapper function has the
    same signature as the test function that is decorated.

    Parameters of the outer and inner function:

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

    Notes:

    * Using the decorator together with the `pytest.mark.parametrize`
      decorator requires applying this decorator first to the test function
      (see the example).

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
        @pytest_extensions.test_function
        def test_CIMClass_equal(
                desc, kwargs, exp_exc_types, exp_warn_types, condition):
            # pylint: disable=unused-argument

            obj1 = kwargs['obj1']
            obj2 = kwargs['obj2']
            exp_equal = kwargs['exp_equal']

            # The code to be tested
            equal = (obj1 == obj2)

            # Verify that an exception raised in this function is not mistaken
            # to be the expected exception
            assert exp_exc_types is None

            # Verify the result
            assert equal == exp_equal
    """

    if not condition:
        pytest.skip("Condition for test case not met")

    if condition == 'pdb':
        import pdb

    args = (desc, kwargs, exp_exc_types, exp_warn_types, condition)

    if exp_warn_types:
        with pytest.warns(exp_warn_types) as rec_warnings:
            if exp_exc_types:
                with pytest.raises(exp_exc_types):
                    if condition == 'pdb':
                        pdb.set_trace()

                    test_func(*args)  # expecting an exception

                ret = None  # Debugging hint
                # In combination with exceptions, we do not verify warnings
                # (they could have been issued before or after the exception).
            else:
                if condition == 'pdb':
                    pdb.set_trace()

                test_func(*args)  # not expecting an exception

                ret = None  # Debugging hint
                assert len(rec_warnings) >= 1
    else:
        if exp_exc_types:
            with pytest.raises(exp_exc_types):
                if condition == 'pdb':
                    pdb.set_trace()

                test_func(*args)  # expecting an exception

            ret = None  # Debugging hint
        else:
            if condition == 'pdb':
                pdb.set_trace()

            test_func(*args)  # not expecting an exception

            ret = None  # Debugging hint
    return ret
