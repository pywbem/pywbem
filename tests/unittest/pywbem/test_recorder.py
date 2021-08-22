"""
Unit tests for the recorder functions (_recorder.py module).
"""

from __future__ import absolute_import, print_function

# Allows use of lots of single character variable names.
# pylint: disable=invalid-name,missing-docstring,too-many-statements
# pylint: disable=too-many-lines,no-self-use
import sys
import os
import io
import logging
import logging.handlers
import warnings
from datetime import datetime, timedelta
try:
    from collections.abc import Mapping
except ImportError:
    # pylint: disable=deprecated-class
    from collections import Mapping

import pytest
import six
from testfixtures import LogCapture
# Enabled only to display a tree of loggers
# from logging_tree import printout as logging_tree_printout
import yaml
import yamlloader
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

from ...utils import skip_if_moftab_regenerated, is_inherited_from
from ..utils.dmtf_mof_schema_def import install_test_dmtf_schema
from ..utils.pytest_extensions import simplified_test_function
from ..utils.unittest_extensions import assert_copy

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import CIMInstanceName, CIMInstance, CIMClassName, CIMClass, \
    CIMProperty, CIMMethod, CIMParameter, CIMQualifier, \
    CIMQualifierDeclaration, \
    Uint8, Uint16, Uint32, Uint64, Sint8, Sint16, \
    Sint32, Sint64, Real32, Real64, CIMDateTime, MinutesFromUTC, CIMError, \
    HTTPError, WBEMConnection, LogOperationRecorder, BaseOperationRecorder, \
    configure_logger  # noqa: E402
# Renamed the following import to not have py.test pick it up as a test class:
from pywbem import TestClientRecorder as _TestClientRecorder  # noqa: E402
from pywbem._cim_operations import pull_path_result_tuple, \
    pull_inst_result_tuple  # noqa: E402
from pywbem._utils import _format  # noqa: E402
pywbem_mock = import_installed('pywbem_mock')
from pywbem_mock import FakedWBEMConnection  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name

# Ordered dict type created by yamlloader.ordereddict loaders
if sys.version_info[0:2] >= (3, 7):
    yaml_ordereddict = dict  # pylint: disable=invalid-name
else:
    yaml_ordereddict = OrderedDict  # pylint: disable=invalid-name

# Name of null device
DEV_NULL = 'nul' if sys.platform == 'win32' else '/dev/null'

TEST_DIR = os.path.dirname(__file__)

# test outpuf file for the recorder tests.  This is opened for each
# test to save yaml output and may be reloaded during the same test
# to confirm the yaml results.
TEST_YAML_FILE = os.path.join(TEST_DIR, 'test_recorder.yaml')

TEST_OUTPUT_LOG = os.path.join(TEST_DIR, 'test_recorder.log')

VERBOSE = False
DEBUG_TEST_YAML_FILE = False  # Show the generated test client YAML file


# CIMProperty objects of all types and the corresponding test client YAML
CIMPROPERTY_B1_OBJ = CIMProperty('B1', value=True)
CIMPROPERTY_B1_TCYAML = dict(
    pywbem_object='CIMProperty',
    name=u'B1',
    type=u'boolean',
    value=True,
    reference_class=None,
    embedded_object=None,
    is_array=False,
    array_size=None,
    class_origin=None,
    propagated=None,
    qualifiers=yaml_ordereddict(),
)
CIMPROPERTY_C1_OBJ = CIMProperty('C1', type='char16', value=u'A')
CIMPROPERTY_C1_TCYAML = dict(
    pywbem_object='CIMProperty',
    name=u'C1',
    type=u'char16',
    value=u'A',
    reference_class=None,
    embedded_object=None,
    is_array=False,
    array_size=None,
    class_origin=None,
    propagated=None,
    qualifiers=yaml_ordereddict(),
)
CIMPROPERTY_C2_OBJ = CIMProperty('C2', type='char16', value=u'\u00E4')
CIMPROPERTY_C2_TCYAML = dict(
    pywbem_object='CIMProperty',
    name=u'C2',
    type=u'char16',
    value=u'\u00E4',
    reference_class=None,
    embedded_object=None,
    is_array=False,
    array_size=None,
    class_origin=None,
    propagated=None,
    qualifiers=yaml_ordereddict(),
)
# Note that the value space of the char16 datatype is UCS-2
CIMPROPERTY_S1_OBJ = CIMProperty('S1', type='string', value=u'Ham')
CIMPROPERTY_S1_TCYAML = dict(
    pywbem_object='CIMProperty',
    name=u'S1',
    type=u'string',
    value=u'Ham',
    reference_class=None,
    embedded_object=None,
    is_array=False,
    array_size=None,
    class_origin=None,
    propagated=None,
    qualifiers=yaml_ordereddict(),
)
CIMPROPERTY_S2_OBJ = CIMProperty('S2', type='string', value=u'H\u00E4m')
CIMPROPERTY_S2_TCYAML = dict(
    pywbem_object='CIMProperty',
    name=u'S2',
    type=u'string',
    value=u'H\u00E4m',
    reference_class=None,
    embedded_object=None,
    is_array=False,
    array_size=None,
    class_origin=None,
    propagated=None,
    qualifiers=yaml_ordereddict(),
)
CIMPROPERTY_S3_OBJ = CIMProperty('S3', type='string', value=u'A\U00010142B')
CIMPROPERTY_S3_TCYAML = dict(
    pywbem_object='CIMProperty',
    name=u'S3',
    type=u'string',
    value=u'A\U00010142B',
    reference_class=None,
    embedded_object=None,
    is_array=False,
    array_size=None,
    class_origin=None,
    propagated=None,
    qualifiers=yaml_ordereddict(),
)
CIMPROPERTY_E1_OBJ = CIMProperty('E1', type='string',
                                 embedded_object='instance',
                                 value=CIMInstance('C_Emb'))
CIMPROPERTY_E1_TCYAML = dict(
    pywbem_object='CIMProperty',
    name=u'E1',
    type=u'string',
    value=dict(
        pywbem_object='CIMInstance',
        classname='C_Emb',
        properties=yaml_ordereddict(),
        qualifiers=yaml_ordereddict(),
        path=None,
    ),
    reference_class=None,
    embedded_object=u'instance',
    is_array=False,
    array_size=None,
    class_origin=None,
    propagated=None,
    qualifiers=yaml_ordereddict(),
)
CIMPROPERTY_E2_OBJ = CIMProperty('E2', type='string',
                                 embedded_object='object',
                                 value=CIMInstance('C_Emb'))
CIMPROPERTY_E2_TCYAML = dict(
    pywbem_object='CIMProperty',
    name=u'E2',
    type=u'string',
    value=dict(
        pywbem_object='CIMInstance',
        classname='C_Emb',
        properties=yaml_ordereddict(),
        qualifiers=yaml_ordereddict(),
        path=None,
    ),
    reference_class=None,
    embedded_object=u'object',
    is_array=False,
    array_size=None,
    class_origin=None,
    propagated=None,
    qualifiers=yaml_ordereddict(),
)
CIMPROPERTY_E3_OBJ = CIMProperty('E3', type='string',
                                 embedded_object='object',
                                 value=CIMClass('C_Emb'))
CIMPROPERTY_E3_TCYAML = dict(
    pywbem_object='CIMProperty',
    name=u'E3',
    type=u'string',
    value=dict(
        pywbem_object='CIMClass',
        classname='C_Emb',
        superclass=None,
        properties=yaml_ordereddict(),
        methods=yaml_ordereddict(),
        qualifiers=yaml_ordereddict(),
        path=None,
    ),
    reference_class=None,
    embedded_object=u'object',
    is_array=False,
    array_size=None,
    class_origin=None,
    propagated=None,
    qualifiers=yaml_ordereddict(),
)
CIMPROPERTY_U11_OBJ = CIMProperty('U11', value=Uint8(42))
CIMPROPERTY_U11_TCYAML = dict(
    pywbem_object='CIMProperty',
    name=u'U11',
    type=u'uint8',
    value=42,
    reference_class=None,
    embedded_object=None,
    is_array=False,
    array_size=None,
    class_origin=None,
    propagated=None,
    qualifiers=yaml_ordereddict(),
)
CIMPROPERTY_U21_OBJ = CIMProperty('U21', value=Uint16(4216))
CIMPROPERTY_U21_TCYAML = dict(
    pywbem_object='CIMProperty',
    name=u'U21',
    type=u'uint16',
    value=4216,
    reference_class=None,
    embedded_object=None,
    is_array=False,
    array_size=None,
    class_origin=None,
    propagated=None,
    qualifiers=yaml_ordereddict(),
)
CIMPROPERTY_U41_OBJ = CIMProperty('U41', value=Uint32(4232))
CIMPROPERTY_U41_TCYAML = dict(
    pywbem_object='CIMProperty',
    name=u'U41',
    type=u'uint32',
    value=4232,
    reference_class=None,
    embedded_object=None,
    is_array=False,
    array_size=None,
    class_origin=None,
    propagated=None,
    qualifiers=yaml_ordereddict(),
)
CIMPROPERTY_U81_OBJ = CIMProperty('U81', value=Uint64(4264))
CIMPROPERTY_U81_TCYAML = dict(
    pywbem_object='CIMProperty',
    name=u'U81',
    type=u'uint64',
    value=4264,
    reference_class=None,
    embedded_object=None,
    is_array=False,
    array_size=None,
    class_origin=None,
    propagated=None,
    qualifiers=yaml_ordereddict(),
)
CIMPROPERTY_S11_OBJ = CIMProperty('S11', value=Sint8(-42))
CIMPROPERTY_S11_TCYAML = dict(
    pywbem_object='CIMProperty',
    name=u'S11',
    type=u'sint8',
    value=-42,
    reference_class=None,
    embedded_object=None,
    is_array=False,
    array_size=None,
    class_origin=None,
    propagated=None,
    qualifiers=yaml_ordereddict(),
)
CIMPROPERTY_S21_OBJ = CIMProperty('S21', value=Sint16(-4216))
CIMPROPERTY_S21_TCYAML = dict(
    pywbem_object='CIMProperty',
    name=u'S21',
    type=u'sint16',
    value=-4216,
    reference_class=None,
    embedded_object=None,
    is_array=False,
    array_size=None,
    class_origin=None,
    propagated=None,
    qualifiers=yaml_ordereddict(),
)
CIMPROPERTY_S41_OBJ = CIMProperty('S41', value=Sint32(-4232))
CIMPROPERTY_S41_TCYAML = dict(
    pywbem_object='CIMProperty',
    name=u'S41',
    type=u'sint32',
    value=-4232,
    reference_class=None,
    embedded_object=None,
    is_array=False,
    array_size=None,
    class_origin=None,
    propagated=None,
    qualifiers=yaml_ordereddict(),
)
CIMPROPERTY_S81_OBJ = CIMProperty('S81', value=Sint64(-4264))
CIMPROPERTY_S81_TCYAML = dict(
    pywbem_object='CIMProperty',
    name=u'S81',
    type=u'sint64',
    value=-4264,
    reference_class=None,
    embedded_object=None,
    is_array=False,
    array_size=None,
    class_origin=None,
    propagated=None,
    qualifiers=yaml_ordereddict(),
)
CIMPROPERTY_R41_OBJ = CIMProperty('R41', value=Real32(42.0))
CIMPROPERTY_R41_TCYAML = dict(
    pywbem_object='CIMProperty',
    name=u'R41',
    type=u'real32',
    value=42.0,
    reference_class=None,
    embedded_object=None,
    is_array=False,
    array_size=None,
    class_origin=None,
    propagated=None,
    qualifiers=yaml_ordereddict(),
)
CIMPROPERTY_R81_OBJ = CIMProperty('R81', value=Real64(42.64))
CIMPROPERTY_R81_TCYAML = dict(
    pywbem_object='CIMProperty',
    name=u'R81',
    type=u'real64',
    value=42.64,
    reference_class=None,
    embedded_object=None,
    is_array=False,
    array_size=None,
    class_origin=None,
    propagated=None,
    qualifiers=yaml_ordereddict(),
)
CIMPROPERTY_R1_OBJ = CIMProperty('R1', value=CIMInstanceName('C1'))
CIMPROPERTY_R1_TCYAML = dict(
    pywbem_object='CIMProperty',
    name=u'R1',
    type=u'reference',
    value=dict(
        pywbem_object='CIMInstanceName',
        classname='C1',
        keybindings=yaml_ordereddict(),
        namespace=None,
        host=None,
    ),
    reference_class=None,
    embedded_object=None,
    is_array=False,
    array_size=None,
    class_origin=None,
    propagated=None,
    qualifiers=yaml_ordereddict(),
)
CIMPROPERTY_D1_OBJ = CIMProperty(
    'D1',
    value=CIMDateTime('20140924193040.654321+120'))
CIMPROPERTY_D1_TCYAML = dict(
    pywbem_object='CIMProperty',
    name=u'D1',
    type=u'datetime',
    value=u'20140924193040.654321+120',
    reference_class=None,
    embedded_object=None,
    is_array=False,
    array_size=None,
    class_origin=None,
    propagated=None,
    qualifiers=yaml_ordereddict(),
)

