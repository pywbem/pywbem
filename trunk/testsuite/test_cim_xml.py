#!/usr/bin/env python
#
# Exercise routines in cim_xml by creating xml document fragments and
# passing them through a validator.
#
# TODO: Currently this forks of an instance of xmllint which is a
# little slow.  It would be nicer to have an in-process validator.
#
# TODO: A bunch of tests are still unimplemented for bits of the
# schema that PyWBEM doesn't use right now.
#

import sys

from pywbem import cim_xml

import comfychair

DTD_FILE = 'CIM_DTD_V22.dtd'

def validate_xml(data, dtd_directory=None):

    from subprocess import Popen, PIPE

    # Run xmllint to validate file

    dtd_file = DTD_FILE
    if dtd_directory is not None:
        dtd_file = '%s/%s' % (dtd_directory, DTD_FILE)

    p = Popen('xmllint --dtdvalid %s --noout -' % dtd_file, stdout=PIPE,
              stdin=PIPE, stderr=PIPE, shell=True)

    p.stdin.write(data)
    p.stdin.close()

    [sys.stdout.write(x) for x in p.stdout.readlines()]

    status = p.wait()

    if status != 0:
        return False

    return True

# Test data to save typing

def LOCALNAMESPACEPATH():
    return cim_xml.LOCALNAMESPACEPATH([cim_xml.NAMESPACE('root'),
                                       cim_xml.NAMESPACE('cimv2')])

def NAMESPACEPATH():
    return cim_xml.NAMESPACEPATH(
        cim_xml.HOST('leonardo'), LOCALNAMESPACEPATH())

def CLASSNAME():
    return cim_xml.CLASSNAME('CIM_Foo')

def INSTANCENAME():
    return cim_xml.INSTANCENAME(
        'CIM_Pet',
        [cim_xml.KEYBINDING('type', cim_xml.KEYVALUE('dog', 'string')),
         cim_xml.KEYBINDING('age', cim_xml.KEYVALUE('2', 'numeric'))])

# Base classes

class CIMXMLTest(comfychair.TestCase):
    """Run validate.py script against an xml document fragment."""

    xml = []                            # Test data

    def validate(self, xml, expectedResult=0):
        validate_xml(xml, dtd_directory='../..')

    def runtest(self):

        # Test xml fragments pass validation

        for x in [x.toxml() for x in self.xml]:
            self.validate(x)

class UnimplementedTest(CIMXMLTest):
    def runtest(self):
        raise comfychair.NotRunError('unimplemented')

#################################################################
#     3.2.1. Top Level Elements
#################################################################

#     3.2.1.1. CIM

