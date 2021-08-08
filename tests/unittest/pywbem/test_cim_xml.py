"""
Unit tests for pywbem _cim_xml.py module.
"""

from __future__ import absolute_import

try:
    from collections.abc import Iterable
except ImportError:  # py2
    # pylint: disable=deprecated-class
    from collections import Iterable
import six
import pytest

from ..utils.validate import validate_cim_xml, CIMXMLValidationError, \
    assert_xml_equal, DTD_VERSION
from ..utils.pytest_extensions import simplified_test_function

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import _cim_xml  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


def iter_flattened(lst):
    """
    Flatten the arbitrarily nested input list of lists, and yield each
    resulting list item.
    """
    for item in lst:
        if isinstance(item, Iterable) and \
                not isinstance(item, six.string_types):
            for sub_item in iter_flattened(item):
                yield sub_item
        else:
            yield item


# The following functions return a simple but valid CIM-XML element, including
# child elements. This simplifies the definition of testcases for the more
# complex CIM-XML elements.
# The *_node() functions return the pywbem CIM-XML node, and the same-named
# *_str() functions return that node as a (possibly nested) list of XML
# strings.


def simple_HOST_node(name='leonardo'):
    """
    Return a simple HOST as a _cim_xml node.
    """
    return _cim_xml.HOST(name)


def simple_HOST_str(name='leonardo'):
    """
    Return a simple HOST as a list of XML strings.
    """
    return [
        '<HOST>{name}</HOST>'.format(name=name),
    ]


def simple_NAMESPACE_node(name='myns'):
    """
    Return a simple NAMESPACE as a _cim_xml node.
    """
    return _cim_xml.NAMESPACE(name)


def simple_NAMESPACE_str(name='myns'):
    """
    Return a simple NAMESPACE as a list of XML strings.
    """
    return [
        '<NAMESPACE NAME="{name}"/>'.format(name=name),
    ]


def simple_LOCALNAMESPACEPATH_node():
    """
    Return a simple LOCALNAMESPACEPATH as a _cim_xml node.
    """
    return _cim_xml.LOCALNAMESPACEPATH(
        [
            simple_NAMESPACE_node('root'),
            simple_NAMESPACE_node('cimv2'),
        ]
    )


def simple_LOCALNAMESPACEPATH_str():
    """
    Return a simple LOCALNAMESPACEPATH as a nested list of XML strings.
    """
    return [
        '<LOCALNAMESPACEPATH>',
        simple_NAMESPACE_str('root'),
        simple_NAMESPACE_str('cimv2'),
        '</LOCALNAMESPACEPATH>',
    ]


def simple_NAMESPACEPATH_node():
    """
    Return a simple NAMESPACEPATH as a _cim_xml node.
    """
    return _cim_xml.NAMESPACEPATH(
        simple_HOST_node(),
        simple_LOCALNAMESPACEPATH_node(),
    )


def simple_NAMESPACEPATH_str():
    """
    Return a simple NAMESPACEPATH as a nested list of XML strings.
    """
    return [
        '<NAMESPACEPATH>',
        simple_HOST_str(),
        simple_LOCALNAMESPACEPATH_str(),
        '</NAMESPACEPATH>',
    ]


def simple_CLASSNAME_node(name='MyClass'):
    """
    Return a simple CLASSNAME as a _cim_xml node.
    """
    return _cim_xml.CLASSNAME(name)


def simple_CLASSNAME_str(name='MyClass'):
    """
    Return a simple CLASSNAME as a list of XML strings.
    """
    return [
        '<CLASSNAME NAME="{name}"/>'.format(name=name),
    ]


def simple_LOCALCLASSPATH_node(name='MyClass'):
    """
    Return a simple LOCALCLASSPATH as a _cim_xml node.
    """
    return _cim_xml.LOCALCLASSPATH(
        simple_LOCALNAMESPACEPATH_node(),
        simple_CLASSNAME_node(name),
    )


def simple_LOCALCLASSPATH_str(name='MyClass'):
    """
    Return a simple LOCALCLASSPATH as a nested list of XML strings.
    """
    return [
        '<LOCALCLASSPATH>',
        simple_LOCALNAMESPACEPATH_str(),
        simple_CLASSNAME_str(name),
        '</LOCALCLASSPATH>',
    ]


def simple_CLASSPATH_node(name='MyClass'):
    """
    Return a simple CLASSPATH as a _cim_xml node.
    """
    return _cim_xml.CLASSPATH(
        simple_NAMESPACEPATH_node(),
        simple_CLASSNAME_node(name),
    )


def simple_CLASSPATH_str(name='MyClass'):
    """
    Return a simple CLASSPATH as a nested list of XML strings.
    """
    return [
        '<CLASSPATH>',
        simple_NAMESPACEPATH_str(),
        simple_CLASSNAME_str(name),
        '</CLASSPATH>',
    ]


def simple_INSTANCENAME_node(name='MyClass'):
    """
    Return a simple INSTANCENAME as a _cim_xml node.
    """
    return _cim_xml.INSTANCENAME(
        name,
        [
            _cim_xml.KEYBINDING(
                'type',
                _cim_xml.KEYVALUE('dog', 'string')
            ),
            _cim_xml.KEYBINDING(
                'age',
                _cim_xml.KEYVALUE('2', 'numeric')
            ),
        ],
    )


def simple_INSTANCENAME_str(name='MyClass'):
    """
    Return a simple INSTANCENAME as a list of XML strings.
    """
    return [
        '<INSTANCENAME CLASSNAME="{name}">'.format(name=name),
        '<KEYBINDING NAME="type">',
        '<KEYVALUE VALUETYPE="string">dog</KEYVALUE>',
        '</KEYBINDING>',
        '<KEYBINDING NAME="age">',
        '<KEYVALUE VALUETYPE="numeric">2</KEYVALUE>',
        '</KEYBINDING>',
        '</INSTANCENAME>',
    ]


def simple_OBJECTPATH_node(name='MyClass'):
    """
    Return a simple OBJECTPATH as a _cim_xml node.
    """
    return _cim_xml.OBJECTPATH(
        simple_INSTANCEPATH_node(name),
    )


def simple_OBJECTPATH_str(name='MyClass'):
    """
    Return a simple OBJECTPATH as a nested list of XML strings.
    """
    return [
        '<OBJECTPATH>',
        simple_INSTANCEPATH_str(name),
        '</OBJECTPATH>',
    ]


def simple_LOCALINSTANCEPATH_node(name='MyClass'):
    """
    Return a simple LOCALINSTANCEPATH as a _cim_xml node.
    """
    return _cim_xml.LOCALINSTANCEPATH(
        simple_LOCALNAMESPACEPATH_node(),
        simple_INSTANCENAME_node(name),
    )


def simple_LOCALINSTANCEPATH_str(name='MyClass'):
    """
    Return a simple LOCALINSTANCEPATH as a nested list of XML strings.
    """
    return [
        '<LOCALINSTANCEPATH>',
        simple_LOCALNAMESPACEPATH_str(),
        simple_INSTANCENAME_str(name),
        '</LOCALINSTANCEPATH>',
    ]


def simple_INSTANCEPATH_node(name='MyClass'):
    """
    Return a simple INSTANCEPATH as a _cim_xml node.
    """
    return _cim_xml.INSTANCEPATH(
        simple_NAMESPACEPATH_node(),
        simple_INSTANCENAME_node(name),
    )


def simple_INSTANCEPATH_str(name='MyClass'):
    """
    Return a simple INSTANCEPATH as a nested list of XML strings.
    """
    return [
        '<INSTANCEPATH>',
        simple_NAMESPACEPATH_str(),
        simple_INSTANCENAME_str(name),
        '</INSTANCEPATH>',
    ]


def simple_VALUE_OBJECT_node(name='MyClass'):
    """
    Return a simple VALUE.OBJECT with a CLASS as a _cim_xml node.
    """
    return _cim_xml.VALUE_OBJECT(
        simple_CLASS_node(name),
    )


def simple_VALUE_OBJECT_str(name='MyClass'):
    """
    Return a simple VALUE.OBJECT with a CLASS as a nested list of XML strings.
    """
    return [
        '<VALUE.OBJECT>',
        simple_CLASS_str(name),
        '</VALUE.OBJECT>',
    ]


def simple_VALUE_NAMEDINSTANCE_node(name='MyClass'):
    """
    Return a simple VALUE.NAMEDINSTANCE as a _cim_xml node.
    """
    return _cim_xml.VALUE_NAMEDINSTANCE(
        simple_INSTANCENAME_node(name),
        simple_INSTANCE_node(name),
    )


def simple_VALUE_NAMEDINSTANCE_str(name='MyClass'):
    """
    Return a simple VALUE.NAMEDINSTANCE as a nested list of XML strings.
    """
    return [
        '<VALUE.NAMEDINSTANCE>',
        simple_INSTANCENAME_str(name),
        simple_INSTANCE_str(name),
        '</VALUE.NAMEDINSTANCE>',
    ]


def simple_VALUE_NAMEDOBJECT_node(name='MyClass'):
    """
    Return a simple VALUE.NAMEDOBJECT with a CLASS as a _cim_xml node.
    """
    return _cim_xml.VALUE_NAMEDOBJECT(
        simple_CLASS_node(name),
    )


def simple_VALUE_NAMEDOBJECT_str(name='MyClass'):
    """
    Return a simple VALUE.NAMEDOBJECT with a CLASS as a (nested) list of XML
    strings.
    """
    return [
        '<VALUE.NAMEDOBJECT>',
        simple_CLASS_str(name),
        '</VALUE.NAMEDOBJECT>',
    ]


def simple_VALUE_OBJECTWITHLOCALPATH_node(name='MyClass'):
    """
    Return a simple VALUE.OBJECTWITHLOCALPATH with a CLASS as a _cim_xml node.
    """
    return _cim_xml.VALUE_OBJECTWITHLOCALPATH(
        simple_LOCALCLASSPATH_node(name),
        simple_CLASS_node(name),
    )


def simple_VALUE_OBJECTWITHLOCALPATH_str(name='MyClass'):
    """
    Return a simple VALUE.OBJECTWITHLOCALPATH with a CLASS as a (nested) list
    of XML strings.
    """
    return [
        '<VALUE.OBJECTWITHLOCALPATH>',
        simple_LOCALCLASSPATH_str(name),
        simple_CLASS_str(name),
        '</VALUE.OBJECTWITHLOCALPATH>',
    ]


def simple_VALUE_OBJECTWITHPATH_node(name='MyClass'):
    """
    Return a simple VALUE.OBJECTWITHPATH with a CLASS as a _cim_xml node.
    """
    return _cim_xml.VALUE_OBJECTWITHPATH(
        simple_CLASSPATH_node(name),
        simple_CLASS_node(name),
    )


def simple_VALUE_OBJECTWITHPATH_str(name='MyClass'):
    """
    Return a simple VALUE.OBJECTWITHPATH with a CLASS as a (nested) list
    of XML strings.
    """
    return [
        '<VALUE.OBJECTWITHPATH>',
        simple_CLASSPATH_str(name),
        simple_CLASS_str(name),
        '</VALUE.OBJECTWITHPATH>',
    ]


def simple_VALUE_INSTANCEWITHPATH_node(name='MyClass'):
    """
    Return a simple VALUE.INSTANCEWITHPATH as a _cim_xml node.
    """
    return _cim_xml.VALUE_INSTANCEWITHPATH(
        simple_INSTANCEPATH_node(name),
        simple_INSTANCE_node(name),
    )


def simple_VALUE_INSTANCEWITHPATH_str(name='MyClass'):
    """
    Return a simple VALUE.INSTANCEWITHPATH as a (nested) list
    of XML strings.
    """
    return [
        '<VALUE.INSTANCEWITHPATH>',
        simple_INSTANCEPATH_str(name),
        simple_INSTANCE_str(name),
        '</VALUE.INSTANCEWITHPATH>',
    ]


def simple_CLASS_node(name='MyClass'):
    """
    Return a simple CLASS as a _cim_xml node.
    """
    return _cim_xml.CLASS(name)


def simple_CLASS_str(name='MyClass'):
    """
    Return a simple CLASS as a list of XML strings.
    """
    return [
        '<CLASS NAME="{name}"/>'.format(name=name),
    ]


def simple_INSTANCE_node(name='MyClass'):
    """
    Return a simple INSTANCE as a _cim_xml node.
    """
    return _cim_xml.INSTANCE(name)


def simple_INSTANCE_str(name='MyClass'):
    """
    Return a simple INSTANCE as a list of XML strings.
    """
    return [
        '<INSTANCE CLASSNAME="{name}"/>'.format(name=name),
    ]


def simple_QUALIFIER_DECLARATION_node(name='MyQualifier', type_='string'):
    """
    Return a simple QUALIFIER.DECLARATION as a _cim_xml node.
    """
    return _cim_xml.QUALIFIER_DECLARATION(name, type_)


def simple_QUALIFIER_DECLARATION_str(name='MyQualifier', type_='string'):
    """
    Return a simple QUALIFIER.DECLARATION as a list of XML strings.
    """
    return [
        '<QUALIFIER.DECLARATION NAME="{name}" TYPE="{type}"/>'.
        format(name=name, type=type_),
    ]


