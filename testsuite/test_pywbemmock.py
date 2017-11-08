#!/usr/bin/env python

# (C) Copyright 2017 IBM Corp.
# (C) Copyright 2017 Inova Development Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Prototype test of using mock to enable tests of pywbemcli with pytest as
the test driver.

Creates a class for each pywbemcli subcommand.
"""
from __future__ import absolute_import, print_function
import operator

from pprint import pprint as pp  # noqa: F401

import pytest

from pywbem import CIMClass, CIMProperty, CIMInstance, \
    CIMInstanceName, CIMQualifier, CIMQualifierDeclaration, CIMError, \
    CIM_ERR_INVALID_CLASS, CIM_ERR_ALREADY_EXISTS, DEFAULT_NAMESPACE

from _pywbem_mock import FakedWBEMConnection




class TestClassOperationMock(object):
    """
    Test mocking of Class level operations
    """
    def test_get_class1(self):
        """
        Test mocking wbemconnection getClass accessed through pywbemtools
        class get

        test using Mock directly and returning a class.

        Currently fails  result <Result SystemExit(1,)>
        """
        conn = FakedWBEMConnection(verbose=True)

        c = CIMClass(
            'CIM_Foo', properties={'InstanceID':
                                   CIMProperty('InstanceID', None,
                                               type='string')})
        conn.add_cimobjects(c)
        cl = conn.GetClass('CIM_Foo')
        print('getclass returns %s' % cl.tomof())
        assert(cl == c)

    @pytest.mark.parametrize(
       "ns", [None, 'root/blah'])
    def test_get_class2(self, ns):
        """
        Test mocking wbemconnection getClass
        test using Mock directly and returning a class.
        """
        conn = FakedWBEMConnection(verbose=True)

        c = CIMClass(
            'CIM_Foo', properties={'InstanceID':
                                   CIMProperty('InstanceID', None,
                                               type='string')})
        conn.add_cimobjects(c)
        cl = conn.GetClass('CIM_Foo', namespace=ns)
        print('getclass returns %s' % cl.tomof())
        assert(cl == c)


class TestInstanceOperationMock(object):

    def test_mock_get_instance(self):
        """
        Test mocking wbemconnection getClass accessed through pywbemtools
        class get

        test using Mock directly and returning a class.

        Currently fails  result <Result SystemExit(1,)>
        """
        fake_conn = FakedWBEMConnection(verbose=True)

        inst_path = CIMInstanceName('CIM_Foo', {'Name': 'Foo'})
        i = CIMInstance('CIM_Foo',
                        properties={'Name': 'Foo', 'Chicken': 'Ham'},
                        qualifiers={'Key': CIMQualifier('Key', True)},
                        path=inst_path)
        print('created instance %r' % i)

        fake_conn.add_cimobjects(i, namespace='root/cimv2')
        print('instances in rep %s' % fake_conn.instances)

        inst = fake_conn.GetInstance(inst_path)
        print('getinstance returns %s' % inst.tomof())
        inst_path.namespace = inst.path.namespace
        assert(inst.path == inst_path)


class TestQualifierDeclarationOperationMock(object):

    def test_mock_get_qualdecl(self):
        """
        Test adding a qualifierdecl to the repository and doing a
        WBEMConnection get to retrieve it.
        """
        fake_conn = FakedWBEMConnection(verbose=False)

        q1 = CIMQualifierDeclaration('FooQualDecl1', 'uint32')

        q2 = CIMQualifierDeclaration('FooQualDecl2', 'string',
                                     value='my string')
        q_list = [q1, q2]

        fake_conn.add_cimobjects(q_list)

        rtn_q1 = fake_conn.GetQualifier('FooQualDecl1')

        print(q1.tomof())
        assert(q1 == rtn_q1)

    def test_mock_enum_qualdecl(self):
        """
        Test adding a qualifierdecl to the repository and doing a
        WBEMConnection get to retrieve it.
        """
        fake_conn = FakedWBEMConnection(verbose=False)

        q1 = CIMQualifierDeclaration('FooQualDecl1', 'uint32')

        q2 = CIMQualifierDeclaration('FooQualDecl2', 'string',
                                     value='my string')
        q_input = [q1, q2]

        fake_conn.add_cimobjects(q_input)

        q_rtn = fake_conn.EnumerateQualifiers()
        print('Qualifiers returned=============================')
        pp(q_rtn)
        for q in q_rtn:
            assert(isinstance(q, CIMQualifierDeclaration))
        # TODO sort before testing
        q_input.sort(key=lambda x: x.name)
        q_rtn.sort(key=lambda x: x.name)
        assert(q_input == q_rtn)

