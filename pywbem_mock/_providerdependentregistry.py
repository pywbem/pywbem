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

"""
This module defines the ProviderDependentRegistry class.
"""

import os
import six
from pywbem._utils import _format

__all__ = ['ProviderDependentRegistry']


class ProviderDependentRegistry(object):
    """
    A registry for provider dependent files in context of a mock script.

    *New in pywbem 1.1 as experimental and finalized in 1.2.*

    This registry allows registering additional dependent files in context of
    a mock script, and to look them up again.

    The registry works with the path names of the mock script and dependent
    files and normalizes these path names as follows:

    * The path is relative to the user's home directory, if possible. If
      not possible (i.e. on Windows when on a different drive than the home
      directory), the path is absolute.
    * The path does not contain redundant path separators or same-level or
      up-level directories.
    * On case insensitive file systems, the lexical case is normalized to
      lower case.
    * The native path seprarators of the operating system are used.
    """

    def __init__(self):
        # Dictionary of registered provider dependent files.
        # Key: Normalized path name of mock script.
        # Value: List of normalized path names of provider dependent files.
        self._registry = {}

    def __repr__(self):
        return _format(
            "ProviderDependentRegistry(registry={s._registry})",
            s=self)

    @staticmethod
    def _normpath(path):
        """
        Return the input file or directory path in a normalized version,
        as described in the class docstring.
        """
        home_dir = os.path.expanduser('~')
        try:
            normpath = os.path.relpath(path, home_dir)
        except ValueError:
            # On Windows, os.path.relpath() raises ValueError when the paths
            # are on different drives
            normpath = path
        return os.path.normcase(os.path.normpath(normpath))

    @staticmethod
    def _cwdpath(normpath):
        """
        Return the normalized input file or directory path such that it is
        accessible from the current working directory.
        """
        if os.path.isabs(normpath):
            cwdpath = normpath
        else:
            # If relative, it is always relative to the user's home directory
            home_dir = os.path.expanduser('~')
            cwdpath = os.path.join(home_dir, normpath)
            try:
                cwdpath = os.path.relpath(cwdpath)
            except ValueError:
                # On Windows, os.path.relpath() raises ValueError when the paths
                # are on different drives
                pass
        return cwdpath

    def add_dependents(self, mock_script_path, dependent_paths):
        # pylint: disable=line-too-long
        """
        Add dependent files to the registry, in context of a mock script.

        Parameters:

          mock_script_path (:term:`string`):
            Path name of the mock script. May be relative or absolute, and will
            be normalized to look up the registered dependents.

          dependent_paths (:term:`string` or :class:`py:list` of :term:`string`):
            Path name(s) of provider dependent files to be registered.
            May be relative or absolute, and will be normalized when
            registering them.
        """  # noqa: E501
        # pylint: enable=line-too-long

        if isinstance(dependent_paths, six.string_types):
            dependent_paths = [dependent_paths]

        mock_script_normpath = self._normpath(mock_script_path)

        dependent_normpaths = []
        for path in dependent_paths:
            dependent_normpaths.append(self._normpath(path))

        if mock_script_normpath not in self._registry:
            self._registry[mock_script_normpath] = []
        self._registry[mock_script_normpath].extend(dependent_normpaths)

    def iter_dependents(self, mock_script_path):
        """
        Iterate through the path names of the dependent files that are
        registered for a mock script.

        If the mock script is not registered, the iteration is empty.

        The iterated path names are the normalized path names, but with a path
        that makes them accessible from within the current directory.

        Parameters:

          mock_script_path (:term:`string`):
            Path name of the mock script. May be relative or absolute, and will
            be normalized to look up the registered dependents.

        Returns:

          :term:`iterator`: A generator iterator for the path names of the
          dependent files.
        """
        mock_script_normpath = self._normpath(mock_script_path)
        if mock_script_normpath not in self._registry:
            return  # yield empty
        for dep_normpath in self._registry[mock_script_normpath]:
            dep_path = self._cwdpath(dep_normpath)
            yield dep_path

    def load(self, other):
        """
        Replace the data in this object with the data from the other object.

        This is used to restore the object from a serialized state, without
        changing its identity.
        """
        # pylint: disable=protected-access
        self._registry = other._registry
