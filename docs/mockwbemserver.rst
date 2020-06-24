.. _`Mock WBEM server`:

Mock WBEM server
================

**Experimental:** *New in pywbem 0.12.0 as experimental.*

.. _`Overview`:

Overview
--------

The 'pywbem_mock' module of pywbem provides a mock WBEM server that
enables using the pywbem client library without a real WBEM server.
This module is useful for testing the pywbem client library itself as well
as for the development and testing of Python programs that use the pywbem
client library.

The 'pywbem_mock' module contains the :class:`pywbem_mock.FakedWBEMConnection`
class that establishes a *faked connection*. That class is a subclass of
:class:`pywbem.WBEMConnection` and replaces its internal methods that use
HTTP/HTTPS to communicate with a WBEM server with methods that communicate
with  an in-process in-memory repository of CIM objects (the *mock repository*).

:class:`~pywbem_mock.FakedWBEMConnection` acts as both the client API and an
in-process fake WBEM server. It includes methods to establish, configure, and
visualize this fake WBEM server. As a result, the operation methods of
:class:`~pywbem_mock.FakedWBEMConnection` are those inherited from
:class:`~pywbem.WBEMConnection`, so they have exactly the same input
parameters, output parameters, return values, and even most of the raised
exceptions, as when invoked on a :class:`~pywbem.WBEMConnection` object against
a real WBEM server.

Each :class:`~pywbem_mock.FakedWBEMConnection` object creates its own mock
repository that contains the same kinds of CIM objects a WBEM
server repository contains: CIM classes, CIM instances, and CIM qualifier
declarations types contained in CIM namespaces. Because
:class:`~pywbem_mock.FakedWBEMConnection` operates only on the mock repository,
the class does not have any connection or security-related constructor
parameters.

Like :class:`~pywbem.WBEMConnection`, :class:`~pywbem_mock.FakedWBEMConnection`
has a default CIM namespace that is created upon
:class:`~pywbem_mock.FakedWBEMConnection` instance creation.
:class:`~pywbem_mock.FakedWBEMConnection` allows defining additional namespaces
with :meth:`~pywbem_mock.FakedWBEMConnection.add_namespace()` .

The mock repository must contain the CIM classes, CIM instances and CIM qualifier
declaration types that are needed for the operations that are invoked. This
results in a behavior of the faked operations that is close to the behavior of
the operations of a real WBEM server.
:class:`~pywbem_mock.FakedWBEMConnection` has methods that provide for adding
CIM classes, instances and qualifier types to its mock repository by providing
them as :term:`CIM objects <CIM object>`, or by compiling MOF.
See :ref:`Building a mock repository` for details.

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

    # Create a faked connection (with a mock repository)
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

The mock WBEM server supports:

1. All of the :class:`~pywbem.WBEMConnection` operation methods that communicate
   with the WBEM server (see below for the operations supported and their
   limitations).
2. Multiple CIM namespaces and a default namespace on the faked connection.
3. Gathering time statistics and delaying responses for a predetermined time.
4. :class:`~pywbem.WBEMConnection` logging except that there are no HTTP entries
   in the log.
5. User-defined providers that replace the WBEM  server responder for specific
   request methods, CIM classes, and namespaces. See :ref:`User-defined
   providers`.

The mock WBEM server does NOT support:

1. CIM-XML protocol security and security constructor parameters of
   :class:`~pywbem.WBEMConnection`.
2. Processing of queries defined for :meth:`~pywbem.WBEMConnection.ExecQuery`
   in languages like CQL and WQL. The mocked operation parses only the very
   general portions of the query for class/instance name and properties.
3. Filter processing of FQL (see :term:`DSP0212`) the Filter Query Language
   parameter ``QueryFilter`` used by the Open... operations because it does not
   implement the parser/processor for the FQL language.  It returns the same
   data as if the filter did not exist.
4. Providing data in the trace variables for last request and last reply in
   :class:`~pywbem.WBEMConnection`: ``last_request``, ``last_raw_request``,
   ``last_reply``, ``last_raw_reply``, ``last_request_len``, or
   ``last_reply_len``.
5. Log entries for HTTP request and response in the logging support of
   :class:`~pywbem.WBEMConnection`, because it does not actually build the
   HTTP requests or responses.
