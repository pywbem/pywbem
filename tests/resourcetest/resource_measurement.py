"""
Context manager that measures resource consumption of its body.
"""

import tracemalloc

from .timers import Timer


class ResourceMeasurement(object):
    """
    Context manager that measures resource consumption of its body.

    Example::

        with ResourceMeasurement() as rm:
            # code to be measured
        print(rm.cpu_time_ms)

    Attributes:

      peak_size (int): Peak size in Bytes used during execution of the body, as
        reported by tracemalloc.

      elapsed_time_ms (int): Elapsed (wall clock) time in ms for the execution
        of the body.

      cpu_time_ms (int): CPU (execution) time in ms for the execution
        of the body.
    """

    def __init__(self):
        self.timer = Timer()
        self.peak_size = None
        self.elapsed_time_ms = None
        self.cpu_time_ms = None

    def __enter__(self):
        self.timer.start()
        tracemalloc.start()  # pylint: disable=no-member  # On pypy3
        return self

    def __exit__(self, exc_type, exc_value, traceback):

        # pylint: disable=no-member  # On pypy3
        _, self.peak_size = tracemalloc.get_traced_memory()
        self.timer.stop()
        tracemalloc.stop()  # pylint: disable=no-member  # On pypy3
        self.elapsed_time_ms = self.timer.elapsed_ms()
        self.cpu_time_ms = self.timer.cpu_ms()
        return False  # re-raise any exceptions
