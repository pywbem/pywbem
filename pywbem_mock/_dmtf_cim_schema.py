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
A DMTF CIM schema is the collection of CIM qualifier declarations and CIM
classes managed by the DMTF and released as a single tested, coherent package
with a defined major, minor, update number.  The MOF representation of a DMTF
schema release is packaged as a single zip file and is available on the DMTF
web site.

Because the DMTF MOF schemas are the source of most of the classes that a WBEM
server would implement we felt it was important to create a simple mechanism
to include the DMTF CIM classes and qualifier declarations in the
:class:`~pywbem.FakedWBEMConnection` mock repository.

The :class:`~pywbem_mock.DMTFCIMSchema` class downloads the DMTF CIM schema MOF
(a zip file) defined by version from the DMTF web site into a defined directory,
unzips the MOF files into a subdirectory and makes the this subdirectory
available as a property of the :class:`~pywbem_mock.DMTFCIMSchema` object.

Multiple DMTF CIM schemas may be maintained in the same `schema_root_dir`
simultaneously because each schema is expanded into a subdirectory identified
by the schema version information.

NOTE: This class works only for the DMTF repository because a) it gets the
original zip file from the DMTF repository and b)the implementation depends on
the class names being unique as part of its process in
:meth:`~pywbem_mock.DMTFCIMSchema.build_mof_schema`

Once a DMTF CIM schema is expanded into the individual schema files it consumes
considerable space since it expands to almost 3000 files.  Therefore it is
logical to remove all of the individual MOF files when not being used and also
if the schema information is to be committed to be used in testing in an
environment like github. Therefore, a method
:meth:`~pywbem_mock.DMTFCIMSchema.clean` removes all of the MOF files from
local storage.  They are restored the next time the
:class:`~pywbem_mock.DMTFCIMSchema` object for the same version is constructed.

The DMTF maintains two versions of each released schema:

* Final - This schema does not contain any of the schema classes that are
  marked experimantel.  It is considered the stable release.

* Experimental - Contains the classes in the `Final` schema file plus other
  classes that are considered experimental. Typically it is considered less
  stable.

:class:`~pywbem_mock.DMTFCIMSchema` can install either the `Final` or
'experimental' schema depending on the value of the `user-experimental`
parameter.

