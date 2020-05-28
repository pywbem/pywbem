#
# (C) Copyright 2018 InovaDevelopment.comn
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
# Author: Karl Schopmeyer <inovadevelopment.com>
#

"""
Mock support for the WBEMConnection class that adds the methods that
process a class by incorporating any inherited qualifiers, properties, methods,
and parameters from the superclass so that the class contains all of the
properties, methods, parameters, and qualifiers that reflect this inheritance
and has the class_origin attribute and the propagated attribute correctly set
in the resulting resolved class.

This resolves the combination of the class ancestry with the definition of the
new class to create a what the user expects in the results from get_class, etc.

NOTE: The repository methods will determine when a class is resolved, as it
is inserted into the repository by CreateClass or as it is removed with the
GetClass or EnumerateClass methods.

For documentation, see mocksupport.rst.
"""

from __future__ import absolute_import, print_function

import six

from pywbem import CIMError, CIM_ERR_INVALID_PARAMETER, CIM_ERR_NOT_FOUND, \
    CIM_ERR_INVALID_SUPERCLASS, CIMParameter, CIMMethod, CIMProperty

from pywbem._utils import _format


class ResolverMixin(object):  # pylint: disable=too-few-public-methods
    """
    Mixin class that adds the methods for resolving class and the properties,
    methods, and parameters that are contained in the classes to be useful
    in the repository.

    As classes are passed to the create_class method or through the compiler
    into the mock repository they are incomplete (they define the properties
    and methods of the defined class as well as a possible superclass
    definition, and qualifiers (ex. override) that define relationships with
    superclasses). When a user requests or other methods like getinstance uses
    a class from the repository they depend on all of the properties, methods,
    parameters, and qualifiers to be properly resolved so that the class is
    viewed in total. This requires further processing (resolution) to fit into
    the repository including:

    1. Inheritance of properties and methods from superclasses.

    2. Validation that the class is legally defined and that the dependences
       exist.

    3. Consolidation of superclass definitions (properties, methods, qualifiers)
       into the class.

    4. Setting of the characteristics of property, method, and qualifier
       attributes such as class_origin, and propagated properties.

    """
    @staticmethod
    def _test_qualifier_decl(qualifier, qualifier_store, namespace):
        """
        Test that qualifier is in repo and valid.
        """
        if qualifier_store is None:
            return
        if not qualifier_store.object_exists(qualifier.name):
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("Qualifier declaration {0!A} required by CreateClass "
                        "not found in namespace {1!A}.",
                        qualifier.name, namespace))

    @staticmethod
    def _validate_qualifiers(qualifier_list, qualifier_store, new_class, scope):
        """
        Validate a list of qualifiers against the Qualifier decl in the
        repository.

        1. Whether it is declared (can be obtained from the declContext).
        2. Whether it has the same type as the declaration.
        3. Whether the qualifier is valid for the given scope.
        4. Whether the qualifier can be overridden.
        5. Whether the qualifier should be propagated to the subclass.
        """
        for qname, qvalue in qualifier_list.items():
            if not qualifier_store.object_exists(qname):
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Qualifier {0!A} used in new class {1!A} "
                            "has no qualifier declaration in repository.",
                            qname, new_class.classname))
            q_decl = qualifier_store.get(qname)
            if qvalue.type != q_decl.type:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Qualifier {0!A} used in new class {1!A} has "
                            "invalid type {2!A} (Qualifier declaration type: "
                            "{3!A}).",
                            qname, new_class.classname, qvalue.type,
                            q_decl.type))
            if scope not in q_decl.scopes and 'ANY' not in q_decl.scopes:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Qualifier {0!A} in new class {1!A} is used in "
                            "invalid scope {2!A} (Qualifier declaration "
                            "scopes: {3})",
                            qname, new_class.classname, scope, q_decl.scopes))

    @staticmethod
    def _init_qualifier(qualifier, qualifier_store):
        """
        Initialize the flavors of a qualifier from the qualifier repo and
        initialize propagated.
        """
        qual_dict_entry = qualifier_store.get(qualifier.name)
        qualifier.propagated = False
        if qualifier.tosubclass is None:
            if qual_dict_entry.tosubclass is None:
                qualifier.tosubclass = True
            else:
                qualifier.tosubclass = qual_dict_entry.tosubclass
        if qualifier.overridable is None:
            if qual_dict_entry.overridable is None:
                qualifier.overridable = True
            else:
                qualifier.overridable = qual_dict_entry.overridable
        if qualifier.translatable is None:
            qualifier.translatable = qual_dict_entry.translatable

    @staticmethod
    def _init_qualifier_decl(qualifier_decl, qualifier_store):
        """
        Initialize the flavors of a qualifier declaration if they are not
        already set.
        """
        assert qualifier_store.object_exists(qualifier_decl.name)
        if qualifier_decl.tosubclass is None:
            qualifier_decl.tosubclass = True
        if qualifier_decl.overridable is None:
            qualifier_decl.overridable = True
        if qualifier_decl.translatable is None:
            qualifier_decl.translatable = False

    def _resolve_objects(self, new_objects, superclass_objects, new_class,
                         superclass, classrepo, qualifier_store, type_str,
                         verbose=None):
        """
        Resolve a dictionary of objects where the objects can be CIMProperty,
        CIMMethod, or CIMParameter.  This method resolves each of the objects
        in the dictionary, using the superclass if it is defined.
        """

        if not superclass:
            for new_obj in six.itervalues(new_objects):
                self._set_new_object(new_obj, None, new_class, None,
                                     qualifier_store,
                                     False, type_str)
            return

        # Process objects if superclass exists
        for obj_name, new_obj in six.iteritems(new_objects):
            # If obj_name not in superclass, set into new class
            if obj_name not in superclass_objects:
                self._set_new_object(new_obj, None, new_class,
                                     superclass, qualifier_store,
                                     False, type_str)
                continue

            # If obj_name in superclass_objects
            if 'Override' not in new_objects[obj_name].qualifiers:
                if not isinstance(new_objects[obj_name], CIMParameter):
                    raise CIMError(
                        CIM_ERR_INVALID_PARAMETER,
                        _format("{0} {1!A} in {2!A} duplicates {0} in "
                                "{3!A} without override.",
                                type_str, obj_name, new_class.classname,
                                superclass.classname))

                # TODO need to finish this.  For now let parameter slide
                continue

            # process object override
            # get override name
            override_name = new_objects[obj_name].qualifiers["override"].value
            if isinstance(new_obj, (CIMParameter, CIMProperty)):
                if new_obj.type == 'reference':
                    if override_name != obj_name:
                        raise CIMError(
                            CIM_ERR_INVALID_PARAMETER,
                            _format("Invalid new_class reference "
                                    "{0} {1!A}. in class {2!A}"
                                    "Override must not change {0} "
                                    "name but override name is {3!A}",
                                    type_str, obj_name, superclass.classname,
                                    override_name))
            try:
                super_obj = superclass_objects[override_name]
            except KeyError:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Invalid new_class override  {0} {1!A}. in class "
                            "{2!A}. Override name {3!A}} not found in  {3!A}.",
                            type_str, obj_name, new_class.classname,
                            override_name, superclass.classname))

            # Test if new object characteristics consistent with
            # requirements for that object type
            if isinstance(super_obj, CIMProperty):
                if super_obj.type != new_obj.type \
                    or super_obj.is_array != new_obj.is_array \
                        or super_obj.embedded_object != \
                        new_obj.embedded_object:
                    raise CIMError(
                        CIM_ERR_INVALID_PARAMETER,
                        _format("Invalid new_class property {0!A}. "
                                "Does not match overridden property "
                                "{1!A} in class {2!A}",
                                obj_name, super_obj.name,
                                superclass.classname))
            elif isinstance(super_obj, CIMMethod):
                if super_obj.return_type != new_obj.return_type:
                    raise CIMError(
                        CIM_ERR_INVALID_PARAMETER,
                        _format("Invalid new_class method {0!A}. "
                                "Mismatch method  return typein "
                                "class {1!A}.", obj_name,
                                superclass.classname))
            elif isinstance(super_obj, CIMParameter):
                if super_obj.type != new_obj.type or \
                   super_obj.is_array != new_obj.is_array or \
                   super_obj.array_size != new_obj.array_size or \
                   super_obj.embedded_object != new_obj.embedded_object:
                    mname = None
                    raise CIMError(
                        CIM_ERR_INVALID_PARAMETER,
                        _format("Invalid new_class parameter "
                                "{0!A} param {1!A}. "
                                "Does not match signature of "
                                "overridden method parameters "
                                "in class {2!A}.", mname, obj_name,
                                superclass.classname))
            else:
                # This is our programming error
                assert True, "Invalid Type {0}" .format(type(super_obj))

            self._set_new_object(new_obj, super_obj,
                                 new_class,
                                 superclass, qualifier_store,
                                 True, type_str)

            # if type is method, resolve the parameters.
            if isinstance(new_obj, CIMMethod):
                self._resolve_objects(
                    new_obj.parameters,
                    superclass_objects[new_obj.name].parameters,
                    new_class,
                    superclass, classrepo, qualifier_store,
                    "Parameter", verbose=verbose)

        # Copy objects from from superclass that are not in new_class
        # Placed after loop with items in new_object so they are not part
        # of that loop.
        for obj_name, obj_value in six.iteritems(superclass_objects):
            if obj_name not in new_objects:
                new_value = obj_value.copy()
                new_value.propagated = True
                assert obj_value.class_origin
                new_value.class_origin = obj_value.class_origin
                for qualifier in new_value.qualifiers.values():
                    qualifier.propagated = True
                new_objects[obj_name] = new_value

    def _set_new_object(self, new_obj, inherited_obj, new_class, superclass,
                        qualifier_store, propagated, type_str):
        """
        Set the object attributes for a single object and resolve the
        qualifiers. This sets attributes for Properties, Methods, and
        Parameters.
        """
        assert isinstance(new_obj, (CIMMethod, CIMProperty, CIMParameter))
        if inherited_obj:
            inherited_obj_qual = inherited_obj.qualifiers
        else:
            inherited_obj_qual = None

        if propagated:
            assert superclass is not None

        new_obj.propagated = propagated
        if propagated:
            assert inherited_obj is not None
            new_obj.class_origin = inherited_obj.class_origin
        else:
            assert inherited_obj is None
            new_obj.class_origin = new_class.classname
        self._resolve_qualifiers(new_obj.qualifiers,
                                 inherited_obj_qual,
                                 new_class,
                                 superclass,
                                 new_obj.name, type_str,
                                 qualifier_store,
                                 propagate=propagated)

    def _resolve_qualifiers(self, new_quals, inherited_quals, new_class,
                            super_class, obj_name, obj_type, qualifier_store,
                            propagate=False):
        """
        Process the override of qualifiers from the inherited_quals dictionary
        to the new_quals dict following the override rules in DSP0004.
        """
        superclassname = super_class.classname if super_class else None

        # If propagate flag not set, initialize the qualfiers
        # by setting flavor defaults and propagated False
        if not propagate:
            for qname, qvalue in new_quals.items():
                self._init_qualifier(qvalue, qualifier_store)
            return

        # resolve qualifiers not in inherited object
        for qname, qvalue in new_quals.items():
            if not inherited_quals or qname not in inherited_quals:
                self._init_qualifier(qvalue, qualifier_store)

        # resolve qualifiers from inherited object
        for inh_qname, inh_qvalue in inherited_quals.items():
            if inh_qvalue.tosubclass:
                if inh_qvalue.overridable:
                    # if not in new quals, copy to new quals, else ignore
                    if inh_qname not in new_quals:
                        new_quals[inh_qname] = inherited_quals[inh_qname].copy()
                        new_quals[inh_qname].propagated = True
                    else:
                        new_quals[inh_qname].propagated = False
                        self._init_qualifier(new_quals[inh_qname],
                                             qualifier_store)

                else:  # not overridable
                    if inh_qname in new_quals:
                        # Allow for same qualifier definition in subclass
                        if new_quals[inh_qname].value != \
                                inherited_quals[inh_qname].value \
                                or \
                                new_quals[inh_qname].type != \
                                inherited_quals[inh_qname].type:
                            raise CIMError(
                                CIM_ERR_INVALID_PARAMETER,
                                _format("Invalid new_class {0!A}:{1!A} "
                                        "qualifier {2!A}. "
                                        "in class {3!A}. Not overridable ",
                                        obj_type, obj_name, inh_qname,
                                        new_class.classname))
                        new_quals[inh_qname].propagated = True

                    else:  # not in new class, add it
                        new_quals[inh_qname] = inherited_quals[inh_qname].copy()
                        new_quals[inh_qname].propagated = True

            else:  # not tosubclass, i.e. restricted.
                if inh_qname in new_quals:
                    if inh_qvalue.overridable or inh_qvalue.overridable is None:
                        new_quals[inh_qname].propagated = True

                    else:
                        raise CIMError(
                            CIM_ERR_INVALID_PARAMETER,
                            _format("Invalid qualifier object {0!A} qualifier "
                                    "{1!A} . Restricted in super class {2!A}",
                                    obj_name, inh_qname, superclassname))

    def _resolve_class(self, new_class, namespace, qualifier_store,
                       verbose=None):
        """
        Resolve the class defined by new_class by:

        1. Validating that the new class provided is a valid class.

        2. Validating the class against the repository to confirm that
           components required in the repository are in the repository, This
           includes the superclass if specified and the dependencies for
           EmbeddedInstance and reference properties.

        2. propagating any properties, methods, parameters, and qualifiers
           from the superclass if it is defined.

        """
        is_association_class = 'Association' in new_class.qualifiers

        if new_class.superclass:
            try:
                superclass = self.get_class(namespace, new_class.superclass,
                                            local_only=False,
                                            include_qualifiers=True,
                                            include_classorigin=True)
            except CIMError as ce:
                if ce.status_code == CIM_ERR_NOT_FOUND:
                    raise CIMError(
                        CIM_ERR_INVALID_SUPERCLASS,
                        _format("Superclass {0!A} for class {1!A} not found "
                                "in namespace {2!A}.",
                                new_class.superclass, new_class.classname,
                                namespace))
                raise
        else:
            superclass = None

        # Validate association qualifier matches superclass
        if is_association_class and superclass:
            if 'Association' not in superclass.qualifiers:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("New class {0!A} derived from superclass {1!A} "
                            "in namespace {3!A} which is not Association "
                            "Class .",
                            new_class.classname, new_class.superclass,
                            namespace))

        # validate no reference properties in non-association
        for new_prop in six.itervalues(new_class.properties):
            if not is_association_class and new_prop.type == 'reference':
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Reference property {0!A} not allowed on "
                            "non-association class {1!A}",
                            new_prop.name, new_class.classname))

        objects = list(new_class.properties.values())
        for meth in new_class.methods.values():
            objects += list(meth.parameters.values())

        # Validate the attributes of all qualifiers in the new class
        if qualifier_store:
            self._validate_qualifiers(new_class.qualifiers, qualifier_store,
                                      new_class, 'CLASS')
            for pvalue in new_class.properties.values():
                self._validate_qualifiers(pvalue.qualifiers, qualifier_store,
                                          new_class, 'PROPERTY')
            for mvalue in new_class.methods.values():
                self._validate_qualifiers(mvalue.qualifiers, qualifier_store,
                                          new_class, 'METHOD')
                for pvalue in mvalue.parameters.values():
                    self._validate_qualifiers(pvalue.qualifiers,
                                              qualifier_store,
                                              new_class, 'PARAMETER')

        # resolve class level qualifiers and attributes
        qualdict = superclass.qualifiers if superclass else {}
        new_class.classorigin = superclass.classname if superclass \
            else new_class.classname
        new_class.propagated = bool(superclass)
        self._resolve_qualifiers(new_class.qualifiers,
                                 qualdict,
                                 new_class,
                                 superclass,
                                 new_class.classname, 'class',
                                 qualifier_store,
                                 propagate=False)

        classrepo = self.cimrepository.get_class_store(namespace)
        # resolve properties in new class
        self._resolve_objects(new_class.properties,
                              superclass.properties if superclass else None,
                              new_class, superclass,
                              classrepo, qualifier_store, "Property",
                              verbose=verbose)

        # resolve methods and parameters in new class
        self._resolve_objects(new_class.methods,
                              superclass.methods if superclass else None,
                              new_class, superclass,
                              classrepo, qualifier_store, "Method")

        return new_class
