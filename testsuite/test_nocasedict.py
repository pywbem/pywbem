#!/usr/bin/env python
"""
    Test case-insensitive dictionary implementation.
"""

from __future__ import absolute_import

import unittest
import warnings
import six

from pywbem.cim_obj import NocaseDict


class TestInit(unittest.TestCase):
    """Test initialization"""
    def test_all(self):
        """Test all init options"""
        # Empty

        dic = NocaseDict()
        self.assertTrue(len(dic) == 0)

        dic = NocaseDict(None)
        self.assertTrue(len(dic) == 0)

        dic = NocaseDict(list())
        self.assertTrue(len(dic) == 0)

        dic = NocaseDict(tuple())
        self.assertTrue(len(dic) == 0)

        dic = NocaseDict(dict())
        self.assertTrue(len(dic) == 0)

        dic = NocaseDict(dic)
        self.assertTrue(len(dic) == 0)

        # Initialise from iterable

        dic = NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')])
        self.assertTrue(len(dic) == 2)
        self.assertTrue(dic['Dog'] == 'Cat' and dic['Budgie'] == 'Fish')

        dic = NocaseDict((('Dog', 'Cat'), ('Budgie', 'Fish')))
        self.assertTrue(len(dic) == 2)
        self.assertTrue(dic['Dog'] == 'Cat' and dic['Budgie'] == 'Fish')

        # Initialise from dictionary

        dic = NocaseDict({'Dog': 'Cat', 'Budgie': 'Fish'})
        self.assertTrue(len(dic) == 2)
        self.assertTrue(dic['Dog'] == 'Cat' and dic['Budgie'] == 'Fish')

        # Initialise from kwargs

        dic = NocaseDict(Dog='Cat', Budgie='Fish')
        self.assertTrue(len(dic) == 2)
        self.assertTrue(dic['Dog'] == 'Cat' and dic['Budgie'] == 'Fish')

        # Initialise from iterable and kwargs

        dic = NocaseDict([('Dog', 'Cat'), ], Budgie='Fish')
        self.assertTrue(len(dic) == 2)
        self.assertTrue(dic['Dog'] == 'Cat' and dic['Budgie'] == 'Fish')

        dic = NocaseDict((('Dog', 'Cat'),), Budgie='Fish')
        self.assertTrue(len(dic) == 2)
        self.assertTrue(dic['Dog'] == 'Cat' and dic['Budgie'] == 'Fish')

        # Initialise from dictionary and kwargs

        dic = NocaseDict({'Dog': 'Cat'}, Budgie='Fish')
        self.assertTrue(len(dic) == 2)
        self.assertTrue(dic['Dog'] == 'Cat' and dic['Budgie'] == 'Fish')

        # Initialise from unsupported object type

        try:
            dic = NocaseDict('illegal')
        except TypeError:
            pass
        else:
            self.fail("TypeError was unexpectedly not thrown.")

        # Initialise with too many positional arguments

        try:
            dic = NocaseDict(list(), list())
        except TypeError:
            pass
        else:
            self.fail("TypeError was unexpectedly not thrown.")


class BaseTest(unittest.TestCase):
    """Base class for following unit test. Does common setup which
       creates a NoCaseDict.
    """
    def setUp(self):
        """unittest setUp creates NoCaseDict"""
        self.dic = NocaseDict()
        self.dic['Dog'] = 'Cat'
        self.dic['Budgie'] = 'Fish'


class TestGetitem(BaseTest):
    """Tests for getitem"""
    def test_all(self):
        """All tests"""
        self.assertTrue(self.dic['dog'] == 'Cat')
        self.assertTrue(self.dic['DOG'] == 'Cat')

        try:
            self.dic['notfound']
        except KeyError:
            pass
        else:
            self.fail("KeyError was unexpectedly not thrown.")


class TestLen(BaseTest):
    """Tests for len of dict"""
    def test_all(self):
        """Test method"""
        self.assertTrue(len(self.dic) == 2)


class TestSetitem(BaseTest):
    """Test setting items"""
    def test_all(self):
        """All setitem tests"""
        self.dic['DOG'] = 'Kitten'
        self.assertTrue(self.dic['DOG'] == 'Kitten')
        self.assertTrue(self.dic['Dog'] == 'Kitten')
        self.assertTrue(self.dic['dog'] == 'Kitten')

        # Check that using a non-string key raises an exception

        try:
            self.dic[1234] = '1234'
        except TypeError:
            pass
        else:
            self.fail('TypeError expected')


class TestDelitem(BaseTest):
    """Class for del items from dictionary"""
    def test_all(self):
        """All tests"""
        del self.dic['DOG']
        del self.dic['budgie']
        self.assertTrue(self.dic.keys() == [])

        try:
            del self.dic['notfound']
        except KeyError:
            pass
        else:
            self.fail("KeyError was unexpectedly not thrown.")