class CIM(CIMXMLTest):
    def setup(self):
        self.xml.append(cim_xml.CIM(
            cim_xml.MESSAGE(
                cim_xml.SIMPLEREQ(
                    cim_xml.IMETHODCALL(
                        'IntrinsicMethod',
                        LOCALNAMESPACEPATH())),
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

class Declaration(UnimplementedTest):
    """
    <!ELEMENT DECLARATION  (DECLGROUP|DECLGROUP.WITHNAME|DECLGROUP.WITHPATH)+>
    """

class DeclGroup(UnimplementedTest):
    """
    <!ELEMENT DECLGROUP  ((LOCALNAMESPACEPATH|NAMESPACEPATH)?,
                          QUALIFIER.DECLARATION*,VALUE.OBJECT*)>
    """

    pass

class DeclGroupWithName(UnimplementedTest):
    """
    <!ELEMENT DECLGROUP.WITHNAME  ((LOCALNAMESPACEPATH|NAMESPACEPATH)?,
                                   QUALIFIER.DECLARATION*,VALUE.NAMEDOBJECT*)>
    """

class DeclGroupWithPath(UnimplementedTest):
    """
    <!ELEMENT DECLGROUP.WITHPATH  (VALUE.OBJECTWITHPATH|
                                   VALUE.OBJECTWITHLOCALPATH)*>
    """

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

    def setup(self):
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

    def setup(self):

        self.xml.append(cim_xml.VALUE('dog'))
        self.xml.append(cim_xml.VALUE(None))
        self.xml.append(cim_xml.VALUE(''))

class ValueArray(CIMXMLTest):
    """
    <!ELEMENT VALUE.ARRAY (VALUE*)>
    """

    def setup(self):

        self.xml.append(cim_xml.VALUE_ARRAY([]))

        self.xml.append(cim_xml.VALUE_ARRAY([cim_xml.VALUE('cat'),
                                             cim_xml.VALUE('dog')]))

class ValueReference(CIMXMLTest):
    """
    <!ELEMENT VALUE.REFERENCE (CLASSPATH|LOCALCLASSPATH|CLASSNAME|
                               INSTANCEPATH|LOCALINSTANCEPATH|INSTANCENAME)>
    """

    def setup(self):

        # CLASSPATH

        self.xml.append(cim_xml.VALUE_REFERENCE(
            cim_xml.CLASSPATH(NAMESPACEPATH(), CLASSNAME())))

        # LOCALCLASSPATH

        self.xml.append(cim_xml.VALUE_REFERENCE(
            cim_xml.LOCALCLASSPATH(LOCALNAMESPACEPATH(), CLASSNAME())))

        # CLASSNAME

        self.xml.append(cim_xml.VALUE_REFERENCE(CLASSNAME()))

        # INSTANCEPATH

        self.xml.append(cim_xml.VALUE_REFERENCE(
            cim_xml.INSTANCEPATH(
                NAMESPACEPATH(), INSTANCENAME())))

        # LOCALINSTANCEPATH

        self.xml.append(cim_xml.VALUE_REFERENCE(
            cim_xml.LOCALINSTANCEPATH(
                LOCALNAMESPACEPATH(), INSTANCENAME())))

        # INSTANCENAME

        self.xml.append(cim_xml.VALUE_REFERENCE(INSTANCENAME()))

class ValueRefArray(CIMXMLTest):
    """
    <!ELEMENT VALUE.REFARRAY (VALUE.REFERENCE*)>
    """

    def setup(self):

        # Empty

        self.xml.append(cim_xml.VALUE_REFARRAY([]))

        # VALUE.REFARRAY

        self.xml.append(cim_xml.VALUE_REFARRAY(
            [cim_xml.VALUE_REFERENCE(cim_xml.CLASSNAME('CIM_Foo')),
             cim_xml.VALUE_REFERENCE(cim_xml.LOCALCLASSPATH(
                 LOCALNAMESPACEPATH(), CLASSNAME()))]))

class ValueObject(CIMXMLTest):
    """
    <!ELEMENT VALUE.OBJECT (CLASS|INSTANCE)>
    """

    def setup(self):

        # CLASS

        self.xml.append(cim_xml.VALUE_OBJECT(cim_xml.CLASS('CIM_Foo')))

        # INSTANCE

        self.xml.append(cim_xml.VALUE_OBJECT(cim_xml.INSTANCE('CIM_Pet', [])))

class ValueNamedInstance(CIMXMLTest):
    """
    <!ELEMENT VALUE.NAMEDINSTANCE (INSTANCENAME,INSTANCE)>
    """

    def setup(self):

        self.xml.append(cim_xml.VALUE_NAMEDINSTANCE(
            INSTANCENAME(),
            cim_xml.INSTANCE('CIM_Pet', [])))

class ValueNamedObject(CIMXMLTest):
    """
    <!ELEMENT VALUE.NAMEDOBJECT (CLASS|(INSTANCENAME,INSTANCE))>
    """

    def setup(self):

        # CLASS

        self.xml.append(cim_xml.VALUE_NAMEDOBJECT(
            cim_xml.CLASS('CIM_Foo')))

        # INSTANCENAME, INSTANCE

        self.xml.append(cim_xml.VALUE_NAMEDOBJECT(
            (INSTANCENAME(),
             cim_xml.INSTANCE('CIM_Pet', []))))

class ValueObjectWithPath(CIMXMLTest):
    """
    <!ELEMENT VALUE.OBJECTWITHPATH ((CLASSPATH,CLASS)|
                                    (INSTANCEPATH,INSTANCE))>
    """

    def setup(self):

        # (CLASSPATH, CLASS)

        self.xml.append(cim_xml.VALUE_OBJECTWITHPATH(
            cim_xml.CLASSPATH(NAMESPACEPATH(), CLASSNAME()),
            cim_xml.CLASS('CIM_Foo')))

        # (INSTANCEPATH, INSTANCE)

        self.xml.append(cim_xml.VALUE_OBJECTWITHPATH(
            cim_xml.INSTANCEPATH(
                NAMESPACEPATH(), INSTANCENAME()),
            cim_xml.INSTANCE('CIM_Pet', [])))

class ValueObjectWithLocalPath(CIMXMLTest):
    """
    <!ELEMENT VALUE.OBJECTWITHLOCALPATH ((LOCALCLASSPATH,CLASS)|
                                         (LOCALINSTANCEPATH,INSTANCE))>
    """

    def setup(self):

        # (LOCALCLASSPATH, CLASS)

        self.xml.append(cim_xml.VALUE_OBJECTWITHLOCALPATH(
            cim_xml.LOCALCLASSPATH(LOCALNAMESPACEPATH(), CLASSNAME()),
            cim_xml.CLASS('CIM_Foo')))

        # (LOCALINSTANCEPATH, INSTANCE)

        self.xml.append(cim_xml.VALUE_OBJECTWITHLOCALPATH(
            cim_xml.LOCALINSTANCEPATH(
                LOCALNAMESPACEPATH(),
                INSTANCENAME()),
            cim_xml.INSTANCE('CIM_Pet', [])))

class ValueNull(UnimplementedTest):
    """
    <!ELEMENT VALUE.NULL EMPTY>
    """

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

    def setup(self):
        self.xml.append(NAMESPACEPATH())

class LocalNamespacePath(CIMXMLTest):
    """
    <!ELEMENT LOCALNAMESPACEPATH (NAMESPACE+)>
    """

    def setup(self):
        self.xml.append(LOCALNAMESPACEPATH())

class Host(CIMXMLTest):
    """
    <!ELEMENT HOST (#PCDATA)>
    """

    def setup(self):
        self.xml.append(cim_xml.HOST('leonardo'))

class Namespace(CIMXMLTest):
    """
    <!ELEMENT NAMESPACE EMPTY>
    <!ATTLIST NAMESPACE
        %CIMName;>
    """

    def setup(self):
        self.xml.append(cim_xml.NAMESPACE('root'))

class ClassPath(CIMXMLTest):
    """
    <!ELEMENT CLASSPATH (NAMESPACEPATH,CLASSNAME)>
    """

    def setup(self):
        self.xml.append(cim_xml.CLASSPATH(NAMESPACEPATH(), CLASSNAME()))

class LocalClassPath(CIMXMLTest):
    """
    <!ELEMENT LOCALCLASSPATH (LOCALNAMESPACEPATH, CLASSNAME)>
    """

    def setup(self):
        self.xml.append(cim_xml.LOCALCLASSPATH(
            LOCALNAMESPACEPATH(), CLASSNAME()))

class ClassName(CIMXMLTest):
    """
    <!ELEMENT CLASSNAME EMPTY>
    <!ATTLIST CLASSNAME
        %CIMName;>
    """

    def setup(self):
        self.xml.append(CLASSNAME())

class InstancePath(CIMXMLTest):
    """
    <!ELEMENT INSTANCEPATH (NAMESPACEPATH,INSTANCENAME)>
    """

    def setup(self):
        self.xml.append(cim_xml.INSTANCEPATH(
            NAMESPACEPATH(), INSTANCENAME()))

class LocalInstancePath(CIMXMLTest):
    """
    <!ELEMENT LOCALINSTANCEPATH (LOCALNAMESPACEPATH,INSTANCENAME)>
    """

    def setup(self):
        self.xml.append(cim_xml.LOCALINSTANCEPATH(
            LOCALNAMESPACEPATH(), INSTANCENAME()))

class InstanceName(CIMXMLTest):
    """
    <!ELEMENT INSTANCENAME (KEYBINDING*|KEYVALUE?|VALUE.REFERENCE?)>
    <!ATTLIST INSTANCENAME
        %ClassName;>
    """

    def setup(self):

        # Empty

        self.xml.append(cim_xml.INSTANCENAME('CIM_Pet', None))

        # KEYBINDING

        self.xml.append(INSTANCENAME())

        # KEYVALUE

        self.xml.append(cim_xml.INSTANCENAME(
            'CIM_Pet', cim_xml.KEYVALUE('FALSE', 'boolean')))

        # VALUE.REFERENCE

        self.xml.append(cim_xml.INSTANCENAME(
            'CIM_Pet',
            cim_xml.VALUE_REFERENCE(INSTANCENAME())))

class ObjectPath(CIMXMLTest):
    """
    <!ELEMENT OBJECTPATH (INSTANCEPATH|CLASSPATH)>
    """

    def setup(self):

        self.xml.append(cim_xml.OBJECTPATH(
            cim_xml.INSTANCEPATH(
                NAMESPACEPATH(), INSTANCENAME())))

        self.xml.append(cim_xml.OBJECTPATH(
            cim_xml.CLASSPATH(NAMESPACEPATH(), CLASSNAME())))

class KeyBinding(CIMXMLTest):
    """
    <!ELEMENT KEYBINDING (KEYVALUE|VALUE.REFERENCE)>
    <!ATTLIST KEYBINDING
        %CIMName;>
    """

    def setup(self):

        self.xml.append(cim_xml.KEYBINDING(
            'pet', cim_xml.KEYVALUE('dog', 'string')))

        self.xml.append(cim_xml.KEYBINDING(
            'CIM_Foo',
            cim_xml.VALUE_REFERENCE(
                cim_xml.CLASSPATH(NAMESPACEPATH(), CLASSNAME()))))

class KeyValue(CIMXMLTest):
    """
    <!ELEMENT KEYVALUE (#PCDATA)>
    <!ATTLIST KEYVALUE
        VALUETYPE    (string|boolean|numeric)  'string'
        %CIMType;    #IMPLIED>
    """

    def setup(self):

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
#     3.2.5.12. TABLECELL.DECLARATION
#     3.2.5.13. TABLECELL.REFERENCE
#     3.2.5.14. TABLEROW.DECLARATION
#     3.2.5.15. TABLE
#     3.2.5.16. TABLEROW

class Class(CIMXMLTest):
    """
    <!ELEMENT CLASS (QUALIFIER*,(PROPERTY|PROPERTY.ARRAY|PROPERTY.REFERENCE)*,
                     METHOD*)>
    <!ATTLIST CLASS
        %CIMName;
        %SuperClass;>
    """

    def setup(self):

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

    def setup(self):

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

    def setup(self):

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

    def setup(self):

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

    def setup(self):

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

    def setup(self):

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

    def setup(self):

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

    def setup(self):

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

    def setup(self):

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

    def setup(self):

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

    def setup(self):

        # Empty

        self.xml.append(cim_xml.PARAMETER_REFARRAY('arg'))

        # QUALIFIERS + attributes

        self.xml.append(cim_xml.PARAMETER_REFARRAY(
            'arg',
            reference_class='CIM_Foo',
            array_size='0',
            qualifiers=[cim_xml.QUALIFIER('IMPISH', 'string',
                                          cim_xml.VALUE('true'))]))

# New in v2.2 of the DTD

# TABLECELL.DECLARATION
# TABLECELL.REFERENCE
# TABLEROW.DECLARATION
# TABLE
# TABLEROW

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
#     3.2.6.22 RESPONSEDESTINATION
#     3.2.6.23 SIMPLEREQACK

class Message(CIMXMLTest):
    """
    <!ELEMENT MESSAGE (SIMPLEREQ | MULTIREQ | SIMPLERSP | MULTIRSP |
                       SIMPLEEXPREQ | MULTIEXPREQ | SIMPLEEXPRSP |
                       MULTIEXPRSP)>
    <!ATTLIST MESSAGE
        ID CDATA #REQUIRED
        PROTOCOLVERSION CDATA #REQUIRED>
    """

    def setup(self):

        # SIMPLEREQ

        self.xml.append(cim_xml.MESSAGE(
            cim_xml.SIMPLEREQ(
                cim_xml.IMETHODCALL(
                    'FooMethod',
                    LOCALNAMESPACEPATH())),
            '1001', '1.0'))

        # MULTIREQ

        self.xml.append(cim_xml.MESSAGE(
            cim_xml.MULTIREQ(
                [cim_xml.SIMPLEREQ(cim_xml.IMETHODCALL('FooMethod',
                                                       LOCALNAMESPACEPATH())),
                 cim_xml.SIMPLEREQ(cim_xml.IMETHODCALL('FooMethod',
                                                       LOCALNAMESPACEPATH()))]),
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

    def setup(self):

        self.xml.append(cim_xml.MULTIREQ(
            [cim_xml.SIMPLEREQ(cim_xml.IMETHODCALL('FooMethod',
                                                   LOCALNAMESPACEPATH())),
             cim_xml.SIMPLEREQ(cim_xml.IMETHODCALL('FooMethod',
                                                   LOCALNAMESPACEPATH()))]))

class MultiExpReq(CIMXMLTest):
    """
    <!ELEMENT MULTIEXPREQ (SIMPLEEXPREQ, SIMPLEEXPREQ+)>
    """

    def setup(self):

        self.xml.append(cim_xml.MULTIEXPREQ(
            [cim_xml.SIMPLEEXPREQ(cim_xml.EXPMETHODCALL('FooMethod')),
             cim_xml.SIMPLEEXPREQ(cim_xml.EXPMETHODCALL('FooMethod'))]))

class SimpleReq(CIMXMLTest):
    """
    <!ELEMENT SIMPLEREQ (IMETHODCALL | METHODCALL)>
    """

    def setup(self):

        # IMETHODCALL

        self.xml.append(cim_xml.SIMPLEREQ(
            cim_xml.IMETHODCALL('FooIMethod', LOCALNAMESPACEPATH())))

        # METHODCALL

        self.xml.append(cim_xml.SIMPLEREQ(
            cim_xml.METHODCALL(
                'FooMethod',
                cim_xml.LOCALCLASSPATH(LOCALNAMESPACEPATH(), CLASSNAME()))))

class SimpleExpReq(CIMXMLTest):
    """
    <!ELEMENT SIMPLEEXPREQ (EXPMETHODCALL)>
    """

    def setup(self):
        self.xml.append(cim_xml.SIMPLEEXPREQ(
            cim_xml.EXPMETHODCALL('FooMethod')))

class IMethodCall(CIMXMLTest):
    """
    <!ELEMENT IMETHODCALL (LOCALNAMESPACEPATH, IPARAMVALUE*,
                           RESPONSEDESTINATION?)>
    <!ATTLIST IMETHODCALL
        %CIMName;>
    """

    def setup(self):

        self.xml.append(
            cim_xml.IMETHODCALL('FooMethod', LOCALNAMESPACEPATH()))

        self.xml.append(cim_xml.IMETHODCALL(
            'FooMethod2', LOCALNAMESPACEPATH(),
            [cim_xml.IPARAMVALUE('Dog', cim_xml.VALUE('Spottyfoot'))]))

        # TODO: RESPONSEDESTINATION

class MethodCall(CIMXMLTest):
    """
    <!ELEMENT METHODCALL ((LOCALINSTANCEPATH | LOCALCLASSPATH), PARAMVALUE*,
                          RESPONSEDESTINATION?>
    <!ATTLIST METHODCALL
        %CIMName;>
    """

    def setup(self):

        # LOCALINSTANCEPATH

        self.xml.append(cim_xml.METHODCALL(
            'FooMethod',
            cim_xml.LOCALINSTANCEPATH(LOCALNAMESPACEPATH(), INSTANCENAME())))

        # LOCALCLASSPATH

        self.xml.append(cim_xml.METHODCALL(
            'FooMethod',
            cim_xml.LOCALCLASSPATH(LOCALNAMESPACEPATH(), CLASSNAME())))

        # PARAMVALUEs

        self.xml.append(cim_xml.METHODCALL(
            'FooMethod',
            cim_xml.LOCALINSTANCEPATH(LOCALNAMESPACEPATH(), INSTANCENAME()),
            [cim_xml.PARAMVALUE('Dog', cim_xml.VALUE('Spottyfoot'))]))

        # TODO: RESPONSEDESTINATION

class ExpMethodCall(CIMXMLTest):
    """
    <!ELEMENT EXPMETHODCALL (EXPPARAMVALUE*)>
    <!ATTLIST EXPMETHODCALL
        %CIMName;>
    """

    def setup(self):

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

    def setup(self):

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
            cim_xml.VALUE_REFERENCE(cim_xml.CLASSPATH(NAMESPACEPATH(),
                                                      CLASSNAME()))))

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

    def setup(self):

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
            cim_xml.VALUE_REFERENCE(
                cim_xml.CLASSPATH(NAMESPACEPATH(), CLASSNAME()))))

        # INSTANCENAME

        self.xml.append(cim_xml.IPARAMVALUE(
            'Pet',
            INSTANCENAME()))

        # CLASSNAME

        self.xml.append(cim_xml.IPARAMVALUE(
            'Pet',
            CLASSNAME()))

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
                INSTANCENAME(),
                cim_xml.INSTANCE('CIM_Pet', []))))


