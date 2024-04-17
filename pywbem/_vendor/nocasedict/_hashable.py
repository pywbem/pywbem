"""
This module provides class HashableMixin.
"""

from __future__ import print_function, absolute_import

__all__ = ['HashableMixin']


class HashableMixin(object):
    # pylint: disable=too-few-public-methods
    """
    A mixin class that adds case-insensitive hashability to
    :class:`nocasedict.NocaseDict`.

    The derived class inheriting from :class:`~nocasedict.HashableMixin`
    must (directly or indirectly) inherit from
    :class:`~nocasedict.NocaseDict`.

    Hashability allows objects of the derived class to be used as keys of
    :class:`py:dict` and members of :class:`py:set`, because these data
    structures use the hash values internally.

    The hash value calculated by this mixin class uses the hash values of the
    keys and values of the dictionary in such a way that the hash value of the
    key is case-insensitive (i.e. it does not change for different lexical
    cases of a key), and the hash value of the dictionary is order-insensitive
    (i.e. it does not change for a different order of items).

    Since :class:`~nocasedict.NocaseDict` objects are mutable, reliable use of
    the hash value requires that no items in the dictionary are added, removed
    or updated, while the dictionary object is used as a key (in another
    dictionary) or as a set member.

    See `hashable <https://docs.python.org/3/glossary.html#term-hashable>`_
    for more details.

    Example::

        from nocasedict import NocaseDict, HashableMixin

        class MyDict(HashableMixin, NocaseDict):
            pass

        mykey1 = MyDict(a=1, b=2)
        mykey2 = MyDict(B=2, A=1)  # case- and order-insensitively equal

        dict1 = {mykey1: 'foo'}  # Add item using first key

        print(dict1[mykey2])  # Access item using second key
        # 'foo'
    """

    def __hash__(self):
        """
        Return a case-insensitive and order-insensitive hash value for the
        dictionary.
        """
        fs = frozenset([(knc, self.__getitem__(knc))
                        for knc in self.keys_nocase()])
        return hash(fs)
