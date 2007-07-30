#!/usr/bin/python
#
# Test case-insensitive dictionary implementation.
#

import comfychair
from pywbem import cim_obj

class TestInit(comfychair.TestCase):
    def runtest(self):

        # Basic init

        d = cim_obj.NocaseDict()
        self.assert_(len(d) == 0)

        # Initialise from sequence object

        d = cim_obj.NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')])
        self.assert_(len(d) == 2)
        self.assert_(d['Dog'] == 'Cat' and d['Budgie'] == 'Fish')

        # Initialise from mapping object

        d = cim_obj.NocaseDict({'Dog': 'Cat', 'Budgie': 'Fish'})
        self.assert_(len(d) == 2)
        self.assert_(d['Dog'] == 'Cat' and d['Budgie'] == 'Fish')

        # Initialise from kwargs

        d = cim_obj.NocaseDict(Dog = 'Cat', Budgie = 'Fish')
        self.assert_(len(d) == 2)
        self.assert_(d['Dog'] == 'Cat' and d['Budgie'] == 'Fish')

class BaseTest(comfychair.TestCase):
    def setup(self):
        self.d = cim_obj.NocaseDict()
        self.d['Dog'] = 'Cat'
        self.d['Budgie'] = 'Fish'

class TestGetitem(BaseTest):
    def runtest(self):
        self.assert_(self.d['dog'] == 'Cat')
        self.assert_(self.d['DOG'] == 'Cat')

class TestLen(BaseTest):
    def runtest(self):
        self.assert_(len(self.d) == 2)

class TestSetitem(BaseTest):
    def runtest(self):

        self.d['DOG'] = 'Kitten'
        self.assert_(self.d['DOG'] == 'Kitten')
        self.assert_(self.d['Dog'] == 'Kitten')
        self.assert_(self.d['dog'] == 'Kitten')

        # Check that using a non-string key raises an exception

        try:
            self.d[1234] = '1234'
        except KeyError:
            pass
        else:
            self.fail('KeyError expected')

class TestDelitem(BaseTest):
    def runtest(self):
        del self.d['DOG']
        del self.d['budgie']
        self.assert_(self.d.keys() == [])

class TestHasKey(BaseTest):
    def runtest(self):
        self.assert_(self.d.has_key('DOG'))
        self.assert_(self.d.has_key('budgie'))
        self.assert_(not self.d.has_key(1234))

class TestKeys(BaseTest):
    def runtest(self):
        keys = self.d.keys()
        animals = ['Budgie', 'Dog']
        for a in animals:
            self.assert_(a in keys)
            keys.remove(a)
        self.assert_(keys == [])

class TestValues(BaseTest):
    def runtest(self):
        values = self.d.values()
        animals = ['Cat', 'Fish']
        for a in animals:
            self.assert_(a in values)
            values.remove(a)
        self.assert_(values == [])

class TestItems(BaseTest):
    def runtest(self):
        items = self.d.items()
        animals = [('Dog', 'Cat'), ('Budgie', 'Fish')]
        for a in animals:
            self.assert_(a in items)
            items.remove(a)
        self.assert_(items == [])
        
class TestClear(BaseTest):
    def runtest(self):
        self.d.clear()
        self.assert_(len(self.d) == 0)

class TestUpdate(BaseTest):
    def runtest(self):
        self.d.clear()
        self.d.update({'Chicken': 'Ham'})
        self.assert_(self.d.keys() == ['Chicken'])
        self.assert_(self.d.values() == ['Ham'])

class TestCopy(BaseTest):
    def runtest(self):
        c = self.d.copy()
        self.assert_equal(c, self.d)
        self.assert_(isinstance(c, cim_obj.NocaseDict))
        c['Dog'] = 'Kitten'
        self.assert_(self.d['Dog'] == 'Cat')
        self.assert_(c['Dog'] == 'Kitten')

class TestGet(BaseTest):
    def runtest(self):
        self.assert_(self.d.get('Dog', 'Chicken') == 'Cat')
        self.assert_(self.d.get('Ningaui') == None)
        self.assert_(self.d.get('Ningaui', 'Chicken') == 'Chicken')

class TestSetDefault(BaseTest):
    def runtest(self):
        self.d.setdefault('Dog', 'Kitten')
        self.assert_(self.d['Dog'] == 'Cat')
        self.d.setdefault('Ningaui', 'Chicken')
        self.assert_(self.d['Ningaui'] == 'Chicken')

class TestPopItem(BaseTest):
    def runtest(self):
        pass

class TestEqual(BaseTest):
    def runtest(self):
        c = cim_obj.NocaseDict({'dog': 'Cat', 'Budgie': 'Fish'})
        self.assert_(self.d == c)
        c['Budgie'] = 'fish'
        self.assert_(self.d != c)

class TestContains(BaseTest):
    def runtest(self):
        self.assert_('dog' in self.d)
        self.assert_('Dog' in self.d)
        self.assert_(not 'Cat' in self.d)

class TestIterkeys(BaseTest):
    def runtest(self):
        for k in self.d.iterkeys():
            self.assert_(k in ['Budgie', 'Dog'])

class TestItervalues(BaseTest):
    def runtest(self):
        for v in self.d.itervalues():
            self.assert_(v in ['Cat', 'Fish'])

class TestIteritems(BaseTest):
    def runtest(self):
        for i in self.d.iteritems():
            self.assert_(i in [('Budgie', 'Fish'), ('Dog', 'Cat')])

tests = [
    TestInit,
    TestGetitem,
    TestSetitem,
    TestDelitem,
    TestLen,
    TestHasKey,
    TestKeys,
    TestValues,
    TestItems,
    TestClear,
    TestUpdate,
    TestCopy,
    TestGet,
    TestSetDefault,
    TestPopItem,
    TestEqual,
    TestContains,
    TestIterkeys,
    TestItervalues,
    TestIteritems,
    ]

if __name__ == '__main__':
    comfychair.main(tests)
