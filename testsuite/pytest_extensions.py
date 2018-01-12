"""
Extensions for pytest module.
"""

from __future__ import absolute_import

import pytest
from decorator import decorator


@decorator
def test_function(test_func, desc, kwargs, exp_exc_types, exp_warn_types,
                  condition):
    """
    A decorator for test functions that calls the test function and handles:

    * Skipping the test if the condition is False,

    * Invoking the Python debugger if condition == "pdb",

    * Capturing and validating any warnings issued by the test function,
      if exp_warn_types is set,

    * Catching and validating any exceptions raised by the test function,
      if exp_exc_types is set,

    Parameters:

    * test_func (function): The decorated function.

    * desc (string): A short testcase description.

    * kwargs (dict): Testcase-specific input parameters.

    * exp_exc_types (Exception or list of Exception): Expected exception types.

    * exp_warn_types (Warning or list of Warning): Expected warning types.

    * condition (bool or 'pdb'): Boolean condition for running the testcase.
      If it evaluates to `bool(False)`, the testcase will be skipped.
      If it evaluates to `bool(True)`, the testcase will be run.
      String value 'pdb' will cause the testcase to run under the Python
      debugger.

    Notes:

    * This is a parameter-preserving decorator: The decorated function has
      the same parameters as the original function.

    * Using the decorator together with the `pytest.mark.parametrize`
      decorator requires applying this decorator first to the test function
      (see the example).

    Example::

        testcases_CIMClass_equal = [
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
            testcases_CIMClass_equal)
        @pytest_extensions.test_function
        def test_CIMClass_equal(
                desc, kwargs, exp_exc_types, exp_warn_types, condition):

            obj1 = kwargs['obj1']
            obj2 = kwargs['obj2']

            # The code to be tested
            equal = (obj1 == obj2)

            exp_equal = kwargs['exp_equal']
            assert equal == exp_equal
        )
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
            else:
                if condition == 'pdb':
                    pdb.set_trace()

                test_func(*args)  # not expecting an exception

                ret = None  # Debugging hint
        assert len(rec_warnings) == 1
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
