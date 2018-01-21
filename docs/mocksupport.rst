.. _`Mock support`:

Mock support
============

**Experimental:** *New in pywbem 0.12.0 as experimental.*

.. _`Overview`:

Overview
--------

The ``pywbem_mock`` module provides mock support that enables usage of the
pywbem library without a WBEM server.

This is used for testing the pywbem library itself and can also be used for
the development and testing of Python programs using the pywbem library.

The pywbem mock support consists of a :class:`pywbem_mock.FakedWBEMConnection`
class that establishes a *faked connection*. That class is a subclass of
:class:`pywbem.WBEMConnection` and replaces its internal methods that use
HTTP/HTTPS to communicate with a WBEM server with methods that instead operate
on a local in-memory repository of CIM objects (the *mock repository*).

As a result, the operation methods of :class:`~pywbem_mock.FakedWBEMConnection`
are those inherited from :class:`~pywbem.WBEMConnection`, so they have the
exact same input parameters, output parameters, return values, and even most of
the raised exceptions, as when they would be invoked on a
:class:`~pywbem.WBEMConnection` object against a WBEM server.

Each :class:`~pywbem_mock.FakedWBEMConnection` object has its own mock
repository.
The mock repository contains the same kinds of CIM objects a WBEM server
contains: CIM classes, CIM instances, and CIM qualifier types (declarations),
all contained in CIM namespaces.

Because :class:`~pywbem_mock.FakedWBEMConnection` operates only on the mock
repository, the class does not have any connection- or security-related
constructor parameters.

Like :class:`~pywbem.WBEMConnection`, :class:`~pywbem_mock.FakedWBEMConnection`
has a default CIM namespace that can be set upon object creation.

:class:`~pywbem_mock.FakedWBEMConnection` has some additional methods that
provide for adding CIM classes, instances and qualifier types to its mock
repository:

* :meth:`~pywbem_mock.FakedWBEMConnection.add_cimobjects` adds
  the specified :ref:`CIM objects`.

* :meth:`~pywbem_mock.FakedWBEMConnection.compile_mof_str` compiles a MOF
  string and adds the resulting CIM objects.

* :meth:`~pywbem_mock.FakedWBEMConnection.compile_mof_file` compiles a MOF
  file and adds the resulting CIM objects.

In all cases, certain prerequisite CIM objects must already exist in the target
namespace of the mock repository for a new CIM object to be successfully added:
For a CIM class to be added, the superclass of that class as well as CIM
qualifier types for the qualifiers used by that class must exist.
For a CIM instance to be added, its CIM creation class must exist.

Some CIM objects that are used by a CIM object to be added, do not need to
exist and in fact allow forward references:
CIM classes specified in reference properties or in reference parameters of
methods of a class to be added do not need to exist.
CIM classes specified in qualifiers (for example, in the EmbeddedInstance
qualifier) of a class to be added do not need to exist.

There are no setup methods to remove or modify CIM objects in the mock
repository. However, if needed, that can be done by using operation methods
such as :meth:`~pywbem.WBEMConnection.DeleteClass` or
:meth:`~pywbem.WBEMConnection.ModifyInstance`.

The following example demonstrates setting up a faked connection, adding some
CIM objects defined in a MOF string to its mock repository, and performing a
few operations:

.. code-block:: python

    import pywbem
    import pywbem_mock

    # MOF string defining qualifiers, class, and instance
    mof = """
        # CIM qualifier types (declarations)
        Qualifier Key : boolean = false,
            Scope(property, reference),
            Flavor(DisableOverride, ToSubclass);
        Qualifier Description : string = null,
            Scope(any),
            Flavor(EnableOverride, ToSubclass, Translatable);

        # A CIM class declaration
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

        # A CIM instance
        instance of CIM_Foo as $I1 { InstanceID = "I1"; SomeData=3 };
        """

    # Create a faked connection
    conn = pywbem_mock.FakedWBEMConnection(default_namespace='root/cimv2')

    # Compile the MOF string and add its CIM objects to the default namespace
    # of the mock repository
    conn.compile_mof_str(mof)

    # Perform a few operations on the faked connection:

    # Enumerate top-level classes in the default namespace (without subclasses)
    classes = conn.EnumerateClasses();

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
   as the ``__Namespace__`` class/provider or the ``CIM_Namespace``
   class/provider, because these are WBEM server-specific implementations and
   not WBEM request level capabilities.  Note that such capabilities can be at
   least partly built on top of the existing capabilities by inserting
   corresponding CIM instances into the mock repository.


