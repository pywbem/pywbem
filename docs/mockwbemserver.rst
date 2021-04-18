.. _`Mock WBEM server`:

Mock WBEM server
================

*New in pywbem 0.12 as experimental and finalized in 1.2.*

.. _`Overview`:

Overview
--------

The 'pywbem_mock' module of pywbem provides a *mock WBEM server* that
enables using the pywbem client library without a real WBEM server.
This is useful for testing the pywbem client library itself as well
as for the development and testing of Python programs that use the pywbem
client library.

The :class:`pywbem_mock.FakedWBEMConnection` class establishes an in-process
mock WBEM server and represents a *faked connection* to that mock WBEM server.
That class acts as both the client API and as an API for managing the mocked
WBEM server.

The :class:`pywbem_mock.FakedWBEMConnection` class is a subclass of
:class:`pywbem.WBEMConnection` and replaces its internal methods that use
HTTP/HTTPS to communicate with a WBEM server with methods that communicate with
the mock WBEM server. As a result, the operation methods of
:class:`~pywbem_mock.FakedWBEMConnection` are those inherited from
:class:`~pywbem.WBEMConnection`, so they have exactly the same input parameters,
output parameters, return values, and even most of the raised exceptions, as
when invoked on a :class:`~pywbem.WBEMConnection` object against a real
WBEM server.

The mock WBEM server has an in-memory repository of CIM objects
(the *CIM repository*). Each :class:`~pywbem_mock.FakedWBEMConnection` object
creates its own CIM repository that contains the same kinds of CIM objects a
WBEM server repository contains: CIM classes, CIM instances, and CIM qualifier
declarations types, contained in CIM namespaces. Because
:class:`~pywbem_mock.FakedWBEMConnection` operates only on the CIM repository,
the class does not have any connection- or security-related constructor
parameters.

Like :class:`~pywbem.WBEMConnection`, :class:`~pywbem_mock.FakedWBEMConnection`
has a default CIM namespace that is created in the CIM repository upon
:class:`~pywbem_mock.FakedWBEMConnection` object creation.
Additional namespaces in the CIM repository can be created with
:meth:`~pywbem_mock.FakedWBEMConnection.add_namespace()` .

An Interop namespace can be created by adding it via
:meth:`~pywbem_mock.FakedWBEMConnection.add_namespace`. The Interop
namespace will be initially empty, and the necessary instance(s) of a CIM
namespace class will be automatically created when registering the namespace
provider :class:`~pywbem_mock.CIMNamespaceProvider`. See
:ref:`Mocking multiple CIM namespaces` for details.

The CIM repository must contain the CIM classes, CIM instances and CIM qualifier
declaration types that are needed for the operations that are invoked. This
results in a behavior of the mock WBEM server that is close to the behavior of
the operations of a real WBEM server.
:class:`~pywbem_mock.FakedWBEMConnection` has methods that provide for adding
CIM classes, instances and qualifier types to its CIM repository by providing
them as :term:`CIM objects <CIM object>`, or by compiling MOF.
See :ref:`Building a mocked CIM repository` for details.

The following example demonstrates setting up a mock WBEM server, adding
several CIM objects defined in a MOF string to its CIM repository, and
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

    # Create a faked connection including a mock WBEM server with a CIM repo
    conn = pywbem_mock.FakedWBEMConnection(default_namespace='root/cimv2')

    # Compile the MOF string and add its CIM objects to the default namespace
    # of the CIM repository
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
    inst = conn.GetInstance(CIMInstanceName('CIM_Foo', {'InstanceID': "I1"}))

The mock WBEM server supports:

1. All of the :class:`~pywbem.WBEMConnection` operation methods that communicate
   with the WBEM server (see below for the operations supported and their
   limitations).
2. Multiple CIM namespaces and a default namespace on the faked connection.
3. Gathering time statistics and delaying responses for a predetermined time.
4. :class:`~pywbem.WBEMConnection` logging except that there are no HTTP entries
   in the log.
5. User-defined providers that replace the the default providers specific
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
    | |   ..CreateClass, etc.        | |           |             +------->+ Method     |                       |
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


.. _`WBEM operations of a mock WBEM server`:

WBEM operations of a mock WBEM server
-------------------------------------

