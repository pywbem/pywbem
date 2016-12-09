# ------------------------------------------------------------------------------
# Makefile for pywbem
#
# Supported platforms for this makefile:
#   Linux
#   OS-X
#   Windows (with CygWin)
#
# Basic prerequisites for running this makefile:
#   bash, sh
#   rm, find, xargs, grep, sed, tar
#   python (Some active Python version, virtualenv is supported)
#   pip (in the active Python environment)
#
# Additional prerequisites for development and for running some parts of this
# makefile will be installed by 'make develop'.
#
# Prerequisites for usage will be installed by 'make install'.
# ------------------------------------------------------------------------------

# Determine OS platform make runs on
ifeq ($(OS),Windows_NT)
  PLATFORM := Windows
else
  # Values: Linux, Darwin
  PLATFORM := $(shell uname -s)
endif

# Name of this Python package
package_name := pywbem

# Package version as specified in pywbem/_version.py
package_specified_version := $(shell sh -c "grep -E '^ *__version__ *= ' pywbem/_version.py |sed -r 's/__version__ *= *\x27(.*)\x27.*/\1/'")

# Normalized package version (as normalized by setup.py during building)
package_version := $(shell sh -c "echo $(package_specified_version) |sed 's/[.-]\?\(rc[0-9]\+\)$$/\1/' |sed 's/[.]\?dev[0-9]\*$$/\.dev0/'")

# Final version of this package (M.N.U)
package_final_version := $(shell sh -c "echo $(package_version) |sed 's/rc[0-9]\+$$//' |sed 's/\.dev0$$//'")

# Python major version
python_major_version := $(shell python -c "import sys; sys.stdout.write('%s'%sys.version_info[0])")

# Python version for use in file names
python_version_fn := $(shell python -c "import sys; sys.stdout.write('%s%s'%(sys.version_info[0],sys.version_info[1]))")

# Directory for the generated distribution files
dist_dir := dist

# Distribution archives
bdist_file := $(dist_dir)/$(package_name)-$(package_version)-py2.py3-none-any.whl
sdist_file := $(dist_dir)/$(package_name)-$(package_version).tar.gz

dist_files := $(bdist_file) $(sdist_file)

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
doc_opts := -v -d $(doc_build_dir)/doctrees -c $(doc_conf_dir) -D latex_paper_size=$(doc_paper_format) .

# File names of automatically generated utility help message text output
doc_utility_help_files := \
    $(doc_conf_dir)/wbemcli.help.txt \
    $(doc_conf_dir)/mof_compiler.help.txt \

