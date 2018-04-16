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
#
"""
A DMTF_Schema is the collection of mof files managed by the DMTF and
released as a single tested, coherent package with a defined Major, Minor,
Revision number.  The mof for these files is packaged as a single zip
file and is available on the DMTF web site.

The DMTF schema is the core set of mofs that represent the models used in
most CIM/WBEM implementations that that utilize pywbem.

The DMTFSchema class installs a DMTF MOF schema into a directory and makes
information on that installation available. Donwloads a DMTF schema defined by
its version number from the DMTF web site and expands it into a directory
defined by a constructor input parameter.

The version defined will be downloaded in the directory defined by the
'schema_dir' constructor parameter if that directory is empty does not exist
and expanded from the downloaded zip file if the expanded files do not exist.

Installation into the 'schema_dir' directory includes:

1. If necessary, creates the directory defined by schema_dir.

2. Downloads the schema from the DMTF repository into the schema_dir.

3. Expands the zip file for the mof into the directory 'mof' in the schema_dir.

To change the DMTF schema version used by the DMTFSchema class in the
same 'schema_dir':

1. Remove the directory (defined by 'schema_dir') for the existing version.

2. Recreate the DMTFSchema with the new schema version.

The DMTFSchema class also provides a method to create a MOF include file
from the DMTF Schema downloaded that includes only a subset of the classes
actually in the repository for compile into a MOF repository.
"""
import os
from zipfile import ZipFile
import six

if six.PY2:
    # pylint: disable=wrong-import-order
    from urllib2 import urlopen
else:
    # pylint: disable=wrong-import-order
    from urllib.request import urlopen


__all__ = ['DMTFSchema']


