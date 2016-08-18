[![Test on master](https://img.shields.io/travis/pywbem/pywbem/master.svg?style=plastic&label=test%20on%20master)](https://travis-ci.org/pywbem/pywbem/branches)
[![PyPI version](https://img.shields.io/pypi/v/pywbem.svg?style=plastic&label=PyPI%20version)](https://pypi.python.org/pypi/pywbem)

About this project
------------------

Pywbem is a WBEM client, written in pure Python. It runs on Python 2 and
Python 3.

A WBEM client allows issuing operations to a WBEM server, using the CIM
operations over HTTP (CIM-XML) protocol defined in the DMTF standards DSP0200
and DSP0201. The CIM/WBEM infrastructure is used for a wide variety of systems
management tasks supported by systems running WBEM servers. See
[WBEM Standards](http://www.dmtf.org/standards/wbem) for more information about
WBEM.

Usage
-----

For information on how to use pywbem, or how to contribute to it, go to the
[pywbem page](http://pywbem.github.io/pywbem/).

Project plans
-------------

**Version 0.9.0** - (UPDATE 21 Aug. 2016) - Delaying 0.9.0 release by
one more week to resolve open issues. Current expected release is now
26 August 2016

**Version 0.9.0** - (UPDATE 2 Aug. 2016) The pywbem team has concluded that
we will delay the release of version 0.9.0 to 20 August 2016 because of a couple
of open issues, in particular, the new listener. While the current listener in
the development code works we feel we should restructure it to allow indication
listeners to be independent of the functions of subscription management.
Otherwise, anybody who uses the existing code could be subjected to a major
rewrite in version 0.10.0.

This release was orignally scheduled for
early June 2016.  See issue #163 for an overview of version 0.9.0 goal sand the
github issues for milestone 0.9.0 for details on what changes are done and
planned for pywbem version 0.9.0.

**Version 0.10.0** - Next version after the version 0.9.0 release. See the issues
for milestone 0.10.0 for current planning for this release. Generally release
expected about 2 months after 0.9.0 but that is a very preliminary estimate.

License
-------

Pywbem is provided under the
[GNU Lesser General Public License (LGPL) version 2.1](src/pywbem/LICENSE.txt),
or (at your option) any later version.