.. _`FakedWBEMConnection methods`:

FakedWBEMConnection methods
---------------------------

:class:`pywbem_mock.FakedWBEMConnection` defines a set of WBEM Server methods
corresponding to the WBEMConnection client methods and mocks the communication with
the WBEMServer) and returns syntatically the same forms of data and
exceptions as the :class:`pywbem.WBEMConnection` methods.  These methods adher to the
behavior requirements defined in the DMTF specification :term:`DSP0200` for
handling requests from the client and returning responses.

Generally it attempts to get data required by the operation from the fake
repository created by the user or to put the data from operations that modify
the server objects (create, modify, and delete operations) into the fake
repository.  However because this is a simulation of a WBEM server and
intended to be used primarily for testing there are a number of limitations
and differences between what these methods do and what a real server would do.

The descriptions below describes differences between the mocker and access to
a real WBEM server.

Generally these methods provide the same behavior as the corresponding
methods in a real WBEM Server and the behavior definitions in
:term:`DSP0200` except for specific limitations and variations.


.. _`Server class operation methods`:

Server class operation methods
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The methods that get data require the target classes to be in the repository
before the mock call.  The methods including limitations are:

- **GetClass:** Behaves like :meth:`~pywbem.WBEMConnection.GetClass`.

- **EnumerateClasses:** Behaves like
  :meth:`~pywbem.WBEMConnection.EnumerateClasses`. Requires that there
  be one or more top level classes (i.e. no superclass) in the repository
  if the request does not include the classname parameter.

- **EnumerateClassNames:** Behaves like
  :meth:`~pywbem.WBEMConnection.EnumerateClassNames`. Requires that there
  be one or more top level classes (i.e. no subclass) in the mock repository
  if the request does not include the classname parameter.

- **CreateClass:** Behaves like
  :meth:`~pywbem.WBEMConnection.CreateClass`. It requires that any superclass
  defined in the new class be in the mock repository.

- **DeleteClass:** Behaves like
  :meth:`~pywbem.WBEMConnection.DeleteClass`. This includes deleting all
  subclasses and instances.

- **ModifyClass:** Currently not implemented. Returns CIMError, not supported


.. _`Server CIMQualifierDeclaration operation methods`:

Server CIMQualifierDeclaration operation methods
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- **SetQualifier:** Behaves like :meth:`~pywbem.WBEMConnection.SetQualifier`.

- **GetQualifier:** Behaves like :meth:`~pywbem.WBEMConnection.GetQualifier`.

- **EnumerateQualifiers:** Behaves like
  :meth:`~pywbem.WBEMConnection.EnumerateQualifiers`.


.. _`Server CIMInstance operation methods`:

Server CIMInstance operation methods
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The methods that get data require instances in the
repository for the instances to be recovered.  We allow some of these methods to
try to return data if the class repository is empty but they may react differently
if there are classes in the repository.

- **GetInstance:** Behaves like :meth:`~pywbem.WBEMConnection.GetInstance` except
  that the LocalOnly option depends only on instance class_origin attribute
  of each property if repo_lite is True

- **EnumerateInstances:** Behaves like
  :meth:`~pywbem.WBEMConnection.EnumerateInstances` except that what it
  returns depends on  the repo_lite WBEMConnection flag.  If repo_lite == True
  only instances of the defined classname are returned if they exist and the
  existence of the target classname is not validated.
  If repo_lite == None, it is assumed that there is no class repository
  so the DeepInheritance, LocalOnly, parameters are ignored and it returns
  only instances of the classname defined on input.

- **EnumerateInstanceNames:** Behaves like
  :meth:`~pywbem.WBEMConnection.EnumerateInstances` except that what it
  returns depends on if there are classes in the repository.

- **CreateInstance**: Behaves like
  :meth:`~pywbem.WBEMConnection.CreateInstance`. This operation requires
  that the corresponding class exist in the repository.  It returns
  not supported if repo_lite is set. It adds the new
  instance to the repository.  It also requires that all key properties be
  in the new_instance parameter since the repository has no way to define
  key property values.

- **ModifyInstance**: Behaves like :meth:`~pywbem.WBEMConnection.ModifyInstance`.
  This operation requires that the corresponding class exist in the
  repository and that the repo_lite flag is False. It modifies an existing
  instance in the repository.

