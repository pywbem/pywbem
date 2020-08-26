#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

"""
Test of pywbem_mock.ProviderRegistry.
"""

from __future__ import absolute_import, print_function

import pickle
import pytest

from ..utils.pytest_extensions import simplified_test_function

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import CIMClass  # noqa: E402
pywbem_mock = import_installed('pywbem_mock')
from pywbem_mock import FakedWBEMConnection, MethodProvider, \
    InstanceWriteProvider, BaseProvider  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


def assert_provreg_equal(provreg1, provreg2):
    """
    Assert that two ProviderRegistry objects are equal.

    Structure: self._registry[namespace][classname][prov_type] = prov_obj
    """
    ns_dict1 = provreg1._registry  # pylint: disable=protected-access
    ns_dict2 = provreg2._registry  # pylint: disable=protected-access

    assert sorted(ns_dict1) == sorted(ns_dict2)
    for ns in ns_dict1:
        class_dict1 = ns_dict1[ns]
        assert ns in ns_dict2
        class_dict2 = ns_dict2[ns]

        assert sorted(class_dict1.keys()) == sorted(class_dict2.keys())
        for cln in class_dict1.keys():
            ptype_dict1 = class_dict1[cln]
            assert cln in class_dict2
            ptype_dict2 = class_dict2[cln]

            assert sorted(ptype_dict1.keys()) == sorted(ptype_dict2.keys())
            for pt in ptype_dict1.keys():
                pobj1 = ptype_dict1[pt]
                assert pt in ptype_dict2
                pobj2 = ptype_dict2[pt]

                assert_prov_equal(pobj1, pobj2)


def assert_prov_equal(prov1, prov2):
    """
    Assert that two Provider objects (derived from BaseProvider) are equal.
    """
    assert isinstance(prov1, BaseProvider)
    assert isinstance(prov2, BaseProvider)
    assert prov1.__class__ == prov2.__class__
    assert prov1.provider_type == prov2.provider_type
    assert prov1.provider_classnames == prov2.provider_classnames
    # pylint: disable=protected-access
    assert prov1._interop_namespace_names == prov2._interop_namespace_names


def create_registered_conn(providers):
    """
    Create and return a FakedWBEMConnection object that has the specified
    providers registered.

    providers: Providers to be registered.
       providers are specified as tuple(prov_class, cim_class, namespace):
         - prov_class: Python class of provider
         - cim_class: Name of CIM class for the provider
         - namespace: CIM namespace for the provider
    """

    # Build a FakedWBEMConnection that has the required namespaces, classes
    # and registered providers in its provider registry.
    conn = FakedWBEMConnection()
    for item in providers:

        prov_class, cim_class, namespace = item

        # Make sure the namespace exists in the CIM repository
        if namespace not in conn.namespaces:
            conn.add_namespace(namespace)

        # Make sure the CIM class exists in the CIM repository
        class_store = conn.cimrepository.get_class_store(namespace)
        if not class_store.object_exists(cim_class):
            # An empty class is sufficient for this purpose:
            class_obj = CIMClass(cim_class)
            conn.add_cimobjects(class_obj, namespace=namespace)

        # Create the provider object, setting up its provider classes
        prov_class.provider_classnames = cim_class
        prov_obj = prov_class(conn.cimrepository)

        # Register the provider
        conn.register_provider(prov_obj, namespaces=namespace)

    return conn


class TstMethodProvider1(MethodProvider):
    """Test method provider #1"""

    provider_classnames = None  # Will be set before use

    def __init__(self, cimrepository):
        super(TstMethodProvider1, self).__init__(cimrepository)

    def InvokeMethod(self, methodname, localobject, params):
        """Dummy provider method"""
        pass


class TstMethodProvider2(MethodProvider):
    """Test method provider #2"""

    provider_classnames = None  # Will be set before use

    def __init__(self, cimrepository):
        super(TstMethodProvider2, self).__init__(cimrepository)

    def InvokeMethod(self, methodname, localobject, params):
        """Dummy provider method"""
        pass


class TstInstWrProvider1(InstanceWriteProvider):
    """Test instance write provider #1"""

    provider_classnames = None  # Will be set before use

    def __init__(self, cimrepository):
        super(TstInstWrProvider1, self).__init__(cimrepository)

    def CreateInstance(self, namespace, new_instance):
        """Dummy provider method"""
        pass


class TstInstWrProvider2(InstanceWriteProvider):
    """Test instance write provider #2"""

    provider_classnames = None  # Will be set before use

    def __init__(self, cimrepository):
        super(TstInstWrProvider2, self).__init__(cimrepository)

    def CreateInstance(self, namespace, new_instance):
        """Dummy provider method"""
        pass


# TODO: Add tests for __repr__()
# TODO: Add tests for display_registered_providers()
# TODO: Add tests for register_provider()
# TODO: Add tests for get_registered_provider()
# TODO: Add tests for provider_namespaces()
# TODO: Add tests for provider_classes()
# TODO: Add tests for provider_types()
# TODO: Add tests for provider_obj()