6. Generating CIM indications.
7. Some of the functionality that may be implemented in real WBEM servers such
   as the `__Namespace__` class/provider.  Note that such capabilities can be at
   least partly built on top of the existing capabilities by implementing
   user-defined providers.  Thus the CIM_Namespace class is supported with
   the user defined provider in the pywbem_mock directory but only registered
   if the user wants to use the provider.

.. code-block:: text

    +----------------------------------+
    |                                  |
    | +------------------------------+ |           +-------------+
    | |                              | |           |             |
    | | WBEM Server Mock Methods     | |           | Main        |
    | |                              | |           | Provider    |
    | |            All other Requests+------------>+             |
    | |  CreateInstance, ModifyInst  +------+      | Class ,assoc|
    | |  DeleteInstance, InvokeMeth  | |    |      | some inst   |
    | +------------^-----------------+ |    |      | requests    +--+
    |              |                   |    |      +-------------+  |
    | +------------+-----------------+ |    |                       |
    | | WBEM Server Mock Interface   | |    |      +-------------+  |     +-----------+
    | |                              | |    |      |             |  |     | Instance  |
    | +------------^-----------------+ |    |      | Provider    |  |     | Write     |
    |              |                   |    |      | Dispatcher  |  |     | Provider  |
    |              |                   |    |      |             +------->+ (Default) |
    |              |                   |    |      | Dispatches  |  |     +-|---|-----+       +----------+
    | +------------+-----------------+ |    |      | methods to  |  | +-----|   |-------------+ User     |
    | |                              | |    +----->+ default or  +----------------------------> Instance |
    | |  Client API request methods  | |           | registered  |  | |                       | Providers|
    | |  from WBEM Connection        | |           | user        |  | |   +------------+      |          +-----+
    | |                              | |           | providers   |  | |   |            |      +----------+     |
    | |   *CreateClass, etc.         | |           |             +------->+ Method     |                       |
   --->                              | |           |             |  | |   | Provider   |                       |
    | |                              | |           |             |  | |   | (Default)  |                       |
    | |                              | |           +-----------+-+  | |   +-----|------+                       |
    | +------------------------------+ |                       |    | |         |------------------------+     |
    | +------------------------------+ |                       +-------------------------------> User    |     |
    | |  Mock Environment management | |                            | |                        | Method  |     |
    | |  methods                     | |                            | |                        | Providers     |
    | |  * Mof Compiler, add objects | |                            | |                        |         |     |
    | |  * Manage namespaces         | |                            | |                        +---------+     |
    | |  * Register user providers   +---------+    +---------------v-V----------------------------------+     |
    | +------------------------------+ |       |    |                                                    |     |
    |  FakedWBEMConnection             |       +---->          CIM Repository                            <-----+
    +----------------------------------+            |                                                    |
                                                    +----------------------------------------------------+

Diagram of flow of requests operations through mocker

.. _`Faked WBEM operations`:

Faked WBEM operations
---------------------

The :class:`pywbem_mock.FakedWBEMConnection`  class supports the same WBEM
operations that are supported by the :class:`pywbem.WBEMConnection` class and
in addition a set of methods to execute WBEM server responders for each of these
client methods using an internal CIM repository of CIM classes, CIM instances,
and CIM qualifier declarations.

These faked operations generally adhere to the behavior requirements defined in
:term:`DSP0200` for handling input parameters and returning a result.

The faked operations get the data to be returned from the mock repository of
the faked connection, and put the data provided in operation parameters that
modify objects (create, modify, and delete operations) into the mock
repository.

However, because the pywbem mock support is only a simulation of a WBEM server
and intended to be used primarily for testing, there are limitations and
differences between the behavior of the faked operations and a real WBEM
server.

The descriptions below describe differences between the faked operations of
the pywbem mock support and the operations of a real WBEM server, and the
effects of the operation modes of the mock repository.


.. _`Faked instance operations`:

Faked instance operations
^^^^^^^^^^^^^^^^^^^^^^^^^

The operations that retrieve instances require instances in the
repository for the instances to be recovered and that the classes
for these instances exist in the repository.

- **GetInstance:** Behaves like :meth:`~pywbem.WBEMConnection.GetInstance`.
  Returns an instance defined by the instance name input parameter if that
  instance exists in the repository.

