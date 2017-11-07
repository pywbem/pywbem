.. _`Mock support`:

Mock support
============

.. _`Overview`:

Overview
--------

The pywbem PyPI package provides unit testing support for pywbem users via its
``pywbem_mock`` Python package. This package allows users of pywbem to
define fake WBEMConnections and :class:`pywbem.CIMClass`,
:class:`pywbem.CIMInstance`, and :class:`pywbem.CIMQualifierDeclaration`
objects that are be processed by the methods of the faked connection.
This creates a local in-process fake WBEM Server with a CIM object repository
and the capability to respond to WBEM requests capabilities equivalent
to a WBEM Server.

The fake WBEMConnection is initialized by creating an instance of the
:class:`pywbem_mock.FakedWBEMConnection_mock` class instead of the
:class:`pywbem.WBEMConnection` class and then adding CIM Objects
to the fake repository.

The following example demonstrates, defining  a  faked connection, adding
objects defined in MOF to the repository and using WBEMConnection methods
including GetClass, EnumerateClasses, etc. to access the objects in the
repository.

.. code-block:: python

    import pywbem
    import pywbem_mock

    conn = pywbem_mock.FakedWBEMConnection()

    # MOF string defining qualifiers, class, and instance
    mof = """
        Qualifier Key : boolean = false,
            Scope(property, reference),
            Flavor(DisableOverride, ToSubclass);
        Qualifier Description : string = null,
            Scope(any),
            Flavor(EnableOverride, ToSubclass, Translatable);

        #  Class MOF
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

        # Sample instances.
        instance of CIM_Foo as $I1 { InstanceID = "I1"; SomeData=3 };
        """

    conn.compile_mof_str(mof)

    # examples of pywbem WBEMConnection operations on the repository
    classes = conn.EnumerateClasses();   # enumerate classes
    qd = conn.GetQualifier('Description')   # # get the description qualifier
    classes2 = conn.EnumerateClasses(classname='CIMFoo')
    my_class = conn.GetClass('CIMFoo')   # get a single class
    inst = conn.GetInstance(CIMInstanceName('CIMFoo', kb={'InstanceID': "I1"}

TODO confirm namespaces in the above example

Generally the pywbem mock environment supports:

1. All of the :class:`pywbem.WBEMConnection` request methods that communicate
   with the WBEM server (see below for list of operations supported and their
   limitations).
2. Multiple namespaces and the pywbem DEFAULT_NAMESPACE.
3. Gathering time statistics and delaying responses for a predetermined
   time.
4. :class:`pywbem.WBEMConnection` logging except that there are no HTTP entries
   in the log.

It does this by mocking WBEM Server requests and responses at a level below the
:class:`pywbem.WBEMConnection` methods such as :meth:`pywbem.WBEMConnection.GetClass',
etc. but before the requests are formatted into HTTP.  pywbem_mock also provides
a cim object repository (similar to the one a WBEM server provides) built by
the user into which the CIM objects are are inserted for any given
test.

Pywbem mock does NOT support:

1. CIM/XML protocol security and security constructor parameters of
   :class:`pywbem.WBEMConnection`.
2. Dynamic WBEM Server providers in that the data for responses is from the
   fake repository that is built before the request rather than from resources
   defined by the WBEM server. Thus it does not provide for creating
   instance providers into FakedWBEMConnection which could simulate
   real instance providers.  This means that all instances require that the
   complete instance name be defined before the instance is added to the
   repository or in the case of CreateInstance all key properties must be in
   the new_instance.
3. Processing of queries defined for ExecQuery in
   languages like CQL and WQL.  The mocker parses only the very
   general portions of the query for class/instance name and properties)
4. Filter processing of the FQL(FQL, see DSP0212) filter query language parameter
   QueryFilter used by the Open... operations because it does not implement the
   parser/processor for the FQL language.  It returns the same data as if the
   filter did not exist.
5. It does not provide data for the last_request variables in :class:`pywbem.WBEMConnection`
   including `last_request`, `last_raw_request`, `last_reply`, `last_raw_reply`,
   `last_request_len`, or `last_reply_len`.

6. It does not return the http entries in logging within WBEMConnection
   because it does not actually build the http requests or responses.

7. It does not support generating indications from the fake server.

8. It does not support some of the functionality that may be implemented in
   real WBEM Servers such as the __Namespace__ class/provider or the
   CIMNamespace class/provider since these are WBEM server specific
   implementation and not WBEM request level capabilities.  Note that these
   capabilities can be at least partly built on top of the existing
   capabilities by inserting data into the
   :class:`pywbem_mock.FakedWBEMConnection` repository.


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
    be one or more top level classes (i.e. no subclass) in the fake repository
    if the request does not include the classname parameter.

  - **CreateClass:** Behaves like
    :meth:`~pywbem.WBEMConnection.CreateClass`. It requires that any superclass
    defined in the new class be in the fake repository.

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
 instance requests.  At the same time, they allow fake repositories that
 would be used to test only instance methods to be built without the
 corresponding classes. They include the following methods:

  - AssociatorNames: Behaves like
    :meth:`~pywbem.WBEMConnection.AssociatorNames`. If a classname is specified
    the source, target, and association classes must be in the repository. If
    an instance target is specified, correct results are returned if classes
    are in the repository. More limited results are returned if repo_lite is
    set (the classes in the repository are ignored so do not need to be
    installed.)

  - Associators: Behaves like
    :meth:`~pywbem.WBEMConnection.Associators` See AssociatorNames above for
    limitations

  - ReferenceNames: Behaves like
    :meth:`~pywbem.WBEMConnection.ReferenceNames` See AssociatorNames above
    for limitations

  - References: Behaves like
    :meth:`~pywbem.WBEMConnection.References` See AssociatorNames above for
    limitations.

.. _`Server InvokeMethod  operation methods`:

Server InvokeMethod operation method
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The fake InvokeMethod behaves like :meth:`~pywbem.WBEMConnection.InvokeMethod`.
Since this method is outside the normal operations in that it generally implies
some sort of side effect it could not be implemented simply to get objects
from the repository or put them into the repository.

the fake InvokeMethod requires a callback to a user defined function
based on the namespace, class, and method defined in the call. Because the
very nature of invoke method, there was no way to define a standard means
to get information just from the fake repository for the responses.

TODO define further.

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


.. _`Building the Fake Repository`:

Building the Fake Repository
----------------------------

Having data with which to respond to requests from a client is required for
the Fake WBEMConnection to do useful work.  Therefore, in incorporates a
repository which can be built as part of a test.

There are three methods in the fake WBEMConnection to add data to the
mock repository

1. Add pywbem CIM Objects directly to the repository.
   This is the method :meth:`~pywbem.FakedWBEMConnection.add_cimobject`. The
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

   - The method :meth:`~pywbem.FakedWBEMConnection.compile_mof_file` compiles
     MOF into the repository from a file.

   - The method :meth:`~pywbem.FakedWBEMConnection.compile_mof_str` compiles
     MOF into the repository from python string.


.. _`Examples`:

Examples
--------

.. _`Add object with add_CIMObject`:

Add object with add_CIMObject
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

.. automodule:: pywbem_mock._wbemconnection_mock

.. autoclass:: pywbem_mock.FakedWBEMConnection
   :members:


