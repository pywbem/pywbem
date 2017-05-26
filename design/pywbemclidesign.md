#Design Document for a PyWBEM Command Line Browser


Status: In Process
Date: 9 Feb. 2017
      Update 11 Feb 2017

##Goals

* Python Based
* Expandable. Users should be able to add functionality with plugins
* Usable effectively by both occasional and power users
  * Interactive mode
  * Script mode (complete command entered from command line)
* Capable of executing all WBEM CIM/XML operations (with specific exceptions)
* Include commands for other operations that will be a real advantage to
developers, users, etc.
* Good integrated help to minize requirement for external documentation

##Licensing

Since the goal is to have the code in a separate repository, we propose to use
a more liberal license.  Either MIT or the Apache license is logical.  Since
the Apache v2 license has one additional feature above MIT (patent right to use)
that seems like a logical solution.

Conclusion: Use Apache 2 license. However, lets do license/ copyright statements
once and ref in files instead of keeping whole license statement in each file.


## Code Location

We propose that the code be in a separate git repository in the pywbem project
for a number of reasons including:

* It uses a number of additional packages that are not used elsewhere in the
pywbem client package and this imposes an extra set of constraints on uses
of just the infrastructure.
* It is not certain that the cli can meet the same python versoning constraints
as the client infrastructure code because of the extra packages used some of
which are not today compatible with python 2.6.

It would have its own release cycle, etc.  However since pywbem and pywbemcli
are closely developed we should seriously consider integrating them into a
single documentation set.

The only negatives to this approach are:

* We now have two repositories to maintain with two issue lists, etc.
* It will be more difficult to consider using pywbemcli as a testtool for
pywbem itself, in part because they are on different development and release
cycles.
  

## Command Taxonomy

Overall we propose that this be written in the manner of a command <subcommand>
environment where there is a single cli and multiple subcommands.

Wheras most wbem clis are written to parallel the client api taxonomy
(separate subcommands to match the individual methods of the client api)
we propose that the taxonomy of this cli be organized around the following
levels:

* first subcommand - noun representing the entity type against which the
command is to be executed (class, instance, qualifierdecl, server,
subscription manager, log, connection, etc.)
* the second level subcommand be an action on that entity, for example, get,
delete, create, enumarate, etc.
* The options for each subcommand represent
  * All of the options available for the corresponding client api (i.e.
    localonly, includeclassorigin, includequalifiers, propertylist, etc.)
  * Include only the maxObjectCount as an option to represent the existence
    of pull operations
  * ability to select namespace be included in all commands except those that
    do not need a namespace or use all namespaces.

The following is the current overall taxonomy of subcommands and their major
options.

**pywbemwcli**

* **class**
  * **get** &lt;classname> --namespace &lt;getclass options> (corresponds to getclass)  
  * **enumerate**  (corresponds to enumerateclasses) &lt;classname> --namespace --names-only &lt;enumerateclass options>  
  * **references**  &lt;sourceclass> --namespace --names_only &lt;references options>(corresponds to class references)  
  * **associators** &lt;sourceclass> --namespace --names_only &lt;associator options>(corresponds to class associators)  
  * **method** &lt;classname> &lt;methodname> [&lt;param_name=value>]*  
  * **find** Find a class across namespaces (regex names allowed)
  
* **instance**
  * **get** &lt;inst_name>  --namespace &lt;get inst options> (corresponds to GetInstance)
  * **enumerate** &lt;instname>-- namespace --names-only &lt;enumerate inst options> (corresponds to EnumerateInstances)
  * **references** &lt;instname>--namespace --names_only &lt;references options>(corresponds to inst references)
  * **associators** &lt;instname> --namespace --names_only &lt;associator options>(corresponds to inst associators)
  * **delete** &lt;instname> | &lt;classname>   (use classname for interactive select mode)
  * **method** &lt;instname> &lt;methodname> [&lt;param_name=value>]*
* **qualifier**             # operations on the QualifierDecl type
  * **get** &lt;qualifier_name>  --namespace &lt;get qualifier options> (corresponds to GetQualifier)
  * **enumerate**   --namespace &lt;enumerate qualifier options> (corresponds to EnumerateQualifiers)
* **server**                # operations on the pywbem Server Class       
  * **namespace**
    * **list**
    * **interop**
  * **jobs**                # Operations on a future Jobs Class 
    *  list
    *  TBD
    *  &lt;possible other server objects, etc. adapters>        
  * **profiles**            # Further operations on the pywbem server class
    * **list**
    * ???
  * **subscriptions**       # Operations on the PywbemSubscriptionManager Class
    * **list** --filters --subs --dest
    * **create** &lt;filter|destination|subscription>
    * **delete** &lt;filter|destination|subscription> 
  * **connection**          # changes to the WBEMConnection Class
    * **info**
    * **setnamespace**
    * **setnewconnection**
  * **profile**             # Lots unknown here. This is where we can expand into profiles
    * **profilename**
      * **info**
      * **classes**
      * **attached_instances**

## General Options

The general options/arguments will include;
* arguments to define the connection to a wbem server (uri, defaultnamespace,
credentials, security, output format, verbosity, etc.)

This can parallel the existing parameter set in wbemcli.

ISSUES: This is a lot of overhead for each command.  There are two logical
solutions:

1. Click includes the capability to use environment variables as alternate
   to cmd line input for options.  We should take advantage of that

2. It is probably seriously time to begin to use a config file for at least
   some characteristics so that the user can set defaults, specific options,
   etc.  This will require some thought since the use of config files has
   many variations.


## Required Packages

We are going to base this on the python click package and other contributions
to click so at least click and possibly several of the click contributions will
be required

## User Define Extensions
TODO

## Testing

This needs some sort of mock testing environment, either through pywbem or
direct.
TODO

## Proposal

single tool with git-like subcommand structure:

    pywbemcli [generat-option]* command usb-command [specific-option]*

Examples:

    pywbemcli http://localhost -o mof class get CIM_ManagedElement
    # Returns the mof for CIM_ManagedElement

    pywbem http://localhost instance get CIM_Blah -i
    # Does get instances of CIM_Blah and offers user selection for operation

    pywbem http://localhost class fine TST_
    # finds all classes in environment that begins with TST_ and returns list
    # of class and namespace

The overall directory structure is probably:

**root**

   * **pywbemcli** - Add files that define the click infrastructure
   * **pywbemclient** - interface with the pywbem apis.
   * **tests**
   * **doc**

QUESTION: Should we break up the code into a package that implements the
commands and subcommands and a separate one that implements the action functions
as shown above. Question: Advantages/disadvantages

## TODO Items

### Timing
Timing of cmd execution. Should we have an option to time the execution of
commands

### Command Chaining
Is there a way to achieve command chaining.

TODO Need real example first.

### Aliases
There are at least two possibilities for aliases:

  * subcommand alias (en substitutes for enumerate)
  * general text aliasing where a combination of text elements could be
    aliased (as git does). Thus, the text 'class get' could be aliased to
    getclass or gc.
    
I believe that the current `alias` contrib handles the first but not the second
form of aliasing.

### Manual level documentation
 TODO 

