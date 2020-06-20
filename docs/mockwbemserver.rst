.. _`Mock WBEM server`:

Mock WBEM server
================

**Experimental:** *New in pywbem 0.12.0 as experimental.*

.. _`Overview`:

Overview
--------

The pywbem package contains the ``pywbem_mock`` subpackage which provides mock
WBEM server support that enables using the pywbem library without a WBEM
server. This subpackage is useful for testing the pywbem library itself as well
as for the development and testing of Python programs that use the pywbem
library.

pywbem_mock  contains the :class:`pywbem_mock.FakedWBEMConnection`
class that establishes a *faked connection*. That class is a subclass of
:class:`pywbem.WBEMConnection` and replaces its internal methods that use
HTTP/HTTPS to communicate with a WBEM server with methods that communicate
with  an in-process in-memory repository of CIM objects (the *mock repository*).

:class:`~pywbem_mock.FakedWBEMConnection` acts as both the client API and a
in-process fake WBEM server. It includes methods to establish, configure, and
visualize this fake WBEM server.  As a result, the operation methods of
:class:`~pywbem_mock.FakedWBEMConnection` are those inherited from
:class:`~pywbem.WBEMConnection`, so they have exactly the same input
parameters, output parameters, return values, and even most of the raised
exceptions, as when invoked on a :class:`~pywbem.WBEMConnection` object against
a WBEM server.

Each :class:`~pywbem_mock.FakedWBEMConnection` object creates its own mock
repository that contains the same kinds of CIM objects a WBEM
server repository contains: CIM classes, CIM instances, and CIM qualifier
declarations types contained in CIM namespaces. Because
:class:`~pywbem_mock.FakedWBEMConnection` operates only on the mock repository,
the class does not have any connection or security-related constructor
parameters.

Like :class:`~pywbem.WBEMConnection`, :class:`~pywbem_mock.FakedWBEMConnection`
has a default CIM namespace that is created upon
:class:`~pywbem_mock.FakedWBEMConnection` instance creation;
:class:`~pywbem.WBEMConnection` allows defining additional namespaces with
:meth:`~pywbem_mock.FakedWBEMConnection.add_namespace()` .

:class:`~pywbem_mock.FakedWBEMConnection` has additional methods that
provide for adding CIM classes, instances and qualifier types to its mock
repository. See :ref:`Building a mock repository` for details.

The repository must contain the CIM classes, CIM instances and CIM qualifier
declaration types that are needed for the operations that are invoked. This
results in a behavior of the faked operations that is close to the behavior of
the operations of a real WBEM server. The CIM repository can be build from
pywbem python classes for CIMClass, CIMInstance or CIMQualifier using methods
in :class:`~pywbem_mock.FakedWBEMConnection` as defined in section
:ref:`Building a mock repository`.

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
   limitations) except for specific limitations
   (``DeleteClass`` and ``ExecQuery``).
2. Multiple CIM namespaces and a default namespace on the faked connection.
3. Gathering time statistics and delaying responses for a predetermined time.
4. :class:`~pywbem.WBEMConnection` logging except that there are no HTTP entries
   in the log.
5. User-defined providers that replace the WBEM  server responder for specific
   request methods, CIM classes, and namespaces. See :ref:`User-defined
   providers`.

Pywbem mock does NOT support:

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
   as the `__Namespace__` class/provider .  Note that such capabilities can be at
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
  exceptions and requirements:
  For class-level use, the mock repository must be in full mode and the source,
  target, and association classes and their subclasses must exist in the mock
  repository.
  For instance-level use, correct results are returned if the mock repository
  is in full mode and the the source, target, and association classes and their
  subclasses exist in the repository.

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

The mock repository should contain CIM qualifier declarations, CIM classes,
and CIM instances to be required by the user. These are created as part of
the setup of any particular pywbem mock environment. Thus, if the user only
requires CIM_ComputerSystem, only that class and its dependent classes and
qualifier declarations need be in the repository along with instances of the
classes that will satisfy the client methods executed.

The classes :class:`~pywbem_mock.FakedWBEMConnection` and
:class:`~pywbem_mock.DMTFCIMSchema` provide the tools to build the mock
repository.

There are two ways to build a mock repository:

* Directly from pywbem CIM objects (:class:`~pywbem.CIMClass`,
  :class:`~pywbem.CIMInstance` or :class:`~pywbem.CIMQualifierDeclaration`,
  etc). The method :meth:`~pywbem_mock.FakedWBEMConnection.add_cimobjects`
  installs these objects into the CIM repository