TESTCASES_CIM_XML_NODE = [

    # Testcases for _cim_xml nodes.

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * xml_node: _cim_xml node to be tested (_cim_xml.CIMElement subclass).
    #   * exp_xml_str_list: Expected XML string of the _cim_xml node, as a
    #     (possibly nested) list of strings.
    #   * cdata_escaping: optional flag controlling whether escaping using
    #     CDATA sections is used when creating the XML, instead of XML escaping.
    #     Defaults to False.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Testcases for CIM element
    #
    #    <!ELEMENT CIM (MESSAGE | DECLARATION)>
    #    <!ATTLIST CIM
    #        CIMVERSION CDATA #REQUIRED
    #        DTDVERSION CDATA #REQUIRED>
    (
        "CIM with minimalistic MESSAGE",
        dict(
            xml_node=_cim_xml.CIM(
                _cim_xml.MESSAGE(
                    _cim_xml.SIMPLEREQ(
                        _cim_xml.IMETHODCALL(
                            'EnumerateInstances',
                            simple_LOCALNAMESPACEPATH_node(),
                        ),
                    ),
                    '1001', '1.4'),
                '2.7', '2.3'),
            exp_xml_str_list=[
                '<CIM CIMVERSION="2.7" DTDVERSION="2.3">',
                '<MESSAGE ID="1001" PROTOCOLVERSION="1.4">',
                '<SIMPLEREQ>',
                '<IMETHODCALL NAME="EnumerateInstances">',
                simple_LOCALNAMESPACEPATH_str(),
                '</IMETHODCALL>',
                '</SIMPLEREQ>',
                '</MESSAGE>',
                '</CIM>',
            ],
        ),
        None, None, True
    ),
    (
        "CIM with minimalistic DECLARATION",
        dict(
            xml_node=_cim_xml.CIM(
                _cim_xml.DECLARATION([
                    _cim_xml.DECLGROUP([
                    ]),
                ]),
                '2.7', '2.3'),
            exp_xml_str_list=[
                '<CIM CIMVERSION="2.7" DTDVERSION="2.3">',
                '<DECLARATION>',
                '<DECLGROUP/>',
                '</DECLARATION>',
                '</CIM>',
            ],
        ),
        None, None, True
    ),

    # Testcases for DECLARATION, DECLGROUP, DECLGROUP.WITHNAME,
    #  DECLGROUP.WITHPATH elements
    #
    #    <!ELEMENT DECLARATION (DECLGROUP | DECLGROUP.WITHNAME |
    #                           DECLGROUP.WITHPATH)+>
    #
    #    <!ELEMENT DECLGROUP ((LOCALNAMESPACEPATH | NAMESPACEPATH)?,
    #                         QUALIFIER.DECLARATION*, VALUE.OBJECT*)>
    #
    #    <!ELEMENT DECLGROUP.WITHNAME ((LOCALNAMESPACEPATH | NAMESPACEPATH)?,
    #                              QUALIFIER.DECLARATION*, VALUE.NAMEDOBJECT*)>
    #
    #    <!ELEMENT DECLGROUP.WITHPATH (VALUE.OBJECTWITHPATH |
    #                                  VALUE.OBJECTWITHLOCALPATH)*>
    (
        "DECLARATION with DECLGROUP with two qualifier declarations + "
        "two objects, no namespace path",
        dict(
            xml_node=_cim_xml.DECLARATION([
                _cim_xml.DECLGROUP([
                    simple_QUALIFIER_DECLARATION_node('Q1'),
                    simple_QUALIFIER_DECLARATION_node('Q2'),
                    simple_VALUE_OBJECT_node('C1'),
                    simple_VALUE_OBJECT_node('C2'),
                ]),
            ]),
            exp_xml_str_list=[
                '<DECLARATION>',
                '<DECLGROUP>',
                simple_QUALIFIER_DECLARATION_str('Q1'),
                simple_QUALIFIER_DECLARATION_str('Q2'),
                simple_VALUE_OBJECT_str('C1'),
                simple_VALUE_OBJECT_str('C2'),
                '</DECLGROUP>',
                '</DECLARATION>',
            ],
        ),
        None, None, True
    ),
    (
        "DECLARATION with DECLGROUP with two qualifier declarations + "
        "two objects, local namespace path",
        dict(
            xml_node=_cim_xml.DECLARATION([
                _cim_xml.DECLGROUP([
                    simple_LOCALNAMESPACEPATH_node(),
                    simple_QUALIFIER_DECLARATION_node('Q1'),
                    simple_QUALIFIER_DECLARATION_node('Q2'),
                    simple_VALUE_OBJECT_node('C1'),
                    simple_VALUE_OBJECT_node('C2'),
                ]),
            ]),
            exp_xml_str_list=[
                '<DECLARATION>',
                '<DECLGROUP>',
                simple_LOCALNAMESPACEPATH_str(),
                simple_QUALIFIER_DECLARATION_str('Q1'),
                simple_QUALIFIER_DECLARATION_str('Q2'),
                simple_VALUE_OBJECT_str('C1'),
                simple_VALUE_OBJECT_str('C2'),
                '</DECLGROUP>',
                '</DECLARATION>',
            ],
        ),
        None, None, True
    ),
    (
        "DECLARATION with DECLGROUP with two qualifier declarations + "
        "two objects, namespace path",
        dict(
            xml_node=_cim_xml.DECLARATION([
                _cim_xml.DECLGROUP([
                    simple_NAMESPACEPATH_node(),
                    simple_QUALIFIER_DECLARATION_node('Q1'),
                    simple_QUALIFIER_DECLARATION_node('Q2'),
                    simple_VALUE_OBJECT_node('C1'),
                    simple_VALUE_OBJECT_node('C2'),
                ]),
            ]),
            exp_xml_str_list=[
                '<DECLARATION>',
                '<DECLGROUP>',
                simple_NAMESPACEPATH_str(),
                simple_QUALIFIER_DECLARATION_str('Q1'),
                simple_QUALIFIER_DECLARATION_str('Q2'),
                simple_VALUE_OBJECT_str('C1'),
                simple_VALUE_OBJECT_str('C2'),
                '</DECLGROUP>',
                '</DECLARATION>',
            ],
        ),
        None, None, True
    ),
    (
        "DECLARATION with DECLGROUP.WITHNAME with two qualifier declarations + "
        "two named objects, no namespace path",
        dict(
            xml_node=_cim_xml.DECLARATION([
                _cim_xml.DECLGROUP_WITHNAME([
                    simple_QUALIFIER_DECLARATION_node('Q1'),
                    simple_QUALIFIER_DECLARATION_node('Q2'),
                    simple_VALUE_NAMEDOBJECT_node('C1'),
                    simple_VALUE_NAMEDOBJECT_node('C2'),
                ]),
            ]),
            exp_xml_str_list=[
                '<DECLARATION>',
                '<DECLGROUP.WITHNAME>',
                simple_QUALIFIER_DECLARATION_str('Q1'),
                simple_QUALIFIER_DECLARATION_str('Q2'),
                simple_VALUE_NAMEDOBJECT_str('C1'),
                simple_VALUE_NAMEDOBJECT_str('C2'),
                '</DECLGROUP.WITHNAME>',
                '</DECLARATION>',
            ],
        ),
        None, None, True
    ),
    (
        "DECLARATION with DECLGROUP.WITHNAME with two qualifier declarations + "
        "two named objects, local namespace path",
        dict(
            xml_node=_cim_xml.DECLARATION([
                _cim_xml.DECLGROUP_WITHNAME([
                    simple_LOCALNAMESPACEPATH_node(),
                    simple_QUALIFIER_DECLARATION_node('Q1'),
                    simple_QUALIFIER_DECLARATION_node('Q2'),
                    simple_VALUE_NAMEDOBJECT_node('C1'),
                    simple_VALUE_NAMEDOBJECT_node('C2'),
                ]),
            ]),
            exp_xml_str_list=[
                '<DECLARATION>',
                '<DECLGROUP.WITHNAME>',
                simple_LOCALNAMESPACEPATH_str(),
                simple_QUALIFIER_DECLARATION_str('Q1'),
                simple_QUALIFIER_DECLARATION_str('Q2'),
                simple_VALUE_NAMEDOBJECT_str('C1'),
                simple_VALUE_NAMEDOBJECT_str('C2'),
                '</DECLGROUP.WITHNAME>',
                '</DECLARATION>',
            ],
        ),
        None, None, True
    ),
    (
        "DECLARATION with DECLGROUP.WITHNAME with two qualifier declarations + "
        "two named objects, namespace path",
        dict(
            xml_node=_cim_xml.DECLARATION([
                _cim_xml.DECLGROUP_WITHNAME([
                    simple_NAMESPACEPATH_node(),
                    simple_QUALIFIER_DECLARATION_node('Q1'),
                    simple_QUALIFIER_DECLARATION_node('Q2'),
                    simple_VALUE_NAMEDOBJECT_node('C1'),
                    simple_VALUE_NAMEDOBJECT_node('C2'),
                ]),
            ]),
            exp_xml_str_list=[
                '<DECLARATION>',
                '<DECLGROUP.WITHNAME>',
                simple_NAMESPACEPATH_str(),
                simple_QUALIFIER_DECLARATION_str('Q1'),
                simple_QUALIFIER_DECLARATION_str('Q2'),
                simple_VALUE_NAMEDOBJECT_str('C1'),
                simple_VALUE_NAMEDOBJECT_str('C2'),
                '</DECLGROUP.WITHNAME>',
                '</DECLARATION>',
            ],
        ),
        None, None, True
    ),
    (
        "DECLARATION with DECLGROUP.WITHPATH with two qualifier declarations + "
        "two objects with path",
        dict(
            xml_node=_cim_xml.DECLARATION([
                _cim_xml.DECLGROUP_WITHPATH([
                    simple_VALUE_OBJECTWITHPATH_node('C1'),
                    simple_VALUE_OBJECTWITHPATH_node('C2'),
                    simple_VALUE_OBJECTWITHLOCALPATH_node('C1'),
                    simple_VALUE_OBJECTWITHLOCALPATH_node('C2'),
                ]),
            ]),
            exp_xml_str_list=[
                '<DECLARATION>',
                '<DECLGROUP.WITHPATH>',
                simple_VALUE_OBJECTWITHPATH_str('C1'),
                simple_VALUE_OBJECTWITHPATH_str('C2'),
                simple_VALUE_OBJECTWITHLOCALPATH_str('C1'),
                simple_VALUE_OBJECTWITHLOCALPATH_str('C2'),
                '</DECLGROUP.WITHPATH>',
                '</DECLARATION>',
            ],
        ),
        None, None, True
    ),
    (
        "DECLARATION with two DECLGROUP with "
        "one qualifier declaration + one object, no namespace path",
        dict(
            xml_node=_cim_xml.DECLARATION([
                _cim_xml.DECLGROUP([
                    simple_QUALIFIER_DECLARATION_node('Q1'),
                    simple_VALUE_OBJECT_node('C1'),
                ]),
                _cim_xml.DECLGROUP([
                    simple_QUALIFIER_DECLARATION_node('Q2'),
                    simple_VALUE_OBJECT_node('C2'),
                ]),
            ]),
            exp_xml_str_list=[
                '<DECLARATION>',
                '<DECLGROUP>',
                simple_QUALIFIER_DECLARATION_str('Q1'),
                simple_VALUE_OBJECT_str('C1'),
                '</DECLGROUP>',
                '<DECLGROUP>',
                simple_QUALIFIER_DECLARATION_str('Q2'),
                simple_VALUE_OBJECT_str('C2'),
                '</DECLGROUP>',
                '</DECLARATION>',
            ],
        ),
        None, None, True
    ),
    (
        "DECLARATION with with two DECLGROUP with "
        "one qualifier declaration + one object, local namespace path",
        dict(
            xml_node=_cim_xml.DECLARATION([
                _cim_xml.DECLGROUP([
                    simple_LOCALNAMESPACEPATH_node(),
                    simple_QUALIFIER_DECLARATION_node('Q1'),
                    simple_VALUE_OBJECT_node('C1'),
                ]),
                _cim_xml.DECLGROUP([
                    simple_LOCALNAMESPACEPATH_node(),
                    simple_QUALIFIER_DECLARATION_node('Q2'),
                    simple_VALUE_OBJECT_node('C2'),
                ]),
            ]),
            exp_xml_str_list=[
                '<DECLARATION>',
                '<DECLGROUP>',
                simple_LOCALNAMESPACEPATH_str(),
                simple_QUALIFIER_DECLARATION_str('Q1'),
                simple_VALUE_OBJECT_str('C1'),
                '</DECLGROUP>',
                '<DECLGROUP>',
                simple_LOCALNAMESPACEPATH_str(),
                simple_QUALIFIER_DECLARATION_str('Q2'),
                simple_VALUE_OBJECT_str('C2'),
                '</DECLGROUP>',
                '</DECLARATION>',
            ],
        ),
        None, None, True
    ),
    (
        "DECLARATION with two DECLGROUP with "
        "one qualifier declaration + one object, namespace path",
        dict(
            xml_node=_cim_xml.DECLARATION([
                _cim_xml.DECLGROUP([
                    simple_NAMESPACEPATH_node(),
                    simple_QUALIFIER_DECLARATION_node('Q1'),
                    simple_VALUE_OBJECT_node('C1'),
                ]),
                _cim_xml.DECLGROUP([
                    simple_NAMESPACEPATH_node(),
                    simple_QUALIFIER_DECLARATION_node('Q2'),
                    simple_VALUE_OBJECT_node('C2'),
                ]),
            ]),
            exp_xml_str_list=[
                '<DECLARATION>',
                '<DECLGROUP>',
                simple_NAMESPACEPATH_str(),
                simple_QUALIFIER_DECLARATION_str('Q1'),
                simple_VALUE_OBJECT_str('C1'),
                '</DECLGROUP>',
                '<DECLGROUP>',
                simple_NAMESPACEPATH_str(),
                simple_QUALIFIER_DECLARATION_str('Q2'),
                simple_VALUE_OBJECT_str('C2'),
                '</DECLGROUP>',
                '</DECLARATION>',
            ],
        ),
        None, None, True
    ),
    (
        "DECLARATION with two DECLGROUP.WITHNAME with "
        "one qualifier declaration + one named object, no namespace path",
        dict(
            xml_node=_cim_xml.DECLARATION([
                _cim_xml.DECLGROUP_WITHNAME([
                    simple_QUALIFIER_DECLARATION_node('Q1'),
                    simple_VALUE_NAMEDOBJECT_node('C1'),
                ]),
                _cim_xml.DECLGROUP_WITHNAME([
                    simple_QUALIFIER_DECLARATION_node('Q2'),
                    simple_VALUE_NAMEDOBJECT_node('C2'),
                ]),
            ]),
            exp_xml_str_list=[
                '<DECLARATION>',
                '<DECLGROUP.WITHNAME>',
                simple_QUALIFIER_DECLARATION_str('Q1'),
                simple_VALUE_NAMEDOBJECT_str('C1'),
                '</DECLGROUP.WITHNAME>',
                '<DECLGROUP.WITHNAME>',
                simple_QUALIFIER_DECLARATION_str('Q2'),
                simple_VALUE_NAMEDOBJECT_str('C2'),
                '</DECLGROUP.WITHNAME>',
                '</DECLARATION>',
            ],
        ),
        None, None, True
    ),
    (
        "DECLARATION with two DECLGROUP.WITHNAME with "
        "one qualifier declaration + one named object, local namespace path",
        dict(
            xml_node=_cim_xml.DECLARATION([
                _cim_xml.DECLGROUP_WITHNAME([
                    simple_LOCALNAMESPACEPATH_node(),
                    simple_QUALIFIER_DECLARATION_node('Q1'),
                    simple_VALUE_NAMEDOBJECT_node('C1'),
                ]),
                _cim_xml.DECLGROUP_WITHNAME([
                    simple_LOCALNAMESPACEPATH_node(),
                    simple_QUALIFIER_DECLARATION_node('Q2'),
                    simple_VALUE_NAMEDOBJECT_node('C2'),
                ]),
            ]),
            exp_xml_str_list=[
                '<DECLARATION>',
                '<DECLGROUP.WITHNAME>',
                simple_LOCALNAMESPACEPATH_str(),
                simple_QUALIFIER_DECLARATION_str('Q1'),
                simple_VALUE_NAMEDOBJECT_str('C1'),
                '</DECLGROUP.WITHNAME>',
                '<DECLGROUP.WITHNAME>',
                simple_LOCALNAMESPACEPATH_str(),
                simple_QUALIFIER_DECLARATION_str('Q2'),
                simple_VALUE_NAMEDOBJECT_str('C2'),
                '</DECLGROUP.WITHNAME>',
                '</DECLARATION>',
            ],
        ),
        None, None, True
    ),
    (
        "DECLARATION with DECLGROUP.WITHNAME with "
        "one qualifier declaration + one named object, namespace path",
        dict(
            xml_node=_cim_xml.DECLARATION([
                _cim_xml.DECLGROUP_WITHNAME([
                    simple_NAMESPACEPATH_node(),
                    simple_QUALIFIER_DECLARATION_node('Q1'),
                    simple_VALUE_NAMEDOBJECT_node('C1'),
                ]),
                _cim_xml.DECLGROUP_WITHNAME([
                    simple_NAMESPACEPATH_node(),
                    simple_QUALIFIER_DECLARATION_node('Q2'),
                    simple_VALUE_NAMEDOBJECT_node('C2'),
                ]),
            ]),
            exp_xml_str_list=[
                '<DECLARATION>',
                '<DECLGROUP.WITHNAME>',
                simple_NAMESPACEPATH_str(),
                simple_QUALIFIER_DECLARATION_str('Q1'),
                simple_VALUE_NAMEDOBJECT_str('C1'),
                '</DECLGROUP.WITHNAME>',
                '<DECLGROUP.WITHNAME>',
                simple_NAMESPACEPATH_str(),
                simple_QUALIFIER_DECLARATION_str('Q2'),
                simple_VALUE_NAMEDOBJECT_str('C2'),
                '</DECLGROUP.WITHNAME>',
                '</DECLARATION>',
            ],
        ),
        None, None, True
    ),
    (
        "DECLARATION with two DECLGROUP.WITHPATH with "
        "one qualifier declaration + one object with path",
        dict(
            xml_node=_cim_xml.DECLARATION([
                _cim_xml.DECLGROUP_WITHPATH([
                    simple_VALUE_OBJECTWITHPATH_node('C1'),
                    simple_VALUE_OBJECTWITHLOCALPATH_node('C1'),
                ]),
                _cim_xml.DECLGROUP_WITHPATH([
                    simple_VALUE_OBJECTWITHPATH_node('C2'),
                    simple_VALUE_OBJECTWITHLOCALPATH_node('C2'),
                ]),
            ]),
            exp_xml_str_list=[
                '<DECLARATION>',
                '<DECLGROUP.WITHPATH>',
                simple_VALUE_OBJECTWITHPATH_str('C1'),
                simple_VALUE_OBJECTWITHLOCALPATH_str('C1'),
                '</DECLGROUP.WITHPATH>',
                '<DECLGROUP.WITHPATH>',
                simple_VALUE_OBJECTWITHPATH_str('C2'),
                simple_VALUE_OBJECTWITHLOCALPATH_str('C2'),
                '</DECLGROUP.WITHPATH>',
                '</DECLARATION>',
            ],
        ),
        None, None, True
    ),

    # Testcases for QUALIFIER.DECLARATION element
    #
    #    <!ELEMENT QUALIFIER.DECLARATION (SCOPE?, (VALUE | VALUE.ARRAY)?)>
    #    <!ATTLIST QUALIFIER.DECLARATION
    #         %CIMName;
    #         %CIMType;               #REQUIRED
    #         ISARRAY    (true|false) #IMPLIED
    #         %ArraySize;
    #         %QualifierFlavor;>
    (
        "QUALIFIER.DECLARATION: Fully equipped scalar qualifier",
        dict(
            xml_node=_cim_xml.QUALIFIER_DECLARATION(
                'MyQualifier',
                'string',
                value=_cim_xml.VALUE('abc'),
                is_array=False,
                qualifier_scopes={
                    'CLASS': True,
                    'ASSOCIATION': True,
                },
                overridable=True,
                tosubclass=True,
                toinstance=False,
                translatable=False,
            ),
            exp_xml_str_list=[
                '<QUALIFIER.DECLARATION NAME="MyQualifier" TYPE="string" '
                'ISARRAY="false" OVERRIDABLE="true" TOSUBCLASS="true" '
                'TOINSTANCE="false" TRANSLATABLE="false">',
                '<SCOPE CLASS="true" ASSOCIATION="true"/>',
                '<VALUE>abc</VALUE>',
                '</QUALIFIER.DECLARATION>',
            ],
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION: Fully equipped fixed array qualifier",
        dict(
            xml_node=_cim_xml.QUALIFIER_DECLARATION(
                'MyQualifier',
                'string',
                value=_cim_xml.VALUE_ARRAY([
                    _cim_xml.VALUE('abc'),
                    _cim_xml.VALUE_NULL(),
                    _cim_xml.VALUE('def'),
                ]),
                is_array=True,
                array_size=4,
                qualifier_scopes={
                    'any': True,
                },
                overridable=False,
                tosubclass=False,
                toinstance=True,
                translatable=True,
            ),
            exp_xml_str_list=[
                '<QUALIFIER.DECLARATION NAME="MyQualifier" TYPE="string" '
                'ISARRAY="true" ARRAYSIZE="4" '
                'OVERRIDABLE="false" TOSUBCLASS="false" '
                'TOINSTANCE="true" TRANSLATABLE="true">',
                '<SCOPE CLASS="true" ASSOCIATION="true" '
                'REFERENCE="true" PROPERTY="true" METHOD="true" '
                'PARAMETER="true" INDICATION="true"/>',
                '<VALUE.ARRAY>',
                '<VALUE>abc</VALUE>',
                '<VALUE.NULL/>',
                '<VALUE>def</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            ],
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION: Minimalistic qualifier",
        dict(
            xml_node=_cim_xml.QUALIFIER_DECLARATION(
                'MyQualifier',
                'string',
            ),
            exp_xml_str_list=[
                '<QUALIFIER.DECLARATION NAME="MyQualifier" TYPE="string"/>',
            ],
        ),
        None, None, True
    ),

    # Testcases for SCOPE element
    #
    #    <!ELEMENT SCOPE EMPTY>
    #    <!ATTLIST SCOPE
    #         CLASS        (true|false)      'false'
    #         ASSOCIATION  (true|false)      'false'
    #         REFERENCE    (true|false)      'false'
    #         PROPERTY     (true|false)      'false'
    #         METHOD       (true|false)      'false'
    #         PARAMETER    (true|false)      'false'
    #         INDICATION   (true|false)      'false'>
    (
        "SCOPE: Default input",
        dict(
            xml_node=_cim_xml.SCOPE(),
            exp_xml_str_list=[
                '<SCOPE/>',
            ],
        ),
        None, None, True
    ),
    (
        "SCOPE: all scopes true",
        dict(
            xml_node=_cim_xml.SCOPE({
                'CLASS': True,
                'ASSOCIATION': True,
                'REFERENCE': True,
                'PROPERTY': True,
                'METHOD': True,
                'PARAMETER': True,
                'INDICATION': True,
            }),
            exp_xml_str_list=[
                '<SCOPE CLASS="true" ASSOCIATION="true" '
                'REFERENCE="true" PROPERTY="true" METHOD="true" '
                'PARAMETER="true" INDICATION="true"/>',
            ],
        ),
        None, None, True
    ),
    (
        "SCOPE: all scopes false",
        dict(
            xml_node=_cim_xml.SCOPE({
                'CLASS': False,
                'ASSOCIATION': False,
                'REFERENCE': False,
                'PROPERTY': False,
                'METHOD': False,
                'PARAMETER': False,
                'INDICATION': False,
            }),
            exp_xml_str_list=[
                '<SCOPE CLASS="false" ASSOCIATION="false" '
                'REFERENCE="false" PROPERTY="false" METHOD="false" '
                'PARAMETER="false" INDICATION="false"/>',
            ],
        ),
        None, None, True
    ),
    (
        "SCOPE: any scope",
        dict(
            xml_node=_cim_xml.SCOPE({
                'any': True,
            }),
            exp_xml_str_list=[
                '<SCOPE CLASS="true" ASSOCIATION="true" '
                'REFERENCE="true" PROPERTY="true" METHOD="true" '
                'PARAMETER="true" INDICATION="true"/>',
            ],
        ),
        None, None, True
    ),

    # Testcases for VALUE element
    #
    #    <!ELEMENT VALUE (#PCDATA)>
    (
        "VALUE with None as input",
        dict(
            xml_node=_cim_xml.VALUE(None),
            exp_xml_str_list=[
                '<VALUE/>',
            ],
        ),
        None, None, True
    ),
    (
        "VALUE with empty string as input",
        dict(
            xml_node=_cim_xml.VALUE(''),
            exp_xml_str_list=[
                '<VALUE/>',
            ],
        ),
        None, None, True
    ),
    (
        "VALUE with non-empty string as input",
        dict(
            xml_node=_cim_xml.VALUE('abc'),
            exp_xml_str_list=[
                '<VALUE>abc</VALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "VALUE with XML special characters as input, "
        "using XML escaping",
        dict(
            xml_node=_cim_xml.VALUE('a&b<c>d'),
            exp_xml_str_list=[
                '<VALUE>a&amp;b&lt;c&gt;d</VALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "VALUE with XML special characters as input, "
        "using CDATA escaping",
        dict(
            xml_node=_cim_xml.VALUE('a&b<c>d'),
            exp_xml_str_list=[
                '<VALUE><![CDATA[a&b<c>d]]></VALUE>',
            ],
            cdata_escaping=True,
        ),
        None, None, True
    ),
    (
        "VALUE with already XML-escaped XML special characters as input, "
        "using XML escaping",
        dict(
            xml_node=_cim_xml.VALUE('a&amp;b&lt;c&gt;d'),
            exp_xml_str_list=[
                '<VALUE>a&amp;amp;b&amp;lt;c&amp;gt;d</VALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "VALUE with already XML-escaped XML special characters as input, "
        "using CDATA escaping",
        dict(
            xml_node=_cim_xml.VALUE('a&amp;b&lt;c&gt;d'),
            exp_xml_str_list=[
                '<VALUE><![CDATA[a&amp;b&lt;c&gt;d]]></VALUE>',
            ],
            cdata_escaping=True,
        ),
        None, None, True
    ),
    (
        "VALUE with already CDATA-escaped XML special characters as input, "
        "using XML escaping",
        dict(
            xml_node=_cim_xml.VALUE('<![CDATA[a&b<c>d]]>'),
            exp_xml_str_list=[
                '<VALUE>&lt;![CDATA[a&amp;b&lt;c&gt;d]]&gt;</VALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "VALUE with already CDATA-escaped XML special characters as input, "
        "using CDATA escaping",
        dict(
            xml_node=_cim_xml.VALUE('<![CDATA[a&b<c>d]]>'),
            exp_xml_str_list=[
                '<VALUE><![CDATA[<![CDATA[a&b<c>d]]]><![CDATA[]>]]></VALUE>',
            ],
            cdata_escaping=True,
        ),
        None, None, True
    ),
    (
        "VALUE with some control characters as input",
        dict(
            xml_node=_cim_xml.VALUE('a\nb\rc\td'),
            exp_xml_str_list=[
                '<VALUE>a\nb\rc\td</VALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "VALUE with whitespace as input",
        dict(
            xml_node=_cim_xml.VALUE('  a  b  '),
            exp_xml_str_list=[
                '<VALUE>  a  b  </VALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "VALUE with backlash character as input",
        dict(
            xml_node=_cim_xml.VALUE('\\'),
            exp_xml_str_list=[
                '<VALUE>\\</VALUE>',
            ],
        ),
        None, None, True
    ),

    # Testcases for VALUE.ARRAY element
    #
    #    <!ELEMENT VALUE.ARRAY (VALUE*)>
    (
        "VALUE.ARRAY with empty list as input",
        dict(
            xml_node=_cim_xml.VALUE_ARRAY([]),
            exp_xml_str_list=[
                '<VALUE.ARRAY/>',
            ],
        ),
        None, None, True
    ),
    (
        "VALUE.ARRAY with list of multiple VALUE and VALUE.NULL as input",
        dict(
            xml_node=_cim_xml.VALUE_ARRAY([
                _cim_xml.VALUE_NULL(),
                _cim_xml.VALUE('abc'),
                _cim_xml.VALUE_NULL(),
                _cim_xml.VALUE('def'),
                _cim_xml.VALUE_NULL(),
            ]),
            exp_xml_str_list=[
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '<VALUE>abc</VALUE>',
                '<VALUE.NULL/>',
                '<VALUE>def</VALUE>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
            ],
        ),
        None, None, True
    ),

    # Testcases for VALUE.REFERENCE element
    #
    #    <!ELEMENT VALUE.REFERENCE (CLASSPATH | LOCALCLASSPATH | CLASSNAME |
    #                               INSTANCEPATH | LOCALINSTANCEPATH |
    #                               INSTANCENAME)>
    (
        "VALUE.REFERENCE with CLASSPATH",
        dict(
            xml_node=_cim_xml.VALUE_REFERENCE(
                simple_CLASSPATH_node(),
            ),
            exp_xml_str_list=[
                '<VALUE.REFERENCE>',
                simple_CLASSPATH_str(),
                '</VALUE.REFERENCE>',
            ],
        ),
        None, None, True
    ),
    (
        "VALUE.REFERENCE with LOCALCLASSPATH",
        dict(
            xml_node=_cim_xml.VALUE_REFERENCE(
                simple_LOCALCLASSPATH_node(),
            ),
            exp_xml_str_list=[
                '<VALUE.REFERENCE>',
                simple_LOCALCLASSPATH_str(),
                '</VALUE.REFERENCE>',
            ],
        ),
        None, None, True
    ),
    (
        "VALUE.REFERENCE with CLASSNAME",
        dict(
            xml_node=_cim_xml.VALUE_REFERENCE(
                simple_CLASSNAME_node(),
            ),
            exp_xml_str_list=[
                '<VALUE.REFERENCE>',
                simple_CLASSNAME_str(),
                '</VALUE.REFERENCE>',
            ],
        ),
        None, None, True
    ),
    (
        "VALUE.REFERENCE with INSTANCEPATH",
        dict(
            xml_node=_cim_xml.VALUE_REFERENCE(
                simple_INSTANCEPATH_node(),
            ),
            exp_xml_str_list=[
                '<VALUE.REFERENCE>',
                simple_INSTANCEPATH_str(),
                '</VALUE.REFERENCE>',
            ],
        ),
        None, None, True
    ),
    (
        "VALUE.REFERENCE with LOCALINSTANCEPATH",
        dict(
            xml_node=_cim_xml.VALUE_REFERENCE(
                simple_LOCALINSTANCEPATH_node(),
            ),
            exp_xml_str_list=[
                '<VALUE.REFERENCE>',
                simple_LOCALINSTANCEPATH_str(),
                '</VALUE.REFERENCE>',
            ],
        ),
        None, None, True
    ),
    (
        "VALUE.REFERENCE with INSTANCENAME",
        dict(
            xml_node=_cim_xml.VALUE_REFERENCE(
                simple_INSTANCENAME_node(),
            ),
            exp_xml_str_list=[
                '<VALUE.REFERENCE>',
                simple_INSTANCENAME_str(),
                '</VALUE.REFERENCE>',
            ],
        ),
        None, None, True
    ),

    # Testcases for VALUE.REFARRAY element
    #
    #    <!ELEMENT VALUE.REFARRAY (VALUE.REFERENCE*)>
    (
        "VALUE.REFARRAY with empty list",
        dict(
            xml_node=_cim_xml.VALUE_REFARRAY([]),
            exp_xml_str_list=[
                '<VALUE.REFARRAY/>',
            ],
        ),
        None, None, True
    ),
    (
        "VALUE.REFARRAY with two VALUE.REFERENCE",
        dict(
            xml_node=_cim_xml.VALUE_REFARRAY([
                _cim_xml.VALUE_REFERENCE(
                    simple_CLASSNAME_node('C1'),
                ),
                _cim_xml.VALUE_REFERENCE(
                    simple_CLASSNAME_node('C2'),
                ),
            ]),
            exp_xml_str_list=[
                '<VALUE.REFARRAY>',
                '<VALUE.REFERENCE>',
                simple_CLASSNAME_str('C1'),
                '</VALUE.REFERENCE>',
                '<VALUE.REFERENCE>',
                simple_CLASSNAME_str('C2'),
                '</VALUE.REFERENCE>',
                '</VALUE.REFARRAY>',
            ],
        ),
        None, None, True
    ),

    # Testcases for VALUE.OBJECT element
    #
    #    <!ELEMENT VALUE.OBJECT (CLASS | INSTANCE)>
    (
        "VALUE.OBJECT with CLASS",
        dict(
            xml_node=_cim_xml.VALUE_OBJECT(
                simple_CLASS_node(),
            ),
            exp_xml_str_list=[
                '<VALUE.OBJECT>',
                simple_CLASS_str(),
                '</VALUE.OBJECT>',
            ],
        ),
        None, None, True
    ),
    (
        "VALUE.OBJECT with INSTANCE",
        dict(
            xml_node=_cim_xml.VALUE_OBJECT(
                simple_INSTANCE_node(),
            ),
            exp_xml_str_list=[
                '<VALUE.OBJECT>',
                simple_INSTANCE_str(),
                '</VALUE.OBJECT>',
            ],
        ),
        None, None, True
    ),

    # Testcases for VALUE.NAMEDINSTANCE element
    #
    #    <!ELEMENT VALUE.NAMEDINSTANCE (INSTANCENAME, INSTANCE)>
    (
        "VALUE.NAMEDINSTANCE with INSTANCENAME and INSTANCE",
        dict(
            xml_node=_cim_xml.VALUE_NAMEDINSTANCE(
                simple_INSTANCENAME_node(),
                simple_INSTANCE_node(),
            ),
            exp_xml_str_list=[
                '<VALUE.NAMEDINSTANCE>',
                simple_INSTANCENAME_str(),
                simple_INSTANCE_str(),
                '</VALUE.NAMEDINSTANCE>',
            ],
        ),
        None, None, True
    ),

    # Testcases for VALUE.NAMEDOBJECT element
    #
    #    <!ELEMENT VALUE.NAMEDOBJECT (CLASS | (INSTANCENAME, INSTANCE))>
    (
        "VALUE.NAMEDOBJECT with CLASS",
        dict(
            xml_node=_cim_xml.VALUE_NAMEDOBJECT(
                simple_CLASS_node(),
            ),
            exp_xml_str_list=[
                '<VALUE.NAMEDOBJECT>',
                simple_CLASS_str(),
                '</VALUE.NAMEDOBJECT>',
            ],
        ),
        None, None, True
    ),
    (
        "VALUE.NAMEDOBJECT with CLASS",
        dict(
            xml_node=_cim_xml.VALUE_NAMEDOBJECT([
                simple_INSTANCENAME_node(),
                simple_INSTANCE_node(),
            ]),
            exp_xml_str_list=[
                '<VALUE.NAMEDOBJECT>',
                simple_INSTANCENAME_str(),
                simple_INSTANCE_str(),
                '</VALUE.NAMEDOBJECT>',
            ],
        ),
        None, None, True
    ),

    # Testcases for VALUE.OBJECTWITHLOCALPATH element
    #
    #    <!ELEMENT VALUE.OBJECTWITHLOCALPATH ((LOCALCLASSPATH, CLASS) |
    #                                         (LOCALINSTANCEPATH, INSTANCE))>
    (
        "VALUE.OBJECTWITHLOCALPATH with LOCALCLASSPATH and CLASS",
        dict(
            xml_node=_cim_xml.VALUE_OBJECTWITHLOCALPATH(
                simple_LOCALCLASSPATH_node(),
                simple_CLASS_node(),
            ),
            exp_xml_str_list=[
                '<VALUE.OBJECTWITHLOCALPATH>',
                simple_LOCALCLASSPATH_str(),
                simple_CLASS_str(),
                '</VALUE.OBJECTWITHLOCALPATH>',
            ],
        ),
        None, None, True
    ),
    (
        "VALUE.OBJECTWITHLOCALPATH with LOCALINSTANCEPATH and INSTANCE",
        dict(
            xml_node=_cim_xml.VALUE_OBJECTWITHLOCALPATH(
                simple_LOCALINSTANCEPATH_node(),
                simple_INSTANCE_node(),
            ),
            exp_xml_str_list=[
                '<VALUE.OBJECTWITHLOCALPATH>',
                simple_LOCALINSTANCEPATH_str(),
                simple_INSTANCE_str(),
                '</VALUE.OBJECTWITHLOCALPATH>',
            ],
        ),
        None, None, True
    ),

    # Testcases for VALUE.OBJECTWITHPATH element
    #
    #    <!ELEMENT VALUE.OBJECTWITHPATH ((CLASSPATH, CLASS) |
    #                                    (INSTANCEPATH, INSTANCE))>
    (
        "VALUE.OBJECTWITHPATH with CLASSPATH and CLASS",
        dict(
            xml_node=_cim_xml.VALUE_OBJECTWITHPATH(
                simple_CLASSPATH_node(),
                simple_CLASS_node(),
            ),
            exp_xml_str_list=[
                '<VALUE.OBJECTWITHPATH>',
                simple_CLASSPATH_str(),
                simple_CLASS_str(),
                '</VALUE.OBJECTWITHPATH>',
            ],
        ),
        None, None, True
    ),
    (
        "VALUE.OBJECTWITHPATH with INSTANCEPATH and INSTANCE",
        dict(
            xml_node=_cim_xml.VALUE_OBJECTWITHPATH(
                simple_INSTANCEPATH_node(),
                simple_INSTANCE_node(),
            ),
            exp_xml_str_list=[
                '<VALUE.OBJECTWITHPATH>',
                simple_INSTANCEPATH_str(),
                simple_INSTANCE_str(),
                '</VALUE.OBJECTWITHPATH>',
            ],
        ),
        None, None, True
    ),

    # Testcases for VALUE.NULL element
    #
    #    <!ELEMENT VALUE.NULL EMPTY>
    (
        "VALUE.NULL",
        dict(
            xml_node=_cim_xml.VALUE_NULL(),
            exp_xml_str_list=[
                '<VALUE.NULL/>',
            ],
        ),
        None, None, True
    ),

    # Testcases for VALUE.INSTANCEWITHPATH element
    #
    #    <!ELEMENT VALUE.INSTANCEWITHPATH (INSTANCEPATH, INSTANCE)>
    (
        "VALUE.INSTANCEWITHPATH",
        dict(
            xml_node=_cim_xml.VALUE_INSTANCEWITHPATH(
                simple_INSTANCEPATH_node(),
                simple_INSTANCE_node(),
            ),
            exp_xml_str_list=[
                '<VALUE.INSTANCEWITHPATH>',
                simple_INSTANCEPATH_str(),
                simple_INSTANCE_str(),
                '</VALUE.INSTANCEWITHPATH>',
            ],
        ),
        None, None, True
    ),

    # Testcases for NAMESPACEPATH element
    #
    #    <!ELEMENT NAMESPACEPATH (HOST, LOCALNAMESPACEPATH)>
    (
        "NAMESPACEPATH",
        dict(
            xml_node=_cim_xml.NAMESPACEPATH(
                simple_HOST_node(),
                simple_LOCALNAMESPACEPATH_node(),
            ),
            exp_xml_str_list=[
                '<NAMESPACEPATH>',
                simple_HOST_str(),
                simple_LOCALNAMESPACEPATH_str(),
                '</NAMESPACEPATH>',
            ],
        ),
        None, None, True
    ),

    # Testcases for LOCALNAMESPACEPATH element
    #
    #    <!ELEMENT LOCALNAMESPACEPATH (NAMESPACE+)>
    (
        "LOCALNAMESPACEPATH with one NAMESPACE",
        dict(
            xml_node=_cim_xml.LOCALNAMESPACEPATH([
                simple_NAMESPACE_node(),
            ]),
            exp_xml_str_list=[
                '<LOCALNAMESPACEPATH>',
                simple_NAMESPACE_str(),
                '</LOCALNAMESPACEPATH>',
            ],
        ),
        None, None, True
    ),
    (
        "LOCALNAMESPACEPATH with two NAMESPACE",
        dict(
            xml_node=_cim_xml.LOCALNAMESPACEPATH([
                simple_NAMESPACE_node('root'),
                simple_NAMESPACE_node('myns'),
            ]),
            exp_xml_str_list=[
                '<LOCALNAMESPACEPATH>',
                simple_NAMESPACE_str('root'),
                simple_NAMESPACE_str('myns'),
                '</LOCALNAMESPACEPATH>',
            ],
        ),
        None, None, True
    ),

    # Testcases for HOST element
    #
    #    <!ELEMENT HOST (#PCDATA)>
    (
        "HOST with empty string as input",
        dict(
            xml_node=_cim_xml.HOST(''),
            exp_xml_str_list=[
                '<HOST/>',
            ],
        ),
        None, None, True
    ),
    (
        "HOST with non-empty string as input",
        dict(
            xml_node=_cim_xml.HOST('abc'),
            exp_xml_str_list=[
                '<HOST>abc</HOST>',
            ],
        ),
        None, None, True
    ),

    # Testcases for NAMESPACE element
    #
    #    <!ELEMENT NAMESPACE EMPTY>
    #    <!ATTLIST NAMESPACE
    #        %CIMName;>
    (
        "NAMESPACE with empty string as name",
        dict(
            xml_node=_cim_xml.NAMESPACE(''),
            exp_xml_str_list=[
                '<NAMESPACE NAME=""/>',
            ],
        ),
        None, None, True
    ),
    (
        "NAMESPACE with non-empty string as name",
        dict(
            xml_node=_cim_xml.NAMESPACE('abc'),
            exp_xml_str_list=[
                '<NAMESPACE NAME="abc"/>',
            ],
        ),
        None, None, True
    ),

    # Testcases for CLASSPATH element
    #
    #    <!ELEMENT CLASSPATH (NAMESPACEPATH, CLASSNAME)>
    (
        "CLASSPATH",
        dict(
            xml_node=_cim_xml.CLASSPATH(
                simple_NAMESPACEPATH_node(),
                simple_CLASSNAME_node(),
            ),
            exp_xml_str_list=[
                '<CLASSPATH>',
                simple_NAMESPACEPATH_str(),
                simple_CLASSNAME_str(),
                '</CLASSPATH>',
            ],
        ),
        None, None, True
    ),

    # Testcases for LOCALCLASSPATH element
    #
    #    <!ELEMENT LOCALCLASSPATH (LOCALNAMESPACEPATH, CLASSNAME)>
    (
        "LOCALCLASSPATH",
        dict(
            xml_node=_cim_xml.LOCALCLASSPATH(
                simple_LOCALNAMESPACEPATH_node(),
                simple_CLASSNAME_node(),
            ),
            exp_xml_str_list=[
                '<LOCALCLASSPATH>',
                simple_LOCALNAMESPACEPATH_str(),
                simple_CLASSNAME_str(),
                '</LOCALCLASSPATH>',
            ],
        ),
        None, None, True
    ),

    # Testcases for CLASSNAME element
    #
    #    <!ELEMENT CLASSNAME EMPTY>
    #    <!ATTLIST CLASSNAME
    #        %CIMName;>
    (
        "CLASSNAME with empty string as name",
        dict(
            xml_node=_cim_xml.CLASSNAME(''),
            exp_xml_str_list=[
                '<CLASSNAME NAME=""/>',
            ],
        ),
        None, None, True
    ),
    (
        "CLASSNAME with 7-bit ASCII string as name",
        dict(
            xml_node=_cim_xml.CLASSNAME('ACME_Ab42'),
            exp_xml_str_list=[
                '<CLASSNAME NAME="ACME_Ab42"/>',
            ],
        ),
        None, None, True
    ),
    (
        "CLASSNAME with non-ASCII UCS-2 string as name",
        dict(
            xml_node=_cim_xml.CLASSNAME(u'ACME_\u00E4'),
            exp_xml_str_list=[
                u'<CLASSNAME NAME="ACME_\u00E4"/>',
            ],
        ),
        None, None, True
    ),
    (
        "CLASSNAME with non-UCS-2 unicode string as name",
        dict(
            xml_node=_cim_xml.CLASSNAME(u'ACME_\U00010142'),
            exp_xml_str_list=[
                u'<CLASSNAME NAME="ACME_\U00010142"/>',
            ],
        ),
        None, None, True
    ),

    # Testcases for INSTANCEPATH element
    #
    #    <!ELEMENT INSTANCEPATH (NAMESPACEPATH, INSTANCENAME)>
    (
        "INSTANCEPATH",
        dict(
            xml_node=_cim_xml.INSTANCEPATH(
                simple_NAMESPACEPATH_node(),
                simple_INSTANCENAME_node(),
            ),
            exp_xml_str_list=[
                '<INSTANCEPATH>',
                simple_NAMESPACEPATH_str(),
                simple_INSTANCENAME_str(),
                '</INSTANCEPATH>',
            ],
        ),
        None, None, True
    ),

    # Testcases for LOCALINSTANCEPATH element
    #
    #    <!ELEMENT LOCALINSTANCEPATH (LOCALNAMESPACEPATH, INSTANCENAME)>
    (
        "LOCALINSTANCEPATH",
        dict(
            xml_node=_cim_xml.LOCALINSTANCEPATH(
                simple_LOCALNAMESPACEPATH_node(),
                simple_INSTANCENAME_node(),
            ),
            exp_xml_str_list=[
                '<LOCALINSTANCEPATH>',
                simple_LOCALNAMESPACEPATH_str(),
                simple_INSTANCENAME_str(),
                '</LOCALINSTANCEPATH>',
            ],
        ),
        None, None, True
    ),

    # Testcases for INSTANCENAME element
    #
    #    <!ELEMENT INSTANCENAME (KEYBINDING* | KEYVALUE? | VALUE.REFERENCE?)>
    #    <!ATTLIST INSTANCENAME
    #        %ClassName;>
    (
        "INSTANCENAME with no keys",
        dict(
            xml_node=_cim_xml.INSTANCENAME(
                'MyClass',
                None
            ),
            exp_xml_str_list=[
                '<INSTANCENAME CLASSNAME="MyClass"/>',
            ],
        ),
        None, None, True
    ),
    (
        "INSTANCENAME with one KEYBINDING",
        dict(
            xml_node=_cim_xml.INSTANCENAME(
                'MyClass',
                _cim_xml.KEYBINDING(
                    'Key1',
                    _cim_xml.KEYVALUE('abc'),
                ),
            ),
            exp_xml_str_list=[
                '<INSTANCENAME CLASSNAME="MyClass">',
                '<KEYBINDING NAME="Key1">',
                '<KEYVALUE VALUETYPE="string">abc</KEYVALUE>',
                '</KEYBINDING>',
                '</INSTANCENAME>',
            ],
        ),
        None, None, True
    ),
    (
        "INSTANCENAME with two KEYBINDING",
        dict(
            xml_node=_cim_xml.INSTANCENAME(
                'MyClass',
                [
                    _cim_xml.KEYBINDING(
                        'Key1',
                        _cim_xml.KEYVALUE('abc'),
                    ),
                    _cim_xml.KEYBINDING(
                        'Key2',
                        _cim_xml.KEYVALUE('def'),
                    ),
                ],
            ),
            exp_xml_str_list=[
                '<INSTANCENAME CLASSNAME="MyClass">',
                '<KEYBINDING NAME="Key1">',
                '<KEYVALUE VALUETYPE="string">abc</KEYVALUE>',
                '</KEYBINDING>',
                '<KEYBINDING NAME="Key2">',
                '<KEYVALUE VALUETYPE="string">def</KEYVALUE>',
                '</KEYBINDING>',
                '</INSTANCENAME>',
            ],
        ),
        None, None, True
    ),
    (
        "INSTANCENAME with one KEYVALUE",
        dict(
            xml_node=_cim_xml.INSTANCENAME(
                'MyClass',
                _cim_xml.KEYVALUE('abc'),
            ),
            exp_xml_str_list=[
                '<INSTANCENAME CLASSNAME="MyClass">',
                '<KEYVALUE VALUETYPE="string">abc</KEYVALUE>',
                '</INSTANCENAME>',
            ],
        ),
        None, None, True
    ),
    (
        "INSTANCENAME with one VALUE.REFERENCE",
        dict(
            xml_node=_cim_xml.INSTANCENAME(
                'MyClass',
                _cim_xml.VALUE_REFERENCE(
                    simple_CLASSNAME_node('C2'),
                ),
            ),
            exp_xml_str_list=[
                '<INSTANCENAME CLASSNAME="MyClass">',
                '<VALUE.REFERENCE>',
                simple_CLASSNAME_str('C2'),
                '</VALUE.REFERENCE>',
                '</INSTANCENAME>',
            ],
        ),
        None, None, True
    ),

    # Testcases for OBJECTPATH element
    #
    #    <!ELEMENT OBJECTPATH (INSTANCEPATH | CLASSPATH)>
    (
        "OBJECTPATH with INSTANCEPATH",
        dict(
            xml_node=_cim_xml.OBJECTPATH(
                simple_INSTANCEPATH_node(),
            ),
            exp_xml_str_list=[
                '<OBJECTPATH>',
                simple_INSTANCEPATH_str(),
                '</OBJECTPATH>',
            ],
        ),
        None, None, True
    ),
    (
        "OBJECTPATH with CLASSPATH",
        dict(
            xml_node=_cim_xml.OBJECTPATH(
                simple_CLASSPATH_node(),
            ),
            exp_xml_str_list=[
                '<OBJECTPATH>',
                simple_CLASSPATH_str(),
                '</OBJECTPATH>',
            ],
        ),
        None, None, True
    ),

    # Testcases for KEYBINDING element
    #
    #    <!ELEMENT KEYBINDING (KEYVALUE | VALUE.REFERENCE)>
    #    <!ATTLIST KEYBINDING
    #        %CIMName;>
    (
        "KEYBINDING with KEYVALUE",
        dict(
            xml_node=_cim_xml.KEYBINDING(
                'Key1',
                _cim_xml.KEYVALUE('abc'),
            ),
            exp_xml_str_list=[
                '<KEYBINDING NAME="Key1">',
                '<KEYVALUE VALUETYPE="string">abc</KEYVALUE>',
                '</KEYBINDING>',
            ],
        ),
        None, None, True
    ),
    (
        "KEYBINDING with VALUE.REFERENCE",
        dict(
            xml_node=_cim_xml.KEYBINDING(
                'Key1',
                _cim_xml.VALUE_REFERENCE(
                    simple_CLASSNAME_node('C2'),
                ),
            ),
            exp_xml_str_list=[
                '<KEYBINDING NAME="Key1">',
                '<VALUE.REFERENCE>',
                simple_CLASSNAME_str('C2'),
                '</VALUE.REFERENCE>',
                '</KEYBINDING>',
            ],
        ),
        None, None, True
    ),

    # Testcases for KEYVALUE element
    #
    #    <!ELEMENT KEYVALUE (#PCDATA)>
    #    <!ATTLIST KEYVALUE
    #        VALUETYPE    (string|boolean|numeric)  'string'
    #        %CIMType;    #IMPLIED>
    (
        "KEYVALUE with None (not very useful, though)",
        dict(
            xml_node=_cim_xml.KEYVALUE(None),
            exp_xml_str_list=[
                '<KEYVALUE VALUETYPE="string"></KEYVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "KEYVALUE with empty string and no types",
        dict(
            xml_node=_cim_xml.KEYVALUE(''),
            exp_xml_str_list=[
                '<KEYVALUE VALUETYPE="string"></KEYVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "KEYVALUE with non-empty string and VALUETYPE",
        dict(
            xml_node=_cim_xml.KEYVALUE(
                'abc', value_type='string'),
            exp_xml_str_list=[
                '<KEYVALUE VALUETYPE="string">abc</KEYVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "KEYVALUE with non-empty string and VALUETYPE and TYPE",
        dict(
            xml_node=_cim_xml.KEYVALUE(
                'abc', value_type='string', cim_type='string'),
            exp_xml_str_list=[
                '<KEYVALUE VALUETYPE="string" TYPE="string">abc</KEYVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "KEYVALUE with numeric and VALUETYPE",
        dict(
            xml_node=_cim_xml.KEYVALUE(
                '42', value_type='numeric'),
            exp_xml_str_list=[
                '<KEYVALUE VALUETYPE="numeric">42</KEYVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "KEYVALUE with numeric and VALUETYPE and TYPE",
        dict(
            xml_node=_cim_xml.KEYVALUE(
                '42', value_type='numeric', cim_type='uint8'),
            exp_xml_str_list=[
                '<KEYVALUE VALUETYPE="numeric" TYPE="uint8">42</KEYVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "KEYVALUE with boolean and VALUETYPE",
        dict(
            xml_node=_cim_xml.KEYVALUE(
                'true', value_type='boolean'),
            exp_xml_str_list=[
                '<KEYVALUE VALUETYPE="boolean">true</KEYVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "KEYVALUE with boolean and VALUETYPE and TYPE",
        dict(
            xml_node=_cim_xml.KEYVALUE(
                'true', value_type='boolean', cim_type='boolean'),
            exp_xml_str_list=[
                '<KEYVALUE VALUETYPE="boolean" TYPE="boolean">true</KEYVALUE>',
            ],
        ),
        None, None, True
    ),

    # Testcases for CLASS element
    #
    #    <!ELEMENT CLASS (QUALIFIER*, (PROPERTY | PROPERTY.ARRAY |
    #                     PROPERTY.REFERENCE)*, METHOD*)>
    #    <!ATTLIST CLASS
    #        %CIMName;
    #        %SuperClass;>
    (
        "CLASS with minimalistic elements",
        dict(
            xml_node=_cim_xml.CLASS(
                'MyClass',
            ),
            exp_xml_str_list=[
                '<CLASS NAME="MyClass"/>',
            ],
        ),
        None, None, True
    ),
    (
        "CLASS fully equipped",
        dict(
            xml_node=_cim_xml.CLASS(
                'MyClass',
                properties=[
                    _cim_xml.PROPERTY('P1', 'string'),
                    _cim_xml.PROPERTY_ARRAY('P2', 'string'),
                    _cim_xml.PROPERTY_REFERENCE('P3'),
                ],
                methods=[
                    _cim_xml.METHOD('M1'),
                    _cim_xml.METHOD('M2'),
                ],
                qualifiers=[
                    _cim_xml.QUALIFIER('Q1', 'string'),
                    _cim_xml.QUALIFIER('Q2', 'string'),
                ],
                superclass='MySuper',
            ),
            exp_xml_str_list=[
                '<CLASS NAME="MyClass" SUPERCLASS="MySuper">',
                '<QUALIFIER NAME="Q1" TYPE="string"/>',
                '<QUALIFIER NAME="Q2" TYPE="string"/>',
                '<PROPERTY NAME="P1" TYPE="string"/>',
                '<PROPERTY.ARRAY NAME="P2" TYPE="string"/>',
                '<PROPERTY.REFERENCE NAME="P3"/>',
                '<METHOD NAME="M1"/>',
                '<METHOD NAME="M2"/>',
                '</CLASS>',
            ],
        ),
        None, None, True
    ),

    # Testcases for INSTANCE element
    #
    #    <!ELEMENT INSTANCE (QUALIFIER*, (PROPERTY | PROPERTY.ARRAY |
    #                                     PROPERTY.REFERENCE)*)>
    #    <!ATTLIST INSTANCE
    #        %ClassName;
    #        xml:lang   NMTOKEN  #IMPLIED>
    (
        "INSTANCE with minimalistic elements",
        dict(
            xml_node=_cim_xml.INSTANCE(
                'MyClass',
            ),
            exp_xml_str_list=[
                '<INSTANCE CLASSNAME="MyClass"/>',
            ],
        ),
        None, None, True
    ),
    (
        "INSTANCE fully equipped",
        dict(
            xml_node=_cim_xml.INSTANCE(
                'MyClass',
                properties=[
                    _cim_xml.PROPERTY('P1', 'string'),
                    _cim_xml.PROPERTY_ARRAY('P2', 'string'),
                    _cim_xml.PROPERTY_REFERENCE('P3'),
                ],
                qualifiers=[
                    _cim_xml.QUALIFIER('Q1', 'string'),
                    _cim_xml.QUALIFIER('Q2', 'string'),
                ],
            ),
            exp_xml_str_list=[
                '<INSTANCE CLASSNAME="MyClass">',
                '<QUALIFIER NAME="Q1" TYPE="string"/>',
                '<QUALIFIER NAME="Q2" TYPE="string"/>',
                '<PROPERTY NAME="P1" TYPE="string"/>',
                '<PROPERTY.ARRAY NAME="P2" TYPE="string"/>',
                '<PROPERTY.REFERENCE NAME="P3"/>',
                '</INSTANCE>',
            ],
        ),
        None, None, True
    ),

    # Testcases for QUALIFIER element
    #
    #    <!ELEMENT QUALIFIER ((VALUE | VALUE.ARRAY)?)>
    #    <!ATTLIST QUALIFIER
    #        %CIMName;
    #        %CIMType;               #REQUIRED
    #        %Propagated;
    #        %QualifierFlavor;
    #        xml:lang  NMTOKEN  #IMPLIED>
    (
        "QUALIFIER of scalar string type, minimalistic",
        dict(
            xml_node=_cim_xml.QUALIFIER(
                'MyQualifier',
                'string',
            ),
            exp_xml_str_list=[
                '<QUALIFIER NAME="MyQualifier" TYPE="string"/>',
            ],
        ),
        None, None, True
    ),
    (
        "QUALIFIER of scalar string type and flavors all true",
        dict(
            xml_node=_cim_xml.QUALIFIER(
                'MyQualifier',
                'string',
                value=_cim_xml.VALUE('abc'),
                propagated=True,
                overridable=True,
                tosubclass=True,
                toinstance=True,
                translatable=True,
                xml_lang='de_DE'
            ),
            exp_xml_str_list=[
                '<QUALIFIER NAME="MyQualifier" TYPE="string" '
                'PROPAGATED="true" OVERRIDABLE="true" '
                'TOSUBCLASS="true" TOINSTANCE="true" '
                'TRANSLATABLE="true" xml:lang="de_DE">',
                '<VALUE>abc</VALUE>',
                '</QUALIFIER>',
            ],
        ),
        None, None, True
    ),
    (
        "QUALIFIER of array string type and flavors all false",
        dict(
            xml_node=_cim_xml.QUALIFIER(
                'MyQualifier',
                'string',
                value=_cim_xml.VALUE_ARRAY([
                    _cim_xml.VALUE('abc'),
                    _cim_xml.VALUE_NULL(),
                ]),
                propagated=False,
                overridable=False,
                tosubclass=False,
                toinstance=False,
                translatable=False,
                xml_lang='de_DE'
            ),
            exp_xml_str_list=[
                '<QUALIFIER NAME="MyQualifier" TYPE="string" '
                'PROPAGATED="false" OVERRIDABLE="false" '
                'TOSUBCLASS="false" TOINSTANCE="false" '
                'TRANSLATABLE="false" xml:lang="de_DE">',
                '<VALUE.ARRAY>',
                '<VALUE>abc</VALUE>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            ],
        ),
        None, None, True
    ),

    # Testcases for PROPERTY element
    #
    #    <!ELEMENT PROPERTY (QUALIFIER*, VALUE?)>
    #    <!ATTLIST PROPERTY
    #        %CIMName;
    #        %CIMType;           #REQUIRED
    #        %ClassOrigin;
    #        %Propagated;
    #        %EmbeddedObject;
    #        xml:lang   NMTOKEN  #IMPLIED>
    (
        "PROPERTY of string type, minimalistic",
        dict(
            xml_node=_cim_xml.PROPERTY(
                'MyProp',
                'string',
            ),
            exp_xml_str_list=[
                '<PROPERTY NAME="MyProp" TYPE="string"/>',
            ],
        ),
        None, None, True
    ),
    (
        "PROPERTY of string type, all attributes",
        dict(
            xml_node=_cim_xml.PROPERTY(
                'MyProp',
                'string',
                value=_cim_xml.VALUE('abc'),
                class_origin='OriginClass',
                propagated=True,
                qualifiers=[
                    _cim_xml.QUALIFIER('Q1', 'string'),
                    _cim_xml.QUALIFIER('Q2', 'string'),
                ],
                xml_lang='de_DE',
                embedded_object='instance'
            ),
            exp_xml_str_list=[
                '<PROPERTY NAME="MyProp" TYPE="string" '
                'CLASSORIGIN="OriginClass" PROPAGATED="true" '
                'EmbeddedObject="instance" xml:lang="de_DE">',
                '<QUALIFIER NAME="Q1" TYPE="string"/>',
                '<QUALIFIER NAME="Q2" TYPE="string"/>',
                '<VALUE>abc</VALUE>',
                '</PROPERTY>',
            ],
        ),
        None, None, True
    ),

    # Testcases for PROPERTY.ARRAY element
    #
    #    <!ELEMENT PROPERTY.ARRAY (QUALIFIER*, VALUE.ARRAY?)>
    #    <!ATTLIST PROPERTY.ARRAY
    #        %CIMName;
    #        %CIMType;           #REQUIRED
    #        %ArraySize;
    #        %ClassOrigin;
    #        %Propagated;
    #        %EmbeddedObject;
    #        xml:lang   NMTOKEN  #IMPLIED>
    (
        "PROPERTY.ARRAY of string type, minimalistic",
        dict(
            xml_node=_cim_xml.PROPERTY_ARRAY(
                'MyProp',
                'string',
            ),
            exp_xml_str_list=[
                '<PROPERTY.ARRAY NAME="MyProp" TYPE="string"/>',
            ],
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY of string type, all attributes",
        dict(
            xml_node=_cim_xml.PROPERTY_ARRAY(
                'MyProp',
                'string',
                value_array=_cim_xml.VALUE_ARRAY([
                    _cim_xml.VALUE('abc'),
                    _cim_xml.VALUE_NULL(),
                ]),
                array_size='4',
                class_origin='OriginClass',
                propagated=True,
                qualifiers=[
                    _cim_xml.QUALIFIER('Q1', 'string'),
                    _cim_xml.QUALIFIER('Q2', 'string'),
                ],
                xml_lang='de_DE',
                embedded_object='instance'
            ),
            exp_xml_str_list=[
                '<PROPERTY.ARRAY NAME="MyProp" TYPE="string" ARRAYSIZE="4" '
                'CLASSORIGIN="OriginClass" PROPAGATED="true" '
                'EmbeddedObject="instance" xml:lang="de_DE">',
                '<QUALIFIER NAME="Q1" TYPE="string"/>',
                '<QUALIFIER NAME="Q2" TYPE="string"/>',
                '<VALUE.ARRAY>',
                '<VALUE>abc</VALUE>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            ],
        ),
        None, None, True
    ),

    # Testcases for PROPERTY.REFERENCE element
    #
    #    <!ELEMENT PROPERTY.REFERENCE (QUALIFIER*, VALUE.REFERENCE?)>
    #    <!ATTLIST PROPERTY.REFERENCE
    #        %CIMName;
    #        %ReferenceClass;
    #        %ClassOrigin;
    #        %Propagated;>
    (
        "PROPERTY.REFERENCE, minimalistic",
        dict(
            xml_node=_cim_xml.PROPERTY_REFERENCE(
                'MyProp',
            ),
            exp_xml_str_list=[
                '<PROPERTY.REFERENCE NAME="MyProp"/>',
            ],
        ),
        None, None, True
    ),
    (
        "PROPERTY.REFERENCE, all attributes",
        dict(
            xml_node=_cim_xml.PROPERTY_REFERENCE(
                'MyProp',
                value_reference=_cim_xml.VALUE_REFERENCE(
                    simple_INSTANCENAME_node('RefClass'),
                ),
                reference_class='RefClass',
                class_origin='OriginClass',
                propagated=True,
                qualifiers=[
                    _cim_xml.QUALIFIER('Q1', 'string'),
                    _cim_xml.QUALIFIER('Q2', 'string'),
                ]
            ),
            exp_xml_str_list=[
                '<PROPERTY.REFERENCE NAME="MyProp" '
                'REFERENCECLASS="RefClass" '
                'CLASSORIGIN="OriginClass" PROPAGATED="true">'
                '<QUALIFIER NAME="Q1" TYPE="string"/>',
                '<QUALIFIER NAME="Q2" TYPE="string"/>',
                '<VALUE.REFERENCE>',
                simple_INSTANCENAME_str('RefClass'),
                '</VALUE.REFERENCE>',
                '</PROPERTY.REFERENCE>',
            ],
        ),
        None, None, True
    ),

    # Testcases for METHOD element
    #
    #    <!ELEMENT METHOD (QUALIFIER*, (PARAMETER | PARAMETER.REFERENCE |
    #                               PARAMETER.ARRAY | PARAMETER.REFARRAY)*)>
    #    <!ATTLIST METHOD
    #        %CIMName;
    #        %CIMType;          #IMPLIED
    #        %ClassOrigin;
    #        %Propagated;>
    (
        "METHOD, minimalistic",
        dict(
            xml_node=_cim_xml.METHOD(
                'MyMethod',
            ),
            exp_xml_str_list=[
                '<METHOD NAME="MyMethod"/>',
            ],
        ),
        None, None, True
    ),
    (
        "METHOD, fully equipped",
        dict(
            xml_node=_cim_xml.METHOD(
                'MyMethod',
                parameters=[
                    _cim_xml.PARAMETER('P1', 'string'),
                    _cim_xml.PARAMETER('P2', 'string'),
                ],
                return_type='string',
                class_origin='OriginClass',
                propagated=True,
                qualifiers=[
                    _cim_xml.QUALIFIER('Q1', 'string'),
                    _cim_xml.QUALIFIER('Q2', 'string'),
                ]
            ),
            exp_xml_str_list=[
                '<METHOD NAME="MyMethod" TYPE="string" '
                'CLASSORIGIN="OriginClass" PROPAGATED="true">'
                '<QUALIFIER NAME="Q1" TYPE="string"/>',
                '<QUALIFIER NAME="Q2" TYPE="string"/>',
                '<PARAMETER NAME="P1" TYPE="string"/>',
                '<PARAMETER NAME="P2" TYPE="string"/>',
                '</METHOD>',
            ],
        ),
        None, None, True
    ),

    # Testcases for PARAMETER element
    #
    #    <!ELEMENT PARAMETER (QUALIFIER*)>
    #    <!ATTLIST PARAMETER
    #        %CIMName;
    #        %CIMType;      #REQUIRED>
    (
        "PARAMETER, minimalistic",
        dict(
            xml_node=_cim_xml.PARAMETER(
                'MyParm',
                'string',
            ),
            exp_xml_str_list=[
                '<PARAMETER NAME="MyParm" TYPE="string"/>',
            ],
        ),
        None, None, True
    ),
    (
        "PARAMETER, fully equipped",
        dict(
            xml_node=_cim_xml.PARAMETER(
                'MyParm',
                'string',
                qualifiers=[
                    _cim_xml.QUALIFIER('Q1', 'string'),
                    _cim_xml.QUALIFIER('Q2', 'string'),
                ]
            ),
            exp_xml_str_list=[
                '<PARAMETER NAME="MyParm" TYPE="string">',
                '<QUALIFIER NAME="Q1" TYPE="string"/>',
                '<QUALIFIER NAME="Q2" TYPE="string"/>',
                '</PARAMETER>',
            ],
        ),
        None, None, True
    ),

    # Testcases for PARAMETER.REFERENCE element
    #
    #    <!ELEMENT PARAMETER.REFERENCE (QUALIFIER*)>
    #    <!ATTLIST PARAMETER.REFERENCE
    #        %CIMName;
    #        %ReferenceClass;>
    (
        "PARAMETER.REFERENCE, minimalistic",
        dict(
            xml_node=_cim_xml.PARAMETER_REFERENCE(
                'MyParm',
            ),
            exp_xml_str_list=[
                '<PARAMETER.REFERENCE NAME="MyParm"/>',
            ],
        ),
        None, None, True
    ),
    (
        "PARAMETER.REFERENCE, fully equipped",
        dict(
            xml_node=_cim_xml.PARAMETER_REFERENCE(
                'MyParm',
                reference_class='RefClass',
                qualifiers=[
                    _cim_xml.QUALIFIER('Q1', 'string'),
                    _cim_xml.QUALIFIER('Q2', 'string'),
                ]
            ),
            exp_xml_str_list=[
                '<PARAMETER.REFERENCE NAME="MyParm" '
                'REFERENCECLASS="RefClass">',
                '<QUALIFIER NAME="Q1" TYPE="string"/>',
                '<QUALIFIER NAME="Q2" TYPE="string"/>',
                '</PARAMETER.REFERENCE>',
            ],
        ),
        None, None, True
    ),

    # Testcases for PARAMETER.ARRAY element
    #
    #    <!ELEMENT PARAMETER.ARRAY (QUALIFIER*)>
    #    <!ATTLIST PARAMETER.ARRAY
    #        %CIMName;
    #        %CIMType;           #REQUIRED
    #        %ArraySize;>
    (
        "PARAMETER.ARRAY, minimalistic",
        dict(
            xml_node=_cim_xml.PARAMETER_ARRAY(
                'MyParm',
                'string',
            ),
            exp_xml_str_list=[
                '<PARAMETER.ARRAY NAME="MyParm" TYPE="string"/>',
            ],
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY, fully equipped",
        dict(
            xml_node=_cim_xml.PARAMETER_ARRAY(
                'MyParm',
                'string',
                array_size='4',
                qualifiers=[
                    _cim_xml.QUALIFIER('Q1', 'string'),
                    _cim_xml.QUALIFIER('Q2', 'string'),
                ]
            ),
            exp_xml_str_list=[
                '<PARAMETER.ARRAY NAME="MyParm" TYPE="string" ',
                'ARRAYSIZE="4">',
                '<QUALIFIER NAME="Q1" TYPE="string"/>',
                '<QUALIFIER NAME="Q2" TYPE="string"/>',
                '</PARAMETER.ARRAY>',
            ],
        ),
        None, None, True
    ),

    # Testcases for PARAMETER.REFARRAY element
    #
    #    <!ELEMENT PARAMETER.REFARRAY (QUALIFIER*)>
    #    <!ATTLIST PARAMETER.REFARRAY
    #        %CIMName;
    #        %ReferenceClass;
    #        %ArraySize;>
    (
        "PARAMETER.REFARRAY, minimalistic",
        dict(
            xml_node=_cim_xml.PARAMETER_REFARRAY(
                'MyParm',
            ),
            exp_xml_str_list=[
                '<PARAMETER.REFARRAY NAME="MyParm"/>',
            ],
        ),
        None, None, True
    ),
    (
        "PARAMETER.REFARRAY, fully equipped",
        dict(
            xml_node=_cim_xml.PARAMETER_REFARRAY(
                'MyParm',
                reference_class='RefClass',
                array_size='4',
                qualifiers=[
                    _cim_xml.QUALIFIER('Q1', 'string'),
                    _cim_xml.QUALIFIER('Q2', 'string'),
                ]
            ),
            exp_xml_str_list=[
                '<PARAMETER.REFARRAY NAME="MyParm" '
                'REFERENCECLASS="RefClass" ARRAYSIZE="4">',
                '<QUALIFIER NAME="Q1" TYPE="string"/>',
                '<QUALIFIER NAME="Q2" TYPE="string"/>',
                '</PARAMETER.REFARRAY>',
            ],
        ),
        None, None, True
    ),

    # Testcases for MESSAGE element
    #
    # Note that the variation of child elements withion MESSAGE is tested
    # in the testcases for these child elements.
    #
    #    <!ELEMENT MESSAGE (SIMPLEREQ | MULTIREQ | SIMPLERSP | MULTIRSP |
    #                       SIMPLEEXPREQ | MULTIEXPREQ | SIMPLEEXPRSP |
    #                       MULTIEXPRSP)>
    #    <!ATTLIST MESSAGE
    #        ID CDATA #REQUIRED
    #        PROTOCOLVERSION CDATA #REQUIRED>
    (
        "MESSAGE with minimalistic children",
        dict(
            xml_node=_cim_xml.MESSAGE(
                _cim_xml.SIMPLEREQ(
                    _cim_xml.IMETHODCALL(
                        'EnumerateInstances',
                        simple_LOCALNAMESPACEPATH_node(),
                    ),
                ),
                '1001', '1.4'),
            exp_xml_str_list=[
                '<MESSAGE ID="1001" PROTOCOLVERSION="1.4">',
                '<SIMPLEREQ>',
                '<IMETHODCALL NAME="EnumerateInstances">',
                simple_LOCALNAMESPACEPATH_str(),
                '</IMETHODCALL>',
                '</SIMPLEREQ>',
                '</MESSAGE>',
            ],
        ),
        None, None, True
    ),

    # Testcases for MULTIREQ element (within MESSAGE element)
    #
    #    <!ELEMENT MULTIREQ (SIMPLEREQ, SIMPLEREQ+)>
    (
        "MESSAGE/MULTIREQ: Request for two intrinsic operation calls",
        dict(
            xml_node=_cim_xml.MESSAGE(
                _cim_xml.MULTIREQ([
                    _cim_xml.SIMPLEREQ(
                        _cim_xml.IMETHODCALL(
                            'EnumerateInstances',
                            simple_LOCALNAMESPACEPATH_node(),
                            [
                                _cim_xml.IPARAMVALUE(
                                    'ClassName',
                                    simple_CLASSNAME_node(),
                                ),
                            ],
                        ),
                    ),
                    _cim_xml.SIMPLEREQ(
                        _cim_xml.IMETHODCALL(
                            'EnumerateInstanceNames',
                            simple_LOCALNAMESPACEPATH_node(),
                            [
                                _cim_xml.IPARAMVALUE(
                                    'ClassName',
                                    simple_CLASSNAME_node(),
                                ),
                            ],
                        ),
                    ),
                ]),
                '1001', '1.4'),
            exp_xml_str_list=[
                '<MESSAGE ID="1001" PROTOCOLVERSION="1.4">',
                '<MULTIREQ>',
                '<SIMPLEREQ>',
                '<IMETHODCALL NAME="EnumerateInstances">',
                simple_LOCALNAMESPACEPATH_str(),
                '<IPARAMVALUE NAME="ClassName">',
                simple_CLASSNAME_str(),
                '</IPARAMVALUE>',
                '</IMETHODCALL>',
                '</SIMPLEREQ>',
                '<SIMPLEREQ>',
                '<IMETHODCALL NAME="EnumerateInstanceNames">',
                simple_LOCALNAMESPACEPATH_str(),
                '<IPARAMVALUE NAME="ClassName">',
                simple_CLASSNAME_str(),
                '</IPARAMVALUE>',
                '</IMETHODCALL>',
                '</SIMPLEREQ>',
                '</MULTIREQ>',
                '</MESSAGE>',
            ],
        ),
        None, None, True
    ),

    # Testcases for MULTIEXPREQ element (within MESSAGE element)
    #
    #    <!ELEMENT MULTIEXPREQ (SIMPLEEXPREQ, SIMPLEEXPREQ+)>
    (
        "MESSAGE/MULTIEXPREQ: Request for two export method calls",
        dict(
            xml_node=_cim_xml.MESSAGE(
                _cim_xml.MULTIEXPREQ([
                    _cim_xml.SIMPLEEXPREQ(
                        _cim_xml.EXPMETHODCALL(
                            'DeliverIndication',
                        ),
                    ),
                    _cim_xml.SIMPLEEXPREQ(
                        _cim_xml.EXPMETHODCALL(
                            'DeliverIndication2',
                        ),
                    ),
                ]),
                '1001', '1.4'),
            exp_xml_str_list=[
                '<MESSAGE ID="1001" PROTOCOLVERSION="1.4">',
                '<MULTIEXPREQ>',
                '<SIMPLEEXPREQ>',
                '<EXPMETHODCALL NAME="DeliverIndication"/>',
                '</SIMPLEEXPREQ>',
                '<SIMPLEEXPREQ>',
                '<EXPMETHODCALL NAME="DeliverIndication2"/>',
                '</SIMPLEEXPREQ>',
                '</MULTIEXPREQ>',
                '</MESSAGE>',
            ],
        ),
        None, None, True
    ),

    # Testcases for SIMPLEREQ, IMETHODCALL, METHODCALL elements
    # (within MESSAGE element)
    #
    #    <!ELEMENT SIMPLEREQ (IMETHODCALL | METHODCALL)>
    #
    #    <!ELEMENT IMETHODCALL (LOCALNAMESPACEPATH, IPARAMVALUE*)>
    #    <!ATTLIST IMETHODCALL
    #        %CIMName;>
    #
    #    <!ELEMENT METHODCALL ((LOCALINSTANCEPATH | LOCALCLASSPATH),
    #                          PARAMVALUE*)>
    #    <!ATTLIST METHODCALL
    #        %CIMName;>
    (
        "MESSAGE/SIMPLEREQ: Request for intrinsic operation call",
        dict(
            xml_node=_cim_xml.MESSAGE(
                _cim_xml.SIMPLEREQ(
                    _cim_xml.IMETHODCALL(
                        'EnumerateInstances',
                        simple_LOCALNAMESPACEPATH_node(),
                        [
                            _cim_xml.IPARAMVALUE(
                                'ClassName',
                                simple_CLASSNAME_node(),
                            ),
                        ],
                    ),
                ),
                '1001', '1.4'),
            exp_xml_str_list=[
                '<MESSAGE ID="1001" PROTOCOLVERSION="1.4">',
                '<SIMPLEREQ>',
                '<IMETHODCALL NAME="EnumerateInstances">',
                simple_LOCALNAMESPACEPATH_str(),
                '<IPARAMVALUE NAME="ClassName">',
                simple_CLASSNAME_str(),
                '</IPARAMVALUE>',
                '</IMETHODCALL>',
                '</SIMPLEREQ>',
                '</MESSAGE>',
            ],
        ),
        None, None, True
    ),
    (
        "MESSAGE/SIMPLEREQ: Request for extrinsic method call with "
        "two parameters",
        dict(
            xml_node=_cim_xml.MESSAGE(
                _cim_xml.SIMPLEREQ(
                    _cim_xml.METHODCALL(
                        'MyMethod',
                        simple_LOCALINSTANCEPATH_node(),
                        [
                            _cim_xml.PARAMVALUE(
                                'Parm1',
                                _cim_xml.VALUE('abc'),
                            ),
                            _cim_xml.PARAMVALUE(
                                'Parm2',
                                _cim_xml.VALUE('def'),
                            ),
                        ],
                    ),
                ),
                '1001', '1.4'),
            exp_xml_str_list=[
                '<MESSAGE ID="1001" PROTOCOLVERSION="1.4">',
                '<SIMPLEREQ>',
                '<METHODCALL NAME="MyMethod">',
                simple_LOCALINSTANCEPATH_str(),
                '<PARAMVALUE NAME="Parm1">',
                '<VALUE>abc</VALUE>',
                '</PARAMVALUE>',
                '<PARAMVALUE NAME="Parm2">',
                '<VALUE>def</VALUE>',
                '</PARAMVALUE>',
                '</METHODCALL>',
                '</SIMPLEREQ>',
                '</MESSAGE>',
            ],
        ),
        None, None, True
    ),

    # Testcases for SIMPLEEXPREQ, EXPMETHODCALL elements
    # (within MESSAGE element)
    #
    #    <!ELEMENT SIMPLEEXPREQ (EXPMETHODCALL)>
    #
    #    <!ELEMENT EXPMETHODCALL (EXPPARAMVALUE*)>
    #    <!ATTLIST EXPMETHODCALL
    #        %CIMName;>
    (
        "MESSAGE/SIMPLEEXPREQ: Request for export method call with "
        "two parameters",
        dict(
            xml_node=_cim_xml.MESSAGE(
                _cim_xml.SIMPLEEXPREQ(
                    _cim_xml.EXPMETHODCALL(
                        'DeliverIndication',
                        [
                            _cim_xml.EXPPARAMVALUE(
                                'Parm1',
                                _cim_xml.VALUE('abc'),
                            ),
                            _cim_xml.EXPPARAMVALUE(
                                'Parm2',
                                _cim_xml.VALUE('def'),
                            ),
                        ],
                    ),
                ),
                '1001', '1.4'),
            exp_xml_str_list=[
                '<MESSAGE ID="1001" PROTOCOLVERSION="1.4">',
                '<SIMPLEEXPREQ>',
                '<EXPMETHODCALL NAME="DeliverIndication">',
                '<EXPPARAMVALUE NAME="Parm1">',
                '<VALUE>abc</VALUE>',
                '</EXPPARAMVALUE>',
                '<EXPPARAMVALUE NAME="Parm2">',
                '<VALUE>def</VALUE>',
                '</EXPPARAMVALUE>',
                '</EXPMETHODCALL>',
                '</SIMPLEEXPREQ>',
                '</MESSAGE>',
            ],
        ),
        None, None, True
    ),

    # Testcases for SIMPLERSP, IMETHODRESPONSE, METHODRESPONSE elements
    # (within MESSAGE element)
    #
    #    <!ELEMENT SIMPLERSP (METHODRESPONSE | IMETHODRESPONSE)>
    #
    #    <!ELEMENT IMETHODRESPONSE (ERROR | (IRETURNVALUE?, PARAMVALUE*))>
    #    <!ATTLIST IMETHODRESPONSE
    #        %CIMName;>
    #
    #    <!ELEMENT METHODRESPONSE (ERROR | (RETURNVALUE?, PARAMVALUE*))>
    #    <!ATTLIST METHODRESPONSE
    #        %CIMName;>
    (
        "MESSAGE/SIMPLERSP: Response from intrinsic operation call, "
        "success without return value",
        dict(
            xml_node=_cim_xml.MESSAGE(
                _cim_xml.SIMPLERSP(
                    _cim_xml.IMETHODRESPONSE(
                        'ModifyInstance',
                    ),
                ),
                '1001', '1.4'),
            exp_xml_str_list=[
                '<MESSAGE ID="1001" PROTOCOLVERSION="1.4">',
                '<SIMPLERSP>',
                '<IMETHODRESPONSE NAME="ModifyInstance"/>',
                '</SIMPLERSP>',
                '</MESSAGE>',
            ],
        ),
        None, None, True
    ),
    (
        "MESSAGE/SIMPLERSP: Response from intrinsic operation call, "
        "success with return value",
        dict(
            xml_node=_cim_xml.MESSAGE(
                _cim_xml.SIMPLERSP(
                    _cim_xml.IMETHODRESPONSE(
                        'EnumerateInstances',
                        _cim_xml.IRETURNVALUE([
                            simple_VALUE_NAMEDINSTANCE_node('C1'),
                            simple_VALUE_NAMEDINSTANCE_node('C2'),
                        ]),
                    ),
                ),
                '1001', '1.4'),
            exp_xml_str_list=[
                '<MESSAGE ID="1001" PROTOCOLVERSION="1.4">',
                '<SIMPLERSP>',
                '<IMETHODRESPONSE NAME="EnumerateInstances">',
                '<IRETURNVALUE>',
                simple_VALUE_NAMEDINSTANCE_str('C1'),
                simple_VALUE_NAMEDINSTANCE_str('C2'),
                '</IRETURNVALUE>',
                '</IMETHODRESPONSE>',
                '</SIMPLERSP>',
                '</MESSAGE>',
            ],
        ),
        None, None, True
    ),
    (
        "MESSAGE/SIMPLERSP: Response from intrinsic operation call, "
        "success with return value and two output parameters",
        dict(
            xml_node=_cim_xml.MESSAGE(
                _cim_xml.SIMPLERSP(
                    _cim_xml.IMETHODRESPONSE(
                        'EnumerateInstances',
                        [
                            _cim_xml.IRETURNVALUE([
                                simple_VALUE_NAMEDINSTANCE_node('C1'),
                                simple_VALUE_NAMEDINSTANCE_node('C2'),
                            ]),
                            _cim_xml.PARAMVALUE(
                                'Parm1',
                                _cim_xml.VALUE('abc'),
                            ),
                            _cim_xml.PARAMVALUE(
                                'Parm2',
                                _cim_xml.VALUE('def'),
                            ),
                        ],
                    ),
                ),
                '1001', '1.4'),
            exp_xml_str_list=[
                '<MESSAGE ID="1001" PROTOCOLVERSION="1.4">',
                '<SIMPLERSP>',
                '<IMETHODRESPONSE NAME="EnumerateInstances">',
                '<IRETURNVALUE>',
                simple_VALUE_NAMEDINSTANCE_str('C1'),
                simple_VALUE_NAMEDINSTANCE_str('C2'),
                '</IRETURNVALUE>',
                '<PARAMVALUE NAME="Parm1">',
                '<VALUE>abc</VALUE>',
                '</PARAMVALUE>',
                '<PARAMVALUE NAME="Parm2">',
                '<VALUE>def</VALUE>',
                '</PARAMVALUE>',
                '</IMETHODRESPONSE>',
                '</SIMPLERSP>',
                '</MESSAGE>',
            ],
        ),
        None, None, True
    ),
    (
        "MESSAGE/SIMPLERSP: Response from intrinsic operation call, error",
        dict(
            xml_node=_cim_xml.MESSAGE(
                _cim_xml.SIMPLERSP(
                    _cim_xml.IMETHODRESPONSE(
                        'EnumerateInstances',
                        _cim_xml.ERROR('6', 'Class not found'),
                    ),
                ),
                '1001', '1.4'),
            exp_xml_str_list=[
                '<MESSAGE ID="1001" PROTOCOLVERSION="1.4">',
                '<SIMPLERSP>',
                '<IMETHODRESPONSE NAME="EnumerateInstances">',
                '<ERROR CODE="6" DESCRIPTION="Class not found"/>',
                '</IMETHODRESPONSE>',
                '</SIMPLERSP>',
                '</MESSAGE>',
            ],
        ),
        None, None, True
    ),
    (
        "MESSAGE/SIMPLERSP: Response from extrinsic method call, "
        "success without return value",
        dict(
            xml_node=_cim_xml.MESSAGE(
                _cim_xml.SIMPLERSP(
                    _cim_xml.METHODRESPONSE(
                        'MyMethod',
                    ),
                ),
                '1001', '1.4'),
            exp_xml_str_list=[
                '<MESSAGE ID="1001" PROTOCOLVERSION="1.4">',
                '<SIMPLERSP>',
                '<METHODRESPONSE NAME="MyMethod"/>',
                '</SIMPLERSP>',
                '</MESSAGE>',
            ],
        ),
        None, None, True
    ),
    (
        "MESSAGE/SIMPLERSP: Response from extrinsic method call, "
        "success with return value",
        dict(
            xml_node=_cim_xml.MESSAGE(
                _cim_xml.SIMPLERSP(
                    _cim_xml.METHODRESPONSE(
                        'MyMethod',
                        _cim_xml.RETURNVALUE(
                            _cim_xml.VALUE('abc'),
                        ),
                    ),
                ),
                '1001', '1.4'),
            exp_xml_str_list=[
                '<MESSAGE ID="1001" PROTOCOLVERSION="1.4">',
                '<SIMPLERSP>',
                '<METHODRESPONSE NAME="MyMethod">',
                '<RETURNVALUE>',
                '<VALUE>abc</VALUE>',
                '</RETURNVALUE>',
                '</METHODRESPONSE>',
                '</SIMPLERSP>',
                '</MESSAGE>',
            ],
        ),
        None, None, True
    ),
    (
        "MESSAGE/SIMPLERSP: Response from extrinsic method call, "
        "success with return value and two output parameters",
        dict(
            xml_node=_cim_xml.MESSAGE(
                _cim_xml.SIMPLERSP(
                    _cim_xml.METHODRESPONSE(
                        'MyMethod',
                        [
                            _cim_xml.RETURNVALUE(
                                _cim_xml.VALUE('abc'),
                            ),
                            _cim_xml.PARAMVALUE(
                                'Parm1',
                                _cim_xml.VALUE('foo'),
                            ),
                            _cim_xml.PARAMVALUE(
                                'Parm2',
                                _cim_xml.VALUE('bar'),
                            ),
                        ],
                    ),
                ),
                '1001', '1.4'),
            exp_xml_str_list=[
                '<MESSAGE ID="1001" PROTOCOLVERSION="1.4">',
                '<SIMPLERSP>',
                '<METHODRESPONSE NAME="MyMethod">',
                '<RETURNVALUE>',
                '<VALUE>abc</VALUE>',
                '</RETURNVALUE>',
                '<PARAMVALUE NAME="Parm1">',
                '<VALUE>foo</VALUE>',
                '</PARAMVALUE>',
                '<PARAMVALUE NAME="Parm2">',
                '<VALUE>bar</VALUE>',
                '</PARAMVALUE>',
                '</METHODRESPONSE>',
                '</SIMPLERSP>',
                '</MESSAGE>',
            ],
        ),
        None, None, True
    ),
    (
        "MESSAGE/SIMPLERSP: Response from extrinsic method call, error",
        dict(
            xml_node=_cim_xml.MESSAGE(
                _cim_xml.SIMPLERSP(
                    _cim_xml.METHODRESPONSE(
                        'MyMethod',
                        _cim_xml.ERROR('6', 'Class not found'),
                    ),
                ),
                '1001', '1.4'),
            exp_xml_str_list=[
                '<MESSAGE ID="1001" PROTOCOLVERSION="1.4">',
                '<SIMPLERSP>',
                '<METHODRESPONSE NAME="MyMethod">',
                '<ERROR CODE="6" DESCRIPTION="Class not found"/>',
                '</METHODRESPONSE>',
                '</SIMPLERSP>',
                '</MESSAGE>',
            ],
        ),
        None, None, True
    ),

    # Testcases for SIMPLEEXPRSP, EXPMETHODRESPONSE elements
    # (within MESSAGE element)
    #
    #    <!ELEMENT SIMPLEEXPRSP (EXPMETHODRESPONSE)>
    #
    #    <!ELEMENT EXPMETHODRESPONSE (ERROR | IRETURNVALUE?)>
    #    <!ATTLIST EXPMETHODRESPONSE
    #        %CIMName;>
    (
        "MESSAGE/SIMPLEEXPRSP: Response from export method call, "
        "success without return value",
        dict(
            xml_node=_cim_xml.MESSAGE(
                _cim_xml.SIMPLEEXPRSP(
                    _cim_xml.EXPMETHODRESPONSE(
                        'DeliverIndication',
                    ),
                ),
                '1001', '1.4'),
            exp_xml_str_list=[
                '<MESSAGE ID="1001" PROTOCOLVERSION="1.4">',
                '<SIMPLEEXPRSP>',
                '<EXPMETHODRESPONSE NAME="DeliverIndication"/>',
                '</SIMPLEEXPRSP>',
                '</MESSAGE>',
            ],
        ),
        None, None, True
    ),
    (
        "MESSAGE/SIMPLEEXPRSP: Response from export method call, "
        "success with return value",
        dict(
            xml_node=_cim_xml.MESSAGE(
                _cim_xml.SIMPLEEXPRSP(
                    _cim_xml.EXPMETHODRESPONSE(
                        'DeliverIndication',
                        _cim_xml.IRETURNVALUE(
                            _cim_xml.VALUE('abc'),
                        ),
                    ),
                ),
                '1001', '1.4'),
            exp_xml_str_list=[
                '<MESSAGE ID="1001" PROTOCOLVERSION="1.4">',
                '<SIMPLEEXPRSP>',
                '<EXPMETHODRESPONSE NAME="DeliverIndication">',
                '<IRETURNVALUE>',
                '<VALUE>abc</VALUE>',
                '</IRETURNVALUE>',
                '</EXPMETHODRESPONSE>',
                '</SIMPLEEXPRSP>',
                '</MESSAGE>',
            ],
        ),
        None, None, True
    ),
    (
        "MESSAGE/SIMPLEEXPRSP: Response from export method call, error",
        dict(
            xml_node=_cim_xml.MESSAGE(
                _cim_xml.SIMPLEEXPRSP(
                    _cim_xml.EXPMETHODRESPONSE(
                        'DeliverIndication',
                        _cim_xml.ERROR('6', 'Class not found'),
                    ),
                ),
                '1001', '1.4'),
            exp_xml_str_list=[
                '<MESSAGE ID="1001" PROTOCOLVERSION="1.4">',
                '<SIMPLEEXPRSP>',
                '<EXPMETHODRESPONSE NAME="DeliverIndication">',
                '<ERROR CODE="6" DESCRIPTION="Class not found"/>',
                '</EXPMETHODRESPONSE>',
                '</SIMPLEEXPRSP>',
                '</MESSAGE>',
            ],
        ),
        None, None, True
    ),

    # Testcases for MULTIRSP element (within MESSAGE element)
    #
    #    <!ELEMENT MULTIRSP (SIMPLERSP, SIMPLERSP+)>
    (
        "MESSAGE/MULTIRSP: Response from two intrinsic operation calls",
        dict(
            xml_node=_cim_xml.MESSAGE(
                _cim_xml.MULTIRSP([
                    _cim_xml.SIMPLERSP(
                        _cim_xml.IMETHODRESPONSE(
                            'ModifyInstance',
                        ),
                    ),
                    _cim_xml.SIMPLERSP(
                        _cim_xml.IMETHODRESPONSE(
                            'DeleteInstance',
                        ),
                    ),
                ]),
                '1001', '1.4'),
            exp_xml_str_list=[
                '<MESSAGE ID="1001" PROTOCOLVERSION="1.4">',
                '<MULTIRSP>',
                '<SIMPLERSP>',
                '<IMETHODRESPONSE NAME="ModifyInstance"/>',
                '</SIMPLERSP>',
                '<SIMPLERSP>',
                '<IMETHODRESPONSE NAME="DeleteInstance"/>',
                '</SIMPLERSP>',
                '</MULTIRSP>',
                '</MESSAGE>',
            ],
        ),
        None, None, True
    ),

    # Testcases for MULTIEXPRSP element (within MESSAGE element)
    #
    #    <!ELEMENT MULTIEXPRSP (SIMPLEEXPRSP, SIMPLEEXPRSP+)>
    (
        "MESSAGE/MULTIEXPRSP: Response from two export method calls",
        dict(
            xml_node=_cim_xml.MESSAGE(
                _cim_xml.MULTIEXPRSP([
                    _cim_xml.SIMPLEEXPRSP(
                        _cim_xml.EXPMETHODRESPONSE(
                            'DeliverIndication',
                        ),
                    ),
                    _cim_xml.SIMPLEEXPRSP(
                        _cim_xml.EXPMETHODRESPONSE(
                            'DeliverIndication2',
                        ),
                    ),
                ]),
                '1001', '1.4'),
            exp_xml_str_list=[
                '<MESSAGE ID="1001" PROTOCOLVERSION="1.4">',
                '<MULTIEXPRSP>',
                '<SIMPLEEXPRSP>',
                '<EXPMETHODRESPONSE NAME="DeliverIndication"/>',
                '</SIMPLEEXPRSP>',
                '<SIMPLEEXPRSP>',
                '<EXPMETHODRESPONSE NAME="DeliverIndication2"/>',
                '</SIMPLEEXPRSP>',
                '</MULTIEXPRSP>',
                '</MESSAGE>',
            ],
        ),
        None, None, True
    ),

    # Testcases for PARAMVALUE element
    #
    #    <!ELEMENT PARAMVALUE (VALUE | VALUE.REFERENCE | VALUE.ARRAY |
    #                          VALUE.REFARRAY | CLASSNAME | INSTANCENAME |
    #                          CLASS | INSTANCE | VALUE.NAMEDINSTANCE)?>
    #    <!ATTLIST PARAMVALUE
    #        %CIMName;
    #        %ParamType;    #IMPLIED
    #        %EmbeddedObject;>
    (
        "PARAMVALUE, minimalistic",
        dict(
            xml_node=_cim_xml.PARAMVALUE(
                'Parm1',
                _cim_xml.VALUE('foo'),
            ),
            exp_xml_str_list=[
                '<PARAMVALUE NAME="Parm1">',
                '<VALUE>foo</VALUE>',
                '</PARAMVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "PARAMVALUE representing NULL",
        dict(
            xml_node=_cim_xml.PARAMVALUE(
                'Parm1',
            ),
            exp_xml_str_list=[
                '<PARAMVALUE NAME="Parm1"/>',
            ],
        ),
        None, None, True
    ),
    (
        "PARAMVALUE, with string VALUE",
        dict(
            xml_node=_cim_xml.PARAMVALUE(
                'Parm1',
                _cim_xml.VALUE('foo'),
                paramtype='string',
            ),
            exp_xml_str_list=[
                '<PARAMVALUE NAME="Parm1" PARAMTYPE="string">',
                '<VALUE>foo</VALUE>',
                '</PARAMVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "PARAMVALUE, with embedded instance VALUE",
        dict(
            xml_node=_cim_xml.PARAMVALUE(
                'Parm1',
                _cim_xml.VALUE('(the instance)'),
                paramtype='string',
                embedded_object='instance',
            ),
            exp_xml_str_list=[
                '<PARAMVALUE NAME="Parm1" PARAMTYPE="string" '
                'EmbeddedObject="instance">',
                '<VALUE>(the instance)</VALUE>',
                '</PARAMVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "PARAMVALUE, with VALUE.REFERENCE",
        dict(
            xml_node=_cim_xml.PARAMVALUE(
                'Parm1',
                _cim_xml.VALUE_REFERENCE(
                    simple_INSTANCENAME_node(),
                ),
                paramtype='reference',
            ),
            exp_xml_str_list=[
                '<PARAMVALUE NAME="Parm1" PARAMTYPE="reference">',
                '<VALUE.REFERENCE>',
                simple_INSTANCENAME_str(),
                '</VALUE.REFERENCE>',
                '</PARAMVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "PARAMVALUE, with VALUE.ARRAY",
        dict(
            xml_node=_cim_xml.PARAMVALUE(
                'Parm1',
                _cim_xml.VALUE_ARRAY([]),
                paramtype='string',
            ),
            exp_xml_str_list=[
                '<PARAMVALUE NAME="Parm1" PARAMTYPE="string">',
                '<VALUE.ARRAY/>',
                '</PARAMVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "PARAMVALUE, with VALUE.REFARRAY",
        dict(
            xml_node=_cim_xml.PARAMVALUE(
                'Parm1',
                _cim_xml.VALUE_REFARRAY([]),
                paramtype='reference',
            ),
            exp_xml_str_list=[
                '<PARAMVALUE NAME="Parm1" PARAMTYPE="reference">',
                '<VALUE.REFARRAY/>',
                '</PARAMVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "PARAMVALUE, with CLASSNAME",
        dict(
            xml_node=_cim_xml.PARAMVALUE(
                'Parm1',
                simple_CLASSNAME_node(),
            ),
            exp_xml_str_list=[
                '<PARAMVALUE NAME="Parm1">',
                simple_CLASSNAME_str(),
                '</PARAMVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "PARAMVALUE, with INSTANCENAME",
        dict(
            xml_node=_cim_xml.PARAMVALUE(
                'Parm1',
                simple_INSTANCENAME_node(),
            ),
            exp_xml_str_list=[
                '<PARAMVALUE NAME="Parm1">',
                simple_INSTANCENAME_str(),
                '</PARAMVALUE>',
            ],
        ),
        None, None, DTD_VERSION >= (2, 4)
    ),
    (
        "PARAMVALUE, with CLASS",
        dict(
            xml_node=_cim_xml.PARAMVALUE(
                'Parm1',
                simple_CLASS_node(),
            ),
            exp_xml_str_list=[
                '<PARAMVALUE NAME="Parm1">',
                simple_CLASS_str(),
                '</PARAMVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "PARAMVALUE, with INSTANCE",
        dict(
            xml_node=_cim_xml.PARAMVALUE(
                'Parm1',
                simple_INSTANCE_node(),
            ),
            exp_xml_str_list=[
                '<PARAMVALUE NAME="Parm1">',
                simple_INSTANCE_str(),
                '</PARAMVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "PARAMVALUE, with VALUE.NAMEDINSTANCE",
        dict(
            xml_node=_cim_xml.PARAMVALUE(
                'Parm1',
                simple_VALUE_NAMEDINSTANCE_node(),
            ),
            exp_xml_str_list=[
                '<PARAMVALUE NAME="Parm1">',
                simple_VALUE_NAMEDINSTANCE_str(),
                '</PARAMVALUE>',
            ],
        ),
        None, None, True
    ),

    # Testcases for IPARAMVALUE element
    #
    #    <!ELEMENT IPARAMVALUE (VALUE | VALUE.ARRAY | VALUE.REFERENCE |
    #                           INSTANCENAME | CLASSNAME |
    #                           QUALIFIER.DECLARATION |
    #                           CLASS | INSTANCE | VALUE.NAMEDINSTANCE)?>
    #    <!ATTLIST IPARAMVALUE
    #        %CIMName;>
    (
        "IPARAMVALUE, minimalistic",
        dict(
            xml_node=_cim_xml.IPARAMVALUE(
                'Parm1',
                _cim_xml.VALUE('foo'),
            ),
            exp_xml_str_list=[
                '<IPARAMVALUE NAME="Parm1">',
                '<VALUE>foo</VALUE>',
                '</IPARAMVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "IPARAMVALUE representing NULL",
        dict(
            xml_node=_cim_xml.IPARAMVALUE(
                'Parm1',
            ),
            exp_xml_str_list=[
                '<IPARAMVALUE NAME="Parm1"/>',
            ],
        ),
        None, None, True
    ),
    (
        "IPARAMVALUE, with string VALUE",
        dict(
            xml_node=_cim_xml.IPARAMVALUE(
                'Parm1',
                _cim_xml.VALUE('foo'),
            ),
            exp_xml_str_list=[
                '<IPARAMVALUE NAME="Parm1">',
                '<VALUE>foo</VALUE>',
                '</IPARAMVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "IPARAMVALUE, with VALUE.ARRAY",
        dict(
            xml_node=_cim_xml.IPARAMVALUE(
                'Parm1',
                _cim_xml.VALUE_ARRAY([]),
            ),
            exp_xml_str_list=[
                '<IPARAMVALUE NAME="Parm1">',
                '<VALUE.ARRAY/>',
                '</IPARAMVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "IPARAMVALUE, with VALUE.REFERENCE",
        dict(
            xml_node=_cim_xml.IPARAMVALUE(
                'Parm1',
                _cim_xml.VALUE_REFERENCE(
                    simple_INSTANCENAME_node(),
                ),
            ),
            exp_xml_str_list=[
                '<IPARAMVALUE NAME="Parm1">',
                '<VALUE.REFERENCE>',
                simple_INSTANCENAME_str(),
                '</VALUE.REFERENCE>',
                '</IPARAMVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "IPARAMVALUE, with INSTANCENAME",
        dict(
            xml_node=_cim_xml.IPARAMVALUE(
                'Parm1',
                simple_INSTANCENAME_node(),
            ),
            exp_xml_str_list=[
                '<IPARAMVALUE NAME="Parm1">',
                simple_INSTANCENAME_str(),
                '</IPARAMVALUE>',
            ],
        ),
        None, None, DTD_VERSION >= (2, 4)
    ),
    (
        "IPARAMVALUE, with CLASSNAME",
        dict(
            xml_node=_cim_xml.IPARAMVALUE(
                'Parm1',
                simple_CLASSNAME_node(),
            ),
            exp_xml_str_list=[
                '<IPARAMVALUE NAME="Parm1">',
                simple_CLASSNAME_str(),
                '</IPARAMVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "IPARAMVALUE, with QUALIFIER.DECLARATION",
        dict(
            xml_node=_cim_xml.IPARAMVALUE(
                'Parm1',
                simple_QUALIFIER_DECLARATION_node(),
            ),
            exp_xml_str_list=[
                '<IPARAMVALUE NAME="Parm1">',
                simple_QUALIFIER_DECLARATION_str(),
                '</IPARAMVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "IPARAMVALUE, with CLASS",
        dict(
            xml_node=_cim_xml.IPARAMVALUE(
                'Parm1',
                simple_CLASS_node(),
            ),
            exp_xml_str_list=[
                '<IPARAMVALUE NAME="Parm1">',
                simple_CLASS_str(),
                '</IPARAMVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "IPARAMVALUE, with INSTANCE",
        dict(
            xml_node=_cim_xml.IPARAMVALUE(
                'Parm1',
                simple_INSTANCE_node(),
            ),
            exp_xml_str_list=[
                '<IPARAMVALUE NAME="Parm1">',
                simple_INSTANCE_str(),
                '</IPARAMVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "IPARAMVALUE, with VALUE.NAMEDINSTANCE",
        dict(
            xml_node=_cim_xml.IPARAMVALUE(
                'Parm1',
                simple_VALUE_NAMEDINSTANCE_node(),
            ),
            exp_xml_str_list=[
                '<IPARAMVALUE NAME="Parm1">',
                simple_VALUE_NAMEDINSTANCE_str(),
                '</IPARAMVALUE>',
            ],
        ),
        None, None, True
    ),


    # Testcases for EXPPARAMVALUE element
    #
    #    <!ELEMENT EXPPARAMVALUE (INSTANCE?)>
    #    <!ATTLIST EXPPARAMVALUE
    #        %CIMName;
    (
        "EXPPARAMVALUE representing NULL",
        dict(
            xml_node=_cim_xml.EXPPARAMVALUE('Parm1'),
            exp_xml_str_list=[
                '<EXPPARAMVALUE NAME="Parm1"/>',
            ],
        ),
        None, None, True
    ),
    (
        "EXPPARAMVALUE with INSTANCE",
        dict(
            xml_node=_cim_xml.EXPPARAMVALUE(
                'Parm1',
                simple_INSTANCE_node(),
            ),
            exp_xml_str_list=[
                '<EXPPARAMVALUE NAME="Parm1">',
                simple_INSTANCE_str(),
                '</EXPPARAMVALUE>',
            ],
        ),
        None, None, True
    ),

    # Testcases for RETURNVALUE element
    #
    #    <!ELEMENT RETURNVALUE (VALUE | VALUE.REFERENCE)?>
    #    <!ATTLIST RETURNVALUE
    #        %EmbeddedObject;
    #        %ParamType;     #IMPLIED>
    (
        "RETURNVALUE representing NULL",
        dict(
            xml_node=_cim_xml.RETURNVALUE(None),
            exp_xml_str_list=[
                '<RETURNVALUE/>',
            ],
        ),
        None, None, True
    ),
    (
        "RETURNVALUE, with string VALUE",
        dict(
            xml_node=_cim_xml.RETURNVALUE(
                _cim_xml.VALUE('foo'),
                param_type='string',
            ),
            exp_xml_str_list=[
                '<RETURNVALUE PARAMTYPE="string">',
                '<VALUE>foo</VALUE>',
                '</RETURNVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "RETURNVALUE, with embedded instance VALUE",
        dict(
            xml_node=_cim_xml.RETURNVALUE(
                _cim_xml.VALUE('(the instance)'),
                param_type='string',
                embedded_object='instance',
            ),
            exp_xml_str_list=[
                '<RETURNVALUE PARAMTYPE="string" '
                'EmbeddedObject="instance">',
                '<VALUE>(the instance)</VALUE>',
                '</RETURNVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "RETURNVALUE, with VALUE.REFERENCE",
        dict(
            xml_node=_cim_xml.RETURNVALUE(
                _cim_xml.VALUE_REFERENCE(
                    simple_INSTANCENAME_node(),
                ),
                param_type='reference',
            ),
            exp_xml_str_list=[
                '<RETURNVALUE PARAMTYPE="reference">',
                '<VALUE.REFERENCE>',
                simple_INSTANCENAME_str(),
                '</VALUE.REFERENCE>',
                '</RETURNVALUE>',
            ],
        ),
        None, None, True
    ),

    # Testcases for IRETURNVALUE element
    #
    #    <!ELEMENT IRETURNVALUE (CLASSNAME* | INSTANCENAME* | VALUE* |
    #                            VALUE.OBJECTWITHPATH* |
    #                            VALUE.OBJECTWITHLOCALPATH* | VALUE.OBJECT* |
    #                            OBJECTPATH* | QUALIFIER.DECLARATION* |
    #                            VALUE.ARRAY? | VALUE.REFERENCE? | CLASS* |
    #                            INSTANCE* | VALUE.NAMEDINSTANCE*)>
    (
        "IRETURNVALUE representing NULL",
        dict(
            xml_node=_cim_xml.IRETURNVALUE(None),
            exp_xml_str_list=[
                '<IRETURNVALUE/>',
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with one CLASSNAME",
        dict(
            xml_node=_cim_xml.IRETURNVALUE(
                simple_CLASSNAME_node(),
            ),
            exp_xml_str_list=[
                '<IRETURNVALUE>',
                simple_CLASSNAME_str(),
                '</IRETURNVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with two CLASSNAME",
        dict(
            xml_node=_cim_xml.IRETURNVALUE([
                simple_CLASSNAME_node('C1'),
                simple_CLASSNAME_node('C2'),
            ]),
            exp_xml_str_list=[
                '<IRETURNVALUE>',
                simple_CLASSNAME_str('C1'),
                simple_CLASSNAME_str('C2'),
                '</IRETURNVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with one INSTANCENAME",
        dict(
            xml_node=_cim_xml.IRETURNVALUE(
                simple_INSTANCENAME_node(),
            ),
            exp_xml_str_list=[
                '<IRETURNVALUE>',
                simple_INSTANCENAME_str(),
                '</IRETURNVALUE>',
            ],
        ),
        None, None, DTD_VERSION >= (2, 4)
    ),
    (
        "IRETURNVALUE with two INSTANCENAME",
        dict(
            xml_node=_cim_xml.IRETURNVALUE([
                simple_INSTANCENAME_node('C1'),
                simple_INSTANCENAME_node('C2'),
            ]),
            exp_xml_str_list=[
                '<IRETURNVALUE>',
                simple_INSTANCENAME_str('C1'),
                simple_INSTANCENAME_str('C2'),
                '</IRETURNVALUE>',
            ],
        ),
        None, None, DTD_VERSION >= (2, 4)
    ),
    (
        "IRETURNVALUE with one string VALUE",
        dict(
            xml_node=_cim_xml.IRETURNVALUE(
                _cim_xml.VALUE('foo'),
            ),
            exp_xml_str_list=[
                '<IRETURNVALUE>',
                '<VALUE>foo</VALUE>',
                '</IRETURNVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with two string VALUE",
        dict(
            xml_node=_cim_xml.IRETURNVALUE([
                _cim_xml.VALUE('foo'),
                _cim_xml.VALUE('bar'),
            ]),
            exp_xml_str_list=[
                '<IRETURNVALUE>',
                '<VALUE>foo</VALUE>',
                '<VALUE>bar</VALUE>',
                '</IRETURNVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with one VALUE.OBJECTWITHPATH",
        dict(
            xml_node=_cim_xml.IRETURNVALUE(
                simple_VALUE_OBJECTWITHPATH_node(),
            ),
            exp_xml_str_list=[
                '<IRETURNVALUE>',
                simple_VALUE_OBJECTWITHPATH_str(),
                '</IRETURNVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with two VALUE.OBJECTWITHPATH",
        dict(
            xml_node=_cim_xml.IRETURNVALUE([
                simple_VALUE_OBJECTWITHPATH_node('C1'),
                simple_VALUE_OBJECTWITHPATH_node('C2'),
            ]),
            exp_xml_str_list=[
                '<IRETURNVALUE>',
                simple_VALUE_OBJECTWITHPATH_str('C1'),
                simple_VALUE_OBJECTWITHPATH_str('C2'),
                '</IRETURNVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with one VALUE.OBJECTWITHLOCALPATH",
        dict(
            xml_node=_cim_xml.IRETURNVALUE(
                simple_VALUE_OBJECTWITHLOCALPATH_node(),
            ),
            exp_xml_str_list=[
                '<IRETURNVALUE>',
                simple_VALUE_OBJECTWITHLOCALPATH_str(),
                '</IRETURNVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with two VALUE.OBJECTWITHLOCALPATH",
        dict(
            xml_node=_cim_xml.IRETURNVALUE([
                simple_VALUE_OBJECTWITHLOCALPATH_node('C1'),
                simple_VALUE_OBJECTWITHLOCALPATH_node('C2'),
            ]),
            exp_xml_str_list=[
                '<IRETURNVALUE>',
                simple_VALUE_OBJECTWITHLOCALPATH_str('C1'),
                simple_VALUE_OBJECTWITHLOCALPATH_str('C2'),
                '</IRETURNVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with one VALUE.OBJECT",
        dict(
            xml_node=_cim_xml.IRETURNVALUE(
                simple_VALUE_OBJECT_node(),
            ),
            exp_xml_str_list=[
                '<IRETURNVALUE>',
                simple_VALUE_OBJECT_str(),
                '</IRETURNVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with two VALUE.OBJECT",
        dict(
            xml_node=_cim_xml.IRETURNVALUE([
                simple_VALUE_OBJECT_node('C1'),
                simple_VALUE_OBJECT_node('C2'),
            ]),
            exp_xml_str_list=[
                '<IRETURNVALUE>',
                simple_VALUE_OBJECT_str('C1'),
                simple_VALUE_OBJECT_str('C2'),
                '</IRETURNVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with one OBJECTPATH",
        dict(
            xml_node=_cim_xml.IRETURNVALUE(
                simple_OBJECTPATH_node(),
            ),
            exp_xml_str_list=[
                '<IRETURNVALUE>',
                simple_OBJECTPATH_str(),
                '</IRETURNVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with two OBJECTPATH",
        dict(
            xml_node=_cim_xml.IRETURNVALUE([
                simple_OBJECTPATH_node('C1'),
                simple_OBJECTPATH_node('C2'),
            ]),
            exp_xml_str_list=[
                '<IRETURNVALUE>',
                simple_OBJECTPATH_str('C1'),
                simple_OBJECTPATH_str('C2'),
                '</IRETURNVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with one QUALIFIER.DECLARATION",
        dict(
            xml_node=_cim_xml.IRETURNVALUE(
                simple_QUALIFIER_DECLARATION_node(),
            ),
            exp_xml_str_list=[
                '<IRETURNVALUE>',
                simple_QUALIFIER_DECLARATION_str(),
                '</IRETURNVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with two QUALIFIER.DECLARATION",
        dict(
            xml_node=_cim_xml.IRETURNVALUE([
                simple_QUALIFIER_DECLARATION_node('Q1'),
                simple_QUALIFIER_DECLARATION_node('Q2'),
            ]),
            exp_xml_str_list=[
                '<IRETURNVALUE>',
                simple_QUALIFIER_DECLARATION_str('Q1'),
                simple_QUALIFIER_DECLARATION_str('Q2'),
                '</IRETURNVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with VALUE.ARRAY",
        dict(
            xml_node=_cim_xml.IRETURNVALUE(
                _cim_xml.VALUE_ARRAY([]),
            ),
            exp_xml_str_list=[
                '<IRETURNVALUE>',
                '<VALUE.ARRAY/>',
                '</IRETURNVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with VALUE.REFERENCE",
        dict(
            xml_node=_cim_xml.IRETURNVALUE(
                _cim_xml.VALUE_REFERENCE(
                    simple_INSTANCENAME_node(),
                ),
            ),
            exp_xml_str_list=[
                '<IRETURNVALUE>',
                '<VALUE.REFERENCE>',
                simple_INSTANCENAME_str(),
                '</VALUE.REFERENCE>',
                '</IRETURNVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with one CLASS",
        dict(
            xml_node=_cim_xml.IRETURNVALUE(
                simple_CLASS_node(),
            ),
            exp_xml_str_list=[
                '<IRETURNVALUE>',
                simple_CLASS_str(),
                '</IRETURNVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with two CLASS",
        dict(
            xml_node=_cim_xml.IRETURNVALUE([
                simple_CLASS_node('C1'),
                simple_CLASS_node('C2'),
            ]),
            exp_xml_str_list=[
                '<IRETURNVALUE>',
                simple_CLASS_str('C1'),
                simple_CLASS_str('C2'),
                '</IRETURNVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with one INSTANCE",
        dict(
            xml_node=_cim_xml.IRETURNVALUE(
                simple_INSTANCE_node(),
            ),
            exp_xml_str_list=[
                '<IRETURNVALUE>',
                simple_INSTANCE_str(),
                '</IRETURNVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with two INSTANCE",
        dict(
            xml_node=_cim_xml.IRETURNVALUE([
                simple_INSTANCE_node('C1'),
                simple_INSTANCE_node('C2'),
            ]),
            exp_xml_str_list=[
                '<IRETURNVALUE>',
                simple_INSTANCE_str('C1'),
                simple_INSTANCE_str('C2'),
                '</IRETURNVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with one VALUE.NAMEDINSTANCE",
        dict(
            xml_node=_cim_xml.IRETURNVALUE(
                simple_VALUE_NAMEDINSTANCE_node(),
            ),
            exp_xml_str_list=[
                '<IRETURNVALUE>',
                simple_VALUE_NAMEDINSTANCE_str(),
                '</IRETURNVALUE>',
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with two VALUE.NAMEDINSTANCE",
        dict(
            xml_node=_cim_xml.IRETURNVALUE([
                simple_VALUE_NAMEDINSTANCE_node('C1'),
                simple_VALUE_NAMEDINSTANCE_node('C2'),
            ]),
            exp_xml_str_list=[
                '<IRETURNVALUE>',
                simple_VALUE_NAMEDINSTANCE_str('C1'),
                simple_VALUE_NAMEDINSTANCE_str('C2'),
                '</IRETURNVALUE>',
            ],
        ),
        None, None, True
    ),

    # Testcases for ERROR element
    #
    #    <!ELEMENT ERROR (INSTANCE*)>
    #    <!ATTLIST ERROR
    #        CODE CDATA #REQUIRED
    #        DESCRIPTION CDATA #IMPLIED>
    (
        "ERROR, minimalistic",
        dict(
            xml_node=_cim_xml.ERROR('1'),
            exp_xml_str_list=[
                '<ERROR CODE="1"/>',
            ],
        ),
        None, None, True
    ),
    (
        "ERROR, with all attributes, empty list of instances",
        dict(
            xml_node=_cim_xml.ERROR(
                '1',
                description="some description",
                instances=[],
            ),
            exp_xml_str_list=[
                '<ERROR CODE="1" DESCRIPTION="some description"/>',
            ],
        ),
        None, None, True
    ),
    (
        "ERROR, with all attributes, two instances",
        dict(
            xml_node=_cim_xml.ERROR(
                '1',
                description="some description",
                instances=[
                    simple_INSTANCE_node('C1'),
                    simple_INSTANCE_node('C2'),
                ],
            ),
            exp_xml_str_list=[
                '<ERROR CODE="1" DESCRIPTION="some description">',
                simple_INSTANCE_str('C1'),
                simple_INSTANCE_str('C2'),
                '</ERROR>',
            ],
        ),
        None, None, True
    ),

]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIM_XML_NODE)
@simplified_test_function
def test_cim_xml_node(testcase, xml_node, exp_xml_str_list, **kwargs):
    # pylint: disable=unused-argument
    """
    Test function for a _cim_xml node.
    """

    cdata_escaping = kwargs.get('cdata_escaping', False)

    # Convert the _cim_xml node (a subclass of xml.dom.minidom.Element) to an
    # XML string
    act_xml_str = xml_node.toxml()

    try:
        if cdata_escaping:
            _cim_xml._CDATA_ESCAPING = True  # pylint: disable=protected-access

        # Validate the XML string against the CIM-XML DTD
        try:
            validate_cim_xml(act_xml_str)
        except CIMXMLValidationError as exc:
            raise AssertionError(
                "DTD validation of CIM-XML failed:\n"
                "{0}\n"
                "CIM-XML string:\n"
                "{1}".
                format(exc, act_xml_str))

        # Verify that the XML string is as expected
        exp_xml_str = ''.join(iter_flattened(exp_xml_str_list))
        assert_xml_equal(act_xml_str, exp_xml_str)

    finally:
        if cdata_escaping:
            _cim_xml._CDATA_ESCAPING = False  # pylint: disable=protected-access
