"""
Unit tests for pywbem cim_xml.py module.
"""

from __future__ import absolute_import

try:
    from collections.abc import Iterable
except ImportError:  # py2
    from collections import Iterable
import unittest
import six
import pytest

from pywbem import cim_xml

from ..utils.validate import validate_cim_xml, CIMXMLValidationError
from ..utils.pytest_extensions import simplified_test_function


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


def sample_LOCALNAMESPACEPATH_node():
    """
    Return a sample LOCALNAMESPACEPATH as a cim_xml node.
    Must match the result of the corresponding ..._str() function.
    """
    return cim_xml.LOCALNAMESPACEPATH(
        [cim_xml.NAMESPACE('root'),
         cim_xml.NAMESPACE('cimv2')])


def sample_LOCALNAMESPACEPATH_str():
    """
    Return a sample LOCALNAMESPACEPATH as a list of XML strings.
    Must match the result of the corresponding ..._node() function.
    """
    return [
        '<LOCALNAMESPACEPATH>',
        '<NAMESPACE NAME="root"/>',
        '<NAMESPACE NAME="cimv2"/>',
        '</LOCALNAMESPACEPATH>',
    ]


def sample_NAMESPACEPATH_node():
    """
    Return a sample NAMESPACEPATH as a cim_xml node.
    Must match the result of the corresponding ..._str() function.
    """
    return cim_xml.NAMESPACEPATH(
        cim_xml.HOST('leonardo'),
        sample_LOCALNAMESPACEPATH_node())


def sample_NAMESPACEPATH_str():
    """
    Return a sample NAMESPACEPATH as a (nested) list of XML strings.
    Must match the result of the corresponding ..._node() function.
    """
    return [
        '<NAMESPACEPATH>',
        '<HOST>leonardo</HOST>',
        sample_LOCALNAMESPACEPATH_str(),
        '</NAMESPACEPATH>',
    ]


def sample_CLASSNAME_node():
    """
    Return a sample CLASSNAME as a cim_xml node.
    Must match the result of the corresponding ..._str() function.
    """
    return cim_xml.CLASSNAME('CIM_Foo')


def sample_CLASSNAME_str():
    """
    Return a sample CLASSNAME as a list of XML strings.
    Must match the result of the corresponding ..._node() function.
    """
    return [
        '<CLASSNAME NAME="CIM_Foo"/>',
    ]


def sample_LOCALCLASSPATH_node():
    """
    Return a sample LOCALCLASSPATH as a cim_xml node.
    Must match the result of the corresponding ..._str() function.
    """
    return cim_xml.LOCALCLASSPATH(
        sample_LOCALNAMESPACEPATH_node(),
        sample_CLASSNAME_node())


def sample_LOCALCLASSPATH_str():
    """
    Return a sample LOCALCLASSPATH as a (nested) list of XML strings.
    Must match the result of the corresponding ..._node() function.
    """
    return [
        '<LOCALCLASSPATH>',
        sample_LOCALNAMESPACEPATH_str(),
        sample_CLASSNAME_str(),
        '</LOCALCLASSPATH>',
    ]


def sample_CLASSPATH_node():
    """
    Return a sample CLASSPATH as a cim_xml node.
    Must match the result of the corresponding ..._str() function.
    """
    return cim_xml.CLASSPATH(
        sample_NAMESPACEPATH_node(),
        sample_CLASSNAME_node())


def sample_CLASSPATH_str():
    """
    Return a sample CLASSPATH as a (nested) list of XML strings.
    Must match the result of the corresponding ..._node() function.
    """
    return [
        '<CLASSPATH>',
        sample_NAMESPACEPATH_str(),
        sample_CLASSNAME_str(),
        '</CLASSPATH>',
    ]


def sample_INSTANCENAME_node():
    """
    Return a sample INSTANCENAME as a cim_xml node.
    Must match the result of the corresponding ..._str() function.
    """
    return cim_xml.INSTANCENAME(
        'CIM_Pet',
        [cim_xml.KEYBINDING(
            'type',
            cim_xml.KEYVALUE('dog', 'string')),
         cim_xml.KEYBINDING(
             'age',
             cim_xml.KEYVALUE('2', 'numeric'))])


def sample_INSTANCENAME_str():
    """
    Return a sample INSTANCENAME as a (nested) list of XML strings.
    Must match the result of the corresponding ..._node() function.
    """
    return [
        '<INSTANCENAME CLASSNAME="CIM_Pet">',
        '<KEYBINDING NAME="type">',
        '<KEYVALUE TYPE="string">dog</KEYVALUE>',
        '</KEYBINDING>',
        '<KEYBINDING NAME="age">',
        '<KEYVALUE TYPE="numeric">2</KEYVALUE>',
        '</KEYBINDING>',
        '</INSTANCENAME>',
    ]


def sample_LOCALINSTANCEPATH_node():
    """
    Return a sample LOCALINSTANCEPATH as a cim_xml node.
    Must match the result of the corresponding ..._str() function.
    """
    return cim_xml.LOCALINSTANCEPATH(
        sample_LOCALNAMESPACEPATH_node(),
        sample_INSTANCENAME_node())


def sample_LOCALINSTANCEPATH_str():
    """
    Return a sample LOCALINSTANCEPATH as a (nested) list of XML strings.
    Must match the result of the corresponding ..._node() function.
    """
    return [
        '<LOCALINSTANCEPATH>',
        sample_LOCALNAMESPACEPATH_str(),
        sample_INSTANCENAME_str(),
        '</LOCALINSTANCEPATH>',
    ]


