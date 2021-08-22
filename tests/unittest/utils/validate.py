#
# (C) Copyright 2004,2005 Hewlett-Packard Development Company, L.P.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
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
# Author: Tim Potter <tpot@hp.com>
#

"""
Utility function for validation of XML strings against the CIM-XML DTD.

The CIM-XML DTD is defined in DSP0201 as a text standard that shows the DTD
in the text. DSP0203 is the complete DTD, but is provided only for convenience.
In case of differences, DSP0201 overrules DSP0203.

Note: The CIM_DTD_V22.dtd file used for DTD checking by pywbem for some time
      is a preliminary version that contained a few elements that were never
      released as a DMTF standard:
        TABLE, TABLEROW, TABLEROW.DECLARATION, TABLECELL.DECLARATION,
        TABLECELL.REFERENCE, RESPONSEDESTINATION, SIMPLEREQACK.

Note: Changes in DSP0203 2.3.1, compared to 2.2.0 (final):
      - SIMPLERSP: Removed child SIMPLEREQACK, to fix a an incompletely removed
        left-over from the preliminary version of 2.2.
      - RETURNVALUE: Made its child elements optional, in support of void
        CIM methods.
      - IMETHODRESPONSE: Added PARAMVALUE*, in support of pull operations. Note
        this was inconsistent and IPARAMVALUE should have been used.
      - PARAMVALUE: Added choices for children CLASSNAME, CLASS, INSTANCE,
        VALUE.NAMEDINSTANCE, in support of pull operations (became necessary
        as a result of using PARAMVALUE in IMETHODRESPONSE).
      - ENUMERATIONCONTEXT: Added this element in support of pull operations.

Note: Changes in DSP0203 2.4.0, compared to 2.3.1:
      - KEYVALUE: Its TYPE attribute is now required. (incompatible!)
      - SIMPLEREQ: Added optional CORRELATOR* children, in support of operation
        correlation.
      - CORRELATOR: Added this element in support of operation correlation.
      - PARAMVALUE: Added choice for children INSTANCENAME* in support of
        pull operations (became necessary as a result of using PARAMVALUE in
        IMETHODRESPONSE).
      - IRETURNVALUE: Added choice for children VALUE.INSTANCEWITHPATH* in
        support of pull operations.
      - ENUMERATIONCONTEXT: Removed this element again, because representation
        of enumeration context value in pull operations was changed to string
        in DSP0200.
      - EXPPARAMVALUE: Removed incorrect children VALUE, METHODRESPONSE,
        IMETHODRESPONSE, because they were not needed.
"""

from __future__ import print_function, absolute_import

import os
import re
from subprocess import Popen, PIPE, STDOUT

from formencode import doctest_xml_compare
from lxml import etree

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
pywbem = import_installed('pywbem')
from pywbem._utils import _ensure_bytes, _ensure_unicode  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


# Version of DSP0201 to validate against
DTD_VERSION = (2, 3, 1)

# CIM-XML DTD file to validate against
DTD_FILE = os.path.join(
    'tests', 'dtd', 'DSP0203_{v[0]}.{v[1]}.{v[2]}.dtd'.format(v=DTD_VERSION))


class CIMXMLValidationError(Exception):
    """
    Exception indicating a CIM-XML validation error.
    """
    pass


