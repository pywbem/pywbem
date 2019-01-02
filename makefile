# ------------------------------------------------------------------------------
# Makefile for pybem repository of pywbem project
#
# Supported OS platforms for this makefile:
#     Linux (any distro)
#     OS-X
#     Windows with UNIX-like env such as CygWin (with Python in UNIX-like env)
#     native Windows (with Python in Windows)
#
# Prerequisites for running this makefile:
#   These commands are used on all supported OS platforms. On native Windows,
#   they may be provided by CygWin:
#     make (GNU make)
#     bash
#     echo, rm, mv, find, xargs, tee, touch, chmod, wget
#     python (This Makefile uses the active Python environment, virtual Python
#        environments are supported)
#     pip (in the active Python environment)
#     twine (in the active Python environment)
#   These additional commands are used on Linux, OS-X and Windows with UNIX env:
#     uname
#   These additional commands are used on native Windows:
#     cmd
# ------------------------------------------------------------------------------

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

# Determine OS platform make runs on.
# Note: Native Windows and CygWin are hard to distinguish: The native Windows
# envvars are set in CygWin as well. Using uname will display CYGWIN_NT-.. on
# both platforms. If the CygWin make is used on native Windows, most of the
# CygWin behavior is then visible in context of that make (e.g. a SHELL envvar
# is set, the PATH envvar gets converted to UNIX syntax, execution of batch
# files requires execute permission, etc.). The check below with
# :/usr/local/bin: being in PATH was found to work even when using the CygWin
# make on native Windows.
ifeq ($(OS),Windows_NT)
  ifeq ($(findstring :/usr/local/bin:,$(PATH)),:/usr/local/bin:)
    PLATFORM := CygWin
  else
    PLATFORM := Windows
  endif
else
  # Values: Linux, Darwin
  PLATFORM := $(shell uname -s)
endif

ifeq ($(PLATFORM),Windows)
  # Using the CygWin find
  FIND := /bin/find
else
  FIND := find
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
package_version = $(shell $(PYTHON_CMD) -c "$$(printf 'try:\n from pbr.version import VersionInfo\nexcept ImportError:\n pass\nelse:\n print(VersionInfo(\042$(package_name)\042).release_string())\n')")