The :class:`pywbem_mock.FakedWBEMConnection` class supports the same WBEM
operations that are supported by the :class:`pywbem.WBEMConnection` class and
in addition a set of methods for setting up its mocked CIM repository, and
for registering user-defined providers for selected WBEM operations.

These *faked WBEM operations* generally adhere to the behavior requirements
defined in :term:`DSP0200` for handling input parameters and returning a result.

The faked WBEM operations get the data to be returned from the CIM repository of
the mock WBEM server, and put the data provided in operation parameters that
modify objects (create, modify, and delete operations) into the
CIM repository.

However, because the pywbem mock support is only a simulation of a WBEM server
and intended to be used primarily for testing, there are limitations and
differences between the behavior of the faked WBEM operations and a real WBEM
server.

The descriptions below describe differences between the faked WBEM operations of
the pywbem mock support and the operations of a real WBEM server, and the
effects of the operation modes of the CIM repository.


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
class-level requests. Class-level use requires the CIM repository to be in full
mode, while instance-level use works in both operation modes of the
CIM repository.

- **AssociatorNames**: Behaves like
  :meth:`~pywbem.WBEMConnection.AssociatorNames`, with the following
  requirements:
  The source, target, and association classes and their subclasses must exist
  in the CIM repository for both class-level use and instance-level use.

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

Class operations only work if the CIM repository is in full operation mode.

- **GetClass:** Behaves like :meth:`~pywbem.WBEMConnection.GetClass`. Requires
  that the class to be returned is in the CIM repository.

- **EnumerateClasses:** Behaves like
  :meth:`~pywbem.WBEMConnection.EnumerateClasses`. Requires that the class
  specified in the `ClassName` parameter be in the CIM repository.

- **EnumerateClassNames:** Behaves like
  :meth:`~pywbem.WBEMConnection.EnumerateClassNames`. Requires that the class
  specified in the `ClassName` parameter be  in the CIM repository.

- **CreateClass:** Behaves like
  :meth:`~pywbem.WBEMConnection.CreateClass`. Requires that the superclass of
  the new class (if it specifies one) is in the CIM repository.

- **DeleteClass:** Behaves like :meth:`~pywbem.WBEMConnection.DeleteClass`,
  with the following difference: This operation additionally deletes all direct
  and indirect subclasses of the class to be deleted, and all instances of the
  classes that are being deleted. Requires that the class to be deleted is in
  the CIM repository.

- **ModifyClass:** Behaves like :meth:`~pywbem.WBEMConnection.ModifyClass`.
  The pywbem_mock implementation rejects modifications where the class to
  modifiy has either subclasses or instances and resolves the various
  qualifiers, class origin values and propagated values as the the CreateClass
  operation.


.. _`Faked qualifier declaration operations`:

Faked qualifier declaration operations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Qualifier operations declaration include the following.

- **SetQualifier:** Behaves like :meth:`~pywbem.WBEMConnection.SetQualifier`.
  Requires that the specified qualifier type is in the CIM repository.

- **GetQualifier:** Behaves like :meth:`~pywbem.WBEMConnection.GetQualifier`.
  Requires that the specified qualifier type is in the CIM repository.

- **EnumerateQualifiers:** Behaves like
  :meth:`~pywbem.WBEMConnection.EnumerateQualifiers`.
  Requires that the qualifier types to be returned are in the CIM repository.

- **DeleteQualifier:** - Not implemented.


.. _`FakedWBEMConnection class`:

FakedWBEMConnection class
-------------------------

.. # Note: The pywbem_mock._wbemconnection_mock module docstring is a dummy.

.. autoclass:: pywbem_mock.FakedWBEMConnection
    :members:
    :special-members:
    :exclude-members: __init__,__weakref__
    :autosummary:
    :autosummary-inherited-members:


.. _`Building a mocked CIM repository`:

Building a mocked CIM repository
--------------------------------

The CIM repository of a mock WBEM server needs to contain the CIM namespaces,
and within them, the
CIM qualifier declarations, CIM classes, and CIM instances required by the user.
These are created as part of the setup of any particular pywbem mock environment.
Thus, if the user only requires CIM_ComputerSystem in a particular namespace,
only that class and its dependent classes and qualifier declarations need be in
that namespace in the CIM repository, along with instances of the classes that
will satisfy the client methods executed.

The classes :class:`~pywbem_mock.FakedWBEMConnection` and
:class:`~pywbem_mock.DMTFCIMSchema` provide the tools to build the
CIM repository.