# CIMInstance object without path, with all property types and the test client
# YAML object
CIMINSTANCE_ALL_OBJ = CIMInstance(
    'CIM_Foo',
    properties=[
        CIMPROPERTY_B1_OBJ,
        CIMPROPERTY_C1_OBJ,
        CIMPROPERTY_C2_OBJ,
        CIMPROPERTY_S1_OBJ,
        CIMPROPERTY_S2_OBJ,
        CIMPROPERTY_S3_OBJ,
        CIMPROPERTY_E1_OBJ,
        CIMPROPERTY_E2_OBJ,
        CIMPROPERTY_E3_OBJ,
        CIMPROPERTY_U11_OBJ,
        CIMPROPERTY_U21_OBJ,
        CIMPROPERTY_U41_OBJ,
        CIMPROPERTY_U81_OBJ,
        CIMPROPERTY_S11_OBJ,
        CIMPROPERTY_S21_OBJ,
        CIMPROPERTY_S41_OBJ,
        CIMPROPERTY_S81_OBJ,
        CIMPROPERTY_R41_OBJ,
        CIMPROPERTY_R81_OBJ,
        CIMPROPERTY_R1_OBJ,
        CIMPROPERTY_D1_OBJ,
    ],
    path=None,
)
CIMINSTANCE_ALL_TCYAML = yaml_ordereddict([
    ('pywbem_object', 'CIMInstance'),
    ('classname', 'CIM_Foo'),
    ('properties', yaml_ordereddict([
        ('B1', CIMPROPERTY_B1_TCYAML),
        ('C1', CIMPROPERTY_C1_TCYAML),
        ('C2', CIMPROPERTY_C2_TCYAML),
        ('S1', CIMPROPERTY_S1_TCYAML),
        ('S2', CIMPROPERTY_S2_TCYAML),
        ('S3', CIMPROPERTY_S3_TCYAML),
        ('E1', CIMPROPERTY_E1_TCYAML),
        ('E2', CIMPROPERTY_E2_TCYAML),
        ('E3', CIMPROPERTY_E3_TCYAML),
        ('U11', CIMPROPERTY_U11_TCYAML),
        ('U21', CIMPROPERTY_U21_TCYAML),
        ('U41', CIMPROPERTY_U41_TCYAML),
        ('U81', CIMPROPERTY_U81_TCYAML),
        ('S11', CIMPROPERTY_S11_TCYAML),
        ('S21', CIMPROPERTY_S21_TCYAML),
        ('S41', CIMPROPERTY_S41_TCYAML),
        ('S81', CIMPROPERTY_S81_TCYAML),
        ('R41', CIMPROPERTY_R41_TCYAML),
        ('R81', CIMPROPERTY_R81_TCYAML),
        ('R1', CIMPROPERTY_R1_TCYAML),
        ('D1', CIMPROPERTY_D1_TCYAML),
    ])),
    ('qualifiers', yaml_ordereddict()),
    ('path', None),
])

# CIMInstance object without path, with one property and the test client
# YAML object
CIMINSTANCE_ONE_OBJ = CIMInstance(
    'CIM_Foo',
    properties=[
        CIMPROPERTY_S1_OBJ,
    ],
    path=None,
)
CIMINSTANCE_ONE_TCYAML = yaml_ordereddict([
    ('pywbem_object', 'CIMInstance'),
    ('classname', 'CIM_Foo'),
    ('properties', yaml_ordereddict([
        ('S1', CIMPROPERTY_S1_TCYAML),
    ])),
    ('qualifiers', yaml_ordereddict()),
    ('path', None),
])


@pytest.fixture(params=[
    (CIMINSTANCE_ALL_OBJ, CIMINSTANCE_ALL_TCYAML),
], scope='module')
def instance_tuple(request):
    """
    Fixture for a CIMInstance object without path and its corresponding
    test client YAML object.

    Returns a tuple(CIMInstance, tcyaml_dict).
    """
    return request.param


# CIMInstance object with path, with all property types and the test client
# YAML object
CIMINSTANCE_WP_ALL_OBJ = CIMInstance(
    'CIM_Foo',
    properties=[
        CIMPROPERTY_B1_OBJ,
        CIMPROPERTY_C1_OBJ,
        CIMPROPERTY_C2_OBJ,
        CIMPROPERTY_S1_OBJ,
        CIMPROPERTY_S2_OBJ,
        CIMPROPERTY_S3_OBJ,
        CIMPROPERTY_E1_OBJ,
        CIMPROPERTY_E2_OBJ,
        CIMPROPERTY_E3_OBJ,
        CIMPROPERTY_U11_OBJ,
        CIMPROPERTY_U21_OBJ,
        CIMPROPERTY_U41_OBJ,
        CIMPROPERTY_U81_OBJ,
        CIMPROPERTY_S11_OBJ,
        CIMPROPERTY_S21_OBJ,
        CIMPROPERTY_S41_OBJ,
        CIMPROPERTY_S81_OBJ,
        CIMPROPERTY_R41_OBJ,
        CIMPROPERTY_R81_OBJ,
        CIMPROPERTY_R1_OBJ,
        CIMPROPERTY_D1_OBJ,
    ],
    path=CIMInstanceName(
        'CIM_Foo',
        keybindings=dict(S1=CIMPROPERTY_S1_OBJ.value),
        namespace='root/cimv2',
        host='woot.com',
    ),
)
CIMINSTANCE_WP_ALL_TCYAML = yaml_ordereddict([
    ('pywbem_object', 'CIMInstance'),
    ('classname', 'CIM_Foo'),
    ('properties', yaml_ordereddict([
        ('B1', CIMPROPERTY_B1_TCYAML),
        ('C1', CIMPROPERTY_C1_TCYAML),
        ('C2', CIMPROPERTY_C2_TCYAML),
        ('S1', CIMPROPERTY_S1_TCYAML),
        ('S2', CIMPROPERTY_S2_TCYAML),
        ('S3', CIMPROPERTY_S3_TCYAML),
        ('E1', CIMPROPERTY_E1_TCYAML),
        ('E2', CIMPROPERTY_E2_TCYAML),
        ('E3', CIMPROPERTY_E3_TCYAML),
        ('U11', CIMPROPERTY_U11_TCYAML),
        ('U21', CIMPROPERTY_U21_TCYAML),
        ('U41', CIMPROPERTY_U41_TCYAML),
        ('U81', CIMPROPERTY_U81_TCYAML),
        ('S11', CIMPROPERTY_S11_TCYAML),
        ('S21', CIMPROPERTY_S21_TCYAML),
        ('S41', CIMPROPERTY_S41_TCYAML),
        ('S81', CIMPROPERTY_S81_TCYAML),
        ('R41', CIMPROPERTY_R41_TCYAML),
        ('R81', CIMPROPERTY_R81_TCYAML),
        ('R1', CIMPROPERTY_R1_TCYAML),
        ('D1', CIMPROPERTY_D1_TCYAML),
    ])),
    ('qualifiers', yaml_ordereddict()),
    ('path', yaml_ordereddict([
        ('pywbem_object', 'CIMInstanceName'),
        ('classname', 'CIM_Foo'),
        ('keybindings', dict(S1=CIMPROPERTY_S1_TCYAML['value'])),
        ('namespace', 'root/cimv2'),
        ('host', 'woot.com'),
    ])),
])


@pytest.fixture(params=[
    (CIMINSTANCE_WP_ALL_OBJ, CIMINSTANCE_WP_ALL_TCYAML),
], scope='module')
def instance_wp_tuple(request):
    """
    Fixture for a CIMInstance object with path and its corresponding
    test client YAML object.

    Returns a tuple(CIMInstance, tcyaml_dict).
    """
    return request.param


# Two CIMInstance objects without path and the test client YAML object
CIMINSTANCES_OBJS = [
    CIMInstance(
        'CIM_Foo',
        properties=[
            CIMPROPERTY_S1_OBJ,
            CIMPROPERTY_S2_OBJ,
        ],
        path=None,
    ),
    CIMInstance(
        'CIM_Foo',
        properties=[
            CIMPROPERTY_S3_OBJ,
        ],
        path=None,
    ),
]
CIMINSTANCES_TCYAML = [
    yaml_ordereddict([
        ('pywbem_object', 'CIMInstance'),
        ('classname', 'CIM_Foo'),
        ('properties', yaml_ordereddict([
            ('S1', CIMPROPERTY_S1_TCYAML),
            ('S2', CIMPROPERTY_S2_TCYAML),
        ])),
        ('qualifiers', yaml_ordereddict()),
        ('path', None),
    ]),
    yaml_ordereddict([
        ('pywbem_object', 'CIMInstance'),
        ('classname', 'CIM_Foo'),
        ('properties', yaml_ordereddict([
            ('S3', CIMPROPERTY_S3_TCYAML),
        ])),
        ('qualifiers', yaml_ordereddict()),
        ('path', None),
    ]),
]


@pytest.fixture(params=[
    (CIMINSTANCES_OBJS, CIMINSTANCES_TCYAML),
], scope='module')
def instances_tuple(request):
    """
    Fixture for a list of two CIMInstance objects without path and its
    corresponding test client YAML object.

    Returns a tuple(list(CIMInstance), tcyaml_dict).
    """
    return request.param


# Two CIMInstance objects with path and the test client YAML object
CIMINSTANCES_WP_OBJS = [
    CIMInstance(
        'CIM_Foo',
        properties=[
            CIMPROPERTY_S1_OBJ,
            CIMPROPERTY_S2_OBJ,
        ],
        path=CIMInstanceName(
            'CIM_Foo',
            keybindings=dict(S1=CIMPROPERTY_S1_OBJ.value),
            namespace='root/cimv2',
            host='woot.com',
        ),
    ),
    CIMInstance(
        'CIM_Foo',
        properties=[
            CIMPROPERTY_S1_OBJ,
            CIMPROPERTY_S3_OBJ,
        ],
        path=CIMInstanceName(
            'CIM_Foo',
            keybindings=dict(S1=CIMPROPERTY_S1_OBJ.value),
            namespace='root/cimv2',
            host='woot.com',
        ),
    ),
]
CIMINSTANCES_WP_TCYAML = [
    yaml_ordereddict([
        ('pywbem_object', 'CIMInstance'),
        ('classname', 'CIM_Foo'),
        ('properties', yaml_ordereddict([
            ('S1', CIMPROPERTY_S1_TCYAML),
            ('S2', CIMPROPERTY_S2_TCYAML),
        ])),
        ('qualifiers', yaml_ordereddict()),
        ('path', yaml_ordereddict([
            ('pywbem_object', 'CIMInstanceName'),
            ('classname', 'CIM_Foo'),
            ('keybindings', dict(S1=CIMPROPERTY_S1_TCYAML['value'])),
            ('namespace', 'root/cimv2'),
            ('host', 'woot.com'),
        ])),
    ]),
    yaml_ordereddict([
        ('pywbem_object', 'CIMInstance'),
        ('classname', 'CIM_Foo'),
        ('properties', yaml_ordereddict([
            ('S1', CIMPROPERTY_S1_TCYAML),
            ('S3', CIMPROPERTY_S3_TCYAML),
        ])),
        ('qualifiers', yaml_ordereddict()),
        ('path', yaml_ordereddict([
            ('pywbem_object', 'CIMInstanceName'),
            ('classname', 'CIM_Foo'),
            ('keybindings', dict(S1=CIMPROPERTY_S1_TCYAML['value'])),
            ('namespace', 'root/cimv2'),
            ('host', 'woot.com'),
        ])),
    ]),
]


@pytest.fixture(params=[
    (CIMINSTANCES_WP_OBJS, CIMINSTANCES_WP_TCYAML),
], scope='module')
def instances_wp_tuple(request):
    """
    Fixture for a list of two CIMInstance objects with path and its
    corresponding test client YAML object.

    Returns a tuple(list(CIMInstance), tcyaml_dict).
    """
    return request.param


# CIMInstanceName object and the test client YAML object
CIMINSTANCENAME_OBJ = CIMInstanceName(
    'CIM_Foo',
    keybindings=dict(S1='a'),
    namespace='root/cimv2',
    host='woot.com',
)
CIMINSTANCENAME_TCYAML = yaml_ordereddict([
    ('pywbem_object', 'CIMInstanceName'),
    ('classname', 'CIM_Foo'),
    ('keybindings', dict(S1='a')),
    ('namespace', 'root/cimv2'),
    ('host', 'woot.com'),
])


@pytest.fixture(params=[
    (CIMINSTANCENAME_OBJ, CIMINSTANCENAME_TCYAML),
], scope='module')
def instancename_tuple(request):
    """
    Fixture for a CIMInstanceName object and its corresponding
    test client YAML object.

    Returns a tuple(CIMInstanceName, tcyaml_dict).
    """
    return request.param


@pytest.fixture(autouse=True)
def capture():
    """
    Fixture for log capturing. Returns a testfixtures.LogCapture object.

    Note: The log_capture decorator of testfixtures is not compatible with
    pytest fixtures, see
    https://testfixtures.readthedocs.io/en/latest/logging.html#the-decorator
    """
    with LogCapture() as lc:
        yield lc


