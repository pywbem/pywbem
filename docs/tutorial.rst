
.. _`Tutorial`:

Tutorial
========

This section contains a few short tutorials about using pywbem. It is intended
to be enough to get people up and going who already know a bit about WBEM and
CIM.

The tutorials in this section are
`Jupyter Notebooks <https://jupyter-notebook-beginner-guide.readthedocs.io/>`_,
and are shown using the online
`Jupyter Notebook Viewer <https://nbviewer.jupyter.org/>`_.
This allows viewing the tutorials without having Jupyter Notebook installed
locally.

In order to view a tutorial, just click on a link in this table:

===================================== ==========================================
Tutorial                              Short description
===================================== ==========================================
:nbview:`connections.ipynb`           Making connections to a WBEM server
:nbview:`datamodel.ipynb`             Representation of CIM objects in Python
:nbview:`enuminsts.ipynb`             EnumerateInstances
:nbview:`enuminstnames.ipynb`         EnumerateInstanceNames
:nbview:`getinstance.ipynb`           GetInstance
:nbview:`createdeleteinst.ipynb`      CreateInstance + DeleteInstance
:nbview:`modifyinstance.ipynb`        ModifyInstance
:nbview:`invokemethod.ipynb`          InvokeMethod
:nbview:`pulloperations.ipynb`        The Pull Operations
:nbview:`iterablecimoperations.ipynb` The Iterable Operation Extensions
:nbview:`wbemserverclass.ipynb`       Pywbem WBEMServer Class
:nbview:`subscriptionmanager.ipynb`   Subscription Manager
===================================== ==========================================

For the following topics, tutorials are not yet available:

* ExecQuery
* Association Operations
* Class Operations
* Qualifier Operations
* WBEMListener
* Iter* Operations

Executing code in the tutorials
-------------------------------

You cannot directly modify or execute the code in the tutorials using the
Jupyter Notebook Viewer, though. In order to do that, the Jupyter Notebook
Viewer provides a download button at the top right corner of the page.

You must have Jupyter Notebook
`installed <https://jupyter.readthedocs.io/en/latest/install.html>`_,
preferrably in a
`virtual Python environment <https://docs.python-guide.org/en/latest/dev/virtualenvs/>`_,
and you must have pywbem installed.

To see a list of your downloaded notebook files, start Jupyter Notebook as
follows::

    jupyter notebook --notebook-dir={your-notebook-dir}