* From MOF definitions of the objects (which can be a string or a file):

  * Build from MOF definitions of the objects which are compiled into the
    repository. See :meth:`~pywbem_mock.FakedWBEMConnection.compile_mof_string`
    and :meth:`~pywbem_mock.FakedWBEMConnection.compile_mof_file`.

    If an instance compiled with the MOF compiler duplicates the path of an
    existing instance in the repository, the existing instance will modified
    because the MOF compiler uses ModifyInstance on the request if the
    CreateInstance fails. When defining new instances in MOF, the corresponding
    class must exist in the repository but not necessarily in the current MOF
    file.

  * Build MOF qualifier declarations and classes directly from the DMTF
    CIM schema by downloading the schema from the DMTF and selecting all
    or part of the schema to compile. This automatically compiles all
    qualifier declarations into the mock repository and allows setting up
    a partial class repository (i.e. selected classes) with a single
    method call. See section `DMTF CIM schema download support`_ and the
    :meth:`~pywbem_mock.FakedWBEMConnection.schema_pragma_file` method.

It may take a combination of all of the above methods to build a schema
that satisfies a particular usage requirement including:

1. Build the DMTF CIM classes and CIM qualifier declarations from the
   DMTF schema. This is easy to code, and eliminates errors defining
   components. It also loads all qualifier declarations.

2. Build non-DMTF classes (subclasses, etc.) by defining either MOF for the
   classes and compiling or directly building the pywbem CIM classes.

3. Build CIM instances by defining MOF and compiling or directly building
   the pywbem CIM instances. Often MOF is easier for this because it
   simplifies the definition of association instances with the instance
   alias.

4. Register user-defined providers for which the mock server
   is expected to respond. See :ref:`User-defined providers`

Since building a working CIM repository with all of the required elements
to successfully execute client operations can mean understanding the CIM model
dependencies, the pywbem MOF compiler provides support for:

1. Automatically including all qualifier declarations if classes are added
   with the method :meth:`~pywbem_mock.FakedWBEMConnection.schema_pragma_file`
   or the :class:`DMTFCIMSchema`.

2. Adding dependent classes from the DMTF schema in the case where they are
   missing in the compiled mof and the compiler search path includes the
   MOF directory of the DMTF CIM schema.  This include superclasses,
   reference classes defined in reference properties and parameters, and
   the class referenced through the EmbeddedInstance qualifier. Thus, the
   user does not have to track down those dependent classes to be able to
   create a working mock repository.

This means that the user creating a mock repository only needs to know the DMTF
schema to be used and the leaf classes required. All qualifier declarations and
classes upon which these leaf classes depends are automatically installed into the
CIM repository. It also means that there is normally no reason to compile the
complete DMTF schema which is much larger than the classes required for most
test environments.


.. _`Example: Set up qualifier types and classes DMTF CIM schema`:

Example: Set up qualifier types and classes in DMTF CIM schema
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This example creates a faked connection using ``root/interop`` as the default
namespace and compiles the classes defined in the list 'classes' from DMTF
schema version 2.49.0 into the repository along with all of the qualifier
declarations defined by the DMTF schema and any dependent classes
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

    # Compile dmtf schema version 2.49.0, the qualifier declarations and
    # the classes in 'leaf_classes' and all dependent classes and keep the
    # schema in directory my_schema_dir

    schema = DMTFCIMSchema(2, 49, 0), "my_schema_dir", leaf_classes,
                           verbose=True)
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
adds two class instances and one association instance from their CIM objects
using the ``add-cimobjects`` method.

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

There is a default-namespace created when
:class:`pywbem_mock.FakedWBEMConnection` is created from either the
`default_namespace` of the constructor or with the system default of
`root/cimv2`

However, a working WBEM environment normally includes at least two namespaces

1. An :term:`interop namespace` which contains the parts of the model that deal
   with the WBEM server itself (ex. CIM_Namespace, CIM_ObjectManager, etc.) and
   which must be publically discoverable without the user knowing what CIM
   namespaces exist in the WBEM server The DM

2. A user namespace where the CIM classes for the user model

Pywbem_mock includes a user-defined provider for the CIM_Namespace class that
can be enabled by adding code similar to the following to the setup of a
mock environment.

.. code-block:: text

    # install the CIM_Namespace class either by directly compiling the class
    # or using the DMTFCIMSchema class to compile the class

    provider = CIMNamespaceProvider(self.cimrepository)
    interop_namespace = "interop"   # or root/interop
    conn.add_namespace(interop_namespace)
    conn.register_provider, namespaces=interop_namespace)


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

