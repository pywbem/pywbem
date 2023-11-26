Installation of pywbem
======================

To install the latest released version of pywbem into your active Python
environment:

      $ pip install pywbem

This will also install any prerequisite Python packages.

Since version 1.0.0, pywbem has no more OS-level prerequisite packages.

On newer versions of some OS's'(ex. Ubuntu 23.04, Debian 12) pywbem
will only install into a virtual environment. This is by design to avoid conflicts
between OS distributed python packages and other user installed packages and is
documented in `Python PEP 668`_. See the pywbem documentation
`Troubleshooting section`_ for more information if an "Externally-managed-environment"
error occurs during installation.

For more details and alternative ways to install, see the
[Installation section](https://pywbem.readthedocs.io/en/stable/intro.html#installation)
in the pywbem documentation.
