#!/usr/bin/env python
#
# Test case-insensitive dictionary implementation.
#

from __future__ import absolute_import

import unittest

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

        dic = NocaseDict([('Dog', 'Cat'),], Budgie='Fish')
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
        except TypeError as exc:
            pass
        else:
            self.fail("TypeError was unexpectedly not thrown.")

        # Initialise with too many positional arguments

        try:
            dic = NocaseDict(list(), list())
        except TypeError as exc:
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
            x = self.dic['notfound']
        except KeyError as exc:
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
        except KeyError as exc:
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

class TestEqual(BaseTest):

    def test_all(self):
        dic2 = NocaseDict({'dog': 'Cat', 'Budgie': 'Fish'})
        self.assertTrue(self.dic == dic2)
        dic2['Budgie'] = 'fish'
        self.assertTrue(self.dic != dic2)

class TestComparison(BaseTest):

    def assertSame(self, dic1, dic2):

        self.assertTrue(dic1 == dic2)
        self.assertFalse(dic1 != dic2)
        self.assertTrue(dic1 >= dic2)
        self.assertFalse(dic1 > dic2)
        self.assertTrue(dic1 <= dic2)
        self.assertFalse(dic1 < dic2)

        self.assertTrue(dic2 == dic1)
        self.assertFalse(dic2 != dic1)
        self.assertTrue(dic2 >= dic1)
        self.assertFalse(dic2 > dic1)
        self.assertTrue(dic2 <= dic1)
        self.assertFalse(dic2 < dic1)

    def assertLess(self, dic1, dic2):

        self.assertTrue(dic1 != dic2)
        self.assertFalse(dic1 == dic2)
        self.assertTrue(dic1 < dic2)
        self.assertFalse(dic1 > dic2)
        self.assertTrue(dic1 <= dic2)
        self.assertFalse(dic1 >= dic2)

        self.assertTrue(dic2 != dic1)
        self.assertFalse(dic2 == dic1)
        self.assertTrue(dic2 > dic1)
        self.assertFalse(dic2 < dic1)
        self.assertTrue(dic2 >= dic1)
        self.assertFalse(dic2 <= dic1)

    def test_all(self):
        dic_same = NocaseDict({'doG': 'Cat', 'BuDgie': 'Fish'})
        dic_less1 = NocaseDict({'doG': 'Cat'})
        dic_less2 = NocaseDict({'DOg': 'Cat', 'Alf': 'Horse'})
        dic_less3 = NocaseDict({'doG': 'Car', 'budGie': 'Fish'})

        self.assertSame(dic_same, self.dic)
        # TODO: Enable these tests to work on the dict ordering issue
        #self.assertLess(dic_less1, self.dic)
        #self.assertLess(dic_less2, self.dic)
        #self.assertLess(dic_less3, self.dic)

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
