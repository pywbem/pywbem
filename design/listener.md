Design for WBEM listener
========================

Requirements
------------

   * Must support an easy way for applications to subscribe for indications, and
     to get the corresponding indications.

   * Subscriptions from one "application" must be independent from subscriptions
     by another application, so that each application has its own scope and can
     manage its own subscriptions independently.

   * Must be able to start and stop the listener service.

   * The listener service should have a simple default way to be run (e.g. as a
     thread) but should also be integrateable into external service frameworks.

   * Must support multiple WBEM servers.

Design notes
------------

   * An "application" is a Python process.

   * Each Python process has the listener demon included in the form of a
     thread.

     - That automatically results in each application having its own scope of
       managing subcriptions.
     - On the downside, the price for that is that two Python processes on the
       same client system that subscribe for the same set of indications get
       them delivered bythe WBEM server once for each of them.
     - Another downside is that each such listener demon occupies one port
       (or set of ports) on the client system.
     - However, it is probably rare to have multiple applications interested
       in indications on the same system.

   * Indications are communicated to the subscribing application:

     - By callback function
     - Other mechanisms are left for the future (e.g. some event notification)