TESTCASES_PROVREG_ITERITEMS = [

    # Testcases for ProviderRegistry.iteritems()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * providers: providers for ProviderRegistry object
    #   providers are specified as tuple(prov_class, cim_class, namespace):
    #     - prov_class: Python class of provider
    #     - cim_class: Name of CIM class for the provider
    #     - namespace: CIM namespace for the provider
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Empty registry",
        dict(
            providers=[],
        ),
        None, None, True
    ),
    (
        "Registry with one provider",
        dict(
            providers=[
                (TstMethodProvider1, 'CIM_Foo1', 'root/blah1'),
            ],
        ),
        None, None, True
    ),
    (
        "Registry with prov for two different classes in same namespace",
        dict(
            providers=[
                (TstMethodProvider1, 'CIM_Foo1', 'root/blah1'),
                (TstInstWrProvider1, 'CIM_Foo1', 'root/blah1'),
                (TstMethodProvider2, 'CIM_Foo2', 'root/blah1'),
                (TstInstWrProvider2, 'CIM_Foo2', 'root/blah1'),
            ],
        ),
        None, None, True
    ),
    (
        "Registry with prov for same class in two different namespaces",
        dict(
            providers=[
                (TstMethodProvider1, 'CIM_Foo1', 'root/blah1'),
                (TstInstWrProvider1, 'CIM_Foo1', 'root/blah1'),
                (TstMethodProvider1, 'CIM_Foo1', 'root/blah2'),
                (TstInstWrProvider1, 'CIM_Foo1', 'root/blah2'),
            ],
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_PROVREG_ITERITEMS)
@simplified_test_function
def test_ProviderRegistry_iteritems(testcase, providers):
    """
    Test function for ProviderRegistry.iteritems().
    """
    conn = create_registered_conn(providers)
    provreg = conn._provider_registry  # pylint: disable=protected-access

    # The code to be tested
    res_providers = list(provreg.iteritems())

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    # Build lists for comparison, with list items that are:
    # tuple(namespace, cim_classname, prov_type, prov_classname)
    res_list = sorted([(p[0], p[1], p[2], p[3].__class__.__name__)
                       for p in res_providers])
    exp_list = sorted([(p[2], p[1], p[0].provider_type, p[0].__name__)
                       for p in providers])

    assert res_list == exp_list


TESTCASES_PROVREG_LOAD = [

    # Testcases for ProviderRegistry.load()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * providers1: providers for ProviderRegistry object #1
    #   * providers2: providers for ProviderRegistry object #2
    #   providers are specified as tuple(prov_class, cim_class, namespace):
    #     - prov_class: Python class of provider
    #     - cim_class: Name of CIM class for the provider
    #     - namespace: CIM namespace for the provider
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Empty registry loaded with empty registry",
        dict(
            providers1=[],
            providers2=[],
        ),
        None, None, True
    ),
    (
        "Empty registry loaded with registry with one provider",
        dict(
            providers1=[],
            providers2=[
                (TstMethodProvider1, 'CIM_Foo', 'root/blah'),
            ],
        ),
        None, None, True
    ),
    (
        "Registry with one provider loaded with empty registry",
        dict(
            providers1=[
                (TstMethodProvider1, 'CIM_Foo', 'root/blah'),
            ],
            providers2=[],
        ),
        None, None, True
    ),
    (
        "Registry with one provider loaded with registry with diff. provider",
        dict(
            providers1=[
                (TstMethodProvider1, 'CIM_Foo', 'root/blah'),
            ],
            providers2=[
                (TstInstWrProvider1, 'CIM_Foo', 'root/blah'),
            ],
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_PROVREG_LOAD)
@simplified_test_function
def test_ProviderRegistry_load(testcase, providers1, providers2):
    """
    Test function for ProviderRegistry.load().
    """
    conn1 = create_registered_conn(providers1)
    provreg1 = conn1._provider_registry  # pylint: disable=protected-access

    conn2 = create_registered_conn(providers2)
    provreg2 = conn2._provider_registry  # pylint: disable=protected-access

    # The code to be tested
    provreg1.load(provreg2)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert_provreg_equal(provreg1, provreg2)


TESTCASES_PROVREG_PICKLE = [

    # Testcases for pickling and unpickling ProviderRegistry objects

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * providers: providers for ProviderRegistry object to be used for test
    #   providers are specified as tuple(prov_class, cim_class, namespace):
    #     - prov_class: Python class of provider
    #     - cim_class: Name of CIM class for the provider
    #     - namespace: CIM namespace for the provider
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Empty provider registry",
        dict(
            providers=[],
        ),
        None, None, True
    ),
    (
        "Provider registry with one method provider",
        dict(
            providers=[
                (TstMethodProvider1, 'CIM_Foo', 'root/blah'),
            ],
        ),
        None, None, True
    ),
    (
        "Provider registry with one method provider",
        dict(
            providers=[
                (TstMethodProvider1, 'CIM_Foo', 'root/blah'),
                (TstInstWrProvider1, 'CIM_Foo', 'root/blah'),
            ],
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_PROVREG_PICKLE)
@simplified_test_function
def test_ProviderRegistry_pickle(testcase, providers):
    """
    Test function for pickling and unpickling ProviderRegistry objects.
    """
    conn = create_registered_conn(providers)
    provreg = conn._provider_registry  # pylint: disable=protected-access

    # Pickle the object
    pkl = pickle.dumps(provreg)

    # Unpickle the object
    provreg2 = pickle.loads(pkl)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert_provreg_equal(provreg2, provreg)
