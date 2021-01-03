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

"""
:class:`~pywbem.RollbackWBEMConnection` is a WBEM connection that can commit
and roll back the operations.
"""

from __future__ import print_function, absolute_import

from ._cim_operations import WBEMConnection
from ._cim_constants import CIM_ERR_NOT_FOUND
from ._exceptions import Error, CIMError, RollbackError, \
    RollbackPreparationError

__all__ = ['RollbackWBEMConnection']


class RollbackWBEMConnection(object):
    """
    A WBEM connection that can commit and roll back the operations.

    *New in pywbem 1.2.*

    The :class:`RollbackWBEMConnection` object is initialized with a target
    WBEM connection and any WBEM operations are passed on to the target WBEM
    connection, maintaining an undo list of the inverse operations.

    The target WBEM connection can be a :class:`~pywbem.WBEMConnection` object
    or a :class:`~pywbem_mock.FakedWBEMConnection` object.

    When the :meth:`commit` method is called, the operations are committed by
    emptying the undo list.

    When the :meth:`rollback` method is called, the current undo list is used
    to perform the inverse operations in the undo list, so that a roll back is
    performed back to the last commit point. For each successful undo operation,
    the corresponding item is removed from the undo list. If all undo
    operations succeed, the undo list will be empty.

    The WBEM operation methods listed below are those that have associated
    undo operations. All other WBEM operations are passed through to the
    target connection.

    Limitations:

    * CIM method invocations (i.e. the
      :meth:`~pywbem.WBEMConnection.InvokeMethod` operation) cannot be rolled
      back for conceptual reasons. The :meth:`rollback` method will raise
      :exc:`~pywbem.RollbackError` once it encounters the undo item for that
      operation. Users that want to simply ignore CIM method invocations during
      rollback can catch that exception, detect the operation from its
      :attr:`~pywbem.RollbackError.orig_name` attribute and ignore it.

    * An enumeration session that was closed either implicitly by exhausting
      the enumeration, or explicitly via
      :meth:`~pywbem.WBEMConnection.CloseEnumeration` will not be reopened
      during a roll back. No exception is raised, though.
    """

    def __init__(self, conn):
        """
        Parameters:

          conn (:class:`~pywbem.WBEMConnection`): The target WBEM connection.
            Can also be a :class:`~pywbem_mock.FakedWBEMConnection` object.
            Must not be `None`.
        """
        if not isinstance(conn, WBEMConnection):
            raise TypeError(
                "conn argument must be a pywbem.WBEMConnection object, "
                "but is {}".format(type(conn)))

        # Target connection
        self._conn = conn

        # Undo list with items: tuple(orig_name, undo_name, undo_kwargs)
        # The items are in the original (=forward) order.
        self._undo_list = []

    @property
    def conn(self):
        """
        :class:`~pywbem.WBEMConnection`: The target WBEM connection.
        """
        return self._conn

    @property
    def undo_list(self):
        """
        list: The current undo list.

        The undo list is in the original (=forward) order, where each item is
        a tuple(orig_name, undo_name, undo_kwargs), with:

        * orig_name(string): Name of the original operation that will be undone.
        * undo_name(string): Name of the undo operation.
        * undo_kwargs(dict): Keyword arguments for the undo operation.
        """
        return self._undo_list

    def commit(self):
        """
        Commit the operations, establishing a new commit point.

        This empties the undo list.
        """
        del self.undo_list[:]  # list.clear() requires Python >=3.3

    def rollback(self):
        """
        Roll back the operations until the current commit point.

        This performs the undo operations in the current undo list in reverse
        order. For each successful undo operation, it removes the
        corresponding item from the undo list. If all undo operations succeed,
        the undo list will be empty; otherwise it will contain the remaining
        undo items.

        Raises:
          RollbackError: An undo operation had a problem.
        """
        for undo_tuple in reversed(self.undo_list):
            orig_name, undo_name, undo_kwargs = undo_tuple
            if undo_name == 'RollbackError':
                raise RollbackError(
                    orig_name=orig_name,
                    message=undo_kwargs['message'])
            undo_meth = getattr(self.conn, undo_name)
            try:
                undo_meth(**undo_kwargs)
                del self.undo_list[-1]  # Last item
            except Error as exc:
                new_exc = RollbackError(
                    orig_name=orig_name,
                    undo_name=undo_name,
                    undo_kwargs=undo_kwargs,
                    message="Cannot roll back {oop}: {uop} failed: {msg}".
                    format(oop=orig_name, uop=undo_name, msg=exc))
                new_exc.__cause__ = None
                raise new_exc
        assert not self.undo_list

    def ModifyInstance(
            self, ModifiedInstance, IncludeQualifiers=None, PropertyList=None):
        # pylint: disable=invalid-name
        """
        Call :meth:`~pywbem.WBEMConnection.ModifyInstance` and prepare the
        inverse ModifyInstance operation in the undo list.
        """

        # Get data needed for inverse operation
        try:
            original_inst = self.conn.GetInstance(
                InstanceName=ModifiedInstance.path,
                LocalOnly=False,
                IncludeQualifiers=IncludeQualifiers,
                IncludeClassOrigin=False)
            exc = None
        except Error as ex:
            exc = ex

        # Call the operation on the target connection.
        # Exceptions will perculate up and the undo list remains unchanged.
        self.conn.ModifyInstance(
            ModifiedInstance=ModifiedInstance,
            IncludeQualifiers=IncludeQualifiers,
            PropertyList=PropertyList)

        # The operation succeeded.
        # Append the inverse operation to the undo list.
        if exc:
            new_exc = RollbackPreparationError(
                "Cannot create undo operation for ModifyInstance: "
                "GetInstance failed: {}".format(exc))
            new_exc.__cause__ = None
            raise new_exc
        self.undo_list.append(
            ('ModifyInstance',
             'ModifyInstance',
             dict(
                 ModifiedInstance=original_inst,
                 IncludeQualifiers=IncludeQualifiers,
                 PropertyList=PropertyList)))

    def CreateInstance(self, NewInstance, namespace=None):
        # pylint: disable=invalid-name
        """
        Call :meth:`~pywbem.WBEMConnection.CreateInstance` and prepare the
        inverse DeleteInstance operation in the undo list.
        """

        # Call the operation on the target connection.
        # Exceptions will perculate up and the undo list remains unchanged.
        inst_path = self.conn.CreateInstance(
            NewInstance=NewInstance,
            namespace=namespace)

        # The operation succeeded.
        # Append the inverse operation to the undo list.
        self.undo_list.append(
            ('CreateInstance',
             'DeleteInstance',
             dict(
                 InstanceName=inst_path)))

        return inst_path

    def DeleteInstance(self, InstanceName):
        # pylint: disable=invalid-name
        """
        Call :meth:`~pywbem.WBEMConnection.DeleteInstance` and prepare the
        inverse CreateInstance operation in the undo list.
        """

        # Get data needed for inverse operation
        try:
            original_inst = self.conn.GetInstance(
                InstanceName=InstanceName,
                LocalOnly=False,
                IncludeQualifiers=False,
                IncludeClassOrigin=False)
            exc = None
        except Error as ex:
            exc = ex

        # Call the operation on the target connection.
        # Exceptions will perculate up and the undo list remains unchanged.
        self.conn.DeleteInstance(InstanceName=InstanceName)

        # The operation succeeded.
        # Append the inverse operation to the undo list.
        if exc:
            new_exc = RollbackPreparationError(
                "Cannot create undo operation for DeleteInstance: "
                "GetInstance failed: {}".format(exc))
            new_exc.__cause__ = None
            raise new_exc
        self.undo_list.append(
            ('DeleteInstance',
             'CreateInstance',
             dict(
                 NewInstance=original_inst,
                 namespace=InstanceName.namespace)))

    def InvokeMethod(self, MethodName, ObjectName, Params=None, **params):
        # pylint: disable=invalid-name
        """
        Call :meth:`~pywbem.WBEMConnection.InvokeMethod` and prepare a
        rollback error in the undo list (CIM method invocations cannot be
        rolled back).
        """

        # Call the operation on the target connection.
        # Exceptions will perculate up and the undo list remains unchanged.
        result = self.conn.InvokeMethod(
            MethodName=MethodName,
            ObjectName=ObjectName,
            Params=Params,
            **params)

        # The operation succeeded.
        # Append a rollback error to the undo list.
        self.undo_list.append(
            ('InvokeMethod',
             'RollbackError',
             dict(
                 message="Cannot roll back InvokeMethod: MethodName={mn}, "
                 "ObjectName={on}".format(mn=MethodName, on=ObjectName))))

        return result

    def ModifyClass(self, ModifiedClass, namespace=None):
        # pylint: disable=invalid-name
        """
        Call :meth:`~pywbem.WBEMConnection.ModifyClass` and prepare the
        inverse ModifyClass operation in the undo list.
        """

        # Get data needed for inverse operation
        try:
            original_class = self.conn.GetClass(
                ClassName=ModifiedClass.classname,
                namespace=namespace,
                LocalOnly=True,
                IncludeQualifiers=True,
                IncludeClassOrigin=True)
            exc = None
        except Error as ex:
            exc = ex

        # Call the operation on the target connection.
        # Exceptions will perculate up and the undo list remains unchanged.
        self.conn.ModifyClass(
            ModifiedClass=ModifiedClass,
            namespace=namespace)

        # The operation succeeded.
        # Append the inverse operation to the undo list.
        if exc:
            new_exc = RollbackPreparationError(
                "Cannot create undo operation for ModifyClass: "
                "GetClass failed: {}".format(exc))
            new_exc.__cause__ = None
            raise new_exc
        self.undo_list.append(
            ('ModifyClass',
             'ModifyClass',
             dict(
                 ModifiedClass=original_class,
                 namespace=namespace)))

    def CreateClass(self, NewClass, namespace=None):
        # pylint: disable=invalid-name
        """
        Call :meth:`~pywbem.WBEMConnection.CreateClass` and prepare the
        inverse DeleteClass operation in the undo list.
        """

        # Call the operation on the target connection.
        # Exceptions will perculate up and the undo list remains unchanged.
        self.conn.CreateClass(
            NewClass=NewClass,
            namespace=namespace)

        # The operation succeeded.
        # Append the inverse operation to the undo list.
        self.undo_list.append(
            ('CreateClass',
             'DeleteClass',
             dict(
                 ClassName=NewClass.classname,
                 namespace=namespace)))

    def DeleteClass(self, ClassName, namespace=None):
        # pylint: disable=invalid-name
        """
        Call :meth:`~pywbem.WBEMConnection.DeleteClass` and prepare the
        inverse CreateClass operation in the undo list.
        """

        # Get data needed for inverse operation
        try:
            original_class = self.conn.GetClass(
                ClassName=ClassName,
                namespace=namespace,
                LocalOnly=True,
                IncludeQualifiers=True,
                IncludeClassOrigin=True)
            exc = None
        except Error as ex:
            exc = ex

        # Call the operation on the target connection.
        # Exceptions will perculate up and the undo list remains unchanged.
        self.conn.DeleteClass(
            ClassName=ClassName,
            namespace=namespace)

        # The operation succeeded.
        # Append the inverse operation to the undo list.
        if exc:
            new_exc = RollbackPreparationError(
                "Cannot create undo operation for DeleteClass: "
                "GetClass failed: {}".format(exc))
            new_exc.__cause__ = None
            raise new_exc
        self.undo_list.append(
            ('DeleteClass',
             'CreateClass',
             dict(
                 NewClass=original_class,
                 namespace=namespace)))

    def SetQualifier(self, QualifierDeclaration, namespace=None):
        # pylint: disable=invalid-name
        """
        Call :meth:`~pywbem.WBEMConnection.SetQualifier` and prepare the
        inverse SetQualifier or DeleteQualifier operation in the undo list.
        """

        # Get data needed for inverse operation
        try:
            original_qualifier = self.conn.GetQualifier(
                QualifierName=QualifierDeclaration.name,
                namespace=namespace)
            exc = None
        except CIMError as ex:
            if ex.status_code == CIM_ERR_NOT_FOUND:
                original_qualifier = None
                exc = None
            else:
                exc = ex
        except Error as ex:
            exc = ex

        # Call the operation on the target connection.
        # Exceptions will perculate up and the undo list remains unchanged.
        self.conn.SetQualifier(
            QualifierDeclaration=QualifierDeclaration,
            namespace=namespace)

        # The operation succeeded.
        # Append the inverse operation to the undo list.
        if exc:
            new_exc = RollbackPreparationError(
                "Cannot create undo operation for SetQualifier: "
                "GetQualifier failed: {}".format(exc))
            new_exc.__cause__ = None
            raise new_exc
        if original_qualifier:
            # The qualifier declaration existed before, so this was a modify:
            self.undo_list.append(
                ('SetQualifier',
                 'SetQualifier',
                 dict(
                     QualifierDeclaration=original_qualifier,
                     namespace=namespace)))
        else:
            # The qualifier declaration did not exist before, so this was a
            # create:
            self.undo_list.append(
                ('SetQualifier',
                 'DeleteQualifier',
                 dict(
                     QualifierName=QualifierDeclaration.name,
                     namespace=namespace)))

    def DeleteQualifier(self, QualifierName, namespace=None):
        # pylint: disable=invalid-name
        """
        Call :meth:`~pywbem.WBEMConnection.DeleteQualifier` and prepare the
        inverse SetQualifier operation in the undo list.
        """

        # Get data needed for inverse operation
        try:
            original_qualifier = self.conn.GetQualifier(
                QualifierName=QualifierName,
                namespace=namespace)
            exc = None
        except Error as ex:
            exc = ex

        # Call the operation on the target connection.
        # Exceptions will perculate up and the undo list remains unchanged.
        self.conn.DeleteQualifier(
            QualifierName=QualifierName,
            namespace=namespace)

        # The operation succeeded.
        # Append the inverse operation to the undo list.
        if exc:
            new_exc = RollbackPreparationError(
                "Cannot create undo operation for DeleteQualifier: "
                "GetQualifier failed: {}".format(exc))
            new_exc.__cause__ = None
            raise new_exc
        self.undo_list.append(
            ('DeleteQualifier',
             'SetQualifier',
             dict(
                 QualifierDeclaration=original_qualifier,
                 namespace=namespace)))

    def EnumerateInstances(self, *args, **kwargs):
        # pylint: disable=invalid-name
        "Call :meth:`~pywbem.WBEMConnection.EnumerateInstances`"
        return self.conn.EnumerateInstances(*args, **kwargs)

    def EnumerateInstanceNames(self, *args, **kwargs):
        # pylint: disable=invalid-name
        "Call :meth:`~pywbem.WBEMConnection.EnumerateInstanceNames`"
        return self.conn.EnumerateInstanceNames(*args, **kwargs)

    def GetInstance(self, *args, **kwargs):
        # pylint: disable=invalid-name
        "Call :meth:`~pywbem.WBEMConnection.GetInstance`"
        return self.conn.GetInstance(*args, **kwargs)

    def Associators(self, *args, **kwargs):
        # pylint: disable=invalid-name
        "Call :meth:`~pywbem.WBEMConnection.Associators`"
        return self.conn.Associators(*args, **kwargs)

    def AssociatorNames(self, *args, **kwargs):
        # pylint: disable=invalid-name
        "Call :meth:`~pywbem.WBEMConnection.AssociatorNames`"
        return self.conn.AssociatorNames(*args, **kwargs)

    def References(self, *args, **kwargs):
        # pylint: disable=invalid-name
        "Call :meth:`~pywbem.WBEMConnection.References`"
        return self.conn.References(*args, **kwargs)

    def ReferenceNames(self, *args, **kwargs):
        # pylint: disable=invalid-name
        "Call :meth:`~pywbem.WBEMConnection.ReferenceNames`"
        return self.conn.ReferenceNames(*args, **kwargs)

    def ExecQuery(self, *args, **kwargs):
        # pylint: disable=invalid-name
        "Call :meth:`~pywbem.WBEMConnection.ExecQuery`"
        return self.conn.ExecQuery(*args, **kwargs)

    def IterEnumerateInstances(self, *args, **kwargs):
        # pylint: disable=invalid-name
        "Call :meth:`~pywbem.WBEMConnection.IterEnumerateInstances`"
        return self.conn.IterEnumerateInstances(*args, **kwargs)

    def IterEnumerateInstancePaths(self, *args, **kwargs):
        # pylint: disable=invalid-name
        "Call :meth:`~pywbem.WBEMConnection.IterEnumerateInstancePaths`"
        return self.conn.IterEnumerateInstancePaths(*args, **kwargs)

    def IterAssociatorInstances(self, *args, **kwargs):
        # pylint: disable=invalid-name
        "Call :meth:`~pywbem.WBEMConnection.IterAssociatorInstances`"
        return self.conn.IterAssociatorInstances(*args, **kwargs)

    def IterAssociatorInstancePaths(self, *args, **kwargs):
        # pylint: disable=invalid-name
        "Call :meth:`~pywbem.WBEMConnection.IterAssociatorInstancePaths`"
        return self.conn.IterAssociatorInstancePaths(*args, **kwargs)

    def IterReferenceInstances(self, *args, **kwargs):
        # pylint: disable=invalid-name
        "Call :meth:`~pywbem.WBEMConnection.IterReferenceInstances`"
        return self.conn.IterReferenceInstances(*args, **kwargs)

    def IterReferenceInstancePaths(self, *args, **kwargs):
        # pylint: disable=invalid-name
        "Call :meth:`~pywbem.WBEMConnection.IterReferenceInstancePaths`"
        return self.conn.IterReferenceInstancePaths(*args, **kwargs)

    def IterQueryInstances(self, *args, **kwargs):
        # pylint: disable=invalid-name
        "Call :meth:`~pywbem.WBEMConnection.IterQueryInstances`"
        return self.conn.IterQueryInstances(*args, **kwargs)

    def OpenEnumerateInstances(self, *args, **kwargs):
        # pylint: disable=invalid-name
        "Call :meth:`~pywbem.WBEMConnection.OpenEnumerateInstances`"
        return self.conn.OpenEnumerateInstances(*args, **kwargs)

    def OpenEnumerateInstancePaths(self, *args, **kwargs):
        # pylint: disable=invalid-name
        "Call :meth:`~pywbem.WBEMConnection.OpenEnumerateInstancePaths`"
        return self.conn.OpenEnumerateInstancePaths(*args, **kwargs)

    def OpenAssociatorInstances(self, *args, **kwargs):
        # pylint: disable=invalid-name
        "Call :meth:`~pywbem.WBEMConnection.OpenAssociatorInstances`"
        return self.conn.OpenAssociatorInstances(*args, **kwargs)

    def OpenAssociatorInstancePaths(self, *args, **kwargs):
        # pylint: disable=invalid-name
        "Call :meth:`~pywbem.WBEMConnection.OpenAssociatorInstancePaths`"
        return self.conn.OpenAssociatorInstancePaths(*args, **kwargs)

    def OpenReferenceInstances(self, *args, **kwargs):
        # pylint: disable=invalid-name
        "Call :meth:`~pywbem.WBEMConnection.OpenReferenceInstances`"
        return self.conn.OpenReferenceInstances(*args, **kwargs)

    def OpenReferenceInstancePaths(self, *args, **kwargs):
        # pylint: disable=invalid-name
        "Call :meth:`~pywbem.WBEMConnection.OpenReferenceInstancePaths`"
        return self.conn.OpenReferenceInstancePaths(*args, **kwargs)

    def OpenQueryInstances(self, *args, **kwargs):
        # pylint: disable=invalid-name
        "Call :meth:`~pywbem.WBEMConnection.OpenQueryInstances`"
        return self.conn.OpenQueryInstances(*args, **kwargs)

    def PullInstancesWithPath(self, *args, **kwargs):
        # pylint: disable=invalid-name
        "Call :meth:`~pywbem.WBEMConnection.PullInstancesWithPath`"
        return self.conn.PullInstancesWithPath(*args, **kwargs)

    def PullInstancePaths(self, *args, **kwargs):
        # pylint: disable=invalid-name
        "Call :meth:`~pywbem.WBEMConnection.PullInstancePaths`"
        return self.conn.PullInstancePaths(*args, **kwargs)

    def PullInstances(self, *args, **kwargs):
        # pylint: disable=invalid-name
        "Call :meth:`~pywbem.WBEMConnection.PullInstances`"
        return self.conn.PullInstances(*args, **kwargs)

    def CloseEnumeration(self, *args, **kwargs):
        # pylint: disable=invalid-name
        "Call :meth:`~pywbem.WBEMConnection.CloseEnumeration`"
        return self.conn.CloseEnumeration(*args, **kwargs)

    def EnumerateClasses(self, *args, **kwargs):
        # pylint: disable=invalid-name
        "Call :meth:`~pywbem.WBEMConnection.EnumerateClasses`"
        return self.conn.EnumerateClasses(*args, **kwargs)

    def EnumerateClassNames(self, *args, **kwargs):
        # pylint: disable=invalid-name
        "Call :meth:`~pywbem.WBEMConnection.EnumerateClassNames`"
        return self.conn.EnumerateClassNames(*args, **kwargs)

    def GetClass(self, *args, **kwargs):
        # pylint: disable=invalid-name
        "Call :meth:`~pywbem.WBEMConnection.GetClass`"
        return self.conn.GetClass(*args, **kwargs)

    def EnumerateQualifiers(self, *args, **kwargs):
        # pylint: disable=invalid-name
        "Call :meth:`~pywbem.WBEMConnection.EnumerateQualifiers`"
        return self.conn.EnumerateQualifiers(*args, **kwargs)

    def GetQualifier(self, *args, **kwargs):
        # pylint: disable=invalid-name
        "Call :meth:`~pywbem.WBEMConnection.GetQualifier`"
        return self.conn.GetQualifier(*args, **kwargs)
