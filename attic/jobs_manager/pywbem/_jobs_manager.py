#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
"""
The :class:`~pywbem.WBEMJobsManager` class is a  manager for CIM Jobs
that provides for managing long running tasks defined by the DMTF CIM Jobs and
subclasses on multiple WBEM servers
"""
__all__ = ['WBEMSubscriptionManager']

JOB_CLASSNAME = 'CIM_ConcreteJob'

JOB_OWNINGELEMENT = 'CIM_OwningJobElement'
JOB_AFFECTEDELEMENT = 'CIM_AffectedJobElement'

class WBEMJobsManager(object):
    """
    A class for managing CIM Jobs on WBEM servers.

    The class may be used as a Python context manager, in order to get
    automatic clean up (see :meth:`~pywbem.JobsManager.__exit__`).

    This class is a tool to:

    1. Get overall status on existing jobs in WBEMServers.
    2. invoke request job status changes
    3. Add/remove servers from the list that this class is actively managing
    4. TODO, should we allow both a server and active job to be added to
       the list being managed by this class???. Certainly another part of the
       client could add a new server but is it logical for it to be able to
       add a job path?

    5. Is there any logic to this class being able to execute indication
       subscriptions to manage jobs??? i.e. monitor status.

    6. Note that at this point we do not have a separate job class but depend
       on the pywbem class for the job that is returned from a server or
       input.

    AT This point this code does NOT include a job constructor since we see
    that as the responsibility of the server???
    Also, we are dependent on the job path as a job_id
    """

    def __init__(self):
        """
        Parameters:
        """
        self._servers = {}  # WBEMServer objects for the WBEM servers

    def __repr__(self):
        """
        Return a representation of the :class:`~pywbem.WBEMJobsManager`
        object with all attributes, that is suitable for debugging.
        """
        return "%s(_subscription_manager_id=%r,)" % \
               (self.__class__.__name__,)

    def __enter__(self):
        """
        Enter method when the class is used as a context manager.
        Returns the subscription manager object
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Exit method when the class is used as a context manager.

        It cleans up by calling
        :meth:`~pywbem.WBEMJobs.remove_all_servers`.
        """
        self.remove_all_servers()
        return False  # re-raise any exceptions

    def _get_server(self, server_id):
        """
        Internal method to get the server object, given a server_id.

        Parameters:

          server_id (str):
            The server ID of the WBEM server, returned by
            :meth:`~pywbem.WBEMJobs.add_server`.

        Returns:

          server (:class:`~pywbem.WBEMServer`):
            The WBEM server.

        Raises:

            ValueError: server_id not known to subscription manager.
        """

        if server_id not in self._servers:
            raise ValueError('WBEM server %s not known by subscription '
                             'manager' % server_id)

        return self._servers[server_id]

    def add_server(self, server):
        """
        Register a WBEM server with the jobs manager. This is a
        prerequisite for working with jobs on a server

        Parameters:

          server (:class:`~pywbem.WBEMServer`):
            The WBEM server.

        Returns:

            str: An ID for the WBEM server, for use by other
            methods of this class.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            ValueError, TypeError for incorrect input parameters.
        """

        if not isinstance(server, WBEMServer):
            raise TypeError("Server argument of add_server() must be a "
                            "WBEMServer object")
        server_id = server.url
        if server_id in self._servers:
            raise ValueError("WBEM server already known by listener: %s" %
                             server_id)

        # Create dictionary entries for this server
        self._servers[server_id] = server

        #TODO FINISH CODE

    def remove_server(self, server_id):
        """
        Remove a registered WBEM server from the subscription manager. This
        also unregisters listeners from that server and removes all owned
        indication subscriptions, owned indication filters and owned listener
        destinations that were created by this subscription manager for that
        server.

        Parameters:

          server_id (str):
            The server ID of the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        # Validate server_id
        server = self._get_server(server_id)

        # Delete any instances we recorded to be cleaned up

        # Remove server from this listener
        del self._servers[server_id]

    def add_job(server, job_path):
        """
        This would add a job to our monitor store. This would allow another
        component of the client to ask this component to work with a specific
        job where it had the
        """

    def get_jobs_from_server(self, server_id):
        """
        Return all existing jobs in a WBEM server.

        This function contacts the WBEM server and retrieves any existing
        jobs

        Parameters:

          server_id (str):
            The server ID of the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

        Returns:

            :class:`py:list` of :class:`~pywbem.CIMConcreteJob`: The job
            subscription instances.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        # Validate server_id
        server = self._get_server(server_id)

        #TODO should
        return server.conn.EnumerateInstances(JOB_CLASSNAME,
                                              namespace=server.interop_ns)

        #TODO right now we are just returning jobs, not putting them into
        # our own store

    def get_job_status(server_id, job_id):
        """
        TODO: Probably better to have specific function for each possible
        status component (start time, state, status, %complete, job_id)
        """
    def get_job_state(server_id, job_id):
        """
            Get the current operational state of the job.

            Parameters:

            Returns:

            Exceptions:
        """

    def delete_job(server_id, job_id):
        """
        """

    # Define the possible requested states. They appear to be
    # suspend/resume, terminate, and kill
    # DECISION: Probably better to have specific methods for each state
    # change.
    def change_job_status(server_id, job_id, requested_state,
        timeout_period=None):
        """
        """
    def suspend_job(server_id, job_path):
        """
        Issues request to server to suspend the job. The job will remain
        suspended until it is resumed.

        Paramsters:

        Returns:

        Exceptions:
        """

    def resume_job(server_id, job_id):
        """
        Starts a suspended. If the method fails additional information may be
        available in the thrown exception and by calling getError(). This
        method can only be called while the job is in the “Suspended” state.
        Resuming makes a “Start” request to change the state of the job to
        “Running.”
        """

    def terminate_job(server_id, job_id):
        """
        """

    def kill_job(server_id, job_id):
        """
        Terminates the job immediately with no requirement to save data
        or preserve the state. If the method fails additional information may
        be available in the thrown exception and by calling getError(). This
        method can be called while the job is one of the following states.
        “Starting” “Running” “Suspended” “Exception” “Service”

        Parameters:

        Returns:
        """
