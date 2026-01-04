Listener: Added new exception :exc:`pywbem.ListenerStartError` to indicate
problems when starting the listener using the :meth:`pywbem.WBEMListener.start`
method and improved the error handling in that method.
Changed :exc:`pywbem.ListenerPortError` to become a subclass of the new
exception.
