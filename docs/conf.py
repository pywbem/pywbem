#
# Configuration file for Sphinx builds, created by
# sphinx-quickstart on Wed Mar  2 11:33:06 2016.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os
import io
import re

# Add the repo main directory to the Python module search path, so that the
# pywbem and pywbem_mock modules can be found without having the pywbem
# package installed.
sys.path.insert(
    0, os.path.normpath(os.path.join(os.path.dirname(__file__), '..')))

# Default CIM namespace for WBEM connection
# Keep in sync with pywbem/_cim_constants.py
DEFAULT_NAMESPACE = 'root/cimv2'


def get_version():
    """
    Return the package version as a string.

    This script is used both for local docs builds and by ReadTheDocs builds.

    For local builds, the Makefile ensures that there is a _version_scm.py
    file with the exact version. The version file must have been generated by
    setuptools-scm.

    For ReadTheDocs builds, the Makefile is not used and because the
    _version_scm.py file is not in the repo (since it would need to be updated
    in each PR) it is not available. In that case, the version is determined
    from the highest tag reachable from the checked out branch (ie. shown by
    'git tag -l --merged').
    """
    version_file = os.path.join('..', 'pywbem', '_version_scm.py')
    # pylint: disable=unspecified-encoding

    if not os.path.exists(version_file):

        print(f"conf.py: Creating version file {version_file}")

        cmd = 'git tag -l --merged'
        cp = subprocess.run(
            cmd, shell=True, check=True, capture_output=True, timeout=30)
        tags = cp.stdout.decode('utf-8').split('\n')

        # Convert the version strings into lists of integers for sorting
        tags2 = []  # list of tags represented as list of int
        for tag in tags:
            if tag != '':  # output ends with an empty line -> empty string
                tag_parts = tag.split('.')
                tag_parts2 = []
                for tag_part in tag_parts:
                    if tag_part.endswith('a0'):
                        tag_parts2.append(int(tag_part[:-2]))
                        tag_parts2.append('a0')
                    else:
                        tag_parts2.append(int(tag_part))
                tags2.append(tag_parts2)
        tags2 = sorted(tags2)

        # Take the highest version and convert back to string
        _version_tuple = tuple(tags2[-1])
        _version = '.'.join(map(str, _version_tuple))

        with open(version_file, 'w') as fp:
            fp.write(
f"""# This file has been generated by docs/conf.py using the highest version tag
# that is reachable from the checked-out branch. This is not the exact version
# generated by setuptools-scm.

__version__ = version = {_version!r}
__version_tuple__ = version_tuple = {_version_tuple!r}
""")

        return _version

    # Get version from existing version file
    print(f"conf.py: Getting version from existing version file {version_file}")
    with open(version_file) as fp:
        version_source = fp.read()
    _globals = {}
    exec(version_source, _globals)  # pylint: disable=exec-used
    try:
        _version = _globals['__version__']
    except KeyError:
        _version = _globals['version']
    return _version


# RST variable substitutions
rst_prolog = f"""

.. |DEFAULT_NAMESPACE| replace:: ``"{DEFAULT_NAMESPACE}"``

"""

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
# sys.path.insert(0, os.path.abspath('..'))

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
needs_sphinx = '1.7'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
    'sphinx.ext.extlinks',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.viewcode',   # disabed, raises anexception
    'sphinx.ext.ifconfig',
    'sphinx_git',            # requires 'sphinx-git' Python package
    # Note: sphinx_rtd_theme is not compatible with sphinxcontrib.fulltoc,
    # but since it already provides a full TOC in the navigation pane, the
    # sphinxcontrib.fulltoc extension is not needed.
    'sphinx_rtd_theme',
    'autodocsumm',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
# source_suffix = ['.rst', '.md']
source_suffix = '.rst'

# The encoding of source files.
source_encoding = 'utf-8'