# Python versions
python_version := $(shell $(PYTHON_CMD) -c "import sys; sys.stdout.write('%s.%s.%s'%sys.version_info[0:3])")
python_mn_version := $(shell $(PYTHON_CMD) -c "import sys; sys.stdout.write('%s%s'%sys.version_info[0:2])")
python_m_version := $(shell $(PYTHON_CMD) -c "import sys; sys.stdout.write('%s'%sys.version_info[0:1])")

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
    $(wildcard testsuite/*.py) \
    $(wildcard testsuite/testclient/*.py) \
		$(wildcard testsuite/end2end/*.py) \
    wbemcli \
    wbemcli.py \
    mof_compiler \
    $(wildcard $(mock_package_name)/*.py) \

# Test log
test_log_file := test_$(python_mn_version).log
test_tmp_file := test_$(python_mn_version).tmp.log
test_end2end_log_file := test_end2end_$(python_mn_version).log
test_end2end_tmp_file := test_end2end_$(python_mn_version).tmp.log

ifdef TESTCASES
pytest_opts := $(TESTOPTS) -k $(TESTCASES)
else
pytest_opts := $(TESTOPTS)
endif
pytest_end2end_opts := --tb=short $(pytest_opts)

pytest_warnings := default
ifeq ($(python_m_version),3)
  pytest_end2end_warnings := default,ignore::DeprecationWarning,ignore::ResourceWarning
else
  pytest_end2end_warnings := default,ignore::DeprecationWarning
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

# No built-in rules needed:
.SUFFIXES:

.PHONY: help
help:
	@echo "Makefile for $(package_name) repository of pywbem project"
	@echo "Package version will be: $(package_version)"
	@echo "Uses the currently active Python environment: Python $(python_version)"
	@echo "Platform: $(PLATFORM)"
	@echo ""
	@echo "Make targets:"
	@echo "  install    - Install pywbem and its Python installation and runtime prereqs (includes install_os once after clobber)"
	@echo "  develop    - Install Python development prereqs (includes develop_os once after clobber)"
	@echo "  build      - Build the distribution archive files in: $(dist_dir)"
	@echo "  builddoc   - Build documentation in: $(doc_build_dir)"
	@echo "  check      - Run Flake8 on sources and save results in: flake8.log"
	@echo "  pylint     - Run PyLint on sources and save results in: pylint.log"
	@echo "  test       - Run tests and save results in: $(test_log_file)"
	@echo "  all        - Do all of the above"
	@echo "  end2end    - Run end2end tests and save results in: $(test_end2end_log_file)"
	@echo "  install_os - Install OS-level installation and runtime prereqs"
	@echo "  develop_os - Install OS-level development prereqs"
	@echo "  upload     - build + upload the distribution archive files to PyPI"
	@echo "  clean      - Remove any temporary files"
	@echo "  clobber    - Remove everything created to ensure clean start - use after setting git tag"
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

.PHONY: _check_version
_check_version:
ifeq (,$(package_version))
	@echo 'Error: Package version could not be determined (requires pbr; run "make install")'
	@false
else
	@true
endif

install_basic.done:
	@echo "makefile: Installing/upgrading basic Python packages (pip, etc., with PACKAGE_LEVEL=$(PACKAGE_LEVEL))"
ifeq ($(python_mn_version),26)
	$(PIP_CMD) install importlib
endif
	$(PYTHON_CMD) remove_duplicate_setuptools.py
# Keep the condition for the 'wheel' package consistent with the requirements & constraints files.
# The approach with "python -m pip" is needed for Windows because pip.exe may be locked,
# but it is not supported on Python 2.6 (which is not supported with pywbem on Windows).
ifeq ($(python_mn_version),26)
	$(PIP_CMD) install $(pip_level_opts) pip setuptools 'wheel<0.30.0'
else
	$(PYTHON_CMD) -m pip install $(pip_level_opts) pip setuptools wheel
endif
	$(PIP_CMD) install $(pip_level_opts) pbr
	touch install_basic.done
	@echo "makefile: Done installing/upgrading basic Python packages"

.PHONY: install_os
install_os: install_os.done
	@echo "makefile: Target $@ done."

install_os.done: pywbem_os_setup.sh
	@echo "makefile: Installing OS-level installation and runtime requirements"
	@echo "Debug: PATH=$(PATH)"
ifeq ($(PLATFORM),Windows)
	cmd /d /c pywbem_os_setup.bat install
else
	./pywbem_os_setup.sh install
endif
	touch install_os.done
	@echo "makefile: Done installing OS-level installation and runtime requirements"

.PHONY: _show_bitsize
_show_bitsize:
	@echo "makefile: Determining bit size of Python executable"
	$(PYTHON_CMD) -c "import ctypes; print(ctypes.sizeof(ctypes.c_void_p)*8)"
	$(PYTHON_CMD) -c "import sys; print(64 if sys.maxsize > 2**32 else 32)"
	$(PYTHON_CMD) -c "import platform; print(int(platform.architecture()[0].rstrip('bit')))"
	@echo "makefile: Done determining bit size of Python executable"

install_pywbem.done: requirements.txt setup.py setup.cfg
	@echo "makefile: Installing pywbem (editable) and its Python runtime prerequisites (with PACKAGE_LEVEL=$(PACKAGE_LEVEL))"
	rm -Rf build $(package_name).egg-info .eggs
	rm -f PKG-INFO
	$(PIP_CMD) install $(pip_level_opts) -r requirements.txt
	$(PIP_CMD) install $(pip_level_opts) -e .
	cp -r $(package_name).egg-info/PKG-INFO .
	touch install_pywbem.done
	@echo "makefile: Done installing pywbem and its Python runtime prerequisites"

.PHONY: install
install: install.done
	@echo "makefile: Target $@ done."

install.done: makefile install_os.done install_basic.done install_pywbem.done
	$(PYTHON_CMD) -c "import $(package_name); print('ok, version=%r'%$(package_name).__version__)"
	$(PYTHON_CMD) -c "import $(mock_package_name); print('ok')"
	touch install.done

.PHONY: develop_os
develop_os: develop_os.done
	@echo "makefile: Target $@ done."

develop_os.done: pywbem_os_setup.sh
	@echo "makefile: Installing OS-level development requirements"
ifeq ($(PLATFORM),Windows)
	cmd /d /c pywbem_os_setup.bat develop
else
	./pywbem_os_setup.sh develop
endif
	touch develop_os.done
	@echo "makefile: Done installing OS-level development requirements"

.PHONY: develop
develop: develop.done
	@echo "makefile: Target $@ done."

develop.done: install.done develop_os.done install_basic.done dev-requirements.txt
	@echo "makefile: Installing Python development requirements (with PACKAGE_LEVEL=$(PACKAGE_LEVEL))"
	$(PIP_CMD) install $(pip_level_opts) -r dev-requirements.txt
	touch develop.done
	@echo "makefile: Done installing Python development requirements"

.PHONY: build
build: $(bdist_file) $(sdist_file)
	@echo "makefile: Target $@ done."

.PHONY: builddoc
builddoc: html
	@echo "makefile: Target $@ done."

.PHONY: check
check: flake8.log safety.log
	@echo "makefile: Target $@ done."

.PHONY: pylint
pylint: pylint.log
	@echo "makefile: Target $@ done."

.PHONY: all
all: install develop build builddoc check pylint test
	@echo "makefile: Target $@ done."

.PHONY: clobber
clobber: clean
	@echo "makefile: Removing everything for a fresh start"
	rm -f *.done pylint.log flake8.log epydoc.log test_*.log $(moftab_files) $(dist_files) pywbem/*,cover wbemcli.log
	rm -Rf $(doc_build_dir) .tox $(coverage_html_dir)
	@echo "makefile: Done removing everything for a fresh start"
	@echo "makefile: Target $@ done."

# Also remove any build products that are dependent on the Python version
.PHONY: clean
clean:
	@echo "makefile: Removing temporary build products"
	bash -c "$(FIND) . -name '*.pyc' -delete"
	bash -c "$(FIND) . -name \"__pycache__\" |xargs -n 1 rm -Rf"
	rm -Rf tmp_ tmp_*
	rm -f MANIFEST parser.out .coverage $(package_name)/parser.out $(test_tmp_file)
	rm -Rf build tmp_install testtmp testsuite/testtmp .cache $(package_name).egg-info .eggs
	@echo "makefile: Done removing temporary build products"
	@echo "makefile: Target $@ done."

.PHONY: upload
upload: _check_version $(dist_files)
	@echo "makefile: Uploading to PyPI: pywbem $(package_version)"
	twine upload $(dist_files)
	@echo "makefile: Done uploading to PyPI"
	@echo "makefile: Target $@ done."

.PHONY: html
html: $(doc_build_dir)/html/docs/index.html
	@echo "makefile: Target $@ done."

$(doc_build_dir)/html/docs/index.html: makefile $(doc_utility_help_files) $(doc_dependent_files)
ifeq ($(python_mn_version),26)
	@echo "makefile: Warning: Skipping Sphinx doc build for target $@ on Python $(python_version)" >&2
else
	@echo "makefile: Creating the documentation as HTML pages"
	rm -f $@
	PYTHONPATH=. $(doc_cmd) -b html $(doc_opts) $(doc_build_dir)/html
	@echo "makefile: Done creating the documentation as HTML pages; top level file: $@"
endif

.PHONY: pdf
pdf: makefile $(doc_utility_help_files) $(doc_dependent_files)
ifeq ($(python_mn_version),26)
	@echo "makefile: Warning: Skipping Sphinx doc build for target $@ on Python $(python_version)" >&2
else
	@echo "makefile: Creating the documentation as PDF file"
	rm -f $@
	$(doc_cmd) -b latex $(doc_opts) $(doc_build_dir)/pdf
	@echo "makefile: Running LaTeX files through pdflatex..."
	$(MAKE) -C $(doc_build_dir)/pdf all-pdf
	@echo "makefile: Done creating the documentation as PDF file in: $(doc_build_dir)/pdf/"
	@echo "makefile: Target $@ done."
endif

.PHONY: man
man: makefile $(doc_utility_help_files) $(doc_dependent_files)
ifeq ($(python_mn_version),26)
	@echo "makefile: Warning: Skipping Sphinx doc build for target $@ on Python $(python_version)" >&2
else
	@echo "makefile: Creating the documentation as man pages"
	rm -f $@
	$(doc_cmd) -b man $(doc_opts) $(doc_build_dir)/man
	@echo "makefile: Done creating the documentation as man pages in: $(doc_build_dir)/man/"
	@echo "makefile: Target $@ done."
endif

.PHONY: docchanges
docchanges:
ifeq ($(python_mn_version),26)
	@echo "makefile: Warning: Skipping Sphinx doc build for target $@ on Python $(python_version)" >&2
else
	@echo "makefile: Creating the doc changes overview file"
	$(doc_cmd) -b changes $(doc_opts) $(doc_build_dir)/changes
	@echo
	@echo "makefile: Done creating the doc changes overview file in: $(doc_build_dir)/changes/"
	@echo "makefile: Target $@ done."
endif

.PHONY: doclinkcheck
doclinkcheck:
ifeq ($(python_mn_version),26)
	@echo "makefile: Warning: Skipping Sphinx doc build for target $@ on Python $(python_version)" >&2
else
	@echo "makefile: Creating the doc link errors file"
	$(doc_cmd) -b linkcheck $(doc_opts) $(doc_build_dir)/linkcheck
	@echo
	@echo "makefile: Done creating the doc link errors file: $(doc_build_dir)/linkcheck/output.txt"
	@echo "makefile: Target $@ done."
endif

.PHONY: doccoverage
doccoverage:
ifeq ($(python_mn_version),26)
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
MANIFEST.in: makefile
	@echo "makefile: Creating the manifest input file"
	echo "# file GENERATED by makefile, do NOT edit" >$@
	echo "$(dist_manifest_in_files)" |xargs -n 1 echo include >>$@
	@echo "makefile: Done creating the manifest input file: $@"

# Distribution archives.
# Note: Deleting MANIFEST causes distutils (setup.py) to read MANIFEST.in and to
# regenerate MANIFEST. Otherwise, changes in MANIFEST.in will not be used.
# Note: Deleting build is a safeguard against picking up partial build products
# which can lead to incorrect hashbangs in the pywbem scripts in wheel archives.
$(bdist_file) $(sdist_file): _check_version setup.py MANIFEST.in $(dist_dependent_files) $(moftab_files)
	@echo "makefile: Creating the distribution archive files"
	rm -rf MANIFEST $(package_name).egg-info .eggs build
	rm -f PKG-INFO
	$(PYTHON_CMD) setup.py sdist -d $(dist_dir) bdist_wheel -d $(dist_dir) --universal
	cp -r $(package_name).egg-info/PKG-INFO .
	@echo "makefile: Done creating the distribution archive files: $(bdist_file) $(sdist_file)"

# Note: The mof*tab files need to be removed in order to rebuild them (make rules vs. ply rules)
$(moftab_files): install.done $(moftab_dependent_files) build_moftab.py
	@echo "makefile: Creating the LEX/YACC table modules"
	rm -f $(package_name)/mofparsetab.py* $(package_name)/moflextab.py*
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
pylint.log: makefile $(pylint_rc_file) $(py_src_files)
ifeq ($(python_mn_version),27)
	@echo "makefile: Running Pylint"
	rm -f pylint.log
	pylint --version
	-bash -c 'set -o pipefail; PYTHONPATH=. pylint --rcfile=$(pylint_rc_file) $(py_src_files) 2>&1 |tee pylint.tmp.log; rc=$$?; if (($$rc >= 32 || $$rc & 0x03)); then exit $$rc; fi'
	mv -f pylint.tmp.log pylint.log
	@echo "makefile: Done running Pylint; Log file: $@"
else
	@echo "makefile: Warning: Skipping Pylint on Python $(python_version)" >&2
endif

flake8.log: makefile $(flake8_rc_file) $(py_src_files)
ifeq ($(python_mn_version),26)
	@echo "makefile: Warning: Skipping Flake8 on Python $(python_version)" >&2
else
	@echo "makefile: Running Flake8"
	rm -f flake8.log
	flake8 --version
	bash -c "set -o pipefail; PYTHONPATH=. flake8 --statistics --config=$(flake8_rc_file) --filename="*" $(py_src_files) 2>&1 |tee flake8.tmp.log"
	mv -f flake8.tmp.log flake8.log
	@echo "makefile: Done running Flake8; Log file: $@"
endif

safety.log: makefile minimum-constraints.txt
	@echo "makefile: Running pyup.io safety check"
	rm -f $@
	-bash -c "set -o pipefail; safety check -r minimum-constraints.txt --full-report |tee $@.tmp"
	mv -f $@.tmp $@
	@echo "makefile: Done running pyup.io safety check; Log file: $@"

.PHONY: test
test: makefile $(package_name)/*.py $(mock_package_name)/*.py testsuite/*.py testsuite/test_uprint.* testsuite/testclient/*.py testsuite/testclient/*.yaml coveragerc
	@echo "makefile: Running tests"
	rm -f $(test_log_file)
ifeq ($(PLATFORM),Windows)
	cmd /d /c testsuite\test_uprint.bat
else
	testsuite/test_uprint.sh
endif
	bash -c "set -o pipefail; PYTHONWARNINGS=$(pytest_warnings) py.test --color=yes --cov $(package_name) --cov $(mock_package_name) $(coverage_report) --cov-config coveragerc $(pytest_opts) --ignore=attic --ignore=releases --ignore=testsuite/end2end -s 2>&1 |tee $(test_tmp_file)"
	mv -f $(test_tmp_file) $(test_log_file)
	@echo "makefile: Done running tests; Log file: $(test_log_file)"

.PHONY: end2end
end2end: makefile $(package_name)/*.py $(mock_package_name)/*.py testsuite/end2end/*.py
	@echo "makefile: Running end2end tests"
	rm -f $(test_end2end_log_file)
	bash -c "set -o pipefail; cd testsuite/end2end; PYTHONWARNINGS=$(pytest_end2end_warnings) py.test --color=yes $(pytest_end2end_opts) -s 2>&1 |tee ../../$(test_end2end_tmp_file)"
	mv -f $(test_end2end_tmp_file) $(test_end2end_log_file)
	@echo "makefile: Done running end2end tests; Log file: $(test_end2end_log_file)"

$(doc_conf_dir)/wbemcli.help.txt: wbemcli wbemcli.py
	@echo "makefile: Creating wbemcli script help message file"
ifeq ($(PLATFORM),Windows)
	cmd /d /c wbemcli.bat --help >$@
else
	./wbemcli --help >$@
endif
	@echo "makefile: Done creating wbemcli script help message file: $@"

$(doc_conf_dir)/mof_compiler.help.txt: mof_compiler $(package_name)/mof_compiler.py
	@echo "makefile: Creating mof_compiler script help message file"
ifeq ($(PLATFORM),Windows)
	cmd /d /c mof_compiler.bat --help >$@
else
	./mof_compiler --help >$@
endif
	@echo "makefile: Done creating mof_compiler script help message file: $@"
