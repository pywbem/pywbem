#!/usr/bin/env python
#
# Test case-insensitive dictionary implementation.
#

from __future__ import absolute_import

import unittest

from pywbem.cim_obj import NocaseDict


class TestInit(unittest.TestCase):

    def test_all(self):

        # Basic init

        d = NocaseDict()
        self.assertTrue(len(d) == 0)

        # Initialise from sequence object

        d = NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')])
        self.assertTrue(len(d) == 2)
        self.assertTrue(d['Dog'] == 'Cat' and d['Budgie'] == 'Fish')

        # Initialise from mapping object

        d = NocaseDict({'Dog': 'Cat', 'Budgie': 'Fish'})
        self.assertTrue(len(d) == 2)
        self.assertTrue(d['Dog'] == 'Cat' and d['Budgie'] == 'Fish')

        # Initialise from kwargs

        d = NocaseDict(Dog='Cat', Budgie='Fish')
        self.assertTrue(len(d) == 2)
        self.assertTrue(d['Dog'] == 'Cat' and d['Budgie'] == 'Fish')

class BaseTest(unittest.TestCase):

    def setUp(self):
        self.d = NocaseDict()
        self.d['Dog'] = 'Cat'
        self.d['Budgie'] = 'Fish'

class TestGetitem(BaseTest):

    def test_all(self):
        self.assertTrue(self.d['dog'] == 'Cat')
        self.assertTrue(self.d['DOG'] == 'Cat')

class TestLen(BaseTest):

    def test_all(self):
        self.assertTrue(len(self.d) == 2)

class TestSetitem(BaseTest):

    def test_all(self):

        self.d['DOG'] = 'Kitten'
        self.assertTrue(self.d['DOG'] == 'Kitten')
        self.assertTrue(self.d['Dog'] == 'Kitten')
        self.assertTrue(self.d['dog'] == 'Kitten')

        # Check that using a non-string key raises an exception

        try:
            self.d[1234] = '1234'
        except TypeError:
            pass
        else:
            self.fail('TypeError expected')

class TestDelitem(BaseTest):

    def test_all(self):
        del self.d['DOG']
        del self.d['budgie']
        self.assertTrue(self.d.keys() == [])

class TestHasKey(BaseTest):

    def test_all(self):
        self.assertTrue('DOG' in self.d)
        self.assertTrue('budgie' in self.d)
        self.assertTrue(1234 not in self.d)

class TestKeys(BaseTest):

    def test_all(self):
        keys = self.d.keys()
        animals = ['Budgie', 'Dog']
        for a in animals:
            self.assertTrue(a in keys)
            keys.remove(a)
        self.assertTrue(keys == [])

class TestValues(BaseTest):

    def test_all(self):
        values = self.d.values()
        animals = ['Cat', 'Fish']
        for a in animals:
            self.assertTrue(a in values)
            values.remove(a)
        self.assertTrue(values == [])

class TestItems(BaseTest):

    def test_all(self):
        items = self.d.items()
        animals = [('Dog', 'Cat'), ('Budgie', 'Fish')]
        for a in animals:
            self.assertTrue(a in items)
            items.remove(a)
        self.assertTrue(items == [])

class TestClear(BaseTest):

    def test_all(self):
        self.d.clear()
        self.assertTrue(len(self.d) == 0)

class TestUpdate(BaseTest):

    def test_all(self):
        self.d.clear()
        self.d.update({'Chicken': 'Ham'})
        self.assertTrue(self.d.keys() == ['Chicken'])
        self.assertTrue(self.d.values() == ['Ham'])
        self.d.clear()
        self.d.update({'Chicken': 'Ham'}, {'Dog': 'Cat'})
        keys = self.d.keys()
        vals = self.d.values()
        keys = list(keys)
        vals = list(vals)
        keys.sort()
        vals.sort()
        self.assertTrue(keys == ['Chicken', 'Dog'])
        self.assertTrue(vals == ['Cat', 'Ham'])
        self.d.update([('Chicken', 'Egg')], {'Fish': 'Eel'})
        self.assertTrue(self.d['chicken'] == 'Egg')
        self.assertTrue(self.d['fish'] == 'Eel')
        self.d.update({'Fish': 'Salmon'}, Cow='Beef')
        self.assertTrue(self.d['fish'] == 'Salmon')
        self.assertTrue(self.d['Cow'] == 'Beef')
        self.assertTrue(self.d['COW'] == 'Beef')
        self.assertTrue(self.d['cow'] == 'Beef')

class TestCopy(BaseTest):

    def test_all(self):
        c = self.d.copy()
        self.assertEqual(c, self.d)
        self.assertTrue(isinstance(c, NocaseDict))
        c['Dog'] = 'Kitten'
        self.assertTrue(self.d['Dog'] == 'Cat')
        self.assertTrue(c['Dog'] == 'Kitten')

class TestGet(BaseTest):

    def test_all(self):
        self.assertTrue(self.d.get('Dog', 'Chicken') == 'Cat')
        self.assertTrue(self.d.get('Ningaui') is None)
        self.assertTrue(self.d.get('Ningaui', 'Chicken') == 'Chicken')

class TestSetDefault(BaseTest):

    def test_all(self):
        self.d.setdefault('Dog', 'Kitten')
        self.assertTrue(self.d['Dog'] == 'Cat')
        self.d.setdefault('Ningaui', 'Chicken')
        self.assertTrue(self.d['Ningaui'] == 'Chicken')

class TestPopItem(BaseTest):

    def test_all(self):
        pass

class TestEqual(BaseTest):

    def test_all(self):
        c = NocaseDict({'dog': 'Cat', 'Budgie': 'Fish'})
        self.assertTrue(self.d == c)
        c['Budgie'] = 'fish'
        self.assertTrue(self.d != c)

class TestContains(BaseTest):

    def test_all(self):
        self.assertTrue('dog' in self.d)
        self.assertTrue('Dog' in self.d)
        self.assertTrue('Cat' not in self.d)

class TestIterkeys(BaseTest):

    def test_all(self):
        for k in self.d.iterkeys():
            self.assertTrue(k in ['Budgie', 'Dog'])

class TestItervalues(BaseTest):

    def test_all(self):
        for v in self.d.itervalues():
            self.assertTrue(v in ['Cat', 'Fish'])

class TestIteritems(BaseTest):

    def test_all(self):
        for i in self.d.iteritems():
            self.assertTrue(i in [('Budgie', 'Fish'), ('Dog', 'Cat')])


if __name__ == '__main__':
    unittest.main()