- **EnumerateInstances:** Behaves like
  :meth:`~pywbem.WBEMConnection.EnumerateInstances`, returning all instances
  of the CIM class defined on input and subclasses of this class filtered
  by the optional attributes for property names, etc.

- **EnumerateInstanceNames:** Behaves like
  :meth:`~pywbem.WBEMConnection.EnumerateInstances`, Returns the instance name
  of all instances of the :class:`pywbem.CIMClass` defined on input and
  subclasses of this class.

- **CreateInstance**: Behaves like
  :meth:`~pywbem.WBEMConnection.CreateInstance`.

  Creates the defined instance in the CIM repository.

  If there is no user-defined provider (see :ref:`User-defined providers`)for
  the class defined in the ``NewInstance`` parameter operation requires that
  all key properties be specified in the new instance since the CIM repository
  has no support for dynamically setting key properties and all key properties
  are required to get the newly defined instance with other requests.  If a
  user-defined provider exists for the class, the behavior depends on that
  provider.

- **ModifyInstance**: Behaves like
  :meth:`~pywbem.WBEMConnection.ModifyInstance`. Modifies the instance
  defined by the instance name provided on input if that instance exists in
  the repository. It modifies only the properties defined by the instance
  provided and will not modify any key properties. If there is a user-defined
  provider defined for this operation, that provider may modify the default
  behavior.

- **DeleteInstance**: Behaves like
  :meth:`~pywbem.WBEMConnection.DeleteInstance`. Deletes the instance defined
  by the instance name provided on input if that instance exists. If there is a
  user-defined provider defined for this operation, that provider may modify
  the default behavior.

- **ExecQuery**: This operation is not currently implemented.

See :ref:`User-defined providers` for more information on writing a
user-defined provider.


.. _`Faked association operations`:

Faked association operations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The faked association operations support both instance-level use and
class-level requests. Class-level use requires the mock repository to be in full
mode, while instance-level use works in both operation modes of the mock
repository.

- **AssociatorNames**: Behaves like
  :meth:`~pywbem.WBEMConnection.AssociatorNames`, with the following
  requirements:
  The source, target, and association classes and their subclasses must exist
  in the mock repository for both class-level use and instance-level use.

- **Associators**: Behaves like
  :meth:`~pywbem.WBEMConnection.Associators`, with the
  requirements described for `AssociatorNames`, above.

- **ReferenceNames**: Behaves like
  :meth:`~pywbem.WBEMConnection.ReferenceNames`, with the
  requirements described for `AssociatorNames`, above.

- **References**: Behaves like
  :meth:`~pywbem.WBEMConnection.References`, with the
  requirements described for `AssociatorNames`, above.


.. _`Faked method invocation operation`:

Faked method invocation operation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. index:: single: User-defined providers

The faked method invocation operation (`InvokeMethod`) behaves like
:meth:`~pywbem.WBEMConnection.InvokeMethod`, but because of the nature of
`InvokeMethod`, the user must provide an implementation of InvokeMethod
based on the API defined in :meth:`~pywbem_mock.MethodProvider.InvokeMethod`.

NOTE: InvokeMethod is the method name pywbem and other clients and WBEM
servers use for what the DMTF defines as extrinsic methods.

See :ref:`User-defined providers` for more information on writing a
user-defined provider.


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
and responses on the connection, but instead are a layer on top of
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
  specified in the `ClassName` parameter be in the mock repository.

- **EnumerateClassNames:** Behaves like
  :meth:`~pywbem.WBEMConnection.EnumerateClassNames`. Requires that the class
  specified in the `ClassName` parameter be  in the mock repository.

- **CreateClass:** Behaves like
  :meth:`~pywbem.WBEMConnection.CreateClass`. Requires that the superclass of
  the new class (if it specifies one) is in the mock repository.

- **DeleteClass:** Behaves like
  :meth:`~pywbem.WBEMConnection.DeleteClass`, with the following difference:
  This operation additionally deletes all direct and indirect subclasses of the
  class to be deleted, and all instances of the classes that are being deleted.
  Requires that the class to be deleted is in the mock repository.

- **ModifyClass:** Not currently implemented.


.. _`Faked qualifier declaration operations`:

Faked qualifier declaration operations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Qualifier operations declaration include the following.