CIM namespaces are created in the CIM repository by defining a default
namespace for the :class:`~pywbem_mock.FakedWBEMConnection` object, and by using
the :meth:`~pywbem_mock.FakedWBEMConnection.add_namespace` method to create
additional namespaces.

There are multiple ways to add CIM objects to a target namespace of the
CIM repository:

* From :term:`CIM objects <CIM object>`, using the
  :meth:`~pywbem_mock.FakedWBEMConnection.add_cimobjects` method.

  The specified CIM objects are added to or updated in a target namespace of
  the CIM repository. Dependent classes and qualifier types of these objects
  must already exist in the target namespace.

* From definitions of the CIM objects in a MOF string or a MOF file, using
  the :meth:`~pywbem_mock.FakedWBEMConnection.compile_mof_string`
  or :meth:`~pywbem_mock.FakedWBEMConnection.compile_mof_file` methods.

  The CIM objects defined in the MOF are added to or updated in a target
  namespace of the CIM repository. Dependent classes and qualifier types of
  these objects must already exist in the target namespace.

* From CIM class names and a schema search path containing the MOF files of one
  or more schemas, using the
  :meth:`~pywbem_mock.FakedWBEMConnection.compile_schema_classes` method.

  The schema MOF files can either be provided by the user, or the DMTF CIM
  schema can be automatically downloaded from the DMTF using the
  :meth:`~pywbem_mock.DMTFCIMSchema` class.

  The specified CIM classes are added to or updated in a target namespace of the
  CIM repository, and their dependent classes and qualifier types are added
  to the target namespace from the schemas in the search path as needed.

  The dependent classes and qualifier types are determined automatically and
  recursively. This includes superclasses, reference classes (used in
  reference properties and reference parameters), and embedded classes (i.e.
  classes referenced through the EmbeddedInstance qualifier). Thus, a user
  building a CIM repository does not have to track down those dependent classes
  and qualifier types, and instead only needs to know the schema(s) to be used
  and the creation classes for any CIM instances. This also means that there is
  normally no reason to compile the complete schema which is much larger than
  the classes that are minimally needed.

It may take a combination of all of the above methods to build a CIM repository
that satisfies a particular usage requirement. A typical approach for building
a CIM repository is:

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

This example creates a mock WBEM server using ``root/interop`` as the default
namespace and compiles the classes defined in the list 'classes' from DMTF
schema version 2.49.0 into the CIM repository along with all of the qualifier
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

This example creates a mock WBEM server and sets up its CIM repository with
qualifier types and classes that are defined in a MOF string.

.. code-block:: python

    import pywbem
    import pywbem_mock

    tst_namespace = 'root/blah'
    conn = pywbem_mock.FakedWBEMConnection()

    # Add some qualifier types and classes to the CIM repo by compiling MOF
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

Here is the output from displaying the CIM repository in the example above:

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

Based on the CIM repository content of the previous example, this example
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


.. _`DMTF CIM schema download support`:

DMTF CIM schema download support
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: pywbem_mock._dmtf_cim_schema

.. autoclass:: pywbem_mock.DMTFCIMSchema
    :members:
    :special-members:
    :exclude-members: __init__,__weakref__
    :autosummary:
    :autosummary-inherited-members:


.. _`In-memory CIM repository classes`:

In-memory CIM repository classes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: pywbem_mock._inmemoryrepository

.. autoclass:: pywbem_mock.InMemoryRepository
    :members:
    :special-members:
    :exclude-members: __init__,__weakref__
    :autosummary:
    :autosummary-inherited-members:

.. autoclass:: pywbem_mock.InMemoryObjectStore
    :members:
    :special-members:
    :exclude-members: __init__,__weakref__
    :autosummary:
    :autosummary-inherited-members:


.. _`Mocking multiple CIM namespaces`:

Mocking multiple CIM namespaces
-------------------------------

The mock WBEM server allows creating multiple CIM namespaces in its
CIM repository and adding CIM objects in some or all of those namespaces.

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
mock environment:

.. code-block:: python

    conn = pywbem_mock.FakedWBEMConnection(...)

    . . .

    interop_ns = "interop"   # or "root/interop"
    conn.add_namespace(interop_ns)
    ns_provider = pywbem_mock.CIMNamespaceProvider(conn.cimrepository)
    conn.register_provider(ns_provider, namespaces=interop_ns)