- **DeleteInstance**: Behaves like :meth:`~pywbem.WBEMConnection.DeleteInstance`.
  If the repo_lite flag is set, it does not check for corresponding class.
  In the current implementation it does not attempt to delete references
  to this instance. If the repo_lite flag is not set, it validates the
  existence of the corresponding class before attempting to delete the
  instance.

- **ExecQuery**: Behaves like :meth:`~pywbem.WBEMConnection.ExecQuery` except
  that it returns instances based on a very limited parse of the
  query string (generally the SELECT and FROM clauses. It ignores the WHERE clause).
  It does not execute the select statement itself nor does it parse it completely.
  An incorrect select statement will be ignored other than SELECT and FROM.
  It does check to be sure that the language is one of those normally defined.
  TODO: Not done. Clarify when we finish code.


.. _`Server WBEM associators and reference operation methods`:

Server associators and reference operation methods
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The fake versions of the esponders for these methods allow both class and
instance requests.  At the same time, they allow mock repositories that
would be used to test only instance methods to be built without the
corresponding classes. They include the following methods:

- **AssociatorNames**: Behaves like
  :meth:`~pywbem.WBEMConnection.AssociatorNames`. If a classname is specified
  the source, target, and association classes must be in the repository. If
  an instance target is specified, correct results are returned if classes
  are in the repository. More limited results are returned if repo_lite is
  set (the classes in the repository are ignored so do not need to be
  installed.)

- **Associators**: Behaves like
  :meth:`~pywbem.WBEMConnection.Associators` See AssociatorNames above for
  limitations

- **ReferenceNames**: Behaves like
  :meth:`~pywbem.WBEMConnection.ReferenceNames` See AssociatorNames above
  for limitations

- **References**: Behaves like
  :meth:`~pywbem.WBEMConnection.References` See AssociatorNames above for
  limitations.


.. _`Server InvokeMethod  operation methods`:

Server InvokeMethod operation method
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The fake InvokeMethod behaves like :meth:`~pywbem.WBEMConnection.InvokeMethod`.

Since this method is outside the normal intrinsic WBEM operations in that it
generally implies a side effect and not just a get/put interface to a
repository.  It could not be implemented simply to get objects from the
repository or put them into the repository.

The fake InvokeMethod requires a callback to a user defined function
based on the namespace, objectname, and method defined in the call.\
Because the nature of InvokeMethod, there was no way to define a standard means
to get information just from the mock repository for the responses.

This user defined function acts as the WBEM server implementation of the
InvokeMethod, processing input parameters and returning a return value and
output parameters.

The user must create a function that will be executed as a callback for each
method that is to be tested. This method is attached to the mock repository
through :meth:`~pywbem_mock.FakedWBEMConnection.add_method_callback` which
defines the namespace, class, and methodname for the InvokeMethod and the
callback method to be executed.


This user defined callback method should have the signature defined in
:meth:`~pywbem_mock.FakedWBEMConnection.add_method_callback`.

The callback is expected to return a tuple consiting of ReturnValue and
a `NocaseDict` containing any output parameters. The following is an example
of the definition and execution of InvokeMethod.

.. code-block:: python

    import pywbem
    import pywbem_mock

    def method1_callback(self, conn, methodname, local_object, params=None):
        """ Callback for method1"""

        # this method can access the repository through pywbem client calls
        # in this case the CIMClassName in local_object
        cl = conn.GetClass(local_object)

        rtn_val = 0  # return 0 as a return code
        rtn_params = NocaseDict('OP1' : 'Some return Data')
        return (rtn_val, rtn_params)

    mof = """
        Qualifier In : boolean = true,
            Scope(parameter),
            Flavor(DisableOverride, ToSubclass);

        Qualifier Key : boolean = false,
            Scope(property, reference),
            Flavor(DisableOverride, ToSubclass);

        Qualifier Out : boolean = false,
            Scope(parameter),
            Flavor(DisableOverride, ToSubclass);
        class TST_Class {
            string InstanceID;
                [Description("Sample method with input and output parameters")]
            uint32 Method1(
                [IN, Description("Input Param1")]
              string IP1,
                [IN ( false), OUT, Description("Response param 1")]
              string OP1);
    """

    # Create a faked connection
    conn = pywbem_mock.FakedWBEMConnection(default_namespace='root/cimv2')

    # Compile the MOF string and add its CIM objects to the default namespace
    # of the mock repository
    conn.compile_mof_str(mof)

    # Add the defined class and method to the defaault repository.
    conn.add_method_callback('TST_Class', 'Method1',
                          self.method1_callback)

    # execute the InvokeMethod as a static (class level) method.
    params = [('IP1', 'someData')]
    result = conn.InvokeMethod('Method1', 'TST_Class', Params=params)

    print('return value %s' result[0])
    print('Return parameters %s' % (result[1],))

