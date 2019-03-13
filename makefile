# ------------------------------------------------------------------------------
# Makefile for pybem repository of pywbem project
#
# Supported OS platforms for this makefile:
#     Linux (any distro)
#     OS-X
#     Windows with UNIX-like env such as CygWin (with a UNIX-like shell and
#       Python in the UNIX-like env)
#     native Windows (with the native Windows command processor and Python in
#       Windows)
#
# Prerequisites for running this makefile:
#   These commands are used on all supported OS platforms. On native Windows,
#   they may be provided by UNIX-like environments such as CygWin:
#     make (GNU make)
#     python (This Makefile uses the active Python environment, virtual Python
#       environments are supported)
#     pip (in the active Python environment)
#     twine (in the active Python environment)
#   These additional commands are used on Linux, OS-X and on Windows with
#   UNIX-like environments:
#     uname
#     rm, find, xargs, cp
#     The commands listed in pywbem_os_setup.sh
#   These additional commands are used on native Windows:
#     del, copy, rmdir
#     The commands listed in pywbem_os_setup.bat
# ------------------------------------------------------------------------------

# No built-in rules needed:
MAKEFLAGS += --no-builtin-rules
.SUFFIXES:

# Python / Pip commands
ifndef PYTHON_CMD
  PYTHON_CMD := python
endif
ifndef PIP_CMD
  PIP_CMD := pip
endif

# Package level
ifndef PACKAGE_LEVEL
  PACKAGE_LEVEL := latest
endif
ifeq ($(PACKAGE_LEVEL),minimum)
  pip_level_opts := -c minimum-constraints.txt
else
  ifeq ($(PACKAGE_LEVEL),latest)
    pip_level_opts := --upgrade
  else
    $(error Error: Invalid value for PACKAGE_LEVEL variable: $(PACKAGE_LEVEL))
  endif
endif

# Make variables are case sensitive and some native Windows environments have
# ComSpec set instead of COMSPEC.
ifndef COMSPEC
  ifdef ComSpec
    COMSPEC = $(ComSpec)
  endif
endif

# Determine OS platform make runs on.
#
# The PLATFORM variable is set to one of:
# * Windows_native: Windows native environment (the Windows command processor
#   is used as shell and its internal commands are used, such as "del").
# * Windows_UNIX: A UNIX-like envieonment on Windows (the UNIX shell and its
#   internal commands are used, such as "rm").
# * Linux: Some Linux distribution
# * Darwin: OS-X / macOS
#
# This in turn determines the type of shell that is used by make when invoking
# commands, and the set of internal shell commands that is assumed to be
# available (e.g. "del" for the Windows native command processor and "rm" for
# a UNIX-like shell). Note that GNU make always uses the value of the SHELL
# make variable to invoke the shell for its commands, but it does not always
# read that variable from the environment. In fact, the approach GNU make uses
# to set the SHELL make variable is very special, see
# https://www.gnu.org/software/make/manual/html_node/Choosing-the-Shell.html.
# On native Windows this seems to be implemented differently than described:
# SHELL is not set to COMSPEC, so we do that here.
#
# Note: Native Windows and CygWin are hard to distinguish: The native Windows
# envvars are set in CygWin as well. COMSPEC (or ComSpec) is set on both
# platforms. Using "uname" will display CYGWIN_NT-.. on both platforms. If the
# CygWin make is used on native Windows, most of the CygWin behavior is visible
# in context of that make (e.g. a SHELL variable is set, PATH gets converted to
# UNIX syntax, execution of batch files requires execute permission, etc.).
ifeq ($(OS),Windows_NT)
  ifdef PWD
    PLATFORM := Windows_UNIX
  else
    PLATFORM := Windows_native
    ifdef COMSPEC
      SHELL := $(subst \,/,$(COMSPEC))
    else
      SHELL := cmd.exe
    endif
    .SHELLFLAGS := /c
  endif
