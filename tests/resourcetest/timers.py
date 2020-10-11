"""
Utility functions for measuring time.
"""

from datetime import datetime
try:
    import psutil
except ImportError:
    # No psutil support e.g. on CygWin
    psutil = None


class Timer(object):
    """
    Timer measuring elapsed time (= wall clock time) and CPU time
    (= execution time).

    Elapsed time is measured using 'datetime.datetime.now()'.
    Its resolution depends on the platform.

    CPU time is measured using the 'psutil' package using the 'cpu_times()'
    method on the current process. The CPU time includes user time and system
    time across all CPUs of the system in context of the current process.
    Its resolution depends on the platform.
    """

    def __init__(self):
        """
        Initialize the timer. It is initially not running.
        """
        self.start_datetime = None
        self.start_cpu_times = None
        self.stop_datetime = None
        self.stop_cpu_times = None
        self.process = psutil.Process() if psutil else None

    @property
    def running(self):
        """
        Return bool indicating whether the timer is running.
        """
        return self.start_datetime is not None and self.stop_datetime is None

    def start(self):
        """
        Start the timer.
        """
        self.start_datetime = datetime.now()
        if psutil:
            self.start_cpu_times = self.process.cpu_times()
        self.stop_datetime = None
        if psutil:
            self.stop_cpu_times = None

    def stop(self):
        """
        Stop the timer.

        The timer must be running.
        """
        stop_datetime = datetime.now()
        if psutil:
            stop_cpu_times = self.process.cpu_times()
        if not self.running:
            raise ValueError("Timer is not running")
        self.stop_datetime = stop_datetime
        if psutil:
            self.stop_cpu_times = stop_cpu_times

    def elapsed_ms(self):
        """
        Get the elapsed time in milliseconds between last start and stop.

        The timer must not be running.

        Returns:
           float: Elapsed time in milliseconds.
        """
        if self.running:
            raise ValueError("Timer is running")
        dt = self.stop_datetime - self.start_datetime
        return ((dt.days * 24 * 3600) + dt.seconds) * 1000 + \
            dt.microseconds / 1000.0

    def cpu_ms(self):
        """
        Get the CPU time (= execution time) in milliseconds between last
        start and stop.

        The CPU time is the total spent on all CPUs of the system and
        includes user time plus system time.

        The timer must not be running.

        If the platform does not support the 'psutil' package, 0.0 is returned.

        Returns:
           float: CPU time in milliseconds.
        """
        if self.running:
            raise ValueError("Timer is running")
        if not psutil:
            return 0.0
        dt_user = self.stop_cpu_times.user - self.start_cpu_times.user
        dt_system = self.stop_cpu_times.system - self.start_cpu_times.system
        dt = dt_user + dt_system
        return dt * 1000