class TestHasKey(BaseTest):
    """Class to test haskey on dict"""
    def test_all(self):
        """Method to test haskey"""
        self.assertTrue('DOG' in self.dic)
        self.assertTrue('budgie' in self.dic)
        self.assertTrue(1234 not in self.dic)


class TestKeys(BaseTest):
    """Class for TestKeys method"""
    def test_all(self):
        """All tests in single method"""
        keys = self.dic.keys()
        animals = ['Budgie', 'Dog']
        for ani in animals:
            self.assertTrue(ani in keys)
            keys.remove(ani)
        self.assertTrue(keys == [])


class TestValues(BaseTest):
    """Class for values tests"""
    def test_all(self):
        """Test all for TestValues"""
        values = self.dic.values()
        animals = ['Cat', 'Fish']
        for ani in animals:
            self.assertTrue(ani in values)
            values.remove(ani)
        self.assertTrue(values == [])


class TestItems(BaseTest):
    """Class for Test items"""
    def test_all(self):
        """All tests for item"""
        items = self.dic.items()
        animals = [('Dog', 'Cat'), ('Budgie', 'Fish')]
        for ani in animals:
            self.assertTrue(ani in items)
            items.remove(ani)
        self.assertTrue(items == [])


class TestClear(BaseTest):
    """Class for dict clear method"""
    def test_all(self):
        """All clear method tests"""
        self.dic.clear()
        self.assertTrue(len(self.dic) == 0)


class TestUpdate(BaseTest):
    """Class for test update method"""
    def test_all(self):
        """All methods for TestUpdate"""
        self.dic.clear()
        self.dic.update({'Chicken': 'Ham'})
        self.assertTrue(self.dic.keys() == ['Chicken'])
        self.assertTrue(self.dic.values() == ['Ham'])
        self.dic.clear()
        self.dic.update({'Chicken': 'Ham'}, {'Dog': 'Cat'})
        keys = self.dic.keys()
        vals = self.dic.values()
        keys = list(keys)
        vals = list(vals)
        keys.sort()
        vals.sort()
        self.assertTrue(keys == ['Chicken', 'Dog'])
        self.assertTrue(vals == ['Cat', 'Ham'])
        self.dic.update([('Chicken', 'Egg')], {'Fish': 'Eel'})
        self.assertTrue(self.dic['chicken'] == 'Egg')
        self.assertTrue(self.dic['fish'] == 'Eel')
        self.dic.update({'Fish': 'Salmon'}, Cow='Beef')
        self.assertTrue(self.dic['fish'] == 'Salmon')
        self.assertTrue(self.dic['Cow'] == 'Beef')
        self.assertTrue(self.dic['COW'] == 'Beef')
        self.assertTrue(self.dic['cow'] == 'Beef')


class TestCopy(BaseTest):
    """Class to test dict copy"""
    def test_all(self):
        """All tests for dict copy"""
        cp = self.dic.copy()
        self.assertEqual(cp, self.dic)
        self.assertTrue(isinstance(cp, NocaseDict))
        cp['Dog'] = 'Kitten'
        self.assertTrue(self.dic['Dog'] == 'Cat')
        self.assertTrue(cp['Dog'] == 'Kitten')


class TestGet(BaseTest):
    """Class to test get method"""
    def test_all(self):
        """Test get method"""
        self.assertTrue(self.dic.get('Dog', 'Chicken') == 'Cat')
        self.assertTrue(self.dic.get('Ningaui') is None)
        self.assertTrue(self.dic.get('Ningaui', 'Chicken') == 'Chicken')


class TestSetDefault(BaseTest):
    """Class for setdefault test methods"""
    def test_all(self):
        """All tests for setdefault of dict"""
        self.dic.setdefault('Dog', 'Kitten')
        self.assertTrue(self.dic['Dog'] == 'Cat')
        self.dic.setdefault('Ningaui', 'Chicken')
        self.assertTrue(self.dic['Ningaui'] == 'Chicken')


class TestPopItem(BaseTest):
    """Class for PopItem"""
    def test_all(self):
        """This test does nothing"""
        pass


# TODO: swapcase2() is also defined in test_cim_obj.py. Consolidate.
def swapcase2(text):
    """Returns text, where every other character has been changed to swap
    its lexical case. For strings that contain at least one letter, the
    returned string is guaranteed to be different from the input string."""
    text_cs = ''
    i = 0
    for c in text:
        if i % 2 != 0:
            c = c.swapcase()
        text_cs += c
        i += 1
    return text_cs