else
  # Values: Linux, Darwin
  PLATFORM := $(shell uname -s)
endif

ifeq ($(PLATFORM),Windows_native)
  # Note: The substituted backslashes must be doubled.
  # Remove files (blank-separated list of wildcard path specs)
  RM_FUNC = del /f /q $(subst /,\\,$(1))
  # Remove files recursively (single wildcard path spec)
  RM_R_FUNC = del /f /q /s $(subst /,\\,$(1))
  # Remove directories (blank-separated list of wildcard path specs)
  RMDIR_FUNC = rmdir /q /s $(subst /,\\,$(1))
  # Remove directories recursively (single wildcard path spec)
  RMDIR_R_FUNC = rmdir /q /s $(subst /,\\,$(1))
  # Copy a file, preserving the modified date
  CP_FUNC = copy /y $(subst /,\\,$(1)) $(subst /,\\,$(2))
  ENV = set
  WHICH = where
else
  RM_FUNC = rm -f $(1)
  RM_R_FUNC = find . -type f -name '$(1)' -delete
  RMDIR_FUNC = rm -rf $(1)
  RMDIR_R_FUNC = find . -type d -name '$(1)' | xargs -n 1 rm -rf
  CP_FUNC = cp -r $(1) $(2)
  ENV = env | sort
  WHICH = which
endif

# Name of this Python package
package_name := pywbem

mock_package_name := pywbem_mock

# Determine if coverage details report generated
# The variable can be passed in as either an environment variable or
# command line variable. When set, generates a set of reports of the
# pywbem/*.py files showing line by line coverage.
ifdef COVERAGE_REPORT
  coverage_report := --cov-report=annotate --cov-report=html
else
  coverage_report :=
endif

# Directory for coverage html output. Must be in sync with the one in coveragerc.
coverage_html_dir := coverage_html

# Package version (full version, including any pre-release suffixes, e.g. "0.1.0-dev1")#
# Note: Some make actions (such as clobber) cause the package version to change,
# e.g. because the pywbem.egg-info directory or the PKG-INFO file are deleted,
# when a new version tag has been assigned. Therefore, this variable is assigned with
# "=" so that it is evaluated every time it is used.
package_version = $(shell $(PYTHON_CMD) tools/package_version.py $(package_name))

# Python versions
python_version := $(shell $(PYTHON_CMD) tools/python_version.py 3)
python_mn_version := $(shell $(PYTHON_CMD) tools/python_version.py 2)
python_m_version := $(shell $(PYTHON_CMD) tools/python_version.py 1)
pymn := py$(python_mn_version)

# Directory for the generated distribution files
dist_dir := dist

# Distribution archives
# These variables are set with "=" for the same reason as package_version.
bdist_file = $(dist_dir)/$(package_name)-$(package_version)-py2.py3-none-any.whl
sdist_file = $(dist_dir)/$(package_name)-$(package_version).tar.gz

dist_files = $(bdist_file) $(sdist_file)

# Source files in the packages
package_py_files := \
    $(wildcard $(package_name)/*.py) \
    $(wildcard $(package_name)/*/*.py) \

# Lex/Yacc table files, generated from and by mof_compiler.py
moftab_files := $(package_name)/mofparsetab.py $(package_name)/moflextab.py

# Dependents for Lex/Yacc table files
moftab_dependent_files := \
    $(package_name)/mof_compiler.py \

# Directory for generated API documentation
doc_build_dir := build_doc

# Directory where Sphinx conf.py is located
doc_conf_dir := docs

# Paper format for the Sphinx LaTex/PDF builder.
# Valid values: a4, letter
doc_paper_format := a4

# Documentation generator command
doc_cmd := sphinx-build
doc_opts := -v -d $(doc_build_dir)/doctrees -c $(doc_conf_dir) -D latex_elements.papersize=$(doc_paper_format) .

# File names of automatically generated utility help message text output
doc_utility_help_files := \
    $(doc_conf_dir)/wbemcli.help.txt \
    $(doc_conf_dir)/mof_compiler.help.txt \

