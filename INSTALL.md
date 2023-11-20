Installation of pywbem
======================

To install the latest released version of pywbem into your active Python
environment:

      $ pip install pywbem

This will also install any prerequisite Python packages.

Since version 1.0.0, pywbem has no more OS-level prerequisite packages.

On newer versions of some OS's (ex. Ubuntu 23.10, Debian 12) pywbem can only
be installed into a virtual environment.  If an attempt is made to install it
into the system directories the install will fail with a message about
"externally managed" environments.

For more details and alternative ways to install, see the
[Installation section](https://pywbem.readthedocs.io/en/stable/intro.html#installation)
in the pywbem documentation.
