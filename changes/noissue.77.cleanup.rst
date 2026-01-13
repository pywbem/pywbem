The stoppable thread functionality was moved from ``CallbackThread`` into a new
``StoppableThread`` class, and the exception handling functionality was moved
from ``ServerThread`` into a new ``ExceptionHandlingThread`` class, in order to
be able to use both in a derived class in the future.
The ``ServerThread`` class now inherits from ``ExceptionHandlingThread``, and
the ``CallbackThread`` class now inherits from ``StoppableThread``, and thus
they have no change in functionality.