# Dependents for Sphinx documentation build
doc_dependent_files := \
    $(doc_conf_dir)/conf.py \
    $(wildcard $(doc_conf_dir)/*.rst) \
    $(wildcard $(doc_conf_dir)/client/*.rst) \
    $(wildcard $(doc_conf_dir)/notebooks/*.ipynb) \
    $(package_name)/__init__.py \
    $(package_name)/_listener.py \
    $(package_name)/_logging.py \
    $(package_name)/_recorder.py \
    $(package_name)/_server.py \
    $(package_name)/_statistics.py \
    $(package_name)/_subscription_manager.py \
    $(package_name)/_valuemapping.py \
    $(package_name)/_version.py \
    $(package_name)/_nocasedict.py \
    $(package_name)/cim_constants.py \
    $(package_name)/cim_http.py \
    $(package_name)/cim_obj.py \
    $(package_name)/cim_operations.py \
    $(package_name)/cim_types.py \
    $(package_name)/config.py \
    $(package_name)/exceptions.py \
    $(package_name)/mof_compiler.py \
    $(mock_package_name)/__init__.py \
    $(mock_package_name)/_wbemconnection_mock.py\
    $(mock_package_name)/_dmtf_cim_schema.py\
    wbemcli.py \

# PyLint config file
pylint_rc_file := pylintrc

# Flake8 config file
flake8_rc_file := .flake8

# Python source files to be checked by PyLint and Flake8
py_src_files := \
    setup.py \
    $(filter-out $(moftab_files), $(wildcard $(package_name)/*.py)) \
    $(wildcard tests/*.py) \
    $(wildcard tests/*/*.py) \
    $(wildcard tests/*/*/*.py) \
    $(wildcard tests/*/*/*/*.py) \
    wbemcli \
    wbemcli.py \
    mof_compiler \
    $(wildcard $(mock_package_name)/*.py) \

# Python source files for test (unit test and function test)
test_src_files := \
    $(wildcard tests/unittest/*.py) \
    $(wildcard tests/unittest/*/*.py) \
    $(wildcard tests/functiontest/*.py) \

test_yaml_files := \
    $(wildcard tests/unittest/*.y*ml) \
    $(wildcard tests/unittest/*/*.y*ml) \
    $(wildcard tests/functiontest/*.y*ml) \

ifdef TESTCASES
  pytest_opts := $(TESTOPTS) -k $(TESTCASES)
else
  pytest_opts := $(TESTOPTS)
endif
pytest_end2end_opts := -v --tb=short $(pytest_opts)

ifeq ($(python_m_version),3)
  pytest_warnings := --pythonwarnings=default
  pytest_end2end_warnings_opts := --pythonwarnings=default,ignore::DeprecationWarning,ignore::PendingDeprecationWarning,ignore::ResourceWarning
else
  ifeq ($(python_mn_version),2.6)
    pytest_warnings :=
    pytest_end2end_warnings_opts :=
  else
    pytest_warnings := --pythonwarnings=default
    pytest_end2end_warnings_opts := --pythonwarnings=default,ignore::DeprecationWarning,ignore::PendingDeprecationWarning
  endif
endif

# Files to be put into distribution archive.
# Keep in sync with dist_dependent_files.
# This is used for 'include' statements in MANIFEST.in. The wildcards are used
# as specified, without being expanded.
dist_manifest_in_files := \
    LICENSE.txt \
    README.rst \
    INSTALL.md \
    *.py \
    $(package_name)/*.py \
    $(mock_package_name)/*.py \

# Files that are dependents of the distribution archive.
# Keep in sync with dist_manifest_in_files.
dist_dependent_files := \
    LICENSE.txt \
    README.rst \
    INSTALL.md \
    $(wildcard *.py) \
    $(wildcard $(package_name)/*.py) \
    $(wildcard $(mock_package_name)/*.py) \

.PHONY: help
help:
	@echo "Makefile for $(package_name) package"
	@echo "Platform: $(PLATFORM)"
	@echo "Shell used for commands: $(SHELL)"
	@echo "Shell flags: $(.SHELLFLAGS)"
	@echo "Make version: $(MAKE_VERSION)"
	@echo "Python location: $(shell $(WHICH) python)"
	@echo "Python version: $(python_version)"
	@echo "$(package_name) package version: $(package_version)"
	@echo ""
	@echo "Make targets:"
	@echo "  install    - Install pywbem and its Python installation and runtime prereqs (includes install_os once after clobber)"
	@echo "  develop    - Install Python development prereqs (includes develop_os once after clobber)"
	@echo "  build      - Build the distribution archive files in: $(dist_dir)"
	@echo "  builddoc   - Build documentation in: $(doc_build_dir)"
	@echo "  check      - Run Flake8 on sources"
	@echo "  pylint     - Run PyLint on sources"
	@echo "  test       - Run unit and function tests"
	@echo "  all        - Do all of the above"
	@echo "  end2end    - Run end2end tests"
	@echo "  install_os - Install OS-level installation and runtime prereqs"
	@echo "  develop_os - Install OS-level development prereqs"
	@echo "  upload     - build + upload the distribution archive files to PyPI"
	@echo "  clean      - Remove any temporary files"
	@echo "  clobber    - Remove everything created to ensure clean start - use after setting git tag"
	@echo "  platform   - Display the information about the platform as seen by make"
	@echo "  env        - Display the environment as seen by make"
	@echo ""
	@echo "Environment variables:"
	@echo "  COVERAGE_REPORT - When set, the 'test' target creates a coverage report as"
	@echo "      annotated html files showing lines covered and missed, in the directory:"
	@echo "      $(coverage_html_dir)"
	@echo "      Optional, defaults to no such coverage report."
	@echo "  TESTCASES - When set, 'test' target runs only the specified test cases. The"
	@echo "      value is used for the -k option of pytest (see 'pytest --help')."
	@echo "      Optional, defaults to running all tests."
	@echo "  TESTSERVER - Optional: Nickname of test server or server group in WBEM server"
	@echo "      definition file for end2end tests. Default: 'default'"
	@echo "  TESTOPTS - Optional: Additional options for py.tests (see 'pytest --help')."
	@echo "  TEST_SCHEMA_DOWNLOAD - When set, enables test cases in test_wbemconnection_mock"
	@echo "      to test downloading of DMTF schema from the DMTF web site."
	@echo "      Optional, defaults to disabling these test cases."
	@echo "  PACKAGE_LEVEL - Package level to be used for installing dependent Python"
	@echo "      packages in 'install' and 'develop' targets:"
	@echo "        latest - Latest package versions available on Pypi"
	@echo "        minimum - A minimum version as defined in minimum-constraints.txt"
	@echo "      Optional, defaults to 'latest'."
	@echo "  PYTHON_CMD - Python command to be used. Useful for Python 3 in some envs."
	@echo "      Optional, defaults to 'python'."
	@echo "  PIP_CMD - Pip command to be used. Useful for Python 3 in some envs."
	@echo "      Optional, defaults to 'pip'."

.PHONY: platform
platform:
	@echo "Platform: $(PLATFORM)"
	@echo "Shell used for commands: $(SHELL)"
	@echo "Shell flags: $(.SHELLFLAGS)"
	@echo "Make version: $(MAKE_VERSION)"
	@echo "Python location: $(shell $(WHICH) python)"
	@echo "Python version: $(python_version)"
	@echo "$(package_name) package version: $(package_version)"

.PHONY: env
env:
	@echo "Environment as seen by make:"
	$(ENV)

.PHONY: _check_version
_check_version:
ifeq (,$(package_version))
	$(error Package version could not be determined - requires pbr - run "make install")
endif

pip_upgrade_$(pymn).done: makefile
	-$(call RM_FUNC,$@)
ifeq ($(python_mn_version),2.6)
	$(PIP_CMD) install $(pip_level_opts) pip
else
	$(PYTHON_CMD) -m pip install $(pip_level_opts) pip
endif
	echo "done" >$@

install_basic_$(pymn).done: makefile pip_upgrade_$(pymn).done
	@echo "makefile: Installing/upgrading basic Python packages with PACKAGE_LEVEL=$(PACKAGE_LEVEL)"
	-$(call RM_FUNC,$@)
ifeq ($(python_mn_version),2.6)
	$(PIP_CMD) install importlib
endif
	$(PYTHON_CMD) remove_duplicate_setuptools.py
# Keep the condition for the 'wheel' package consistent with the requirements & constraints files.
# The approach with "python -m pip" is needed for Windows because pip.exe may be locked,
# but it is not supported on Python 2.6 (which is not supported with pywbem on Windows).
ifeq ($(python_mn_version),2.6)
	$(PIP_CMD) install $(pip_level_opts) setuptools 'wheel<0.30.0'
else
	$(PIP_CMD) install $(pip_level_opts) setuptools wheel
endif
	$(PIP_CMD) install $(pip_level_opts) pbr
	echo "done" >$@
	@echo "makefile: Done installing/upgrading basic Python packages"

.PHONY: install_os
install_os: install_os_$(pymn).done
	@echo "makefile: Target $@ done."

install_os_$(pymn).done: makefile pip_upgrade_$(pymn).done pywbem_os_setup.sh pywbem_os_setup.bat
	@echo "makefile: Installing OS-level installation and runtime requirements"
	@echo "Debug: PATH=$(PATH)"
	-$(call RM_FUNC,$@)
ifeq ($(PLATFORM),Windows_native)
	pywbem_os_setup.bat install
else
	./pywbem_os_setup.sh install
endif
	echo "done" >$@
	@echo "makefile: Done installing OS-level installation and runtime requirements"

.PHONY: _show_bitsize
_show_bitsize:
	@echo "makefile: Determining bit size of Python executable"
	$(PYTHON_CMD) tools/python_bitsize.py
	@echo "makefile: Done determining bit size of Python executable"

install_pywbem_$(pymn).done: makefile pip_upgrade_$(pymn).done requirements.txt setup.py setup.cfg
	@echo "makefile: Installing pywbem (editable) and its Python runtime prerequisites (with PACKAGE_LEVEL=$(PACKAGE_LEVEL))"
	-$(call RM_FUNC,$@)
	-$(call RM_FUNC,PKG-INFO)
	-$(call RMDIR_FUNC,build $(package_name).egg-info .eggs)
	$(PIP_CMD) install $(pip_level_opts) -r requirements.txt
	$(PIP_CMD) install $(pip_level_opts) -e .
	$(call CP_FUNC,$(package_name).egg-info/PKG-INFO,.)
	echo "done" >$@
	@echo "makefile: Done installing pywbem and its Python runtime prerequisites"

.PHONY: install
install: install_$(pymn).done
	@echo "makefile: Target $@ done."

install_$(pymn).done: makefile install_os_$(pymn).done install_basic_$(pymn).done install_pywbem_$(pymn).done
	-$(call RM_FUNC,$@)
	$(PYTHON_CMD) -c "import $(package_name)"
	$(PYTHON_CMD) -c "import $(mock_package_name)"
	echo "done" >$@

.PHONY: develop_os
develop_os: develop_os_$(pymn).done
	@echo "makefile: Target $@ done."

develop_os_$(pymn).done: makefile pip_upgrade_$(pymn).done pywbem_os_setup.sh pywbem_os_setup.bat
	@echo "makefile: Installing OS-level development requirements"
	-$(call RM_FUNC,$@)
ifeq ($(PLATFORM),Windows_native)
	pywbem_os_setup.bat develop
else
	./pywbem_os_setup.sh develop
endif
	echo "done" >$@
	@echo "makefile: Done installing OS-level development requirements"

.PHONY: develop
develop: develop_$(pymn).done
	@echo "makefile: Target $@ done."

develop_$(pymn).done: pip_upgrade_$(pymn).done install_$(pymn).done develop_os_$(pymn).done install_basic_$(pymn).done dev-requirements.txt
	@echo "makefile: Installing Python development requirements (with PACKAGE_LEVEL=$(PACKAGE_LEVEL))"
	-$(call RM_FUNC,$@)
	$(PIP_CMD) install $(pip_level_opts) -r dev-requirements.txt
	echo "done" >$@
	@echo "makefile: Done installing Python development requirements"

.PHONY: build
build: $(bdist_file) $(sdist_file)
	@echo "makefile: Target $@ done."

.PHONY: builddoc
builddoc: html
	@echo "makefile: Target $@ done."

.PHONY: check
check: flake8_$(pymn).done safety_$(pymn).done
	@echo "makefile: Target $@ done."

.PHONY: pylint
pylint: pylint_$(pymn).done
	@echo "makefile: Target $@ done."

.PHONY: all
all: install develop build builddoc check pylint test
	@echo "makefile: Target $@ done."

.PHONY: clobber
clobber: clean
	@echo "makefile: Removing everything for a fresh start"
	-$(call RM_FUNC,*.done epydoc.log $(moftab_files) $(dist_files) pywbem/*cover pywbem_mock/*cover wbemcli.log)
	-$(call RMDIR_FUNC,$(doc_build_dir) .tox $(coverage_html_dir))
	@echo "makefile: Done removing everything for a fresh start"
	@echo "makefile: Target $@ done."

# Also remove any build products that are dependent on the Python version
.PHONY: clean
clean:
	@echo "makefile: Removing temporary build products"
	-$(call RM_R_FUNC,*.pyc)
	-$(call RMDIR_R_FUNC,__pycache__)
	-$(call RM_FUNC,MANIFEST parser.out .coverage $(package_name)/parser.out)
	-$(call RMDIR_FUNC,build .cache $(package_name).egg-info .eggs)
	@echo "makefile: Done removing temporary build products"
	@echo "makefile: Target $@ done."

.PHONY: upload
upload: _check_version $(dist_files)
	@echo "makefile: Uploading to PyPI: pywbem $(package_version)"
	twine upload $(dist_files)
	@echo "makefile: Done uploading to PyPI"
	@echo "makefile: Target $@ done."

.PHONY: html
html: develop_$(pymn).done $(doc_build_dir)/html/docs/index.html
	@echo "makefile: Target $@ done."

$(doc_build_dir)/html/docs/index.html: makefile $(doc_utility_help_files) $(doc_dependent_files)
ifeq ($(python_mn_version),2.6)
	@echo "makefile: Warning: Skipping Sphinx doc build for target $@ on Python $(python_version)" >&2
else
	@echo "makefile: Creating the documentation as HTML pages"
	-$(call RM_FUNC,$@)
	$(doc_cmd) -b html $(doc_opts) $(doc_build_dir)/html
	@echo "makefile: Done creating the documentation as HTML pages; top level file: $@"
endif

.PHONY: pdf
pdf: develop_$(pymn).done makefile $(doc_utility_help_files) $(doc_dependent_files)
ifeq ($(python_mn_version),2.6)
	@echo "makefile: Warning: Skipping Sphinx doc build for target $@ on Python $(python_version)" >&2
else
	@echo "makefile: Creating the documentation as PDF file"
	-$(call RM_FUNC,$@)
	$(doc_cmd) -b latex $(doc_opts) $(doc_build_dir)/pdf
	@echo "makefile: Running LaTeX files through pdflatex..."
	$(MAKE) -C $(doc_build_dir)/pdf all-pdf
	@echo "makefile: Done creating the documentation as PDF file in: $(doc_build_dir)/pdf/"
	@echo "makefile: Target $@ done."
endif

.PHONY: man
man: develop_$(pymn).done makefile $(doc_utility_help_files) $(doc_dependent_files)
ifeq ($(python_mn_version),2.6)
	@echo "makefile: Warning: Skipping Sphinx doc build for target $@ on Python $(python_version)" >&2
else
	@echo "makefile: Creating the documentation as man pages"
	-$(call RM_FUNC,$@)
	$(doc_cmd) -b man $(doc_opts) $(doc_build_dir)/man
	@echo "makefile: Done creating the documentation as man pages in: $(doc_build_dir)/man/"
	@echo "makefile: Target $@ done."
endif

.PHONY: docchanges
docchanges: develop_$(pymn).done
ifeq ($(python_mn_version),2.6)
	@echo "makefile: Warning: Skipping Sphinx doc build for target $@ on Python $(python_version)" >&2
else
	@echo "makefile: Creating the doc changes overview file"
	$(doc_cmd) -b changes $(doc_opts) $(doc_build_dir)/changes
	@echo
	@echo "makefile: Done creating the doc changes overview file in: $(doc_build_dir)/changes/"
	@echo "makefile: Target $@ done."
endif

.PHONY: doclinkcheck
doclinkcheck: develop_$(pymn).done
ifeq ($(python_mn_version),2.6)
	@echo "makefile: Warning: Skipping Sphinx doc build for target $@ on Python $(python_version)" >&2
else
	@echo "makefile: Creating the doc link errors file"
	$(doc_cmd) -b linkcheck $(doc_opts) $(doc_build_dir)/linkcheck
	@echo
	@echo "makefile: Done creating the doc link errors file: $(doc_build_dir)/linkcheck/output.txt"
	@echo "makefile: Target $@ done."
endif

.PHONY: doccoverage
doccoverage: develop_$(pymn).done
ifeq ($(python_mn_version),2.6)
	@echo "makefile: Warning: Skipping Sphinx doc build for target $@ on Python $(python_version)" >&2
else
	@echo "makefile: Creating the doc coverage results file"
	$(doc_cmd) -b coverage $(doc_opts) $(doc_build_dir)/coverage
	@echo "makefile: Done creating the doc coverage results file: $(doc_build_dir)/coverage/python.txt"
	@echo "makefile: Target $@ done."
endif

# Note: distutils depends on the right files specified in MANIFEST.in, even when
# they are already specified e.g. in 'package_data' in setup.py.
# We generate the MANIFEST.in file automatically, to have a single point of
# control (this makefile) for what gets into the distribution archive.
MANIFEST.in: makefile $(dist_manifest_in_files)
	@echo "makefile: Creating the manifest input file"
	echo "# file GENERATED by makefile, do NOT edit" >$@
ifeq ($(PLATFORM),Windows_native)
	for %%f in ($(dist_manifest_in_files)) do (echo include %%f >>$@)
else
	echo "$(dist_manifest_in_files)" |xargs -n 1 echo include >>$@
endif
	@echo "makefile: Done creating the manifest input file: $@"

# Distribution archives.
# Note: Deleting MANIFEST causes distutils (setup.py) to read MANIFEST.in and to
# regenerate MANIFEST. Otherwise, changes in MANIFEST.in will not be used.
# Note: Deleting build is a safeguard against picking up partial build products
# which can lead to incorrect hashbangs in the pywbem scripts in wheel archives.
$(bdist_file) $(sdist_file): _check_version setup.py MANIFEST.in $(dist_dependent_files) $(moftab_files)
	@echo "makefile: Creating the distribution archive files"
	-$(call RM_FUNC,MANIFEST PKG-INFO)
	-$(call RMDIR_FUNC,build $(package_name).egg-info-INFO .eggs)
	$(PYTHON_CMD) setup.py sdist -d $(dist_dir) bdist_wheel -d $(dist_dir) --universal
	$(call CP_FUNC,$(package_name).egg-info/PKG-INFO,.)
	@echo "makefile: Done creating the distribution archive files: $(bdist_file) $(sdist_file)"

# Note: The mof*tab files need to be removed in order to rebuild them (make rules vs. ply rules)
$(moftab_files): install_$(pymn).done $(moftab_dependent_files) build_moftab.py
	@echo "makefile: Creating the LEX/YACC table modules"
	-$(call RM_FUNC,$(package_name)/mofparsetab.py* $(package_name)/moflextab.py*)
	$(PYTHON_CMD) -c "from pywbem import mof_compiler; mof_compiler._build(verbose=True)"
	@echo "makefile: Done creating the LEX/YACC table modules: $(moftab_files)"

# TODO: Once pylint has no more errors, remove the dash "-"
# PyLint status codes:
# * 0 if everything went fine
# * 1 if fatal messages issued
# * 2 if error messages issued
# * 4 if warning messages issued
# * 8 if refactor messages issued
# * 16 if convention messages issued
# * 32 on usage error
# Status 1 to 16 will be bit-ORed.
# The make command checks for statuses: 1,2,32
pylint_$(pymn).done: develop_$(pymn).done makefile $(pylint_rc_file) $(py_src_files)
ifeq ($(python_mn_version),2.6)
	@echo "makefile: Warning: Skipping Pylint on Python $(python_version)" >&2
else
	@echo "makefile: Running Pylint"
	-$(call RM_FUNC,$@)
	pylint --version
	-pylint --rcfile=$(pylint_rc_file) $(py_src_files)
	echo "done" >$@
	@echo "makefile: Done running Pylint"
endif

flake8_$(pymn).done: develop_$(pymn).done makefile $(flake8_rc_file) $(py_src_files)
ifeq ($(python_mn_version),2.6)
	@echo "makefile: Warning: Skipping Flake8 on Python $(python_version)" >&2
else
	@echo "makefile: Running Flake8"
	-$(call RM_FUNC,$@)
	flake8 --version
	flake8 --statistics --config=$(flake8_rc_file) --filename='*' $(py_src_files)
	echo "done" >$@
	@echo "makefile: Done running Flake8"
endif

safety_$(pymn).done: develop_$(pymn).done makefile minimum-constraints.txt
	@echo "makefile: Running pyup.io safety check"
	-$(call RM_FUNC,$@)
	-safety check -r minimum-constraints.txt --full-report
	echo "done" >$@
	@echo "makefile: Done running pyup.io safety check"

.PHONY: test
test: develop_$(pymn).done $(moftab_files)
	@echo "makefile: Running unit and function tests"
	py.test --color=yes --cov $(package_name) --cov $(mock_package_name) $(coverage_report) --cov-config coveragerc $(pytest_warnings_opts) $(pytest_opts) tests/unittest tests/functiontest -s
	@echo "makefile: Done running tests"

.PHONY: end2end
end2end: develop_$(pymn).done $(moftab_files)
	@echo "makefile: Running end2end tests"
	py.test --color=yes $(pytest_end2end_warnings_opts) $(pytest_end2end_opts) tests/end2endtest -s
	@echo "makefile: Done running end2end tests"

$(doc_conf_dir)/wbemcli.help.txt: wbemcli wbemcli.py
	@echo "makefile: Creating wbemcli script help message file"
ifeq ($(PLATFORM),Windows_native)
	wbemcli.bat --help >$@
else
	./wbemcli --help >$@
endif
	@echo "makefile: Done creating wbemcli script help message file: $@"

$(doc_conf_dir)/mof_compiler.help.txt: mof_compiler $(package_name)/mof_compiler.py
	@echo "makefile: Creating mof_compiler script help message file"
ifeq ($(PLATFORM),Windows_native)
	mof_compiler.bat --help >$@
else
	./mof_compiler --help >$@
endif
	@echo "makefile: Done creating mof_compiler script help message file: $@"