- **SetQualifier:** Behaves like :meth:`~pywbem.WBEMConnection.SetQualifier`.
  Requires that the specified qualifier type is in the mock repository.

- **GetQualifier:** Behaves like :meth:`~pywbem.WBEMConnection.GetQualifier`.
  Requires that the specified qualifier type is in the mock repository.

- **EnumerateQualifiers:** Behaves like
  :meth:`~pywbem.WBEMConnection.EnumerateQualifiers`.
  Requires that the qualifier types to be returned are in the mock repository.

- **DeleteQualifier:** - Not implemented.


.. _`Building a mock repository`:

Building a mock repository
--------------------------

The mock repository needs to contain the CIM namespaces, and within them, the
CIM qualifier declarations, CIM classes, and CIM instances required by the user.
These are created as part of the setup of any particular pywbem mock environment.
Thus, if the user only requires CIM_ComputerSystem in a particular namespace,
only that class and its dependent classes and qualifier declarations need be in
that namespace in the mock repository, along with instances of the classes that
will satisfy the client methods executed.

The classes :class:`~pywbem_mock.FakedWBEMConnection` and
:class:`~pywbem_mock.DMTFCIMSchema` provide the tools to build the mock
repository.

CIM namespaces are created in the mock repository by defining a default
namespace for the :class:`~pywbem_mock.FakedWBEMConnection` object, and by using
the :meth:`~pywbem_mock.FakedWBEMConnection.add_namespace` method to create
additional namespaces.

There are multiple ways to add CIM objects to a target namespace of the
mock repository:

* From :term:`CIM objects <CIM object>`, using the
  :meth:`~pywbem_mock.FakedWBEMConnection.add_cimobjects` method.

  The specified CIM objects are added to or updated in a target namespace of
  the mock repository. Dependent classes and qualifier types of these objects
  must already exist in the target namespace.

* From definitions of the CIM objects in a MOF string or a MOF file, using
  the :meth:`~pywbem_mock.FakedWBEMConnection.compile_mof_string`
  or :meth:`~pywbem_mock.FakedWBEMConnection.compile_mof_file` methods.

  The CIM objects defined in the MOF are added to or updated in a target
  namespace of the mock repository. Dependent classes and qualifier types of
  these objects must already exist in the target namespace.

* From CIM class names and a schema search path containing the MOF files of one
  or more schemas, using the
  :meth:`~pywbem_mock.FakedWBEMConnection.compile_schema_classes` method.

  The schema MOF files can either be provided by the user, or the DMTF CIM
  schema can be automatically downloaded from the DMTF using the
  :meth:`~pywbem_mock.DMTFCIMSchema` class.

  The specified CIM classes are added to or updated in a target namespace of the
  mock repository, and their dependent classes and qualifier types are added
  to the target namespace from the schemas in the search path as needed.

  The dependent classes and qualifier types are determined automatically and
  recursively. This includes superclasses, reference classes (used in
  reference properties and reference parameters), and embedded classes (i.e.
  classes referenced through the EmbeddedInstance qualifier). Thus, a user
  creating a mock repository does not have to track down those dependent classes
  and qualifier types, and instead only needs to know the schema(s) to be used
  and the creation classes for any CIM instances. This also means that there is
  normally no reason to compile the complete schema which is much larger than
  the classes that are minimally needed.

It may take a combination of all of the above methods to build a mock repository
that satisfies a particular usage requirement. A typical approach for building
a mock repository is:

1. Establish the MOF subtrees for the schema(s) needed. That can be a downloaded
   version of the DMTF CIM schema, local modifications to a version of the DMTF
   CIM schema, user-defined schemas including schemas derived from the DMTF CIM
   schema, or a combination thereof.

2. Create the CIM namespaces needed, either as the default namespace or by
   adding namespaces, including the :term:`interop namespace`.

3. For each CIM namespace needed, create the set of needed CIM classes and
   qualifier types by using the
   :meth:`~pywbem_mock.FakedWBEMConnection.compile_schema_classes` method
   and specifying the set of creation classes of the CIM instances that are
   intended to be added, and specifying the pragma MOF files of the schema(s)
   added in step 1 as a schema search path.

4. For each CIM namespace needed, create the set of needed CIM instances
   by defining and compiling instance MOF, or by creating and adding
   :class:`~pywbem.CIMInstance` objects, or both. Often defining MOF is easier
   for this because it simplifies the definition of association instances with
   the instance alias.

