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
        TABLECELL.REFERENCE, RESPONSEDESTINATION.

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
import os.path
import re
from subprocess import Popen, PIPE, STDOUT

from pywbem._utils import _ensure_bytes, _ensure_unicode

# CIM-XML DTD file to validate against
DTD_FILE = os.path.join('tests', 'dtd', 'DSP0203_2.3.1.dtd')

# TODO: The DTD 2.4.0 requires the TYPE attribute on the KEYVALUE elements,
#       and this causes some tests in test_cim_xml.py to fail. Fix them.


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

    p = Popen(xmllint_cmd, stdout=PIPE, stderr=STDOUT, stdin=PIPE, shell=True)

    cim_xml_str = _ensure_bytes(cim_xml_str)
    p.stdin.write(cim_xml_str)
    p.stdin.close()

    status = p.wait()
    if status != 0:
        out_lines = p.stdout.readlines()
        output = _ensure_unicode(b'\n'.join(out_lines))
        raise CIMXMLValidationError(output)


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

    assert obj_xml_str == exp_xml_str

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
