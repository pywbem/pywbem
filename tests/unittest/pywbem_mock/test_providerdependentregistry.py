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
Test of pywbem_mock.ProviderDependentRegistry.
"""

from __future__ import absolute_import, print_function

import os
import re
import pickle
import pytest

from ..utils.pytest_extensions import simplified_test_function

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
pywbem_mock = import_installed('pywbem_mock')
from pywbem_mock import FakedWBEMConnection  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


def assert_registry_equal(registry1, registry2):
    """
    Assert that two ProviderDependentRegistry objects are equal.

    Structure: self._registry[ms_path] = [dep_paths]
    """
    reg_dict1 = registry1._registry  # pylint: disable=protected-access
    reg_dict2 = registry2._registry  # pylint: disable=protected-access
    assert sorted(reg_dict1.keys()) == sorted(reg_dict2.keys())
    for ms_path in reg_dict1.keys():
        dep_paths1 = reg_dict1[ms_path]
        assert ms_path in reg_dict2
        dep_paths2 = reg_dict2[ms_path]
        assert sorted(dep_paths1) == sorted(dep_paths2)


def create_conn(reg_dict):
    """
    Create and return a FakedWBEMConnection object that has the specified
    dependents registered.

    Parameters:
      reg_dict (dict): Dependents to be registered, with:
        Key (string): Path name of mock script; does not need to be normalized.
        Value (list): List of path names of dependent files; do not need to be
          normalized.
    """
    conn = FakedWBEMConnection()
    for ms_path in reg_dict:
        dep_paths = reg_dict[ms_path]
        conn.provider_dependent_registry.add_dependents(ms_path, dep_paths)
    return conn


def exp_normcwdpath(path):
    """
    Return the input file as if it had been put into the
    ProviderDependentRegistry and retrieved again.

    Parameters:
        path: Path name of file, accessible from current dir.

    Returns:
        Path name of file, accessible from current dir.
    """

    # Must be consistent with ProviderDependentRegistry.add_dependents():
    home_dir = os.path.expanduser('~')
    try:
        normpath = os.path.relpath(path, home_dir)
    except ValueError:
        # On Windows, os.path.relpath() raises ValueError when the paths
        # are on different drives
        normpath = path
    normpath = os.path.normcase(os.path.normpath(normpath))

    # Must be consistent with ProviderDependentRegistry.iter_dependents():
    if os.path.isabs(normpath):
        cwdpath = normpath
    else:
        # If relative, it is always relative to the user's home directory
        cwdpath = os.path.join(home_dir, normpath)
        try:
            cwdpath = os.path.relpath(cwdpath)
        except ValueError:
            # On Windows, os.path.relpath() raises ValueError when the paths
            # are on different drives
            pass
    return cwdpath


TESTCASES_REGISTRY_REPR = [

    # Testcases for ProviderDependentRegistry.__repr__()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * reg_dict: input for ProviderDependentRegistry object
    #   input is specified as a dict with:
    #   - key: Path name of mock script to be registered;
    #     does not need to be normalized.
    #   - value: List of path names of dependent files to be registered;
    #     do not need to be normalized.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Empty registry",
        dict(
            reg_dict={},
        ),
        None, None, True
    ),
    (
        "Registry with one item",
        dict(
            reg_dict={
                'mock1': ['dep1', 'dep2'],
            },
        ),
        None, None, True
    ),
    (
        "Registry with two items",
        dict(
            reg_dict={
                'mock1': ['dep1'],
                'mock2': ['dep2', 'dep3'],
            },
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REGISTRY_REPR)
@simplified_test_function
def test_ProviderDependentRegistry_repr(testcase, reg_dict):
    """
    Test function for ProviderDependentRegistry.__repr__().
    """
    conn = create_conn(reg_dict)
    registry = conn.provider_dependent_registry

    # The code to be tested
    repr_str = repr(registry)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    m = re.match(r"^ProviderDependentRegistry\(registry=(.*)\)$", repr_str)
    assert m is not None
    reg_str = m.group(1)
    for mock_script in reg_dict:
        dependents = reg_dict[mock_script]
        assert mock_script in reg_str
        for dep in dependents:
            assert dep in reg_str


TESTCASES_REGISTRY_ADD_ITER_DEPENDENTS = [

    # Testcases for ProviderDependentRegistry.add_dependents() and
    # iter_dependents()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * mock_script: Path name of mock script be registered;
    #     does not need to be normalized.
    #   * dependents: List of path names of dependent files to be registered;
    #     do not need to be normalized.
    #   * exp_dependents: Expected list of path names of dependent files,
    #     normalized and relative to the current directory.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Registry with no dependents",
        dict(
            mock_script='mock1',
            dependents=[],
            exp_dependents=[],
        ),
        None, None, True
    ),
    (
        "Registry with two dependents, no path",
        dict(
            mock_script='mock1',
            dependents=['dep1', 'dep2'],
            exp_dependents=[
                exp_normcwdpath('dep1'),
                exp_normcwdpath('dep2')
            ],
        ),
        None, None, True
    ),
    (
        "Registry with two dependents, relative path",
        dict(
            mock_script='rel1/mock1',
            dependents=['rel1/dep1', 'rel2/dep2'],
            exp_dependents=[
                exp_normcwdpath('rel1/dep1'),
                exp_normcwdpath('rel2/dep2')
            ],
        ),
        None, None, True
    ),
    (
        "Registry with two dependents, absolute path",
        dict(
            mock_script='/rel1/mock1',
            dependents=['/rel1/dep1', '/rel2/dep2'],
            exp_dependents=[
                exp_normcwdpath('/rel1/dep1'),
                exp_normcwdpath('/rel2/dep2')
            ],
        ),
        None, None, True
    ),
    (
        "Registry with two dependents, unnormalized path",
        dict(
            mock_script='rel1/rel2/../mock1',
            dependents=['rel1/rel2/../dep1', 'rel2/rel3/../dep2'],
            exp_dependents=[
                exp_normcwdpath('rel1/dep1'),
                exp_normcwdpath('rel2/dep2')
            ],
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REGISTRY_ADD_ITER_DEPENDENTS)
@simplified_test_function
def test_ProviderDependentRegistry_add_dependents(
        testcase, mock_script, dependents, exp_dependents):
    """
    Test function for ProviderDependentRegistry.add_dependents() and
    iter_dependents().
    """
    conn = FakedWBEMConnection()
    registry = conn.provider_dependent_registry

    # The code to be tested
    registry.add_dependents(mock_script, dependents)

    # The code to be tested
    res_dependents = list(registry.iter_dependents(mock_script))

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert res_dependents == exp_dependents


TESTCASES_REGISTRY_LOAD = [

    # Testcases for ProviderDependentRegistry.load()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * reg_dict1: input for ProviderDependentRegistry object #1
    #   * reg_dict2: input for ProviderDependentRegistry object #2
    #   input is specified as a dict with:
    #   - key: Path name of mock script to be registered;
    #     does not need to be normalized.
    #   - value: List of path names of dependent files to be registered;
    #     do not need to be normalized.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Empty registry loaded with empty registry",
        dict(
            reg_dict1={},
            reg_dict2={},
        ),
        None, None, True
    ),
    (
        "Empty registry loaded with registry with one item",
        dict(
            reg_dict1={},
            reg_dict2={
                'mock1': ['dep1'],
            },
        ),
        None, None, True
    ),
    (
        "Registry with one item loaded with empty registry",
        dict(
            reg_dict1={
                'mock1': ['dep1'],
            },
            reg_dict2={},
        ),
        None, None, True
    ),
    (
        "Registry with one item loaded with registry with same key",
        dict(
            reg_dict1={
                'mock1': ['dep1'],
            },
            reg_dict2={
                'mock1': ['dep2'],
            },
        ),
        None, None, True
    ),
    (
        "Registry with one item loaded with registry with different key",
        dict(
            reg_dict1={
                'mock1': ['dep1'],
            },
            reg_dict2={
                'mock2': ['dep2'],
            },
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REGISTRY_LOAD)
@simplified_test_function
def test_ProviderDependentRegistry_load(testcase, reg_dict1, reg_dict2):
    """
    Test function for ProviderDependentRegistry.load().
    """
    conn1 = create_conn(reg_dict1)
    registry1 = conn1.provider_dependent_registry

    conn2 = create_conn(reg_dict2)
    registry2 = conn2.provider_dependent_registry

    # The code to be tested
    registry1.load(registry2)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert_registry_equal(registry1, registry2)


TESTCASES_REGISTRY_PICKLE = [

    # Testcases for pickling and unpickling ProviderDependentRegistry objects

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * reg_dict: input for ProviderDependentRegistry object
    #   input is specified as a dict with:
    #   - key: Path name of mock script to be registered;
    #     does not need to be normalized.
    #   - value: List of path names of dependent files to be registered;
    #     do not need to be normalized.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Empty registry",
        dict(
            reg_dict={},
        ),
        None, None, True
    ),
    (
        "Registry with one item",
        dict(
            reg_dict={
                'mock1': ['dep1', 'dep2'],
            },
        ),
        None, None, True
    ),
    (
        "Registry with two items",
        dict(
            reg_dict={
                'mock1': ['dep1'],
                'mock2': ['dep2', 'dep3'],
            },
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REGISTRY_PICKLE)
@simplified_test_function
def test_ProviderDependentRegistry_pickle(testcase, reg_dict):
    """
    Test function for pickling and unpickling ProviderDependentRegistry objects.
    """
    conn = create_conn(reg_dict)
    registry = conn.provider_dependent_registry

    # Pickle the object
    pkl = pickle.dumps(registry)

    # Unpickle the object
    registry2 = pickle.loads(pkl)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert_registry_equal(registry2, registry)
