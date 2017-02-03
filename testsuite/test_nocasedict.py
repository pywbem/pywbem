#!/usr/bin/env python
#
# Test case-insensitive dictionary implementation.
#

from __future__ import absolute_import

import unittest
import warnings
import six

from pywbem.cim_obj import NocaseDict


class TestInit(unittest.TestCase):

    def test_all(self):

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

    def setUp(self):
        self.dic = NocaseDict()
        self.dic['Dog'] = 'Cat'
        self.dic['Budgie'] = 'Fish'


class TestGetitem(BaseTest):

    def test_all(self):
        self.assertTrue(self.dic['dog'] == 'Cat')
        self.assertTrue(self.dic['DOG'] == 'Cat')

        try:
            self.dic['notfound']
        except KeyError:
            pass
        else:
            self.fail("KeyError was unexpectedly not thrown.")


class TestLen(BaseTest):

    def test_all(self):
        self.assertTrue(len(self.dic) == 2)


class TestSetitem(BaseTest):

    def test_all(self):

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

    def test_all(self):
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

    def test_all(self):
        self.assertTrue('DOG' in self.dic)
        self.assertTrue('budgie' in self.dic)
        self.assertTrue(1234 not in self.dic)


class TestKeys(BaseTest):

    def test_all(self):
        keys = self.dic.keys()
        animals = ['Budgie', 'Dog']
        for ani in animals:
            self.assertTrue(ani in keys)
            keys.remove(ani)
        self.assertTrue(keys == [])


class TestValues(BaseTest):

    def test_all(self):
        values = self.dic.values()
        animals = ['Cat', 'Fish']
        for ani in animals:
            self.assertTrue(ani in values)
            values.remove(ani)
        self.assertTrue(values == [])


class TestItems(BaseTest):

    def test_all(self):
        items = self.dic.items()
        animals = [('Dog', 'Cat'), ('Budgie', 'Fish')]
        for ani in animals:
            self.assertTrue(ani in items)
            items.remove(ani)
        self.assertTrue(items == [])


class TestClear(BaseTest):

    def test_all(self):
        self.dic.clear()
        self.assertTrue(len(self.dic) == 0)


class TestUpdate(BaseTest):

    def test_all(self):
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

    def test_all(self):
        cp = self.dic.copy()
        self.assertEqual(cp, self.dic)
        self.assertTrue(isinstance(cp, NocaseDict))
        cp['Dog'] = 'Kitten'
        self.assertTrue(self.dic['Dog'] == 'Cat')
        self.assertTrue(cp['Dog'] == 'Kitten')


class TestGet(BaseTest):

    def test_all(self):
        self.assertTrue(self.dic.get('Dog', 'Chicken') == 'Cat')
        self.assertTrue(self.dic.get('Ningaui') is None)
        self.assertTrue(self.dic.get('Ningaui', 'Chicken') == 'Chicken')


class TestSetDefault(BaseTest):

    def test_all(self):
        self.dic.setdefault('Dog', 'Kitten')
        self.assertTrue(self.dic['Dog'] == 'Cat')
        self.dic.setdefault('Ningaui', 'Chicken')
        self.assertTrue(self.dic['Ningaui'] == 'Chicken')