# Dependents for Sphinx documentation build
doc_dependent_files := \
    $(doc_conf_dir)/conf.py \
    $(wildcard $(doc_conf_dir)/*.rst) \
    $(wildcard $(doc_conf_dir)/notebooks/*.ipynb) \
    $(package_name)/__init__.py \
    $(package_name)/cim_constants.py \
    $(package_name)/cim_obj.py \
    $(package_name)/cim_operations.py \
    $(package_name)/cim_types.py \
    $(package_name)/cim_http.py \
    $(package_name)/mof_compiler.py \
    $(package_name)/exceptions.py \
    $(package_name)/_listener.py \
    $(package_name)/_subscription_manager.py \
    $(package_name)/_recorder.py \
    $(package_name)/_server.py \
    $(package_name)/config.py \

# PyLint config file
pylint_rc_file := pylint.rc

# PyLint source files to check
pylint_py_files := \
    setup.py \
    os_setup.py \
    $(filter-out $(moftab_files), $(wildcard $(package_name)/*.py)) \
    $(wildcard testsuite/test*.py) \
    testsuite/validate.py \

# Test log
test_log_file := test_$(python_version_fn).log
test_tmp_file := test_$(python_version_fn).tmp.log

# Files to be put into distribution archive.
# Keep in sync with dist_dependent_files.
# This is used for 'include' statements in MANIFEST.in. The wildcards are used
# as specified, without being expanded.
dist_manifest_in_files := \
    $(package_name)/LICENSE.txt \
    README.md \
    INSTALL.md \
    *.py \
    $(package_name)/*.py \

# Files that are dependents of the distribution archive.
# Keep in sync with dist_manifest_in_files.
dist_dependent_files := \
    $(package_name)/LICENSE.txt \
    README.md \
    INSTALL.md \
    $(wildcard *.py) \
    $(wildcard $(package_name)/*.py) \

# No built-in rules needed:
.SUFFIXES:

.PHONY: help
help:
	@echo 'makefile for $(package_name)'
	@echo 'Package version will be: $(package_version)'
	@echo 'Uses the currently active Python environment: Python $(python_version_fn)'
	@echo 'Valid targets are (they do just what is stated, i.e. no automatic prereq targets):'
	@echo '  develop    - Prepare the development environment by installing prerequisites'
	@echo '  build      - Build the distribution files in: $(dist_dir)'
	@echo '  builddoc   - Build documentation in: $(doc_build_dir)'
	@echo '  check      - Run PyLint on sources and save results in: pylint.log'
	@echo '  test       - Run unit tests and save results in: $(test_log_file)'
	@echo '  all        - Do all of the above'
	@echo '  install    - Install distribution archive to active Python environment'
	@echo '  upload     - build + upload the distribution files to PyPI'
	@echo '  clean      - Remove any temporary files'
	@echo '  clobber    - Remove everything; ensure clean start like a fresh clone'

.PHONY: develop
develop:
	python setup.py develop_os
	python setup.py develop
	@echo '$@ done.'

.PHONY: build
build: $(bdist_file) $(sdist_file)
	@echo '$@ done.'

.PHONY: builddoc
builddoc: html
	@echo '$@ done.'

.PHONY: html
html: $(doc_build_dir)/html/docs/index.html
	@echo '$@ done.'

$(doc_build_dir)/html/docs/index.html: makefile $(doc_utility_help_files) $(doc_dependent_files)
ifeq ($(python_version_fn),26)
	@echo 'Info: Sphinx requires Python 2.7 or Python 3; skipping this step on Python $(python_version)'
else
	rm -f $@
	PYTHONPATH=. $(doc_cmd) -b html $(doc_opts) $(doc_build_dir)/html
	@echo "Done: Created the HTML pages with top level file: $@"
endif

.PHONY: pdf
pdf: makefile $(doc_utility_help_files) $(doc_dependent_files)
ifeq ($(python_version_fn),26)
	@echo 'Info: Sphinx requires Python 2.7 or Python 3; skipping this step on Python $(python_version)'
else
	rm -f $@
	$(doc_cmd) -b latex $(doc_opts) $(doc_build_dir)/pdf
	@echo "Running LaTeX files through pdflatex..."
	$(MAKE) -C $(doc_build_dir)/pdf all-pdf
	@echo "Done: Created the PDF files in: $(doc_build_dir)/pdf/"
	@echo '$@ done.'
endif

.PHONY: man
man: makefile $(doc_utility_help_files) $(doc_dependent_files)
ifeq ($(python_version_fn),26)
	@echo 'Info: Sphinx requires Python 2.7 or Python 3; skipping this step on Python $(python_version)'
else
	rm -f $@
	$(doc_cmd) -b man $(doc_opts) $(doc_build_dir)/man
	@echo "Done: Created the manual pages in: $(doc_build_dir)/man/"
	@echo '$@ done.'
endif

.PHONY: docchanges
docchanges:
ifeq ($(python_version_fn),26)
	@echo 'Info: Sphinx requires Python 2.7 or Python 3; skipping this step on Python $(python_version)'
else
	$(doc_cmd) -b changes $(doc_opts) $(doc_build_dir)/changes
	@echo
	@echo "Done: Created the doc changes overview file in: $(doc_build_dir)/changes/"
	@echo '$@ done.'
endif

.PHONY: doclinkcheck
doclinkcheck:
ifeq ($(python_version_fn),26)
	@echo 'Info: Sphinx requires Python 2.7 or Python 3; skipping this step on Python $(python_version)'
else
	$(doc_cmd) -b linkcheck $(doc_opts) $(doc_build_dir)/linkcheck
	@echo
	@echo "Done: Look for any errors in the above output or in: $(doc_build_dir)/linkcheck/output.txt"
	@echo '$@ done.'
endif

.PHONY: doccoverage
doccoverage:
ifeq ($(python_version_fn),26)
	@echo 'Info: Sphinx requires Python 2.7 or Python 3; skipping this step on Python $(python_version)'
else
	$(doc_cmd) -b coverage $(doc_opts) $(doc_build_dir)/coverage
	@echo "Done: Created the doc coverage results in: $(doc_build_dir)/coverage/python.txt"
	@echo '$@ done.'
endif

.PHONY: check
check: pylint.log
	@echo '$@ done.'

.PHONY: install
install: $(sdist_file)
	mkdir tmp_install
	tar -x -C tmp_install -f $(sdist_file)
	sh -c "cd tmp_install/$(package_name)-$(package_version) && python setup.py install_os && python setup.py install"
	rm -Rf tmp_install
	@echo 'Done: Installed pywbem into current Python environment.'
	@echo '$@ done.'

.PHONY: test
test: $(test_log_file)
	@echo '$@ done.'

.PHONY: clobber
clobber: clean
	rm -f pylint.log epydoc.log test_*.log $(moftab_files) $(dist_files)
	rm -Rf $(doc_build_dir) .tox
	@echo 'Done: Removed everything to get to a fresh state.'
	@echo '$@ done.'

# Also remove any build products that are dependent on the Python version
.PHONY: clean
clean:
	find . -name "*.pyc" -delete
	sh -c "find . -name \"__pycache__\" |xargs -r rm -Rf"
	sh -c "ls -d tmp_* |xargs -r rm -Rf"
	rm -f MANIFEST parser.out .coverage $(package_name)/parser.out $(test_tmp_file)
	rm -Rf build tmp_install testtmp testsuite/testtmp .cache $(package_name).egg-info .eggs
	@echo 'Done: Cleaned out all temporary files.'
	@echo '$@ done.'

.PHONY: all
all: develop check build builddoc test
	@echo '$@ done.'

.PHONY: upload
upload:  $(dist_files)
	twine upload $(dist_files)
	@echo 'Done: Uploaded pywbem version to PyPI: $(package_version)'
	@echo '$@ done.'

# Note: distutils depends on the right files specified in MANIFEST.in, even when
# they are already specified e.g. in 'package_data' in setup.py.
# We generate the MANIFEST.in file automatically, to have a single point of
# control (this makefile) for what gets into the distribution archive.
MANIFEST.in: makefile
	echo '# file GENERATED by makefile, do NOT edit' >$@
	echo '$(dist_manifest_in_files)' | xargs -r -n 1 echo include >>$@
	@echo 'Done: Created manifest input file: $@'

# Distribution archives.
# Note: Deleting MANIFEST causes distutils (setup.py) to read MANIFEST.in and to
# regenerate MANIFEST. Otherwise, changes in MANIFEST.in will not be used.
$(bdist_file) $(sdist_file): setup.py MANIFEST.in $(dist_dependent_files) $(moftab_files)
	rm -rf MANIFEST $(package_name).egg-info .eggs
	python setup.py sdist -d $(dist_dir) bdist_wheel -d $(dist_dir) --universal
	@echo 'Done: Created distribution files: $@'

# Note: The mof*tab files need to be removed in order to rebuild them (make rules vs. ply rules)
$(moftab_files): $(moftab_dependent_files) build_moftab.py
	rm -f $(package_name)/mofparsetab.py* $(package_name)/moflextab.py*
	python -c "from pywbem import mof_compiler; mof_compiler._build(verbose=True)"
	@echo 'Done: Created LEX/YACC table modules: $@'

# TODO: Once pylint has no more errors, remove the dash "-"
pylint.log: makefile $(pylint_rc_file) $(pylint_py_files)
ifeq ($(python_major_version), 2)
	rm -f pylint.log
	-bash -c "set -o pipefail; PYTHONPATH=. pylint --rcfile=$(pylint_rc_file) --output-format=text $(pylint_py_files) 2>&1 |tee pylint.tmp.log"
	mv -f pylint.tmp.log pylint.log
	@echo 'Done: Created Pylint log file: $@'
else
	@echo 'Info: Pylint requires Python 2; skipping this step on Python $(python_major_version)'
endif

$(test_log_file): makefile $(package_name)/*.py testsuite/*.py coveragerc
	rm -f $(test_log_file)
	bash -c "set -o pipefail; PYTHONWARNINGS=default PYTHONPATH=. py.test --cov $(package_name) --cov-config coveragerc --ignore=attic --ignore=releases --ignore=testsuite/testclient -s 2>&1 |tee $(test_tmp_file)"
	mv -f $(test_tmp_file) $(test_log_file)
	@echo 'Done: Created test log file: $@'

$(doc_conf_dir)/wbemcli.help.txt: wbemcli
	./wbemcli --help >$@
	@echo 'Done: Created wbemcli script help message file: $@'

$(doc_conf_dir)/mof_compiler.help.txt: mof_compiler $(package_name)/mof_compiler.py
	./mof_compiler --help >$@
	@echo 'Done: Created mof_compiler script help message file: $@'