@pytest.fixture(scope='function')
def test_client_recorder(request):
    # pylint: disable=unused-argument
    """
    Fixture for a TestClientRecorder object that records to TEST_YAML_FILE and
    that is enabled.
    """
    fp = _TestClientRecorder.open_file(TEST_YAML_FILE, 'w')
    recorder = _TestClientRecorder(fp)
    recorder.reset()
    recorder.enable()
    # recorder.test_fp = fp
    yield recorder
    # del recorder.test_fp
    fp.close()


def logged_payload(payload):
    """
    Return the payload unicode string as it is logged by the pywbem recorders.
    """
    ret_payload = repr(payload)
    if ret_payload.startswith("u'"):
        ret_payload = ret_payload[1:]
    return ret_payload


def load_recorder_yaml_file():
    """
    Load the test YAML file created by the test recorder and return its content
    as a dict.
    """
    with io.open(TEST_YAML_FILE, encoding="utf-8") as fp:
        yaml_content = yaml.load(
            fp, Loader=yamlloader.ordereddict.CSafeLoader)
    return yaml_content


def cleanup_recorder_yaml_file():
    """
    Delete the test YAML file created by the test recorder, to clean up.
    """
    if os.path.exists(TEST_YAML_FILE):
        try:
            os.remove(TEST_YAML_FILE)
        except Exception as exc:  # pylint: disable=broad-except
            # The file is still open at this point and on Windows,
            # a WindowsError is raised.
            warnings.warn(
                "Cleaning up the test client YAML file {} failed: {}".
                format(TEST_YAML_FILE, exc), UserWarning)


def test_BaseOperationRecorder_init():
    """
    Test function for BaseOperationRecorder.__init__()
    """

    # BaseOperationRecorder is an abstract base class, so we test its methods
    # through its derived class TestClientRecorder, but we verify that the
    # derived class attributes/methods we use were inherited from the base
    # class.
    assert is_inherited_from(
        'enabled', _TestClientRecorder, BaseOperationRecorder)

    with io.open(os.devnull, 'w', encoding='utf-8') as fp:

        # The code to be tested
        recorder = _TestClientRecorder(fp)

        assert recorder.enabled is True


def test_BaseOperationRecorder_enable_disable():
    """
    Test function for BaseOperationRecorder.enable() and disable()
    """

    # BaseOperationRecorder is an abstract base class, so we test its methods
    # through its derived class TestClientRecorder, but we verify that the
    # derived class attributes/methods we use were inherited from the base
    # class.
    assert is_inherited_from(
        'disable', _TestClientRecorder, BaseOperationRecorder)
    assert is_inherited_from(
        'enable', _TestClientRecorder, BaseOperationRecorder)
    assert is_inherited_from(
        'enabled', _TestClientRecorder, BaseOperationRecorder)

    with io.open(os.devnull, 'w', encoding='utf-8') as fp:

        recorder = _TestClientRecorder(fp)

        # The code to be tested
        recorder.enable()
        assert recorder.enabled is True

        # The code to be tested
        recorder.disable()
        assert recorder.enabled is False

        # The code to be tested
        recorder.disable()
        assert recorder.enabled is False

        # The code to be tested
        recorder.enable()
        assert recorder.enabled is True