# The master toctree document.
# Note: This requires running Sphinx from within the 'docs' directory.
# RTD does that automatically, local builds switch there in the Makefile.
master_doc = 'index'

# General information about the project.
project = 'pywbem'
#copyright = u''
author = 'pywbem team'

# The short description of the package.
_short_description = 'Pywbem - a WBEM client written in pure Python'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.

# The short X.Y version.
# Note: We use the full version in both cases (e.g. 'M.N.U' or 'M.N.U.dev0').
version = get_version()

# The full version, including alpha/beta/rc tags.
release = version

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = 'en'

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ["listener_design.rst",
                    "tests", ".tox", ".git", "attic", "dist", "irecv",
                    "tools", "packaging", "build_doc", "pywbem.egg-info",
                    ".eggs"]

# The reST default role (used for this markup: `text`) to use for all
# documents. None means it is rendered in italic, without a link.
default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True


# -- Options for Napoleon extension ---------------------------------------

# Enable support for Google style docstrings. Defaults to True.
napoleon_google_docstring = True

# Enable support for NumPy style docstrings. Defaults to True.
napoleon_numpy_docstring = False

# Include private members (like _membername). False to fall back to Sphinx’s
# default behavior. Defaults to False.
napoleon_include_private_with_doc = False

# Include special members (like __membername__). False to fall back to Sphinx’s
# default behavior. Defaults to True.
napoleon_include_special_with_doc = True

# Use the .. admonition:: directive for the Example and Examples sections,
# instead of the .. rubric:: directive. Defaults to False.
napoleon_use_admonition_for_examples = False

# Use the .. admonition:: directive for Notes sections, instead of the
# .. rubric:: directive. Defaults to False.
napoleon_use_admonition_for_notes = False

# Use the .. admonition:: directive for References sections, instead of the
# .. rubric:: directive. Defaults to False.
napoleon_use_admonition_for_references = False

# Use the :ivar: role for instance variables, instead of the .. attribute::
# directive. Defaults to False.
napoleon_use_ivar = True

# Use a :param: role for each function parameter, instead of a single
# :parameters: role for all the parameters. Defaults to True.
napoleon_use_param = True

# Use the :rtype: role for the return type, instead of inlining it with the
# description. Defaults to True.
napoleon_use_rtype = True


# -- Options for viewcode extension ---------------------------------------

# Follow alias objects that are imported from another module such as functions,
# classes and attributes. As side effects, this option ... ???
# If false, ... ???.
# The default is True.
viewcode_import = True


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.
# See https://www.sphinx-doc.org/en/stable/theming.html for built-in themes.
html_theme = 'sphinx_rtd_theme'

# Theme options are theme-specific and customize the look and feel of a theme
# further.
# See https://www.sphinx-doc.org/en/stable/theming.html for the options
# available for built-in themes.
# For options of the 'sphinx_rtd_theme', see
# https://sphinx-rtd-theme.readthedocs.io/en/latest/configuring.html
html_theme_options = {
    'style_external_links': False,
    'collapse_navigation': False,
}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If not defined, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = 'ld'

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (relative to this directory) to use as a favicon of
# the docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
# html_extra_path = ['_extra']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Language to be used for generating the HTML full-text search index.
# Sphinx supports the following languages:
#   'da', 'de', 'en', 'es', 'fi', 'fr', 'hu', 'it', 'ja'
#   'nl', 'no', 'pt', 'ro', 'ru', 'sv', 'tr'
#html_search_language = 'en'

# A dictionary with options for the search language support, empty by default.
# Now only 'ja' uses this config value
#html_search_options = {'type': 'default'}

# The name of a javascript file (relative to the configuration directory) that
# implements a search results scorer. If empty, the default will be used.
#html_search_scorer = 'scorer.js'

# Output file base name for HTML help builder.
htmlhelp_basename = 'pywbem_doc'

# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',