class TestEqual(BaseTest):
    """Class for test equal for dict items"""

    def assertDictEqual(self, d1, d2, msg=None):
        """Assert that two NocaseDict objects are equal."""

        # We override the inherited unittest.Testcase method and do checking in
        # both directions, because we override the __eq__() and __ne__()
        # methods on NocaseDict.
        # Note that the Python docs state that assertDictEqual() has parameters
        # 'expected', 'actual', but the implemented method has 'd1', 'd2'.

        self.assertTrue(d1 == d2, msg)
        self.assertFalse(d1 != d2, msg)

        self.assertTrue(d2 == d1, msg)
        self.assertFalse(d2 != d1, msg)

    def assertDictNotEqual(self, d1, d2, msg=None):
        """Assert that two NocaseDict objects are not equal."""

        # unittest.Testcase does not have an according method. We perform
        # checking in both directions, because we override the __eq__() and
        # __ne__() methods on NocaseDict.

        self.assertTrue(d1 != d2, msg)
        self.assertFalse(d1 == d2, msg)

        self.assertTrue(d2 != d1, msg)
        self.assertFalse(d2 == d1, msg)

    def run_test_dicts(self, base_dict, test_dicts):
        """General test_dictionaries"""
        for test_dict, relation, dict_types, comment in test_dicts:

            if type(test_dict) not in dict_types:  # noqa: E501 pylint: disable=unidiomatic-typecheck
                continue

            if relation == 'eq':
                self.assertDictEqual(test_dict, base_dict,
                                     "Expected test_dict == base_dict:\n"
                                     "  test case: %s\n"
                                     "  test_dict: %r\n"
                                     "  base_dict: %r" %
                                     (comment, test_dict, base_dict))
            elif relation == 'ne':
                self.assertDictNotEqual(test_dict, base_dict,
                                        "Expected test_dict != base_dict:\n"
                                        "  test case: %s\n"
                                        "  test_dict: %r\n"
                                        "  base_dict: %r" %
                                        (comment, test_dict, base_dict))
            else:
                raise AssertionError("Internal Error: Invalid relation %s"
                                     "specified in testcase: %s" %
                                     (relation, comment))

    def test_all(self):
        """Class for overall test"""

        class C1(object):
            # pylint: disable=too-few-public-methods
            """Class used as dict item to provoke non-comparability."""

            def __eq__(self, other):
                raise TypeError("Cannot compare %r to %r" % (self, other))

            def __ne__(self, other):
                raise TypeError("Cannot compare %r to %r" % (self, other))

        # The base dictionary that is used for all comparisons
        base_dict = dict({'Budgie': 'Fish', 'Dog': 'Cat'})

        # Test dictionaries to test against the base dict, as a list of
        # tuple(dict, relation, comment), with relation being the expected
        # comparison relation, and one of ('eq', 'ne').
        test_dicts = [

            (dict({'Budgie': 'Fish', 'Dog': 'Cat'}),
             'eq',
             (dict, NocaseDict),
             'Same'),

            (dict({'Budgie': 'Fish'}),
             'ne',
             (dict, NocaseDict),
             'Higher key missing, shorter size'),

            (dict({'Dog': 'Cat'}),
             'ne',
             (dict, NocaseDict),
             'Lower key missing, shorter size'),

            (dict({'Budgie': 'Fish', 'Curly': 'Snake', 'Cozy': 'Dog'}),
             'ne',
             (dict, NocaseDict),
             'First non-matching key is less. But longer size!'),

            (dict({'Alf': 'F', 'Anton': 'S', 'Aussie': 'D'}),
             'ne',
             (dict, NocaseDict),
             'Only non-matching keys that are less. But longer size!'),

            (dict({'Budgio': 'Fish'}),
             'ne',
             (dict, NocaseDict),
             'First non-matching key is greater. But shorter size!'),

            (dict({'Zoe': 'F'}),
             'ne',
             (dict, NocaseDict),
             'Only non-matching keys that are greater. But shorter size!'),

            (dict({'Budgie': 'Fish', 'Curly': 'Snake'}),
             'ne',
             (dict, NocaseDict),
             'Same size. First non-matching key is less'),

            (dict({'Alf': 'F', 'Anton': 'S'}),
             'ne',
             (dict, NocaseDict),
             'Same size. Only non-matching keys that are less'),

            (dict({'Zoe': 'F', 'Zulu': 'S'}),
             'ne',
             (dict, NocaseDict),
             'Same size. Only non-matching keys that are greater'),

            (dict({'Budgie': 'Fish', 'Dog': 'Car'}),
             'ne',
             (dict, NocaseDict),
             'Same size, only matching keys. First non-matching value is less'),

            (dict({'Budgie': 'Fish', 'Dog': 'Caz'}),
             'ne',
             (dict, NocaseDict),
             'Same size, only matching keys. First non-matching value is grt.'),

            (dict({'Budgie': C1(), 'Dog': 'Cat'}),
             'ne',
             (NocaseDict,),
             'Not-comparable items.'),
        ]

        # First, run these tests against a standard dictionary to verify
        # that the test case definitions conform to that

        self.run_test_dicts(base_dict, test_dicts)

        # Then, transform these tests to NocaseDict and run them again
        TEST_CASE_INSENSITIVITY = True
        base_ncdict = NocaseDict(base_dict)
        test_ncdicts = []
        for test_dict, relation, dict_types, comment in test_dicts:
            test_ncdict = NocaseDict()
            for key in test_dict:
                if TEST_CASE_INSENSITIVITY:
                    nc_key = swapcase2(key)
                else:
                    nc_key = key
                test_ncdict[nc_key] = test_dict[key]
            test_ncdicts.append((test_ncdict, relation, dict_types, comment))
        self.run_test_dicts(base_ncdict, test_ncdicts)