Also, the :meth:`pywbem_mock.WBEMConnection.InvokeMethod` on
:class:`pywbem_mock.FakedWBEMConnection` client operation depends on a specific
responder method in the WBEM server since the behavior of WBEM server methods
is dependent on the specific method.

To meet these needs, pywbem_mock has implemented the capability to create
:term:`user-defined providers <user-defined provider>` that become request
responders for defined classes and operations which can can manipulate the
client input and generate responses specific for defined CIM classes.

User-defined providers can be written by the user by defining subclasses of
specific provider classes used by the fake WBEM server and registering these
classes as providers using
:meth:`~pywbem_mock.FakedWBEMConnection.register_provider`.

Pywbem defines user-defined provider types so that specific request operations
can be executed for each provider type.


.. table:: Pywbem_mock provider types

    ====================== =================== ======================== ================================
    Provider Type          type name           CIM Request Operations   Default provider class
    ====================== =================== ======================== ================================
    method                 "method"            InvokeMethod             :ref:`Method Provider`
    instance write         "instance-write"    CreateInstance           :ref:`Instance Write Provider`
    instance write         "instance-write"    ModifyInstance           :ref:`Instance Write Provider`
    instance write         "instance-write"    DeleteInstance           :ref:`Instance Write Provider`
    ====================== =================== ======================== ================================

Each user-defined provider is a Python class which is a subclass
of the corresponding default provider for the provider type as defined in
the previous table.


.. _`Creating user-defined instance providers`:

Creating user-defined instance providers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
 User-defined instance providers can override the default implementations for
 the methods defined in the above table (``CreateInstance``, ``ModifyInstance``,
 and ``DeleteInstance``). These methods are defined in a user-defined class
 that subclasses :class:`pywbem_mock.InstanceWriteProvider`. The details of
 defining this provider are in section :ref:`Instance Write Provider`.

The following is a simple example of a user-defined instance write provider

.. code-block:: python

    import pywbem
    import pywbem_mock

    from pywbem_mock import InstanceWriteProvider, CIMError, \
        CIM_ERR_METHOD_NOT_SUPPORTED

    class CIMFooUserInstanceProvider(InstanceWriteProvider):
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
            super(UserInstanceTestProvider, self).__init__(cimrepository)

        def CreateInstance(self, namespace, NewInstance):
            """Create instance just calls super class method"""

            NewInstance.properties["myproperty"] = "Fixed"

            return super(UserInstanceTestProvider, self).CreateInstance(
                namespace, NewInstance)

        def ModifyInstance(self, ModifiedInstance, IncludeQualifiers=None,
                           PropertyList=None):
            """Disallows ModifyInstance"""

            raise CIMError('CIM_ERR_NOT_SUPPORTED',
                           "{0} provider does not allow ModifyInstance.".format(
                           self.__class__.__name__))

        def DeleteInstance(self, InstanceName):
            """Test Create instance just calls super class method"""
            # pylint: disable=useless-super-delegation
            return super(UserInstanceTestProvider, self).DeleteInstance(
                InstanceName)

    def post_register_setup(self, conn):
        """Execute setup code after provider is registered."""
        pass


.. _`Creating user-defined method providers`:

Creating user-defined method providers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A user-defined method provider provides a server responder for specific
CIM classes and namespaces.  If no user-defined method provider exists for
the requested CIM class and namespace, the default is an exception since there
is not normal behavior for a method

The detailed requirements for implementing a user-defined method provider are
in section :ref:`Method Provider`.

The following is an example of a method provider:

.. code-block:: python

    import pywbem
    import pywbem_mock

    from pywbem_mock import MethodProvider, CIMParameter, CIMError, \
        CIM_ERR_NOT_FOUND, CIM_ERR_METHOD_NOT_AVAILABLE

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
                    _format("class {0|A} does not exist in CIM repository, "
                            "namespace {1!A}", classname, namespace))

            if isinstance(ObjectName, CIMInstanceName):
                instance_store = self.get_instance_store(namespace)
                inst = self.find_instance(objectname, instance_store,
                                          copy=False)
                if inst is None:
                    raise CIMError(
                        CIM_ERR_NOT_FOUND,
                        _format("Instance {0|A} does not exist in CIM repository, "
                                "namespace {1!A}", ObjectName, namespace))

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