# Latex figure (float) alignment
#'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (master_doc, 'pywbem.tex', _short_description, author, 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (master_doc, 'pywbem', _short_description, [author], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (master_doc, 'pywbem', _short_description,
     author, 'pywbem', _short_description,
     'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False


# -- Options for autodoc extension ----------------------------------------
# For documentation, see
# https://www.sphinx-doc.org/en/stable/ext/autodoc.html

# Note on the :special-members: option:
# In Sphinx releases azt least up to 1.6.5, this option does not behave
# as documented. Its behavior is that it only has an effect on the presence
# of the __init__ member in the documentation, which is shown when the
# option is specified without arguments or with an an argument list that
# includes __init__. Other special members that exist in the code are
# always shown (regardless of whether the option is omitted, specified without
# arguments, or specified with an argument list that may or may not
# include the special member).

# Selects what content will be inserted into a class description.
# The possible values are:
#   "class" - Only the class’ docstring is inserted. This is the default.
#   "both"  - Both the class’ and the __init__ method’s docstring are
#             concatenated and inserted.
#   "init"  - Only the __init__ method’s docstring is inserted.
# In all cases, the __init__ method is still independently rendered as a
# special method when the :special-members: option of the autoclass
# directive includes __init__ or is specified with no arguments.
# Based upon the behavior of the :special-members: option described above,
# the recommendation is to not specify the :special-members: option
# when this config value is set to "both" or "init".
autoclass_content = "both"

# Selects if automatically documented members are sorted alphabetically
# (value 'alphabetical'), by member type (value 'groupwise') or by source
# order (value 'bysource'). The default is alphabetical.
autodoc_member_order = "alphabetical"

# This value is a list of autodoc directive options (flags) that should be
# automatically applied to all autodoc directives. The supported options
# are:
#   'members', 'undoc-members', 'private-members', 'special-members',
#   'inherited-members' and 'show-inheritance'.
# If you set one of these options in this config value, they behave as if
# they had been specified without arguments on each applicable autodoc
# directive. If needed, an autodoc directive can then unspecify the option
# for the current autodoc directive with a negated form :no-{option}:.
# For example, you would specify an option :no-members: on an autoclass
# directive to unspecify a 'members' option included in this config value.
# Note that the :members: option on automodule is recursive w.r.t. the
# classes or other items in the module, so when you want to have specific
# autoclass directives, make sure that the :nmembers: option is not
# set for automodule.
autodoc_default_flags = []

# Functions imported from C modules cannot be introspected, and therefore the
# signature for such functions cannot be automatically determined. However, it
# is an often-used convention to put the signature into the first line of the
# function’s docstring.
# If this boolean value is set to True (which is the default), autodoc will
# look at the first line of the docstring for functions and methods, and if it
# looks like a signature, use the line as the signature and remove it from the
# docstring content.
autodoc_docstring_signature = True

# This value contains a list of modules to be mocked up. This is useful when
# some external dependencies are not met at build time and break the building
# process.
autodoc_mock_imports = []

# -- Options for autodocsumm extension ------------------------------------
# For documentation, see
# https://autodocsumm.readthedocs.io/en/latest/

# Default options to be applied by autodocsumm to ::autoclass and all
# other ::auto... directives. While it would nicely allow specifying autoclass
# options that have values, autodocsumm applies this setting to all directives,
# and autosummary cannot be turned off by directive, so we don't use it.
autodoc_default_options = {}

# -- Options for intersphinx extension ------------------------------------
# For documentation, see
# https://www.sphinx-doc.org/en/stable/ext/intersphinx.html

# Defines the prefixes for intersphinx links, and the targets they resolve to.
# Example RST source for 'py2' prefix:
#     :func:`py2:platform.dist`
#
# Note: The URLs apparently cannot be the same for two different IDs; otherwise
#       the links for one of them are not being created. A small difference
#       such as adding a trailing backslash is already sufficient to work
#       around the problem.
#
# Note: This mapping does not control how links to datatypes of function
#       parameters are generated.
#
intersphinx_mapping = {
  'py': ('https://docs.python.org/3/', None), # agnostic to Python version
  'py2': ('https://docs.python.org/2', None), # specific to Python 2
  'py3': ('https://docs.python.org/3', None), # specific to Python 3
}

