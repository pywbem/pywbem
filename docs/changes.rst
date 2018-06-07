
.. _`Change log`:

Change log
==========

.. ifconfig:: '.dev' in version

   This version of the documentation is development version |version| and
   contains the `master` branch up to this commit:

   .. git_changelog::
      :revisions: 1


Version 0.13.0
^^^^^^^^^^^^^^

This version is currently in development and is shown as |version|.

Released: not yet

**Incompatible changes:**

* Changed the `path` argument of `CIMInstance` to be deep copied, because it
  may be modified by setting properties. It was previously shallow copied
  (and incorrectly documented as not being copied). This is only incompatible
  if user code relies on the init method modifying the keybindings of its
  `path` input argument. If user code relies on that, it is highly recommended
  that you decouple such dependencies (Issue #1251).

* Changed the `path` argument of `CIMClass` to be shallow copied, in order
  to decouple the created object from its input arguments. It was previously
  not copied but referenced. This is only incompatible if user code relies on
  the init method modifying the provided `path` input argument. If user code
  relies on that, it is highly recommended that you decouple such
  dependencies (Issue #1251).

**Deprecations:**

* Deprecated the `tocimobj()` function because it has some inconsistencies,
  in favor of the `cimvalue()` function introduced in pywbem 0.12. Changed all
  internal uses of `tocimobj()` to `cimvalue()`. (Issue #904).

**Bug fixes:**

* Fixed the issue where wbemcli-help-txt was not being updated when wbemcli.py
  changed. (Issue #1205)

* Test: Fixed access to incorrect tuple members in run_cim_operations.py.
  that were used only in long version of the test. Found by Pylint.
  (Issue #1206).

* Fixed that `CIMInstanceName.from_wbem_uri()` did not support the
  representation of integer key values in binary, octal or hex format
  (part of Issue #904).

* Fixed an issue with running the tests on Travis CI that occurred on
  Python 2.6 with the latest package level and that was caused by the fact
  that a new version of the "httpretty" Python package was released that
  had dropped support for Python 2.6. This was fixed by limiting the
  version of httpretty to <0.9 when running on Python 2.6. Note that
  this only affects the development environment.

* Correct issue in pywbem_mock where we return incorrect CIMError
  (CIM_ERR_NOT_FOUND rather than CIM_ERR_METHOD_NOT_FOUND) when the
  class for a method is not defined in the methods repository. issue #1256

* Fixed issue in pywbem_mock where we were not creating deepcopy (we were using
  the pywbem .copy that is part of each object (see issue #1251) of objects
  returned from the repository so that if the objects were modified some of the
  changes bled back into the repository. Code modified to do deepcopy of
  everything inserted into the repository through add_cimobjects and the
  Create... methods and returned from the repository with any of the
  get/enumerate/etc. methods.  We also modified code so that if there is a
  class repository there is also an instance repository even if it
  is empty. See issue #1253

* Fixed issue where pywbem_mock EnumerateClass and EnumerateClassNames
  parameter losing the ClassName parameter and no test for the ClassName
  parameter not existing in the repository. (See issue #1271)

* Correct issue in pywbem_mock where we return incorrect CIMError
  (CIM_ERR_NOT_FOUND rather than CIM_ERR_METHOD_NOT_FOUND) when the
  class for a method is not defined in the methods repository. issue #1256

* Fix issue causing pywbem_mock/_wbemconnection_mock.py display_repository()
  to display as bytes in Python 3.  See issue # 1276

**Enhancements:**

* Extend pywbem MOF compiler to search for dependent classes including:
  a) reference classes (classes defined in reference properties or parameters)
  b)EmbeddedInstance qualifier classes if they are not compiled before the
  classes that reference them is compiled. Previously the lack of these
  dependent classes was ignored.  The compiler already searches for superclasses
  if they are not compiled before their subclasses.

  Extends MOFWBEMConnection to generate an exception if the compile of a
  class with reference parameters or properties reference class is not in the
  repository or if the class defined for an EmbeddedInstance qualifier is
  not in the repository.

  This uses the capability in the MOF compiler to search the defined
  search path for the missing classes if they are not in the repository.

  This means that the mof_compiler can be used to create a complete class
  repository builds without having to  specifically declare all dependent
  classes for the classes the user needs in a repository if the mof for the
  dependent classes in in the search path. (Issue #1160).

* Made `CIMInstanceName.from_wbem_uri()` and `CIMClassName.from_wbem_uri()`
  more flexible w.r.t. tolerating non-standard WBEM URIs that omit the leading
  colon before class names (part of Issue #904).

* Added a `tobinary()` method to the `ValueMapping` class, which translates the
  value mapping from a `Values` string to binary integer values, or a range
  thereof. This is the opposite direction of the existing `tovalues()` method.
  (Issue #1153)

* Added an `items()` generator method to the `ValueMapping` class for iterating
  through the items of the value mapping, returning tuples of the binary value
  (or a range thereof), and the `Values` string. (Issue #1153)

* Docs: Clarified that the `copy()` methods of `NocaseDict` and of the CIM object
  classes produce middle-deep copies, whereby mutable leaf attributes are not
  copied and thus are shared between original and copy (Issue #1251).

* Docs: Added a note to the description of the `copy()` methods of the CIM
  objects that states that `copy.copy()` and `copy.deepcopy()` can be used
  to create completely shallow or completely deep copies (Issue #1251).

* Extend wbemcli to use pywbem_mock with a new command line parameter
  (--mock_server <mock_info-filename>). Added a set of new tests for this
  parameter and a mof file and pythong to testsuite to test the new option.
  (Issue #1268)

**Cleanup**

* Moved class `NocaseDict` into its own module (Issue #848).

* Resolved several Pylint issues, including several fixes (Issue #1206).

* Cleanup mof_compiler use of args[0] and args[1] with CIMError. (Issue #1221)

* Removed one level of superflous copies of dictionaries in the `copy()`
  methods of the CIM object classes. These dictionaries are already copied
  in the setter methods for the respective attributes (Issue #1251).

Build, test, quality
^^^^^^^^^^^^^^^^^^^^

* Add tests for WBEMSubscriptionManager class using pywbem_mock.  This involved
  changing the tests for the WBEMServer class using pywbem_mock because the the
  WBEMSubscriptionManager class depends on the existence of the classes and
  instances that support the pywbem WbemServer class existing in the WBEM
  server.  A new file (wbemserver_mock.py) was added to the testsuite directory
  that creates the pywbem_mock for any tests that depend on classes like
  CIM_Namespace, CIM_ObjectManager existing in the mocked server. See issue
  #1250

**Known issues:**

* See `list of open issues`_.

.. _`list of open issues`: https://github.com/pywbem/pywbem/issues


pywbem v0.12.0
--------------

Released: 2018-04-11

Incompatible changes
^^^^^^^^^^^^^^^^^^^^

* Finalized the Iter support that was experimental so far. This affects the
  `Iter...()` methods of class `WBEMConnection`, the `use_pull_operations`
  init parameter and instance attribute of class `WBEMConnection`, and the
  iter-related shortcuts in the `wbemcli` script.

* The following initialization parameters of some CIM object classes that are
  required not to be `None` (as per the documentation) are now enforced not to
  be `None`, and `ValueError` is now raised when providing them as `None`:

  - `CIMInstanceName.classname` (already raised `ValueError`)
  - `CIMInstance.classname`
  - `CIMClassName.classname` (previously raised `TypeError`)
  - `CIMClass.classname`
  - `CIMProperty.name` (already raised `ValueError`)
  - `CIMMethod.name` (previously raised `TypeError`)
  - `CIMParameter.name`
  - `CIMParameter.type`
  - `CIMQualifier.name`
  - `CIMQualifierDeclaration.name`
  - `CIMQualifierDeclaration.type`

  Unless otherwise noted, the previous behavior was to tolerate `None`.

  Note that in all cases, the requirement not to be `None` had previously been
  documented.

* When setting some attributes of CIM object classes that are required not to
  be `None` (as per the documentation), `ValueError` is now raised when
  attempting to set them to `None`:

  - `CIMInstanceName.classname`
  - `CIMInstance.classname`
  - `CIMClassName.classname`
  - `CIMClass.classname`
  - `CIMProperty.name`
  - `CIMMethod.name`
  - `CIMParameter.name`
  - `CIMParameter.type`
  - `CIMQualifier.name`
  - `CIMQualifierDeclaration.name`
  - `CIMQualifierDeclaration.type`

  The previous behavior was to tolerate `None`.

  Note that in all cases, the requirement not to be `None` had previously been
  documented.

* When initializing objects of the CIM object classes `CIMProperty` and
  `CIMQualifier` with a `type` parameter of `None`, and when initializing
  the properties of `CIMInstance`, their CIM type is (and has previously been)
  inferred from the value.

  If inferring the type is not possible (for example because the value is a
  Python integer, float, long (Python 2 only), or `None`), the exception that
  is raised is now `ValueError`. Previously, `TypeError` was raised in that
  case.

* When setting the `type` attribute of the CIM object classes `CIMProperty` and
  `CIMQualifier`, the type is now enforced not to be `None`, and `ValueError`
  is raised when providing it as `None`.

  Previously, setting a type of `None` was tolerated.

  Note that in both cases, the requirement not to be `None` had previously been
  documented.

* For CIM elements passed as dictionaries into CIM object classes (i.e.
  the aparameters/attributes `properties`, `keybindings`, `parameters`,
  `qualifiers`), the consistency between the dictionary key and the name of the
  CIM object that is the dictionary value is now checked and `ValueError` is
  raised if it does not match (case insensitively).

* Initializing a `CIMProperty` object as an embedded object or embedded
  instance and with a value of `None` now requires specifying `type="string"`.

  Previously (but only starting with pywbem v0.8.1), the type was inferred from
  the `embedded_instance` parameter and thus could be omitted. This new
  requirement for specifying `type` is not really intentional, but a by-product
  of simplifying the implementation of `CIMProperty`. It was considered
  acceptable because that should not be a common case (and has not been
  supported before pywbem v0.8.1 anyway).

* When converting a `CIMInstance` object to CIM-XML using its `tocimxml()`
  method, instance properties whose values are simple types instead of
  `CIMProperty` objects are no longer converted into `CIMProperty` objects
  because that has worked only for a very limited set of cases, and
  because they are required to be `CIMProperty` objects anyway. A `TypeError`
  is now raised if that is detected.

* The `atomic_to_cim_xml()` function now raises `TypeError` if it cannot
  convert the input value. Previously, it used `str()` on the input value
  as a last resort.

* The global `tocimxml()` function now raises `TypeError` if it cannot
  convert the input value. Previously, it raised `ValueError`.

* The `CIMQualifierDeclaration.tomof()` method now generates the flavor
  keywords only if the `tosubclass` and `overridable` attributes are set
  to `True` or `False`. Previously, default keywords were generated when
  these attributes were set to `None` (and these defaults were the opposite of
  the defaults defined in DSP0004 and DSP0201). The new behavior is consistent
  with the definition that `None` for these attributes means the information is
  not available, and it is also consistent with the `tocimxml()` method.
  If you used this method and relied on the defaults being generated, you will
  now have to set these attributes explicitly.

* If a WBEM server specifies contradicting `TYPE` and `VALUETYPE` attributes on
  a `KEYVALUE` element returned to the client (this element is used in instance
  paths, e.g. for the result of the `EnumerateInstanceNames` operation), `TYPE`
  now takes precedence. Previously, `VALUETYPE` took precedence. DSP0201 leaves
  the handling of such discrepancies open, and it seems more logical to let the
  more precise value take precedence. Because WBEM servers are required to
  specify consistent values for these attributes, this change should not affect
  users of pywbem.

* Values of CIM type 'reference' in CIM objects (`CIMProperty`,
  `CIMParameter`, `CIMQualifier`, and `CIMQualifierDeclaration`) may now be
  `CIMClassName` objects (i.e. class paths). This has been changed for
  consistency with DSP0201 (Issue #1035).

* Renamed the `enable_stats` init argument of class `WBEMConnection` to
  `stats_enabled`, as part of its finalization. It was experimental, before.
  (Issue #1068).

* Renamed the `-e`, `--enable-stats` options of the `wbemcli` utility to
  `--statistics` , as part of its finalization. It was experimental, before.
  (Issue #1068).

* Changed the `WBEMConnection` attributes for the last request and last
  response to become read-only (`last_request`, `last_raw_request`,
  `last_reply`, `last_raw_reply`). They have never been supposed to be
  writeable by users. (Issue #1068).

* In the wbemcli shell, renamed the following function parameters. This
  is only relevant if you wrote scripts against the shell and named these
  parameters: (Issue #1110).

  - The "op" parameter of iter functions that have it was renamed to "ip",
    because it is always an instance path.

  - The "qi" parameter of the query functions was renamed to "qs",
    for consistency with the filtering functions.

  - The "fq" parameter of the filtering functions was renamed to "fs",
    for consistency with the query functions.

* Revamped the (experimental) logger configuration mechanism completely.
  It remains experimental. See issue #859. The changes include:

  - Created 3 methods in `WBEMConnection` that allow pywbem logs to be
    configured and activated.  These methods contain parameters for:
    a. configuring the Python loggers for either/or/both the api and http
    loggers. b. Setting the level of detail in the log output. c. Activating
    each logger within `WBEMConnection`.
  - Allow for the standard Python loggers to be used to configure logger
    names that will be used by the pywbem loggers. This allows the pywbem
    loggers to be compatible with user code that creates their specific logger
    configurations.
  - Eliminated the `PyWBEMLogger` class that was the original
    logging setup tool in pywbem 0.11.0 since its use was incompatible with
    using standard Python logging configuration methods to define loggers.
  - Created a function in the _logging module that allows pywbem logging
    to be defined by a single string input.
  - Addition of a new property `conn_id` to `WBEMConnection` which is a
    unique identifier for each `WBEMConnection` object and is part of each log
    record. This allows linking logs for each `WBEMConnection` in the log.

Deprecations
^^^^^^^^^^^^

* Deprecated modifications of the connection-related attributes of
  `WBEMConnection` objects (Issue #1068).

* Deprecated the value `None` for the `value` argument of
  `pywbem.tocimxml()`, because it generates an empty `VALUE` element
  (which represents an empty string) (Issue #1136).

Enhancements
^^^^^^^^^^^^

* Finalized the time statistics support that was experimental so far. This
  affects classes `OperationStatistic`, `Statistics`, the init argument
  `enable_stats` of class `WBEMConnection`, and the properties
  `stats_enabled`, `statistics`, `last_operation_time`, and
  `last_server_response_time` of class `WBEMConnection`. As part of that,
  renamed the `enable_stats` init argument to `stats_enabled`, consistent with
  the corresponding property.

* For `CIMInstanceName`, the values of keybindings can now be specified as
  `CIMProperty` objects from which their value will be used (this is in
  addition to specfying the values of keybindings as CIM data types).

* For `CIMInstanceName`, values of keybindings specified as binary strings are
  now converted to Unicode.

* For `CIMInstanceName`, the type of the input keybindings is now checked
  and TypeError is raised if the value is not a CIM data type.

* Updating attributes of CIM objects (e.g. updating `CIMInstance.properties`)
  now goes through the same conversions (e.g. binary string to unicode string)
  as for the same-named constructor parameters. As a result, it is ensured
  that all attributes that are strings (e.g. `name`) contain unicode strings,
  all attributes that are booleans (e.g. `propagated`) contain bool values,
  and all CIM values (e.g. `CIMProperty.value`) are of a :term:`CIM data type`.

* Added static `from_wbem_uri()` methods to `CIMInstanceName` and
  `CIMClassName`, that create a new object of these classes from a
  WBEM URI string.

* Added a `cimvalue()` function that converts input values specified
  at the interface of CIM object classes, into the internally stored
  CIM value. It is mainly used internally by the CIM object classes, but
  has also been made available at the public API of pywbem.
  Its functionality is very close to the existing `tocimobj()` function.

* Changed public attributes to Python properties with getter and setter methods
  in all CIM object classes (e.g. `CIMInstance`). This allows normalizing and
  applying checks for new values of these properties. In addition, it solves
  the Sphinx warnings about duplicate 'host' attribute when building the
  documentation (issue #761).

* Added catching of some exceptions M2Cryptro can raise that were not caught
  so far: SSL.SSLError, SSL.Checker.SSLVerificationError. These exceptions
  are now transformed into `pywbem.ConnectionError` and will therefore be
  caught by a caller of pywbem who is prepared for pywbem's own exceptions,
  but not necessarily aware of these M2Crypto exceptions. (issue #891)

* Added the catching of a httplib base exception to make sure all httplib
  exceptions are surfaced by WBEMConnection methods as a
  pywbem.ConnectionError (issue #916).

* In the `tomof()` methods of the CIM object classes, changed the formatting
  of the generated MOF to be more consistent with the CIM Schema MOF.

* Added new methods `CIMInstanceName.to_wbem_uri()` and
  `CIMClassName.to_wbem_uri()` that return the path as a WBEM URI string that
  conforms to untyped WBEM URIs as defined in DSP0207.
  The `CIMInstanceName.__str__()` and `CIMClassName.__str__()` methods still
  return the same WBEM URI string they previously did, but that is a historical
  format close to but not conformant to DSP0207 (issues #928, #943).

* Improved the way CIM-XML parsing errors are handled, by providing the
  original traceback information when re-raising a low-level exception
  as pywbem.ParseError, and re-established the improved exception message
  for invalid UTF-8 and XML characters that was broken since the move to
  using the SAX parser.

* Added support for properly hashing CIM objects (`CIMClass`, etc.) and
  CIM data types (particularly `CIMDateTime`), as long as these (mutable)
  objects are not changed. Because the objects must not be changed while
  being in a set, a new term "changed-hashable" has been introduced that
  describes this. This allows to have CIM objects in sets such that they
  behave as one would expect from a set. Previously, two CIM objects that
  were equal could both be in the same set, because their hash value was
  different. In the documentation, added a new section "Putting CIM objects
  in sets" that explains the considerations when utilizing the hash value of
  the mutable CIM objects.

* Added support for retrieving the operation recorders of a connection
  via a new `operation_recorders` read-only property (Issue #976).

* Extended `CIMParameter` to represent CIM parameter values in method
  invocations. As part of that, removed the deprecation from its `value`
  property and added an `embedded_object` property. Extended the testcases
  accordingly. Added an `as_value` argument to `CIMParameter.tocimxml()`
  and to `tocimxmlstr()` to allow control over whether the object is
  interpreted as a value or as a declaration. (Issue #950).

* Added a new conversion function to the public API: `cimtype()` takes a CIM
  data typed value (e.g. `Uint8(42)`) and returns the CIM data type name for
  it (e.g. "uint8"). Previously, this was an internal function (Issue #993).

* Added a new conversion function to the public API: `type_from_name()` takes
  a CIM data type name (e.g. "uint8") and returns the Python type representing
  that CIM data type (e.g. `Uint8`). Previously, this was an internal
  function (Issue #993).

* Extended `WBEMConnection.InvokeMethod()` to accept an iterable of
  `CIMParameter` objects as input parameters, in addition to the currently
  supported forms of input parameters. This allows specifying the
  `embedded_object` attribute (instead of inferring it from the value).
  (Issue #950).

* Docs: Improved the descriptions of CIM objects and their attributes to
  describe how the attributes are used to determine object equality and
  the hash value of the object.

* The child elements of CIM objects (e.g. properties of `CIMClass`) now
  preserve the order in which they had been added to their parent object.
  Methods such as `tomof()`, `tocimxml()`, and `to_wbem_uri()` now
  output the child elements of the target object in the preserved order.
  If a child element is initialized with an object that does not preserve
  order of items (e.g. a standard dict), a UserWarning is now issued.

* Added a new kind of input object for initializing CIM objects: An iterable
  of the desired CIM object type, and documented the already supported iterable
  of tuple(key, value) as a further input type.

* Improved checking of input objects when initializing a list of child
  elements in a CIM object(e.g.  properties of `CIMClass`), and raise
  TypeError if not supported.

* Made the `ValueMapping` class more generally available and no longer tied
  to the `WBEMServer` class. It is now described in the "Client" chapter of the
  documentation, and it is possible to create new `ValueMapping` objects by
  providing a `WBEMConnection` object (as an alternative to the `WBEMServer`
  object that is still supported, for compatibility). Issue #997.

* Extended the `ValueMapping` class; its objects now remember the context in
  which the value mapping is defined, in terms of the connection, namespace,
  class, and of the mapped CIM element (i.e. property, method or parameter).

* Extended the `ValueMapping` class by adding a `__repr__()` method that
  prints all of its attributes, for debug purposes.

* Added capability to mock WBEM Operations so that both pywbem and pywbem
  users can create unit tests without requiring a working WBEM Server,
  This feature allows the user to create CIM objects
  in a mock WBEM Server defined with the class `FakedWBEMConnection` and
  substitute that class for `WBEMConnection` to create a mock WBEM Server
  that responds to wbem operations.
  This enhancement is documented in the pywbem documentation section 10,
  Mock Support. See issue #838.

* Improved the messages in `ParseError` exceptions raised when parsing CIM-XML
  received from a WBEM server.

* The type of keybinding names in `CIMInstanceName` objects is now checked
  to be a string (or None, for unnamed keys). The requirement for a string
  has always been documented. This was changed as part of addressing issue
  #1026.

* Fixed the support for unnamed keys (i.e. instance paths with `KEYVALUE`
  or `VALUE.REFERENCE` elements without a parent `KEYBINDINGS` element).
  DSP0201 allows for this as a special case. (Issue #1026).

* Added support for instance qualifiers when parsing received CIM-XML responses
  (Issue #1030).

* CIM data type names specified for the `type` or `return_type` parameter
  of CIM objects are now checked for validity, and `ValueError` is raised
  if not valid (Issue 1043).

* Added a new method `CIMInstanceName.from_instance()` to create
  `CIMInstanceName` objects from class and instance. This was done as part of
  building the pywbem_mock environment. See issue #1069.

* The `url` property of `WBEMConnection` now transforms its input value
  to unicode. (Issue #1068).

* In the `WBEMListener` class, added support for using it as a context
  manager in order to ensure that the listener is stopped automatically
  upon leaving the context manager scope.

* In the `WBEMListener` class, added properties `http_started` and
  `https_started` indicating whether the listener is started for the
  respective port.

* `CIMInstance.tocimxml()/tocimxmlstr()` were extended to allow controlling
  whether the path is ignored even if present. This capability is used for
  ignoring the path in embedded instance parameter values (as part of
  fixing issue #1136).

* `CIMInstanceName/CIMClassName.tocimxml()/tocimxmlstr()` were extended to
  allow controlling whether the host and namespace are ignored even if
  present. This capability is not currently used but was introduced for
  consistency with ignoring the path on
  `CIMInstance.tocimxml()/tocimxmlstr()` (as part of fixing issue #1136).

* Improved the handling of certain connection errors by retrying and by
  issuing user warnings instead of printing if debug. (Issue #1118).

Bug fixes
^^^^^^^^^

* Added `libxml2` operating system package as a dependency. It provides xmllint,
  which is used for testing.

* Fixed issue where `MOFCompiler.compile_str()` could not compile MOF that was
  defined through a MOF file containing `#pragma include` statements.
  This precluded using a string to define the classes to include in
  a mof compile in a string and required that the include be a file.
  See issue #1138.

* Fixed issue in `IterReferenceNames` and `IterAssociatiorNames` where it was
  not passing the `IncludeQualifiers` input parameter to the
  `OpenReferenceNames` operation. This should not have been a significant issue
  since in general qualifiers are not parts of instances. See issue #833.

* Also changed code in `IterQueryInstances` were parameters that are required
  by the called `ExecQuery` and `OpenQueryInstances` were defined as named
  arguments where since they are required, the name component is not required.
  This should not change operations except that when we were mocking the
  methods, it returns sees the parameter as `name=value` rather than value.
  See issue #833.

* Fixed the bug that `CIMInstanceName.tocimxml()` produced invalid CIM-XML
  if a keybinding value was set to an invalid CIM object type (e.g. to
  `CIMParameter`). The only allowed CIM object type for a keybinding value
  is `CIMInstanceName`, for keys that are references. Now, `TypeError` is
  raised in that case.

* Fix issues in `cim_operations.py` where a open or pull that returned with
  missing `enumeration_context` and `eos` would pass one of the internal tests.
  See issue #844

* Fixed an error in the CIM-XML representation of qualifier values where
  the values were not properly converted to CIM-XML. They are now properly
  converted using `atomic_to_cim_xml()`.

* Fixed local authentication for OpenWBEM and OpenPegasus. Due to one bug
  introduced in pywbem 0.9.0, it was disabled by accident. A second bug in
  local authentication has been there at least since pywbem 0.7.0.

* Fixed missing exception handling for CIM-XML parsing errors when parsing
  embedded objects. This could have caused low-level exceptions to be raised
  at the pywbem API.

* Fixed the problem that a `for`-loop over `CIMInstance` / `CIMInstanceName`
  objects iterated over the lower-case-converted property/key names. They now
  iterate over the names in their original lexical case, as documented,
  and consistent with the other iteration mechanisms for CIM objects.
  The test cases that were supposed to verify that did not perform the
  correct check and were also fixed.

* Fixed the bug that an (unsupported!) reference type could be specified for
  the return value of CIM methods, by raising `ValueError` if
  `CIMMethod.return_value` is initialized or set to "reference".

* Fixed issue introduced in mof_compiler when atomic_to_cimxml was cleaned up
  that did not allow using alias with some association classes.  Also
  added test for this issue. See issue #936

* Fixed the `CIMInstanceName.__str__()` and `CIMClassName.__str__()` methods to
  now return WBEM URI strings that are compliant to DSP0207. Changes include:

  * Local WBEM URIs (i.e. when authority/host is not set) now have a leading
    slash. That leading slash was previously omitted.
  * WBEM URIs with no namespace set now have a colon before the class name.
    Previously, the colon was produced only when a namespace was set.

  Issue #928.

* Fixed the comparison of `CIMProperty` objects to also consider the
  `embedded_object` attribute. Previously, this attribute was not considered,
  probably due to mistake (there is no reason not to consider it, as it is a
  user-provided input argument). Fixed the yaml testcases for embedded objects
  that failed as a result of that fix. These testcases did not set the
  `embedded_object` attribute to 'object', so it got its default value
  'instance', which caused the testcases to fail. Needed to use the long
  form for specifying property values inthe yaml now, because the short
  form does not allow for specifying the embedded_object attribute.

* Fixed the comparison of `CIMProperty` and `CIMMethod` objects to compare
  their `class_origin` attribute case-insensitively. If set, it contains a CIM
  class name. Previously, that attribute was compared case-sensitively.

* Fixed the use of hard coded value limits in the `ValueMapping` class
  for open ranges of the `ValueMap` qualifier, by making them dependent on
  the data type of the qualified element. This only affected elements
  with data types other than Uint32 and only if the `ValueMap` qualifier
  defined open ranges whose open side reached the min or max limit (i.e.
  was first or last in the list). Extended the test cases to include
  this situation (Issue #992).

* Fixed the lookup of the `Values` string for negative values in the
  `ValueMapping` class (found when solving #992).

* Added support for octal, binary and hex numbers when parsing MOF
  using the `MOFCompiler` class, in compliance with DSP0004 (Issue #974).
  Extended the testcases to cover such numbers.

* Fixed the issue that any use of `CIMDateTime` objects in the
  `TestClientRecorder` resulted in a `RepresenterError` being raised, by adding
  PyYAML representer and constructor functions that serialize `CIMDateTime`
  objects to YAML. Extended the testcases in `test_recorder.py` accordingly
  (Issues #702, #588).

* Fixed an AttributeError when `ValueMapping` was used for methods, when an
  internal method attempted to access the 'type' attribute of the CIM object.
  For methods, that attribute is called 'return_type'. Testcases for methods
  and parameters have now been added.

* Fixed the issue that leading and trailing slash characters in namespace
  names were preserved. This was leading to empty `NAMESPACE/NAME` elements,
  which can be rejected by WBEM servers. Now, leading and trailing slash
  characters on namespace names are stripped off in pywbem before sending
  the request to the server. (Issue #255).

* Fixed the issue that the parser for CIM-XML received from the WBEM server
  required the `VALUETYPE` attribute of the `KEYVALUE` element. DSP0201 defines
  `VALUETYPE` as optional, with a default of 'string'. That is now implemented.

* Fixed the issue that the parser for CIM-XML received from the WBEM server
  did not support hexadecimal representations of integers in the `KEYVALUE`
  element. They are now supported.

* Fixed the issue that the parser for CIM-XML received from the WBEM server
  accepted characters for char16 typed values outside of the range for
  UCS-2 characters. Such characters are now rejected by raising `ParseError`.

* Fixed the issue that the parser for CIM-XML received from the WBEM server
  tolerated invalid child elements under `INSTANCE`, `ERROR` and
  `PROPERTY.REFERENCE` elements, and invalid attributes on the `PROPERTY.ARRAY`
  element. This now results in a `ParseError` being raised.

* Fixed the issue that the parser for CIM-XML received from the WBEM server
  did not set the `propagated` attribute to `False` in `CIMProperty` objects
  retrieved from operations (e.g. as part of a class or instance), as
  required by DSP0201. It does now.

* Fixed the issue that `VALUE.NULL` (for representing array items that are NULL)
  was not supported in array values returned by the WBEM server. Note that it
  already had been supported for array values sent to the server, or in CIM-XML
  created by `toximcml()` methods (Issue #1022).

* Fixed the issue that the size of a fixed-size array property declaration was
  ignored when retrieving classes from CIM operations. It is now represented
  in the `array_size` attribute of the returned `CIMProperty` objects.
  (Issue #1031).

* Fixed the issue that the `xml:lang` attributes that are allowed on some
  CIM-XML elements have been rejected by raising `ParseError`. They are now
  tolerated but ignored (Issue #1033).

* Fixed the issue that mixed case values (e.g. "True") for the boolean
  attributes of the `QUALIFIER` element in CIM-XML was not supported and
  resulted in `ParseError` to be raised (Issue #1042).

* Fixed the issue that an empty boolean value in a CIM-XML response returned
  from a WBEM server was accepted and treated as a NULL value. This treatment
  does not conform to DSP0201. Empty boolean values now cause a `UserWarning`
  to be issued, but otherwise continue to work as before. (Issue #1032).

* Fixed the issue that invalid values were accepted for the boolean attributes
  of the `SCOPE` element in CIM-XML received from a WBEM server. They now cause
  `ParseError` to be raised (Issue #1040).

* Fixed the issue that invalid values for the boolean attributes of
  `QUALIFIER.DECLARATION` elements in CIM-XML responses from WBEM servers were
  tolerated and treated as `False`. They now cause `ParseError` to be raised
  (Issue #1041).

* Fixed the incorrect default value for the `propagated` constructor parameter
  of `CIMMethod`. Previously, the default value was `False` and it has been
  corrected to be `None`, consistent with its meaning of "information not
  available".
  The only CIM operations that take a `CIMMethod` object as input are
  `CreateClass()` and `ModifyClass()` (as part of the class that is created
  or modified). Because WBEM servers must ignore the `propagated` information
  on any elements in the provided class, this change is backwards compatible
  for the CIM operations. (Issue #1039).

* Added support for setting the `propagated` attribute on `CIMQualifier`
  objects returned from CIM operations to a default of `False` when it is
  not specified in the CIM-XML response, consistent with DSP0201, and
  consistent with how it was already done for other CIM objects.
  This change should normally be backwards compatible for pywbem users,
  because they don't even know whether the information has been set by
  the server or defaulted by the client as it is now done. (Issue #1039).

* Added support for setting the flavor attributes on `CIMQualifier` and
  `CIMQUalifierDeclaration` objects returned from CIM operations to their
  default values defined in CIM-XML, when they are not specified in the
  CIM-XML response, consistent with DSP0201, and consistent with how it
  was already done for other CIM objects.
  This change should normally be backwards compatible for pywbem users,
  because they don't even know whether the information has been set by
  the server or defaulted by the client as it is now done. (Issue #1039).

* In the wbemcli shell, fixed the "\*params" parameter of the `im()` function,
  to become "params" (an iterable). (Issue #1110).

* For the `InvokeMethod` operation, fixed that passing Python `None` as an input
  parameter valus resulted in `TypeError`. Extended the testclient testcases
  for `InvokeMethod` accordingly. Documented that `None` is a valid CIM typed
  value (Issue #1123).

* Fixed the error that embedded instances in parameter values were incorrectly
  represented with the CIM-XML element corresponding to their path (e.g.
  `VALUE.NAMEDINSTANCE`). The path is now correctly ignored on embedded instance
  parameter values, and they are always represented as `INSTANCE` elements
  (Issue #1136).

* Fixed the error that `CIMInstance.tocimxml()/tocimxmlstr()` represented its
  instance path always with a `VALUE.NAMEDINSTANCE` element and generated
  incorrect child elements depending which components of the instance path
  were present. Now, the element for the path depends correctly on the
  components that are present in the instance path (Issue #1136).

* Fixed the missing support for generating a `VALUE.INSTANCEWITHPATH` element
  in CIM-XML. This is needed when a `CIMInstance` with path has namespace and
  host. This error was previously now showing up because the
  `VALUE.NAMEDINSTANCE` element was always created (Issue #1136).

* Fixed the error that the `tocimxml()` and `tocimxmlstr()` methods of
  `CIMProperty`, `CIMQualifier` and `CIMQualifierDeclaration` represented
  NULL entries in array values using an empty `VALUE` element. They now
  correctly generate the `VALUE.NULL` element for NULL entries (Issue #1136).
  In order to provide for backwards compatibility to WBEM servers that
  do not support `VALUE.NULL`, a config option `SEND_VALUE_NULL` was added
  that by default sends `VALUE.NULL`, but allows for disabling that
  (Issue #1144).

* Fixed the error that the special float values `INF`, `-INF` and `NaN`
  were represented in lower case in CIM-XML. DSP0201 requires the
  exact case INF, -INF and NaN (Issue #1136).

* Fixed the error that float values in CIM-XML were truncated to six
  significant digits. They now have at least the minimum number of
  significant digits required by DSP0201: 11 for real32, and 17 for real64.
  (Issue #1136).

* In the `WBEMServer.get_central_instances()` method, fixed the error that a
  CIM status code of `CIM_ERR_METHOD_NOT_FOUND` returned when attempting to
  invoke the `GetCentralInstances()` CIM method lead to failing the
  `get_central_instances()` method. Now, execution continues with attempting
  the next approach for determining the central instances (Issue #1145).

* In the mof_compiler.bat script file, fixed the issue that it did not return
  an exit code if the MOF compiler failed (Issue #1156).

* Several fixes and display related improvements in the mof_compiler script:
  MOF file not found is now also handled instead of failing with an exception
  traceback. Exceptions are now displayed before exiting. Dry-run mode is now
  displayed, for information. The target MOF repository is now always
  displayed; previously it was displayed only in verbose mode. (Issue #1157).

Cleanup
^^^^^^^

* Removed the unimplemented and unused `popitem()` method of `NocaseDict`.

* The `atomic_to_cim_xml()` function and any generated CIM-XML now generates
  boolean values in upper case 'TRUE' and 'FALSE', following the recommendation
  in DSP0201. Previously, boolean values were produced in lower case. This
  change is compatible for WBEM servers that meet the requirement of DSP0201
  to treat boolean values case-insensitively.

* Cleaned up the implementation of `CIMProperty/CIMParameter.tocimxml()`,
  so that it is now easier understandable (as part of fixing issue #1136).

* Removed any logging.NullHandler objects on pywbem loggers, including
  the pywbem listener loggers, because it turns out that for the use
  of loggers as a trace tool, the DEBUG level is used by the pywbem client
  and the INFO level is used by the pywbem listener, which are both not
  printed by default by the Python root logger, so the use of null handlers
  is not really needed (Issue #1175).

Build, test, quality
^^^^^^^^^^^^^^^^^^^^

* Added a boolean config variable `DEBUG_WARNING_ORIGIN` that when enabled
  causes a stack traceback to be added to the message of most warnings issued
  by pywbem. This allows identifying which code originated the warning.

* Cleaned up a lot of pylint warnings, for things like missing-doc, etc. so that
  we can actually review the remainder.  See issue #808.

* Update to current DMTF Schema (2.49.0) for pywbem tests. This also validates
  that pywbem can compile this DMTF released schema. See issue #816

* Add unit tests for the iter... operations. See issue #818

* Migrated installation and development setup to use `pbr` and Pip requirements
  files. As a consequence, removed files no longer used: `os_setup.py`,
  `uninstall_pbr_on_py26.py`.

* Added ability to test with minimum Python package level, according
  to the package versions defined in `minimum-constraints.txt`.

* Fixed a setup issue on Travis CI with duplicate metadata directories for the
  setuptools package. This issue prevented downgrading setuptools for the test
  with minimum package levels. Added script `remove_duplicate_setuptools.py`
  for that.

* Reorganized the make targets for installing pywbem and its dependencies
  somewhat. They now need to be used in this order:

  - make install - installs pywbem and dependencies for runtime
  - make develop - installs dependencies for development

  There are two new targets (that are included in the targets above,
  when first run after a `make clobber`):

  - make install_os - installs OS-level dependencies for runtime
  - make develop_os - installs OS-level dependencies for development

* Enabled testing on OS-X in the Travis CI.

* Added unit test for `WBEMServer` class using pywbem_mock.  See the file
  testsuite/test_wbemserverclass.py.  This test is incomplete today but tests
  most of the main paths.

Documentation
^^^^^^^^^^^^^

Improved the complete pywbem documentation (Issue #1115). Some specific
changes are listed in the remainder of this section.

* The installation for Windows on Python 2.7 now requires an additional
  manual step for installing the M2CryptoWin32/64 Python package. For details,
  see the Installation section in the documentation.

* Fixed the documentation of the `CIMInstanceName.keybindings` setter
  method, by adding 'number' as an allowed input type.

* Moved the detail documentation of input to child element lists (e.g.
  for properties of `CIMInstance`) as a data type 'properties input object',
  etc., into the glossary. These types are now referenced as the type of
  the corresponding parameter.

* Clarified that the return type of `BaseOperationRecorder.open_file()`
  is a file-like object and that the caller is responsible for closing that
  file.

* Clarified in the description of the `return_type` init parameter of
  `CIMMethod` that array return types, void return types, and reference
  return types are all not supported in pywbem. See issue #1038, for void.

* Fixed the type `string` for the keys of the `CIMInstance.qualifiers`
  attribute to be `unicode string`.

* Many clarifications for CIM objects, e.g. about case preservation of
  CIM element names, or making copies of input parameters vs. storing the
  provided object.

* Improved the description of the `WBEMConnection.ModifyInstance()` method.

* Improved the description of the `tocimxml()` and `tocimxmlstr()` methods
  on CIM objects.

* Clarifications and small fixes in the documentation of the
  `WBEMConnection.Iter...()` generator functions.

* Added "New in pywbem M.N ..." text to descriptions of anything that was
  introduced in version 0.8 or later.

* Clarified use of `ca_certs` parameter of `WBEMConnection` and its defaults in
  `DEFAULT_CA_CERT_PATHS`.

* Clarified that the instance path returned by the `CreateInstance()` operation
  method has classname, keybindings and namespace set.

* For CIM floating point types (real32, real64), added cautionary text for
  equality comparison and hash value calculation.

* Clarified that CIM-XML multi-requests are not supported by pywbem and why
  that is not a functional limitation.

* In the wbemcli shell, improved and fixed the description of operation
  functions (Issue #1110).

* Improved and fixed the description of `WBEMConnection` operation methods
  (Issue #1110).

* Improved and fixed the description of the pywbem statistics support
  (Issue #1115).

* Clarified the use of logging for the pywbem client (in section
  4.8 "WBEM operation logging") and for the pywbem listener (in
  section 6.1.2 "Logging in the listener" (Issue #1175).

pywbem v0.11.0
--------------

Released: 2017-09-27

Incompatible changes
^^^^^^^^^^^^^^^^^^^^

None

Enhancements
^^^^^^^^^^^^

* Added support for automatically finding out whether for RHEL/CentOS/Fedora,
  the IUS version of the Python development packages should be used,
  dependent on whether the Python package is from IUS.

* Added the MOF compiler API to the ``pywbem`` namespace. For compatibility, it
  is still available in the ``pywbem.mof_compiler`` namespace. See issue #634.

* Modify the pattern used for cim_operation.py request methods from using
  except/else to use except/finally to reduce number of places code like
  the recorder call and future statistics, log, etc. calls have to be included.
  No other functional changes.
  See issue #680

* Add operation statistics gathering **experimental**.  Adds the class
  Statistics which serves as a common place to gather execution time and
  request/reply size information on server requests and replies. The detailed
  information is available in WBEMConnection for operation execution time
  and request/reply content size at the end of each operation.

  When statistics gathering is enabled, the information is placed into the
  Statistics class where min/max/avg information is available for each
  operation type.
  Statistics gathering is enabled if the WBEMConnection attribute
  `enable_stats` is `True`.

  Statistics can be externalized through the snapshot method of the Statistics
  class.

  The functionality is marked experimental for the current release

  See issue #761

* Extended development.rst to define how to update dmtf mof and move the\
  variables for this process from test_compiler.py to a separate file to
  make them easy to find.  See issue #54

* Changed `CIMInstancename.__repr__()` to show the key bindings in the
  iteration order, and no longer in sorted order, to better debug
  iteration order related issues. See issue #585.

* Add new notebooks to the tutorials including notebooks for the
  WBEMServer class, the pull operations, and the Iter operations. See issue
  #682

* Added unit test for recorder. See issue #676

* Ensured that `CIMDateTime` objects for point in time values are
  timezone-aware when supplied with a timezone-naive `datetime` object.
  This does not change the behavior, but increases code clarity.
  Clarified that in the documentation of  `CIMDateTime`. See issue #698.

* Extend the documentation to list support for specific non-specification
  features of some WBEM servers. Issue #653.

* Extend cim_http.py, cim_operations.py, _statistics.py to handle optional
  WBEMServerResponseTime header from WBEMServer.  This HTTP header reports
  the server time in microseconds from request to response in the operation
  response.  The extension adds the WBEMConnection property
  last_server_response_time and places the time from the server into the
  attribute for this property.

* Extend pywbem to handle optional WBEMServerResponseTime header from a
  WBEM server.  This HTTP header reports the server time in microseconds from
  request to response in the operation response.  The extension adds the
  WBEMConnection property `last_server_response_time` and places the time from
  the server into the attribute for this property.
  It also passes server_response_time to statistics so that max/min/avg are
  maintained.  See issue # 687.

* Add test for wbemcli script that will execute the script and test
  results. issue #569

* **Experimental:** Add logging to record information passing between the pywbem
  client and WBEM servers both for the WBEMConnection methods that drive information
  interchange and the http requests and responses.  Logging includes a new module
  (_logging.py) that provides configuration of logging.
  The logging extends WBEMConnection with methods so that the user
  can chose to log a)Calls and returns from the WBEMConnection methods that
  interact with the WBEMServer (ex. getClass), b)http request/responses, c)both.
  The logging uses the python logging package and the output can be directed
  to either stderr or a file. The user can chose to log the complete
  requests and responses or size limited subsets (log_detail level). See issue #691.

* Clarify documentation on wbem operation recorder in client.rst. see
  issue #741

* Added an optional class path to the `CIMClass` class, as a convenience for
  the user in order so that `CIMClass` objects are self-contained w.r.t. their
  path. The class path is set in `CIMClass` objects returned by the `GetClass`,
  `EmumerateClasses`, and the class-level `Associators` and `References`
  operations. The path is added purely on the client side, based on existing
  information returned from WBEM server. This change does therefore not affect
  the interactions with WBEM servers at all.  issue #349.

* Added a ``host`` property to ``WBEMConnection`` which contains the host:port
  component of the WBEM server's URL.  This helps addressing issue #349.

* Made sure that ``repr()`` on CIM objects produces a reliable order of
  items such as properties, qualifiers, methods, parameters, scopes, by
  ordering them by their names. This makes debugging using ``repr()`` easier
  for pywbem users, and it also helps in some unit test cases of pywbem itself.

* Made sure that ``str()`` on ``CIMInstanceName`` produces reliable order of
  key bindings in the returned WBEM URI, by ordering them by key name.

Bug fixes
^^^^^^^^^

* Fix issue with MaxObjectCount on PullInstances and PullInstancePaths
  CIM_Operations.py methods.  The MaxObjectCount was defined as a keyword
  parameter where it should have been be positional.  This should NOT impact
  clients unless they did not supply the parameter at all so that the result
  was None which is illegal(Pull... operations MUST include MaxObjectCount).
  In that case, server should return error.
  Also extends these requests to test the Pull.. methods for valid
  MaxObjectCount and context parameters. See issue #656.

* Add constructor parameter checking to QualifierDeclaration. See issue #645.

* Fixed TypeError "'str' does not support the buffer interface" during
  'setup.py develop' on Python 3.x on Windows (issue #661).

* Fixed ValueError "underlying buffer has been detached" during
  'setup.py develop' on Python 3.x on Windows (issue #661).

* Fixed names of Python development packages for SLES/OpenSUSE.

* Fixed issue in mof_compiler where instance aliases were incomplete. They
  only included the class component so that if they were used in the definition
  of other instances (ex. to define an association where a reference property
  was the aliased instance, the reference path was incomplete.) This is now
  a path with keybindings.  Note: It is the responsibility of the user to
  make these instances complete (i.e. with all key properties) see issue #679

* Correct documentation issue in cim_obj (Exceptions definition missing).
  See issue #677

* Add more mock tests.  ModifyInstance was missing and some others were
  missing an error test. issue#61

* add --version option to mof_compiler and pywbem cli tools.  Generates the
  pywbem version string.  See issue # 630

* Fix several issues in recorder including issue #609:indent by 4,
  # 676: invalid yaml representation for namedtuples that result from
  open/pull operations, #700 and #663: recorder won't write utf8 (at least for our
  tests), #698 : datetime test failures because of timezone, Most
  of these are tested with the new test_recorder.py unit test.

* Fix error in wbemcli with --enable_stats arg.  Since this was added in
  this release, the bug was never public. See issue #709

* Remove extra print in cim_operations. See issue # 704

* Correct Error in run_cimoperations with use of namespace in iter... function
  See issue #718. This was a test code issue. No changes to the iter
  operations.

* Correct issue with Recorder creating non-text files.  This issue
  Documents the requirement for text files and also adds a static
  method to force creation of the recorder output as a text file.
  See issue # 700

* Correct issue in wbemcli.bat where it was not returning error level.
  see issue #727

* Correct issue where dependency pip installs end up with old version
  of coverage package. This old version generates unwanted deprecation
  messages that are fixed after version 4.03. This requires a change to
  the travis.yaml file directly to force a reinstall of coverage.
  See issue #734

* Fixed the issue that ``CIMProperty.__init__()`` had an incorrect check for
  the ``reference_class`` parameter, where it checked the class name specified
  in that parameter to be the creation class of the referenced instance.
  According to DSP0201, reference_class is the declared class, which can be
  a superclass of the  creation class of the referenced instance.
  This is related to issue #598

* Modify mof_compiler documentation to indication issues with property
  names that are compiler keywords. See issue #62.

* Correct issue where dependency pip installs end up with old version
  of coverage package. This old version generates unwanted deprecation
  messages that are fixed after version 4.03. This requires a change to
  the travis.yaml file directly to force a reinstall of coverage.
  See issue #734

* Fix minor doc issue in client.rst. See issue #740.

* Fixed that older versions of pip and setuptools failed or were
  rejected on some older Linux distros during make develop or make install,
  by upgrading them in these steps. See issues #759 and #760.

* Clean up pylint new messages tied to use of len and if else. See issue #770

Build, test, quality
^^^^^^^^^^^^^^^^^^^^

* Added Python 3.6 to the environments to be tested in Travis CI and Appveyor
  CI (issue #661).

* Added Python 2.6, 3.4 and 3.5 to the environments to be tested in Appveyor
  CI (issue #661).

* Fixed uninstall_pbr_on_py26.py to remove 'pbr' only if installed
  (issue #661).

* Fixed TypeError about dict ordering on Python 3.6 in unit test
  'test_nocasedict.TestOrdering' (issue #661).

* Added a testcase for `CIMInstanceName` to compare two objects with
  different ordering of their key bindings for equality. See issue #686.

* In ``parse_property_reference()`` in ``tupleparse.py``, a number of
  attributes of the new ``CIMProperty`` object had been updated after having
  created it. That bypasses the checks in its ``__init__()`` method.
  This has been improved to pass these values in when creating the object.

* Tolerated incorrect Unicode characters in output of commands invoked by
  ``os_setup.py`` (used for installation) that sometimes occurred on Windows
  (e.g. on the Appveyor CI with Python 3).

* Improved the build process to ensure that half-built artefacts are
  removed before building (issue #754).

* Pinned the version of the ``wheel`` package to <0.30.0 for Python 2.6,
  because wheel removed Python 2.6 support in its 0.30.0 version.

Documentation
^^^^^^^^^^^^^

* Documented that pywbem is not supported on Python 2.6 on Windows.
  and that 64-bit versions of Python are not supported on Windows.

* Added material to README and changed to use restructured text. issue #642


pywbem v0.10.0
--------------

Released: 2016-12-20

Incompatible changes
^^^^^^^^^^^^^^^^^^^^

* All methods of the `WBEMSubscriptionManager` class that returned instance
  paths (or lists thereof) in pywbem v0.9 now return the complete instances
  (or lists thereof) (pr #607).

* In `wbemcli`, removed the long global function names (e.g.
  `EnumerateInstances`), and kept the short names (e.g. `ei`) (issue #548).

Enhancements
^^^^^^^^^^^^

* **Experimental:** Added new methods to `WBEMConnection` to provide integrated
  APIs for the non-pull and pull operations, reducing the amount of code app
  writers must produce and providing a pythonic (generator based) interface
  for the methods that enumerate instances and instance paths, enumerator
  associators and references.
  These new methods have names in the pattern
  `Iter<name of original function>`. Thus, for example the new method
  `IterEnumerateInstances` creates a new API to integrate `EnumerateInstances`
  and the `OpenEnumerateInstancesWithPath` / `PullInstancesWithPath`.
  (issue #466).

* Modified the XML parser to use SAX in place of minidom for operation response
  processing and indication processing. This is a significant reduction in
  memory usage (issue #498).

* Declared the WBEM indications API and the WBEM server API to be final. These
  APIs had been introduced in v0.9.0 as experimental.

* Added enter and exit methods to `WBEMSubscriptionManager` to enable using it
  as a context manager, whose exit method automatically cleans up by calling
  `remove_all_servers()` (issue #407).

* Added methods to the operation recorder (class `BaseOperationRecorder`) for
  disabling and enabling it (issue #493).

* The "Name" property of indication filters created via the
  `WBEMSubscriptionManager` class can now be controlled by the user (pr #607).

* Indication filter, listener destination and indication subscription
  instances created via the `WBEMSubscriptionManager` class, that are "owned",
  are now conditionally created, dependent on the owned instances that have
  been discovered upon restart of the `WBEMSubscriptionManager` (pr #607).

* Modified operations that have a "PropertyList" attribute to allow the
  "PropertyList" attribute to have a single string in addition to the iterable.
  Previously this caused an XML error (issue #577).

* Added an option `-s` / `--script` to `wbemcli` that supports executing
  scripts in the wbemcli shell.

  Some example scripts are provided in the examples directory:

  - `wbemcli_server.py` - Creates a `WBEMServer` object named `SERVER`
    representing a WBEM server.

  - `wbemcli_quit.py` - Demo of terminating wbemcli from within a script.

  - `wbemcli_display_args.py` - Demo of displaying input arguments.

  - `wbemcli_count_instances.py` - Counts classes and instances in a server.

  - `wbemcli_clean_subscriptions.py` - Removes all subscriptions, filters, and
    listener destination instances in a server.

  - `test_wbemcli_script.sh` - A shell script that demos scripts.

* Improved robustness and diagnostics in `os_setup.py` (issue #556).

Bug fixes
^^^^^^^^^

* Fixed the use of a variable before it was set in the `remove_destinations()`
  method of class `WBEMSubscriptionManager`.

* Fixed a compatibility issue relative to pywbem 0.7.0, where the
  `pywbem.Error` class was no longer available in the `pywbem.cim_http`
  namespace. It has been made available in that namespace again, for
  compatibility reasons. Note that using sub-namespaces of the `pywbem`
  namespace such as `pywbem.cim_http` has been deprecated in pywbem 0.8.0
  (issue #511).

* Fixed an `AttributeError` in the `remove_all_servers()` method of
  `WBEMSubscriptionManager` and dictionary iteration errors in its
  `remove_server()` method (pr #583).

* Fixed a `TypeError` in the `TestClientRecorder` operation recorder that
  occurred while handling a `ConnectionError` (this recorder is used by the
  `--yamlfile` option of `run_cim_operations.py`) (issue #587).

* Fixed several errors in recorder on Python 3 (issue #531).

* In wbemcli, several fixes in the short global functions (issue #548).

* Fixed name of python devel package for Python 3.4 and 3.5.

* Several changes, fixes and improvements on WBEMSubscriptionManager
  (issues #462, #540, #618, #619).

* Added a check for unset URL target in recorder (issue #612).

* Fixed access to None in recorder (issue #621)

Build, test, quality
^^^^^^^^^^^^^^^^^^^^

* Added flake8 as an additional lint tool. It is executed with `make check`.
  Fixed all flake8 issues (issues #512, #520, #523, #533, #542, #560, #567,
  #575).

* Changed names of the pylint and flake8 config files to match the default
  names defined for these utilities (pylintrc and .flak8) (issue #534).

* Added CIM Schema archive to the repository, in order to avoid repeated
  downloads during testing in the CI systems (issue #49).

* Added `git` as an OS-level dependency for development (it is used by GitPython
  when building the documentation) (pr #581).

* Added `wheel` as a Python dependency for development. This package is not
  installed by default in some Linux distributions such as CentOS 7, and
  when installing into the system Python this becomes an issue (pr #622).

* Added retry in setup script to handle xmlrpc failures when installing
  prerequisites from PyPI.

* Fixed logic errors in pycmp compatibility checking tool.

* Changed makefile to skip documentation build on Python 2.6 due to
  Sphinx having removed Python 2.6 support (issue #604).

* Fixed UnboundLocalError for exc in setup.py (issue #545).

* Added an executable `run_enum_performance.py` to the testsuite to test pull
  performance. It generates a table of the relative performance of
  `EnumerateInstances` vs. `OpenEnumerateInstances` / `PullInstancesWithPath`
  performance over a range of MaxObjectCount, response instance sizes, and
  total number of instances in the response.

* Completed the `test_client.py` mock tests for all instance operations.

* Improved the tests in `run_cim_operations.py`.

Documentation
^^^^^^^^^^^^^

* Added the global functions available in the wbemcli shell to the
  documentation (issue #602).

* Improved usage information for the "Tutorial" section, to make usage of
  Jupyter tutorials more obvious (issue #470).

* Added "Installation" and "Development" sections to the documentation, and
  moved some content from the "Introduction" section into a new "Appendix"
  section. Added an installation trouble shooting section to the appendix
  (pr #509).

* Added a section "Prerequisite operating system packages" to the documentation
  that describes the prerequisite packages by distribution (pr #549).

* Fixed a documentation build error on Python 2.6, by pinning the GitPython
  version to <=2.0.8, due to its use of unittest.case which is not available
  on Python 2.6 (issue #550).

* Clarified the behavior for the default `WBEMConnection` timeout (`None`)
  (issue #628).

* Fixed a documentation issue where the description of `CIMError` was not
  clear that the exception object itself can be accessed by index and slice
  (issue #511).

* Added the `wbemcli` global functions to the documentation (issue #608).


pywbem v0.9.0
-------------

Released: 2016-09-06

Deprecations
^^^^^^^^^^^^

* Deprecated the use of the `value` instance variable and ctor parameter
  of the `CIMParameter` class, because that class represents CIM parameter
  declarations, which do not have a default value. Accessing this instance
  variable and specifying an initial value other than `None` now causes a
  `DeprecationWarning` to be issued.

* Deprecated ordering comparisons for `NocaseDict`, `CIMInstance`,
  `CIMInstanceName`, and `CIMClass` objects. This affects the ordering
  comparisons between two such objects, not the ordering of the items within
  such a dictionary. Use of ordering operators on objects of these classes
  now causes a `DeprecationWarning` to be issued.

* Deprecated the `methodname` input argument of `CIMMethod()`, and renamed it
  to `name`. `methodname` still works but its use causes a `DeprecationWarning`
  to be issued.

* Deprecated the use of the `verify_callback` parameter of `WBEMConnection`.
  because it is not used with the Python ssl module and will probably be
  removed completely in the future.  Its use now causes a `DeprecationWarning`
  to be issued. (Issue #297)

Known Issues
^^^^^^^^^^^^

* Installing PyWBEM on Python 2.6 has a conflict with the `pbr` package
  from PyPI, resulting in a TypeError: "dist must be a Distribution
  instance". This issue is specific to Python 2.6 and does not occur in
  any of the other supported Python versions (2.7, 3.4, 3.5). This issue
  can be mitigated by uninstalling the `pbr` package, or if that is not
  possible, by migrating to Python 2.7. See issue #26 on GitHub.

* MOF using names that are reserved keywords will fail to compile in the
  MOF compiler. For example, a CIM property named 'indication'.
  See issue #62 on GitHub.

Clean Code
^^^^^^^^^^

* Moved the following unused modules from the pywbem package directory
  into a new `attic` directory, in order to clean up the pywbem
  package:

  - `cim_provider.py`
  - `cim_provider2.py`
  - `cimxml_parse.py`
  - `test_cimxml_parse.py`
  - `twisted_client.py`

* Moved the script-related portions of the `pywbem/mof_compiler.py` module
  into the `mof_compiler` script.

* Moved the complete `pywbem/wbemcli.py` module into the `wbemcli` script.

* Removed half-baked code for HTTP proxy/tunneling support.

Enhancements
^^^^^^^^^^^^

* Implemented pull operations per DMTF specification DSP0200 and DSP0201.
  This includes the following new client operations to execute enumeration
  sequences:

  - OpenEnumerateInstances
  - OpenEnumerateInstancePaths
  - OpenAssociatorInstances
  - OpenAssociatorInstancePaths
  - OpenReferenceInstances
  - OpenReferenceInstancePaths
  - OpenQueryInstances
  - PullInstances
  - PullInstancesWithPath
  - PullInstancePaths
  - CloseEnumeration

  The EnumerationCount operation is NOT implemented, because it is both
  deprecated and unusable. (Issue #9)

  Unit tests of the pull operations are included and mock tests are written
  for at least some parts of the pull operations.

* Implemented support for reading information from WBEM servers according to
  the DMTF WBEM Server Profile (DSP1071) and DMTF Profile Registration Profile
  (DSP1033) with a new `WBEMServer` class. Note that not everyhting in these
  profiles needs to be implemented in the WBEM server for this to work:

  - The `WBEMServer` class is a client's view on a WBEM server and provides
    consistent and convenient access to the common elements of the server,
    including namespace names, interop namespace name, registered profile
    information, server branding, and central/scoping class algorithms.

  - Added unit tests for this new class in `run_cim_operations.py` and
    `test_client.py`.

  - Added a demo of the discovery abilities of the `WBEMServer` class in the
    `examples/explore.py` script.

  **Experimental** - This new class is experimental for pywbem version 0.9.0
  because this is the initial release of a significant change and subject to
  changes to the API.

  (Issues #9, #346, #468)

* Implemented support for WBEM subscription management and a WBEM indication
  listener:

  - Added a `WBEMListener` class that allows the creation of a listener entity
    to receive indications.

  - Added a `WBEMSubscriptionManager` class that allows management of
    indication subscriptions, indication filters, and listener destination
    instances on the WBEM Server using the new WBEMServer class.

  - Added unit tests for these new classes and extended other existing tests
    accordingly, e.g. `run_cim_operations.py`.

  **Experimental** - These new classes are experimental for pywbem version
  0.9.0 because this is the initial release of a significant change and subject
  to changes to the API.

  (Issues #66, #421, #414, #379, #378)

* The distribution formats released to PyPI have been extended. There are now:

  - Source archive (existed)
  - Universal wheel (new)

  (Issue #242)

* Starting with v0.9.0, pywbem no longer stores the distribution archives
  in the repository, because the process for releasing to PyPI creates new
  distribution archives instead of using the created ones. This makes it
  difficult to ensure that the archives stored in the repository are the
  same.

* Upgraded M2Crypto to use official 0.24.0 from PyPI.

* Added check for minimum Python version 3.4 when running on Python 3.
  That requirement was already documented, now it is also enforced in the code.

* Migrated API documentation to Sphinx.

* Improved documentation of many classes of the external API.

* Replaced `[]` and `{}` default arguments with None.

* Changed the return value of `repr()` for `WBEMConnection`, CIM type
  classes (e.g. `Sint8`, `CIMDateTime`), and CIM object classes
  (e.g. `CIMInstance`) so that they now return all attributes in a
  reasonable order, and are suitable for debugging.

* Clarified in the description of `CIMClassName.__str__()` and
  `CIMInstanceName.__str__()` that they return the WBEM URI representation
  of the class path and instance path.

* Changed the return value of `str()` for CIM object classes
  (e.g. `CIMProperty`) so that they now return a short set of the most
  important attributes for human consumption.
  Specifically, this resulted in the following changes:

  - For `CIMProperty`, reduced the complete set of attributes to a short set.
  - For `CIMQualifierDeclaration`, added the attribute `value`.

* Changes in the `CIMError` exception class:

  - Changed the behavior of the `__str__()` method to return a human readable
    string containing the symbolic name of the status code, and the status
    description. The previous behavior was to return a Python representation
    of the tuple status code, status description.
  - Added properties `status_code` (numeric CIM status code),
    `status_code_name` (symbolic name of CIM status code), and
    `status_description` (CIM status description).
  - Updated the documentation to no longer show the unused third tuple element
    `exception_obj`. It was never created, so this is only a doc change.

* Added CIM status codes 20 to 28, specifically to support the pull operations.

* Changed the `ParseError` exception to be derived from the `Error` base
  exception, so that now all pywbem specific exceptions are derived from
  `Error`.

* Added `tocimxmlstr()` as a global function and as methods on all CIM
  object classes. It returns the CIM-XML representation of the object
  as a unicode string either in a single-line variant, or in a prettified
  multi-line variant.

* Created `tomof()` for `CIMProperty` making common functionality available
  to both class and instance `tomof()` (PR #151)

* Added an optional `namespace` parameter to the
  `WBEMConnection.CreateInstance()` method, for consistency with other methods,
  and to have an explicit alternative to the namespace in the path component of
  the `NewInstance` parameter.

* The `ClassName` parameter of several operation methods can be specified
  as both a string and a `CIMClassName` object. In the latter case, a namespace
  in that object was ignored so far. Now, it is honored. This affects the
  following `WBEMConnection` methods: `EnumerateInstanceNames`,
  `EnumerateInstances`, `EnumerateClassNames`, `EnumerateClasses`, `GetClass`,
  `DeleteClass`.

* Enhanced the CIM integer data types (e.g. `pywbem.Uint8()`) to accept all
  input parameters that are supported by `int()`.

* Added the concept of a valid value range for the CIM integer data types, that
  is enforced at construction time. For compatibility, this strict checking can
  be turned off via a config variable:
  `pywbem.config.ENFORCE_INTEGER_RANGE = False`.

* Extended `wbemcli` arguments to include all possible arguments that would
  be logical for a ssl or non-ssl client. This included arguments for
  ca certificates, client keys and certificates, timeout. It also modifies
  the server argument to use http:// or https:// prefix and suffix with
  :<port number> and drops the old arguments of `--port` and `--no-ssl`

* Improved Swig installation code by reinstalling Swig if it was installed
  but still cannot be found in PATH (e.g. if the installation was tampered
  with).

* Removed dependency on git (this was a leftover from when M2Crypto needed
  to be obtained from its development repo).

* Added debug prints for two probably legitimate situations where socket
  errors are ignored when the server closes or resets the connection.
  These debug prints can be enabled via the `debug` instance variable
  of the `WBEMConnection` object; they are targeted at development for
  investigating these situations.

* Extended run_cim_operations.py which is a live test against a server.
  It has only been tested against OpenPegasus but was extended to cover
  more details on more of the operation types and to create a test
  subclass to specifically test against OpenPegasus if OpenPegasus is
  detected as the server.

* Added description of supported authentication types in WBEM client API.

* Allowed tuple as input for `PropertyList` parameter of `WBEMConnection`
  operation methods. Documentation indicated that iterable was allowed but was
  limited to list. (Issue #347)

* Added a tutorial section to the generated documentation, using
  Jupyter Notebooks for each tutorial page. (Issue #324)

* Added the concept of operation recording on WBEM connections, that supports
  user-written operation recorders e.g. for tracing purposes. Added an
  operation recorder that generates test cases for the `test_client`
  unit test module. (Issue #351)

* Extended `wbemcli` for all pull operations. (Issue #341)

* Changed command line options of `mof_compiler` command to be consistent
  with `wbemcli`, and added support for specifying certificate related
  options. use of the old options is checked and causes an according error
  message to be displayed. Note, this is an incompatible change in the
  command line options. (Issue #216)

* Cleaned up exception handling in `WBEMConnection` methods: Authentication
  errors are now always raised as `pywbem.AuthError` (OpenWBEM raised
  `pywbem.ConnectionError` in one case), and any other bad HTTP responses
  are now raised as a new exception `pywbem.HTTPError`.

* Clarified `MofParseError` by defining attributes as part of the class init
  and moving some code from productions to the class itself (Issue #169). This
  makes the `MofParseError` exception more suitable for use from the productions
  themselves. The original definition was really only for use as a call from
  ply. Add tests for invalid qualifier flavors to unit tests and add test in
  mof_compiler.py for conflicting flavors ex. tosubclass and restricted in
  the same definition. This test uses the new `MofParseError`. (Issue #204)

* Extended PropertyList argument in request operations to be either list
  or tuple. (Issue #347)

* Added support for representing control characters in MOF strings using MOF
  escape sequences, e.g. U+0001 becomes `"\x0001"`.

* Modified qualifier MOF output to stay within 80 column limits.
  (Issue #35)

Bug fixes
^^^^^^^^^

* Fixed `KeyError` when iterating over `CIMInstance` and `CIMInstanceName`
  objects.

* Fixed bug that MOF escape sequences in strings were passed through
  unchanged, into generated MOF, by removing needless special-casing code.

* Fixed bug with class MOF generation where output was not including array
  indicator ([]). (Issue #233)

* Moved class property MOF output processing to `CIMProperty` and fixed issue
  where default values were not being generated. (Issues #223 and #231)

* Fixed bug in method MOF output where array flag "[]" was left off array
  parameters.

* In the `WBEMConnection.ModifyInstance()` method, the class names in the
  instance and path component of the `ModifiedInstance` parameter are required,
  but that was neither described nor checked. It is now described and checked.

* In the `WBEMConnection.ModifyInstance()` method, a host that was specified in
  the path component of the `ModifiedInstance` parameter incorrectly caused
  an INSTANCEPATH element to be created in the CIM-XML. This bug was fixed,
  and a host is now ignored.

* Fixed a bug where the CIM datetime string returned by the `str()` function
  on `CIMDateTime` interval objects contained incorrect values for the minutes
  and seconds fields on Python 3. (Issue #275).

* Fixed an IndexError in cim_http.wbem_request() that occurred during handling
  of another exception.

* Fixed issue with Python 3 and https that was causing connect() to fail.
  This completely separates connect() code for Python 3 ssl module from
  Python 2 M2Crypto.

* Fixed problem that wbemcli in Python 3 when used without existing history
  file would fail with "TypeError: 'FileNotFoundError' object is not
  subscriptable". (Issue #302)

* Fixed issue with tomof() output where datetime values were not quoted.
  (Issue #289)

* Eliminated automatic setting of toinstance flavor in mof_compiler when
  tosubclass is set.  Also enabled use of toinstance flavor if defined
  in a class or qualifier declaration. (Issue #193)

* Fixed problem in class-level associator operations that namespace was
  classname when classname was passed as a string. (Issue #322)

* Fixed hole in checking where class CIMMethod allowed None as a return_type.
  (Issue #264)

* Fixed a documentation issue with associators/references return types. It was
  documented as a list of classes for class level return, but it actually is a
  list of tuples of classname, class. (Issue #339)

* Created a common function for setting SSL defaults and tried to create
  the same level of defaults for both Python2 (M2Crypto) and Python 3 (SSL
  module).  The minimum level protocol set by the client is TLSV1 now whereas
  in previous versions of pywbem it was SSLV23. (Issue #295)

* Fixed issue where mof_compiler was setting values for compile of instances
  into the class object and also setting the values for the last compiled
  instance in a compile unit into all other compiled instances for the same
  class. Since the concept of compiling a path into compiled instances is
  flawed (there is no requirement to include all properties into a instance to
  compile that code was removed so that the path is NOT build into a compiled
  instance. Finally the qualifiers from the class were also included in
  compiled instances which was incorrect and an accident of the code. They are
  no longer included into the compiled instances.) (Issue #402)

* Fixed description in INSTALL.md to correctly describe how to establish
  OS-level prerequisites.

* Cleaned up the timeouts on SSL and created specific tests for timeouts
  against a live server. (Issues #363, #364)


pywbem v0.8.4
-------------

Released: 2016-05-13

Bug fixes
^^^^^^^^^

* Fixed an IndexError in cim_http.wbem_request() that occurred during
  handling of another exception.

* Fixed problem that wbemcli in Python 3 when used without existing history
  file would fail with "TypeError: 'FileNotFoundError' object is not
  subscriptable" (issue #302).

* Fixed issues with Python 3 and HTTPS that were causing the connecttion
  to fail. This completely separates the `connect()` code for Python 3
  (using the Python SSL module) from the code for Python 2 (using
  M2Crypto) (issues #150, #273, #274, #288).

Enhancements
^^^^^^^^^^^^

* Improved description in INSTALL.md to better describe how to establish
  OS-level prerequisites.

* Improved Swig installation code by reinstalling Swig if it was installed
  but still cannot be found in PATH (e.g. if the installation was tampered
  with).

* Removed dependency on git (this was a leftover from when M2Crypto needed
  to be obtained from its development repo).

* Added debug prints for two probably legitimate situations where socket
  errors are ignored when the server closes or resets the connection.
  These debug prints can be enabled via the `debug` instance variable
  of the WBEMConnection object; they are targeted at development for
  investigating these situations.

* Added check for minimum Python version 3.4 when running on Python 3.
  That requirement was already documented, now it is also enforced in
  the code.

* Enhanced the wbemcli script with options supporting certificates.
  For details, invoke with --help, or look at the online documentation.
  NOTE: The --no-ssl and --port options have been removed. Specify
  the protocol and port number in the server URL.

Clean code
^^^^^^^^^^

* Removed half-baked code for HTTP proxy/tunneling support.


pywbem v0.8.3
-------------

Released: 2016-04-15

Bug fixes
^^^^^^^^^

* To address some M2Crypto issues, upgraded to use M2Crypto >=0.24 from
  PyPI.

* For Windows, using M2CryptoWin32/64 >=0.21 from PyPI, in order to
  avoid the Swig-based build in Windows.

* Improved the mechanism to build the LEX/YACC table modules, so that
  import errors for freshly installed packages (e.g. M2Crypto) no longer
  occur.

Enhancements
^^^^^^^^^^^^

* Added Windows versions of WBEM utility commands: wbemcli.bat,
  mof_compiler.bat.


pywbem v0.8.2
-------------

Released: 2016-03-20

Bug Fixes
^^^^^^^^^

* Eliminated dependency on `six` package during installation of pywbem.
  (Andreas Maier)

Dependencies
^^^^^^^^^^^^

* v0.8.x has the following dependencies on other PyPI packages
  (see `install_requires` argument in setup script):

  - `M2Crypto`
  - `ply`
  - `six`


pywbem v0.8.1
-------------

Released: 2016-03-18

Known Issues
^^^^^^^^^^^^

* Installing PyWBEM on Python 2.6 has a conflict with the `pbr` package
  from PyPI, resulting in a TypeError: "dist must be a Distribution
  instance". This issue is specific to Python 2.6 and does not occur in
  any of the other supported Python versions (2.7, 3.4, 3.5). This issue
  can be mitigated by uninstalling the `pbr` package, or if that is not
  possible, by migrating to Python 2.7. See issue #26 on GitHub.

* MOF using names that are reserved keywords will fail to compile in the
  MOF compiler. For example, a CIM property named 'indication'.
  See issue #62 on GitHub.

* The Pulled Enumeration Operations introduced in DSP0200 1.3 are not
  supported in this release. See issue #9 on GitHub.

* Note that some components of this PyWBEM Client package are still
  considered experimental:

  - The twisted client module `twisted_client.py`.
  - The Python provider modules `cim_provider.py` and `cim_provider2.py`.
  - The CIM indication listener in the `irecv` directory.
    See issue #66 on GitHub.

Changes
^^^^^^^

* The MOF compiler is now available as the command 'mof_compiler' that gets
  installed into the Python script directory. It is now separate from the
  'mof_compiler' module within the 'pywbem' package. In 0.7.0, the module
  was at the same time the script.  (Andreas Maier)

* The WBEM client CLI is now available as the command 'wbemcli' that gets
  installed into the Python script directory. It is now separate from the
  'wbemcli' module within the 'pywbem' package. In 0.7.0, the module
  was at the same time the script.  (Andreas Maier)

* In 0.7.0, most symbols defined in the sub-modules of the 'pywbem' package
  were folded into the 'pywbem' package namespace, cluttering it
  significantly. The symbols in the 'pywbem' package namespace have been
  reduced to a well-defined set that is now declared the external API of
  the WBEM client library, and is supposed to be sufficient. If you find
  that you need something you were used to, please think twice as to
  whether that makes sense to be part of the external PyWBEM API, and if
  so, let us know by opening an issue.

* Since 0.7.0, some exceptions that can be raised at the external API of
  the WBEM client library have been cleaned up.

Enhancements
^^^^^^^^^^^^

* Verify certificates against platform provided CA trust store in
  /etc/pki/tls/certs. Linux only.  (Peter Hatina)

* Added '-d' option to MOF compiler that causes the compiler to perform a
  dry-run and just check the MOF file syntax. This allows to more easily
  detect included MOF files when used together with the '-v' option.
  (Jan Safranek)

* Added support for non-ASCII (Unicode) characters.  (Michal Minar, Andreas
  Maier)

* Improved information in the message text of some exceptions (`TypeError`
  and `KeyError` in `cim_obj.py`, `ValueError` in `cim_obj.py`, and
  `ParseError` in `tupleparse.py`).  (Andreas Maier)

* Moved the definition of the pywbem version from `setup.py` to `__init__.py`,
  in order to make it available to programs using pywbem as
  `pywbem.__version__`.  (Andreas Maier)

* Added support for direct iteration over NocaseDict objects using `for`
  and `in` by adding `__iter__()`, e.g. for use with `CIMInstance.properties`.
  (Andreas Maier)

* Added more instance attributes to be shown in `repr()` on `CIMProperty` and
  other classes in cim_obj.  (Andreas Maier)

* Added and improved docstring-based documentation in the pywbem modules
  cim_operations, cim_http, cim_obj, cim_types, and the pywbem module.
  (Andreas Maier)

* Improved the way missing file:// URL support on Windows is handled, by
  now issuing a proper error message instead of stumbling across the
  missing socket.AF_UNIX constant.  (Andreas Maier)

* Improved the way missing OWLocal authorization with the OpenWBEM server
  is handled on Windows, by now issuing a proper error message instead of
  stumbling across the missing `os.getuid()` function.  (Andreas Maier)

* Improved Windows portability by no longer attempting to import `pwd` in
  case the userid is not set in the environment variables that are checked
  when the WBEM server is local.  (Andreas Maier)

* Added support for ExecQuery operation to twisted client.  (Robert Booth)

* Added get() methods on CIMInstance and CIMInstanceName to step up to the
  statement that they behave like dictionaries w.r.t. properties and key
  bindings.  (Andreas Maier)

* Improved help text of test_cim_operations.py test program.
  (Andreas Maier)

* Added an optional Params argument to `InvokeMethod()`, that is an ordered
  list of CIM input parameters, that preserves its order in the CIM-XML
  request message. This is to accomodate deficient WBEM servers that do
  not tolerate arbitrary order of method input parameters as required by
  the standard. The new argument is optional, making this a backwards
  compatible change of `InvokeMethod()`.  (Andreas Maier)

* Cleaned up the public symbols of each module by making symbols private
  that are used only internally. Specifically, the following symbols have
  been made private: In `cimxml_parse`: `_get_required_attribute`,
  `_get_attribute`, `_get_end_event`, `_is_start`, `_is_end`. In `cim_xml`:
  `_text` (was: `Text`).  (Andreas Maier)

* Cleaned up symbols imported by wildcard import by defining `__all__` in
  each module with only the public symbols defined in that module (removing
  any symbols imported into the module), except for the following modules
  which define less than the complete set of public symbols in their
  `__all__`: `mof_compiler`, `twisted_client`, `tupleparse`, `cimxml_parse`,
  `cim_http`.  (Andreas Maier)

* Added support for using CDATA section based escaping in any requests sent
  to the WBEM server. The default is still XML entity reference based
  escaping, the CDATA based escaping can be turned on by setting the switch
  `_CDATA_ESCAPING` accordingly, which is a global variable in the cim_xml
  module.  (Andreas Maier)

* Simplified the exceptions that can be raised by `WBEMConnection` methods,
  and improved the information in the exception messages. See description
  of `WBEMConnection` class for details.  (Andreas Maier)

* Added support for timeouts to `WBEMConnection`, via a new `timeout` argument,
  that defaults to no timeout.  (This finally increased the minimum version
  of Python to 2.6.  (Andreas Maier)

* Improved installation process of PyWBEM, particularly related to
  M2Crypto.  (Andreas Maier)

* Added support for Python 3.  Issue #3 on GitHub.
  (Ross Peoples, Andreas Maier)

Bug Fixes
^^^^^^^^^

* Fix syntax error in CIM DTDVERSION error path.  Allow KEYVALUE
  VALUETYPE attribute to be optional as specified in the DTD.
  (Andreas Linke)

* Added parsing of `InvokeMethod` return value and output parameters for
  Twisted Python client.  (Tim Potter)

* Fixed `cim_provider2.py` to properly support `shutdown()` and `can_unload()`
  (called from CMPI cleanup() functions).  Support was recently added
  to cmpi-bindings for this.  (Bart Whiteley)

* Fixed XML parsing to accept SFCB-style embedded instance parameters.
  (Mihai Ibanescu)

* Use getpass module instead of pwd to detect local user to fix Win32.
  (Tim Potter)

* Re-throw `KeyError` exceptions with capitalised key string instead
  of lower cased version in `NocaseDict.__getitem__()`.  (Tim Potter)

* Use `base64.b64encode()` instead of `base64.encodestring()` in Twisted
  client. (Mihai Ibanescu)

* Fix missing `CIMDateTime` import in Twisted client.  (Mihai Ibanescu)

* Fixed `CIMInstanceName` rendering to string. It is now possible to pass the
  rendered string value as an instance path argument of a CIM method.
  (Jan Safranek, Michal Minar)

* For Python providers, fixed the comparsion of the Role parameter in
  association operations to be case insensitive, and removed an erroneous
  test that raised an exception when the property specified in the Role
  parameter was not also in the property list specified by the Properties
  parameter.  (Jan Safranek)

* For Python providers, converted debug 'print' statements to trace
  messages that end up in the system log.  (Jan Safranek)

* The CIM-XML parser no longer throws an exception when parsing a
  qualifier declaration.
  Note: The CIM-XML supported by this fix does not conform to DSP0201 so
  far. Further fixes are pending.  (Jan Safranek)

* Fixed parsing errors for connection URLs with IPv6 addresses, including
  zone indexes (aka scope IDs).  (Peter Hatina, Andreas Maier)

* Fixed the hard coded socket addressing family used for HTTPS that was
  incorrect in some IPv6 cases, by determining it dynamically.
  (Peter Hatina)

* Fixed the list of output parameters of extrinsic method calls to be
  returned as a case insensitive dictionary (using `cim_obj.NocaseDict`).
  (Jan Safranek)

* Fixed the checking of CIMVERSION attributes in CIM-XML to only verify the
  major version, consistent with DSP0201 (see subclause 5.2.1, in DSP0201
  version 2.3.1).  (Jan Safranek)

* Fixed error in cim_http.py related to stronger type checking of Python
  2.7. (Eduardo de Barros Lima)

* Removed erroneous qualifier scopes SCHEMA and QUALIFIER from the MOF
  compiler (see DSP0004).  (Andreas Maier)

* Fixed debug logging of CIM-XML payload (that is, `conn.last_*request/reply`
  attributes) for extrinsic method calls, to now be consistent with
  intrinsic method calls.  (Andreas Maier)

* Fixed TOCTOU (time-of-check-time-of-use) error when validating peer's
  certificate.  (Michal Minar)

* Added a check in the `CIMInstanceName` constructor that the `classname`
  argument is not None.  (Andreas Maier)

* Fixed the issue in the `CIMProperty` constructor that specifying a tuple
  for the `value` argument was incorrectly detected to be a scalar (and not
  an array).  (Andreas Maier)

* Fixed the issue in the `CIMProperty` constructor that specifying a
  `datetime` or `timedelta` typed value resulted in storing the provided
  object in the `value` attribute, instead of converting it to a
  `CIMDateTime` object.  (Andreas Maier)

* Fixed the issue in the `CIMProperty` constructor that specifying a datetime
  formatted string typed `value` argument along with `type='datetime'`
  resulted in storing the provided string object in the `value` attribute,
  instead of converting it to a `CIMDateTime` object.  (Andreas Maier)

* Fixed several cases in the `CIMProperty` constructor of unnecessarily
  requiring the optional arguments `type`, `is_array`, `embedded_object`,
  or `reference_class`. These optional arguments are now only necessary to
  be provided if they cannot be implied from provided arguments (mainly
  from `value`).  (Andreas Maier)

* Fixed the issue in the `CIMProperty` constructor that an `embedded_object`
  argument value of 'object' was changed to 'instance' when a `CIMInstance`
  typed `value` argument was also provided.  (Andreas Maier)

* Fixed the issue in the `CIMProperty` constructor that the first array
  element was used for defaulting the `type` attribute, without checking
  that for None, causing an exception to be raised in this case.
  (Andreas Maier)

* Added a check in the `CIMProperty` constructor that the `name` argument is
  not None.  (Andreas Maier)

* Fixed the issue that the `CIMProperty` constructor raised only `TypeError`
  even when the issue was not about types; it now raises in addition
  `ValueError`.  (Andreas Maier)

* Changed the exception that is raised in `NocaseDict.__setitem__()` for
  invalid key types, to be `TypeError` in instead of `KeyError`. Updated the
  testcases accordingly.  (Andreas Maier)

* Added checks for more than one argument and for unsupported argument
  types to the constructor of `NocaseDict`.  (Andreas Maier)

* Fixed incorrectly labeled namespace variables in twisted client.
  (Robert Booth)

* Fixed that `WBEMConnection.last_raw_reply` was not set to the current reply
  in case of parsing errors in the reply.  (Andreas Maier)

* Reintroduced Python 2.6 support in `cim_http.HTTPSConnection.connect()`
  that disappeared in early drafts of this version: (Andreas Maier)

  - Removed `SSLTimeoutError` from except list; being a subclass of
    `SSLError`, it is catched via `SSLError`.
  - Invoked `socket.create_connection()` without source_address, if running
    on Python 2.6.

* Fixed bug where HTTP body was attempted ot be read when CIMError header
  is set, causing a hang.  (Andreas Maier)

* Added CIM-XML declaration support for alternative PyWBEM client based
  on twisted.  (Andreas Maier)

* Added support for Windows to wbemcli.py, by making dependency on HOME
  environment variable optional, and adding HOMEPATH environment variable.
  Also, cleaned up the global namespace of wbemcli.py and made it
  importable as a module.  (Andreas Maier)

* Fixed errors in generated MOF (e.g. in any `tomof()` methods): (Andreas Maier)

  - Missing backslash escaping within string literals for `\n`, `\r`, `\t`,
    `\"`.
  - Representation of REF types was incorrect.
  - '=' in array-typed qualifier declarations was missing.
  - Fixed size indicator was missing in array elements.
  - Qualifiers of method parameters were missing.

* Improvements in generated MOF: (Andreas Maier)

  - Changed order of qualifiers to be sorted by qualifier name.
  - Added empty line before each property and method in the class for
    better readability.
  - Method parameters are now placed on separate lines.
  - Moved generation of method qualifiers from class into method. This
    changes the behavior of `CIMMethod.tomof()` to now generate the method
    qualifiers.

* Fixed error where invoking mof_compiler.py with a file based URL that
  did not start with 'file:' failed with an undefined variable `url_` in
  cim_http.py. Issue #1 on GitHub.  (Klaus Kaempf, Andreas Maier)

* Fixed build error that raised a `YaccError` in mof_compiler.py:
  "Syntax error. Expected ':'". Issue #2 on GitHub.  (Andreas Maier)

* Fixed issue where MOF compiler did not find include files with
  a path specified. Issue #4 on GitHub.  (Karl Schopmeyer)

* Added missing `LocalOnly` parameter to `EnumerateInstances()` of
  the wbemcli script. Issue #33 on GitHub.  (Karl Schopmeyer)

* Added workaround for Python 2.6 for Python issue 15881.

* Removed the lex.py and yacc.py files from PyWBEM, and used them from the
  `ply` package, which is their real home. This fixes a number of issues
  because the latest version is now used. Issue #8 on GitHub.i
  (Karl Schopmeyer)

* Fixed the issue that the LEX and YACC table modules were regenerated
  under certain conditions.  Issue #55 on GitHub.  (Karl Schopmeyer)

* Fixed bugs in the mof_compiler script.  (Karl Schopmeyer)

* Fixed errors in the description of the qualifier operations in
  `WBEMConnection`.  Issue #91 on GitHub.  (Andreas Maier)

Testing
^^^^^^^

* Added support for running the unit test cases without having to be in the
  testsuite directory. This was done by setting up the DTD_FILE path
  correctly for any XML tests.  (Andreas Maier)

* Improved the quality of assertion messages issued when testcases fail, to
  include context information and types.  (Andreas Maier)

* Added docstrings to test cases.  (Andreas Maier)

* Added testcases for `CIMProperty.__init__()` to be comprehensive.
  (Andreas Maier)

* In XML validation tests, added the expected XML root element.
  (Andreas Maier)

* Added a header to any error messages issued by xmllint.  (Andreas Maier)

* Fix: Merged stderr into stdout for the xmllint invocation, xmllint error
  messages go to stderr and had been dropped before.  (Andreas Maier)

* Fix: The "mkdir -p ..:" command in the comfychair testcase constructor
  created subdirectories named "-p" when running on Windows; replaced that
  command with `os.makedirs()`.  (Andreas Maier)

* Fix: Replaced the "rm -fr ..." command in the comfychair testcase
  constructor with `shutil.rmtree()`, in order to better run on Windows.
  (Andreas Maier)

* Fix: In `comfychair._enter_rundir()`, moved registration of cleanup
  function `_restore_directory()` to the end, so cleanup happens only if no
  errors happened.  (Andreas Maier)

* Fixed a bug in `pywbem/trunk/testsuite/test_tupleparse.py` in function
  `ParseCIMProperty.runtest()`, where the use of real tab characters caused
  a few lines to be incorrectly indented, and as a result, ignored for the
  test.  (Andreas Maier)

* Improved Windows portability in testsuite: Moved from using the Unix-only
  functions `posix.WIFSIGNALED()` and `posix.WEXITSTATUS()` for testing the
  success of `subprocess.wait()`, to simply testing for 0.  (Andreas Maier)

* Added ability to invoke `test_cim_operations.py` with comfychair arguments,
  and added printing of exception information if an operation fails.
  (Andreas Maier)

* Migrated from comfychair to py.test, standard Python unittest, and to
  tox.  (Andreas Maier)

* Added `test_client.py` with a few initial testcases. This is an end-to-end
  test concept that allows specifying test cases that cover the entire
  PyWBEM Client top to bottom. It mocks the socket layer and allows
  specifying the test cases in YAML, starting with input at the PyWBEM
  Client API (e.g. an operation and its parameters), the expected CIM-XML
  request at the socket payload level resulting from this input (the
  request is verified), the CIM-XML response that is to be generated,
  and finally an expected result at the PyWBEM Client API that is being
  verified.  (Andreas Maier)

* Added use of Travis CI test environment. Commits to GitHub now trigger
  test runs on the Travis CI. A badge on the GitHub README page shows
  the current test result of the master branch, and links to the Travis
  site for the test results of the branches of any pull requests.
  (Andreas Maier)

* Added support for reporting test coverage, using the Python 'coverage'
  package. Coverage is reported on stdout as part of testing, e.g. with
  'make test' for the current Python environment, or with 'tox' for all
  supported Python environments.  (Andreas Maier)

* Added multiple tests for client connection timeout. A mock test was added
  for both HTTP and HTTPs.  However, this causes an error in python 2 with
  HTTPS so two new options were added to test_client.py. First, a new
  parameter ignore_python_version was added to the yaml to define a major
  version of python for which a particulare testcase would be ignored.  Second
  a non-documente option was added to test_client.py to execute a single
  testcase if the name of that testcase is the only parameter on the
  test_client.py cmd line.
  Finally a whole new run_operationtimeout.py file was added to testsuite to
  throughly test for timeouts. This runs ONLY against particular versions of
  OpenPegasus because it required adding a new method to OpenPegasus. However,
  it established that the timeouts apparently now really do work in both
  python 2 and python 3 with both http and https. (see issue #363)

Clean Code
^^^^^^^^^^

* Removed dangerous default parameter `{}` from `CIMProperty` and
  `CIMInstanceName`, and replaced it with `None`. To support that, added
  support for initializing an empty `NocaseDict` object from `None`.
  (Andreas Maier)

* In cim_obj, changed the use of the deprecated backticks to using `%r` in
  the format string (which produces the same result).  (Andreas Maier)

* In the constructor of `CIMInstanceName`, added assertions to some paths
  that cannot possibly be taken based on the fact that the keybindings
  attribute is always a `NocaseDict`. They should be removed at some point.
  (Andreas Maier)

* Addressed PyLint issues: (Andreas Maier, Karl Schopmeyer)

  - Consolidated imports at the top of the module (after module docstring),
    consistent with the PEP-8 recommendation.
  - Ensured order of imports: standard, non-standard, pywbem, local (on a
    subset of modules only).
  - Replaced wildcard imports with specific imports, as much as possible.
  - Removed unused imports.
  - Addressed PyLint issues that are related to whitespace, continuation
    indentation, and line length.
  - Replaced all real tab characters with spaces.
  - Many more PyLint issues

Packaging / Build
^^^^^^^^^^^^^^^^^

* Fixed grammatical funkiness in the license text.  No change to actual
  license - still LGPLv2.  (Tim Potter)

* Added LICENSE.txt file to release.  (Tim Potter)

* Added LICENSE.txt, NEWS, README and INSTALL files to distribution
  archive.  (Andreas Maier)

* Fixed inconsistencies in license text in file headers to consistently
  say LGPL 2.1 or higher (The LICENSE.txt file has always been LGPL 2.1).
  (Andreas Maier)

* Removed confusing section about build from INSTALL file, to scope it just
  to the topic of installation.  (Andreas Maier)

* Restructured pywbem/trunk subtree to move pywbem package files into a
  pywbem subdirectory.  (Andreas Maier)

* Added a makefile (invoke 'make help' for valid targets).  (Andreas Maier)

* Added support for checking the Python source code using PyLint.
  (Andreas Maier)

* Added support for generating HTML documentation using epydoc, and
  included the documentation into the distribution archive. The syntax
  used in Python docstrings is reStructuredText markdown.   (Andreas Maier)

* Added support for installing OS-level prerequisites via the new setup.py
  script commands 'install_os' and 'develop_os'.  (Andreas Maier)

* Added support for installing Python-level prerequisites when installing
  in development mode using the setup.py script command 'develop'.
  (Andreas Maier)


pywbem v0.7.0
-------------

Released: 2008-12-12

Bug Fixes
^^^^^^^^^

* Fixed enumInstances and references in cim_provider to do a deep
  copy of the model before filtering instances so provider writers
  are less surprised.  (Bart Whiteley)

* Added `CIMDateTime.__cmp__()` so that `CIMDateTime` instances can be
  compared.  (Bart Whiteley)

* Fixed data types of method return values for python providers.
  (Bart Whiteley)

* Fixed REF array out parameters in tupleparse.py.
  (Bart Whiteley)

* Fixed Array parameters with no elements.  (Bart Whiteley)

* Fixed precision for real32 and real64 types.  (Bart Whiteley)

* Fixed Array properties where is_array isn't set in `__init__`.
  (Bart Whiteley)

* Added `NocaseDict.__cmp__(self, other)`.  (Bart Whiteley)

* Fixed `WBEMConnection.__repr__` for anonymous connections. (Tim Potter)

* Fixed XML encoding of `CIMQualifierDeclarations`.  (Bart Whiteley)

* Fixed `EnumerateQualifiers` if there are no qualifiers.  (Bart Whiteley)

* Fixed `InvokeMethod` to only send a LOCALCLASSPATH or LOCALINSTANCEPATH,
  not a CLASSPATH or INSTANCEPATH.  (Bart Whiteley)

* Fix unexpected line break in basic auth header for long
  credentials.  (Daniel Hiltgen)

* Fix Host: HTTP header when connecting to a unix domain socket.
  (Bart Whiteley)

* Fix deprecation warnings with Python 2.6.  (Bart Whiteley)

Enhancements
^^^^^^^^^^^^

* Added support for generating Pegasus provider registration MOF in
  `cim_provider.codegen()`. (Bart Whiteley)

* Implemented methods to parse indication export requests.
  (Bart Whiteley)

* Python provider code generation enhancements.  (Bart Whiteley)

* Support for Pegasus Local authentication.  (Bart Whiteley)

* Support for Pegasus and OpenWBEM Unix Domain Socket.  (Tim and Bart)

* Added support for Pegasus non-compliant EMBEDDEDOBJECT XML attribute.
  (Bart Whiteley)

* Added `CIMQualifierDeclaration.tomof()`.  (Bart Whiteley)

* Added a powerful MOF compiler.  (Bart Whiteley)

* Added property filtering to `CIMInstance`.  (Bart Whiteley)

* Added value attribute to `CIMParameter`.  (Bart Whiteley)

* Rigged CIMInstance to automagically update `CIMInstance.path.keybindings`
  as key properties are set.  (Bart Whiteley)

* Added cim_provider2.py: A new provider interface.  Python providers
  using this interface can use the cmpi-bindings project within OMC
  (http://omc-project.org/) to run under any CIMOM supporting the
  CMPI interface.  This is prefered to the old cim_provider.py interface
  that was used with the Python Provider Managers for OpenWBEM and Pegasus.

* Changed `__init__.py` to not import anything from `cim_provider.py` (or
  `cim_provider2.py`) into the pywbem namespace.  Existing providers based
  on `cim_provider.py` can still work with a minor adjustment involving
  importing `CIMProvider` from `pywbem.cim_provider`.  The codegen funtion
  can now be obtained with `from pywbem.cim_provider import codegen`, or
  `from pywbem.cim_provider2 import codegen` or similar.

* Added `wbemcli.py` command line utility.  (Tim Potter)

* Pass keyword args in unix domain socket connection functions down to
  `WBEMConnection()`.  (Tim Potter)


pywbem v0.6
-----------

Released: 2007-10-26

Licensing
^^^^^^^^^

* Relicensed from the GNU GPLv2 to the GNU LGPLv2.

API Changes
^^^^^^^^^^^

* Add a type keyword arg and attribute to `CIMQualifier`, similar to
  the `CIMProperty` object, to allow the creation of null qualifiers.
  (Tim Potter)

* Remove the `toxml()` method from CIM object classes.  Use
  `tocimxml().toxml()` instead which specifies the CIM-XML
  representation of the object. (Tim Potter)

* `CIMDateTime` class should now be used instead of `datetime.datetime`
  and `datetime.timedelta`.

* Added a new method, `CIMInstance.update_existing()`.  This behaves
  like `update()` on a dict, but only assigns new values to existing
  properties.  It skips values for properties not already present
  in the instance.  This is useful for honoring PropertyList within
  python providers.

Bug Fixes
^^^^^^^^^

* Explicitly specify charset="utf-8" in HTTP Content-type header
  as this is required now by the Pegasus cimserver.  (Tim Potter)

* Parse VALUETYPE elements that contain a TYPE attribute.  This
  feature was introduced in version 2.2 of the CIM-XML DTD and
  produced by some CIMOMs such as the Java WBEM Server.  (Tim Potter)

* Don't require `CreateInstance` to have the path attribute set but
  if it is, use the namespace from it.  (Tim Potter)

* Allow extrinsic methods to return object references.  (Tim Potter)

* Fix `CIMInstanceName` to support more numeric types of keybindings.
  (Bart Whiteley)

* Fix datetime values to support utc offset. (Bart Whiteley)

* Fix http client to monitor the connection more closely (RFC 2616
  section 8.2.2).  Previously, a large request could cause a socket
  exception with no ability to read the response and respond to
  an authentication challenge.

* Fix NULL qualifiers to have a (required) type. (Martin Mrazik)

* Fix initialising `CIMInstanceName` keys from a `NocaseDict`. (Bart
  Whiteley)

* Return correct namespace in path for return value from
  `GetInstance`. (Tim Potter)

* Numerous bugfixes to Twisted Python client. (Tim Potter)

* Fix for x.509 SSL certificate handling. (Bas ten Berge)

* `EnumerateClassNames()` now returns an empty list instead of None
  if there are no classes. (Bart Whiteley)

Enhancements
^^^^^^^^^^^^

* Support for OpenWBEM password-less local authentication.
  (Bart Whiteley)

* Support for embedded objects is described in DSP0201-2.2.0
  (Bart Whiteley)

* New `CIMDateTime` class to deal with CIM-isms of datetimes.
  Most notably, datetime deals with timezone info poorly.
  (Bart Whiteley)

* Add `InvokeMethod()` support in Twisted Python client. (Tim
  Potter)


pywbem v0.5
-----------

Released: 2006-11-21

API Changes
^^^^^^^^^^^

* Many API changes were made to simplify the function and object
  interface of PyWBEM.  Aspects of just about every CIM operation
  call and CIM object have changed.  The major changes are:

  - The "LocalNamespacePath" keyword argument has been renamed to
    simply "namespace" for all CIM operations.

  - Replaced all object location classes with `CIMInstanceName`, and
    all instance classes with `CIMInstance`.  `CIMInstanceName` now
    has "host" and "namespace" attributes to fully name a
    reference to an instance.  The `CIMInstance` class now has a
    "path" attribute which is of type `CIMInstanceName`.

  - `EnumerateInstances()` now returns a list of `CIMInstance` objects
    (with path attribute set) instead of a list of
    `CIMNamedInstance` or tuples of `(CIMInstanceName, CIMInstance)`.

  - All representations of properties can now be represented with
    the `CIMProperty` class.

* All classes now have a `copy()` method which return a deep copy of
  the object.  PyWBEM makes extensive use of dictionary objects
  which are passed by reference in Python.  Use the `copy()` method
  to create and manipulate objects without modifying them by
  accident.

Bug Fixes
^^^^^^^^^

* Fix parse bug when a `CIMInstanceName` is passed as the
  localobject parameter to `WBEMConnection.InvokeMethod()`.

* Fix parsing of INSTANCE elements containing PROPERTY.REFERENCE
  elements bug found by Bart Whiteley.  This turns up when
  processing associations. (Tim Potter)

* Handle extrinsic method calls that don't return a value or any
  output parameters. (Tim Potter)

* Fixed parsing of PARAMETER.ARRAY and PARAMETER.REFARRAY to
  not require optional attrs. (Bart Whiteley)

* Atomic_to_cim_xml string generation for a datetime - was missing
  a >> '.' in the string. (Norm Paxton)

* `InvokeMethod` did not provide for `None` in output parameters.
  (Norm Paxton)

Enhancements
^^^^^^^^^^^^

* More parts of the class provider interface have been
  implemented.  (Tim Potter, Bart Whiteley)

* Many case-sensitivity bugs, mostly in `__cmp__` methods, were
  found and fixed.  (Tim Potter)

* Implemented a test suite for maintaining backward compatibility
  and testing new features.  (Tim Potter)

* Implemented ExecQuery. (Bart Whiteley)

* Allow a string classname to be passed as the localobject
  parameter to `WBEMConnection.InvokeMethod()`. (Tim Potter)

* Add missing qualifiers on array properties. (Bart Whiteley)

* Added code for performing asynchronous WBEM client operations
  using the Twisted Python framework. (Tim Potter)

* Allow extrinsic method calls that take parameters. (Tim Potter)

* Added `cim_http.AuthError` exception class.  This is raised if the
  CIMOM returns a 401 (Unauthorized).  Now the client can
  distinguish this condition, and (re)prompt for credentials.
  (Bart Whiteley)

* Created `cim_obj.CIMParameter` class.  Added return type,
  class origin, propagated to `CIMMethod`.  `CIMParameter` object
  now allows parameter types and qualifiers to be obtained.
  (Bart Whiteley)

* Implemented case-insensitive keys for property and qualifier
  dictionaries, as per the CIM specification.  (Tim Potter, Bart
  Whitely)


pywbem v0.4
-----------

Released: 2005-11-15

Bug Fixes
^^^^^^^^^

* Correctly calculate value of Content-Length HTTP header to include
  opening XML stanza. (Szalai Ferenc)

* Fix syntax error when re-raising socket errors. (Pat Knight)

Enhancements
^^^^^^^^^^^^

* Support for marshaling and unmarshaling CIM dates object into
  Python datetime objects. (Szalai Ferenc)

* Experimental module for making asynchronous WBEM calls with
  PyWBEM in Twisted Python. (Tim Potter)

* Add parameter type checking for object location classes. (Tim
  Potter)

* Allow caller to pass in a dictionary containing the location of
  the SSL certificate and key files as per the httplib.HTTPSConnection()
  class constructor. (Pat Knight)

API Changes
^^^^^^^^^^^

* Change association provider API functions to take a fixed
  parameter for the named object instead of a keyword argument.
  This breaks backward compatibility. (Tim Potter)

* Remove the `CIMLocalNamespacePath` class and replaced by a Python
  string. (Tim Potter)

Portability
^^^^^^^^^^^

* Don't use `UserDict.DictMixin` base class as it only exists in
  Python 2.3 and higher. (Tim Potter)

Tests
^^^^^

* Add tests for parameter type checking for object location
  classes. (Tim Potter)

* Add tests for string representation of object location classes.
  (Tim Potter)