class TestOrdering(BaseTest):
    """Verify that ordering comparisons between NocaseDict instances
    issue a deprecation warning, and for Python 3, in addition raise
    TypeError."""

    def assertWarning(self, comp_str):
        """Common function for assert warning"""
        with warnings.catch_warnings(record=True) as wlist:
            warnings.simplefilter("always")
            if six.PY2:
                eval(comp_str)  # pylint: disable=eval-used
            else:
                try:
                    eval(comp_str)  # pylint: disable=eval-used
                except TypeError as exc:
                    msg = str(exc)
                    if "not supported between instances" not in msg and \
                            "unorderable types" not in msg:
                        self.fail("Applying ordering to a dictionary in "
                                  "Python 3 did raise TypeError but with an "
                                  "unexpected message: %s" % msg)
                except Exception as exc:  # pylint: disable=broad-except
                    msg = str(exc)
                    self.fail("Applying ordering to a dictionary in Python 3 "
                              "did not raise TypeError, but %s: %s" %
                              (exc.__class__.__name__, msg))
                else:
                    self.fail("Applying ordering to a dictionary in Python 3 "
                              "succeeded (should not happen)")
            assert len(wlist) >= 1
            assert issubclass(wlist[-1].category, DeprecationWarning)
            assert "deprecated" in str(wlist[-1].message)

    def test_all(self):
        """Test for the compare options that should generate assertWarning"""
        self.assertWarning("self.dic < self.dic")
        self.assertWarning("self.dic <= self.dic")
        self.assertWarning("self.dic > self.dic")
        self.assertWarning("self.dic >= self.dic")


class TestContains(BaseTest):
    """Class for dict contains functionality"""
    def test_all(self):
        """Method for test dict contains functionality"""
        self.assertTrue('dog' in self.dic)
        self.assertTrue('Dog' in self.dic)
        self.assertTrue('Cat' not in self.dic)


class TestForLoop(BaseTest):
    """Class for test for loop with dictionary"""
    def test_all(self):
        """Test method for TestForLoop"""
        keys = set()
        for key in self.dic:
            keys.add(key)
        self.assertTrue(keys, set(['Budgie', 'Dog']))


class TestIterkeys(BaseTest):
    """Class for iterkeys test"""
    def test_all(self):
        """iterkeys test method"""
        keys = set()
        for key in self.dic.iterkeys():
            keys.add(key)
        self.assertTrue(keys, set(['Budgie', 'Dog']))


class TestItervalues(BaseTest):
    """Class for test itervalues test"""
    def test_all(self):
        """itervalues test method"""
        vals = set()
        for val in self.dic.itervalues():
            vals.add(val)
        self.assertTrue(vals, set(['Cat', 'Fish']))


class TestIteritems(BaseTest):
    """Class to test iteritems for dict"""
    def test_all(self):
        """Method for test iteritems for dict"""
        items = set()
        for item in self.dic.iteritems():
            items.add(item)
        self.assertTrue(items, set([('Budgie', 'Fish'), ('Dog', 'Cat')]))


class TestRepr(unittest.TestCase):
    """Class to test repr functionality for NocaseDict"""
    def test_reliable_order(self):
        """Test that repr() has a reliable result despite different orders of
        insertion into the dictionary."""

        dic1 = NocaseDict()
        dic1['Budgie'] = 'Fish'
        dic1['Dog'] = 'Cat'
        dic1['Foo'] = 'Bla'

        dic2 = NocaseDict()
        dic2['Foo'] = 'Bla'
        dic2['Dog'] = 'Cat'
        dic2['Budgie'] = 'Fish'

        self.assertEqual(repr(dic1), repr(dic2))


if __name__ == '__main__':
    unittest.main()
