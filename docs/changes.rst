
.. _`Change log`:

Change log
==========

.. ifconfig:: version.endswith('dev0')

.. # Reenable the following lines when working on a development version:

This version of the documentation is development version |version| and
contains the `master` branch up to this commit:

.. git_changelog::
   :revisions: 1


pywbem v0.10.0.dev0
-------------------

Released: Not yet

Deprecations
^^^^^^^^^^^^


Known Issues
^^^^^^^^^^^^


Enhancements
^^^^^^^^^^^^

* add flake8 as a lint tool.  It is executed with makefile check target.
  see issues #512, #523

* Improved usage information for Tutorial section, to make usage of Jupyter
  tutorials more obvious.

* Added Installation and Development sections to the documentation, and moved
  some content from the Introduction section into a new Appendix. Added
  an installation trouble shooting section to the Appendix.

* Added a section "Prerequisite operating system packages" to the documentation
  that describes the prerequisite packages by distribution.

* Modified xml parser to use sax parser in place of DOM parser for operation
  response processing and indication processing  This is a significant reduction
  in memory usage. See issue # 498.

* Declared the WBEM indications API and the WBEM server API to be final. These
  APIs had been introduced in v0.9.0 as experimental.

* Added `git` as an OS-level dependency for development (it is used by GitPython
  when building the documentation).

* Added enter and exit methods to `WBEMSubscriptionManager` to enable using it
  as a context manager, whose exit method automatically cleans up by calling
  `remove_all_servers()`.

* Added CIM Schema archive to the repository, in order to avoid repeated
  downloads during testing in the CI systems.

* Added methods to the operation recorder (class `BaseOperationRecorder`) for
  disabling and enabling it. (issue #493).

Bug fixes
^^^^^^^^^

* Fixed the use of a variable before it was set in the `remove_destinations()`
  method of class `WBEMSubscriptionManager`.

* Fixed a compatibility issue relative to pywbem 0.7.0, where the
  `pywbem.Error` class was no longer available in the `pywbem.cim_http`
  namespace. It has been made available in that namespace again, for
  compatibility reasons. Note that using sub-namespaces of the `pywbem`
  namespace such as `pywbem.cim_http` has been deprecated in pywbem 0.8.0.

* Fixed a documentation issue where the description of `CIMError` was not
  clear that the exception object itself can be accessed by index and slice.

* Changed names of the pylint and flake8 config files to match the
  default names defined for these utilities (pylintrc and .flak8). Issue 534

* Fixed a documentation build error on Python 2.6, by pinning the GitPython
  version to <=2.0.8, due to its use of unittest.case which is not available
  on Python 2.6.

* Fixed an `AttributeError` in the `remove_all_servers()` method of
  `WBEMSubscriptionManager` and dictionary iteration errors in its
  `remove_server()` method. PR #583.

* Modified cim_operations that have a PropertyList attribute to allow the
  PropertyList attribute to have a single string in addition to the iterable.
  Previously this caused an XML error (issue #577).


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