class ExpParamValue(CIMXMLTest):
    """
    <!ELEMENT EXPPARAMVALUE (INSTANCE? | VALUE? | METHODRESPONSE? |
                             IMETHODRESPONSE?)>
    <!ATTLIST EXPPARAMVALUE
        %CIMName;
        %ParamType;  #IMPLIED>
    """

    def setup(self):

        self.xml.append(cim_xml.EXPPARAMVALUE('FooParam'))

        self.xml.append(cim_xml.EXPPARAMVALUE(
            'FooParam',
            cim_xml.INSTANCE('CIM_Pet', [])))


class MultiRsp(CIMXMLTest):
    """
    <!ELEMENT MULTIRSP (SIMPLERSP, SIMPLERSP+)>
    """

    def setup(self):

        self.xml.append(
            cim_xml.MULTIRSP(
                [cim_xml.SIMPLERSP(cim_xml.IMETHODRESPONSE('FooMethod')),
                 cim_xml.SIMPLERSP(cim_xml.IMETHODRESPONSE('FooMethod'))]))


class MultiExpRsp(CIMXMLTest):
    """
    <!ELEMENT MULTIEXPRSP (SIMPLEEXPRSP, SIMPLEEXPRSP+)>
    """

    def setup(self):

        self.xml.append(
            cim_xml.MULTIEXPRSP(
                [cim_xml.SIMPLEEXPRSP(cim_xml.EXPMETHODRESPONSE('FooMethod')),
                 cim_xml.SIMPLEEXPRSP(cim_xml.EXPMETHODRESPONSE('FooMethod'))]))

class SimpleRsp(CIMXMLTest):
    """
    <!ELEMENT SIMPLERSP (METHODRESPONSE | IMETHODRESPONSE | SIMPLEREQACK>
    """

    def setup(self):

        # METHODRESPONSE

        self.xml.append(
            cim_xml.SIMPLERSP(cim_xml.METHODRESPONSE('FooMethod')))

        # IMETHODRESPONSE

        self.xml.append(
            cim_xml.SIMPLERSP(cim_xml.IMETHODRESPONSE('FooMethod')))

        # TODO: SIMPLEREQACK

class SimpleExpRsp(CIMXMLTest):
    """
    <!ELEMENT SIMPLEEXPRSP (EXPMETHODRESPONSE)>
    """

    def setup(self):

        self.xml.append(
            cim_xml.SIMPLEEXPRSP(cim_xml.EXPMETHODRESPONSE('FooMethod')))

class MethodResponse(CIMXMLTest):
    """
    <!ELEMENT METHODRESPONSE (ERROR | (RETURNVALUE?, PARAMVALUE*))>
    <!ATTLIST METHODRESPONSE
        %CIMName;>
    """

    def setup(self):

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

    def setup(self):

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

    def setup(self):

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

    def setup(self):
        self.xml.append(cim_xml.ERROR('1'))
        self.xml.append(cim_xml.ERROR('1', 'Foo not found'))
        # TODO: INSTANCE*

class ReturnValue(CIMXMLTest):
    """
    <!ELEMENT RETURNVALUE (VALUE | VALUE.REFERENCE)>
    <!ATTLIST RETURNVALUE
        %ParamType;     #IMPLIED>
    """

    def setup(self):

        # VALUE

        self.xml.append(cim_xml.RETURNVALUE(cim_xml.VALUE('Dog')))

        # VALUE.REFERENCE

        self.xml.append(cim_xml.RETURNVALUE(cim_xml.VALUE_REFERENCE(
            cim_xml.CLASSPATH(NAMESPACEPATH(), CLASSNAME()))))

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

    def setup(self):

        # Empty

        self.xml.append(cim_xml.IRETURNVALUE(None))

        # CLASSNAME

        self.xml.append(cim_xml.IRETURNVALUE(
            CLASSNAME()))

        # INSTANCENAME

        self.xml.append(cim_xml.IRETURNVALUE(
            INSTANCENAME()))

        # VALUE

        self.xml.append(cim_xml.IRETURNVALUE(
            cim_xml.VALUE('Dog')))

        # VALUE.OBJECTWITHPATH

        self.xml.append(cim_xml.IRETURNVALUE(
            cim_xml.VALUE_OBJECTWITHPATH(
                cim_xml.CLASSPATH(NAMESPACEPATH(), CLASSNAME()),
                cim_xml.CLASS('CIM_Foo'))))

        # VALUE.OBJECTWITHLOCALPATH

        self.xml.append(cim_xml.IRETURNVALUE(
            cim_xml.VALUE_OBJECTWITHLOCALPATH(
                cim_xml.LOCALCLASSPATH(LOCALNAMESPACEPATH(), CLASSNAME()),
                cim_xml.CLASS('CIM_Foo'))))

        # VALUE.OBJECT

        self.xml.append(cim_xml.IRETURNVALUE(
            cim_xml.VALUE_OBJECT(cim_xml.INSTANCE('CIM_Pet', []))))

        # OBJECTPATH

        self.xml.append(cim_xml.IRETURNVALUE(
            cim_xml.OBJECTPATH(
                cim_xml.INSTANCEPATH(NAMESPACEPATH(), INSTANCENAME()))))

        # TODO: QUALIFIER.DECLARATION

        # VALUE.ARRAY

        self.xml.append(cim_xml.IRETURNVALUE(
            cim_xml.VALUE_ARRAY([])))

        # VALUE.REFERENCE

        self.xml.append(cim_xml.IRETURNVALUE(
            cim_xml.VALUE_REFERENCE(
                cim_xml.CLASSPATH(NAMESPACEPATH(), CLASSNAME()))))

        # CLASS

        self.xml.append(cim_xml.IRETURNVALUE(
            cim_xml.CLASS('CIM_Foo')))

        # INSTANCE

        self.xml.append(cim_xml.IRETURNVALUE(
            cim_xml.INSTANCE('CIM_Pet', [])))

        # VALUE.NAMEDINSTANCE

        self.xml.append(cim_xml.IRETURNVALUE(
            cim_xml.VALUE_NAMEDINSTANCE(
                INSTANCENAME(),
                cim_xml.INSTANCE('CIM_Pet', []))))

class ResponseDestination(UnimplementedTest):
    """
    The RESPONSEDESTINATION element contains an instance that
    describes the desired destination for the response.

    <!ELEMENT RESPONSEDESTINATON (INSTANCE)>
    """

class SimpleReqAck(UnimplementedTest):
    """

    The SIMPLEREQACK defines the acknowledgement response to a Simple
    CIM Operation asynchronous request. The ERROR subelement is used
    to report a fundamental error which prevented the asynchronous
    request from being initiated.

    <!ELEMENT SIMPLEREQACK (ERROR?)>
    <!ATTLIST SIMPLEREQACK
        INSTANCEID CDATA     #REQUIRED>
    """

#################################################################
# Root element
#################################################################


#################################################################
# Main function
#################################################################

tests = [

    # Root element

    CIM,                                # CIM

    # Object declaration elements

    Declaration,                        # DECLARATION
    DeclGroup,                          # DECLGROUP
    DeclGroupWithName,                  # DECLGROUP.WITHNAME
    DeclGroupWithPath,                  # DECLGROUP.WITHPATH
    QualifierDeclaration,               # QUALIFIER.DECLARATION
    Scope,                              # SCOPE

    # Object value elements

    Value,                              # VALUE
    ValueArray,                         # VALUE.ARRAY
    ValueReference,                     # VALUE.REFERENCE
    ValueRefArray,                      # VALUE.REFARRAY
    ValueObject,                        # VALUE.OBJECT
    ValueNamedInstance,                 # VALUE.NAMEDINSTANCE
    ValueNamedObject,                   # VALUE.NAMEDOBJECT
    ValueObjectWithLocalPath,           # VALUE.OBJECTWITHLOCALPATH
    ValueObjectWithPath,                # VALUE.OBJECTWITHPATH
    ValueNull,                          # VALUE.NULL

    # Object naming and locating elements

    NamespacePath,                      # NAMESPACEPATH
    LocalNamespacePath,                 # LOCALNAMESPACEPATH
    Host,                               # HOST
    Namespace,                          # NAMESPACE
    ClassPath,                          # CLASSPATH
    LocalClassPath,                     # LOCALCLASSPATH
    ClassName,                          # CLASSNAME
    InstancePath,                       # INSTANCEPATH
    LocalInstancePath,                  # LOCALINSTANCEPATH
    InstanceName,                       # INSTANCENAME
    ObjectPath,                         # OBJECTPATH
    KeyBinding,                         # KEYBINDING
    KeyValue,                           # KEYVALUE

    # Object definition elements

    Class,                              # CLASS
    Instance,                           # INSTANCE
    Qualifier,                          # QUALIFIER
    Property,                           # PROPERTY
    PropertyArray,                      # PROPERTY.ARRY
    PropertyReference,                  # PROPERTY.REFERENCE
    Method,                             # METHOD
    Parameter,                          # PARAMETER
    ParameterReference,                 # PARAMETER.REFERENCE
    ParameterArray,                     # PARAMETER.ARRAY
    ParameterReferenceArray,            # PARAMETER.REFARRAY

    # Message elements

    Message,                            # MESSAGE
    MultiReq,                           # MULTIREQ
    MultiExpReq,                        # MULTIEXPREQ
    SimpleReq,                          # SIMPLEREQ
    SimpleExpReq,                       # SIMPLEEXPREQ
    IMethodCall,                        # IMETHODCALL
    MethodCall,                         # METHODCALL
    ExpMethodCall,                      # EXPMETHODCALL
    ParamValue,                         # PARAMVALUE
    IParamValue,                        # IPARAMVALUE
    ExpParamValue,                      # EXPPARAMVALUE
    MultiRsp,                           # MULTIRSP
    MultiExpRsp,                        # MULTIEXPRSP
    SimpleRsp,                          # SIMPLERSP
    SimpleExpRsp,                       # SIMPLEEXPRSP
    MethodResponse,                     # METHODRESPONSE
    ExpMethodResponse,                  # EXPMETHODRESPONSE
    IMethodResponse,                    # IMETHODRESPONSE
    Error,                              # ERROR
    ReturnValue,                        # RETURNVALUE
    IReturnValue,                       # IRETURNVALUE
    ResponseDestination,                # RESPONSEDESTINATION
    SimpleReqAck,                       # SIMPLEREQACK
    ]

if __name__ == '__main__':
    comfychair.main(tests)
