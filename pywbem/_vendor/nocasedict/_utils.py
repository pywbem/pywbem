"""
Utility functions of the nocasedict package.
"""

import inspect


def _stacklevel_above_nocasedict():
    """
    Return the stack level (with 1 = caller of this function) of the first
    caller that is not defined in the _nocasedict module and that is not
    a method of a class named 'NocaseDict' (case insensitively). The second
    check skips user classes derived from nocasedict.NocaseDict.

    The returned stack level can be used directly by the caller of this
    function as an argument for the stacklevel parameter of warnings.warn().
    """
    stacklevel = 2  # start with caller of our caller
    frame = inspect.stack()[stacklevel][0]  # stack() level is 0-based
    while True:
        if frame.f_globals.get('__name__', None) != '_nocasedict':
            try:
                class_name = frame.f_locals['self'].__class__.__name__.lower()
            except KeyError:
                class_name = None
            if class_name != 'nocasedict':
                break
        stacklevel += 1
        frame = frame.f_back
    del frame
    return stacklevel