class TestPopItem(BaseTest):

    def test_all(self):
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

    def assertDictEqual(self, dic1, dic2, msg):

        self.assertTrue(dic1 == dic2, msg)
        self.assertFalse(dic1 != dic2, msg)

        self.assertTrue(dic2 == dic1, msg)
        self.assertFalse(dic2 != dic1, msg)

    def assertDictNotEqual(self, dic1, dic2, msg):

        self.assertTrue(dic1 != dic2, msg)
        self.assertFalse(dic1 == dic2, msg)

        self.assertTrue(dic2 != dic1, msg)
        self.assertFalse(dic2 == dic1, msg)

    def run_test_dicts(self, base_dict, test_dicts):

        for test_dict, relation, comment in test_dicts:
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

        # The base dictionary that is used for all comparisons
        base_dict = dict({'Budgie': 'Fish', 'Dog': 'Cat'})

        # Test dictionaries to test against the base dict, as a list of
        # tuple(dict, relation, comment), with relation being the expected
        # comparison relation, and one of ('eq', 'ne').
        test_dicts = [

            (dict({'Budgie': 'Fish', 'Dog': 'Cat'}),
             'eq',
             'Same'),

            (dict({'Budgie': 'Fish'}),
             'ne',
             'Higher key missing, shorter size'),

            (dict({'Dog': 'Cat'}),
             'ne',
             'Lower key missing, shorter size'),

            (dict({'Budgie': 'Fish', 'Curly': 'Snake', 'Cozy': 'Dog'}),
             'ne',
             'First non-matching key is less. But longer size!'),

            (dict({'Alf': 'F', 'Anton': 'S', 'Aussie': 'D'}),
             'ne',
             'Only non-matching keys that are less. But longer size!'),

            (dict({'Budgio': 'Fish'}),
             'ne',
             'First non-matching key is greater. But shorter size!'),

            (dict({'Zoe': 'F'}),
             'ne',
             'Only non-matching keys that are greater. But shorter size!'),

            (dict({'Budgie': 'Fish', 'Curly': 'Snake'}),
             'ne',
             'Same size. First non-matching key is less'),

            (dict({'Alf': 'F', 'Anton': 'S'}),
             'ne',
             'Same size. Only non-matching keys that are less'),

            (dict({'Zoe': 'F', 'Zulu': 'S'}),
             'ne',
             'Same size. Only non-matching keys that are greater'),

            (dict({'Budgie': 'Fish', 'Dog': 'Car'}),
             'ne',
             'Same size, only matching keys. First non-matching value is less'),

            (dict({'Budgie': 'Fish', 'Dog': 'Caz'}),
             'ne',
             'Same size, only matching keys. First non-matching value is grt.'),
        ]

        # First, run these tests against a standard dictionary to verify
        # that the test case definitions conform to that
        self.run_test_dicts(base_dict, test_dicts)

        # Then, transform these tests to NocaseDict and run them again
        TEST_CASE_INSENSITIVITY = True
        base_ncdict = NocaseDict(base_dict)
        test_ncdicts = []
        for test_dict, relation, comment in test_dicts:
            test_ncdict = NocaseDict()
            for key in test_dict:
                if TEST_CASE_INSENSITIVITY:
                    nc_key = swapcase2(key)
                else:
                    nc_key = key
                test_ncdict[nc_key] = test_dict[key]
            test_ncdicts.append((test_ncdict, relation, comment))
        self.run_test_dicts(base_ncdict, test_ncdicts)


class TestOrdering(BaseTest):
    """Verify that ordering comparisons between NocaseDict instances
    issue a deprecation warning, and for Python 3, in addition raise
    TypeError."""

    def assertWarning(self, comp_str):
        with warnings.catch_warnings(record=True) as wlist:
            warnings.simplefilter("always")
            if six.PY2:
                eval(comp_str)
            else:
                try:
                    eval(comp_str)
                except TypeError as exc:
                    msg = str(exc)
                    if "not supported between instances" not in msg and \
                            "unorderable types" not in msg:
                        self.fail("Applying ordering to a dictionary in "
                                  "Python 3 did raise TypeError but with an "
                                  "unexpected message: %s" % msg)
                except Exception as exc:
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
        self.assertWarning("self.dic < self.dic")
        self.assertWarning("self.dic <= self.dic")
        self.assertWarning("self.dic > self.dic")
        self.assertWarning("self.dic >= self.dic")


class TestContains(BaseTest):

    def test_all(self):
        self.assertTrue('dog' in self.dic)
        self.assertTrue('Dog' in self.dic)
        self.assertTrue('Cat' not in self.dic)


class TestForLoop(BaseTest):

    def test_all(self):
        keys = set()
        for key in self.dic:
            keys.add(key)
        self.assertTrue(keys, set(['Budgie', 'Dog']))


class TestIterkeys(BaseTest):

    def test_all(self):
        keys = set()
        for key in self.dic.iterkeys():
            keys.add(key)
        self.assertTrue(keys, set(['Budgie', 'Dog']))


class TestItervalues(BaseTest):

    def test_all(self):
        vals = set()
        for val in self.dic.itervalues():
            vals.add(val)
        self.assertTrue(vals, set(['Cat', 'Fish']))


class TestIteritems(BaseTest):

    def test_all(self):
        items = set()
        for item in self.dic.iteritems():
            items.add(item)
        self.assertTrue(items, set([('Budgie', 'Fish'), ('Dog', 'Cat')]))


if __name__ == '__main__':
    unittest.main()