TESTCASES_CIM_XML_NODE = [

    # Testcases for cim_xml nodes.

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * xml_node: cim_xml node to be tested (cim_xml.CIMElement subclass).
    #   * exp_xml_str_list: Expected XML string of the cim_xml node, as a
    #     (possibly nested) list of strings, or None.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # CIM top level element
    (
        "CIM: Simple request for EnumerateInstances",
        dict(
            xml_node=cim_xml.CIM(
                cim_xml.MESSAGE(
                    cim_xml.SIMPLEREQ(
                        cim_xml.IMETHODCALL(
                            'EnumerateInstances',
                            sample_LOCALNAMESPACEPATH_node(),
                            [
                                cim_xml.IPARAMVALUE(
                                    'ClassName',
                                    sample_CLASSNAME_node(),
                                ),
                            ],
                        ),
                    ),
                    '1001', '1.0'),
                '2.0', '2.0'),
            exp_xml_str_list=None,
        ),
        None, None, True
    ),
    (
        "CIM: Simple request for extrinsic method call (no parms)",
        dict(
            xml_node=cim_xml.CIM(
                cim_xml.MESSAGE(
                    cim_xml.SIMPLEREQ(
                        cim_xml.METHODCALL(
                            'MyMethod',
                            sample_LOCALINSTANCEPATH_node(),
                        ),
                    ),
                    '1001', '1.0'),
                '2.0', '2.0'),
            exp_xml_str_list=None,
        ),
        None, None, True
    ),

    (
        "VALUE.REFERENCE: Using sample CLASSPATH",
        dict(
            xml_node=cim_xml.VALUE_REFERENCE(
                sample_CLASSPATH_node(),
            ),
            exp_xml_str_list=[
                '<VALUE.REFERENCE>',
                sample_CLASSPATH_str(),
                '</VALUE.REFERENCE>',
            ],
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIM_XML_NODE)
@simplified_test_function
def test_cim_xml_node(testcase, xml_node, exp_xml_str_list):
    """
    Test function for a cim_xml node.

    A cim_xml node is an object of a subclass of cim_xml.CIMElement.

    The helper functions defined in class CIMElement are used only by the
    __init__() methods of its subclasses, so they are not tested separately.

    The __init__() method of the cim_xml node has already been executed during
    creation of the testcase list for this test function, so this test
    function checks the resulting cim_xml node object, as follows:

    * Create the XML string for the cim_xml node, using `toxml()`. That method
      is inherited from some base class of CIMElement and is not subject of
      the test.
    * Validate this XML string against the CIM-XML DTD.
    * Compare this XML string against the expected CIM-XML string, if one is
      defined.
    """

    act_xml_str = xml_node.toxml()

    try:
        validate_cim_xml(act_xml_str)
    except CIMXMLValidationError as exc:
        raise AssertionError(
            "DTD validation of CIM-XML failed:\n"
            "{0}\n"
            "CIM-XML string:\n"
            "{1}".
            format(exc, act_xml_str))

    if exp_xml_str_list is not None:

        # It is a (possibly nested) list of strings
        exp_xml_str = ''.join(iter_flattened(exp_xml_str_list))

        assert act_xml_str == exp_xml_str, \
            "Unexpected CIM-XML string:\n" \
            "  expected: {0!r}\n" \
            "  actual:   {1!r}". \
            format(exp_xml_str, act_xml_str)


###############################################################################
#
# TODO: Convert the following test classes to items in TESTCASES_CIM_XML_NODE
#

class CIMXMLTest(unittest.TestCase):
    """Run validate.py script against an xml document fragment."""

    def setUp(self):

        # List of test cases, each list item being an xml.dom.minidom node
        # representing some element from the CIM-XML payload.
        self.xml = []

        # List of expected XML strings resulting from each test case.
        self.xml_str = []

    @staticmethod
    def validate(xml, expectedResult=0):
        # pylint: disable=unused-argument
        """xml is a string with the CIM-XML."""

        try:
            validate_cim_xml(xml)
        except CIMXMLValidationError as exc:
            raise AssertionError(
                "DTD validation of CIM-XML failed:\n"
                "{0}\n"
                "CIM-XML string:\n"
                "{1}".
                format(exc, xml))

    def test_all(self):
        """Loop over xml to execute tests"""

        for i in range(0, len(self.xml)):

            xml_node = self.xml[i]
            act_xml_str = xml_node.toxml()

            # Test that the XML fragments pass validation against CIM-XML DTD
            self.validate(act_xml_str)

            if i < len(self.xml_str):
                # Test XML fragments for expected string representation
                exp_xml_str = self.xml_str[i]
                if exp_xml_str is not None:
                    self.assertEqual(act_xml_str, exp_xml_str,
                                     "CIM-XML fragment to be tested: %r" %
                                     act_xml_str)


# pylint: disable=too-few-public-methods
class UnimplementedTest(object):
    """Test unimplemented. Raise AssertionError"""

    @staticmethod
    def test_all():
        """raise Assertion Error"""
        raise AssertionError('Unimplemented test')


#################################################################
#     3.2.1. Top Level Elements
#################################################################

#     3.2.1.1. CIM

class CIM(CIMXMLTest):
    """CIM Top level element as class"""

    def setUp(self):
        """setUp for CIM class"""
        super(CIM, self).setUp()
        self.xml.append(cim_xml.CIM(
            cim_xml.MESSAGE(
                cim_xml.SIMPLEREQ(
                    cim_xml.IMETHODCALL(
                        'IntrinsicMethod',
                        sample_LOCALNAMESPACEPATH_node())),
                '1001', '1.0'),
            '2.0', '2.0'))


#################################################################
#     3.2.2. Declaration Elements
#################################################################

#     3.2.2.1. DECLARATION
#     3.2.2.2. DECLGROUP
#     3.2.2.3. DECLGROUP.WITHNAME
#     3.2.2.4. DECLGROUP.WITHPATH
#     3.2.2.5. QUALIFIER.DECLARATION
#     3.2.2.6. SCOPE


# pylint: disable=too-few-public-methods
class Declaration(UnimplementedTest):
    """
    <!ELEMENT DECLARATION  (DECLGROUP|DECLGROUP.WITHNAME|DECLGROUP.WITHPATH)+>
    """


# pylint: disable=too-few-public-methods
class DeclGroup(UnimplementedTest):
    """
    <!ELEMENT DECLGROUP  ((LOCALNAMESPACEPATH|NAMESPACEPATH)?,
                          QUALIFIER.DECLARATION*,VALUE.OBJECT*)>
    """
    pass


# pylint: disable=too-few-public-methods
class DeclGroupWithName(UnimplementedTest):
    """
    <!ELEMENT DECLGROUP.WITHNAME  ((LOCALNAMESPACEPATH|NAMESPACEPATH)?,
                                   QUALIFIER.DECLARATION*,VALUE.NAMEDOBJECT*)>
    """


# pylint: disable=too-few-public-methods
class DeclGroupWithPath(UnimplementedTest):
    """
    <!ELEMENT DECLGROUP.WITHPATH  (VALUE.OBJECTWITHPATH|
                                   VALUE.OBJECTWITHLOCALPATH)*>
    """


# pylint: disable=too-few-public-methods
class QualifierDeclaration(UnimplementedTest):
    """
    <!ELEMENT QUALIFIER.DECLARATION (SCOPE?, (VALUE | VALUE.ARRAY)?)>
    <!ATTLIST QUALIFIER.DECLARATION
        %CIMName;
        %CIMType;               #REQUIRED
        ISARRAY    (true|false) #IMPLIED
        %ArraySize;
        %QualifierFlavor;>
    """


class Scope(CIMXMLTest):
    """
    <!ELEMENT SCOPE EMPTY>
    <!ATTLIST SCOPE
         CLASS        (true|false)      'false'
         ASSOCIATION  (true|false)      'false'
         REFERENCE    (true|false)      'false'
         PROPERTY     (true|false)      'false'
         METHOD       (true|false)      'false'
         PARAMETER    (true|false)      'false'
         INDICATION   (true|false)      'false'>
    """

    def setUp(self):
        super(Scope, self).setUp()
        self.xml.append(cim_xml.SCOPE())


#################################################################
#     3.2.3. Value Elements
#################################################################

#     3.2.3.1. VALUE
#     3.2.3.2. VALUE.ARRAY
#     3.2.3.3. VALUE.REFERENCE
#     3.2.3.4. VALUE.REFARRAY
#     3.2.3.5. VALUE.OBJECT
#     3.2.3.6. VALUE.NAMEDINSTANCE
#     3.2.3.7. VALUE.NAMEDOBJECT
#     3.2.3.8. VALUE.OBJECTWITHPATH
#     3.2.3.9. VALUE.OBJECTWITHLOCALPATH
#     3.2.3.10. VALUE.NULL


class Value(CIMXMLTest):
    """
    <!ELEMENT VALUE (#PCDATA)>
    """

    def setUp(self):
        super(Value, self).setUp()

        # The VALUE element depends on whether XML-based or CDATA-based
        # escaping is used. Therefore, we modify the module-level switch that
        # controls that and run each test twice (wth different expected XML
        # strings).

        cim_xml._CDATA_ESCAPING = True  # pylint: disable=protected-access

        self.xml.append(cim_xml.VALUE('dog'))
        self.xml_str.append('<VALUE>dog</VALUE>')

        # self.xml.append(cim_xml.VALUE(None))
        # Note: This is illegal, Value.Null should be used instead.

        self.xml.append(cim_xml.VALUE(''))
        self.xml_str.append('<VALUE></VALUE>')  # Assum. not folded to <VALUE/>

        # Some control characters
        self.xml.append(cim_xml.VALUE('a\nb\rc\td'))
        self.xml_str.append('<VALUE>a\nb\rc\td</VALUE>')  # Assuming XML 1.1

        # Some XML special characters
        self.xml.append(cim_xml.VALUE('a&b<c>d'))
        self.xml_str.append('<VALUE><![CDATA[a&b<c>d]]></VALUE>')

        # Some XML special characters, already XML-escaped
        self.xml.append(cim_xml.VALUE('a&amp;b&lt;c&gt;d'))
        self.xml_str.append('<VALUE><![CDATA[a&amp;b&lt;c&gt;d]]></VALUE>')

        # Some XML special characters, already CDATA-escaped
        self.xml.append(cim_xml.VALUE('<![CDATA[a&b<c>d]]>'))
        self.xml_str.append(
            '<VALUE><![CDATA[<![CDATA[a&b<c>d]]]><![CDATA[]>]]></VALUE>')

        # set back to its default
        cim_xml._CDATA_ESCAPING = False  # pylint: disable=protected-access

        self.xml.append(cim_xml.VALUE('dog'))
        self.xml_str.append('<VALUE>dog</VALUE>')

        # self.xml.append(cim_xml.VALUE(None))
        # Note: This is illegal, Value.Null is used instead.

        self.xml.append(cim_xml.VALUE(''))
        self.xml_str.append('<VALUE></VALUE>')  # Assum. not folded to <VALUE/>

        # Some control characters
        self.xml.append(cim_xml.VALUE('a\nb\rc\td'))
        self.xml_str.append('<VALUE>a\nb\rc\td</VALUE>')  # Assuming XML 1.1

        # Some XML special characters
        self.xml.append(cim_xml.VALUE('a&b<c>d'))
        self.xml_str.append('<VALUE>a&amp;b&lt;c&gt;d</VALUE>')

        # Some XML special characters, already XML-escaped
        self.xml.append(cim_xml.VALUE('a&amp;b&lt;c&gt;d'))
        self.xml_str.append('<VALUE>a&amp;amp;b&amp;lt;c&amp;gt;d</VALUE>')

        # Some XML special characters, already CDATA-escaped
        self.xml.append(cim_xml.VALUE('<![CDATA[a&b<c>d]]>'))
        self.xml_str.append(
            '<VALUE>&lt;![CDATA[a&amp;b&lt;c&gt;d]]&gt;</VALUE>')


class ValueArray(CIMXMLTest):
    """
    <!ELEMENT VALUE.ARRAY (VALUE*)>
    """

    def setUp(self):
        super(ValueArray, self).setUp()

        self.xml.append(cim_xml.VALUE_ARRAY([]))

        self.xml.append(cim_xml.VALUE_ARRAY([cim_xml.VALUE('cat'),
                                             cim_xml.VALUE('dog')]))


class ValueReference(CIMXMLTest):
    """
    <!ELEMENT VALUE.REFERENCE (CLASSPATH|LOCALCLASSPATH|CLASSNAME|
                               INSTANCEPATH|LOCALINSTANCEPATH|INSTANCENAME)>
    """

    def setUp(self):
        super(ValueReference, self).setUp()

        # CLASSPATH

        self.xml.append(cim_xml.VALUE_REFERENCE(sample_CLASSPATH_node()))

        # LOCALCLASSPATH

        self.xml.append(cim_xml.VALUE_REFERENCE(
            cim_xml.LOCALCLASSPATH(
                sample_LOCALNAMESPACEPATH_node(),
                sample_CLASSNAME_node())))

        # CLASSNAME

        self.xml.append(cim_xml.VALUE_REFERENCE(sample_CLASSNAME_node()))

        # INSTANCEPATH

        self.xml.append(cim_xml.VALUE_REFERENCE(
            cim_xml.INSTANCEPATH(
                sample_NAMESPACEPATH_node(), sample_INSTANCENAME_node())))

        # LOCALINSTANCEPATH

        self.xml.append(cim_xml.VALUE_REFERENCE(
            cim_xml.LOCALINSTANCEPATH(
                sample_LOCALNAMESPACEPATH_node(), sample_INSTANCENAME_node())))

        # INSTANCENAME

        self.xml.append(cim_xml.VALUE_REFERENCE(sample_INSTANCENAME_node()))


class ValueRefArray(CIMXMLTest):
    """
    <!ELEMENT VALUE.REFARRAY (VALUE.REFERENCE*)>
    """

    def setUp(self):
        super(ValueRefArray, self).setUp()

        # Empty

        self.xml.append(cim_xml.VALUE_REFARRAY([]))

        # VALUE.REFARRAY

        self.xml.append(cim_xml.VALUE_REFARRAY(
            [cim_xml.VALUE_REFERENCE(cim_xml.CLASSNAME('CIM_Foo')),
             cim_xml.VALUE_REFERENCE(cim_xml.LOCALCLASSPATH(
                 sample_LOCALNAMESPACEPATH_node(), sample_CLASSNAME_node()))]))


class ValueObject(CIMXMLTest):
    """
    <!ELEMENT VALUE.OBJECT (CLASS|INSTANCE)>
    """

    def setUp(self):
        super(ValueObject, self).setUp()

        # CLASS

        self.xml.append(cim_xml.VALUE_OBJECT(cim_xml.CLASS('CIM_Foo')))

        # INSTANCE

        self.xml.append(cim_xml.VALUE_OBJECT(cim_xml.INSTANCE('CIM_Pet', [])))


class ValueNamedInstance(CIMXMLTest):
    """
    <!ELEMENT VALUE.NAMEDINSTANCE (INSTANCENAME,INSTANCE)>
    """

    def setUp(self):
        super(ValueNamedInstance, self).setUp()

        self.xml.append(cim_xml.VALUE_NAMEDINSTANCE(
            sample_INSTANCENAME_node(),
            cim_xml.INSTANCE('CIM_Pet', [])))


class ValueNamedObject(CIMXMLTest):
    """
    <!ELEMENT VALUE.NAMEDOBJECT (CLASS|(INSTANCENAME,INSTANCE))>
    """

    def setUp(self):
        super(ValueNamedObject, self).setUp()

        # CLASS

        self.xml.append(cim_xml.VALUE_NAMEDOBJECT(
            cim_xml.CLASS('CIM_Foo')))

        # INSTANCENAME, INSTANCE

        self.xml.append(cim_xml.VALUE_NAMEDOBJECT(
            (sample_INSTANCENAME_node(),
             cim_xml.INSTANCE('CIM_Pet', []))))


class ValueObjectWithPath(CIMXMLTest):
    """
    <!ELEMENT VALUE.OBJECTWITHPATH ((CLASSPATH,CLASS)|
                                    (INSTANCEPATH,INSTANCE))>
    """

    def setUp(self):
        super(ValueObjectWithPath, self).setUp()

        # (CLASSPATH, CLASS)

        self.xml.append(cim_xml.VALUE_OBJECTWITHPATH(
            sample_CLASSPATH_node(),
            cim_xml.CLASS('CIM_Foo')))

        # (INSTANCEPATH, INSTANCE)

        self.xml.append(cim_xml.VALUE_OBJECTWITHPATH(
            cim_xml.INSTANCEPATH(
                sample_NAMESPACEPATH_node(), sample_INSTANCENAME_node()),
            cim_xml.INSTANCE('CIM_Pet', [])))


class ValueObjectWithLocalPath(CIMXMLTest):
    """
    <!ELEMENT VALUE.OBJECTWITHLOCALPATH ((LOCALCLASSPATH,CLASS)|
                                         (LOCALINSTANCEPATH,INSTANCE))>
    """

    def setUp(self):
        super(ValueObjectWithLocalPath, self).setUp()

        # (LOCALCLASSPATH, CLASS)

        self.xml.append(cim_xml.VALUE_OBJECTWITHLOCALPATH(
            cim_xml.LOCALCLASSPATH(
                sample_LOCALNAMESPACEPATH_node(),
                sample_CLASSNAME_node()),
            cim_xml.CLASS('CIM_Foo')))

        # (LOCALINSTANCEPATH, INSTANCE)

        self.xml.append(cim_xml.VALUE_OBJECTWITHLOCALPATH(
            cim_xml.LOCALINSTANCEPATH(
                sample_LOCALNAMESPACEPATH_node(),
                sample_INSTANCENAME_node()),
            cim_xml.INSTANCE('CIM_Pet', [])))


# pylint: disable=too-few-public-methods
class ValueNull(UnimplementedTest):
    """
    <!ELEMENT VALUE.NULL EMPTY>
    """
    # TODO: Implement ValueNull test


class ValueInstanceWithPath(CIMXMLTest):
    """
    <!ELEMENT VALUE.INSTANCEWITHPATH (INSTANCEPATH,INSTANCE)>
    """

    def setUp(self):
        super(ValueInstanceWithPath, self).setUp()

        self.xml.append(cim_xml.VALUE_INSTANCEWITHPATH(
            cim_xml.INSTANCEPATH(
                sample_NAMESPACEPATH_node(), sample_INSTANCENAME_node()),
            cim_xml.INSTANCE('CIM_Pet', [])))


#################################################################
#     3.2.4. Naming and Location Elements
#################################################################

#     3.2.4.1. NAMESPACEPATH
#     3.2.4.2. LOCALNAMESPACEPATH
#     3.2.4.3. HOST
#     3.2.4.4. NAMESPACE
#     3.2.4.5. CLASSPATH
#     3.2.4.6. LOCALCLASSPATH
#     3.2.4.7. CLASSNAME
#     3.2.4.8. INSTANCEPATH
#     3.2.4.9. LOCALINSTANCEPATH
#     3.2.4.10. INSTANCENAME
#     3.2.4.11. OBJECTPATH
#     3.2.4.12. KEYBINDING
#     3.2.4.13. KEYVALUE


class NamespacePath(CIMXMLTest):
    """
    <!ELEMENT NAMESPACEPATH (HOST,LOCALNAMESPACEPATH)>
    """

    def setUp(self):
        super(NamespacePath, self).setUp()

        self.xml.append(sample_NAMESPACEPATH_node())


class LocalNamespacePath(CIMXMLTest):
    """
    <!ELEMENT LOCALNAMESPACEPATH (NAMESPACE+)>
    """

    def setUp(self):
        super(LocalNamespacePath, self).setUp()

        self.xml.append(sample_LOCALNAMESPACEPATH_node())


class Host(CIMXMLTest):
    """
    <!ELEMENT HOST (#PCDATA)>
    """

    def setUp(self):
        super(Host, self).setUp()

        self.xml.append(cim_xml.HOST('leonardo'))


class Namespace(CIMXMLTest):
    """
    <!ELEMENT NAMESPACE EMPTY>
    <!ATTLIST NAMESPACE
        %CIMName;>
    """

    def setUp(self):
        super(Namespace, self).setUp()

        self.xml.append(cim_xml.NAMESPACE('root'))


class ClassPath(CIMXMLTest):
    """
    <!ELEMENT CLASSPATH (NAMESPACEPATH,CLASSNAME)>
    """

    def setUp(self):
        super(ClassPath, self).setUp()

        self.xml.append(sample_CLASSPATH_node())


class LocalClassPath(CIMXMLTest):
    """
    <!ELEMENT LOCALCLASSPATH (LOCALNAMESPACEPATH, CLASSNAME)>
    """

    def setUp(self):
        super(LocalClassPath, self).setUp()

        self.xml.append(cim_xml.LOCALCLASSPATH(
            sample_LOCALNAMESPACEPATH_node(), sample_CLASSNAME_node()))


class ClassName(CIMXMLTest):
    """
    <!ELEMENT CLASSNAME EMPTY>
    <!ATTLIST CLASSNAME
        %CIMName;>
    """

    def setUp(self):
        super(ClassName, self).setUp()

        self.xml.append(sample_CLASSNAME_node())


class InstancePath(CIMXMLTest):
    """
    <!ELEMENT INSTANCEPATH (NAMESPACEPATH,INSTANCENAME)>
    """

    def setUp(self):
        super(InstancePath, self).setUp()

        self.xml.append(cim_xml.INSTANCEPATH(
            sample_NAMESPACEPATH_node(), sample_INSTANCENAME_node()))


class LocalInstancePath(CIMXMLTest):
    """
    <!ELEMENT LOCALINSTANCEPATH (LOCALNAMESPACEPATH,INSTANCENAME)>
    """

    def setUp(self):
        super(LocalInstancePath, self).setUp()

        self.xml.append(cim_xml.LOCALINSTANCEPATH(
            sample_LOCALNAMESPACEPATH_node(), sample_INSTANCENAME_node()))


class InstanceName(CIMXMLTest):
    """
    <!ELEMENT INSTANCENAME (KEYBINDING*|KEYVALUE?|VALUE.REFERENCE?)>
    <!ATTLIST INSTANCENAME
        %ClassName;>
    """

    def setUp(self):
        super(InstanceName, self).setUp()

        # Empty

        self.xml.append(cim_xml.INSTANCENAME('CIM_Pet', None))

        # KEYBINDING

        self.xml.append(sample_INSTANCENAME_node())

        # KEYVALUE

        self.xml.append(cim_xml.INSTANCENAME(
            'CIM_Pet', cim_xml.KEYVALUE('FALSE', 'boolean')))

        # VALUE.REFERENCE

        self.xml.append(cim_xml.INSTANCENAME(
            'CIM_Pet',
            cim_xml.VALUE_REFERENCE(sample_INSTANCENAME_node())))


class ObjectPath(CIMXMLTest):
    """
    <!ELEMENT OBJECTPATH (INSTANCEPATH|CLASSPATH)>
    """

    def setUp(self):
        super(ObjectPath, self).setUp()

        self.xml.append(cim_xml.OBJECTPATH(
            cim_xml.INSTANCEPATH(
                sample_NAMESPACEPATH_node(),
                sample_INSTANCENAME_node())))

        self.xml.append(cim_xml.OBJECTPATH(
            sample_CLASSPATH_node()))


class KeyBinding(CIMXMLTest):
    """
    <!ELEMENT KEYBINDING (KEYVALUE|VALUE.REFERENCE)>
    <!ATTLIST KEYBINDING
        %CIMName;>
    """

    def setUp(self):
        super(KeyBinding, self).setUp()

        self.xml.append(cim_xml.KEYBINDING(
            'pet', cim_xml.KEYVALUE('dog', 'string')))

        self.xml.append(cim_xml.KEYBINDING(
            'CIM_Foo',
            cim_xml.VALUE_REFERENCE(sample_CLASSPATH_node())))


class KeyValue(CIMXMLTest):
    """
    <!ELEMENT KEYVALUE (#PCDATA)>
    <!ATTLIST KEYVALUE
        VALUETYPE    (string|boolean|numeric)  'string'
        %CIMType;    #IMPLIED>
    """

    def setUp(self):
        super(KeyValue, self).setUp()

        self.xml.append(cim_xml.KEYVALUE('dog', 'string'))
        self.xml.append(cim_xml.KEYVALUE('2', 'numeric'))
        self.xml.append(cim_xml.KEYVALUE('FALSE', 'boolean'))
        self.xml.append(cim_xml.KEYVALUE('2', 'numeric', 'uint16'))
        self.xml.append(cim_xml.KEYVALUE(None))


#################################################################
#     3.2.5. Object Definition Elements
#################################################################

#     3.2.5.1. CLASS
#     3.2.5.2. INSTANCE
#     3.2.5.3. QUALIFIER
#     3.2.5.4. PROPERTY
#     3.2.5.5. PROPERTY.ARRAY
#     3.2.5.6. PROPERTY.REFERENCE
#     3.2.5.7. METHOD
#     3.2.5.8. PARAMETER
#     3.2.5.9. PARAMETER.REFERENCE
#     3.2.5.10. PARAMETER.ARRAY
#     3.2.5.11. PARAMETER.REFARRAY


class Class(CIMXMLTest):
    """
    <!ELEMENT CLASS (QUALIFIER*,(PROPERTY|PROPERTY.ARRAY|PROPERTY.REFERENCE)*,
                     METHOD*)>
    <!ATTLIST CLASS
        %CIMName;
        %SuperClass;>
    """

    def setUp(self):
        super(Class, self).setUp()

        # Empty

        self.xml.append(cim_xml.CLASS('CIM_Foo'))

        # PROPERTY

        self.xml.append(cim_xml.CLASS(
            'CIM_Foo',
            properties=[cim_xml.PROPERTY('Dog', 'string',
                                         cim_xml.VALUE('Spotty'))]))

        # QUALIFIER + PROPERTY

        self.xml.append(cim_xml.CLASS(
            'CIM_Foo',
            properties=[cim_xml.PROPERTY('Dog', 'string',
                                         cim_xml.VALUE('Spotty'))],
            qualifiers=[cim_xml.QUALIFIER('IMPISH', 'string',
                                          cim_xml.VALUE('true'))]))

        # PROPERTY.ARRAY

        self.xml.append(cim_xml.CLASS(
            'CIM_Foo',
            properties=[cim_xml.PROPERTY_ARRAY('Dogs', 'string', None)]))

        # PROPERTY.REFERENCE

        self.xml.append(cim_xml.CLASS(
            'CIM_Foo',
            properties=[cim_xml.PROPERTY_REFERENCE('Dogs', None)]))

        # METHOD

        self.xml.append(cim_xml.CLASS(
            'CIM_Foo',
            methods=[cim_xml.METHOD('FooMethod')]))


class Instance(CIMXMLTest):
    """
    <!ELEMENT INSTANCE (QUALIFIER*,(PROPERTY|PROPERTY.ARRAY|
                                    PROPERTY.REFERENCE)*)>
    <!ATTLIST INSTANCE
         %ClassName;
         xml:lang   NMTOKEN  #IMPLIED>
    """

    def setUp(self):
        super(Instance, self).setUp()

        # Empty

        self.xml.append(cim_xml.INSTANCE('CIM_Foo', []))

        # PROPERTY

        self.xml.append(cim_xml.INSTANCE(
            'CIM_Foo',
            [cim_xml.PROPERTY('Dog', 'string', cim_xml.VALUE('Spotty')),
             cim_xml.PROPERTY('Cat', 'string', cim_xml.VALUE('Bella'))]))

        # PROPERTY + QUALIFIER

        self.xml.append(cim_xml.INSTANCE(
            'CIM_Foo',
            properties=[cim_xml.PROPERTY('Dog', 'string',
                                         cim_xml.VALUE('Spotty')),
                        cim_xml.PROPERTY('Cat', 'string',
                                         cim_xml.VALUE('Bella'))],
            qualifiers=[cim_xml.QUALIFIER('IMPISH', 'string',
                                          cim_xml.VALUE('true'))]))

        # PROPERTY.ARRAY

        self.xml.append(cim_xml.INSTANCE(
            'CIM_Pets',
            [cim_xml.PROPERTY_ARRAY(
                'Dogs',
                'string',
                cim_xml.VALUE_ARRAY([cim_xml.VALUE('Spotty'),
                                     cim_xml.VALUE('Bronte')])),
             cim_xml.PROPERTY_ARRAY(
                 'Cats',
                 'string',
                 cim_xml.VALUE_ARRAY([cim_xml.VALUE('Bella'),
                                      cim_xml.VALUE('Faux Lily')]))]))

        # PROPERTY.REFERENCE

        self.xml.append(cim_xml.INSTANCE(
            'CIM_Pets',
            [cim_xml.PROPERTY_REFERENCE(
                'Dog',
                cim_xml.VALUE_REFERENCE(cim_xml.CLASSNAME('CIM_Dog'))),
             cim_xml.PROPERTY_REFERENCE(
                 'Cat',
                 cim_xml.VALUE_REFERENCE(cim_xml.CLASSNAME('CIM_Cat')))]))


class Qualifier(CIMXMLTest):
    """
    <!ELEMENT QUALIFIER (VALUE | VALUE.ARRAY)>
    <!ATTLIST QUALIFIER
        %CIMName;
        %CIMType;              #REQUIRED
        %Propagated;
        %QualifierFlavor;
        xml:lang   NMTOKEN  #IMPLIED>
    """

    def setUp(self):
        super(Qualifier, self).setUp()

        # Note: DTD 2.2 allows qualifier to be empty

        # VALUE

        self.xml.append(cim_xml.QUALIFIER(
            'IMPISH', 'string', cim_xml.VALUE('true')))

        # VALUE + attributes

        self.xml.append(cim_xml.QUALIFIER(
            'Key', 'string', cim_xml.VALUE('true'),
            overridable='true'))

        self.xml.append(cim_xml.QUALIFIER(
            'Description', 'string', cim_xml.VALUE('blahblah'),
            translatable='true'))

        self.xml.append(cim_xml.QUALIFIER(
            'Version', 'string', cim_xml.VALUE('foorble'),
            tosubclass='false', translatable='true'))

        # VALUE.ARRAY

        self.xml.append(cim_xml.QUALIFIER(
            'LUCKYNUMBERS', 'uint32',
            cim_xml.VALUE_ARRAY([cim_xml.VALUE('1'), cim_xml.VALUE('2')])))


class Property(CIMXMLTest):
    """
    <!ELEMENT PROPERTY (QUALIFIER*,VALUE?)>
    <!ATTLIST PROPERTY
        %CIMName;
        %CIMType;           #REQUIRED
        %ClassOrigin;
        %Propagated;
        xml:lang   NMTOKEN  #IMPLIED>
    """

    def setUp(self):
        super(Property, self).setUp()

        # Empty

        self.xml.append(cim_xml.PROPERTY('PropertyName', 'string', None))

        # PROPERTY

        self.xml.append(cim_xml.PROPERTY(
            'PropertyName',
            'string',
            cim_xml.VALUE('dog')))

        # PROPERTY + attributes

        self.xml.append(cim_xml.PROPERTY(
            'PropertyName',
            'string',
            cim_xml.VALUE('dog'),
            propagated='true', class_origin='CIM_Pets'))

        # PROPERTY + QUALIFIER

        self.xml.append(cim_xml.PROPERTY(
            'PropertyName',
            'string',
            cim_xml.VALUE('dog'),
            qualifiers=[cim_xml.QUALIFIER('IMPISH', 'string',
                                          cim_xml.VALUE('true'))]))


class PropertyArray(CIMXMLTest):
    """
    <!ELEMENT PROPERTY.ARRAY (QUALIFIER*,VALUE.ARRAY?)>
    <!ATTLIST PROPERTY.ARRAY
       %CIMName;
       %CIMType;           #REQUIRED
       %ArraySize;
       %ClassOrigin;
       %Propagated;
       xml:lang   NMTOKEN  #IMPLIED>

    """

    def setUp(self):
        super(PropertyArray, self).setUp()

        # Empty

        self.xml.append(cim_xml.PROPERTY_ARRAY('Dogs', 'string'))

        # VALUE.ARRAY

        self.xml.append(cim_xml.PROPERTY_ARRAY(
            'Dogs',
            'string',
            cim_xml.VALUE_ARRAY([cim_xml.VALUE('Spotty'),
                                 cim_xml.VALUE('Bronte')])))

        # VALUE.ARRAY + attributes

        self.xml.append(cim_xml.PROPERTY_ARRAY(
            'Dogs',
            'string',
            cim_xml.VALUE_ARRAY([cim_xml.VALUE('Spotty'),
                                 cim_xml.VALUE('Bronte')]),
            array_size='2', class_origin='CIM_Dog'))

        self.xml.append(cim_xml.PROPERTY_ARRAY('Dogs', 'string', None))

        # QUALIFIER + VALUE.ARRAY

        self.xml.append(cim_xml.PROPERTY_ARRAY(
            'Dogs',
            'string',
            cim_xml.VALUE_ARRAY([cim_xml.VALUE('Spotty'),
                                 cim_xml.VALUE('Bronte')]),
            qualifiers=[cim_xml.QUALIFIER('IMPISH', 'string',
                                          cim_xml.VALUE('true'))]))


class PropertyReference(CIMXMLTest):
    """
    <!ELEMENT PROPERTY.REFERENCE (QUALIFIER*,VALUE.REFERENCE?)>
    <!ATTLIST PROPERTY.REFERENCE
        %CIMName;
        %ReferenceClass;
        %ClassOrigin;
        %Propagated;>
    """

    def setUp(self):
        super(PropertyReference, self).setUp()

        # Empty

        self.xml.append(cim_xml.PROPERTY_REFERENCE('Dogs', None))

        # VALUE.REFERENCE

        self.xml.append(cim_xml.PROPERTY_REFERENCE(
            'Dogs',
            cim_xml.VALUE_REFERENCE(cim_xml.CLASSNAME('CIM_Dog'))))

        # VALUE.REFERENCE + attributes

        self.xml.append(cim_xml.PROPERTY_REFERENCE(
            'Dogs',
            cim_xml.VALUE_REFERENCE(cim_xml.CLASSNAME('CIM_Dog')),
            reference_class='CIM_Dog', class_origin='CIM_Dog',
            propagated='true'))

        # QUALIFIER + VALUE.REFERENCE

        self.xml.append(cim_xml.PROPERTY_REFERENCE(
            'Dogs',
            cim_xml.VALUE_REFERENCE(cim_xml.CLASSNAME('CIM_Dog')),
            qualifiers=[cim_xml.QUALIFIER('IMPISH', 'string',
                                          cim_xml.VALUE('true'))]))


class Method(CIMXMLTest):
    """
    <!ELEMENT METHOD (QUALIFIER*,(PARAMETER|PARAMETER.REFERENCE|
                                  PARAMETER.ARRAY|PARAMETER.REFARRAY)*)>
    <!ATTLIST METHOD
        %CIMName;
        %CIMType;          #IMPLIED
        %ClassOrigin;
        %Propagated;>
    """

    def setUp(self):
        super(Method, self).setUp()

        # Empty

        self.xml.append(cim_xml.METHOD('FooMethod'))

        # PARAMETER

        self.xml.append(cim_xml.METHOD(
            'FooMethod',
            [cim_xml.PARAMETER('arg', 'string')]))

        # PARAMETER.REFERENCE

        self.xml.append(cim_xml.METHOD(
            'FooMethod',
            [cim_xml.PARAMETER_REFERENCE('arg', 'CIM_Foo')]))

        # PARAMETER.ARRAY

        self.xml.append(cim_xml.METHOD(
            'FooMethod',
            [cim_xml.PARAMETER_ARRAY('arg', 'string')]))

        # PARAMETER.REFARRAY

        self.xml.append(cim_xml.METHOD(
            'FooMethod',
            [cim_xml.PARAMETER_REFARRAY('arg', 'CIM_Foo')]))

        # PARAMETER + attributes

        self.xml.append(cim_xml.METHOD(
            'FooMethod',
            [cim_xml.PARAMETER('arg', 'string')],
            return_type='uint32',
            class_origin='CIM_Foo',
            propagated='true'))

        # QUALIFIER + PARAMETER

        self.xml.append(cim_xml.METHOD(
            'FooMethod',
            [cim_xml.PARAMETER('arg', 'string')],
            qualifiers=[cim_xml.QUALIFIER('IMPISH', 'string',
                                          cim_xml.VALUE('true'))]))


class Parameter(CIMXMLTest):
    """
    <!ELEMENT PARAMETER (QUALIFIER*)>
    <!ATTLIST PARAMETER
        %CIMName;
        %CIMType;      #REQUIRED>
    """

    def setUp(self):
        super(Parameter, self).setUp()

        # Empty

        self.xml.append(cim_xml.PARAMETER('arg', 'string'))

        # QUALIFIER

        self.xml.append(cim_xml.PARAMETER(
            'arg',
            'string',
            qualifiers=[cim_xml.QUALIFIER('IMPISH', 'string',
                                          cim_xml.VALUE('true'))]))


class ParameterReference(CIMXMLTest):
    """
    <!ELEMENT PARAMETER.REFERENCE (QUALIFIER*)>
    <!ATTLIST PARAMETER.REFERENCE
        %CIMName;
        %ReferenceClass;>
    """

    def setUp(self):
        super(ParameterReference, self).setUp()

        # Empty

        self.xml.append(cim_xml.PARAMETER_REFERENCE('arg'))

        # QUALIFIER + attributes

        self.xml.append(cim_xml.PARAMETER_REFERENCE(
            'arg',
            reference_class='CIM_Foo',
            qualifiers=[cim_xml.QUALIFIER('IMPISH', 'string',
                                          cim_xml.VALUE('true'))]))


class ParameterArray(CIMXMLTest):
    """
    <!ELEMENT PARAMETER.ARRAY (QUALIFIER*)>
    <!ATTLIST PARAMETER.ARRAY
        %CIMName;
        %CIMType;           #REQUIRED
        %ArraySize;>
    """

    def setUp(self):
        super(ParameterArray, self).setUp()

        # Empty

        self.xml.append(cim_xml.PARAMETER_ARRAY('arg', 'string'))

        # QUALIFIERS + attributes

        self.xml.append(cim_xml.PARAMETER_ARRAY(
            'arg',
            'string',
            array_size='0',
            qualifiers=[cim_xml.QUALIFIER('IMPISH', 'string',
                                          cim_xml.VALUE('true'))]))


class ParameterReferenceArray(CIMXMLTest):
    """
    <!ELEMENT PARAMETER.REFARRAY (QUALIFIER*)>
    <!ATTLIST PARAMETER.REFARRAY
        %CIMName;
        %ReferenceClass;
        %ArraySize;>
    """

    def setUp(self):
        super(ParameterReferenceArray, self).setUp()

        # Empty

        self.xml.append(cim_xml.PARAMETER_REFARRAY('arg'))

        # QUALIFIERS + attributes

        self.xml.append(cim_xml.PARAMETER_REFARRAY(
            'arg',
            reference_class='CIM_Foo',
            array_size='0',
            qualifiers=[cim_xml.QUALIFIER('IMPISH', 'string',
                                          cim_xml.VALUE('true'))]))


#################################################################
#     3.2.6. Message Elements
#################################################################

#     3.2.6.1. MESSAGE
#     3.2.6.2. MULTIREQ
#     3.2.6.3. SIMPLEREQ
#     3.2.6.4. METHODCALL
#     3.2.6.5. PARAMVALUE
#     3.2.6.6. IMETHODCALL
#     3.2.6.7. IPARAMVALUE
#     3.2.6.8. MULTIRSP
#     3.2.6.9. SIMPLERSP
#     3.2.6.10. METHODRESPONSE
#     3.2.6.11. IMETHODRESPONSE
#     3.2.6.12. ERROR
#     3.2.6.13. RETURNVALUE
#     3.2.6.14. IRETURNVALUE
#     3.2.6.15 MULTIEXPREQ
#     3.2.6.16 SIMPLEEXPREQ
#     3.2.6.17 EXPMETHODCALL
#     3.2.6.18 MULTIEXPRSP
#     3.2.6.19 SIMPLEEXPRSP
#     3.2.6.20 EXPMETHODRESPONSE
#     3.2.6.21 EXPPARAMVALUE


class Message(CIMXMLTest):
    """
    <!ELEMENT MESSAGE (SIMPLEREQ | MULTIREQ | SIMPLERSP | MULTIRSP |
                       SIMPLEEXPREQ | MULTIEXPREQ | SIMPLEEXPRSP |
                       MULTIEXPRSP)>
    <!ATTLIST MESSAGE
        ID CDATA #REQUIRED
        PROTOCOLVERSION CDATA #REQUIRED>
    """

    def setUp(self):
        super(Message, self).setUp()

        # SIMPLEREQ

        self.xml.append(cim_xml.MESSAGE(
            cim_xml.SIMPLEREQ(
                cim_xml.IMETHODCALL(
                    'FooMethod',
                    sample_LOCALNAMESPACEPATH_node())),
            '1001', '1.0'))

        # MULTIREQ

        self.xml.append(cim_xml.MESSAGE(
            cim_xml.MULTIREQ(
                [cim_xml.SIMPLEREQ(
                    cim_xml.IMETHODCALL(
                        'FooMethod',
                        sample_LOCALNAMESPACEPATH_node())),
                 cim_xml.SIMPLEREQ(
                     cim_xml.IMETHODCALL(
                         'FooMethod',
                         sample_LOCALNAMESPACEPATH_node()))]),
            '1001', '1.0'))

        # SIMPLERSP

        self.xml.append(cim_xml.MESSAGE(
            cim_xml.SIMPLERSP(
                cim_xml.IMETHODRESPONSE('FooMethod')),
            '1001', '1.0'))

        # MULTIRSP

        self.xml.append(cim_xml.MESSAGE(
            cim_xml.MULTIRSP(
                [cim_xml.SIMPLERSP(cim_xml.IMETHODRESPONSE('FooMethod')),
                 cim_xml.SIMPLERSP(cim_xml.IMETHODRESPONSE('FooMethod'))]),
            '1001', '1.0'))

        # TODO:

        # SIMPLEEXPREQ
        # MULTIEXPREQ
        # SIMPLEEXPRSP
        # MULTIEXPRSP


class MultiReq(CIMXMLTest):
    """
    <!ELEMENT MULTIREQ (SIMPLEREQ, SIMPLEREQ+)>
    """

    def setUp(self):
        super(MultiReq, self).setUp()

        self.xml.append(cim_xml.MULTIREQ(
            [cim_xml.SIMPLEREQ(
                cim_xml.IMETHODCALL(
                    'FooMethod',
                    sample_LOCALNAMESPACEPATH_node())),
             cim_xml.SIMPLEREQ(
                 cim_xml.IMETHODCALL(
                     'FooMethod',
                     sample_LOCALNAMESPACEPATH_node()))]))


class MultiExpReq(CIMXMLTest):
    """
    <!ELEMENT MULTIEXPREQ (SIMPLEEXPREQ, SIMPLEEXPREQ+)>
    """

    def setUp(self):
        super(MultiExpReq, self).setUp()

        self.xml.append(cim_xml.MULTIEXPREQ(
            [cim_xml.SIMPLEEXPREQ(cim_xml.EXPMETHODCALL('FooMethod')),
             cim_xml.SIMPLEEXPREQ(cim_xml.EXPMETHODCALL('FooMethod'))]))


class SimpleReq(CIMXMLTest):
    """
    <!ELEMENT SIMPLEREQ (IMETHODCALL | METHODCALL)>
    """

    def setUp(self):
        super(SimpleReq, self).setUp()

        # IMETHODCALL

        self.xml.append(cim_xml.SIMPLEREQ(
            cim_xml.IMETHODCALL(
                'FooIMethod',
                sample_LOCALNAMESPACEPATH_node())))

        # METHODCALL

        self.xml.append(cim_xml.SIMPLEREQ(
            cim_xml.METHODCALL(
                'FooMethod',
                cim_xml.LOCALCLASSPATH(
                    sample_LOCALNAMESPACEPATH_node(),
                    sample_CLASSNAME_node()))))


class SimpleExpReq(CIMXMLTest):
    """
    <!ELEMENT SIMPLEEXPREQ (EXPMETHODCALL)>
    """

    def setUp(self):
        super(SimpleExpReq, self).setUp()

        self.xml.append(cim_xml.SIMPLEEXPREQ(
            cim_xml.EXPMETHODCALL('FooMethod')))


class IMethodCall(CIMXMLTest):
    """
    <!ELEMENT IMETHODCALL (LOCALNAMESPACEPATH, IPARAMVALUE*)>
    <!ATTLIST IMETHODCALL
        %CIMName;>
    """

    def setUp(self):
        super(IMethodCall, self).setUp()

        self.xml.append(
            cim_xml.IMETHODCALL('FooMethod', sample_LOCALNAMESPACEPATH_node()))

        self.xml.append(cim_xml.IMETHODCALL(
            'FooMethod2', sample_LOCALNAMESPACEPATH_node(),
            [cim_xml.IPARAMVALUE('Dog', cim_xml.VALUE('Spottyfoot'))]))


class MethodCall(CIMXMLTest):
    """
    <!ELEMENT METHODCALL ((LOCALINSTANCEPATH | LOCALCLASSPATH), PARAMVALUE*)>
    <!ATTLIST METHODCALL
        %CIMName;>
    """

    def setUp(self):
        super(MethodCall, self).setUp()

        # LOCALINSTANCEPATH

        self.xml.append(cim_xml.METHODCALL(
            'FooMethod',
            cim_xml.LOCALINSTANCEPATH(
                sample_LOCALNAMESPACEPATH_node(),
                sample_INSTANCENAME_node())))

        # LOCALCLASSPATH

        self.xml.append(cim_xml.METHODCALL(
            'FooMethod',
            cim_xml.LOCALCLASSPATH(
                sample_LOCALNAMESPACEPATH_node(),
                sample_CLASSNAME_node())))

        # PARAMVALUEs

        self.xml.append(cim_xml.METHODCALL(
            'FooMethod',
            cim_xml.LOCALINSTANCEPATH(
                sample_LOCALNAMESPACEPATH_node(),
                sample_INSTANCENAME_node()),
            [cim_xml.PARAMVALUE('Dog', cim_xml.VALUE('Spottyfoot'))]))


class ExpMethodCall(CIMXMLTest):
    """
    <!ELEMENT EXPMETHODCALL (EXPPARAMVALUE*)>
    <!ATTLIST EXPMETHODCALL
        %CIMName;>
    """

    def setUp(self):
        super(ExpMethodCall, self).setUp()

        self.xml.append(cim_xml.EXPMETHODCALL('FooMethod'))

        self.xml.append(cim_xml.EXPMETHODCALL(
            'FooMethod',
            [cim_xml.EXPPARAMVALUE('Dog')]))


class ParamValue(CIMXMLTest):
    """
    <!ELEMENT PARAMVALUE (VALUE | VALUE.REFERENCE | VALUE.ARRAY |
                          VALUE.REFARRAY)?>
    <!ATTLIST PARAMVALUE
        %CIMName;
        %ParamType;  #IMPLIED>
    """

    def setUp(self):
        super(ParamValue, self).setUp()

        # Empty

        self.xml.append(cim_xml.PARAMVALUE('Pet'))

        # VALUE

        self.xml.append(cim_xml.PARAMVALUE(
            'Pet',
            cim_xml.VALUE('Dog'),
            'string'))

        # VALUE.REFERENCE

        self.xml.append(cim_xml.PARAMVALUE(
            'Pet',
            cim_xml.VALUE_REFERENCE(sample_CLASSPATH_node())))

        # VALUE.ARRAY

        self.xml.append(cim_xml.PARAMVALUE(
            'Pet',
            cim_xml.VALUE_ARRAY([])))

        # VALUE.REFARRAY

        self.xml.append(cim_xml.PARAMVALUE(
            'Pet',
            cim_xml.VALUE_REFARRAY([])))


class IParamValue(CIMXMLTest):
    """
    <!ELEMENT IPARAMVALUE (VALUE | VALUE.ARRAY | VALUE.REFERENCE |
                           INSTANCENAME | CLASSNAME | QUALIFIER.DECLARATION |
                           CLASS | INSTANCE | VALUE.NAMEDINSTANCE)?>
    <!ATTLIST IPARAMVALUE
        %CIMName;>
    """

    def setUp(self):
        super(IParamValue, self).setUp()

        # Empty

        self.xml.append(cim_xml.IPARAMVALUE('Bird'))

        # VALUE

        self.xml.append(cim_xml.IPARAMVALUE(
            'Pet',
            cim_xml.VALUE('Dog')))

        # VALUE.ARRAY

        self.xml.append(cim_xml.IPARAMVALUE(
            'Pet',
            cim_xml.VALUE_ARRAY([])))

        # VALUE.REFERENCE

        self.xml.append(cim_xml.IPARAMVALUE(
            'Pet',
            cim_xml.VALUE_REFERENCE(sample_CLASSPATH_node())))

        # INSTANCENAME

        self.xml.append(cim_xml.IPARAMVALUE(
            'Pet',
            sample_INSTANCENAME_node()))

        # CLASSNAME

        self.xml.append(cim_xml.IPARAMVALUE(
            'Pet',
            sample_CLASSNAME_node()))

        # TODO: QUALIFIER.DECLARATION

        # CLASS

        self.xml.append(cim_xml.IPARAMVALUE(
            'Pet',
            cim_xml.CLASS('CIM_Foo')))

        # INSTANCE

        self.xml.append(cim_xml.IPARAMVALUE(
            'Pet',
            cim_xml.INSTANCE('CIM_Pet', [])))

        # VALUE.NAMEDINSTANCE

        self.xml.append(cim_xml.IPARAMVALUE(
            'Pet',
            cim_xml.VALUE_NAMEDINSTANCE(
                sample_INSTANCENAME_node(),
                cim_xml.INSTANCE('CIM_Pet', []))))


class ExpParamValue(CIMXMLTest):
    """
    <!ELEMENT EXPPARAMVALUE (INSTANCE? | VALUE? | METHODRESPONSE? |
                             IMETHODRESPONSE?)>
    <!ATTLIST EXPPARAMVALUE
        %CIMName;
        %ParamType;  #IMPLIED>
    """

    def setUp(self):
        super(ExpParamValue, self).setUp()

        self.xml.append(cim_xml.EXPPARAMVALUE('FooParam'))

        self.xml.append(cim_xml.EXPPARAMVALUE(
            'FooParam',
            cim_xml.INSTANCE('CIM_Pet', [])))


class MultiRsp(CIMXMLTest):
    """
    <!ELEMENT MULTIRSP (SIMPLERSP, SIMPLERSP+)>
    """

    def setUp(self):
        super(MultiRsp, self).setUp()

        self.xml.append(
            cim_xml.MULTIRSP(
                [cim_xml.SIMPLERSP(cim_xml.IMETHODRESPONSE('FooMethod')),
                 cim_xml.SIMPLERSP(cim_xml.IMETHODRESPONSE('FooMethod'))]))


class MultiExpRsp(CIMXMLTest):
    """
    <!ELEMENT MULTIEXPRSP (SIMPLEEXPRSP, SIMPLEEXPRSP+)>
    """

    def setUp(self):
        super(MultiExpRsp, self).setUp()

        self.xml.append(
            cim_xml.MULTIEXPRSP(
                [cim_xml.SIMPLEEXPRSP(
                    cim_xml.EXPMETHODRESPONSE('FooMethod')),
                 cim_xml.SIMPLEEXPRSP(
                     cim_xml.EXPMETHODRESPONSE('FooMethod'))]))


class SimpleRsp(CIMXMLTest):
    """
    <!ELEMENT SIMPLERSP (METHODRESPONSE | IMETHODRESPONSE)>
    """

    def setUp(self):
        super(SimpleRsp, self).setUp()

        # METHODRESPONSE

        self.xml.append(
            cim_xml.SIMPLERSP(cim_xml.METHODRESPONSE('FooMethod')))

        # IMETHODRESPONSE

        self.xml.append(
            cim_xml.SIMPLERSP(cim_xml.IMETHODRESPONSE('FooMethod')))


class SimpleExpRsp(CIMXMLTest):
    """
    <!ELEMENT SIMPLEEXPRSP (EXPMETHODRESPONSE)>
    """

    def setUp(self):
        super(SimpleExpRsp, self).setUp()

        self.xml.append(
            cim_xml.SIMPLEEXPRSP(cim_xml.EXPMETHODRESPONSE('FooMethod')))


class MethodResponse(CIMXMLTest):
    """
    <!ELEMENT METHODRESPONSE (ERROR | (RETURNVALUE?, PARAMVALUE*))>
    <!ATTLIST METHODRESPONSE
        %CIMName;>
    """

    def setUp(self):
        super(MethodResponse, self).setUp()

        # ERROR

        self.xml.append(
            cim_xml.METHODRESPONSE(
                'FooMethod',
                cim_xml.ERROR('123')))

        # Empty

        self.xml.append(cim_xml.METHODRESPONSE('FooMethod'))

        # RETURNVALUE

        self.xml.append(
            cim_xml.METHODRESPONSE(
                'FooMethod',
                cim_xml.PARAMVALUE('Dog', cim_xml.VALUE('Spottyfoot'))))

        # PARAMVALUE

        self.xml.append(
            cim_xml.METHODRESPONSE(
                'FooMethod',
                cim_xml.PARAMVALUE('Dog', cim_xml.VALUE('Spottyfoot'))))

        # RETURNVALUE + PARAMVALUE

        self.xml.append(
            cim_xml.METHODRESPONSE(
                'FooMethod',
                (cim_xml.RETURNVALUE(cim_xml.VALUE('Dog')),
                 cim_xml.PARAMVALUE('Dog', cim_xml.VALUE('Spottyfoot')))))


class ExpMethodResponse(CIMXMLTest):
    """
    <!ELEMENT EXPMETHODRESPONSE (ERROR | IRETURNVALUE?)>
    <!ATTLIST EXPMETHODRESPONSE
        %CIMName;>
    """

    def setUp(self):
        super(ExpMethodResponse, self).setUp()

        # Empty

        self.xml.append(cim_xml.EXPMETHODRESPONSE('FooMethod'))

        # ERROR

        self.xml.append(cim_xml.EXPMETHODRESPONSE(
            'FooMethod',
            cim_xml.ERROR('123')))

        # IRETURNVALUE

        self.xml.append(cim_xml.EXPMETHODRESPONSE(
            'FooMethod',
            cim_xml.IRETURNVALUE(cim_xml.VALUE('Dog'))))


class IMethodResponse(CIMXMLTest):
    """
    <!ELEMENT IMETHODRESPONSE (ERROR | IRETURNVALUE?)>
    <!ATTLIST IMETHODRESPONSE
        %CIMName;>
    """

    def setUp(self):
        super(IMethodResponse, self).setUp()

        # Empty

        self.xml.append(cim_xml.IMETHODRESPONSE('FooMethod'))

        # ERROR

        self.xml.append(cim_xml.IMETHODRESPONSE(
            'FooMethod',
            cim_xml.ERROR('123')))

        # IRETURNVALUE

        self.xml.append(cim_xml.IMETHODRESPONSE(
            'FooMethod',
            cim_xml.IRETURNVALUE(cim_xml.VALUE('Dog'))))


class Error(CIMXMLTest):
    """
    <!ELEMENT ERROR (INSTANCE*)>
    <!ATTLIST ERROR
        CODE CDATA #REQUIRED
        DESCRIPTION CDATA #IMPLIED>
    """

    def setUp(self):
        super(Error, self).setUp()

        self.xml.append(cim_xml.ERROR('1'))
        self.xml.append(cim_xml.ERROR('1', 'Foo not found'))
        # TODO: INSTANCE*


class ReturnValue(CIMXMLTest):
    """
    <!ELEMENT RETURNVALUE (VALUE | VALUE.REFERENCE)>
    <!ATTLIST RETURNVALUE
        %ParamType;     #IMPLIED>
    """

    def setUp(self):
        super(ReturnValue, self).setUp()

        # VALUE

        self.xml.append(cim_xml.RETURNVALUE(cim_xml.VALUE('Dog')))

        # VALUE.REFERENCE

        self.xml.append(cim_xml.RETURNVALUE(
            cim_xml.VALUE_REFERENCE(sample_CLASSPATH_node())))

        # TODO: PARAMTYPE


class IReturnValue(CIMXMLTest):
    """
    <!ELEMENT IRETURNVALUE (CLASSNAME* | INSTANCENAME* | VALUE* |
                            VALUE.OBJECTWITHPATH* |
                            VALUE.OBJECTWITHLOCALPATH* | VALUE.OBJECT* |
                            OBJECTPATH* | QUALIFIER.DECLARATION* |
                            VALUE.ARRAY? | VALUE.REFERENCE? | CLASS* |
                            INSTANCE* | VALUE.NAMEDINSTANCE*)>
    """

    def setUp(self):
        super(IReturnValue, self).setUp()

        # Empty

        self.xml.append(cim_xml.IRETURNVALUE(None))

        # CLASSNAME

        self.xml.append(cim_xml.IRETURNVALUE(
            sample_CLASSNAME_node()))

        # INSTANCENAME

        self.xml.append(cim_xml.IRETURNVALUE(
            sample_INSTANCENAME_node()))

        # VALUE

        self.xml.append(cim_xml.IRETURNVALUE(
            cim_xml.VALUE('Dog')))

        # VALUE.OBJECTWITHPATH

        self.xml.append(cim_xml.IRETURNVALUE(
            cim_xml.VALUE_OBJECTWITHPATH(
                sample_CLASSPATH_node(),
                cim_xml.CLASS('CIM_Foo'))))

        # VALUE.OBJECTWITHLOCALPATH

        self.xml.append(cim_xml.IRETURNVALUE(
            cim_xml.VALUE_OBJECTWITHLOCALPATH(
                cim_xml.LOCALCLASSPATH(
                    sample_LOCALNAMESPACEPATH_node(),
                    sample_CLASSNAME_node()),
                cim_xml.CLASS('CIM_Foo'))))

        # VALUE.OBJECT

        self.xml.append(cim_xml.IRETURNVALUE(
            cim_xml.VALUE_OBJECT(cim_xml.INSTANCE('CIM_Pet', []))))

        # OBJECTPATH

        self.xml.append(cim_xml.IRETURNVALUE(
            cim_xml.OBJECTPATH(
                cim_xml.INSTANCEPATH(
                    sample_NAMESPACEPATH_node(),
                    sample_INSTANCENAME_node()))))

        # TODO: QUALIFIER.DECLARATION

        # VALUE.ARRAY

        self.xml.append(cim_xml.IRETURNVALUE(
            cim_xml.VALUE_ARRAY([])))

        # VALUE.REFERENCE

        self.xml.append(cim_xml.IRETURNVALUE(
            cim_xml.VALUE_REFERENCE(sample_CLASSPATH_node())))

        # CLASS

        self.xml.append(cim_xml.IRETURNVALUE(
            cim_xml.CLASS('CIM_Foo')))

        # INSTANCE

        self.xml.append(cim_xml.IRETURNVALUE(
            cim_xml.INSTANCE('CIM_Pet', [])))

        # VALUE.NAMEDINSTANCE

        self.xml.append(cim_xml.IRETURNVALUE(
            cim_xml.VALUE_NAMEDINSTANCE(
                sample_INSTANCENAME_node(),
                cim_xml.INSTANCE('CIM_Pet', []))))