.. index:: pair: User defined providers; user providers

.. _`User-defined providers`:

User-defined providers
----------------------

Within the mock WBEM server, the response to client requests is normally
determined by provider methods that use data in the CIM
repository to generate responses (ex. ``GetInstance`` gets the instances from
the repository, possibly filters properties and returns the instance).
However, it is expected that the user may want WBEM operations on specific
CIM classes to have side effects, or manage the returns differently
than the normal responses.

Thus, for example, the DMTF-defined CIM_Namespace class represents the
namespaces in the CIM repository. That means that its provider method for
``CreateInstance`` must create a namespace as a side effect, and that its
provider methods for ``GetInstance`` or ``EnumerateInstances`` must inspect
the set of namespaces in the CIM repository to generate responses, etc.

Another example of user-defined providers are classes that create their key
property values automatically, for example classes that have a single
``InstanceID`` key. The provider method for ``CreateInstance`` of such classes
would ignore the values for the key properties provided in the ``NewInstance``
parameter, and determine the key values on its own.

Also, the ``InvokeMethod`` operation depends on a specific provider method for
the invoked CIM method in the mock WBEM server.

To meet these needs, the capability is provided to users to write
:term:`user-defined providers <user-defined provider>` that replace the default
providers for defined classes and operations.

User-defined providers are written by implementing subclasses of
specific provider classes and registering these subclasses as providers using
:meth:`~pywbem_mock.FakedWBEMConnection.register_provider`.

The WBEM operations supported by user-defined providers can be implemented one by
one. If a user-defined provider does not implement all WBEM operations, the
default implementation will be used.

The following table shows the WBEM operations for which user-defined providers
are supported, and the corresponding provider types:

==============  ==============  ===========================================  ============================================
WBEM operation  Provider type   Superclass                                   Provider description
==============  ==============  ===========================================  ============================================
CreateInstance  instance write  :class:`~pywbem_mock.InstanceWriteProvider`  :ref:`User-defined instance write providers`
ModifyInstance  instance write  :class:`~pywbem_mock.InstanceWriteProvider`  :ref:`User-defined instance write providers`
DeleteInstance  instance write  :class:`~pywbem_mock.InstanceWriteProvider`  :ref:`User-defined instance write providers`
InvokeMethod    method          :class:`~pywbem_mock.MethodProvider`         :ref:`User-defined method providers`
==============  ==============  ===========================================  ============================================


.. _`Creating user-defined providers`:

Creating user-defined providers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A user-defined provider can be created as follows:

1. Define a subclass of the superclass listed in the table above, with the
   methods and attributes listed below.

   Example for an instance write provider:

   .. code-block:: python

       from pywbem_mock import InstanceWriteProvider

       class MyInstanceProvider(InstanceWriteProvider):

           . . .

   a. Optional: It may have an ``__init__()`` method.

      The ``__init__()`` method takes as input parameters at least the
      ``cimrepository`` parameter and passes it to the superclass, and may have
      additional init parameters the user-defined provider requires (that are
      not passed on to the superclass).
      Additional init parameters are possible because the user creates the
      provider object when registering it with
      :meth:`~pywbem_mock.FakedWBEMConnection.register_provider`.
      Having an ``__init__()`` method is optional if no additional init
      parameters are defined.

      Example for an ``__init__()`` method that does not define additional init
      parameters (and that could therefore be omitted):

      .. code-block:: python

          def __init__(self, cimrepository):
              super(MyInstanceWriteProvider, self).__init__(cimrepository)

   b. It must have a declaration of the CIM class(es) served by the provider.

      The CIM class or classes served by the provider are declared with a class
      attribute named ``provider_classnames``. Its value must be a single string
      or a list/tuple of strings with the CIM class names (in any lexical case).

      .. code-block:: python

          provider_classnames = 'CIM_Foo'

      or

      .. code-block:: python

          provider_classnames = ['CIM_Foo', 'CIM_Foo_blah']

   c. It must have an implementation of the Python methods for the WBEM
      operations that are overwritten by the provider.

      This must be all or a subset of the WBEM operations defined for the
      provider type. WBEM operations not implemented in the user-defined
      provider class default to implementations in the superclass.
      See `Python operation methods in user-defined providers`_ for details.

      Example for an ``CreateInstance`` method of an instance write provider
      that just calls superclass method to perform the work (and that could
      therefore be omitted):

      .. code-block:: python

          def CreateInstance(self, namespace, NewInstance):
              return super(MyInstanceWriteProvider, self).CreateInstance(
                  namespace, NewInstance)

   d. Optional: It may define a post register setup method.

      The provider may override the
      :meth:`~pywbem_mock.InstanceWriteProvider.post_register_setup` method
      of the provider superclass to do any special setup it needs. That method
      includes the current connection as a parameter so that WBEM operations
      on the same or on different classes can be executed.
      That method will be called during invocation of
      :meth:`~pywbem_mock.FakedWBEMConnection.register_provider`, after the
      provider registration is successful.

      Example:

      .. code-block:: python

          def post_register_setup(self, conn):
            # code that performs post registration setup for the provider