def validate_cim_xml(cim_xml_str, root_elem_name=None):
    """
    Validate a CIM-XML string against the CIM-XML DTD, optionally
    requiring a particular XML root element.

    If the validation succeeds, the function returns. Otherwise,
    `CIMXMLValidationError` is raised and its exception message is the
    (possible multi-line) output of the `xmllint` command.

    Parameters:

      cim_xml_str (string): CIM-XML string to be validated.

      root_elem_name (string): Name of XML element that is expected as the root
        element in the CIM-XML string to be validated.
        `None` means no checking for a particular root element is performed.

    Raises:

      CIMXMLValidationError: CIM-XML validation error
    """

    # The DOCTYPE instruction needs the DTD file with forward slashes.
    # Also, the xmllint used on Windows requires forward slashes and complains
    # with "Could not parse DTD tests\dtd\DSP0203_2.3.1.dtd" if invoked
    # with backslashes.
    dtd_file_fw = DTD_FILE.replace('\\', '/')

    # Make sure the validator checks the specified root element, if any
    if root_elem_name is not None:
        cim_xml_str = u'<!DOCTYPE {0} SYSTEM "{1}">\n{2}'. \
            format(root_elem_name, dtd_file_fw, cim_xml_str)
        xmllint_cmd = 'xmllint --valid --noout -'
    else:
        xmllint_cmd = 'xmllint --dtdvalid {0} --noout -'.format(dtd_file_fw)

    # pylint: disable=consider-using-with
    p = Popen(xmllint_cmd, stdout=PIPE, stderr=STDOUT, stdin=PIPE, shell=True)

    cim_xml_str = _ensure_bytes(cim_xml_str)
    p.stdin.write(cim_xml_str)
    p.stdin.close()

    status = p.wait()
    if status != 0:
        out_lines = p.stdout.readlines()
        p.stdout.close()
        output = _ensure_unicode(b'\n'.join(out_lines))
        raise CIMXMLValidationError(output)

    p.stdout.close()


def _xml_semantic_compare(left_xml_str, right_xml_str):
    """
    Compare two XML strings semantically to ensure the content is the same.
    """
    # Reasons for using lxml.etree instead of Python's xml.etree.ElementTree
    # (ET):
    # - The XML strings do not contain an XML directive specifying the
    #   encoding, and the encoding parameter of ET.XMLParser() does not seem
    #   to work.
    # - ET.fromstring() and ET.XML() do not handle byte strings in Python 2.x
    #   (see bugs.python.org/issue11033), so a manual conversion to unicode
    #   would be needed.
    # Note: lxml.etree.fromstring() has issues with unicode strings as input,
    # so we pass UTF-8 encoded byte strings. See lxml bug
    # https://bugs.launchpad.net/lxml/+bug/1902364.
    left_xml = etree.fromstring(_ensure_bytes(left_xml_str))
    right_xml = etree.fromstring(_ensure_bytes(right_xml_str))
    return doctest_xml_compare.xml_compare(left_xml, right_xml)


def validate_cim_xml_obj(obj, obj_xml_str, exp_xml_str):
    """
    Validate a CIM-XML string of a CIM object against an expected CIM-XML
    string and against the CIM-XML DTD.

    Parameters:

      obj (CIM object): The CIM object that belongs to the CIM-XML string,
       just for reporting purposes.

      obj_xml_str (string): The CIM-XML string to be validated.

      exp_xml_str (string): The expected CIM-XML string.
    """

    assert _xml_semantic_compare(obj_xml_str, exp_xml_str), \
        "Unexpected XML string (comparing at XML level):\n" \
        "Actual:   {0!r}\n" \
        "Expected: {1!r}\n".format(obj_xml_str, exp_xml_str)

    m = re.match(r'^<([^ >]+)', exp_xml_str)
    assert m is not None, \
        "Testcase issue: Cannot determine root element from expected " \
        "CIM-XML string:\n{0}".format(exp_xml_str)
    root_elem_name = m.group(1)

    try:
        validate_cim_xml(obj_xml_str, root_elem_name)
    except CIMXMLValidationError as exc:
        raise AssertionError(
            "DTD validation of CIM-XML for {0} object failed:\n"
            "{1}\n"
            "Required XML root element: {2}\n"
            "CIM-XML string:\n"
            "{3}".
            format(type(obj), exc, root_elem_name, obj_xml_str))


def assert_xml_equal(act_xml_str, exp_xml_str):
    """
    Assert that an actual XML string and an expected XML string are equal.

    Equality of two XML elements is defined by:
    - equal name
    - equal set of attributes (in any order)
    - equal set of child elements (in order)
    - equal text content (case sensitive)

    Equality of two XML attributes is defined by:
    - equal name
    - equal value (case sensitive)

    Parameters:

      act_xml_str (string): The actual XML string.

      exp_xml_str (string): The expected XML string.
    """

    assert _xml_semantic_compare(act_xml_str, exp_xml_str), \
        "Unexpected XML element (XML attribute order does not matter):\n" \
        "Actual:   {0!r}\n" \
        "Expected: {1!r}\n".format(act_xml_str, exp_xml_str)