class DMTFSchema(object):
    """
    This class manages the download and install of these files into a form
    that can be used by pywbem_mock to create a class and qualifier declaration
    repository.

    It also provides tools to build repositories with DMTF schema.
    """
    def __init__(self, schema_ver, schema_dir, verbose=False):
        """
        The constructor downloads the schema if the 'schema_dir' does not exist
        and installs it into the directory defined by the 'schema_dir'
        attribute.

        If the schema is already installed it simply sets the property values so
        that the schema can be used.

        If the schema was previously downloaded but not expanded, it is
        automatically expanded (i.e. the schema/mof subdirectory is created
        and the mof files expanded into this directory.). This allows only
        the single file 'schema_mof_filename' to be persisted and the expansion
        to occur on usage which saves downloading from the DMTF repeatedly and
        saves disk space.

        Parameters:

          schema_dir (:term:`string`):
            Directory into which the DMTF schema is installed or will be
            installed.

          schema_ver  (tuple of 3 integers (x, y, z):
            Represents the DMTF the schema version in the format x.yy.z where
                x is the major version
                y is the minor version
                z is the revisions
            This MUST represent a DMTF schema that is available from the
            DMTF web site.

          verbose (:class:`py:bool`):
            If 'True' status messages are output to the console

        Raises:
            ValueError if the schema cannon be retrieved from the DMTF web site.
            ValueError or if the 'schema_dir' differs from the version of the
            schema currently set into the 'schema_dir'

        """
        self._schema_dir = schema_dir
        self._schema_mof_dir = os.path.join(self._schema_dir, 'mof')

        if not isinstance(schema_ver, tuple):
            raise ValueError('schema_ver must be tuple not %s' % schema_ver)
        if len(schema_ver) != 3:
            raise ValueError('DMTF Schema must have 3 integer components, '
                             '(major, minor, rev) not %s' % schema_ver)
        self._schema_ver = schema_ver
        self._dmtf_schema_ver = 'cim_schema_%s' % (self.schema_ver_str)
        self._mof_zip_bn = self._dmtf_schema_ver + 'Final-MOFs.zip'
        self._mof_zip_url = \
            'http://www.dmtf.org/standards/cim/cim_schema_v%s%s%s/%s' % \
            (schema_ver[0], schema_ver[1], schema_ver[2], self._mof_zip_bn)
        self._schema_mof_bld_name = self._dmtf_schema_ver + '.mof'

        self._mof_zip_filename = os.path.join(self.schema_dir, self._mof_zip_bn)
        self._schema_mof_filename = os.path.join(self.schema_mof_dir,
                                                 self._schema_mof_bld_name)

        self.verbose = verbose

        # setup the schema
        self._setup_dmtf_schema()

    @property
    def schema_ver(self):
        """
        :func:`py:tuple` of 3 integers with major version, minor version, and
        revision of the DMTF Schema installed
        """
        return self._schema_ver

    @property
    def schema_ver_str(self):
        """
        :term:`string` with the DMTF schema version in the form
        <major version>.<minor version>.<revison>.
        """
        return '%s.%s.%s' % (self.schema_ver[0], self.schema_ver[1],
                             self.schema_ver[2])

    @property
    def schema_dir(self):
        """
        :term:`string` defining the directory in which the DMTF CIM Schema
        mof is downloaded and expanded.
        """
        return self._schema_dir

    @property
    def schema_mof_dir(self):
        """
        :term:`string` defining the directory in which the DMTF CIM Schema
        mof is defined. This includes the expansion of the individual schema
        mof files.  TODO What is this good for???
        """
        return self._schema_mof_dir

    @property
    def schema_mof_filename(self):
        """
        :term:`string` defining the the path for the DMTF schema
        mof top level file name which includes the pragmas that define
        all of the files in the DMTF schema. This filename is of the
        general form
        """
        return self._schema_mof_filename

    def __str__(self):
        """
        Return a short string representation of the
        :class:`~pywbem_mock.DMTFSchema` object for human consumption.
        """

        return '%s(schema_ver=%s, schema_dir=%s, url=%s)' % \
               (self.__class__.__name__, self.schema_ver_str,
                self.schema_dir, self._mof_zip_url)

    def __repr__(self):
        """
        Return a string representation of the :class:`~pywbem_mock.DMTFSchema`
        object that is suitable for debugging.

        The properties and qualifiers will be ordered by their names in the
        result.
        """

        return '{0}(schema_ver={1}, schema_dir={2})'.format(
            self.__class__.__name__, self.schema_ver, self.schema_dir)

    def _setup_dmtf_schema(self):
        """
        Install the DMTF schema from the DMTF web site if it is not
        already installed.

        Once the schema in installed in 'schema_dir', it is no longer touched if
        this function is recalled.  Further, if the zip file is in the schema
        directory, but there no mof subdirectory, has been created
        the schema is unzipped without downloading the zip file from the
        DMTF.

        This allows the dmtf schema to be downloaded once and reused and further
        allows a much smaller footprint for the schema for repositories, etc by
        unzipping the schema zip file if it has not already been unzipped.

        Raises:
            IOError if the remote url cannot be opened.
        """
        first = [True]  # List allows setting variable from inner function

        def if_first(msg):
            """
            Inner method prints msg if var 'first' is False and verbose is
            True. This allows displaying steps that are actually executed.
            """
            if first:
                if self.verbose:
                    print("")
            first[0] = False
            if self.verbose:
                print(msg)

        if not os.path.isdir(self.schema_dir):
            if_first("Creating directory for CIM Schema archive: %s" %
                     self.schema_dir)
            os.mkdir(self.schema_dir)

        if not os.path.isfile(self._mof_zip_filename):
            if_first("Downloading CIM Schema archive from: %s" %
                     self._mof_zip_url)

            try:
                ufo = urlopen(self._mof_zip_url)
            except IOError as ie:
                os.rmdir(self.schema_dir)
                raise ValueError('Schema url %s not found. Exception: %s' %
                                 (self._mof_zip_url, ie))

            with open(self._mof_zip_filename, 'wb') as fp:
                for data in ufo:
                    fp.write(data)

        if not os.path.isdir(self.schema_mof_dir):
            if_first("Creating directory for CIM Schema MOF files: %s" %
                     self.schema_mof_dir)
            os.mkdir(self.schema_mof_dir)
        if not os.path.isfile(self._schema_mof_filename):
            if_first("Unpacking CIM Schema archive: %s" %
                     self._mof_zip_filename)

            zfp = None
            try:
                zfp = ZipFile(self._mof_zip_filename, 'r')
                nlist = zfp.namelist()
                for file_ in nlist:
                    dfile = os.path.join(self.schema_mof_dir, file_)
                    if dfile[-1] == '/':
                        if not os.path.exists(dfile):
                            os.mkdir(dfile)
                    else:
                        with open(dfile, 'w+b') as dfp:
                            dfp.write(zfp.read(file_))
            finally:
                if zfp:
                    zfp.close()

    def build_schema_mof(self, schema_classes):
        """
        Build a mof file that includes the pragmas for the DMTF schema CIM
        classes defined in 'schema_classes' using the DMTF CIM schema defined by
        the directory 'schema_dir' and the schema version defined by
        'schema_ver'.

        It builds a compilable mof string in the form:

            pragma locale ("en_US")
            pragma include ("System/CIM_ComputerSystem.mof")

        Parameters:

          schema_classes (:term:`py:list` of :term:`string`):
            These must be classes in the define DMTF schema and can be just
            a list of the leaf classes required for a working class repository.
            If the returned string is compiled, the mof compiler will search
            the directory defined by schema_dir for dependent classes.

        Returns:
            :term:`string`. valid MOF containing pragma statements defining
            all of the classes in 'schema_classes' that can be compiled with
            the MOF compiler.be used to compile the classes

        Raises:
            ValueError if classname in 'schema_classes' not in the DMTF
            schema installed
        """
        if isinstance(schema_classes, six.string_types):
            schema_classes = [schema_classes]

        schema_lines = []
        with open(self.schema_mof_filename, 'r') as f:
            schema_lines = f.readlines()
        f.close()

        output_lines = ['#pragma locale ("en_US")\n']
        for cln in schema_classes:
            test_cln = '/%s.mof' % cln
            found = False
            for line in schema_lines:
                if line.find(test_cln) != -1:
                    output_lines.append(line)
                    found = True
                    break
            if not found:
                raise ValueError('Class %s not in DMTF schema %s' %
                                 (cln, self.schema_mof_filename))

        return ''.join(output_lines)
