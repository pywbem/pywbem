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
A CIM schema is the collection of CIM qualifier declarations and CIM
classes and available  a single tested, coherent package
with a defined major, minor, update version number. The DMTF regularly
releases updates to the DMTF CIM schema that represent all of the classes
approved by the DMTF. The MOF representation of
a DMTF schema release is packaged as a single zip file and is available on the
DMTF web site ( https://www.dmtf.org/standards/cim ).

Because CIM schemas are the source of most of the classes that a WBEM server
normally implements it was important to create a simple mechanism to include
the DMTF CIM classes and qualifier declarations from a CIM schema in the
:class:`~pywbem_mock.FakedWBEMConnection` mock repository.

The :class:`~pywbem_mock.DMTFCIMSchema` class downloads the DMTF CIM schema
zip file defined by version from the DMTF web site into a defined directory,
unzips the MOF files into a subdirectory and makes this subdirectory
available as a property of the :class:`~pywbem_mock.DMTFCIMSchema` object.

The implementation of this class depends on all of the qualiifiers and
classes in the CIM schema having unique class names; this is always true for
DMTF CIM schema releases to assure that they can be installed in the same
namespace in a WBEM server repository.

Once aCIM schema is extracted into the individual MOF files it consumes
considerable space since it expands to almost 3000 files.  Therefore it is
logical to remove all of the individual MOF files when not being used and also
if the schema information is to be committed to be used in testing in an
environment like github. Therefore, a method
:meth:`~pywbem_mock.DMTFCIMSchema.clean` removes all of the MOF files from
local storage.  They are restored the next time the
:class:`~pywbem_mock.DMTFCIMSchema` object for the same version is constructed.

The DMTF maintains two versions of each released schema:

* Final - This schema does not contain any of the schema classes that are
  marked experimental.  It is considered the stable release.

* Experimental - Contains the classes in the final schema plus other
  classes that are considered experimental. It is considered less stable and
  the experimental classes with the Experimental qualifier are subject to
  incompatible changes .

:class:`~pywbem_mock.DMTFCIMSchema` will install either the final or
experimental schema depending on the value of the `use_experimental`
parameter.

Because it is usually necessary to compile only a subset of the DMTF CIM
classes into a mock repository for any test, the
:class:`~pywbem_mock.DMTFCIMSchema` class provides a
:meth:`~pywbem_mock.FakedWBEMConnection.build_schema_mof` method to create a
list of MOF pragmans that includes only a subset of the classes in the
downloaded CIM Schema. The task of listing classes to be compiled is futher
simplified because the pywbem MOF compiler searches the DMTF schema for
prerequisite classes (superclasses, reference classes, and EmbeddedInstance
classes) so that generally only the leaf CIM classes required for the
repository need to be in the class list. This speeds up the process of
compiling DMTF CIM classes for any test significantly.
"""

import warnings
import os
from zipfile import ZipFile
import shutil
import re
import six
try:
    from urllib.request import urlopen
except ImportError:  # py2
    from urllib2 import urlopen

from pywbem._utils import _format


__all__ = ['DMTFCIMSchema']


def build_schema_mof(class_names, schema_pragma_file):
    """
    Build a string that includes the ``#include pragma`` statements for the
    schema CIM classes defined in `class_names` using the CIM schema defined by
    this object.

    The class names in `class_names` can be just leaf classes. The pywbem
    MOF compiler will search for dependent classes including superclasses,
    and other classes referenced as the defined classes are compiled.

    It builds a compilable MOF string in the form::

        #pragma locale ("en_US")
        #pragma include ("System/CIM_ComputerSystem.mof")
        ...

    with a ``#pragma include`` for each classname in the `class_names`
    list.

    The resulting set of #pragma statements is in the same order as the
    original pragmas.  In some cases that could be important because the
    DMTF list is ordered to missing dependencies and conflicts between
    class mof compiles.

    Parameters:

      class_names (:term:`py:list` of :term:`string` or :term:`string`):
        These must be class names of classes in the DMTF CIM schema represented
        by the instance of :class:`~pywbem_mock.DMTFCIMSchema` object. This
        parameter can be a string if there is only a single class name to be
        included.

        If the returned string is compiled, the MOF compiler will search the
        directory defined by the path component of `schema_pragma_file` for
        classes referenced by each for class in this list including super
        classes, classed defined by reference properties, and classes defined
        by an embedded-object.

    schema_pragma_file (:term:`string`):
        File path defining a CIM schema pragma file for the set of
        CIM classes that make up a schema such as the DMTF schema.
        This file must contain a pragma statement for each of the
        classes defined in the schema.

    Returns:
        :term:`string`: Valid MOF containing pragma statements from the
        `CIM schema pragma file` for all of the classes in `schema_classes`.

    Raises:
        ValueError: If any of the classnames in `schema_classes` are not in
        the `CIM schema pragma file`.
    """
    if isinstance(class_names, six.string_types):
        class_names = [class_names]

    schema_lines = []
    with open(schema_pragma_file, 'r') as f:
        schema_lines = f.readlines()

    # Build list  classname/line number pairs
    classname_pattern = ' *#.*include.*/(.*)\\.mof'
    class_names_lc = [cln.lower() for cln in class_names]
    lines_list = []
    found_classes = []
    for line_no, line in enumerate(schema_lines, 0):
        result = re.search(classname_pattern, line)
        if result:
            cln = result.group(1)
            if cln.lower() in class_names_lc:
                lines_list.append(line_no)
                found_classes.append(cln)

    # Create list of the line numbers in schema_lines containing
    # pragmas that will be part of the build.
    classes_not_found = set(class_names) - set(found_classes)
    if classes_not_found:
        raise ValueError(
            _format("Classes {0!A} not in the CIM schema pragma file {1!A}",
                    ', '.join(classes_not_found), schema_pragma_file))

    # Sort the list so the result is in the same order as the pragmas
    # in the cim_schema pragma file.
    lines_list.sort()

    # Create list with line from pragma file for each entry in lines_list
    output_lines = [schema_lines[line_number] for line_number in lines_list]

    output_lines.insert(0, '#pragma locale ("en_US")\n')

    return ''.join(output_lines)


class DMTFCIMSchema(object):
    """
    :class:`DMTFCIMSchema` represents a DMTF CIM Schema downloaded from the
    DMTF web site.

    This class manages the download of the DMTF schema zip file and extraction
    of MOF files of DMTF CIM schema releases into a directory that can be used
    by :meth:`~pywbem_mock.FakedWBEMConnection.compile_schema_classes` to
    compile a mock repository with class and qualifier declarations from the
    schema.
    """
    def __init__(self, schema_version, schema_root_dir, use_experimental=False,
                 verbose=False):
        """
        The init method downloads the schema if the `schema_root_dir` or the
        schema zip file do not exist into the directory defined by the
        `schema_root_dir` parameter and extracts the MOF files into
        `schema_mof_dir`.

        If the schema zip file is already downloaded it simply sets the
        :class:`DMTFCIMSchema` property values.

        If the schema zip file was previously downloaded but `schema_mof_dir`
        does not exist the directory is created and the MOF files are extracted
        into this directory.

        Parameters:

          schema_version  (tuple of 3 integers (m, n, u):
            Represents the DMTF CIM schema version m.n.u where:

            * m is the DMTF CIM schema major version
            * n is the DMTF CIM schema minor version
            * u is the DMTF CIM schema update version

            This must represent a DMTF CIM schema that is available from the
            DMTF web site.

          schema_root_dir (:term:`string`):
            Path name of the schema root directory into which the DMTF CIM
            schema zip file is downloaded and in which a subdirectory for the
            extracted MOF files for the schema version defined is created

            Multiple DMTF CIM schemas may be maintained in the same
            `schema_root_dir` simultaneously because the MOF for each schema is
            extracted into a subdirectory identified by the schema version
            information See :attr:`schema_mof_dir`.

          use_experimental (:class:`py:bool`):
            If `True`, the experimental version of the defined DMTF schema is
            installed.

            If `False`, (default) the final version of the defined
            DMTF schema is installed.

          verbose (:class:`py:bool`):
            If `True`, progress messages are output to stdout as the schema is
            downloaded and expanded. Default is `False`.

        Raises:
            ValueError: if the schema cannot be retrieved from the DMTF web
              site.
            TypeError:  if the `schema_version` is not a valid tuple with 3
              integer components

        """
        if not isinstance(schema_version, tuple):
            raise TypeError(
                _format("Schema_version {v!A} must be tuple",
                        v=schema_version))
        if len(schema_version) != 3:
            raise ValueError(
                _format("DMTF Schema must have 3 integer components, "
                        "(major, minor, update version) not {v!A}",
                        v=schema_version))  # is a tuple
        for i in schema_version:
            if not isinstance(i, six.integer_types):
                raise TypeError(
                    _format("{0!A} in schema_version {v!A} not integer",
                            i, v=schema_version))  # is a tuple
        schema_type = 'Experimental' if use_experimental else 'Final'
        self._schema_version = schema_version
        self._schema_root_dir = schema_root_dir

        mof_dir = 'mof{0}{1}'.format(schema_type, self.schema_version_str)
        self._schema_mof_dir = os.path.join(self._schema_root_dir, mof_dir)

        cim_schema_version = 'cim_schema_{0}'.format(self.schema_version_str)
        mof_zip_bn = '{0}{1}-MOFs.zip'.format(cim_schema_version, schema_type)
        self._schema_zip_url = \
            'https://www.dmtf.org/sites/default/files/cim/' \
            'cim_schema_v{0}{1}{2}/{3}'. \
            format(schema_version[0], schema_version[1], schema_version[2],
                   mof_zip_bn)
        schema_mof_bld_name = cim_schema_version + '.mof'

        self._schema_zip_file = os.path.join(self._schema_root_dir, mof_zip_bn)
        self._schema_pragma_file = os.path.join(self.schema_mof_dir,
                                                schema_mof_bld_name)

        self.verbose = verbose

        # Setup the local copy of the DMTF CIM schema which may include creating
        # the schema directory, downloading the schema zip file from the DMTF
        # web site, and extracting the schema into a subdirectory of the schema
        # directory.
        self._setup_dmtf_schema()

    @property
    def schema_version(self):
        """
        :func:`py:tuple`: The DMTF CIM schema version as a tuple of 3 integers
        with major version, minor version, and update version.

        Example: (2, 49, 0) defines DMTF CIM schema version 2.49.0.
        """
        return self._schema_version

    @property
    def schema_version_str(self):
        """
        :term:`string`: The DMTF CIM schema version as a string in the form
        ``major version>.<minor version>.<update version>``.

        Example: "2.49.0" defines DMTF CIM schema version 2.49.0.
        """
        return '{0}.{1}.{2}'.format(*self.schema_version)

    @property
    def schema_root_dir(self):
        """
        :term:`string`: Path name of the directory in which the DMTF CIM
        schema zip file is downloaded. The MOF files are extracted into the
        subdirectory indicated by :attr:`schema_mof_dir`.
        """
        return self._schema_root_dir

    @property
    def schema_mof_dir(self):
        """
        :term:`string`: Path name of the directory in which the DMTF CIM Schema
        MOF files are extracted from the downloaded zip file. This property can
        be used as the MOF compiler search path for compiling classes in the
        DMTF CIM schema. This directory will also contain the
        schema pragma file.
        """
        return self._schema_mof_dir

    @property
    def schema_mof_file(self):
        """
        :term:`string`: Path name of the schema pragma file for the DMTF CIM
        schema. This file contains `#pragama include` statements for all of
        the classes and qualifier declarations of the schema.

        **Deprecated:** This property has been deprecated in pywbem 1.0.0
        in favor of :attr:`schema_pragma_file`.

        The classes are represented with one file per class, and the qualifier
        declarations are in the files `qualifiers.mof` and
        `qualifiers_optional.mof`.

        The path name of the schema pragma file is of the general form::

            <schema_mof_dir>/cim_schema_<schema_version_str>.mof

        Example::

            schemas/dmtf/moffinal2490/cim_schema_2.49.0.mof
        """
        warnings.warn("Property pywbem_mock.DMTFCIMSchema.schema_mof_file is "
                      "deprecated; it will be removed in a future pywbem "
                      "release. Use schema_pragma_file instead.",
                      DeprecationWarning, stacklevel=2)
        return self._schema_pragma_file

    @property
    def schema_pragma_file(self):
        """
        :term:`string`: Path name of the schema pragma file for the DMTF CIM
        schema. This file contains `#pragama include` statements for all of
        the classes and qualifier declarations of the schema.

        The classes are represented with one file per class, and the qualifier
        declarations are in the files `qualifiers.mof` and
        `qualifiers_optional.mof`.

        The path name of the schema pragma file is of the general form::

            <schema_mof_dir>/cim_schema_<schema_version_str>.mof

        Example::

            schemas/dmtf/moffinal2490/cim_schema_2.49.0.mof
        """
        return self._schema_pragma_file

    @property
    def schema_zip_file(self):
        """
        :term:`string`: Path name of the DMTF CIM schema zip file after being
        downloaded from the DMTF web site.
        """
        return self._schema_zip_file

    @property
    def schema_zip_url(self):
        """
        :term:`string`: URL of the DMTF CIM schema zip file that is
        downloaded from the DMTF web site.

        """
        return self._schema_zip_url

    def __str__(self):
        """
        Return a short string representation of the
        :class:`~pywbem_mock.DMTFCIMSchema` object for human consumption.
        This displays the major properties of the object.
        """

        return '{0}(schema_version_str={1}, schema_root_dir={2}, ' \
               'schema_mof_dir={3}, ' \
               'schema_pragma_file={4})'.format(
                   self.__class__.__name__,
                   self.schema_version_str,
                   self.schema_root_dir,
                   self.schema_mof_dir,
                   self.schema_pragma_file)

    def __repr__(self):
        """
        Return a string representation of the
        :class:`~pywbem_mock.DMTFCIMSchema` object that is suitable for
        debugging.
        """
        return '{0}(schema_version={1}, schema_root_dir={2}, ' \
               'schema_zip_file={3}, schema_mof_dir={4}, ' \
               'schema_pragma_file={5}, schema_zip_url={6})' \
               .format(self.__class__.__name__,
                       self.schema_version,
                       self.schema_root_dir,
                       self.schema_zip_file,
                       self.schema_mof_dir,
                       self.schema_pragma_file,
                       self.schema_zip_url)

    def _setup_dmtf_schema(self):
        """
        Install the DMTF CIM schema from the DMTF web site if it is not already
        installed. This includes downloading the DMTF CIM schema zip file from
        the DMTF web site and expanding that file into a subdirectory defined
        by `schema_mof_dir`.

        Once the schema zip file is downloaded into `schema_root_dir`, it is
        not re-downloaded if this function is recalled since DMTF CIM Schema
        releases are never modified; new update versions are released for minor
        changes. If the `schema_zip_file` is in the `schema_root_dir`
        directory, but no 'schema_mof_dir' subdirectory exists, the schema is
        unzipped.

        This allows the DMTF CIM schema zip file to be downloaded once and
        reused and the user to chose if they want to retain the extracted MOF
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

        def print_verbose(msg):
            """
            Inner method prints msg if self.verbose is `True`.
            """
            if self.verbose:
                print(msg)

        if not os.path.isdir(self.schema_root_dir):
            print_verbose(
                _format("Creating directory for CIM Schema archive: {0}",
                        self.schema_root_dir))
            os.mkdir(self.schema_root_dir)

        if not os.path.isfile(self.schema_zip_file):
            print_verbose(
                _format("Downloading CIM Schema archive from: {0}",
                        self.schema_zip_url))

            try:
                ufo = urlopen(self.schema_zip_url)
            except IOError as ie:
                os.rmdir(self.schema_root_dir)
                raise ValueError(
                    _format("DMTF Schema archive not found at url {0}: {1}",
                            self.schema_zip_url, ie))

            with open(self.schema_zip_file, 'wb') as fp:
                for data in ufo:
                    fp.write(data)

        if not os.path.isdir(self.schema_mof_dir):
            print_verbose(
                _format("Creating directory for CIM Schema MOF files: {0}",
                        self.schema_mof_dir))
            os.mkdir(self.schema_mof_dir)
        if not os.path.isfile(self._schema_pragma_file):
            print_verbose(
                _format("Unpacking CIM Schema archive: {0}",
                        self.schema_zip_file))

            zfp = None
            try:
                zfp = ZipFile(self.schema_zip_file, 'r')
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

    def build_schema_mof(self, class_names):
        """
        Build a string that includes the ``#include pragma`` statement for the
        CIM schema classes defined in `class_names` using the DMTF CIM
        schema defined by this instance of the class.

        The class names in `class_names` can be just leaf classes within the
        schema . The pywbem MOF compiler will search for dependent classes
        including superclasses, and other classes referenced as the classes are
        compiled.

        It builds a compilable MOF string in the form::

            #pragma locale ("en_US")
            #pragma include ("System/CIM_ComputerSystem.mof")
            ...

        with a ``#pragma include`` for each class name in the `class_names`
        list.

        The resulting set of #pragma statements is in the same order as the
        original pragmas.  In some cases that could be important because the
        cim schema pragma file is ordered to missing dependencies and conflicts
        between class mof compiles

        Parameters:

          class_names (:term:`py:list` of :term:`string` or :term:`string`):
            These must be class names of classes in the DMTF CIM schema
            represented by this :class:`~pywbem_mock.DMTFCIMSchema` object.
            This parameter can be a string if there is only a single class name
            to be included.

            If the returned string is compiled, the MOF compiler will search
            the directory defined by `schema_mof_dir` for classes referenced by
            each class in this list including super classes, classed defined by
            reference properties, and classes defined by an embedded-object.

        Returns:
            :term:`string`: Valid MOF containing pragma statements for
            all of the classes in `schema_classes`.

        Raises:
            ValueError: If any of the classnames in `schema_classes` are not in
              the DMTF CIM schema installed
        """
        return build_schema_mof(class_names, self.schema_pragma_file)

    def clean(self):
        """
        Remove all of the MOF files and the `schema_mof_dir` for the defined
        schema.  This is useful because while the downloaded schema is a single
        compressed zip file, it creates several thousand MOF files that take up
        considerable space.

        The next time the :class:`~pywbem_mock.DMTFCIMSchema` object for this
        `schema_version` and `schema_root_dir` is created, the MOF file are
        extracted again.
        """
        if os.path.isdir(self.schema_mof_dir):
            shutil.rmtree(self.schema_mof_dir)

    def remove(self):
        """
        The `schema_mof_dir` directory is removed if it esists and the
        `schema_zip_file` is removed if it exists. If the `schema_root_dir` is
        empty after these removals that directory is removed.
        """
        self.clean()
        if os.path.isfile(self.schema_zip_file):
            os.remove(self.schema_zip_file)
        if os.path.isdir(self.schema_root_dir) and \
                os.listdir(self.schema_root_dir) == []:
            os.rmdir(self.schema_root_dir)