5. Register user-defined providers such as the
   :class:`~pywbem_mock.CIMNamespaceProvider` or user-written providers for the
   creation classes of the CIM instances that have non-default instance write
   behavior or that need CIM methods to be supported.
   See :ref:`User-defined providers` for details.


.. _`Example: Set up qualifier types and classes DMTF CIM schema`:

Example: Set up qualifier types and classes in DMTF CIM schema
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This example creates a faked connection using ``root/interop`` as the default
namespace and compiles the classes defined in the list 'classes' from DMTF
schema version 2.49.0 into the mock repository along with all of the qualifier
types defined by the DMTF CIM schema and any dependent classes
(superclasses, etc.).

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

    # Download DMTF CIM schema version 2.49.0 into directory my_schema_dir.
    schema = DMTFCIMSchema((2, 49, 0), "my_schema_dir", leaf_classes,
                           verbose=True)

    # Compile the leaf classes, looking up dependent classes and qualifier
    # types from the downloaded DMTF CIM schema.
    conn.compile_schema_classes(leaf_classes, schema.schema_pragma_file
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

Here is the output from displaying the mock repository in the example above:

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
adds two class instances and one association instance from their CIM objects
using the :meth:`~pywbem_mock.FakedWBEMConnection.add_cimobjects` method.

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


.. _`Mocking multiple CIM namespaces`:

Mocking multiple CIM namespaces
-------------------------------

Pywbem_mock allows creating multiple namespaces in the repository and installing
elements in some or all of those namespaces.

There is a default namespace created when the
:class:`~pywbem_mock.FakedWBEMConnection` object is created from either the
value of the `default_namespace` init parameter or its default value
``root/cimv2``.

However, a working WBEM environment normally includes at least two namespaces:

1. An :term:`interop namespace` which contains the parts of the model that deal
   with the WBEM server itself and with the implemented model
   (ex. CIM_Namespace, CIM_ObjectManager, CIM_RegisteredProfile, etc.) and
   which must be publically discoverable without the user knowing what CIM
   namespaces exist in the WBEM server.

2. A user namespace containing the CIM objects for the user model.

Pywbem_mock includes a user-defined provider for the CIM_Namespace class that
can be enabled by adding code similar to the following to the setup of a
mock environment.

.. code-block:: text

    # Register the provider for the CIM_Namespace class, assuming that
    # dependent classes and qualifier types have already been created in
    # the interop namespace.
    ns_provider = pywbem_mock.CIMNamespaceProvider(conn.cimrepository)
    interop_namespace = "interop"   # or "root/interop"
    conn.add_namespace(interop_namespace)
    conn.register_provider(ns_provider, namespaces=interop_namespace)


.. _`User-defined providers`:

User-defined providers
----------------------

Within the fake  WBEM server the response to client requests is normally
determined by standard server responder methods that use data in the CIM
repository to generate responses (ex. ``GetInstance`` gets the instances from the
repository, possibly filters properties and attributes and returns the
instance). However, it is expected that the user may want specific classes to
generate responses that have side effects, or manage the returns differently
than the normal responses.  Thus, for example, the DMTF defined CIM_Namespace
class returns instances of each of the namespaces in the CIM repository. That means
that somewhere an instance the class must be created each time a namespace is
created or the responder must get the set of namespaces from the CIM repository
to generate responses to ``GetInstance``, ``EnumerateInstance``, etc.

Also, the :meth:`~pywbem_mock.WBEMConnection.InvokeMethod` operation on
on a :class:`~pywbem_mock.FakedWBEMConnection` object depends on a specific
responder method in the mock WBEM server.

To meet these needs, pywbem_mock has implemented the capability to create
:term:`user-defined providers <user-defined provider>` that become request
responders for defined classes and operations which can can manipulate the
client input and generate responses specific for defined CIM classes.

User-defined providers can be written by the user by implementing subclasses of
specific provider classes and registering these subclasses as providers using
:meth:`~pywbem_mock.FakedWBEMConnection.register_provider`.

The WBEM operations supported by user-defined providers can be implement one by
one. If a user-defined provider does not implement all WBEM operations, the
default implementation is used.

The following table shows the WBEM operations for which user-defined providers
are supported, and the corresponding provider types:

.. table:: WBEM operations of user-defined providers

    ==============  ==============  ================  ==============================
    WBEM operation  Provider type   Type name         Description
    ==============  ==============  ================  ==============================
    InvokeMethod    method          "method"          :ref:`Method Provider`
    CreateInstance  instance write  "instance-write"  :ref:`Instance Write Provider`
    ModifyInstance  instance write  "instance-write"  :ref:`Instance Write Provider`
    DeleteInstance  instance write  "instance-write"  :ref:`Instance Write Provider`
    ==============  ==============  ================  ==============================


.. _`Creating user-defined instance providers`:

Creating user-defined instance providers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

User-defined instance write providers can override the default implementations
for the corresponding WBEM operations listed in the above table (i.e.
``CreateInstance``, ``ModifyInstance``, and ``DeleteInstance``). The Python
methods implementing these WBEM operations are defined in a user-defined class
that subclasses the :class:`~pywbem_mock.InstanceWriteProvider` class. The
details of implementing this provider type are described in
:ref:`Instance Write Provider`.

The following is a simple example of a user-defined instance write provider:

.. code-block:: python

    from pywbem import CIMError, CIM_ERR_METHOD_NOT_SUPPORTED
    from pywbem_mock import InstanceWriteProvider

    class MyInstanceProvider(InstanceWriteProvider):
        """
        Simplistic user provider implements CreateInstance and DeleteInstance.
        This example modifies a specific property for CreateInstance, does not
        allow modify instance. For DeleteInstance it simply calls the default
        processor
        """

        # The provider will serve the CIM_Foo and CIM_FooFoo classes
        provider_classnames = ['CIM_Foo', 'CIM_FooFoo']

        def __init__(self, cimrepository):
            """
            Initialize the cimrepository
            """
            super(MyInstanceProvider, self).__init__(cimrepository)

        def CreateInstance(self, namespace, NewInstance):
            """Create instance just calls super class method"""
            NewInstance.properties["myproperty"] = "Fixed"
            return super(MyInstanceProvider, self).CreateInstance(
                namespace, NewInstance)

        def ModifyInstance(self, ModifiedInstance, IncludeQualifiers=None,
                           PropertyList=None):
            """Disallows ModifyInstance"""
            raise CIMError(CIM_ERR_NOT_SUPPORTED,
                           "{0} provider does not allow ModifyInstance.".format(
                           self.__class__.__name__))

        def DeleteInstance(self, InstanceName):
            """Delete instance just calls super class method"""
            return super(MyInstanceProvider, self).DeleteInstance(
                InstanceName)

    def post_register_setup(self, conn):
        """Execute setup code after provider is registered."""
        pass


.. _`Creating user-defined method providers`:

Creating user-defined method providers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

User-defined method providers can implement the WBEM operation for invoking
CIM methods (i.e. ``InvokeMethod``) in the above table. If no user-defined
method provider exists for the requested CIM method, the default is an exception
since there is no default behavior for a CIM method invocation.
The Python method for implementing this WBEM operation is defined in a
user-defined class that subclasses the :class:`~pywbem_mock.MethodProvider`
class. The details of implementing this provider type are described in
:ref:`Method Provider`.

The following is an example of a method provider:

.. code-block:: python

    from pywbem import CIMParameter, CIMError, \
        CIM_ERR_NOT_FOUND, CIM_ERR_METHOD_NOT_AVAILABLE
    from pywbem_mock import MethodProvider

    class MyMethodProvider(MethodProvider):

        provider_classname = 'CIM_Foo_sub_sub'
        """
        User method provider for InvokeMethod using CIM_Foo_sub_sub and method1.
        """
        def __init__(self, cimrepository):
            super(MyMethodProvider, self).__init__(cimrepository)

        def InvokeMethod(self, namespace, MethodName, ObjectName, Params):
            """
            The parameters and return for Invoke method are defined in
            :meth:`~pywbem_mock.MethodProvider.InvokeMethod`

            This acts as both a static (ObjectName is only classname) and
            dynamic (ObjectName is an instance name) method provider.
            """
            # Validate namespace using method in BaseProvider
            self.validate_namespace(namespace)

            # Get classname and validate. This provider uses only one class
            if isinstance(ObjectName, six.string_types):
                classname = ObjectName
            else:
                classname = ObjectName.classname
            assert classname.lower() == 'tst_class'

            # Test if class exists.
            if not self.class_exists(namespace, classname):
                raise CIMError(
                    CIM_ERR_NOT_FOUND,
                    _format("Class {0!A} does not exist in CIM repository, "
                            "namespace {1!A}", classname, namespace))

            if isinstance(ObjectName, CIMInstanceName):
                instance_store = self.cimrepository.get_instance_store(
                    namespace)
                if not instance_store.object_exists(objectname):
                    raise CIMError(
                        CIM_ERR_NOT_FOUND,
                        _format("Instance {0!A} does not exist in CIM "
                                "repository", ObjectName))

            if MethodName.lower() == 'method1':

                rtn_parameters = [CIMParameter('OutputParam1', 'string',
                                               value=namespace)]
                else:
                    rtn_params = None

                return (return_value, rtn_params)

            else:
                raise CIMError(CIM_ERR_METHOD_NOT_AVAILABLE)


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



.. _`config`:

config
------

.. automodule:: pywbem_mock.config
   :members:


.. _`Mock CIM repository`:

Mock CIM repository
-------------------

.. automodule:: pywbem_mock._baserepository

.. autoclass:: pywbem_mock.BaseRepository
   :members:

   .. rubric:: Methods

   .. autoautosummary:: pywbem_mock.BaseRepository
      :methods:
      :nosignatures:

   .. rubric:: Attributes

   .. autoautosummary:: pywbem_mock.BaseRepository
      :attributes:

   .. rubric:: Details


.. autoclass:: pywbem_mock.BaseObjectStore
   :members:

   .. rubric:: Methods

   .. autoautosummary:: pywbem_mock.BaseObjectStore
      :methods:
      :nosignatures:

   .. rubric:: Attributes

   .. autoautosummary:: pywbem_mock.BaseObjectStore
      :attributes:

   .. rubric:: Details


.. automodule:: pywbem_mock._inmemoryrepository

.. autoclass:: pywbem_mock.InMemoryRepository
   :members:

   .. rubric:: Methods

   .. autoautosummary:: pywbem_mock.InMemoryRepository
      :methods:
      :nosignatures:

   .. rubric:: Attributes

   .. autoautosummary:: pywbem_mock.InMemoryRepository
      :attributes:

   .. rubric:: Details


.. autoclass:: pywbem_mock.InMemoryObjectStore
   :members:

   .. rubric:: Methods

   .. autoautosummary:: pywbem_mock.InMemoryObjectStore
      :methods:
      :nosignatures:

   .. rubric:: Attributes

   .. autoautosummary:: pywbem_mock.InMemoryObjectStore
      :attributes:

   .. rubric:: Details


.. index:: pair: User defined providers; user providers

.. _`User provider interfaces`:

User provider interfaces
------------------------

.. _`Instance Write Provider`:

Instance Write Provider
^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: pywbem_mock._instancewriteprovider

.. autoclass:: pywbem_mock.InstanceWriteProvider
   :members:

   .. rubric:: Methods

   .. autoautosummary:: pywbem_mock.InstanceWriteProvider
      :methods:
      :nosignatures:

   .. rubric:: Attributes

   .. autoautosummary:: pywbem_mock.InstanceWriteProvider
      :attributes:

   .. rubric:: Details


.. _`Method Provider`:

Method Provider
^^^^^^^^^^^^^^^

.. automodule:: pywbem_mock._methodprovider

.. autoclass:: pywbem_mock.MethodProvider
   :members:

   .. rubric:: Methods

   .. autoautosummary:: pywbem_mock.MethodProvider
      :methods:
      :nosignatures:

   .. rubric:: Attributes

   .. autoautosummary:: pywbem_mock.MethodProvider
      :attributes:

   .. rubric:: Details


.. _`Base Provider`:

Base Provider
^^^^^^^^^^^^^

.. automodule:: pywbem_mock._baseprovider

.. autoclass:: pywbem_mock.BaseProvider
   :members:

   .. rubric:: Methods

   .. autoautosummary:: pywbem_mock.BaseProvider
      :methods:
      :nosignatures:

   .. rubric:: Attributes

   .. autoautosummary:: pywbem_mock.BaseProvider
      :attributes:

   .. rubric:: Details