intersphinx_cache_limit = 5

# -- Options for extlinks extension ---------------------------------------
# For documentation, see
# https://www.sphinx-doc.org/en/stable/ext/extlinks.html
#
# Defines aliases for external links that can be used as role names.
#
# This config value must be a dictionary of external sites, mapping unique
# short alias names to a base URL and a prefix:
# * key: alias-name
# * value: tuple of (base-url, prefix)
#
# Example for the config value:
#
#   extlinks = {
#     'issue': ('https://github.com/sphinx-doc/sphinx/issues/%s', 'Issue ')
#   }
#
# The alias-name can be used as a role in links. In the example, alias name
# 'issue' is used in RST as follows:
#   :issue:`123`.
# This then translates into a link:
#   https://github.com/sphinx-doc/sphinx/issues/123
# where the %s in the base-url was replaced with the value between back quotes.
#
# The prefix plays a role only for the link caption:
# * If the prefix is None, the link caption is the full URL.
# * If the prefix is the empty string, the link caption is the partial URL
#   given in the role content ("123" in this case.)
# * If the prefix is a non-empty string, the link caption is the partial URL,
#   prepended by the prefix. In the above example, the link caption would be
#   "Issue 123".
#
# You can also use the usual "explicit title" syntax supported by other roles
# that generate links to set the caption. In this case, the prefix is not
# relevant.
# For example, this RST:
#   :issue:`this issue <123>`
# results in the link caption "this issue".

extlinks = {
  'nbview': ('https://nbviewer.jupyter.org/github/pywbem/pywbem/blob/master/docs/notebooks/%s', '%s'),
  'nbdown': ('https://github.com/pywbem/pywbem/raw/master/docs/notebooks/%s', '%s')
}

