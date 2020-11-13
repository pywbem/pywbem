Pywbem - A WBEM client and related utilities, written in pure Python
====================================================================

.. image:: https://badge.fury.io/py/pywbem.svg
    :target: https://pypi.python.org/pypi/pywbem/
    :alt: PyPI Version

.. image:: https://github.com/pywbem/pywbem/workflows/test/badge.svg?branch=master
    :target: https://github.com/pywbem/pywbem/actions/
    :alt: Actions status

.. image:: https://readthedocs.org/projects/pywbem/badge/?version=latest
    :target: https://readthedocs.org/projects/pywbem/builds/
    :alt: ReadTheDocs status

.. image:: https://coveralls.io/repos/github/pywbem/pywbem/badge.svg?branch=master
    :target: https://coveralls.io/github/pywbem/pywbem?branch=master
    :alt: Coveralls result

.. image:: https://img.shields.io/pypi/pyversions/pywbem.svg?color=brightgreen
    :target: https://pypi.python.org/pypi/pywbem/
    :alt: Supported Python


.. # .. contents:: **Contents:**
.. #    :local:

Overview
--------

Pywbem is a WBEM client and WBEM indication listener and provides related
WBEM client-side functionality. It is written in pure Python and runs on
Python 2 and Python 3.

WBEM is a standardized approach for systems management defined by the
`DMTF <https://www.dmtf.org>`_ that is used in the industry for a wide variety
of systems management tasks. See
`WBEM Standards <https://www.dmtf.org/standards/wbem>`_ for more information.
An important use of this approach is the
`SMI-S <https://www.snia.org/tech_activities/standards/curr_standards/smi>`_
standard defined by `SNIA <https://www.snia.org>`_ for managing storage.

Functionality
-------------

The major components of pywbem are shown in this diagram:

.. image:: images/pywbemcomponents.png
   :alt: pywbem components

The green components all have Python APIs for use by user applications.
The yellow components are command line utilities.
The blue components are not part of the pywbem or pywbemtools packages.

The pywbem components all run on the client side and communicate with a remote
WBEM server using the standard CIM operations over HTTP (CIM-XML) protocol
defined by the DMTF.

Pywbem provides the following Python APIs:

* `WBEM Client Library`_ - An API that supports issuing WBEM operations to a
  WBEM server, using the CIM operations over HTTP (CIM-XML) protocol defined
  by the DMTF.

* `WBEM Server Library`_ - An API that encapsulates selected functionality of a
  WBEM server for use by a WBEM client application, such as determining the
  Interop namespace and other basic information about the server, or the
  management profiles advertised by the server.

* `WBEM Indication Listener`_ - An API for creating and managing a thread-based
  WBEM listener that waits for indications (i.e. event notifications) emitted
  by a WBEM server using the CIM-XML protocol. The API supports registering
  callback functions that get called when indications are received by the
  listener.

* `WBEM Subscription Manager`_ -  An API for viewing and managing subscriptions
  for indications on a WBEM server.

* `MOF Compiler`_ - An API for compiling MOF files or strings into a CIM
  repository (e.g. on a WBEM server), or for test-compiling MOF.

* `Mock WBEM server`_ - An API for setting up a mocked WBEM server that is used
  instead of a real WBEM server. This allows setting up well-defined WBEM
  servers locally that can be used for example for prototyping or testing user
  applications.

Pywbem provides this command line utility:

* `mof_compiler`_ - A MOF compiler that takes MOF files as input and compiles
  them into a CIM repository (e.g. on a WBEM server).

The related `pywbemtools project`_ provides this command line utility:

* `pywbemcli`_ - A client-side command line interface for a WBEM server,
  supporting a command line mode and an interactive (repl) mode.

.. _WBEM Client Library: https://pywbem.readthedocs.io/en/latest/client.html
.. _WBEM Server Library: https://pywbem.readthedocs.io/en/latest/server.html
.. _WBEM Indication Listener: https://pywbem.readthedocs.io/en/latest/indication.html
.. _WBEM Subscription Manager: https://pywbem.readthedocs.io/en/latest/subscription.html
.. _MOF Compiler: https://pywbem.readthedocs.io/en/latest/compiler.html
.. _Mock WBEM server: https://pywbem.readthedocs.io/en/latest/mockwbemserver.html
.. _mof_compiler: https://pywbem.readthedocs.io/en/latest/utilities.html#mof-compiler
.. _pywbemtools project: https://github.com/pywbem/pywbemtools
.. _pywbemcli: https://pywbemtools.readthedocs.io/en/latest/pywbemcli


Installation
------------

To install the latest released version of pywbem into your active Python
environment:

.. code-block:: bash

    $ pip install pywbem

This will also install any prerequisite Python packages.

Starting with version 1.0.0, pywbem has no OS-level prerequisite packages.

For more details and alternative ways to install, see the
`Installation section`_ in the pywbem documentation.

.. _Installation section: https://pywbem.readthedocs.io/en/latest/intro.html#installation

Documentation
-------------

* `Documentation`_ - Concepts, tutorials, Python API, command line tools,
  and developer documentation.

.. _Documentation: https://pywbem.readthedocs.io/en/latest/

* `Tutorial`_ - The tutorials in the documentation are provided as Jupyter
  notebooks and provide working examples of pywbem API usage.

.. _Tutorial: https://pywbem.readthedocs.io/en/latest/tutorial.html

* `Change log`_ - Detailed change history in the documentation.

.. _Change log: https://pywbem.readthedocs.io/en/latest/changes.html

* `Presentations`_ - status, concepts, and implementation of pywbem.

.. _Presentations: https://pywbem.github.io/pywbem/documentation.html


Quick Start
-----------

The following simple example script lists the namespaces and the Interop
namespace in a particular WBEM server:

.. code-block:: python

    #!/usr/bin/env python

    import pywbem

    server_url = 'http://localhost'
    user = 'fred'
    password = 'blah'

    conn = pywbem.WBEMConnection(server_url, (user, password))

    server = pywbem.WBEMServer(conn)

    print("Interop namespace:\n  %s" % server.interop_ns)

    print("All namespaces:")
    for ns in server.namespaces:
        print("  %s" % ns)

Project Planning
----------------

For each upcoming release, the bugs and feature requests that are planned to
be addressed in that release are listed in the
`issue tracker <https://github.com/pywbem/pywbem/issues>`_
with an according milestone set that identifies the target release.
The due date on the milestone definition is the planned release date.
There is usually also an issue that sets out the major goals for an upcoming
release.

Planned Next Release
--------------------

Fix versions of pywbem are released as needed.

The next planned feature version(s) of pywbem can be found by listing the
`release definition issues`_.

.. _release definition issues: https://github.com/pywbem/pywbem/issues?q=is%3Aissue+is%3Aopen+label%3A%22release+definition%22

Contributing
------------

For information on how to contribute to pywbem, see the
`Contributing section`_ in the pywbem documentation.

.. _Contributing section: https://pywbem.readthedocs.io/en/latest/development.html#contributing


License
-------

Pywbem is provided under the
`GNU Lesser General Public License (LGPL) version 2.1
<https://raw.githubusercontent.com/pywbem/pywbem/master/LICENSE.txt>`_,
or (at your option) any later version.
