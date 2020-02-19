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

from pywbem_mock import InMemoryRepository
from pywbem_mock._inmemoryrepository import InMemoryObjStore

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
        ('root/def', ['root/blah'], 'root/blah', None, ValueError()),
        (None, ['root/foo'], 'root/blah', 'root/blah', None),
        ('root/def', [], None, 'root/def', ValueError()),
        ('root/def', [], None, None, ValueError()),
    ]
)
def test_add_namespace(default_ns, additional_ns, test_ns, exp_ns, exp_exc):
    # pylint: disable=no-self-use
    """
    Test add_namespace() and the namespaces property
    """
    # setup the inmemory repository
    repo = InMemoryRepository(default_ns)
    for ns in additional_ns:
        repo.add_namespace(ns)
    if not exp_exc:
        # The code to be tested
        repo.add_namespace(test_ns)
        assert isinstance(repo.namespaces, list)
        assert exp_ns in repo.namespaces
        for ns in additional_ns:
            assert ns in repo.namespaces
        if default_ns:
            assert default_ns in repo.namespaces

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

        assert exp_ns not in repo.namespaces
    else:
        with pytest.raises(exp_exc.__class__) as exec_info:

            # The code to be tested
            repo.remove_namespace(test_ns)
            print(exec_info)


TEST_OBJECTS = [
    CIMClass('Foo', properties=[
        CIMProperty('P1', None, type='string',
                    qualifiers=[CIMQualifier('Key', value=True)])]),
    CIMClass('Bar', properties=[
        CIMProperty('P2', None, type='string',
                    qualifiers=[CIMQualifier('Key', value=True)])]),
    CIMInstance('Foo', path=CIMInstanceName('Foo',
                                            keybindings=NocaseDict(P1="P1"))),
    CIMInstance('Bar', path=CIMInstanceName('Bar',
                                            keybindings=NocaseDict(P2="P2"))),
    CIMQualifierDeclaration('Qual1', type='string'),
    CIMQualifierDeclaration('Qual2', type='string'), ]


@pytest.mark.parametrize(
    # Testcases for Inmemory repository object management tests

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * init_args - list of Classes, instances, etc. to populate repo
    # * init_objs - list of CIM objects that will be used to initialize the
    #   repository when it is created.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger
    "desc, args, condition",
    [
        (
            "Test basic setup of repository and execution of object mgt ",
            dict(
                init_args="root/blah",
                init_objs=TEST_OBJECTS
            ),
            True,
        ),
    ],
)
def test_repository_valid_methods(desc, args, condition, capsys):
    """
    This is a test of the various methods of the repository that return
    valid responses for all of the types. This test create, update,
    get, delete and inter* methods of the object store as accessed through
    the InMemoryRepository for good responses. It does not test exception
    responses.
    """
    if not condition:
        pytest.skip("Condition for test case not met")

    init_args = args['init_args']
    init_objs = args['init_objs']

    namespace = init_args

    # setup the inmemory repository and the methods that provide access to
    # the repository for each object type
    repo = InMemoryRepository(initial_namespace=namespace)

    class_repo = repo.get_class_repo(namespace)
    inst_repo = repo.get_instance_repo(namespace)
    qual_repo = repo.get_qualifier_repo(namespace)

    # Holding dict for items created in repository by repository name
    input_items = {'classes': {}, 'instances': {}, 'qualifiers': {}}

    # Relate repository names to corresponsing get_xxx_repo function
    repos = {'classes': repo.get_class_repo(namespace),
             'instances': repo.get_instance_repo(namespace),
             'qualifiers': repo.get_qualifier_repo(namespace)}

    # Insert the items in init_objs into the repository
    # Counter of number of objects by type created.
    inst_count = 0
    class_count = 0
    qual_count = 0
    for item in init_objs:
        if isinstance(item, CIMClass):
            class_repo = repos['classes']
            class_repo.create(item.classname, item)
            class_count += 1
            input_items['classes'][item.classname] = item
        elif isinstance(item, CIMInstance):
            inst_repo = repos['instances']
            inst_repo.create(item.path, item)
            inst_count += 1
            input_items['instances'][item.path] = item
        elif isinstance(item, CIMQualifierDeclaration):
            qual_repo = repos['qualifiers']
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

    # verify the print_repository returns correct data
    print(repo.print_repository())
    captured = capsys.readouterr()

    result = captured.out
    assert "QUALIFIERS: Namespace: root/blah Repo: qualifier len:2" in result
    assert "CLASSES: Namespace: root/blah Repo: class len:2" in result
    assert "INSTANCES: Namespace: root/blah Repo: instance len:2" in result

    # Test exists(), get(), iter_names, iter_values, and delete with with
    # valid names

    # Verify the correct response for each objstore
    for type_dict, obj_dict in input_items.items():
        xxx_repo = repos[type_dict]
        for name, obj in obj_dict.items():
            assert xxx_repo.exists(name), '{} exists() fail {}'.format(desc,
                                                                       name)

            rtnd_obj = xxx_repo.get(name)
            assert rtnd_obj == input_items[type_dict][name]

            # update each object with the same object as originally installed.
            xxx_repo.update(name, obj)

        # test obj store repr
        print(repr(xxx_repo))
        captured = capsys.readouterr()
        result = captured.out
        assert "InMemoryObjStore(" in result
        assert "size=2" in result

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


