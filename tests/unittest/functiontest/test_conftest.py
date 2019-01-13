"""
This test module contains test cases for testing the conftest.py module,
at least those functions that can reasonably be tested in a standalone
manner.
"""

from __future__ import print_function, absolute_import

from lxml import etree

from ...functiontest.conftest import xml_embed, xml_unembed


class Test_EmbedUnembed(object):
    """Test case for xml_embed() / xml_unembed() functions."""

    @staticmethod
    def test_unembed_simple():
        """Unembed a simple embedded instance string."""

        emb_str = b'&lt;INSTANCE NAME=&quot;C1&quot;&gt;' \
                  b'&lt;PROPERTY NAME=&quot;P1&quot;&gt;' \
                  b'&lt;VALUE&gt;V1&lt;/VALUE&gt;' \
                  b'&lt;/PROPERTY&gt;' \
                  b'&lt;/INSTANCE&gt;'

        instance_elem = xml_unembed(emb_str)

        assert instance_elem.tag == 'INSTANCE'
        assert len(instance_elem.attrib) == 1
        assert 'NAME' in instance_elem.attrib
        assert instance_elem.attrib['NAME'] == 'C1'

        assert len(instance_elem) == 1
        property_elem = instance_elem[0]
        assert property_elem.tag == 'PROPERTY'
        assert len(property_elem.attrib) == 1
        assert 'NAME' in property_elem.attrib
        assert property_elem.attrib['NAME'] == 'P1'

        assert len(property_elem) == 1
        value_elem = property_elem[0]
        assert value_elem.tag == 'VALUE'
        assert len(value_elem.attrib) == 0  # pylint: disable=len-as-condition
        assert value_elem.text == 'V1'

    @staticmethod
    def test_embed_simple():
        """Embed a simple instance."""

        instance_elem = etree.Element('INSTANCE')
        instance_elem.attrib['NAME'] = 'C1'
        property_elem = etree.SubElement(instance_elem, 'PROPERTY')
        property_elem.attrib['NAME'] = 'P1'
        value_elem = etree.SubElement(property_elem, 'VALUE')
        value_elem.text = 'V1'

        emb_str = xml_embed(instance_elem)

        exp_emb_str = b'&lt;INSTANCE NAME=&quot;C1&quot;&gt;' \
                      b'&lt;PROPERTY NAME=&quot;P1&quot;&gt;' \
                      b'&lt;VALUE&gt;V1&lt;/VALUE&gt;' \
                      b'&lt;/PROPERTY&gt;' \
                      b'&lt;/INSTANCE&gt;'

        assert emb_str == exp_emb_str