.. _`Server pull operations methods`:

Server pull operations methods
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The fake pull operations implement all of the Open and Pull WBEM server
methods with the same behavior as the real operations except as follows.

- Filter Query Language parameters are ignored and the full instance responses
  generated. Since FQL only filters the set of instanced defined by
  the corresponding request (i.e. Open/Pull EnumerateInstances simply
  filters instances that would be acquired by EnumerateInstances. This means
  that these methods can be used but may return more instances than would
  be returned without the filters.

- The ContinueOnError has no real meaning since we do not have a means to
  introduce an error into a pull operation in process.

- The timeout is ignored unless the faked response time on operations property
  is set.

- TODO Should we name the pull operations to be complete


.. _`Pywbem ClientIter... Operations`:

Pywbem ClientIter... Operations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Because these opertions do not directly call the server but are simply a
layer on top of the basic server communication methods like
EnumerateInstances, OpenEnumerateInstances, etc. hese operations all execute
with the same behavior as the real operations including use of the
``use_pull_operations`` constructor attribute except:

- When the pull operations are used, the same limitations as the faked
  pull operations themselves exist (see `Server pull operations methods`).


.. _`Building the mock repository`:

Building the mock repository
----------------------------

Having data with which to respond to requests from a client is required for
the faked connection to do useful work.  Therefore, in incorporates a
repository which can be built as part of a test.

There are three methods in the faked connection to add data to the
mock repository

1. Add pywbem CIM Objects directly to the repository.
   This is the method :meth:`~pywbem_mock.FakedWBEMConnection.add_cimobjects`. The
   goal of this operation is to be able to add objects independently of
   the normal critera of what is required.  Thus you can add instances withou
   having corresponding classes in the repository or add classes without
   having the corresponding qualifier declarations.

2. Compile pywbem objects from strings or file input with the pywbem MOF compiler
   from strings.
   These  methods allow the user to build correctly a  defined repository
   easily simply by defing the MOF for the objects to be inserted in the
   repository. In order to compile correctly each object type to be compiled
   must be able to find any prerequisites in the repository. Thus to compile
   MOF instances, the CIMClasses for those instances must be in the repository
   and to compile MOF CIM classes the CIM qualifier declarations must be in
   the repository already.

   There are two different methods and the only difference is whether they
   compile from a string input for the MOF or from MOF in a file.

   - The method :meth:`~pywbem_mock.FakedWBEMConnection.compile_mof_file` compiles
     MOF into the repository from a file.

   - The method :meth:`~pywbem_mock.FakedWBEMConnection.compile_mof_str` compiles
     MOF into the repository from python string.


.. _`Examples`:

Examples
--------

.. _`Add object with add_cimobjects()`:

Add object with add_cimobjects()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    import pywbem
    import pywbem_mock

    tst_namespace = 'root/blah'
    conn = pywbem_mock.FakedWBEMConnection()

    # build the qualifier declarations
    q1 = pywbem.CIMQualifierDeclaration('FooQualDecl1', 'uint32')
    q2 = pywbem.CIMQualifierDeclaration('FooQualDecl2', 'string',
                                        value='my string')

    conn.add_cimobjects([q1, q2], tst_namespace)

    # test the WBEMConnection GetQualifier and EnumerateQualifiers methods
    rtn_q1 = conn.GetQualifier('FooQualDecl1', namespace=tst_namespace)

    q_rtn = conn.EnumerateQualifiers(namespace=tst_namespace)


.. _`Define Association`:

Define Association
^^^^^^^^^^^^^^^^^^

TODO add the define association example.

TODO add more examples if necessary


.. _`FakedWBEMConnection`:

FakedWBEMConnection
-------------------

.. # Note: The pywbem_mock._wbemconnection_mock module docstring is a dummy.

.. autoclass:: pywbem_mock.FakedWBEMConnection
   :members:
