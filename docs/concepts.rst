
.. _`Concepts`:

Concepts
========

This sections defines some of the basic concepts that form the basis for
Pywbem including the architecture, basic CIM/WBEM components, operations
and indications.

It also defines the differences between some of the methods defined in
Pywbem cim_operations, in particular, the pull operations and the iter
operations.

.. contents:: Chapter Contents
   :depth: 2


.. _`The CIM/WBEM architecture`:

The CIM/WBEM architecture
-------------------------

TODO: Write this section

.. _`The CIM model and CIM objects`:


The CIM model and CIM objects
-----------------------------

TODO: Write this section


.. _`WBEM operations: Communicating with the WBEM Server`:

WBEM Operations: Communicating with the WBEM Server
---------------------------------------------------

TODO: Write this section

.. _`WBEM operations overview`:

WBEM operations overview
^^^^^^^^^^^^^^^^^^^^^^^^

TODO Write this section

.. _`Traditional operations`:

Traditional operations
^^^^^^^^^^^^^^^^^^^^^^

TODO - Write this section

.. _`Pull operations`:

Pull operations
^^^^^^^^^^^^^^^

The DMTF CIM/XML pull operations allow the WBEM client to break the
monolithic instance operations for requests that deliver multiple objects
into multiple requests/responses executed as a sequence of requests to limit
the size of individual responses.

NOTE: The pull operations were added to pywbem in version 0.9.0.

They were created to reduce scalability issues with extremely large
responses from servers for instance enumerate operations (EnumerateInstances,
Associators, and References) that were causing resource problems in both
clients and servers. The pull operations allow the client to break large responses up into
multiple smaller responses and allowing filtering of the responses to be
performed by the server.

A central concept of pulled enumeration operations is the `enumeration
session`, which provides a context in which the operations perform their
work and which determines the set of instances or instance paths to be
returned. To process the operations of an `enumeration session`, some
parameters of the open operation need to be maintained as long as the
`enumeration session` is open. In addition, some state data about where the
`enumeration session` is with regard to instances or instance paths already
returned must be maintained.

A successful `Open...` operation establishes the `enumeration session` and
returns an enumeration context (Pybbem result.context) value representing
that session. This value is used as a parameter in subsequent
Pull operations on that enumeration session.

In general the pull operations replace the single  monolithic request/response (ex. EnumerateInstances)
that returns all instances in a single response  with a pattern (enumeration sequence)
that is based on three operations:

* `Open...` to open the request enumeration session to the WBEM Server and
  optionally request objects be returned.
* `Pull...` to continue retrieving objects from the WBEM Server after a
  successful `Open...`. The client normally continues to execute pulls until an
  exception or end-of-sequence flag is received.
* `CloseEnumeration` Close an `enumeration sequence` before it is complete. This
  request is ONLY used to execute early close; when the eos flag is returned or
  and error is returned (if `ContinueOnError` is not set),
  the session is closed by the server.

The open... requests use the same request parameters as the traditional
operations to define the basic characteristics of the  corresponding
traditional operation (object name, propertylists, etc) and add several more
request parameters to control the flow of responses (response size,
timeouts, etc.). In addition they add two new request parameters
(`QueryFilter` and `QueryFilterLanguage`) to request that the server filter
the responses and return only instances/paths that match the filter.

Relation to traditional operations
""""""""""""""""""""""""""""""""""

The convention for the pull operation naming is as follows:

1. Prepend the traditional operation name with `Open` and `Pull`
2. Suffix the pull operations that return both instances and paths with `WithPath`
3. Change the name suffix on operations that return path information from `Names` to
   `Paths` to reflect that these operations are returning complete instance
   paths with host and namespace included.  The `Exec` was dropped from the
   name for the `OpenQueryInstances`.

The pull operations parallel to the traditional operations as follows:

======================== ===============================================
*Traditional Operation*  *Pull Operations*
------------------------ -----------------------------------------------
EnumerateInstances       OpenEnumerateInstances / PullInstancesWithPath
EnumerateInstanceNames   OpenEnumerateInstancePaths / PullInstancePaths
Associators              OpenAssociatorInstances / PullInstancesWithPath
AssociatorNames          OpenAssociatorInstancePaths / PullInstancePaths
References               OpenReferenceInstances / PullInstancesWithPath
ReferenceNames           OpenReferenceInstancePaths / PullInstancePaths
ExecQuery                OpenQueryInstances / PullInstances
======================== ===============================================

The pull operations are defined only for instances.  There are NO pull
operations for CIM classes, the for CIM qualifier declarations or for method
invocations.

Pull operation responses
""""""""""""""""""""""""

Each pull operation request returns a Python namedtuple result that
consists of the following named components:

* `eos` - A boolean flag that indicates the end of the enumeration sequence.
  As along as this returned flag is false, the server has more objects to return.
  If this flag is true in a response, the server has no more objects to
  return and it has closed the enumeration sequence.

* `context` - An opaque identifier that **must be** returned to the server with
  subsequent pull requests to continue the enumeration sequence. The context
  received with a response within an enumeration must be returned with the
  next request since the context may uniquely define not only the enumeration
  sequence but the segement returned in the response.

* `instances` or `paths` - A list of pywbem objects returned from the
  server.  The requests that demand instances return the `instances` entry
  in the namedtuple and those that request paths return paths in the `path` entry
  in the namedtuple.

Pull enumeration sequence code pattern
""""""""""""""""""""""""""""""""""""""

Generally the pattern for requesting from a server using the pull operations
is as follows:

::

    # open the enumeration sequence
    result = open...(uri, ...)
        ... process the objects return in result.xx
    # while more objects exist in the server, loop to pull objects
    while not result.eos
        result = pull...(result.context, <MaxObjectCount>, ...)
            ... process the objects return in result.xx

The user opens the request with the open request and if that is successful,
and does not return the end-of-sequence flag the result (`eos`) executed the
pull request to continue receiving objects within the enumeration sequence.
Each pull request MUST include the enumeration context from the previous
response (`context` in the result tuple).

The pull sequence may be terminated by executing a
[`CloseEnumeration()`](https://pywbem.readthedocs.io/en/latest/client.html#pyw
bem.WBEMConnection.CloseEnumerate) to terminate the pull sequence.  However,
this is optional and used only to close pull sequences before the `eos` has
been received.

Common Pull Operation Request Input Arguments
"""""""""""""""""""""""""""""""""""""""""""""

The following are the request arguments that are common across all of the Pull requests.

Open requests
'''''''''''''

* FilterQuery Language and FilterQuery - These input parameters specify a
  filter query that acts as an additional restricting filter on the set of
  enumerated instances/paths returned. WBEM servers must support filter
  queries in pulled enumerations and must support the DMTF Filter Query
  Language(FQL, see DMTF DSP0212) as a query language. If a WBEM server
  accepts a request with the FilterQuery parameter defined it MUST filter the
  response. NOTE: The query and query language defined for the
  OpenQueryInstances is NOT FQL but the same query languages defined for the
  execQuery request.

* OperationTimeout - Determines the minimum time the WBEM server shall
  maintain the opened enumeration session after the last Open or Pull
  operation (unless the enumeration session is closed during the last
  operation). If the operation timeout is exceeded, the WBEM server may close
  the enumeration session at any time, releasing any resources allocated to
  the enumeration session. An OperationTimeout of 0 means that there is no
  operation timeout. That is, the enumeration session is never closed based on
  time. If OperationTimeout is NULL, the WBEM server shall choose an operation
  timeout.

* ContinueOnError - This input parameter, if true, requests a continuation
  on error, which is the ability to resume an enumeration session successfully
  after a Pull operation returns an error. If a WBEM server does not support
  continuation on error and `ContinueOnError` is true, it shall return a failure
  with the status code CIM_ERR_CONTINUATION_ON_ERROR_NOT_SUPPORTED. Most servers
  today do not support `ContinueOnError`.

* MaxObjectCount - Defines the maximum number of instances or instance paths
  that the open operation can return. Any uint32 number is valid, including 0.
  The WBEM server may deliver any number of instances or instance paths up to
  `MaxObjectCount` but shall not deliver more than `MaxObjectCount` elements. The
  default for this is zero so that the WBEM server does not deliver objects in
  the response unless a `MaxObjectCount` is specifically defined. The WBEM
  server may limit the maximum size of this request parameter.

Pull requests
'''''''''''''

* Context - This is the EnumerationContext defined in the specification. It
  is an opaque string returned from the previous open or pull for this
  enumeration sequence as part of the result tuple (result.context).

* MaxObjectCount - This required input parameter defines the maximum number
  of instances or instance paths that may be returned by this Pull operation.
  Any uint32 number is valid, including 0. The WBEM server may deliver any
  number of instances or instance paths up to `MaxObjectCount` but shall not
  deliver more than `MaxObjectCount`. The WBEM client may use a `MaxObjectCount`
  value of 0 to restart the operation timeout for the enumeration session when
  it does not need to not retrieve any instances or instance paths.

Close request
'''''''''''''

* Context - This is the EnumerationContext defined in the specification. It
  is an opaque string returned from the previous open or pull for this
  enumeration sequence as part of the result tuple (result.context).

Differences from traditional operations
"""""""""""""""""""""""""""""""""""""""

The pull operations differ from the traditional operations in the several ways:

1. They allow filtering the response in the WBEM Server which can represent
   a significant resource saving if only selected instances from a large
   response are really required.
2. They limit the amount of memory used by the server since the server need
   not process the complete request before returning information to the client
3. They limit the memory used by the client since it can define the maximum
   size of any response.
4. They allow the client to terminate an enumeration early with the CloseEnumeration.
5. They allow the server and client to receive partial responses in that the
   client receives potentially an error response on each segment of the
   response, not the overall response.
6. They provide a more consistent inclusion of the path component in the responses.


.. _`Iter operations`:

Iter operations
^^^^^^^^^^^^^^^

The iterable operation extensions (short: *iter operations*) are a set of
methods added to
[`pywbem.WBEMConnection`](https://pywbem.readthedocs.io/en/latest/client.html#
pywbem.WBEMConnection) class in pywbem version 0.10.0 to simplify the use of
the pull vs. traditional operations.

These are specific to PyWBEM.

Why the iter operations exist
"""""""""""""""""""""""""""""

The iter operations provide:

1. An interface that is the same whether the user is executing the pull
operations or their equivalent traditional operations.

2. An interface that use the Python iterator paradigm to get instances or
instance paths in place of lists or tuples as for the pull operations and
traditional operations.

3. An interface that allows the user to utilize pull operations or
traditional operations with just an attribute change in WBEMConnection.

4. An interface that automatically attempts to use pull operations and if a
particular WBEM server does not support them falls back to the equivalent
traditional operations so the user does not need to worry about whether the
server supports the pull operations or if they are required for memory
optimization.

Comparison table
""""""""""""""""

The traditional operations and their equivalent pull operations are covered
by the new iter operations as follows:

======================== ================================================== ==========================
*Traditional Operation*  *Pull Operations*                                  *Iter Operation*
------------------------ -------------------------------------------------- --------------------------
EnumerateInstances       OpenEnumerateInstances / PullInstancesWithPath     IterEnumerateInstances
EnumerateInstanceNames   OpenEnumerateInstancePaths / PullInstancePaths     IterEnumerateInstancePaths
Associators              OpenAssociatorInstances / PullInstancesWithPath    IterAssociatorInstances
AssociatorNames          OpenAssociatorInstancePaths / PullInstancePaths    IterAssociatorInstancePaths
References               OpenReferenceInstances / PullInstancesWithPath     IterReferenceInstances
ReferenceNames           OpenReferenceInstancePaths / PullInstancePaths     IterReferenceInstancePaths
ExecQuery                OpenQueryInstances / PullInstances                 IterQueryInstances
======================== ================================================== ==========================


The methods for the iter operations use the same arguments as the Open...
methods of the pull operations, with exceptions noted in section
:ref: `Differences between iter operations and pull operations`.

The general pattern for use of the iter operations is:

::

    try:
        iterator = Iter...(...)
        for object in iterator:
            <process the object>
    except Error as er:
        # NOTE: objects may be received before an exception, because in each call
        # the server returns either objects or error. However, generally the
        # first error terminates the whole sequence.

These operations use the Python iterator paradigm so that the for-loop
processes CIM objects as they are received via the pull operations or via
the traditional operations if the server does not support pull operations.

Internal processing in the iter operations
""""""""""""""""""""""""""""""""""""""""""

The iter operations try to use the existing pull operations or traditional
operations and lay a layer over them to determine if the pull operations can
be used and to manage the iteration. The paradigm for the implementation of
each of these operations is generally as follows (showing an operation
returning instances as an example, and omitting the logic that closes the
pull operation):

::

    # psuedo code pattern for iter function internal processing
    if <use_pull_for_this_operation is try or true>:
        try:
            result = Open...(...)
            <use_pull_for_this_operation = true>
            for inst in result.instances:
                yield inst
            while not result.eos:
                result = PullInstancesWithPath(...)
                for inst in result.instances:
                    yield inst
            return
        except CIMError as ce:
            if <use_pull_for_this_operation is try> and
                    ce.status_code != "CIM_ERR_NOT_SUPPORTED":
                <use_pull_for_this_operation = false>
            else:
                raise
    <check for unsupported parameters when using traditional operations>
    instances = <traditional-operation>(...)
    for inst in instances:
        <fix up path in instance>
        yield inst

.. _Forcing pull vs. traditional operations:

Forcing pull vs. traditional operations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A parameter (`use_pull_operations`) has been added to the
[`pywbem.WBEMConnection`](https://pywbem.readthedocs.io/en/latest/client.html#
pywbem.WBEMConnection) constructor to optionally force the use of either the
pull operations or the traditional operations.

* If `use_pull_operations` is `True` only the pull operations will be
  executed and if this fails for any reason including `CIM_ERR_NOT_SUPPORTED`,
  the exception will be returned.

* If `use_pull_operations` is `False` only the traditional operations will
  be executed and if this fails for any reason, the exception will be returned.

* The default is `None`. In this case, first the pull operation will be
  attempted. If the first request (Open...) returns `CIM_ERR_NOT_SUPPORTED`,
  the corresponding traditional operation will be attempted.

Thus, the iter operations can be used to execute exclusively the traditional
operations by simply setting `use_pull_operations=False`.

::

    conn = pywbem.WBEMConnection(server, (username, password),
                                 default_namespace=namespace,
                                 no_verification=True,
                                 use_pull_operations=False)


.._Differences between iter operations and pull operations:

Differences between iter operations and pull operations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use of FilterQuery
""""""""""""""""""

Since the traditional operations did not incorporate the query filters into
their input parameters, if a query filter is included in the request and the
request is passed to a traditional operation, the request will be refused
and an exception generated. This is because the specification for the
`FilterQuery` states that the server must return filtered responses and
there is no way to do that with the traditional operations.

Paths in returned instances
"""""""""""""""""""""""""""

The requirements on paths in returned instances differ between pull and
traditional operations. The iter operations have been defined to be in line
with the requirements on paths for pull operations, and the implementation
of the iter operations acts to bring the path in returned instances in line
with the requirements of the pull operations, if it uses the traditional
operation. Thus, the iter operation always returns a complete path in any
returned instances.

Use of MaxObjectCount argument
""""""""""""""""""""""""""""""

The `MaxObjectCount` argument is somewhat more limited than if the pull
operations are used directly in that:

1. It is the same value for open and pull requests.
2. The mechanism to delay responses (setting `MaxObjectCount=0` and
   executing a Pull...() method) cannot be used so the interoperation timeout
   must be sufficient for the client to complete its processing.

Receiving returned objects before an exception
""""""""""""""""""""""""""""""""""""""""""""""

In general the pull operations receive either objects or error for each
request (open or pull). Since these operations may be called to get objects
from the server the iterator may receive objects before an exception is
executed. In general, unless the `ContinueOnError` flag is set, the
enumeration sequence will terminate after the first error and that error is
an indication that not all objects were received from the server.
If the traditional enumerate function is called by the Iter...() method,
either objects or an error are received, never both.

Closing an Iter operation before it is complete
"""""""""""""""""""""""""""""""""""""""""""""""

An iter operation may be closed before the processing from the server is
complete by executing the `close()` function on the iterator:

::

    inst_iterator = conn.IterEnumerateInstances(classname,
                                                MaxObjectCount=max_obj_cnt)
    for inst in inst_iterator:
        if <instance fails some test>
            inst_iterator.close()
        else:
            <process the instance>

Note that if the operation executed was the traditional operation rather
than the pull operation, the `close()` will do nothing since the response
instances are received as a single block. If the enumeration sequence is
already complete, this call will also be ignored.

.. _`WBEM Indications and subscriptions`:

WBEM indications and subscriptions
----------------------------------

TODO: Section on indications and subscriptions

.. _`WBEM Management Profiles`:

WBEM Management Profiles
------------------------

TODO: Create this section describing profiles, why there exist and
very generally how to use them