# Turn off some nitpick warnings for specific targets.
# Identifies specific sphinx nitpick WARNINGS to be disabled
nitpick_ignore = [
    ("py:obj", r'pywbem.ConnectionError.add_note'),
    ("py:obj", r'pywbem.ConnectionError.with_traceback'),
    ("py:obj", r'pywbem.ConnectionError.conn_id'),
    ("py:obj", r'pywbem.ConnectionError.conn_str'),
    ("py:obj", r'pywbem.AuthError.add_note'),
    ("py:obj", r'pywbem.AuthError.with_traceback'),
    ("py:obj", r'pywbem.AuthError.conn_id'),
    ("py:obj", r'pywbem.AuthError.conn_str'),
    ("py:obj", r'pywbem.HTTPError.add_note'),
    ("py:obj", r'pywbem.HTTPError.with_traceback'),
    ("py:obj", r'pywbem.HTTPError.conn_id'),
    ("py:obj", r'pywbem.HTTPError.conn_str'),
    ("py:obj", r'pywbem.HTTPError.request_data'),
    ("py:obj", r'pywbem.HTTPError.response_data'),
    ("py:obj", r'pywbem.TimeoutError.add_note'),
    ("py:obj", r'pywbem.TimeoutError.with_traceback'),
    ("py:obj", r'pywbem.TimeoutError.conn_id'),
    ("py:obj", r'pywbem.TimeoutError.conn_str'),
    ("py:obj", r'pywbem.ParseError.add_note'),
    ("py:obj", r'pywbem.ParseError.with_traceback'),
    ("py:obj", r'pywbem.ParseError.conn_id'),
    ("py:obj", r'pywbem.ParseError.conn_str'),
    ("py:obj", r'pywbem.ParseError.request_data'),
    ("py:obj", r'pywbem.ParseError.response_data'),
    ("py:obj", r'pywbem.CIMXMLParseError.add_note'),
    ("py:obj", r'pywbem.CIMXMLParseError.with_traceback'),
    ("py:obj", r'pywbem.CIMXMLParseError.conn_id'),
    ("py:obj", r'pywbem.CIMXMLParseError.conn_str'),
    ("py:obj", r'pywbem.CIMXMLParseError.request_data'),
    ("py:obj", r'pywbem.CIMXMLParseError.response_data'),
    ("py:obj", r'pywbem.XMLParseError.add_note'),
    ("py:obj", r'pywbem.XMLParseError.with_traceback'),
    ("py:obj", r'pywbem.XMLParseError.conn_id'),
    ("py:obj", r'pywbem.XMLParseError.conn_str'),
    ("py:obj", r'pywbem.XMLParseError.request_data'),
    ("py:obj", r'pywbem.XMLParseError.response_data'),
    ("py:obj", r'pywbem.HeaderParseError.add_note'),
    ("py:obj", r'pywbem.HeaderParseError.with_traceback'),
    ("py:obj", r'pywbem.HeaderParseError.conn_id'),
    ("py:obj", r'pywbem.HeaderParseError.conn_str'),
    ("py:obj", r'pywbem.HeaderParseError.request_data'),
    ("py:obj", r'pywbem.HeaderParseError.response_data'),
    ("py:obj", r'pywbem.CIMError.add_note'),
    ("py:obj", r'pywbem.CIMError.with_traceback'),
    ("py:obj", r'pywbem.CIMError.conn_id'),
    ("py:obj", r'pywbem.CIMError.conn_str'),
    ("py:obj", r'pywbem.CIMError.request_data'),
    ("py:obj", r'pywbem.ModelError.add_note'),
    ("py:obj", r'pywbem.ModelError.with_traceback'),
    ("py:obj", r'pywbem.ModelError.conn_id'),
    ("py:obj", r'pywbem.ModelError.conn_str'),
    ("py:obj", r'pywbem.Error.add_note'),
    ("py:obj", r'pywbem.Error.with_traceback'),
    ("py:obj", r'pywbem._logging.DEFAULT_LOG_FILENAME'),
    ("py:func", r'nocasedict.KeyableByMixin'),
    ("py:obj", r'pywbem.CIMInstanceName.__ne__'),
    ("py:obj", r'pywbem.CIMInstance.__ne__'),
    ("py:obj", r'pywbem.CIMClassName.__ne__'),
    ("py:obj", r'pywbem.CIMClass.__ne__'),
    ("py:obj", r'pywbem.CIMProperty.__ne__'),
    ("py:obj", r'pywbem.CIMMethod.__ne__'),
    ("py:obj", r'pywbem.CIMParameter.__ne__'),
    ("py:obj", r'pywbem.CIMQualifier.__ne__'),
    ("py:obj", r'pywbem.CIMQualifierDeclaration.__ne__'),
    ("py:obj", r'pywbem.Warning.add_note'),
    ("py:obj", r'pywbem.Warning.with_traceback'),
    ("py:obj", r'pywbem.Warning.conn_id'),
    ("py:obj", r'pywbem.Warning.conn_str'),
    ("py:obj", r'pywbem.ToleratedServerIssueWarning.add_note'),
    ("py:obj", r'pywbem.ToleratedServerIssueWarning.with_traceback'),
    ("py:obj", r'pywbem.ToleratedServerIssueWarning.conn_id'),
    ("py:obj", r'pywbem.ToleratedServerIssueWarning.conn_str'),
    ("py:obj", r'pywbem.MOFCompileError.__cause__'),
    ("py:obj", r'pywbem.MOFCompileError.__context__'),
    ("py:obj", r'pywbem.MOFCompileError.conn_id'),
    ("py:obj", r'pywbem.MOFCompileError.conn_str'),
    ("py:obj", r'pywbem.MOFCompileError.__delattr__'),
    ("py:obj", r'pywbem.MOFCompileError.__getattribute__'),
    ("py:obj", r'pywbem.MOFCompileError.__new__'),
    ("py:obj", r'pywbem.MOFCompileError.__reduce__'),
    ("py:obj", r'pywbem.MOFCompileError.__repr__'),
    ("py:obj", r'pywbem.MOFCompileError.__setattr__'),
    ("py:obj", r'pywbem.MOFCompileError.add_note'),
    ("py:obj", r'pywbem.MOFCompileError.with_traceback'),
    ("py:obj", r'pywbem.MOFParseError.__cause__'),
    ("py:obj", r'pywbem.MOFParseError.__context__'),
    ("py:obj", r'pywbem.MOFParseError.column'),
    ("py:obj", r'pywbem.MOFParseError.conn_id'),
    ("py:obj", r'pywbem.MOFParseError.conn_str'),
    ("py:obj", r'pywbem.MOFParseError.context'),
    ("py:obj", r'pywbem.MOFParseError.file'),
    ("py:obj", r'pywbem.MOFParseError.lineno'),
    ("py:obj", r'pywbem.MOFParseError.msg'),
    ("py:obj", r'pywbem.MOFParseError.__delattr__'),
    ("py:obj", r'pywbem.MOFParseError.__getattribute__'),
    ("py:obj", r'pywbem.MOFParseError.__new__'),
    ("py:obj", r'pywbem.MOFParseError.__reduce__'),
    ("py:obj", r'pywbem.MOFParseError.__repr__'),
    ("py:obj", r'pywbem.MOFParseError.__setattr__'),
    ("py:obj", r'pywbem.MOFParseError.__str__'),
    ("py:obj", r'pywbem.MOFParseError.add_note'),
    ("py:obj", r'pywbem.MOFParseError.get_err_msg'),
    ("py:obj", r'pywbem.MOFParseError.with_traceback'),
    ("py:obj", r'pywbem.MOFDependencyError.__cause__'),
    ("py:obj", r'pywbem.MOFDependencyError.__context__'),
    ("py:obj", r'pywbem.MOFDependencyError.column'),
    ("py:obj", r'pywbem.MOFDependencyError.conn_id'),
    ("py:obj", r'pywbem.MOFDependencyError.conn_str'),
    ("py:obj", r'pywbem.MOFDependencyError.context'),
    ("py:obj", r'pywbem.MOFDependencyError.file'),
    ("py:obj", r'pywbem.MOFDependencyError.lineno'),
    ("py:obj", r'pywbem.MOFDependencyError.msg'),
    ("py:obj", r'pywbem.MOFDependencyError.__delattr__'),
    ("py:obj", r'pywbem.MOFDependencyError.__getattribute__'),
    ("py:obj", r'pywbem.MOFDependencyError.__new__'),
    ("py:obj", r'pywbem.MOFDependencyError.__reduce__'),
    ("py:obj", r'pywbem.MOFDependencyError.__repr__'),
    ("py:obj", r'pywbem.MOFDependencyError.__setattr__'),
    ("py:obj", r'pywbem.MOFDependencyError.__str__'),
    ("py:obj", r'pywbem.MOFDependencyError.add_note'),
    ("py:obj", r'pywbem.MOFDependencyError.get_err_msg'),
    ("py:obj", r'pywbem.MOFDependencyError.with_traceback'),
    ("py:obj", r'pywbem.MOFRepositoryError.__cause__'),
    ("py:obj", r'pywbem.MOFRepositoryError.__context__'),
    ("py:obj", r'pywbem.MOFRepositoryError.column'),
    ("py:obj", r'pywbem.MOFRepositoryError.conn_id'),
    ("py:obj", r'pywbem.MOFRepositoryError.conn_str'),
    ("py:obj", r'pywbem.MOFRepositoryError.context'),
    ("py:obj", r'pywbem.MOFRepositoryError.file'),
    ("py:obj", r'pywbem.MOFRepositoryError.lineno'),
    ("py:obj", r'pywbem.MOFRepositoryError.msg'),
    ("py:obj", r'pywbem.MOFRepositoryError.__delattr__'),
    ("py:obj", r'pywbem.MOFRepositoryError.__getattribute__'),
    ("py:obj", r'pywbem.MOFRepositoryError.__new__'),
    ("py:obj", r'pywbem.MOFRepositoryError.__reduce__'),
    ("py:obj", r'pywbem.MOFRepositoryError.__repr__'),
    ("py:obj", r'pywbem.MOFRepositoryError.__setattr__'),
    ("py:obj", r'pywbem.MOFRepositoryError.__str__'),
    ("py:obj", r'pywbem.MOFRepositoryError.add_note'),
    ("py:obj", r'pywbem.MOFRepositoryError.with_traceback'),
    ("py:obj", r'pywbem.ListenerCertificateError.add_note'),
    ("py:obj", r'pywbem.ListenerCertificateError.with_traceback'),
    ("py:obj", r'pywbem.ListenerPortError.add_note'),
    ("py:obj", r'pywbem.ListenerPortError.with_traceback'),
    ("py:obj", r'pywbem.ListenerPromptError.add_note'),
    ("py:obj", r'pywbem.ListenerPromptError.with_traceback'),
    ("py:obj", r'pywbem.ListenerError.add_note'),
    ("py:obj", r'pywbem.ListenerError.with_traceback'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.AssociatorNames'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.Associators'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.CloseEnumeration'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.CreateClass'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.CreateInstance'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.DeleteClass'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.DeleteInstance'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.DeleteQualifier'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.EnumerateClassNames'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.EnumerateClasses'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.EnumerateInstanceNames'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.EnumerateInstances'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.EnumerateQualifiers'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.ExecQuery'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.ExportIndication'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.GetClass'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.GetInstance'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.GetQualifier'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.InvokeMethod'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.IterAssociatorInstancePaths'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.IterAssociatorInstances'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.IterEnumerateInstancePaths'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.IterEnumerateInstances'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.IterQueryInstances'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.IterReferenceInstancePaths'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.IterReferenceInstances'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.ModifyClass'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.ModifyInstance'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.OpenAssociatorInstancePaths'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.OpenAssociatorInstances'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.OpenEnumerateInstancePaths'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.OpenEnumerateInstances'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.OpenQueryInstances'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.OpenReferenceInstancePaths'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.OpenReferenceInstances'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.PullInstancePaths'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.PullInstances'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.PullInstancesWithPath'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.ReferenceNames'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.References'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.SetQualifier'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.__enter__'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.__exit__'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.add_operation_recorder'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.close'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.is_subclass'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.operation_recorder_reset'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.operation_recorder_stage_pywbem_args'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.operation_recorder_stage_result'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.ca_certs'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.conn_id'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.creds'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.debug'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.default_namespace'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.host'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.last_operation_time'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.last_raw_reply'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.last_raw_request'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.last_reply'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.last_reply_len'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.last_request'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.last_request_len'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.last_server_response_time'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.no_verification'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.operation_recorder_enabled'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.operation_recorders'),
    ("py:class", r'BaseOperationRecorder'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.proxies'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.scheme'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.statistics'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.stats_enabled'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.timeout'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.url'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.use_pull_operations'),
    ("py:obj", r'pywbem_mock.FakedWBEMConnection.x509'),
    ("py:obj", r'pywbem_mock.InstanceWriteProvider.__repr__'),
    ("py:obj", r'pywbem_mock.InstanceWriteProvider.add_namespace'),
    ("py:obj", r'pywbem_mock.InstanceWriteProvider.class_exists'),
    ("py:obj", r'pywbem_mock.InstanceWriteProvider.filter_properties'),
    ("py:obj", r'pywbem_mock.InstanceWriteProvider.find_interop_namespace'),
    ("py:obj", r'pywbem_mock.InstanceWriteProvider.get_class'),
    ("py:obj", r'pywbem_mock.InstanceWriteProvider.is_interop_namespace'),
    ("py:obj", r'pywbem_mock.InstanceWriteProvider.is_subclass'),
    ("py:obj", r'pywbem_mock.InstanceWriteProvider.remove_namespace'),
    ("py:obj", r'pywbem_mock.InstanceWriteProvider.validate_namespace'),
    ("py:obj", r'pywbem_mock.InstanceWriteProvider.cimrepository'),
    ("py:obj", r'pywbem_mock.InstanceWriteProvider.interop_namespace_names'),
    ("py:obj", r'pywbem_mock.InstanceWriteProvider.namespaces'),
    ("py:obj", r'pywbem_mock.MethodProvider.__repr__'),
    ("py:obj", r'pywbem_mock.MethodProvider.add_namespace'),
    ("py:obj", r'pywbem_mock.MethodProvider.class_exists'),
    ("py:obj", r'pywbem_mock.MethodProvider.filter_properties'),
    ("py:obj", r'pywbem_mock.MethodProvider.find_interop_namespace'),
    ("py:obj", r'pywbem_mock.MethodProvider.get_class'),
    ("py:obj", r'pywbem_mock.MethodProvider.is_interop_namespace'),
    ("py:obj", r'pywbem_mock.MethodProvider.is_subclass'),
    ("py:obj", r'pywbem_mock.MethodProvider.remove_namespace'),
    ("py:obj", r'pywbem_mock.MethodProvider.validate_namespace'),
    ("py:obj", r'pywbem_mock.MethodProvider.cimrepository'),
    ("py:obj", r'pywbem_mock.MethodProvider.interop_namespace_names'),
    ("py:obj", r'pywbem_mock.MethodProvider.namespaces'),
    ("py:obj", r'pywbem_mock.CIMNamespaceProvider.add_namespace'),
    ("py:obj", r'pywbem_mock.CIMNamespaceProvider.add_new_instance'),
    ("py:obj", r'pywbem_mock.CIMNamespaceProvider.class_exists'),
    ("py:obj", r'pywbem_mock.CIMNamespaceProvider.create_multi_namespace_instance'),
    ("py:obj", r'pywbem_mock.CIMNamespaceProvider.create_new_instance_path'),
    ("py:obj", r'pywbem_mock.CIMNamespaceProvider.filter_properties'),
    ("py:obj", r'pywbem_mock.CIMNamespaceProvider.find_interop_namespace'),
    ("py:obj", r'pywbem_mock.CIMNamespaceProvider.find_multins_association_ref_namespaces'),
    ("py:obj", r'pywbem_mock.CIMNamespaceProvider.get_class'),
    ("py:obj", r'pywbem_mock.CIMNamespaceProvider.get_required_class'),
    ("py:obj", r'pywbem_mock.CIMNamespaceProvider.is_association'),
    ("py:obj", r'pywbem_mock.CIMNamespaceProvider.is_interop_namespace'),
    ("py:obj", r'pywbem_mock.CIMNamespaceProvider.is_subclass'),
    ("py:obj", r'pywbem_mock.CIMNamespaceProvider.modify_multi_namespace_instance'),
    ("py:obj", r'pywbem_mock.CIMNamespaceProvider.remove_namespace'),
    ("py:obj", r'pywbem_mock.CIMNamespaceProvider.validate_instance_exists'),
    ("py:obj", r'pywbem_mock.CIMNamespaceProvider.validate_namespace'),
    ("py:obj", r'pywbem_mock.CIMNamespaceProvider.validate_reference_property_endpoint_exists'),
    ("py:obj", r'pywbem_mock.CIMNamespaceProvider.cimrepository'),
    ("py:obj", r'pywbem_mock.CIMNamespaceProvider.interop_namespace_names'),
    ("py:obj", r'pywbem_mock.CIMNamespaceProvider.namespaces'),
]