@pytest.mark.parametrize(
    # Testcases for Inmemory repository object management tests

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * init_args - list of Classes, instances, etc. to populate repo
    # * init_objs - list of CIM objects that will be used to initialize the
    #   repository when it is created.
    # * err_names - Object names that should return exception for
    #   get and delete based on init_objs. These are objects not in the
    #   repository so they can not be retrievied, deleted, or updated
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger
    "desc, args, condition",
    [
        (
            "Test basic setup of repository and execution of object mgt ",
            dict(
                init_args="root/blah",
                init_objs=TEST_OBJECTS,
                err_names={'classes': 'CIM_NotExist',
                           'instances': CIMInstanceName(
                               'NotExist', keybindings=NocaseDict(P1="P1")),
                           'qualifiers': 'NotExist'},
                valid_names={'classes': 'Foo',
                             'instances': CIMInstanceName(
                                 'Foo', keybindings=NocaseDict(P1="P1")),
                             'qualifiers': 'Qual1'},
                valid_objs={'classes': 'Foo',
                            'instances': CIMInstanceName(
                                'Foo', keybindings=NocaseDict(P1="P1")),
                            'qualifiers': 'Qual1'},
            ),
            True,
        ),
    ],
)
def test_repository_method_errs(desc, args, condition, capsys):
    """
    This is a test of the various methods of the repository that return
    valid responses for all of the types. This test create, update,
    get, delete and inter* methods of the object store as accessed through
    the InMemoryRepository for good responses. It does not test exception
    responses.
    """
    if not condition:
        pytest.skip("Condition for test case not met")

    init_args = args['init_args']
    init_objs = args['init_objs']
    err_names = args['err_names']
    valid_names = args['valid_names']

    namespace = init_args

    # setup the inmemory repository and the methods that provide access to
    # the repository for each object type
    repo = InMemoryRepository(namespace)

    # Relate repository names to corresponsing get_xxx_repo function
    repos = {'classes': repo.get_class_repo(namespace),
             'instances': repo.get_instance_repo(namespace),
             'qualifiers': repo.get_qualifier_repo(namespace)}

    for item in init_objs:
        if isinstance(item, CIMClass):
            class_repo = repos['classes']
            class_repo.create(item.classname, item)
        elif isinstance(item, CIMInstance):
            inst_repo = repos['instances']
            inst_repo.create(item.path, item)
        elif isinstance(item, CIMQualifierDeclaration):
            qual_repo = repos['qualifiers']
            qual_repo.create(item.name, item)
        else:
            assert False

    for repo_name, xxx_repo in repos.items():
        err_name = err_names[repo_name]
        valid_name = valid_names[repo_name]
        try:
            xxx_repo.get(err_name)
            assert False, "get should return exception"
        except KeyError:
            pass

        try:
            xxx_repo.delete(err_name)
            assert False, "delete Exception failed {} {}"
        except KeyError:
            pass

        # Try to get object from repo and create it.
        try:
            obj = xxx_repo.get(valid_name)
            obj = xxx_repo.create(valid_name, obj)
        except ValueError:
            pass

        # Try to get object from repo and update it with err_name.
        # NOTE: this works because repo does not validate names against
        # objects on create or update.
        try:
            obj = xxx_repo.get(valid_name)
            obj = xxx_repo.update(err_name, obj)
        except KeyError:
            pass


# TODO: Tests missing: 1) use of copy parameter
#                      2. Namespace name None on add an delete.
