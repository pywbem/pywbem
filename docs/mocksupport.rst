.. _`Mock support`:

Mock support
============

**Experimental:** *New in pywbem 0.12.0 as experimental.*

.. _`Overview`:

Overview
--------

The pywbem package contains the ``pywbem_mock`` subpackage which provides mock
support that enables usage of the pywbem library without a WBEM server.
This subpackage is used for testing the pywbem library itself and can be used
for the development and testing of Python programs that use the pywbem library.

The pywbem mock support contains the :class:`pywbem_mock.FakedWBEMConnection`
class that establishes a *faked connection*. That class is a subclass of
:class:`pywbem.WBEMConnection` and replaces its internal methods that use
HTTP/HTTPS to communicate with a WBEM server with methods that instead operate
on a local in-memory repository of CIM objects (the *mock repository*).

As a result, the operation methods of :class:`~pywbem_mock.FakedWBEMConnection`
are those inherited from :class:`~pywbem.WBEMConnection`, so they have the
exact same input parameters, output parameters, return values, and even most of
the raised exceptions, as when being invoked on a
:class:`~pywbem.WBEMConnection` object against a WBEM server.

Each :class:`~pywbem_mock.FakedWBEMConnection` object has its own mock
repository.
The mock repository contains the same kinds of CIM objects a WBEM server
repository contains: CIM classes, CIM instances, and CIM qualifier types
(declarations), all contained in CIM namespaces.

Because :class:`~pywbem_mock.FakedWBEMConnection` operates only on the mock
repository, the class does not have any connection- or security-related
constructor parameters.

Like :class:`~pywbem.WBEMConnection`, :class:`~pywbem_mock.FakedWBEMConnection`
has a default CIM namespace that can be set upon object creation.

:class:`~pywbem_mock.FakedWBEMConnection` has some additional methods that
provide for adding CIM classes, instances and qualifier types to its mock
repository. See :ref:`Building the mock repository` for details.

There are no setup methods to remove or modify CIM objects in the mock
repository. However, if needed, that can be done by using operation methods
such as :meth:`~pywbem.WBEMConnection.DeleteClass` or
:meth:`~pywbem.WBEMConnection.ModifyInstance`.

.. _`mock repository operation modes`:

The mock repository supports two operation modes:

* full mode: The repository must contain the classes and qualifier types that
  are needed for the operations that are invoked. This results in a behavior of
  the faked operations that is close to the behavior of the operations of a
  real WBEM server.

* lite mode: The repository does not need to contain any classes and qualifier
  types, and can be used when it contains only instances. This simplifies the
  setup of the mock repository for users, but it also affects the behavior of
  the faked instance operations to be farther away from the behavior of the
  operations of a real WBEM server. For example, the faked `EnumerateInstances`
  operation will not return instances of subclasses when `DeepInheritance` is
  set, because without looking at classes, there is no way it can find out what
  the subclasses are. And of course, class operations and qualifier operations
  that retrieve objects don't work at all if the mock repository does not
  contain them.

The operation mode of the mock repository is selected when creating
a :class:`~pywbem_mock.FakedWBEMConnection` object, through its `repo_lite`
init parameter. Full mode is the default.

The following example demonstrates setting up a faked connection, adding
several CIM objects defined in a MOF string to its mock repository, and
executing WBEM operations on the faked connection:

.. code-block:: python

    import pywbem
    import pywbem_mock

    # MOF string defining qualifiers, class, and instance
    mof = '''
        Qualifier Key : boolean = false,
            Scope(property, reference),
            Flavor(DisableOverride, ToSubclass);
        Qualifier Description : string = null,
            Scope(any),
            Flavor(EnableOverride, ToSubclass, Translatable);
        Qualifier In : boolean = true,
            Scope(parameter),
            Flavor(DisableOverride, ToSubclass);

            [Description ("This is a dumb test class")]
        class CIM_Foo {
                [Key, Description ("This is key prop")]
            string InstanceID;
                [Description ("This is some simplistic data")]
            Uint32 SomeData;
                [Description ("This is a method without parameters")]
            string Fuzzy();
                [Description ("This is a second method with parameter")]
            uint32 Delete([IN, Description('blahblah']
              boolean Immediate);
        };

        instance of CIM_Foo as $I1 { InstanceID = "I1"; SomeData=3 };
        '''

    # Create a faked connection (with a mock repository in full mode)
    conn = pywbem_mock.FakedWBEMConnection(default_namespace='root/cimv2')

    # Compile the MOF string and add its CIM objects to the default namespace
    # of the mock repository
    conn.compile_mof_string(mof)

    # Perform a few operations on the faked connection:

    # Enumerate top-level classes in the default namespace (without subclasses)
    classes = conn.EnumerateClasses();
    for cls in classes:
        print(cls.tomof())

    # Get the 'Description' qualifier type in the default namespace
    qd = conn.GetQualifier('Description')

    # Enumerate subclasses of 'CIM_Foo' in the default namespace (without subclasses)
    classes2 = conn.EnumerateClasses(classname='CIM_Foo')

    # Get 'CIM_Foo' class in the default namespace
    my_class = conn.GetClass('CIM_Foo')

    # Get a specific instance of 'CIM_Foo' in the default namespace
    inst = conn.GetInstance(CIMInstanceName('CIM_Foo', {'InstanceID': "I1"})

Pywbem mock supports:

1. All of the :class:`~pywbem.WBEMConnection` operation methods that communicate
   with the WBEM server (see below for list of operations supported and their
   limitations).
2. Multiple CIM namespaces and a default namespace on the faked connection.
3. Gathering time statistics and delaying responses for a predetermined time.
4. :class:`~pywbem.WBEMConnection` logging except that there are no HTTP entries
   in the log.

Pywbem mock does NOT support:

1. CIM-XML protocol security and security constructor parameters of
   :class:`~pywbem.WBEMConnection`.
2. Dynamic WBEM server providers in that the data for responses is from the
   mock repository that is built before the request rather than from resources
   accessed by such providers. This means there is no dynamic determination of
   property values for newly created CIM instances. Therefore, creating CIM
   instances requires that all keybinding values as well as all other property
   values must be provided as input to the
   :meth:`~pywbem.WBEMConnection.CreateInstance` operation by the user.
3. Processing of queries defined for :meth:`~pywbem.WBEMConnection.ExecQuery`
   in languages like CQL and WQL. The mocked operation parses only the very
   general portions of the query for class/instance name and properties.
4. Filter processing of the FQL (see :term:`DSP0212`) Filter Query Language
   parameter QueryFilter used by the Open... operations because it does not
   implement the parser/processor for the FQL language.  It returns the same
   data as if the filter did not exist.
5. Providing data in the trace variables for last request and last reply in
   :class:`~pywbem.WBEMConnection`: `last_request`, `last_raw_request`,
   `last_reply`, `last_raw_reply`, `last_request_len`, or `last_reply_len`.
6. Log entries for HTTP request and response in the logging support of
   :class:`~pywbem.WBEMConnection`, because it does not actually build the
   HTTP requests or responses.
7. Generating CIM indications.
8. Some of the functionality that may be implemented in real WBEM servers such
   as the `__Namespace__` class/provider or the `CIM_Namespace`
   class/provider, because these are WBEM server-specific implementations and
   not WBEM request level capabilities.  Note that such capabilities can be at
   least partly built on top of the existing capabilities by inserting
   corresponding CIM instances into the mock repository.


.. _`Faked WBEM operations`:

Faked WBEM operations
---------------------

The :class:`pywbem_mock.FakedWBEMConnection` class supports the same WBEM
operations that are supported by the :class:`pywbem.WBEMConnection` class.

These faked operations generally adhere to the behavior requirements defined in
:term:`DSP0200` for handling input parameters and returning a result.

The faked operations get the data to be returned from the mock repository of
the faked connection, and put the data provided in operation parameters that
modify objects (create, modify, and delete operations) into that mock
repository.

However, because the pywbem mock support is only a simulation of a WBEM server
and intended to be used primarily for testing, there are a number of
limitations and differences between the behavior of the faked operations and
a real WBEM server.

The descriptions below describe differences between the faked operations of
the pywbem mock support and the operations of a real WBEM server, and the
effects of the operation modes of the mock repository.


.. _`Faked instance operations`:

Faked instance operations
^^^^^^^^^^^^^^^^^^^^^^^^^

Instance operations work in both operation modes of the repository.

The operations that retrieve objects require instances in the
repository for the instances to be recovered.  We allow some of these methods to
try to return data if the class repository is empty but they may react differently
if there are classes in the repository.

- **GetInstance:** Behaves like :meth:`~pywbem.WBEMConnection.GetInstance`,
  except that the behavior of property selection for the returned instance when
  `LocalOnly` is set depends on the operation mode of the mock repository: In
  lite mode, property selection is based upon the `class_origin` attribute of
  the properties of the instance. In full mode, property selection is based
  upon the classes in which they are defined.

- **EnumerateInstances:** Behaves like
  :meth:`~pywbem.WBEMConnection.EnumerateInstances`, except for these
  differences when the mock repository is in lite mode: When `DeepInheritance`
  is set, instances of subclasses of the specified class will not be returned,
  and `LocalOnly` is ignored and treated as if it was set to `False`.

- **EnumerateInstanceNames:** Behaves like
  :meth:`~pywbem.WBEMConnection.EnumerateInstances`, except for this
  difference when the mock repository is in lite mode: When `DeepInheritance`
  is set, instances of subclasses of the specified class will not be returned.

- **CreateInstance**: Behaves like
  :meth:`~pywbem.WBEMConnection.CreateInstance`, except for these
  differences: This operation requires that all key properties are specified in
  the new instance since the mock repository has no support for dynamically
  setting key properties as a dynamic provider for the class in a real WBEM
  server might have. This operation requires that the mock repository is in
  full mode and that the class of the new instance exists in the mock
  repository. It fails with not supported if the mock repository is in lite
  mode.

- **ModifyInstance**: Behaves like
  :meth:`~pywbem.WBEMConnection.ModifyInstance`. This operation requires that
  the mock repository is in full mode and that the class of the instance exists
  in the mock repository. It fails with not supported if the mock repository is
  in lite mode.

- **DeleteInstance**: Behaves like
  :meth:`~pywbem.WBEMConnection.DeleteInstance`, except for this difference
  depending on the operation mode of the mock repository: In lite mode, the
  operation does not check for existence of the class of the instance. In full
  mode, the operation validates the existence of the class of the instance.
  In the current implementation, this operation does not check for association
  instances referencing the instance to be deleted, so any such instances
  become dangling references.

- **ExecQuery**: This operation is not currently implemented. Once implemented:
  Behaves like :meth:`~pywbem.WBEMConnection.ExecQuery`, except
  that it returns instances based on a very limited parsing of the query
  string: Generally, the SELECT and FROM clauses are evaluated, and the WHERE
  clause is ignored. The query string is not validated for correctness.
  The query language is not validated.


.. _`Faked association operations`:

Faked association operations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The faked association operations support both instance-level use and
class-level use. Class-level use requires the mock repository to be in full
mode, while instance-level use works in both operation modes of the mock
repository.

- **AssociatorNames**: Behaves like
  :meth:`~pywbem.WBEMConnection.AssociatorNames`, with the following
  exceptions and requirements:
  For class-level use, the mock repository must be in full mode and the source,
  target, and association classes and their subclasses must exist in the mock
  repository.
  For instance-level use, correct results are returned if the mock repository
  is in full mode and the the source, target, and association classes and their
  subclasses exist in the repository. More limited results are returned in lite
  mode, because the class hierarchy is not considered when selecting the
  instances to be returned.

- **Associators**: Behaves like
  :meth:`~pywbem.WBEMConnection.Associators`, with the exceptions and
  requirements described for `AssociatorNames`, above.

- **ReferenceNames**: Behaves like
  :meth:`~pywbem.WBEMConnection.ReferenceNames`, with the exceptions and
  requirements described for `AssociatorNames`, above.

- **References**: Behaves like
  :meth:`~pywbem.WBEMConnection.References`, with the exceptions and
  requirements described for `AssociatorNames`, above.


.. _`Faked method invocation operation`:

Faked method invocation operation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The faked method invocation operation (`InvokeMethod`) behaves like
:meth:`~pywbem.WBEMConnection.InvokeMethod`, but because of the nature of
`InvokeMethod`, the user must provide a callback function that performs the
actual task of the CIM method. The mock repository must be in full operation
mode.

The callback function must have the signature defined in the
:func:`~pywbem_mock.method_callback_interface` function and must be registered
with the mock repository through
:meth:`~pywbem_mock.FakedWBEMConnection.add_method_callback` for a particular
combination of namespace, class, and CIM method name.

When the callback function is invoked on behalf of an `InvokeMethod` operation,
the target object of the method invocation (class or instance) is provided to
the callback function, in addition to the method input parameters.

The callback function can access the mock repository of the faked connection
using the normal WBEM operation methods.

The callback function is expected to return a tuple consisting of two items:

* the CIM method return value, as a :term:`CIM data type` value.
* a :ref:`NocaseDict` containing any output parameters as
  :class:`~pywbem.CIMParameter` objects.

The following is an example for invoking the faked `InvokeMethod` operation
with a simple callback function.

.. code-block:: python

    import pywbem
    import pywbem_mock

    def method1_callback(conn, methodname, objectname, **params):
        """
        Callback function that demonstrates what can be done, without being
        really useful.
        """
        print('params: %r' % params )
        print('object_name %s' % objectname)

        # Access input parameters
        ip1 = params['IP1']

        # Access the mock repository through the faked connection object.
        # In case of a static CIM method, objectname is a
        :class:`~pywbem.CIMClassName` object.
        cl = conn.GetClass(objectname)

        # Set return value and output parameters
        rtn_val = 0
        op1 = CIMParameter('OP1', 'string', value='Some output data')
        return rtn_val, [op1]

    mof = '''
        Qualifier In : boolean = true,
            Scope(parameter),
            Flavor(DisableOverride, ToSubclass);

        Qualifier Key : boolean = false,
            Scope(property, reference),
            Flavor(DisableOverride, ToSubclass);

        Qualifier Out : boolean = false,
            Scope(parameter),
            Flavor(DisableOverride, ToSubclass);

        Qualifier Static : boolean = false,
            Scope(property, method),
            Flavor(DisableOverride, ToSubclass);

        class TST_Class {

            string InstanceID;

              [Static,
               Description("Static method with input and output parameters")]
            uint32 Method1(
                [IN, Description("Input param 1")]
              string IP1,
                [IN (false), OUT, Description("Output param 1")]
              string OP1);
        };
    '''

    # Create a faked connection
    conn = pywbem_mock.FakedWBEMConnection(default_namespace='root/cimv2')

    # Compile the MOF string and add its CIM objects to the default namespace
    # of the mock repository
    conn.compile_mof_string(mof)

    # Register the method callback function to the mock repository, for the
    # default namespace of the connection
    conn.add_method_callback('TST_Class', 'Method1', method1_callback)

    # Invoke static method Method1
    params = [('IP1', 'someData')]
    result = conn.InvokeMethod('Method1', 'TST_Class', Params=params)

    print('Return value: %r' % result[0])
    print('Output parameters: %r' % (result[1],))


.. _`Callback functions for faked method invocation`:

Callback functions for faked method invocation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The callback functions for faked method invocation must have the following
signature:

.. autofunction:: pywbem_mock.method_callback_interface


.. _`Faked pull operations`:

Faked pull operations
^^^^^^^^^^^^^^^^^^^^^

The faked pull operations behave like the pull operations of
:class:`~pywbem.WBEMConnection`, with the following exceptions:

- The filter query related parameters `FilterQuery` and `FilterQueryLanguage`
  are ignored and no such filtering takes place.

- The `ContinueOnError` parameter is ignored because injecting an error into
  the processing of the pull operations is not supported by the pywbem mock
  support, so no failures can happen during the processing of the pull
  operations.

- The `OperationTimeout` parameter is currently ignored. As a result, there
  will be no timeout if the
  :attr:`~pywbem_mock.FakedWBEMConnection.response_delay` property is set to a
  time larger than the `OperationTimeout` parameter.

The faked pull operations are:

- **OpenEnumerateInstances**: Behaves like
  :meth:`~pywbem.WBEMConnection.OpenEnumerateInstances`,
  with the stated exceptions.

- **OpenEnumerateInstancePaths**: Behaves like
  :meth:`~pywbem.WBEMConnection.OpenEnumerateInstancePaths`,
  with the stated exceptions.

- **OpenAssociatorInstances**: Behaves like
  :meth:`~pywbem.WBEMConnection.OpenAssociatorInstances`,
  with the stated exceptions.

- **OpenAssociatorInstancePaths**: Behaves like
  :meth:`~pywbem.WBEMConnection.OpenAssociatorInstancePaths`,
  with the stated exceptions.

- **OpenReferenceInstances**: Behaves like
  :meth:`~pywbem.WBEMConnection.OpenReferenceInstances`,
  with the stated exceptions.

- **OpenReferenceInstancePaths**: Behaves like
  :meth:`~pywbem.WBEMConnection.OpenReferenceInstancePaths`,
  with the stated exceptions.

- **OpenQueryInstances**: Behaves like
  :meth:`~pywbem.WBEMConnection.OpenQueryInstances`,
  with the stated exceptions.

- **PullInstancesWithPath**: Behaves like
  :meth:`~pywbem.WBEMConnection.PullInstancesWithPath`,
  with the stated exceptions.

- **PullInstancePaths**: Behaves like
  :meth:`~pywbem.WBEMConnection.PullInstancePaths`,
  with the stated exceptions.

- **PullInstances**: Behaves like
  :meth:`~pywbem.WBEMConnection.PullInstances`,
  with the stated exceptions.

- **CloseEnumeration**: Behaves like
  :meth:`~pywbem.WBEMConnection.CloseEnumeration`,
  with the stated exceptions.


.. _`Faked iter operations`:

Faked iter operations
^^^^^^^^^^^^^^^^^^^^^

The iter operations on a faked connection are in fact the iter operations
on :class:`~pywbem.WBEMConnection`, because they do not directly issue requests
and responses on the connection, but instead are simply a layer on top of
underlying operations. For example, `IterEnumerateInstances`
invokes either pull operations (i.e. `OpenEnumerateInstances` followed by
`PullInstancesWithPath`) or traditional operations (i.e. `EnumerateInstances`).
The use of pull vs. traditional operations is controlled via the
`use_pull_operations` init parameter of
:class:`~pywbem_mock.FakedWBEMConnection`.

The iter operations are:

- :meth:`~pywbem.WBEMConnection.IterEnumerateInstances`
- :meth:`~pywbem.WBEMConnection.IterEnumerateInstancePaths`
- :meth:`~pywbem.WBEMConnection.IterAssociatorInstances`
- :meth:`~pywbem.WBEMConnection.IterAssociatorInstancePaths`
- :meth:`~pywbem.WBEMConnection.IterReferenceInstances`
- :meth:`~pywbem.WBEMConnection.IterReferenceInstancePaths`
- :meth:`~pywbem.WBEMConnection.IterQueryInstances`


.. _`Faked class operations`:

Faked class operations
^^^^^^^^^^^^^^^^^^^^^^

Class operations only work if the mock repository is in full operation mode.

- **GetClass:** Behaves like :meth:`~pywbem.WBEMConnection.GetClass`. Requires
  that the class to be returned is in the mock repository.

- **EnumerateClasses:** Behaves like
  :meth:`~pywbem.WBEMConnection.EnumerateClasses`. Requires that the class
  specified in the `ClassName` parameter as well as the classes to be returned
  are in the mock repository.

- **EnumerateClassNames:** Behaves like
  :meth:`~pywbem.WBEMConnection.EnumerateClassNames`. Requires that the class
  specified in the `ClassName` parameter as well as the classes to be returned
  are in the mock repository.

- **CreateClass:** Behaves like
  :meth:`~pywbem.WBEMConnection.CreateClass`. Requires that the superclass of
  the new class (if it specifies one) is in the mock repository.

- **DeleteClass:** Behaves like
  :meth:`~pywbem.WBEMConnection.DeleteClass`, with the following difference:
  This operation additionally deletes all direct and indirect subclasses of the
  class to be deleted, and all instances of the classes that are being deleted.
  Requires that the class to be deleted is in the mock repository.

- **ModifyClass:** Not currently implemented.


.. _`Faked qualifier operations`:

Faked qualifier operations
^^^^^^^^^^^^^^^^^^^^^^^^^^

Qualifier operations only work if the mock repository is in full operation
mode.

- **SetQualifier:** Behaves like :meth:`~pywbem.WBEMConnection.SetQualifier`.
  Requires that the specified qualifier type is in the mock repository.

- **GetQualifier:** Behaves like :meth:`~pywbem.WBEMConnection.GetQualifier`.
  Requires that the specified qualifier type is in the mock repository.

- **EnumerateQualifiers:** Behaves like
  :meth:`~pywbem.WBEMConnection.EnumerateQualifiers`.
  Requires that the qualifier types to be returned are in the mock repository.


.. _`Building the mock repository`:

Building the mock repository
----------------------------

The mock repository should contain the CIM qualifier declarations, CIM classes,
CIM instances, and CIM methods to be used in the mock environment. The
mock user creates a repository that contains the CIM objects required for
the operations to be executed in the mock environment. Thus, if the user only
requires CIM_ComputerSystem, only that class and its dependent classes need
be in the repository along with instances of the classes that will satisfy
the methods called

:class:`~pywbem_mock.FakedWBEMConnection` and
:class:`~pywbem_mock.DMTFCIMSchema` provide the tools to build the mock
repository.

There are two ways to build a mock repository:

* Directly from pywbem CIM objects (:class:`~pywbem.CIMClass`,
  :class:`~pywbem.CIMInstance`, etc). See
  :meth:`~pywbem_mock.FakedWBEMConnection.add_cimobjects`

* From MOF definitions of the objects (which can be a string or a file, in
  and  with MOF pragma include statements).

  There are two methods to help building the repository from MOF:

  * Build from MOF definitions of the objects which are compiled into the
    repository. See :meth:`~pywbem_mock.FakedWBEMConnection.compile_mof_string`
    and See :meth:`~pywbem_mock.FakedWBEMConnection.compile_mof_file`.

  * Build MOF qualifier declarations and classes directly from the DMTF
    CIM schema by downloading the schema from the DMTF and selecting all
    or part of the schema to compile. This automatically compiles all
    qualifiers declarations into the mock repository and allows setting up
    a partial class repository (i.e. just selected classes) in a single
    method. See section `DMTF CIM schema download support`_ and the
    :meth:`~pywbem_mock.FakedWBEMConnection.compile_dmtf_schema` method.

It may take a combination of all three of the above methods to build a schema
that satisfies a particular requirement including:

1. Build the DMTF CIM Classes from the DMTF schema. This is easy to code,
   and eliminates errors defining components. It also loads all qualifier
   declarations.

2. Build non-DMTF classes (subclasses, etc.) by defining either MOF for the
   classes and compiling or directly building the pywbem CIM classes.

3. Build CIM instances by defining MOF and compiling or directly building
   the pywbem CIM instances. Often MOF is easier for this because it
   simplifies the definition of association instances with the instance
   alias.

4. Add the definition of any CIM methods for which the mock server is expected
   to respond. add_method_callback.  See
   :meth:`~pywbem_mock.FakedWBEMConnection. add_method_callback`.

The pywbem MOF compiler provides support for:

1. Automatically including all qualifier declaractions if classes are added
   with the method :meth:`~pywbem_mock.FakedWBEMConnection.compile_dmtf_schema`
   or the :class:`DMTFCIMSchema`.

2. Adding dependent classes from the DMTF schema in the case where they are
   missing in the compiled mof and the compiler search path includes the
   MOF directory of the DMTF CIM schema.  This include superclasses,
   reference classes defined in reference properties and parameters, and
   the class referenced through the EmbeddedInstance qualifier. Thus, the
   user does not have to track down those dependent classes to be able to
   create a working mock repository.

.. _`Example: Set up qualifier types and classes DMTF CIM schema`:

Example: Set up qualifier types and classes in DMTF CIM schema
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This example creates a faked connection and compiles the classes defined in the
list 'classes' from DMTF schema version 2.49.0 into the repository along with
all of the qualifier declarations defined by the DMTF schema and any dependent
classes (superclasses, etc.).

.. code-block:: python

    import pywbem
    import pywbem_mock

    conn = pywbem_mock.FakedWBEMConnection(default_namespace='root/interop')

    # Leaf classes that are to be compiled along with their dependent classes
    leaf_classes = ['CIM_RegisteredProfile',
                    'CIM_Namespace',
                    'CIM_ObjectManager',
                    'CIM_ElementConformsToProfile',
                    'CIM_ReferencedProfile']

    # Compile dmtf schema version 2.49.0, the qualifier declarations and
    # the classes in 'classes' and all dependent classes and keep the
    # schema in directory my_schema_dir
    conn.compile_dmtf_schema((2, 49, 0), "my_schema_dir", classes,
                            verbose=True)

    # Display the resulting repository
    conn.display_repository()

.. _`Example: Set up qualifier types and classes from MOF`:

Example: Set up qualifier types and classes from MOF
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This example creates a faked connection and sets up its mock repository with
qualifier types and classes that are defined in a MOF string.

.. code-block:: python

    import pywbem
    import pywbem_mock

    tst_namespace = 'root/blah'
    conn = pywbem_mock.FakedWBEMConnection()

    # Add some qualifier types and classes to the mock repo by compiling MOF
    mof = '''
        Qualifier Key : boolean = false,
            Scope(property, reference),
            Flavor(DisableOverride, ToSubclass);

        Qualifier Association : boolean,
            Scope(class),
            Flavor(DisableOverride, ToSubclass);

        class TST_Class1 {
              [Key]
            string InstanceID;
            string Prop1;
        };

        class TST_Class2 {
              [Key]
            string InstanceID;
            string Prop2;
        };

          [Association]
        class TST_Association12 {
              [Key]
            TST_Class1 REF Ref1;
              [Key]
            TST_Class2 REF Ref2;
        };
    '''
    conn.compile_mof_string(mof, tst_namespace)

    conn.display_repository()

This code displays the mock repository in MOF format after adding these objects:

.. code-block:: text

    # ========Mock Repo Display fmt=mof namespaces=all =========


    # NAMESPACE root/blah

    # Namespace root/blah: contains 2 Qualifier Declarations

    Qualifier Association : boolean,
        Scope(class),
        Flavor(DisableOverride, ToSubclass);

    Qualifier Key : boolean = false,
        Scope(property, reference),
        Flavor(DisableOverride, ToSubclass);

    # Namespace root/blah: contains 3 Classes

       [Association ( true )]
    class TST_Association12 {

          [Key ( true )]
       TST_Class1 REF Ref1;

          [Key ( true )]
       TST_Class2 REF Ref2;

    };

    class TST_Class1 {

          [Key ( true )]
       string InstanceID;

       string Prop1;

    };

    class TST_Class2 {

          [Key ( true )]
       string InstanceID;

       string Prop2;

    };

    ============End Repository=================


.. _`Example: Set up instances from single CIM objects`:

Example: Set up instances from single CIM objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Based on the mock repository content of the previous example, this example
adds two class instances and one association instance from their CIM objects.

.. code-block:: python

    c1_key = pywbem.CIMProperty('InstanceID', type='string', value='111')
    c1_path = pywbem.CIMInstanceName(
        'TST_Class1',
        keybindings={c1_key.name: c1_key.value},
    )
    c1 = pywbem.CIMInstance(
        'TST_Class1',
        properties=[
            c1_key,
            pywbem.CIMProperty('Prop1', type='string', value='1'),
        ],
        path=c1_path,
    )

    c2_key = pywbem.CIMProperty('InstanceID', type='string', value='222')
    c2_path = pywbem.CIMInstanceName(
        'TST_Class2',
        keybindings={c2_key.name: c2_key.value},
    )
    c2 = pywbem.CIMInstance(
        'TST_Class2',
        properties=[
            c2_key,
            pywbem.CIMProperty('Prop2', type='string', value='2'),
        ],
        path=c2_path,
    )

    a12_key1 = pywbem.CIMProperty('Ref1', type='reference', value=c1_path)
    a12_key2 = pywbem.CIMProperty('Ref2', type='reference', value=c2_path)
    a12_path = pywbem.CIMInstanceName(
        'TST_Association12',
        keybindings={
            a12_key1.name: a12_key1.value,
            a12_key2.name: a12_key2.value,
        },
    )
    a12 = pywbem.CIMInstance(
        'TST_Association12',
        properties=[
            a12_key1,
            a12_key2,
        ],
        path=a12_path,
    )

    conn.add_cimobjects([c1, c2, a12], tst_namespace)

    conn.display_repository()

This adds the instances to the repository display of the previous example:

.. code-block:: text

    # Namespace root/blah: contains 3 Instances

    #  Path=/root/blah:TST_Class1.InstanceID="111"
    instance of TST_Class1 {
       InstanceID = "111";
       Prop1 = "1";
    };

    #  Path=/root/blah:TST_Class2.InstanceID="222"
    instance of TST_Class2 {
       InstanceID = "222";
       Prop2 = "2";
    };

    #  Path=/root/blah:TST_Association12.Ref1="/:TST_Class1.InstanceID=\"111\"",Ref2="/:TST_Class2.InstanceID=\"222\""
    instance of TST_Association12 {
       Ref1 = "/:TST_Class1.InstanceID=\"111\"";
       Ref2 = "/:TST_Class2.InstanceID=\"222\"";
    };


.. _`FakedWBEMConnection`:

FakedWBEMConnection
-------------------

.. # Note: The pywbem_mock._wbemconnection_mock module docstring is a dummy.

.. autoclass:: pywbem_mock.FakedWBEMConnection
   :members:

   .. rubric:: Methods

   .. autoautosummary:: pywbem_mock.FakedWBEMConnection
      :methods:
      :nosignatures:

   .. rubric:: Attributes

   .. autoautosummary:: pywbem_mock.FakedWBEMConnection
      :attributes:

   .. rubric:: Details

.. _`DMTF CIM schema download support`:

DMTF CIM schema download support
--------------------------------

.. automodule:: pywbem_mock._dmtf_cim_schema

.. autoclass:: pywbem_mock.DMTFCIMSchema
   :members:

   .. rubric:: Methods

   .. autoautosummary:: pywbem_mock.DMTFCIMSchema
      :methods:
      :nosignatures:

   .. rubric:: Attributes

   .. autoautosummary:: pywbem_mock.DMTFCIMSchema
      :attributes:

   .. rubric:: Details