TESTCASES_BASEOPERATIONRECORDER_OPEN_FILE = [

    # Testcases for BaseOperationRecorder.open_file()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * text: Input data for the file, as unicode string.
    #   * exp_bytes: Expected UTF-8 Bytes in the file, as byte string.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Single 7-bit ASCII character",
        dict(
            text=u'A',
            exp_bytes=b'A',
        ),
        None, None, True
    ),
    (
        "Single UCS-2 character resulting in 2-char UTF-8 sequence",
        dict(
            text=u'\u00E8',
            exp_bytes=b'\xC3\xA8',
        ),
        None, None, True
    ),
    (
        "Single UCS-2 character resulting in 3-char UTF-8 sequence",
        dict(
            text=u'\u2014',
            exp_bytes=b'\xE2\x80\x94',
        ),
        None, None, True
    ),
    (
        "Single UTF-16 surrogate sequence for U+10142 resulting in 4-char "
        "UTF-8 sequence",
        dict(
            text=u'\uD800\uDD42',
            exp_bytes=b'\xF0\x90\x85\x82',
        ),
        None, None, six.PY2  # Not supported in Python 3
    ),
    (
        "Single UCS-4 character resulting in 4-char UTF-8 sequence",
        dict(
            text=u'\U00010142',
            exp_bytes=b'\xF0\x90\x85\x82',
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_BASEOPERATIONRECORDER_OPEN_FILE)
@simplified_test_function
def test_BaseOperationRecorder_open_file(testcase, text, exp_bytes):
    # pylint: disable=unused-argument
    """
    Test function for BaseOperationRecorder.open_file()
    """

    # BaseOperationRecorder is an abstract base class, so we test its methods
    # through its derived class TestClientRecorder, but we verify that the
    # derived class attributes/methods we use were inherited from the base
    # class.
    assert is_inherited_from(
        'open_file', _TestClientRecorder, BaseOperationRecorder)

    tmp_filename = 'openfile.tmp'

    # The code to be tested
    fp = _TestClientRecorder.open_file(tmp_filename, 'w')

    fp.write(text)
    fp.close()

    with io.open(tmp_filename, 'rb') as fp:
        act_bytes = fp.read()
    assert act_bytes == exp_bytes

    os.remove(tmp_filename)


TESTCASES_TESTCLIENTRECORDER_TOYAML = [

    # Testcases for TestClientRecorder.toyaml()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * obj: Object that has dictionary behavior, e.g. IMInstanceName.
    #   * exp_yaml: Expected YAML object, for validation.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Boolean value True",
        dict(
            obj=True,
            exp_yaml=True,
        ),
        None, None, True
    ),
    (
        "Boolean value False",
        dict(
            obj=False,
            exp_yaml=False,
        ),
        None, None, True
    ),
    (
        "Integer value",
        dict(
            obj=1234,
            exp_yaml=1234,
        ),
        None, None, True
    ),
    (
        "Uint8 value",
        dict(
            obj=Uint8(42),
            exp_yaml=42,
        ),
        None, None, True
    ),
    (
        "Float value",
        dict(
            obj=42.1,
            exp_yaml=None,
        ),
        TypeError, None, True
    ),
    (
        "Real32 value",
        dict(
            obj=Real32(42.1),
            exp_yaml=42.1,
        ),
        None, None, True
    ),
    (
        "Unicode string value",
        dict(
            obj='blahblah ',
            exp_yaml='blahblah ',
        ),
        None, None, True
    ),
    (
        "Byte string value",
        dict(
            obj=b'blahblah ',
            exp_yaml='blahblah ',
        ),
        None, None, True
    ),
    (
        "CIMDateTime object",
        dict(
            obj=CIMDateTime('20140924193040.654321+120'),
            exp_yaml='20140924193040.654321+120',
        ),
        None, None, True
    ),
    (
        "datetime object",
        dict(
            obj=datetime(year=2020, month=1, day=28, hour=14, minute=46,
                         second=40, microsecond=654321,
                         tzinfo=MinutesFromUTC(120)),
            exp_yaml=CIMDateTime('20200128144640.654321+120'),
        ),
        None, None, True
    ),
    (
        "timedelta object",
        dict(
            obj=timedelta(183, (13 * 60 + 25) * 60 + 42, 234567),
            exp_yaml=CIMDateTime('00000183132542.234567:000'),
        ),
        None, None, True
    ),
    (
        "CIMInstanceName object",
        dict(
            obj=CIMInstanceName(
                'CIM_Foo',
                keybindings=OrderedDict([
                    ('Chicken', 'Ham'),
                    ('Beans', Uint8(42)),
                ]),
                namespace='cimv2',
                host='woot.com',
            ),
            exp_yaml=dict(
                pywbem_object='CIMInstanceName',
                classname=u'CIM_Foo',
                namespace=u'cimv2',
                host=u'woot.com',
                keybindings=yaml_ordereddict([
                    (u'Chicken', u'Ham'),
                    (u'Beans', 42),
                ]),
            ),
        ),
        None, None, True
    ),
    (
        "CIMInstance object",
        dict(
            obj=CIMInstance(
                'CIM_Foo',
                properties=[
                    ('Chicken', 'Ham'),
                ],
            ),
            exp_yaml=dict(
                pywbem_object='CIMInstance',
                classname=u'CIM_Foo',
                properties=yaml_ordereddict([
                    (u'Chicken', dict(
                        pywbem_object='CIMProperty',
                        name=u'Chicken',
                        type=u'string',
                        value=u'Ham',
                        reference_class=None,
                        embedded_object=None,
                        is_array=False,
                        array_size=None,
                        class_origin=None,
                        propagated=None,
                        qualifiers=yaml_ordereddict(),
                    )),
                ]),
                qualifiers=yaml_ordereddict(),
                path=None,
            ),
        ),
        None, None, True
    ),
    (
        "CIMClassName object",
        dict(
            obj=CIMClassName(
                'CIM_Foo',
                namespace='cimv2',
                host='woot.com',
            ),
            exp_yaml=dict(
                pywbem_object='CIMClassName',
                classname=u'CIM_Foo',
                namespace=u'cimv2',
                host='woot.com',
            ),
        ),
        None, None, True
    ),
    (
        "CIMClass object",
        dict(
            obj=CIMClass(
                'CIM_Foo',
                properties=[
                    CIMProperty('Chicken', type='string', value='Ham'),
                ],
            ),
            exp_yaml=dict(
                pywbem_object='CIMClass',
                classname=u'CIM_Foo',
                superclass=None,
                properties=yaml_ordereddict([
                    (u'Chicken', dict(
                        pywbem_object='CIMProperty',
                        name=u'Chicken',
                        type=u'string',
                        value=u'Ham',
                        reference_class=None,
                        embedded_object=None,
                        is_array=False,
                        array_size=None,
                        class_origin=None,
                        propagated=None,
                        qualifiers=yaml_ordereddict(),
                    )),
                ]),
                methods=yaml_ordereddict(),
                qualifiers=yaml_ordereddict(),
                path=None,
            ),
        ),
        None, None, True
    ),
    (
        "CIMProperty object",
        dict(
            obj=CIMProperty('Chicken', type='string', value='Ham'),
            exp_yaml=dict(
                pywbem_object='CIMProperty',
                name=u'Chicken',
                type=u'string',
                value=u'Ham',
                reference_class=None,
                embedded_object=None,
                is_array=False,
                array_size=None,
                class_origin=None,
                propagated=None,
                qualifiers=yaml_ordereddict(),
            ),
        ),
        None, None, True
    ),
    # TODO: Add testcase for reference property
    # TODO: Add testcase for embedded object property
    # TODO: Add testcase for array property
    (
        "CIMMethod object",
        dict(
            obj=CIMMethod('Chicken', return_type='string'),
            exp_yaml=dict(
                pywbem_object='CIMMethod',
                name=u'Chicken',
                return_type=u'string',
                class_origin=None,
                propagated=None,
                parameters=yaml_ordereddict(),
                qualifiers=yaml_ordereddict(),
            ),
        ),
        None, None, True
    ),
    (
        "CIMParameter object",
        dict(
            obj=CIMParameter('Chicken', type='string'),
            exp_yaml=dict(
                pywbem_object='CIMParameter',
                name=u'Chicken',
                type=u'string',
                reference_class=None,
                embedded_object=None,
                is_array=False,
                array_size=None,
                qualifiers=yaml_ordereddict(),
            ),
        ),
        None, None, True
    ),
    # TODO: Add testcase for reference parameter
    # TODO: Add testcase for embedded object parameter
    # TODO: Add testcase for array parameter
    (
        "CIMQualifier object",
        dict(
            obj=CIMQualifier('Chicken', type='string', value='Ham'),
            exp_yaml=dict(
                pywbem_object='CIMQualifier',
                name=u'Chicken',
                type=u'string',
                value=u'Ham',
                propagated=None,
                tosubclass=None,
                toinstance=None,
                overridable=None,
                translatable=None,
            ),
        ),
        None, None, True
    ),
    (
        "CIMQualifierDeclaration object",
        dict(
            obj=CIMQualifierDeclaration('Chicken', type='string', value='Ham'),
            exp_yaml=dict(
                pywbem_object='CIMQualifierDeclaration',
                name=u'Chicken',
                type=u'string',
                value=u'Ham',
                is_array=False,
                array_size=None,
                scopes=yaml_ordereddict(),
                tosubclass=None,
                toinstance=None,
                overridable=None,
                translatable=None,
            ),
        ),
        None, None, True
    ),
    # TODO: Add testcase for array qualifier decl
    (
        "pull_path_result_tuple object for exhausted open/pull",
        dict(
            obj=pull_path_result_tuple(
                [],
                True,
                None,
            ),
            exp_yaml=dict(
                paths=[],
                eos=True,
                context=None,
            ),
        ),
        None, None, True
    ),
    (
        "pull_path_result_tuple object for non-exhausted open/pull",
        dict(
            obj=pull_path_result_tuple(
                [],
                False,
                ('test_rtn_context', 'root/cim_namespace'),
            ),
            exp_yaml=dict(
                paths=[],
                eos=False,
                context=['test_rtn_context', 'root/cim_namespace'],
            ),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_TESTCLIENTRECORDER_TOYAML)
@simplified_test_function
def test_TestClientRecorder_toyaml(testcase, obj, exp_yaml):
    # pylint: disable=unused-argument
    """
    Test function for TestClientRecorder.toyaml()
    """

    with io.open(os.devnull, 'w', encoding='utf-8') as fp:

        recorder = _TestClientRecorder(fp)
        recorder.reset()
        recorder.enable()

        # The code to be tested
        act_yaml = recorder.toyaml(obj)

    assert act_yaml == exp_yaml


TESTCASES_TESTCLIENTRECORDER_RECORD = [

    # Testcases for TestClientRecorder.toyaml()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * op_name: Name of the operation
    # * op_kwargs: Input arguments for the operation as kwargs dict
    # * op_result: Return value of the operation
    # * op_exc: Exception raised by the operation, or None
    # * exp_yaml_items: partial set of items that should be compared against
    #   the items in the first entry of the generated test YAML file.

    (
        "InvokeMethod of instance method",
        'InvokeMethod',
        dict(
            namespace='cim/blah',
            MethodName='Blah',
            ObjectName=CIMInstanceName('C1'),
            Params=[
                CIMParameter('P1', type='string', value='abc'),
            ],
        ),
        Uint32(42),
        None,
        dict(
            name='InvokeMethod',
            pywbem_request=dict(
                url='http://acme.com:80',
                creds=['username', 'password'],
                debug=False,
                timeout=10,
                namespace='root/cimv2',
                operation=dict(
                    pywbem_method='InvokeMethod',
                    namespace='cim/blah',
                    MethodName='Blah',
                    ObjectName=dict(
                        pywbem_object='CIMInstanceName',
                        classname='C1',
                        keybindings=yaml_ordereddict(),
                        namespace=None,
                        host=None,
                    ),
                    Params=[
                        dict(
                            pywbem_object='CIMParameter',
                            name='P1',
                            type='string',
                            array_size=None,
                            is_array=False,
                            reference_class=None,
                            embedded_object=None,
                            qualifiers=yaml_ordereddict(),
                        )
                    ],
                ),
            ),
            pywbem_response=dict(
                result=42,
            ),
        ),
    ),
    (
        "GetInstance on an instance",
        'GetInstance',
        dict(
            namespace='cim/blah',
            InstanceName=CIMInstanceName('C1'),
            LocalOnly=False,
            IncludeQualifiers=True,
            IncludeClassOrigin=True,
            PropertyList=['propertyblah'],
        ),
        CIMInstance('C1'),
        None,
        dict(
            name='GetInstance',
            pywbem_request=dict(
                url='http://acme.com:80',
                creds=['username', 'password'],
                debug=False,
                timeout=10,
                namespace='root/cimv2',
                operation=dict(
                    pywbem_method='GetInstance',
                    namespace='cim/blah',
                    IncludeClassOrigin=True,
                    IncludeQualifiers=True,
                    InstanceName=dict(
                        pywbem_object='CIMInstanceName',
                        classname='C1',
                        keybindings=yaml_ordereddict(),
                        namespace=None,
                        host=None,
                    ),
                    LocalOnly=False,
                    PropertyList=['propertyblah'],
                ),
            ),
            pywbem_response=dict(
                result=dict(
                    pywbem_object='CIMInstance',
                    classname='C1',
                    properties=yaml_ordereddict(),
                    qualifiers=yaml_ordereddict(),
                    path=None,
                ),
            ),
        ),
    ),
    (
        "CreateInstance with properties of all types",
        'CreateInstance',
        dict(
            namespace='cim/blah',
            NewInstance=CIMINSTANCE_ALL_OBJ,
        ),
        CIMInstanceName('C1'),
        None,
        dict(
            name='CreateInstance',
            pywbem_request=dict(
                url='http://acme.com:80',
                creds=['username', 'password'],
                debug=False,
                timeout=10,
                namespace='root/cimv2',
                operation=dict(
                    pywbem_method='CreateInstance',
                    namespace='cim/blah',
                    NewInstance=CIMINSTANCE_ALL_TCYAML,
                ),
            ),
            pywbem_response=dict(
                result=dict(
                    pywbem_object='CIMInstanceName',
                    classname='C1',
                    keybindings=yaml_ordereddict(),
                    namespace=None,
                    host=None,
                ),
            ),
        ),
    ),
    (
        "OpenEnumerateInstancePaths operation",
        'OpenEnumerateInstancePaths',
        dict(
            namespace='cim/blah',
            ClassName='CIM_BLAH',
            FilterQueryLanguage='WQL',
            FilterQuery='Property = 3',
            OperationTimeout=40,
            ContinueOnError=False,
            MaxObjectCount=100,
        ),
        pull_path_result_tuple(
            [],
            False,
            ('test_rtn_context', 'root/cim_namespace'),
        ),
        None,
        dict(
            name='OpenEnumerateInstancePaths',
            pywbem_request=dict(
                url='http://acme.com:80',
                creds=['username', 'password'],
                debug=False,
                timeout=10,
                namespace='root/cimv2',
                operation=dict(
                    pywbem_method='OpenEnumerateInstancePaths',
                    namespace='cim/blah',
                    ClassName='CIM_BLAH',
                    ContinueOnError=False,
                    FilterQuery='Property = 3',
                    FilterQueryLanguage='WQL',
                    MaxObjectCount=100,
                    OperationTimeout=40,
                ),
            ),
            pywbem_response=dict(
                pullresult=dict(
                    context=['test_rtn_context', 'root/cim_namespace'],
                    eos=False,
                    paths=[],
                ),
            ),
        ),
    ),

    (
        "ExportIndication with an indication with property",
        'ExportIndication',
        dict(
            NewIndication=CIMINSTANCE_ONE_OBJ,
        ),
        None,
        None,
        dict(
            name='ExportIndication',
            pywbem_request=dict(
                url='http://acme.com:80',
                creds=['username', 'password'],
                debug=False,
                timeout=10,
                namespace='root/cimv2',
                operation=dict(
                    pywbem_method='ExportIndication',
                    NewIndication=CIMINSTANCE_ONE_TCYAML,
                ),
            ),
            pywbem_response={},
        ),
    ),
]


@pytest.mark.parametrize(
    "desc, op_name, op_kwargs, op_result, op_exc, exp_yaml_items",
    TESTCASES_TESTCLIENTRECORDER_RECORD)
def test_TestClientRecorder_record(
        desc, op_name, op_kwargs, op_result, op_exc, exp_yaml_items,
        test_client_recorder):
    # pylint: disable=redefined-outer-name
    """
    Record a single operation using the test client recorder and verify the
    generated YAML file.
    """

    # The code to be tested
    if op_name.startswith('Open') or op_name.startswith('Pull'):
        test_client_recorder.reset(pull_op=True)
    test_client_recorder.stage_pywbem_args(method=op_name, **op_kwargs)
    test_client_recorder.stage_pywbem_result(op_result, op_exc)
    test_client_recorder.record_staged()

    if DEBUG_TEST_YAML_FILE:
        print("\nDebug: Test client YAML file for testcase: {}".
              format(desc))
        if sys.platform == 'win32':
            os.system('type {}'.format(TEST_YAML_FILE))
        else:
            os.system('cat {}'.format(TEST_YAML_FILE))

    # Verify the generated test client YAML file
    test_yaml = load_recorder_yaml_file()
    assert len(test_yaml) == 1
    test_yaml_record = test_yaml[0]
    for key in exp_yaml_items:
        exp_value = exp_yaml_items[key]
        assert_yaml_equal(test_yaml_record[key], exp_value, key)

    cleanup_recorder_yaml_file()


def to_dict(mapping, dict_type):
    """
    Convert a mapping to a specific dict type, and also for all of its items
    that are mappings, recursively.
    """
    assert isinstance(mapping, Mapping)
    if not type(mapping) is dict_type:  # pylint: disable=unidiomatic-typecheck
        mapping = dict(mapping)
    for k, v in mapping.items():
        if isinstance(v, Mapping):
            mapping[k] = to_dict(v, dict_type)
    return mapping


def assert_yaml_equal(act_value, exp_value, location):
    """
    Assert that two YAML objects are equal, whereby dictionaries are compared
    such that the use of an OrderedDict on the side of the expected value
    takes ordering into account, and any other dict type does not.
    """
    if isinstance(exp_value, OrderedDict):
        # Ordered comparison.
        assert act_value == exp_value, \
            "Unexpected YAML object at {}".format(location)
    elif isinstance(exp_value, dict):
        # Ensure unordered comparison by converting to dict.
        # Note that starting with Python 3.7, dict maintains order but equality
        # comparison does not take order into account.
        act_value2 = to_dict(act_value, dict)
        assert act_value2 == exp_value, \
            "Unexpected YAML object at {}".format(location)
    else:
        assert act_value == exp_value, \
            "Unexpected YAML object at {}".format(location)


################################################################
#
#           LogOperationRecorder tests
#
################################################################

class BaseLogOperationRecorderTests(object):
    """
    Test the LogOperationRecorder functions. Creates log entries and
    uses testfixture to validate results
    """

    def setup_method(self):
        """
        Setup that is run before each test method.
        """
        # Shut down any existing logger and reset WBEMConnection and
        # reset WBEMConnection class attributes
        # pylint: disable=protected-access
        WBEMConnection._reset_logging_config()
        logging.shutdown()
        # NOTE We do not clean up handlers or logger names already defined.
        #      That should not affect the tests.

    def recorder_setup(self, detail_level=None):
        """
        Setup the recorder for a defined max output size
        """

        configure_logger('api', log_dest='file',
                         detail_level=detail_level,
                         log_filename=TEST_OUTPUT_LOG, propagate=True)

        configure_logger('http', log_dest='file',
                         detail_level=detail_level,
                         log_filename=TEST_OUTPUT_LOG, propagate=True)

        # Define an attribute that is a single LogOperationRecorder to be used
        # in some of the tests.  Note that if detail_level is dict it is used
        # directly.
        if isinstance(detail_level, (six.string_types, six.integer_types)):
            detail_level = {'api': detail_level, 'http': detail_level}

        # pylint: disable=attribute-defined-outside-init
        # Set a conn id into the connection. Saves testing the connection
        # log for each test.
        self.test_recorder = LogOperationRecorder('test_id',
                                                  detail_levels=detail_level)
        # pylint: disable=protected-access
        self.test_recorder.reset()
        self.test_recorder.enable()

    def teardown_method(self):
        """
        Teardown that is run after each test method.
        """
        LogCapture.uninstall_all()
        logging.shutdown()
        # remove any existing log file
        if os.path.isfile(TEST_OUTPUT_LOG):
            os.remove(TEST_OUTPUT_LOG)


class Test_LOR_Connections(BaseLogOperationRecorderTests):
    """
    Test the LogOperationRecorder with just connections, without any operations.
    """

    def test_connection_1(self, capture):
        # pylint: disable=redefined-outer-name
        """
        Test log of a WBEMConnection object with default parameters.
        """

        # Fake the connection to create a fixed data environment
        conn = WBEMConnection('http://blah:5988')

        configure_logger('api', log_dest='file', detail_level='all',
                         connection=conn, log_filename=TEST_OUTPUT_LOG,
                         propagate=True)

        conn_id = conn.conn_id
        api_exp_log_id = 'pywbem.api.{0}'.format(conn_id)

        result_con = _format(
            "Connection:{0} WBEMConnection("
            "url='http://blah:5988', "
            "creds=None, "
            "conn_id={0!A}, "
            "default_namespace='root/cimv2', "
            "x509=None, "
            "ca_certs=None, "
            "no_verification=False, "
            "timeout=None, "
            "use_pull_operations=False, "
            "stats_enabled=False, "
            "recorders=['LogOperationRecorder'])",
            conn_id)

        capture.check(
            (api_exp_log_id, 'DEBUG', result_con),
        )

    def test_connection_2(self, capture):
        # pylint: disable=redefined-outer-name
        """
        Test log of a WBEMConnection object with most parameters specified,
        and detail level 'all'.
        """

        conn = WBEMConnection('http://blah:5988',
                              default_namespace='root/blah',
                              creds=('username', 'password'),
                              no_verification=True,
                              timeout=10,
                              use_pull_operations=True,
                              stats_enabled=True)

        configure_logger('api', log_dest='file', detail_level='all',
                         connection=conn, log_filename=TEST_OUTPUT_LOG,
                         propagate=True)

        conn_id = conn.conn_id
        api_exp_log_id = 'pywbem.api.{0}'.format(conn_id)

        result_con = _format(
            "Connection:{0} WBEMConnection("
            "url='http://blah:5988', "
            "creds=('username', ...), "
            "conn_id={0!A}, "
            "default_namespace='root/blah', "
            "x509=None, "
            "ca_certs=None, "
            "no_verification=True, "
            "timeout=10, "
            "use_pull_operations=True, "
            "stats_enabled=True, "
            "recorders=['LogOperationRecorder'])",
            conn_id)

        capture.check(
            (api_exp_log_id, 'DEBUG', result_con),
        )

    def test_connection_summary(self, capture):
        # pylint: disable=redefined-outer-name
        """
        Test log of a WBEMConnection object with most parameters specified,
        and detail level 'summary'.
        """

        conn = WBEMConnection('http://blah:5988',
                              default_namespace='root/blah',
                              creds=('username', 'password'),
                              no_verification=True,
                              timeout=10,
                              use_pull_operations=True,
                              stats_enabled=True)

        configure_logger('api', log_dest='file', detail_level='summary',
                         connection=conn, log_filename=TEST_OUTPUT_LOG,
                         propagate=True)

        conn_id = conn.conn_id
        api_exp_log_id = 'pywbem.api.{0}'.format(conn_id)

        result_con = _format(
            "Connection:{0} WBEMConnection("
            "url='http://blah:5988', "
            "creds=('username', ...), "
            "default_namespace='root/blah', "
            "...)",
            conn_id)

        capture.check(
            (api_exp_log_id, 'DEBUG', result_con),
        )


class Test_LOR_PywbemResults(BaseLogOperationRecorderTests):
    """
    Test the LogOperationRecorder by staging pywbem results of operations.
    """

    def test_result_exception(self, capture):
        # pylint: disable=redefined-outer-name
        """
        Test the ops result log None return, HTTPError exception.
        """

        self.recorder_setup(detail_level=10)

        # Note: cimerror is the CIMError HTTP header field
        exc = HTTPError(500, "Fake Reason", cimerror="Fake CIMError")

        self.test_recorder.stage_pywbem_result(None, exc)

        result_exc = "Exception:test_id None('HTTPError...)"

        capture.check(
            ('pywbem.api.test_id', 'DEBUG', result_exc),
        )

    def test_result_exception_all(self, capture):
        # pylint: disable=redefined-outer-name
        """
        Test the ops result log None return, HTTPError exception.
        """

        self.recorder_setup(detail_level='all')

        # Note: cimerror is the CIMError HTTP header field
        exc = HTTPError(500, "Fake Reason", cimerror="Fake CIMError")

        self.test_recorder.stage_pywbem_result(None, exc)

        result_exc = _format(
            "Exception:test_id None('HTTPError({0})')",
            exc)

        capture.check(
            ('pywbem.api.test_id', 'DEBUG', result_exc),
        )

    def test_result_getinstance(self, capture, instancename_tuple):
        # pylint: disable=redefined-outer-name
        """
        Emulates call to getInstance to test parameter processing.
        Currently creates the pywbem_request component.
        """

        instancename = instancename_tuple[0]
        self.recorder_setup(detail_level='all')

        self.test_recorder.stage_pywbem_args(
            method='GetInstance',
            InstanceName=instancename,
            LocalOnly=True,
            IncludeQualifiers=True,
            IncludeClassOrigin=True,
            PropertyList=['propertyblah'])

        result_req = \
            "Request:test_id GetInstance(" \
            "IncludeClassOrigin=True, " \
            "IncludeQualifiers=True, " \
            "InstanceName={ip!r}, " \
            "LocalOnly=True, " \
            "PropertyList=['propertyblah'])". \
            format(ip=instancename)

        capture.check(
            ('pywbem.api.test_id', 'DEBUG', result_req),
        )

    @pytest.mark.parametrize(
        "detail_level", [10, 1000, 'all'])
    def test_result_instance(self, capture, instance_tuple, detail_level):
        # pylint: disable=redefined-outer-name
        """
        Test the staging of a CIM instance with different detail_level values.
        """

        instance = instance_tuple[0]
        self.recorder_setup(detail_level=detail_level)
        exc = None

        self.test_recorder.stage_pywbem_result(instance, exc)

        exp_str = repr(instance)
        if detail_level == 'all':
            # use it in its full length
            pass
        elif len(exp_str) <= detail_level:
            # it fits the desired detail
            pass
        else:
            # shorten it to the desired detail
            exp_str = "{}...".format(exp_str[:detail_level])

        result_ret = "Return:test_id None({})".format(exp_str)

        capture.check(
            ('pywbem.api.test_id', 'DEBUG', result_ret),
        )

    def test_result_instance_paths(self, capture, instance_wp_tuple):
        # pylint: disable=redefined-outer-name
        """
        Test the staging of a CIM instance with path with detail_level 'paths'.
        """

        instance_wp = instance_wp_tuple[0]
        self.recorder_setup(detail_level='paths')
        exc = None

        self.test_recorder.stage_pywbem_result(instance_wp, exc)

        path_str = "'{}'".format(instance_wp.path.to_wbem_uri())
        result_ret = "Return:test_id None({})".format(path_str)

        capture.check(
            ('pywbem.api.test_id', 'DEBUG', result_ret),
        )

    def test_result_instances_paths(self, capture, instances_wp_tuple):
        # pylint: disable=redefined-outer-name
        """
        Test the staging of multiple CIM instances with path with
        detail_level 'paths'.
        """

        instances_wp = instances_wp_tuple[0]
        self.recorder_setup(detail_level='paths')
        exc = None

        self.test_recorder.stage_pywbem_result(instances_wp, exc)

        path_strs = ["'{}'".format(inst.path.to_wbem_uri())
                     for inst in instances_wp]
        result_ret = "Return:test_id None({})".format(', '.join(path_strs))

        capture.check(
            ('pywbem.api.test_id', 'DEBUG', result_ret),
        )

    def test_result_pull_instances_paths(self, capture, instances_wp_tuple):
        # pylint: disable=redefined-outer-name
        """
        Test the staging of multiple CIM instances with path with
        detail_level 'paths'.
        """

        instances_wp = instances_wp_tuple[0]
        self.recorder_setup(detail_level='paths')
        exc = None

        context = ('test_rtn_context', 'root/blah')
        result_tuple = pull_inst_result_tuple(
            instances_wp, False, context)

        self.test_recorder.stage_pywbem_result(result_tuple, exc)

        path_strs = ["'{}'".format(inst.path.to_wbem_uri())
                     for inst in instances_wp]
        result_ret = (
            "Return:test_id None(pull_inst_result_tuple("
            "context=('test_rtn_context', 'root/blah'), eos=False, "
            "instances={}))".format(', '.join(path_strs))
        )

        capture.check(
            ('pywbem.api.test_id', 'DEBUG', result_ret),
        )


class Test_LOR_HTTPRequests(BaseLogOperationRecorderTests):
    """
    Test the LogOperationRecorder by staging HTTP requests of operations.
    """

    def build_http_request(self, instancename):
        """
        Build the HTTP request for a GetInstance operation for the specified
        instance name, for use by the following tests.
        """
        headers = OrderedDict([
            ('CIMOperation', 'MethodCall'),
            ('CIMMethod', 'GetInstance'),
            ('CIMObject', 'root/cimv2')])
        url = 'http://blah:5988'
        method = 'POST'
        target = '/cimom'

        payload = (
            u'<?xml version="1.0" encoding="utf-8" ?>\n'
            u'<CIM CIMVERSION="2.0" DTDVERSION="2.0">\n'
            u'<MESSAGE ID="1001" PROTOCOLVERSION="1.0">\n'
            u'<SIMPLEREQ>\n'
            u'<IMETHODCALL NAME="GetInstance">\n'
            u'<LOCALNAMESPACEPATH>\n'
            u'<NAMESPACE NAME="root"/>\n'
            u'<NAMESPACE NAME="cimv2"/>\n'
            u'</LOCALNAMESPACEPATH>\n'
            u'<IPARAMVALUE NAME="InstanceName">\n'
            u'{ip}\n'
            u'</IPARAMVALUE>\n'
            u'<IPARAMVALUE NAME="LocalOnly">\n'
            u'<VALUE>FALSE</VALUE>\n'
            u'</IPARAMVALUE>\n'
            u'</IMETHODCALL>\n'
            u'</SIMPLEREQ>\n'
            u'</MESSAGE>\n'
            u'</CIM>)'.
            format(ip=instancename.tocimxmlstr(indent=0))
        )

        return url, target, method, headers, payload

    def test_stage_http_request_all(self, capture, instancename_tuple):
        # pylint: disable=redefined-outer-name
        """
        Test stage of http_request log with detail_level='all'
        """

        instancename = instancename_tuple[0]
        self.recorder_setup(detail_level='all')
        url, target, method, headers, payload = \
            self.build_http_request(instancename)

        self.test_recorder.stage_http_request('test_id', 11, url, target,
                                              method, headers, payload)

        result_req = (
            "Request:test_id POST /cimom 11 http://blah:5988 "
            "CIMOperation:'MethodCall' "
            "CIMMethod:'GetInstance' "
            "CIMObject:'root/cimv2' "
            "{}".
            format(logged_payload(payload)))

        capture.check(
            ('pywbem.http.test_id', 'DEBUG', result_req),
        )

    def test_stage_http_request_summary(self, capture, instancename_tuple):
        # pylint: disable=redefined-outer-name
        """
        Test http request log record with summary as detail level
        """

        instancename = instancename_tuple[0]
        self.recorder_setup(detail_level='summary')
        url, target, method, headers, payload = \
            self.build_http_request(instancename)
        self.test_recorder.stage_http_request('test_id', 11, url, target,
                                              method, headers, payload)

        result_req = (
            "Request:test_id POST /cimom 11 http://blah:5988 "
            "CIMOperation:'MethodCall' "
            "CIMMethod:'GetInstance' "
            "CIMObject:'root/cimv2' "
            "''")

        capture.check(
            ('pywbem.http.test_id', 'DEBUG', result_req),
        )

    def test_stage_http_request_int(self, capture, instancename_tuple):
        # pylint: disable=redefined-outer-name
        """
        Test http log record with integer as detail_level
        """

        instancename = instancename_tuple[0]
        self.recorder_setup(detail_level=10)
        url, target, method, headers, payload = \
            self.build_http_request(instancename)

        self.test_recorder.stage_http_request('test_id', 11, url, target,
                                              method, headers, payload)

        result_req = (
            "Request:test_id POST /cimom 11 http://blah:5988 "
            "CIMOperation:'MethodCall' "
            "CIMMethod:'GetInstance' "
            "CIMObject:'root/cimv2' "
            "'<?xml vers...'")

        capture.check(
            ('pywbem.http.test_id', 'DEBUG', result_req),
        )


class Test_LOR_HTTPResponses(BaseLogOperationRecorderTests):
    """
    Test the LogOperationRecorder by staging HTTP responses of operations.
    """

    def build_http_response(self, instance):
        """
        Build the HTTP response for a GetInstance operation for the specified
        instance, for use by the following tests.
        Also, perform part 1 of the response staging.
        """
        body = (
            u'<?xml version="1.0" encoding="utf-8" ?>\n'
            u'<CIM CIMVERSION="2.0" DTDVERSION="2.0">\n'
            u'<MESSAGE ID="1001" PROTOCOLVERSION="1.0">\n'
            u'<SIMPLERSP>\n'
            u'<IMETHODRESPONSE NAME="GetInstance">\n'
            u'<IRETURNVALUE>\n'
            u'{i}\n'
            u'</IRETURNVALUE>\n'
            u'</IMETHODRESPONSE>\n'
            u'</SIMPLERSP>\n'
            u'</MESSAGE>\n'
            u'</CIM>)\n'.
            format(i=instance.tocimxmlstr(indent=0))
        )
        headers = OrderedDict([
            ('Content-type', 'application/xml; charset="utf-8"'),
            ('Content-length', str(len(body)))])
        status = 200
        reason = ""
        version = 11
        self.test_recorder.stage_http_response1('test_id', version,
                                                status, reason, headers)
        return body

    def test_stage_http_response_all(self, capture, instance_tuple):
        # pylint: disable=redefined-outer-name
        """
        Test http response log record with 'all' detail_level
        """

        instance = instance_tuple[0]
        self.recorder_setup(detail_level='all')

        body = self.build_http_response(instance)

        self.test_recorder.stage_http_response2(body)

        result_resp = (
            "Response:test_id 200: 11 "
            "Content-type:'application/xml; charset=\"utf-8\"' "
            "Content-length:'{bl}' "
            "{b}".
            format(bl=len(body), b=logged_payload(body))
        )

        capture.check(
            ('pywbem.http.test_id', 'DEBUG', result_resp),
        )

    def test_stage_http_response_summary(self, capture, instance_tuple):
        # pylint: disable=redefined-outer-name
        """
        Test http response log record with 'all' detail_level
        """

        instance = instance_tuple[0]
        self.recorder_setup(detail_level='summary')

        body = self.build_http_response(instance)

        self.test_recorder.stage_http_response2(body)

        result_resp = (
            "Response:test_id 200: 11 "
            "Content-type:'application/xml; charset=\"utf-8\"' "
            "Content-length:'{bl}' "
            "''".
            format(bl=len(body))
        )

        capture.check(
            ('pywbem.http.test_id', 'DEBUG', result_resp),
        )

    def test_stage_http_response_int(self, capture, instance_tuple):
        # pylint: disable=redefined-outer-name
        """
        Test http response log record with 'all' detail_level
        """

        instance = instance_tuple[0]
        self.recorder_setup(detail_level=30)

        body = self.build_http_response(instance)

        self.test_recorder.stage_http_response2(body)

        result_resp = (
            "Response:test_id 200: 11 "
            "Content-type:'application/xml; charset=\"utf-8\"' "
            "Content-length:'{bl}' "
            '\'<?xml version="1.0" encoding="...\''.
            format(bl=len(body))
        )

        capture.check(
            ('pywbem.http.test_id', 'DEBUG', result_resp),
        )


class Test_LOR_PywbemArgsResults(BaseLogOperationRecorderTests):
    """
    Test the LogOperationRecorder by staging pywbem args and results of
    operations.
    """

    def test_getinstance(self, capture, instance_wp_tuple):
        # pylint: disable=redefined-outer-name
        """
        Test the ops result log for get instance
        """

        instance = instance_wp_tuple[0]
        instancename = instance.path

        # set recorder to limit response to length of 10
        self.recorder_setup(detail_level=10)

        self.test_recorder.stage_pywbem_args(
            method='GetInstance',
            InstanceName=instancename,
            LocalOnly=True,
            IncludeQualifiers=True,
            IncludeClassOrigin=True,
            PropertyList=['propertyblah'])

        exc = None
        self.test_recorder.stage_pywbem_result(instance, exc)

        result_req = (
            "Request:test_id GetInstance(IncludeCla...)")

        result_ret = (
            "Return:test_id GetInstance(CIMInstanc...)")

        capture.check(
            ('pywbem.api.test_id', 'DEBUG', result_req),
            ('pywbem.api.test_id', 'DEBUG', result_ret),
        )

    def test_getinstance_exception(self, capture, instance_wp_tuple):
        # pylint: disable=redefined-outer-name
        """
        Test the ops result log for get instance
        """

        instance = instance_wp_tuple[0]
        instancename = instance.path

        self.recorder_setup(detail_level=11)

        self.test_recorder.stage_pywbem_args(
            method='GetInstance',
            InstanceName=instancename,
            LocalOnly=True,
            IncludeQualifiers=True,
            IncludeClassOrigin=True,
            PropertyList=['propertyblah'])

        instance = None
        exc = CIMError(6, "Fake CIMError")
        self.test_recorder.stage_pywbem_result(instance, exc)

        result_req = (
            "Request:test_id GetInstance(IncludeClas...)")

        result_exc = (
            "Exception:test_id GetInstance('CIMError(6...)")

        capture.check(
            ('pywbem.api.test_id', 'DEBUG', result_req),
            ('pywbem.api.test_id', 'DEBUG', result_exc),
        )

    def test_getinstance_exception_all(self, capture, instance_wp_tuple):
        # pylint: disable=redefined-outer-name
        """
        Test the ops result log for get instance CIMError exception
        """

        instance = instance_wp_tuple[0]
        instancename = instance.path

        self.recorder_setup(detail_level='all')

        self.test_recorder.stage_pywbem_args(
            method='GetInstance',
            InstanceName=instancename)

        instance = None
        exc = CIMError(6, "Fake CIMError")
        self.test_recorder.stage_pywbem_result(instance, exc)

        result_req = (
            "Request:test_id GetInstance("
            "InstanceName={!r})".
            format(instancename))

        result_exc = _format(
            "Exception:test_id GetInstance('CIMError({0})')", exc)

        capture.check(
            ('pywbem.api.test_id', 'DEBUG', result_req),
            ('pywbem.api.test_id', 'DEBUG', result_exc),
        )

    def test_getinstance_result_all(self, capture, instance_wp_tuple):
        # pylint: disable=redefined-outer-name
        """
        Test the ops result log for get instance
        """

        instance = instance_wp_tuple[0]
        instancename = instance.path

        self.recorder_setup(detail_level='all')

        self.test_recorder.stage_pywbem_args(
            method='GetInstance',
            InstanceName=instancename,
            LocalOnly=True,
            IncludeQualifiers=True,
            IncludeClassOrigin=True,
            PropertyList=['propertyblah'])

        exc = None

        self.test_recorder.stage_pywbem_result(instance, exc)

        result_req = (
            "Request:test_id GetInstance("
            "IncludeClassOrigin=True, "
            "IncludeQualifiers=True, "
            "InstanceName={!r}, "
            "LocalOnly=True, "
            "PropertyList=['propertyblah'])".
            format(instancename))

        result_ret = (
            "Return:test_id GetInstance({!r})".
            format(instance))

        capture.check(
            ('pywbem.api.test_id', 'DEBUG', result_req),
            ('pywbem.api.test_id', 'DEBUG', result_ret),
        )

    def test_enuminstances_result(self, capture, instance_wp_tuple):
        # pylint: disable=redefined-outer-name
        """
        Test the ops result log for enumerate instances
        """

        instance = instance_wp_tuple[0]
        classname = instance.classname

        # set recorder to limit response to length of 10
        self.recorder_setup(detail_level=10)

        self.test_recorder.stage_pywbem_args(
            method='EnumerateInstances',
            ClassName=classname,
            LocalOnly=True,
            IncludeQualifiers=True,
            IncludeClassOrigin=True,
            PropertyList=['propertyblah'])

        exc = None

        self.test_recorder.stage_pywbem_result([instance, instance], exc)

        result_req = (
            "Request:test_id EnumerateInstances(ClassName=...)")

        result_ret = (
            "Return:test_id EnumerateInstances([CIMInstan...)")

        capture.check(
            ('pywbem.api.test_id', 'DEBUG', result_req),
            ('pywbem.api.test_id', 'DEBUG', result_ret),
        )

    def test_enuminstancenames_result(self, capture, instance_wp_tuple):
        # pylint: disable=redefined-outer-name
        """
        Test the ops result log for enumerate instances
        """

        instance = instance_wp_tuple[0]
        instancename = instance.path
        classname = instance.classname

        # set recorder to limit response to length of 10
        self.recorder_setup(detail_level=10)

        self.test_recorder.stage_pywbem_args(
            method='EnumerateInstanceNames',
            ClassName=classname,
            LocalOnly=True,
            IncludeQualifiers=True,
            IncludeClassOrigin=True,
            PropertyList=['propertyblah', 'blah2'])

        exc = None

        self.test_recorder.stage_pywbem_result(
            [instancename, instancename], exc)

        result_req = (
            "Request:test_id EnumerateInstanceNames(ClassName=...)")

        result_ret = (
            "Return:test_id EnumerateInstanceNames([CIMInstan...)")

        capture.check(
            ('pywbem.api.test_id', 'DEBUG', result_req),
            ('pywbem.api.test_id', 'DEBUG', result_ret),
        )

    def test_openenuminstances_result_all(self, capture):
        # pylint: disable=redefined-outer-name
        """
        Test the ops result log for enumerate instances. Returns no instances.
        """

        classname = 'CIM_Foo'

        # set recorder to limit response to length of 10
        self.recorder_setup(detail_level='all')

        self.test_recorder.stage_pywbem_args(
            method='OpenEnumerateInstances',
            ClassName=classname,
            LocalOnly=True,
            IncludeQualifiers=True,
            IncludeClassOrigin=True,
            PropertyList=['propertyblah'])

        exc = None

        result = []
        context = ('test_rtn_context', 'root/blah')
        result_tuple = pull_inst_result_tuple(result, False, context)

        self.test_recorder.stage_pywbem_result(result_tuple, exc)

        result_req = (
            "Request:test_id OpenEnumerateInstances("
            "ClassName={!r}, "
            "IncludeClassOrigin=True, "
            "IncludeQualifiers=True, "
            "LocalOnly=True, "
            "PropertyList=['propertyblah'])".
            format(classname))

        result_ret = (
            "Return:test_id OpenEnumerateInstances("
            "pull_inst_result_tuple("
            "context=('test_rtn_context', 'root/blah'), eos=False, "
            "instances=[]))")

        capture.check(
            ('pywbem.api.test_id', 'DEBUG', result_req),
            ('pywbem.api.test_id', 'DEBUG', result_ret),
        )

    def test_openenuminstances_all(self, capture, instance_wp_tuple):
        # pylint: disable=redefined-outer-name
        """
        Test the ops result log for enumerate instances paths with
        data in the paths component
        """

        instance = instance_wp_tuple[0]
        instancename = instance.path
        classname = instance.classname

        # set recorder to limit response to length of 10
        self.recorder_setup(detail_level='all')

        self.test_recorder.stage_pywbem_args(
            method='OpenEnumerateInstancePaths',
            ClassName=classname,
            FilterQueryLanguage='FQL',
            FilterQuery='SELECT A from B',
            OperationTimeout=10,
            ContinueOnError=None,
            MaxObjectCount=100)

        result = [instancename, instancename]
        exc = None

        context = ('test_rtn_context', 'root/blah')
        result_tuple = pull_path_result_tuple(result, False, context)

        self.test_recorder.stage_pywbem_result(result_tuple, exc)

        result_req = (
            "Request:test_id OpenEnumerateInstancePaths("
            "ClassName={!r}, "
            "ContinueOnError=None, "
            "FilterQuery='SELECT A from B', "
            "FilterQueryLanguage='FQL', "
            "MaxObjectCount=100, "
            "OperationTimeout=10)".
            format(classname))

        result_ret = (
            "Return:test_id OpenEnumerateInstancePaths("
            "pull_path_result_tuple("
            "context=('test_rtn_context', 'root/blah'), eos=False, "
            "paths={!r}))".
            format(result))

        capture.check(
            ('pywbem.api.test_id', 'DEBUG', result_req),
            ('pywbem.api.test_id', 'DEBUG', result_ret),
        )

    def test_associators_result(self, capture, instance_wp_tuple):
        # pylint: disable=redefined-outer-name
        """
        Test the ops result log for Associators that returns nothing
        """

        instance = instance_wp_tuple[0]
        instancename = instance.path

        # set recorder to limit response to length of 10
        self.recorder_setup(detail_level=10)

        self.test_recorder.stage_pywbem_args(
            method='Associators',
            InstanceName=instancename,
            AssocClass='BLAH_Assoc',
            ResultClass='BLAH_Result',
            IncludeQualifiers=True,
            IncludeClassOrigin=True,
            PropertyList=['propertyblah', 'propertyblah2'])
        exc = None

        self.test_recorder.stage_pywbem_result([], exc)

        result_req = (
            "Request:test_id Associators(AssocClass...)")

        result_ret = (
            "Return:test_id Associators([])")

        capture.check(
            ('pywbem.api.test_id', 'DEBUG', result_req),
            ('pywbem.api.test_id', 'DEBUG', result_ret),
        )

    def test_associators_result_exception(self, capture):
        # pylint: disable=redefined-outer-name
        """
        Test the ops result log for associators that returns exception
        """

        # set recorder to limit response to length of 10
        self.recorder_setup(detail_level=11)

        exc = CIMError(6, "Fake CIMError")

        self.test_recorder.stage_pywbem_result([], exc)

        result_exc = "Exception:test_id None('CIMError(6...)"

        capture.check(
            ('pywbem.api.test_id', 'DEBUG', result_exc),
        )

    def test_invokemethod_int(self, capture, instance_wp_tuple):
        # pylint: disable=redefined-outer-name
        """
        Test invoke method log
        """

        instance = instance_wp_tuple[0]
        instancename = instance.path

        self.recorder_setup(detail_level=11)

        return_val = 0
        params = [('StringParam', 'Spotty'),
                  ('Uint8', Uint8(1)),
                  ('Sint8', Sint8(2))]

        self.test_recorder.stage_pywbem_args(method='InvokeMethod',
                                             MethodName='Blah',
                                             ObjectName=instancename,
                                             Params=OrderedDict(params))

        self.test_recorder.stage_pywbem_result((return_val, params),
                                               None)

        result_req = "Request:test_id InvokeMethod(MethodName=...)"

        result_ret = "Return:test_id InvokeMethod((0, [('Stri...)"

        capture.check(
            ('pywbem.api.test_id', 'DEBUG', result_req),
            ('pywbem.api.test_id', 'DEBUG', result_ret),
        )

    def test_invokemethod_summary(self, capture, instance_wp_tuple):
        # pylint: disable=redefined-outer-name
        """
        Test invoke method log
        """

        instance = instance_wp_tuple[0]
        instancename = instance.path

        self.recorder_setup(detail_level='summary')

        return_val = 0
        params = [('StringParam', 'Spotty'),
                  ('Uint8', Uint8(1)),
                  ('Sint8', Sint8(2))]

        self.test_recorder.stage_pywbem_args(method='InvokeMethod',
                                             MethodName='Blah',
                                             ObjectName=instancename,
                                             Params=OrderedDict(params))

        self.test_recorder.stage_pywbem_result((return_val, params),
                                               None)

        result_req = (
            "Request:test_id InvokeMethod("
            "MethodName='Blah', "
            "ObjectName={!r}, "
            "Params=OrderedDict(["
            "('StringParam', 'Spotty'), "
            "('Uint8', Uint8(cimtype='uint8', minvalue=0, maxvalue=255, 1)), "
            "('Sint8', Sint8(cimtype='sint8', minvalue=-128, maxvalue=127, 2))"
            "]))".
            format(instancename))

        result_ret = "Return:test_id InvokeMethod(tuple )"

        capture.check(
            ('pywbem.api.test_id', 'DEBUG', result_req),
            ('pywbem.api.test_id', 'DEBUG', result_ret),
        )

    # TODO add tests for all for invoke method.


class TestExternLoggerDef(BaseLogOperationRecorderTests):
    """
    Test configuring loggers above level of our loggers
    """

    def test_root_logger(self, capture, instance_wp_tuple):
        # pylint: disable=redefined-outer-name
        """
        Create a logger using logging.basicConfig and generate logs
        """

        instance = instance_wp_tuple[0]
        instancename = instance.path
        classname = instance.classname

        logging.basicConfig(filename=TEST_OUTPUT_LOG, level=logging.DEBUG)

        detail_level_int = 10
        detail_level = {'api': detail_level_int, 'http': detail_level_int}

        # pylint: disable=attribute-defined-outside-init
        self.test_recorder = LogOperationRecorder('test_id',
                                                  detail_levels=detail_level)

        # We don't activate because we are not using wbemconnection, just
        # the recorder calls.
        self.test_recorder.stage_pywbem_args(
            method='EnumerateInstanceNames',
            ClassName=classname,
            LocalOnly=True,
            IncludeQualifiers=True,
            IncludeClassOrigin=True,
            PropertyList=['propertyblah', 'blah2'])

        exc = None
        result = [instancename, instancename]

        self.test_recorder.stage_pywbem_result(result, exc)

        result_req = "Request:test_id EnumerateInstanceNames(ClassName=...)"

        result_ret = "Return:test_id EnumerateInstanceNames([CIMInstan...)"

        capture.check(
            ('pywbem.api.test_id', 'DEBUG', result_req),
            ('pywbem.api.test_id', 'DEBUG', result_ret),
        )

    @pytest.mark.skip("Test unreliable exception not always the same")
    def test_pywbem_logger(self, capture):
        # pylint: disable=redefined-outer-name
        """
        Test executing a connection with an externally created handler. Note
        that this test inconsistently reports the text of the exception
        in that sometimes adds the message  "[Errno 113] No route to host" and
        sometimes the message "timed out".
        """

        logger = logging.getLogger('pywbem')
        handler = logging.FileHandler(TEST_OUTPUT_LOG)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        configure_logger('api', detail_level='summary', connection=True,
                         propagate=True)
        try:
            conn = WBEMConnection('http://blah:5988', timeout=1)

            conn.GetClass('blah')
        except Exception:  # pylint: disable=broad-except
            pass

        conn_id = conn.conn_id

        api_exp_log_id = 'pywbem.api.{0}'.format(conn_id)
        http_exp_log_id = 'pywbem.http.{0}'.format(conn_id)

        result_exc = _format(
            "Exception:{0} GetClass('ConnectionError(Socket error: "
            "[Errno 113] No route to host)')",
            conn_id)

        result_con = _format(
            "Connection:{0} WBEMConnection("
            "url='http://blah:5988', "
            "creds=None, "
            "conn_id={0!A}, "
            "default_namespace='root/cimv2', "
            "x509=None, "
            "ca_certs=None, "
            "no_verification=False, "
            "timeout=1, "
            "use_pull_operations=False, "
            "stats_enabled=False, "
            "recorders=['LogOperationRecorder'])",
            conn_id)

        result_req = _format(
            "Request:{0} GetClass("
            "ClassName='blah', "
            "IncludeClassOrigin=None, "
            "IncludeQualifiers=None, "
            "LocalOnly=None, "
            "PropertyList=None, "
            "namespace=None)",
            conn_id)

        result_hreq = _format(
            "Request:{0} POST /cimom 11 http://blah:5988 "
            "CIMOperation:'MethodCall' "
            "CIMMethod:'GetClass' "
            "CIMObject:u'root/cimv2'\n"
            '<?xml version="1.0" encoding="utf-8" ?>\n'
            '<CIM CIMVERSION="2.0" DTDVERSION="2.0">'
            '<MESSAGE ID="1001" PROTOCOLVERSION="1.0">'
            '<SIMPLEREQ>'
            '<IMETHODCALL NAME="GetClass">'
            '<LOCALNAMESPACEPATH>'
            '<NAMESPACE NAME="root"/>'
            '<NAMESPACE NAME="cimv2"/>'
            '</LOCALNAMESPACEPATH>'
            '<IPARAMVALUE NAME="ClassName">'
            '<CLASSNAME NAME="blah"/>'
            '</IPARAMVALUE>'
            '</IMETHODCALL>'
            '</SIMPLEREQ>'
            '</MESSAGE>'
            '</CIM>',
            conn_id)

        capture.check(
            (api_exp_log_id, 'DEBUG', result_con),
            (api_exp_log_id, 'DEBUG', result_req),
            (http_exp_log_id, 'DEBUG', result_hreq),
            (api_exp_log_id, 'DEBUG', result_exc),
        )


class TestLoggingEndToEnd(BaseLogOperationRecorderTests):
    """
    Test the examples documented in _logging.py document string. Because
    there is not logging until the first http request, these extend the
    examples to actually issue a request.  Therefore, they use the mocker
    to emulate a server

    """

    def build_repo(self, namespace):
        """Build a CIM repository using FakedWBEMConnection"""
        skip_if_moftab_regenerated()

        schema = install_test_dmtf_schema()
        partial_schema = """
            #pragma locale ("en_US")
            #pragma include ("Interop/CIM_ObjectManager.mof")
            """

        conn = FakedWBEMConnection(default_namespace=namespace)
        conn.compile_mof_string(partial_schema, namespace=namespace,
                                search_paths=[schema.schema_mof_dir])
        return conn

    def test_1(self, capture):
        # pylint: disable=redefined-outer-name
        """
        Configure the "pywbem.api" logger for summary information output to a
        file and activate that logger for all subsequently created
        :class:`~pywbem.WBEMConnection` objects.
        NOTE: We changed from example to log to file and use log_captyre
        """
        skip_if_moftab_regenerated()

        # setup schema in test because we configure before we create the
        # connection in this test.
        namespace = 'root/blah'
        schema = install_test_dmtf_schema()
        partial_schema = """
            #pragma locale ("en_US")
            #pragma include ("Interop/CIM_ObjectManager.mof")
            """
        conn = FakedWBEMConnection(default_namespace=namespace)
        conn.compile_mof_string(partial_schema, namespace=namespace,
                                search_paths=[schema.schema_mof_dir])

        configure_logger('api', log_dest='file',
                         detail_level='summary',
                         log_filename=TEST_OUTPUT_LOG,
                         connection=conn, propagate=True)
        conn.GetClass('CIM_ObjectManager', namespace=namespace)

        conn_id = conn.conn_id

        api_exp_log_id = 'pywbem.api.{0}'.format(conn_id)

        result_con = _format(
            "Connection:{0} FakedWBEMConnection("
            "response_delay=None, "
            "super=WBEMConnection("
            "url='http://FakedUrl:5988', "
            "creds=None, "
            "default_namespace={1!A}, ...))",
            conn_id, namespace)

        result_req = _format(
            "Request:{0} GetClass("
            "ClassName='CIM_ObjectManager', "
            "IncludeClassOrigin=None, "
            "IncludeQualifiers=None, "
            "LocalOnly=None, "
            "PropertyList=None, "
            "namespace={1!A})",
            conn_id, namespace)

        result_ret = _format(
            "Return:{0} GetClass(CIMClass CIM_ObjectManager)",
            conn_id)

        capture.check(
            (api_exp_log_id, 'DEBUG', result_con),
            (api_exp_log_id, 'DEBUG', result_req),
            (api_exp_log_id, 'DEBUG', result_ret)
        )

    def test_2(self, capture):
        # pylint: disable=redefined-outer-name
        """
        Configure and activate a single :class:`~pywbem.WBEMConnection` object
        logger for output of summary information for both "pywbem.api" and
        "pywbem.http"::
        Differs from example in that we set detail_level to limit output for
        test
        """
        namespace = 'root/blah'
        conn = self.build_repo(namespace)
        configure_logger('all', log_dest='file',
                         log_filename=TEST_OUTPUT_LOG,
                         detail_level=10,
                         connection=conn, propagate=True)
        conn.GetClass('CIM_ObjectManager', namespace=namespace)

        conn_id = conn.conn_id

        api_exp_log_id = 'pywbem.api.{0}'.format(conn_id)

        result_con = _format("Connection:{0} FakedWBEMC...", conn_id)

        result_req = _format("Request:{0} GetClass(ClassName=...)", conn_id)

        result_ret = _format("Return:{0} GetClass(CIMClass(c...)", conn_id)

        capture.check(
            (api_exp_log_id, 'DEBUG', result_con),
            (api_exp_log_id, 'DEBUG', result_req),
            (api_exp_log_id, 'DEBUG', result_ret),
        )

    def test_3(self, capture):
        # pylint: disable=redefined-outer-name
        """
        Configure a single pywbem connection with standard Python logger
        methods by defining the root logger with basicConfig
        Differs from example in that we set detail_level to limit output for
        test.
        Does not produce http request/response info because when using the
        pywbem_mock, no http is generated.
        """
        logging.basicConfig(filename='example.log', level=logging.DEBUG)
        namespace = 'root/blah'
        conn = self.build_repo(namespace)

        # Define the detail_level and WBEMConnection object to activate.
        configure_logger('all', detail_level=10, connection=conn,
                         propagate=True)

        # logging_tree_printout()

        conn.GetClass('CIM_ObjectManager', namespace=namespace)

        conn_id = conn.conn_id

        api_exp_log_id = 'pywbem.api.{0}'.format(conn_id)

        result_con = _format("Connection:{0} FakedWBEMC...", conn_id)

        result_req = _format("Request:{0} GetClass(ClassName=...)", conn_id)

        result_ret = _format("Return:{0} GetClass(CIMClass(c...)", conn_id)

        capture.check(
            (api_exp_log_id, 'DEBUG', result_con),
            (api_exp_log_id, 'DEBUG', result_req),
            (api_exp_log_id, 'DEBUG', result_ret),
        )

    def test_4(self, capture):
        # pylint: disable=redefined-outer-name
        """
        Configure a single pywbem connection with standard Python logger
        methods by defining the root logger with basicConfig
        Differs from example in that we set detail_level to limit output for
        test
        """
        logging.basicConfig(filename='basicconfig.log', level=logging.DEBUG)
        namespace = 'root/blah'
        conn = self.build_repo(namespace)

        # Define the detail_level and WBEMConnection object to activate.
        configure_logger('api', detail_level=10, connection=conn,
                         propagate=True)

        # logging_tree_printout()

        conn.GetClass('CIM_ObjectManager', namespace=namespace)

        conn_id = conn.conn_id

        api_exp_log_id = 'pywbem.api.{0}'.format(conn_id)

        result_con = _format("Connection:{0} FakedWBEMC...", conn_id)

        result_req = _format("Request:{0} GetClass(ClassName=...)", conn_id)

        result_ret = _format("Return:{0} GetClass(CIMClass(c...)", conn_id)

        capture.check(
            (api_exp_log_id, 'DEBUG', result_con),
            (api_exp_log_id, 'DEBUG', result_req),
            (api_exp_log_id, 'DEBUG', result_ret),
        )

    def test_5(self, capture):
        # pylint: disable=redefined-outer-name
        """
        Configure a single pywbem connection with standard Python logger
        methods by defining the root logger with basicConfig
        Differs from example in that we set detail_level to limit output for
        test. The basic logger should have no effect since pywbem sets the
        NULLHandler at the pywbem level.
        """
        logging.basicConfig(filename='basicconfig.log', level=logging.DEBUG)
        namespace = 'root/blah'
        conn = self.build_repo(namespace)

        # Define the detail_level and WBEMConnection object to activate.
        configure_logger('api', detail_level=10, connection=conn,
                         propagate=True)

        # logging_tree_printout()

        conn.GetClass('CIM_ObjectManager', namespace=namespace)

        conn_id = conn.conn_id

        api_exp_log_id = 'pywbem.api.{0}'.format(conn_id)

        result_con = _format("Connection:{0} FakedWBEMC...", conn_id)

        result_req = _format("Request:{0} GetClass(ClassName=...)", conn_id)

        result_ret = _format("Return:{0} GetClass(CIMClass(c...)", conn_id)

        capture.check(
            (api_exp_log_id, 'DEBUG', result_con),
            (api_exp_log_id, 'DEBUG', result_req),
            (api_exp_log_id, 'DEBUG', result_ret)
        )

    def test_6(self, capture):
        # pylint: disable=redefined-outer-name
        """
        Configure a http logger with detail_level='all' and
        a log config with just 'http'  (which produces no output because the
        mocker does not generate http requests or responses) and at the
        same time setting the logging basic logger which we do not use.
        This test ability to generate connection log when only http log is
        activated.
        """
        logging.basicConfig(filename='example.log', level=logging.DEBUG)
        namespace = 'root/blah'
        conn = self.build_repo(namespace)

        # Define the detail_level and WBEMConnection object to activate.
        configure_logger('http', detail_level='all', log_dest='file',
                         log_filename=TEST_OUTPUT_LOG,
                         connection=conn, propagate=True)

        conn.GetClass('CIM_ObjectManager', namespace=namespace)

        conn_id = conn.conn_id

        http_exp_log_id = 'pywbem.http.{0}'.format(conn_id)

        result_con = _format(
            "Connection:{0} FakedWBEMConnection("
            "response_delay=None, "
            "disable_pull_operations=False "
            "super=WBEMConnection("
            "url='http://FakedUrl:5988', "
            "creds=None, "
            "conn_id={0!A}, "
            "default_namespace={1!A}, "
            "x509=None, "
            "ca_certs=None, "
            "no_verification=False, "
            "timeout=None, "
            "use_pull_operations=False, "
            "stats_enabled=False, "
            "recorders=['LogOperationRecorder']))",
            conn_id, namespace)

        capture.check(
            (http_exp_log_id, 'DEBUG', result_con)
        )

    def test_7(self, capture):
        # pylint: disable=redefined-outer-name
        """
        Configure a http logger with detail_level='all', log_dest=none
        a log config with just 'http'  (which produces no output because the
        mocker does not generate http requests or responses) and at the
        same time setting the logging basic logger which we do not use.
        This test ability to generate connection log when only http log is
        activated.
        """
        logging.basicConfig(filename='example.log', level=logging.DEBUG)
        namespace = 'root/blah'
        conn = self.build_repo(namespace)

        # Define the detail_level and WBEMConnection object to activate.
        configure_logger('http', detail_level='all', log_dest=None,
                         connection=conn, propagate=True)

        conn.GetClass('CIM_ObjectManager', namespace=namespace)

        conn_id = conn.conn_id

        http_exp_log_id = 'pywbem.http.{0}'.format(conn_id)

        result_con = _format(
            "Connection:{0} FakedWBEMConnection("
            "response_delay=None, "
            "disable_pull_operations=False "
            "super=WBEMConnection("
            "url='http://FakedUrl:5988', "
            "creds=None, "
            "conn_id={0!A}, "
            "default_namespace={1!A}, "
            "x509=None, "
            "ca_certs=None, "
            "no_verification=False, "
            "timeout=None, "
            "use_pull_operations=False, "
            "stats_enabled=False, "
            "recorders=['LogOperationRecorder']))",
            conn_id, namespace)

        capture.check(
            (http_exp_log_id, 'DEBUG', result_con)
        )

    def test_8(self, capture):
        # pylint: disable=redefined-outer-name
        """
        Configure a http logger with detail_level='all' and
        a log config with just 'http'  (which produces no output because the
        mocker does not generate http requests or responses) and at the
        same time setting the logging basic logger which we do not use.
        This test ability to generate connection log when only http log is
        activated.
        """
        msg_format = '%(asctime)s-%(name)s-%(message)s'
        handler = logging.FileHandler(TEST_OUTPUT_LOG, encoding="UTF-8")
        handler.setFormatter(logging.Formatter(msg_format))
        logger = logging.getLogger('pywbem')
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)

        namespace = 'root/blah'
        conn = self.build_repo(namespace)

        # Define the detail_level and WBEMConnection object to activate.
        configure_logger('http', detail_level='all', log_dest=None,
                         connection=conn, propagate=True)

        conn.GetClass('CIM_ObjectManager', namespace=namespace)

        conn_id = conn.conn_id

        http_exp_log_id = 'pywbem.http.{0}'.format(conn_id)

        result_con = _format(
            "Connection:{0} FakedWBEMConnection("
            "response_delay=None, "
            "disable_pull_operations=False "
            "super=WBEMConnection("
            "url='http://FakedUrl:5988', "
            "creds=None, "
            "conn_id={0!A}, "
            "default_namespace={1!A}, "
            "x509=None, "
            "ca_certs=None, "
            "no_verification=False, "
            "timeout=None, "
            "use_pull_operations=False, "
            "stats_enabled=False, "
            "recorders=['LogOperationRecorder']))",
            conn_id, namespace)

        capture.check(
            (http_exp_log_id, 'DEBUG', result_con)
        )

    def test_9(self, capture):
        # pylint: disable=redefined-outer-name
        """
        Configure a http logger with detail_level='all' and
        a log config with just 'http'  (which produces no output because the
        mocker does not generate http requests or responses) and at the
        same time setting the logging basic logger which we do not use.
        This test ability to generate connection log when only http log is
        activated.
        """

        namespace = 'root/blah'
        conn = self.build_repo(namespace)

        # Define the detail_level and WBEMConnection object to activate.
        configure_logger('http', detail_level='all', log_dest=None,
                         connection=conn, propagate=True)

        conn.GetClass('CIM_ObjectManager', namespace=namespace)

        conn_id = conn.conn_id

        http_exp_log_id = 'pywbem.http.{0}'.format(conn_id)

        result_con = _format(
            "Connection:{0} FakedWBEMConnection("
            "response_delay=None, "
            "disable_pull_operations=False "
            "super=WBEMConnection("
            "url='http://FakedUrl:5988', "
            "creds=None, "
            "conn_id={0!A}, "
            "default_namespace={1!A}, "
            "x509=None, "
            "ca_certs=None, "
            "no_verification=False, "
            "timeout=None, "
            "use_pull_operations=False, "
            "stats_enabled=False, "
            "recorders=['LogOperationRecorder']))",
            conn_id, namespace)

        capture.check(
            (http_exp_log_id, 'DEBUG', result_con)
        )

    def test_10(self, capture):
        # pylint: disable=redefined-outer-name
        """
        Configure a http logger with detail_level='all' and
        a log config with just 'http'  (which produces no output because the
        mocker does not generate http requests or responses) and at the
        same time setting the logging basic logger which we do not use.
        This test ability to generate connection log when only http log is
        activated.
        """

        namespace = 'root/blah'
        # Define the detail_level and WBEMConnection object to activate.
        configure_logger('http', detail_level='all',
                         connection=True, propagate=True)
        conn = self.build_repo(namespace)

        conn.GetClass('CIM_ObjectManager', namespace=namespace)

        conn_id = conn.conn_id

        http_exp_log_id = 'pywbem.http.{0}'.format(conn_id)

        result_con = _format(
            "Connection:{0} FakedWBEMConnection("
            "response_delay=None, "
            "disable_pull_operations=None "
            "super=WBEMConnection("
            "url='http://FakedUrl:5988', "
            "creds=None, "
            "conn_id={0!A}, "
            "default_namespace={1!A}, "
            "x509=None, "
            "ca_certs=None, "
            "no_verification=False, "
            "timeout=None, "
            "use_pull_operations=False, "
            "stats_enabled=False, "
            "recorders=['LogOperationRecorder']))",
            conn_id, namespace)

        capture.check(
            (http_exp_log_id, 'DEBUG', result_con)
        )

    def test_err(self, capture):
        # pylint: disable=redefined-outer-name
        """
        Test configure_logger exception
        """
        namespace = 'root/blah'
        conn = self.build_repo(namespace)

        # Define the detail_level and WBEMConnection object to activate.

        with pytest.raises(ValueError):
            configure_logger('api', detail_level='blah', connection=conn,
                             propagate=True)

        capture.check()


TESTCASES_COPY_LOGRECORDER = [

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * init_kwargs: keyword args for LogOperationRecorder init
    #   * enable_recorder: Boolean that causes recorders to be enabled
    #   * record_operation: Boolean that causes an operation to be performed
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for
    #   debugger

    (
        "Only required init parameters",
        dict(
            init_kwargs=dict(
                conn_id='test_id',
            ),
            enable_recorder=False,
            record_operation=False,
        ),
        None, None, True
    ),
    (
        "All init parameters",
        dict(
            init_kwargs=dict(
                conn_id='test_id',
                detail_levels=None,
            ),
            enable_recorder=False,
            record_operation=False,
        ),
        None, None, True
    ),
    (
        "With recorder enabled",
        dict(
            init_kwargs=dict(
                conn_id='test_id',
                detail_levels=None,
            ),
            enable_recorder=True,
            record_operation=False,
        ),
        None, None, True
    ),
    (
        "With recorder enabled, operation performed",
        dict(
            init_kwargs=dict(
                conn_id='test_id',
                detail_levels=None,
            ),
            enable_recorder=True,
            record_operation=True,
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_COPY_LOGRECORDER)
@simplified_test_function
def test_copy_logrecorder(
        testcase, init_kwargs, enable_recorder, record_operation):
    """Test LogOperationRecorder.copy()"""

    rec = LogOperationRecorder(**init_kwargs)

    if enable_recorder:
        rec.enable()

    if record_operation:
        rec.stage_pywbem_args(
            method='GetQualifier', QualifierName='Abstract')
        rec.stage_pywbem_result(
            CIMQualifier('Abstract', type='boolean', value=True), None)
        rec.stage_http_request(
            'test_id', 11, 'http://localhost', '/cimon', 'POST', {}, b'<CIM/>')
        rec.stage_http_response1(
            'test_id', 11, 200, 'OK', {})
        rec.stage_http_response2(b'<CIM/>')
        rec.record_staged()

    # The code to be tested
    cpy = rec.copy()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    # pylint: disable=protected-access,unidiomatic-type-check

    # Verify attributes that should have been copied

    assert_copy(cpy.detail_levels, rec.detail_levels)
    assert_copy(cpy.api_detail_level, rec.api_detail_level)
    assert_copy(cpy.http_detail_level, rec.http_detail_level)
    assert_copy(cpy.api_maxlen, rec.api_maxlen)
    assert_copy(cpy.http_maxlen, rec.http_maxlen)

    # Verify attributes that should have been reset

    assert cpy._pywbem_method is None
    assert cpy._pywbem_args is None
    assert cpy._pywbem_result_ret is None
    assert cpy._pywbem_result_exc is None
    assert cpy._http_request_version is None
    assert cpy._http_request_url is None
    assert cpy._http_request_target is None
    assert cpy._http_request_method is None
    assert cpy._http_request_headers is None
    assert cpy._http_request_payload is None
    assert cpy._http_response_version is None
    assert cpy._http_response_status is None
    assert cpy._http_response_reason is None
    assert cpy._http_response_headers is None
    assert cpy._http_response_payload is None

    # Logger objects are obtained via logging.getLogger() so they should be
    # the same objects.
    assert type(cpy.apilogger) is type(rec.apilogger)  # noqa: E721
    assert id(cpy.apilogger) == id(rec.apilogger)
    assert type(cpy.httplogger) is type(rec.httplogger)  # noqa: E721
    assert id(cpy.httplogger) == id(rec.httplogger)

    # Verify attributes that have been treated specially

    assert cpy._conn_id == rec._conn_id  # TODO: verify

    # pylint: enable=protected-access,unidiomatic-type-check


TESTCASES_COPY_TESTCLIENTRECORDER = [

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * init_kwargs: Additional keyword args for TestClientRecorder init
    #   * enable_recorder: Boolean that causes recorders to be enabled
    #   * record_operation: Boolean that causes an operation to be performed
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for
    #   debugger

    (
        "Not enabled",
        dict(
            init_kwargs={},
            enable_recorder=False,
            record_operation=False,
        ),
        None, None, True
    ),
    (
        "With recorder enabled",
        dict(
            init_kwargs={},
            enable_recorder=True,
            record_operation=False,
        ),
        None, None, True
    ),
    (
        "With recorder enabled, operation performed",
        dict(
            init_kwargs={},
            enable_recorder=True,
            record_operation=True,
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_COPY_TESTCLIENTRECORDER)
@simplified_test_function
def test_copy_testclientrecorder(
        testcase, init_kwargs, enable_recorder, record_operation):
    """Test TestClientRecorder.copy()"""

    with io.open(DEV_NULL, 'a', encoding='utf-8') as dev_null:

        rec = _TestClientRecorder(dev_null, **init_kwargs)

        if enable_recorder:
            rec.enable()

        if record_operation:
            rec.stage_pywbem_args(
                method='GetQualifier', QualifierName='Abstract')
            rec.stage_pywbem_result(
                CIMQualifier('Abstract', type='boolean', value=True), None)
            rec.stage_http_request(
                'test_id', 11, 'http://localhost', '/cimon', 'POST', {},
                b'<CIM/>')
            rec.stage_http_response1(
                'test_id', 11, 200, 'OK', {})
            rec.stage_http_response2(b'<CIM/>')
            rec.record_staged()

        # The code to be tested
        cpy = rec.copy()

        # Ensure that exceptions raised in the remainder of this function
        # are not mistaken as expected exceptions
        assert testcase.exp_exc_types is None

        # pylint: disable=protected-access,unidiomatic-type-check

        # Verify attributes that should have been the same object

        assert cpy._fp is rec._fp

        # Verify attributes that should have been reset

        assert cpy._pywbem_method is None
        assert cpy._pywbem_args is None
        assert cpy._pywbem_result_ret is None
        assert cpy._pywbem_result_exc is None
        assert cpy._http_request_version is None
        assert cpy._http_request_url is None
        assert cpy._http_request_target is None
        assert cpy._http_request_method is None
        assert cpy._http_request_headers is None
        assert cpy._http_request_payload is None
        assert cpy._http_response_version is None
        assert cpy._http_response_status is None
        assert cpy._http_response_reason is None
        assert cpy._http_response_headers is None
        assert cpy._http_response_payload is None

        # pylint: enable=protected-access,unidiomatic-type-check
