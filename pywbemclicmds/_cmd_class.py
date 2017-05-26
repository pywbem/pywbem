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
Click Command definition for the class command group which includes
cmds for get, enumerate, list of classes.
"""
from __future__ import absolute_import

import click
from pywbem import Error
from .pywbemclicmd import pywbemcli, CMD_OPTS_TXT
from ._common import display_result, filter_namelist, fix_propertylist
from ._common_options import propertylist_option, names_only_option, \
    sort_option, includeclassorigin_option, namespace_option, add_options

#
#   Common option definitions for class group
#


# TODO This should default to use qualifiers for class commands.
includequalifiers_option = [              # pylint: disable=invalid-name
    click.option('-i', '--includequalifiers', is_flag=True, required=False,
                 help='Include qualifiers in the result.')]

deepinheritance_option = [              # pylint: disable=invalid-name
    click.option('-d', '--deepinheritance', is_flag=True, required=False,
                 help='Return complete subclass hiearchy for this class.')]

# TODO add a case sensitive option and make the sort an option group.


@pywbemcli.group('class', options_metavar=CMD_OPTS_TXT)
def class_group():
    """
    Command group for class operations.
    """
    pass


# Reverse includequalifiers so the default is true
@class_group.command('get', options_metavar=CMD_OPTS_TXT)
@click.argument('CLASSNAME', type=str, metavar='CLASSNAME', required=True,)
@click.option('-l', '--localonly', is_flag=True, required=False,
              help='Show only local properties of the class.')
@add_options(includequalifiers_option)
@add_options(includeclassorigin_option)
@add_options(propertylist_option)
@add_options(namespace_option)
@click.pass_obj
def class_get(context, classname, **options):
    """
    get and display a single class from the WBEM Server
    """
    context.execute_cmd(lambda: cmd_class_get(context, classname, options))


@class_group.command('names', options_metavar=CMD_OPTS_TXT)
@click.argument('CLASSNAME', type=str, metavar='CLASSNAME', required=False,)
@click.option('-d', '--deepinheritance', is_flag=True, required=False,
              help='Return complete subclass hiearchy for this class.')
@add_options(deepinheritance_option)
@add_options(includequalifiers_option)
@add_options(includeclassorigin_option)
@add_options(sort_option)
@add_options(namespace_option)
@click.pass_obj
def class_names(context, classname, **options):
    """
    get and display a list of classnames from the WBEM Server.
    """
    context.execute_cmd(lambda: cmd_class_names(context, classname, options))


@class_group.command('enumerate', options_metavar=CMD_OPTS_TXT)
@click.argument('CLASSNAME', type=str, metavar='CLASSNAME', required=False)
@click.option('-d', '--deepinheritance', is_flag=True, required=False,
              help='Return complete subclass hiearchy for this class.')
@click.option('-l', '--localonly', is_flag=True, required=False,
              help='Show only local properties of the class.')
@add_options(includequalifiers_option)
@add_options(includeclassorigin_option)
@add_options(names_only_option)
@add_options(sort_option)
@add_options(namespace_option)
@click.pass_obj
def class_enumerate(context, classname, **options):
    """
    Enumerate classes from the WBEMServer starting either at the top or from
    the classname argument if provided
    """
    context.execute_cmd(lambda: cmd_class_enumerate(context, classname,
                                                    options))


@class_group.command('references', options_metavar=CMD_OPTS_TXT)
@click.argument('CLASSNAME', type=str, metavar='CLASSNAME', required=True)
@click.option('-r', '--resultclass', type=str, required=False,
              help='Filter by the classname provided.')
@click.option('-o', '--role', type=str, required=False,
              help='Filter by the role name provided.')
@add_options(includequalifiers_option)
@add_options(includeclassorigin_option)
@add_options(propertylist_option)
@add_options(names_only_option)
@add_options(sort_option)
@add_options(namespace_option)
@click.pass_obj
def class_references(context, classname, **options):
    """
    Get the reference classes for the CLASSNAME argument filtered by the
    role and result class options.
    """
    context.execute_cmd(lambda: cmd_class_references(context, classname,
                                                     options))


@class_group.command('associators', options_metavar=CMD_OPTS_TXT)
@click.argument('CLASSNAME', type=str, metavar='CLASSNAME', required=True)
@click.option('-a', '--assocclass', type=str, required=False,
              help='Filter by the associated class name provided.')
@click.option('-r', '--resultclass', type=str, required=False,
              help='Filter by the result class name provided.')
@click.option('-x', '--role', type=str, required=False,
              help='Filter by the role name provided.')
@click.option('-o', '--resultrole', type=str, required=False,
              help='Filter by the role name provided.')
@add_options(includequalifiers_option)
@add_options(includeclassorigin_option)
@add_options(propertylist_option)
@add_options(names_only_option)
@add_options(sort_option)
@add_options(namespace_option)
@click.pass_obj
def class_associators(context, classname, **options):
    """
    Get the associated classes for the CLASSNAME argument filtered by the
    assocclass, resultclass, role and resultrole arguments.
    """
    context.execute_cmd(lambda: cmd_class_associators(context, classname,
                                                      options))


# TODO we can make optional namespace option the limit search
@class_group.command('find', options_metavar=CMD_OPTS_TXT)
@click.argument('CLASSNAME', type=str, metavar='CLASSNAME', required=True)
@add_options(sort_option)
@click.pass_obj
def class_find(context, classname, **options):
    """
    Find all classes that match the CLASSNAME argument in the namespaces of
    the defined WBEMserver. The CLASSNAME argument may be either a
    classname or a regular expression that can be matched to one or more
    classnames.
    """
    context.execute_cmd(lambda: cmd_class_find(context, classname,
                                               options))

#
#  Command functions for each of the subcommands in the class group
#


def cmd_class_get(context, classname, options):
    """
    Execute the command for get class and display the result
    """
    print('context.conn %r\n classname %s, options %s' %
          (context.conn, classname, options))
    try:
        result = context.conn.GetClass(
            classname,
            namespace=options['namespace'],
            LocalOnly=options['localonly'],
            IncludeQualifiers=options['includequalifiers'],
            IncludeClassOrigin=options['includeclassorigin'],
            PropertyList=fix_propertylist(options['propertylist']))
        display_result(result)
    except Error as er:
        raise click.ClickException("%s: %s" % (er.__class__.__name__, er))


def cmd_class_names(context, classname, options):
    """ Execute the EnumerateClassNames operation."""
    try:
        result = context.conn.EnumerateClassNames(
            ClassName=classname,
            namespace=options['namespace'],
            DeepInheritance=options['deepinheritance'])
        if options['sort']:
            result.sort()
        display_result(result)
    except Error as er:
        raise click.ClickException("%s: %s" % (er.__class__.__name__, er))


def cmd_class_enumerate(context, classname, options):
    """
        Enumerate the classes returning a list of classes from the WBEM server.
    """
    print('options %s' % options)
    try:
        if options['names_only']:
            result = context.conn.EnumerateClassNames(
                ClassName=classname,
                namespace=options['namespace'],
                DeepInheritance=options['deepinheritance'])
            if options['sort']:
                result.sort()
        else:
            result = context.conn.EnumerateClasses(
                ClassName=classname,
                namespace=options['namespace'],
                LocalOnly=options['localonly'],
                Deepinheritance=options['deepinheritance'],
                IncludeQualifiers=options['includequalifiers'],
                IncludeClassOrigin=options['includeclassorigin'])
            if options['sort']:
                result.sort(key=lambda x: x.classname)
        display_result(result)
    except Error as er:
        raise click.ClickException("%s: %s" % (er.__class__.__name__, er))


def cmd_class_references(context, classname, options):
    """Execute the references request operation to get references for
       the classname defined
    """
    try:
        if options['names_only']:
            result = context.conn.ReferenceNames(
                classname,
                namespace=options['namespace'],
                ResultClass=options['resultclass'],
                Role=options['role'])
            if options['sort']:
                result.sort()
        else:
            result = context.conn.References(
                classname,
                namespace=options['namespace'],
                ResultClass=options['resultclass'],
                Role=options['role'],
                IncludeQualifiers=options['includequalifiers'],
                IncludeClassOrigin=options['includeclassorigin'],
                PropertyList=options['propertylist'])
            if options['sort']:
                result.sort(key=lambda x: x.classname)
        display_result(result)
    except Error as er:
        raise click.ClickException("%s: %s" % (er.__class__.__name__, er))


def cmd_class_associators(context, classname, options):
    """Execute the references request operation to get references for
       the classname defined
    """
    try:
        if options['names_only']:
            result = context.conn.Associators(
                classname,
                namespace=options['namespace'],
                AssocClass=options['assocclass'],
                Role=options['role'],
                ResultClass=options['resultclass'],
                ResultRole=options['resultrole'])
            if options['sort']:
                result.sort()
        else:
            result = context.conn.Associators(
                classname,
                namespace=options['namespace'],
                AssocClass=options['assocclass'],
                Role=options['role'],
                ResultClass=options['resultclass'],
                ResultRole=options['resultrole'],
                IncludeQualifiers=options['includequalifiers'],
                IncludeClassOrigin=options['includeclassorigin'],
                PropertyList=options['propertylist'])
            if options['sort']:
                result.sort(key=lambda x: x.classname)
        display_result(result)

    except Error as er:
        raise click.ClickException("%s: %s" % (er.__class__.__name__, er))


def cmd_class_find(context, classname, options):
    """
    Execute the command for get class and display the result. The result is
    a list of classes/namespaces
    """
    ns_names = context.wbem_server.namespaces
    if options['sort']:
        ns_names.sort()

    try:
        print('clasname regex %s' % classname)
        names_dict = {}
        for ns in ns_names:
            classnames = context.conn.EnumerateClassNames(
                namespace=options['namespace'],)
            filtered_classnames = filter_namelist(classname, classnames)
            if options['sort']:
                filtered_classnames.sort()
            names_dict[ns] = filtered_classnames

        # special display function to display classnames returned with
        # their namespaces in the form <namespace>:<classname>
        # TODO merge into single for-loop
        for ns_name in names_dict:
            for classname in names_dict[ns_name]:
                print('  %s:%s' % (ns_name, classname))

        # ##display_result(result)
    except Error as er:
        raise click.ClickException("%s: %s" % (er.__class__.__name__, er))