The :class:`~pywbem_mock.DMTFCIMSchema` class also provides a
:meth:`~pywbem_mock.build_schema_mof` to create a MOF include file from the
DMTF Schema downloaded that includes only a subset of the classes actually in
the repository for compile into a MOF repository.
"""
import os
from zipfile import ZipFile
import shutil
import six

if six.PY2:
    # pylint: disable=wrong-import-order
    from urllib2 import urlopen
else:
    # pylint: disable=wrong-import-order
    from urllib.request import urlopen


__all__ = ['DMTFCIMSchema']


class DMTFCIMSchema(object):
    """
    :class:`DMTFCIMSchema` represents a DMTF CIM Schema downloaded from the
    DMTF WEB site.

    This class manages the download and install of DMTF CIM schema releases into
    a form that can be used by :class:`pywbem_mock.FakedWBEMConnection' to
    create a repository with class and qualifier declarations.
    """
    def __init__(self, schema_version, schema_root_dir, use_experimental=False,
                 verbose=False):
        """
        The constructor downloads the schema if the `schema_root_dir` or the
        schema zip file do not exist and installs it into the directory defined
        by the `schema_root_dir` parameter.

        If the schema zip file is already installed it simply sets the property
        values so that the schema can be compiled.

        If the schema zip file was previously downloaded but not expanded, it is
        expanded (i.e. the mof... subdirectory is created and the MOF files
        expanded into this directory.).

        Parameters:

          schema_version  (tuple of 3 integers (x, y, z):
            Represents the DMTF CIM schema version m.n.u where:

            * m is the DMTF CIM schema major version
            * n is the DMTF CIM schema minor version
            * u is the DMTF CIM schema update

            This MUST represent a DMTF CIM schema that is available from the
            DMTF web site.

          schema_root_dir (:term:`string`):
            Directory into which the DMTF CIM schema is installed or will be
            installed.

          use_experimental (:class:`py:bool`):
            If `True`, the experimintal version of the defined schema is
            installed.

            If `False`, (the default) the Final released version of the DMTF
            is installed.

          verbose (:class:`py:bool`):
            If `True`, progress messages are output to stdout.

        Raises:
            ValueError: if the schema cannot be retrieved
                from the DMTF web site.
            TypeError:  if the `schema_version` is not
                a valid tuple with 3 integer components

        """
        if not isinstance(schema_version, tuple):
            raise TypeError('schema_version must be tuple not %s' %
                            schema_version)
        if len(schema_version) != 3:
            raise TypeError('DMTF Schema must have 3 integer components, '
                            '(major, minor, update) not %s' % schema_version)
        schema_type = 'Experimental' if use_experimental else 'Final'
        self._schema_version = schema_version
        self._schema_root_dir = schema_root_dir

        mof_dir = 'mof%s%s' % (schema_type, self.schema_version_str)
        self._schema_mof_dir = os.path.join(self._schema_root_dir, mof_dir)

        self._dmtf_schema_version = 'cim_schema_%s' % (self.schema_version_str)
        self._mof_zip_bn = '%s%s-MOFs.zip' % (self._dmtf_schema_version,
                                              schema_type)
        self._mof_zip_url = \
            'http://www.dmtf.org/standards/cim/cim_schema_v%s%s%s/%s' % \
            (schema_version[0], schema_version[1], schema_version[2],
             self._mof_zip_bn)
        schema_mof_bld_name = self._dmtf_schema_version + '.mof'

        self._mof_zip_filename = os.path.join(self.schema_root_dir,
                                              self._mof_zip_bn)
        self._schema_mof_filename = os.path.join(self.schema_mof_dir,
                                                 schema_mof_bld_name)

        self.verbose = verbose

        # Setup the local copy of the DMTF CIM schema which may include creating
        # the schema directory, downloading the schema zip file from the DMTF
        # web site, and expanding the schema into a subdirectory of the schema
        # directory.
        self._setup_dmtf_schema()

    @property
    def schema_version(self):
        """
        :func:`py:tuple` of 3 integers with major version, minor version, and
        revision of the DMTF Schema installed. Ex (2, 49, 0) defines DMTF
        schema version 2.49.0.
        """
        return self._schema_version

    @property
    def schema_version_str(self):
        """
        :term:`string` with the DMTF CIM schema version in the form
        <major version>.<minor version>.<revison>.
        """
        return '%s.%s.%s' % (self.schema_version[0], self.schema_version[1],
                             self.schema_version[2])

    @property
    def schema_root_dir(self):
        """
        :term:`string` the directory in which the DMTF CIM Schema
        MOF is downloaded and expanded.
        """
        return self._schema_root_dir

    @property
    def schema_mof_dir(self):
        """
        :term:`string` the directory in which the DMTF CIM Schema
        MOF files are expanded from the downloaded zip file. This includes the
        expansion of the individual schema MOF files. This property is useful
        since it can be used as the MOF compiler search path for compiling
        classes in the DMTF CIM schema.
        """
        return self._schema_mof_dir

    @property
    def schema_mof_filename(self):
        """
        :term:`string` the path for the DMTF CIM schema MOF top level file
        which includes the pragmas that define all of the files in the DMTF
        schema. This is the file that the compiler uses if the complete
        schema is to be compiled. This filename is of the general form::

            cim_schema<schema_version>.mof

        For example::

            cim_schema_2.49.0.mof
        """
        return self._schema_mof_filename

    def __str__(self):
        """
        Return a short string representation of the
        :class:`~pywbem_mock.DMTFCIMSchema` object for human consumption.
        """

        return '%s(schema_version=%s, schema_root_dir=%s, url=%s)' % \
               (self.__class__.__name__, self.schema_version_str,
                self.schema_root_dir, self._mof_zip_url)

    def __repr__(self):
        """
        Return a string representation of the
        :class:`~pywbem_mock.DMTFCIMSchema` object that is suitable for
        debugging.
        """
        return '{0}(schema_version={1}, schema_root_dir={2}, ' \
               'schema_mof_dir={3}, ' \
               'schema_mof_filename={4})'.format(self.__class__.__name__,
                                                 self.schema_version,
                                                 self.schema_root_dir,
                                                 self.schema_mof_dir,
                                                 self.schema_mof_filename)

    def _setup_dmtf_schema(self):
        """
        Install the DMTF CIM schema from the DMTF web site if it is not
        already installed. This includes download from the DMTF of the
        DMTF CIM schema zip file and expansion of that file into a subdirectory
        defined by `schema_mof_dir`.

        Once the schema zip file is downloaded into `schema_root_dir`, it is no
        longer downloaded if this function is recalled since DMTF CIM Schema
        releases are never modified; they are rereleased as new update versions.
        If the schema zip file is in the schema directory, but no
        'schema_mof_dir' subdirectory exists, the schema is unzipped without
        downloading the zip file from the  DMTF.

        This allows the DMTF CIM schema zip file to be downloaded once and
        reused and the user to chose if they want to retain the expanded MOF
        files or remove them with :meth:`~pywbem_mock.DMTFCIMSchema.clean` when
        not being used.

        If the schema is to be committed a source repository such as git
        it is logical to commit only the DMTF CIM schema zip file. Creation of
        the `schema_mof_dir` subdirectory will be created when the
        :class:`pywbem_mock.DMTFCIMSchema` object is created.

        Raises:
            ValueError: If the schema cannot be retrieved from the DMTF web
              site.
            TypeError:  If the `schema_version` is not a valid tuple with 3
              integer components
        """
        first = [True]  # List allows setting variable from inner function

        def print_verbose(msg):
            """
            Inner method prints msg if var `first` is `False` and verbose is
            `True`. Then it sets first to `False`.
            This allows displaying steps that are actually executed.
            """
            if first:
                if self.verbose:
                    print("")
                first[0] = False
            else:
                if self.verbose:
                    print(msg)

        if not os.path.isdir(self.schema_root_dir):
            print_verbose("Creating directory for CIM Schema archive: %s" %
                          self.schema_root_dir)
            os.mkdir(self.schema_root_dir)

        if not os.path.isfile(self._mof_zip_filename):
            print_verbose("Downloading CIM Schema archive from: %s" %
                          self._mof_zip_url)

            try:
                ufo = urlopen(self._mof_zip_url)
            except IOError as ie:
                os.rmdir(self.schema_root_dir)
                raise ValueError('DMTF Schema archive not found at url %s: %s' %
                                 (self._mof_zip_url, ie))

            with open(self._mof_zip_filename, 'wb') as fp:
                for data in ufo:
                    fp.write(data)

        if not os.path.isdir(self.schema_mof_dir):
            print_verbose("Creating directory for CIM Schema MOF files: %s" %
                          self.schema_mof_dir)
            os.mkdir(self.schema_mof_dir)
        if not os.path.isfile(self._schema_mof_filename):
            print_verbose("Unpacking CIM Schema archive: %s" %
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
        Build a string that includes the ``#include pragmas`` for the DMTF
        schema CIM classes defined in `schema_classes` using the DMTF CIM
        schema defined by this object.

        The class names in this list can be just leaf classes. The pywbem
        mof compiler will search for dependent classes.

        It builds a compilable MOF string in the form::

            #pragma locale ("en_US")
            #pragma include ("System/CIM_ComputerSystem.mof")

        with a ``#pragma include`` for each classname in the `schema_classes`
        list

        Parameters:

          schema_classes (:term:`py:list` of :term:`string` or :term:`string`):
            These must be class names of classes in the DMTF CIM schema defined
            for this :class:`~pywbem_mock.DMTFCIMSchema` object. This parameter
            can be a string if there is only a single class name to be
            included.

            If the returned string is compiled, the MOF compiler will search
            the directory defined by `schema_mof_dir` for dependent classes.

        Returns:
            :term:`string`: Valid MOF containing pragma statements for
            all of the classes in`schema_classes`.

        Raises:
            ValueError: If any of the classnames in `schema_classes` are not in
            the DMTF CIM schema installed
        """
        if isinstance(schema_classes, six.string_types):
            schema_classes = [schema_classes]

        schema_lines = []
        with open(self.schema_mof_filename, 'r') as f:
            schema_lines = f.readlines()

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
                raise ValueError('Class %s not in DMTF CIM schema %s' %
                                 (cln, self.schema_mof_filename))

        return ''.join(output_lines)

    def clean(self):
        """
        Clean the individual MOF files from the `schema_root_dir`. This removes
        all of the individual MOF files and the mof... subdirectory for
        the defined schema.  This is useful because while the downloaded
        schema is a single compressed zip file, it creates several
        thousand MOF files that take up considerable space.

        The next time the :class:`~pywbem_mock.DMTFCIMSchema` object for this
        schema_version and `schema_root_dir` is created, the zip file is
        expanded again.
        """
        if os.path.isdir(self.schema_mof_dir):
            shutil.rmtree(self.schema_mof_dir)

    def remove(self):
        """
        If the schema has been installed it is completely removed. If
        the resulting `schema_root_dir` is empty that directory is removed also.
        """
        self.clean()
        if os.path.isfile(self._mof_zip_filename):
            os.remove(self._mof_zip_filename)
        if os.path.isdir(self.schema_root_dir) and \
                os.listdir(self.schema_root_dir) == []:
            os.rmdir(self.schema_root_dir)