2. Register the user-defined provider using
   :meth:`pywbem_mock.FakedWBEMConnection.register_provider`.

   This specifies the CIM namespaces for which the user-defined provider will
   be active. These namespaces must already exist in the CIM repository
   if the mock WBEM server.

   .. code-block:: python

       provider = MyInstanceProvider(self.cimrepository)
       conn.register_provider(provider,
                              namespaces=['root/interop', 'root/cimv2'])


.. _`Python operation methods in user-defined providers`:

Python operation methods in user-defined providers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The *Python operation methods* (i.e. the Python methods implementing WBEM
operations) in user-defined providers may:

* provide parameter or CIM repository validation in addition to the normal
  request validation,
* modify parameters of the request,
* abort the request with a :class:`pywbem.CIMError` exception,
* make modifications to the CIM repository.

The Python operation methods may call the corresponding superclass method to
complete the CIM repository modification, or may implement the code to complete
the modification. In any case, once a Python operation method returns, the
CIM repository needs to reflect any changes on CIM objects the WBEM operation
is normally expected to perform.

The Python operation methods have access to:

* methods defined in the superclass of the provider, including
  :class:~pywbem_mock.BaseProvider`
* methods to access the CIM repository using the methods defined in
  :class:`~pywbem_mock.InMemoryRepository`

The input parameters for the Python operation methods will have been already
validated, including:

* The input parameters have the correct Python type as per the descriptions
  in the superclasses.
* The CIM namespace exists in the CIM repository.
* The CIM class of a CIM instance or instance path specified as an input
  parameter exists in that namespace of the CIM repository.
* The CIM properties of a CIM instance specified as an input parameter
  are defined in the CIM class of the instance and have the correct CIM types.
* The CIM instance does not yet exist for CreateInstance and does exist for
  ModifyInstance.

The Python operation methods should raise any exceptions using
:class:`pywbem.CIMError` using the CIM status codes defined in :term:`DSP0200`.


.. _`User-defined instance write providers`:

User-defined instance write providers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: pywbem_mock._instancewriteprovider

.. autoclass:: pywbem_mock.InstanceWriteProvider
    :members:
    :special-members:
    :exclude-members: __init__,__weakref__
    :autosummary:
    :autosummary-inherited-members:


.. _`User-defined method providers`:

User-defined method providers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: pywbem_mock._methodprovider

.. autoclass:: pywbem_mock.MethodProvider
    :members:
    :special-members:
    :exclude-members: __init__,__weakref__
    :autosummary:
    :autosummary-inherited-members:


.. _`Registry for provider dependent files`:

Registry for provider dependent files
-------------------------------------

A faked WBEM connection provides a registry for provider dependent files
in its :attr:`~pywbem_mock.FakedWBEMConnection.provider_dependent_registry`
property of type :class:`pywbem_mock.ProviderDependentRegistry`.

This registry can be used by callers to register and look up the path names of
additional dependent files of a mock script, in context of that mock script.

The pywbemtools project makes use of this registry for validating whether its
mock cache is up to date w.r.t. additional dependent files a mock script has
used.

.. autoclass:: pywbem_mock.ProviderDependentRegistry
    :members:
    :special-members:
    :exclude-members: __init__,__weakref__
    :autosummary:
    :autosummary-inherited-members:


.. _`Configuration of mocked behavior`:

Configuration of mocked behavior
--------------------------------

.. automodule:: pywbem_mock.config
   :members:
