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
# Author: Karl  Schopmeyer <inovadevelopment.com>
#

"""
Test of pywbem_mock package.  This tests the implementation of pywbem_mock
using a set of local mock qualifiers, classes, and instances.

"""
from __future__ import absolute_import, print_function

import pytest

from pywbem import CIMClass, CIMInstance, CIMInstanceName, CIMProperty, \
    CIMQualifierDeclaration, CIMQualifier

from pywbem._nocasedict import NocaseDict

from pywbem_mock._inmemoryrepository import InMemoryObjStore, InMemoryRepository

from ..utils.pytest_extensions import simplified_test_function

########################################################################
#
#      Test InMemoryObjStore
#
#########################################################################

TESTCASES_OBJSTORE = [

    # Testcases for OBJSTORE tests

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * init_args: list of
    #   * cls_kwargs: single class def or list of class def
    #   * inst_kwargs: Single inst def or list of class def
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Test with an class",
        dict(
            init_args=[True, CIMClass],
            cls_kwargs=dict(
                classname='CIM_Foo',
                properties=[
                    CIMProperty(
                        'P1', None, type='string',
                        qualifiers=[
                            CIMQualifier('Key', value=True)
                        ]
                    ),
                    CIMProperty('P2', value='Cheese'),
                ]
            ),
            inst_kwargs=None,
            qual_kwargs=None,
        ),
        None, None, True
    ),
    (
        "Test with an instance",
        dict(
            init_args=[False, CIMInstance],
            cls_kwargs=dict(
                classname='CIM_Foo',
                properties=[
                    CIMProperty(
                        'P1', None, type='string',
                        qualifiers=[
                            CIMQualifier('Key', value=True)
                        ]
                    ),
                    CIMProperty('P2', value='Cheese'),
                ]
            ),
            inst_kwargs=dict(
                classname='CIM_Foo',
                properties=[
                    CIMProperty('P1', value='Ham'),
                    CIMProperty('P2', value='Cheese'),
                ]
            ),
            qual_kwargs=None,

        ),
        None, None, True
    ),
    (
        "Test with an qualifier declaration",
        dict(
            init_args=[False, CIMQualifierDeclaration],
            cls_kwargs=None,
            inst_kwargs=None,
            qual_kwargs=dict(
                name='Abstract',
                type='string',
                value='blah'),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_OBJSTORE)
@simplified_test_function
def test_objectstore(testcase, init_args, cls_kwargs, inst_kwargs, qual_kwargs):
    """
    Simple test inserts one inst of defined type and tests retrievail
    methods.
    """
    namespace = "root/cimv2"

    # setup the ObjStore
    xxx_repo = InMemoryObjStore(*init_args)
    if cls_kwargs:
        cls = CIMClass(**cls_kwargs)
    if inst_kwargs:
        inst = CIMInstance(**inst_kwargs)
        inst.path = CIMInstanceName.from_instance(
            cls, inst, namespace=namespace, host='me', strict=True)
    if qual_kwargs:
        qual = CIMQualifierDeclaration(**qual_kwargs)

    # is this instance or class test
    if inst_kwargs:
        name = inst.path
        obj = inst
    elif qual_kwargs:
        name = qual.name
        obj = qual
    else:
        name = cls.classname
        obj = cls

    # The code to be tested. The test include adding and testing the
    # various inspection methods for correct returns

    # Create the object in the object store
    xxx_repo.create(name, obj)

    # confirm that exists works
    assert xxx_repo.exists(name)

    # Test len()
    assert xxx_repo.len() == 1

    # Test get the object and test for same object
    rtn_obj = xxx_repo.get(name)
    assert rtn_obj == obj

    names = [n for n in xxx_repo.iter_names()]
    assert len(names) == 1
    assert names[0] == name

    objs = [x for x in xxx_repo.iter_values()]
    assert len(objs) == 1
    assert objs[0] == obj

    # Test update

    # Test update; should work
    obj2 = obj.copy()
    xxx_repo.update(name, obj2)
    assert xxx_repo.get(name) == obj2

    # Test valid delete of object
    xxx_repo.delete(name)
    assert not xxx_repo.exists(name)
    assert xxx_repo.len() == 0

    # Test errors

    # Test update with unknown object; should fail
    try:
        xxx_repo.update(name, obj)
    except KeyError:
        pass

    # Test delete nonexistent entity; should fail
    try:
        xxx_repo.delete(name)
        assert False
    except KeyError:
        pass

    # Test get non existent entity; should fail
    try:
        xxx_repo.get(name)
        assert False
    except KeyError:
        pass

    # Test exists; entity should not exist
    assert not xxx_repo.exists(name)

    # Test create with existing object
    xxx_repo.create(name, obj)

    # Test duplicate create; should fail
    try:
        xxx_repo.create(name, obj)
        assert False
    except ValueError:
        pass

#############################################################
#
# Test InmemoryRepository
#
#############################################################


@pytest.mark.parametrize(
    "default_ns, additional_ns, test_ns, exp_ns, exp_exc",
    [
        ('root/def', [], 'root/blah', 'root/blah', None),
        ('root/def', [], '//root/blah//', 'root/blah', None),
        ('root/def', ['root/foo'], 'root/blah', 'root/blah', None),
        ('root/def', ['root/blah'], 'root/blah', None,
         ValueError()),
        ('root/def', [], None, 'root/def', ValueError()),
        ('root/def', [], None, None, ValueError()),
    ]
)
def test_add_namespace(default_ns, additional_ns, test_ns, exp_ns, exp_exc):
    # pylint: disable=no-self-use
    """
    Test add_namespace()
    """
    # setup the inmemory repository
    repo = InMemoryRepository(default_ns)
    for ns in additional_ns:
        repo.add_namespace(ns)
    if not exp_exc:
        # The code to be tested
        repo.add_namespace(test_ns)
        assert exp_ns in repo.list_namespaces()
    else:
        with pytest.raises(exp_exc.__class__) as exec_info:

            # The code to be tested
            repo.add_namespace(test_ns)

            print(exec_info)


@pytest.mark.parametrize(
    "default_ns, additional_ns, test_ns, exp_ns, exp_exc",
    [
        ('root/def', ['root/blah'], 'root/blah', 'root/blah', None),
        ('root/def', ['root/blah'], '//root/blah//', 'root/blah', None),
        ('root/def', ['root/blah', 'root/foo'], 'root/blah', 'root/blah',
         None),
        ('root/def', [], 'root/blah', None, KeyError()),
        ('root/def', [], None, None, ValueError()),
    ]
)
def test_remove_namespace(default_ns, additional_ns, test_ns, exp_ns, exp_exc):
    # pylint: disable=no-self-use
    """
    Test _remove_namespace()
    """
    repo = InMemoryRepository(default_ns)
    for ns in additional_ns:
        repo.add_namespace(ns)
    if not exp_exc:

        # The code to be tested
        repo.remove_namespace(test_ns)

        assert exp_ns not in repo.list_namespaces()
    else:
        with pytest.raises(exp_exc.__class__) as exec_info:

            # The code to be tested
            repo.remove_namespace(test_ns)
            print(exec_info)


@pytest.mark.parametrize(
    # Testcases for Inmemory repository object management tests

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * init_args - list of Classes, instances, etc. to populate repo
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger
    "desc, args, condition",
    [
        (
            "Test basic setup of repository and execution of object mgt ",
            dict(
                init_args="root/blah",
                init_objs=[
                    CIMClass('Foo', properties=[
                        CIMProperty('P1', None, type='string',
                                    qualifiers=[CIMQualifier('Key', value=True)]
                                    )]),
                    CIMClass('Bar', properties=[
                        CIMProperty('P2', None, type='string',
                                    qualifiers=[CIMQualifier('Key', value=True)]
                                    )]),
                    CIMInstance('Foo',
                                path=CIMInstanceName(
                                    'Foo',
                                    keybindings=NocaseDict(P1="P1"))),
                    CIMInstance('Bar',
                                path=CIMInstanceName(
                                    'Bar',
                                    keybindings=NocaseDict(P2="P2"))),
                    CIMQualifierDeclaration('Qual1', type='string'),
                    CIMQualifierDeclaration('Qual2', type='string'), ]
            ),
            True,
        ),
    ],
)
def test_repository_valid_methods(desc, args, condition):
    """
    This is a test of the various methods of the repository that return
    valid responses for all of the types
    """
    if not condition:
        pytest.skip("Condition for test case not met")

    init_args = args['init_args']
    init_objs = args['init_objs']

    namespace = init_args

    # setup the inmemory repository
    repo = InMemoryRepository(namespace)
    class_repo = repo.get_class_repo(namespace)
    inst_repo = repo.get_instance_repo(namespace)
    qual_repo = repo.get_qualifier_repo(namespace)

    # Counter of number of objects by type created.
    inst_count = 0
    class_count = 0
    qual_count = 0

    # holding dict for items created in repository by repository name
    input_items = {'classes': {}, 'instances': {}, 'qualifiers': {}}

    # Relate repository names to corresponsing get_xxx_repo function
    repos = {'classes': class_repo, 'instances': inst_repo,
             'qualifiers': qual_repo}

    # Insert the items in init_objs into the repository
    for item in init_objs:
        if isinstance(item, CIMClass):
            class_repo.create(item.classname, item)
            class_count += 1
            input_items['classes'][item.classname] = item
        elif isinstance(item, CIMInstance):
            inst_repo.create(item.path, item)
            inst_count += 1
            input_items['instances'][item.path] = item
        elif isinstance(item, CIMQualifierDeclaration):
            qual_repo.create(item.name, item)
            qual_count += 1
            input_items['qualifiers'][item.name] = item
        else:
            assert False

    #
    #   Execute repository object access methods and verifyresults
    #

    # Test counts of objects in the repository
    assert class_count == len(input_items['classes'])
    assert inst_count == len(input_items['instances'])
    assert qual_count == len(input_items['qualifiers'])

    assert class_repo.len() == class_count
    assert inst_repo.len() == inst_count
    assert qual_repo.len() == qual_count

    # Test exists(), get(), iter_names, iter_values, and delete with with
    # valid names

    print(repo.print())

    for type_dict, obj_dict in input_items.items():
        xxx_repo = repos[type_dict]
        for name, obj in obj_dict.items():
            assert xxx_repo.exists(name), '{} exists() fail {}'.format(desc,
                                                                       name)

            rtnd_obj = xxx_repo.get(name)
            assert rtnd_obj == input_items[type_dict][name]

        # Test iter_names and iter_values
        names = list(xxx_repo.iter_names())
        assert set(names) == set(input_items[type_dict].keys())

        objs = list(xxx_repo.iter_values())
        assert set(objs) == set(input_items[type_dict].values())

        for name, obj in obj_dict.items():
            xxx_repo.delete(name)

    for type_dict, obj_dict in input_items.items():
        xxx_repo = repos[type_dict]
        assert xxx_repo.len() == 0

# TODO: Tests missing: 1) object exception returns, use of copy parameter
#                      2. Namespace name None on add an delete.
#                      3. __repr__
