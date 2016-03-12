# ------------------------------------------------------------------------------
# Makefile for pywbem
#
# Supported platforms:
#   Windows
#   Linux
#
# Basic prerequisites for running this makefile:
#   bash, sh
#   zip, unzip
#   rm, find, xargs, grep, sed
#   python (Some active Python version, virtualenv is supported)
#   pip (in the active Python environment)
#
# Additional prerequisites for development and for running some parts of this
# makefile will be installed by 'make develop'.
#
# Prerequisites for usage will be installed by 'make install'.
# ------------------------------------------------------------------------------

# Name of this Python package
package_name := pywbem

# Package version as specified in pywbem/__init__.py
package_specified_version := $(shell sh -c "grep -E '^ *__version__ *= ' pywbem/__init__.py |sed -r 's/__version__ *= *\x27(.*)\x27.*/\1/'")

# Normalized package version (as normalized by setup.py during building)
package_version := $(shell sh -c "echo $(package_specified_version) |sed 's/[.-]\?\(rc[0-9]\+\)$$/\1/' |sed 's/[.]\?dev[0-9]\*$$/\.dev0/'")

# Final version of this package (M.N.U)
package_final_version := $(shell sh -c "echo $(package_version) |sed 's/rc[0-9]\+$$//' |sed 's/\.dev0$$//'")

# Python major version
python_major_version := $(shell python -c "import sys; sys.stdout.write('%s'%sys.version_info[0])")

# Python version for use in file names
python_version_fn := $(shell python -c "import sys; sys.stdout.write('%s%s'%(sys.version_info[0],sys.version_info[1]))")

# Directory for the generated distribution files
dist_dir := dist/$(package_name)-$(package_final_version)

# Distribution archive (as built by setup.py)
dist_file := $(dist_dir)/$(package_name)-$(package_version).zip

# Windows installable (as built by setup.py)
win64_dist_file := $(dist_dir)/$(package_name)-$(package_version).win-amd64.exe

# Lex/Yacc table files, generated from and by mof_compiler.py
moftab_files := $(package_name)/mofparsetab.py $(package_name)/moflextab.py

# Dependents for Lex/Yacc table files
moftab_dependent_files := \
    $(package_name)/mof_compiler.py \

# Dependents for API doc builder
# Note: Should not include the modules in doc_exclude_patterns
doc_dependent_files := \
    $(package_name)/__init__.py \
    $(package_name)/cim_obj.py \
    $(package_name)/cim_operations.py \
    $(package_name)/cim_constants.py \
    $(package_name)/cim_types.py \
    $(package_name)/cim_xml.py \
    $(package_name)/cim_http.py \
    $(package_name)/tupletree.py \
    $(package_name)/tupleparse.py \
    $(package_name)/cimxml_parse.py \
    $(package_name)/wbemcli.py \
    $(package_name)/mof_compiler.py \
    $(package_name)/NEWS \

# Dotted module names to be excluded in API doc generation
# Note: Should not include the dependent files in doc_dependent_files
doc_exclude_patterns := \
    $(package_name).moflextab \
    $(package_name).mofparsetab \
    $(package_name).lex \
    $(package_name).yacc \
    $(package_name).cim_provider \
    $(package_name).cim_provider2 \
    $(package_name).twisted_client \

# Directory for generated API documentation
doc_build_dir := build_doc

# Documentation generator command
doc_cmd := epydoc --verbose --simple-term --html --docformat=restructuredtext --no-private --name=PyWBEM --output=$(doc_build_dir) $(foreach p,$(doc_exclude_patterns),--exclude=$p) $(package_name)

# Directory for documentation publishing
doc_publish_dir := ../pywbem.github.io/pywbem/doc/$(package_final_version)/doc

# PyLint config file
pylint_rc_file := pylint.rc

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
    $(package_name)/NEWS \

# Files that are dependents of the distribution archive.
# Keep in sync with dist_manifest_in_files.
dist_dependent_files := \
    $(package_name)/LICENSE.txt \
    README.md \
    INSTALL.md \
    $(wildcard *.py) \
    $(wildcard $(package_name)/*.py) \
    $(package_name)/NEWS \

# No built-in rules needed:
.SUFFIXES:

.PHONY: build buildwin test install develop upload clean clobber all help

help:
	@echo 'makefile for $(package_name)'
	@echo 'Package version will be: $(package_version)'
	@echo 'Uses the currently active Python environment: Python $(python_version_fn)'
	@echo 'Valid targets are (they do just what is stated, i.e. no automatic prereq targets):'
	@echo '  develop    - Prepare the development environment by installing prerequisites'
	@echo '  build      - Build the distribution archive: $(dist_file)'
	@echo '  buildwin   - Build the Windows installable: $(win64_dist_file) (on Win 64-bit)'
	@echo '  builddoc   - Build documentation in: $(doc_build_dir)'
	@echo '  check      - Run PyLint on sources and save results in: pylint.log'
	@echo '  install    - Install distribution archive to active Python environment'
	@echo '  test       - Run unit tests and save results in: $(test_log_file)'
	@echo '  clean      - Remove any temporary files; ensure clean build start'
	@echo '  all        - Do everything locally (except publish/upload)'
	@echo '  upload     - build + Upload the distribution archive to PyPI'
	@echo '  publish    - builddoc + publish documentation to: $(doc_publish_dir)'
	@echo '  clobber    - Remove any build products'

develop:
	pip install six
	python setup.py develop_os
	python setup.py develop
	@echo '$@ done.'

build: $(dist_file)
	@echo '$@ done; created: $(dist_file)'

buildwin: $(win64_dist_file)
	@echo '$@ done; created: $(win64_dist_file)'

ifeq ($(python_major_version), 2)
builddoc: $(doc_build_dir)/index.html
	@echo '$@ done; created documentation in: $(doc_build_dir); build output is in epydoc.log'
else
builddoc:
	@echo 'Building API documentation requires Python 2; skipping this step'
endif

ifeq ($(python_major_version), 2)
check: pylint.log
	@echo '$@ done; results are in pylint.log'
else
check:
	@echo 'Checking requires Python 2; skipping this step'
endif

install:
	unzip -q -o -d tmp_install $(dist_file)
	sh -c "cd tmp_install/$(package_name)-$(package_version) && python setup.py install_os && python setup.py install"
	rm -Rf tmp_install
	@echo '$@ done.'

test: $(test_log_file)
	@echo '$@ done; results are in $(test_log_file)'

clobber: clean
	rm -f pylint.log epydoc.log test_*.log
	rm -Rf $(doc_build_dir) .tox
	@echo '$@ done.'

# Also remove any build products that are dependent on the Python version
clean:
	find . -name "*.pyc" -delete
	sh -c "find . -name \"__pycache__\" |xargs rm -Rf"
	sh -c "ls -d tmp_* |xargs rm -Rf"
	rm -f MANIFEST parser.out .coverage $(package_name)/parser.out $(test_tmp_file) $(package_name)/mofparsetab.py $(package_name)/moflextab.py
	rm -Rf build tmp_install testtmp testsuite/testtmp .cache $(package_name).egg-info
	@echo '$@ done.'

all: clean develop check builddoc test
	@echo '$@ done.'

upload: build
	@sh -c "\
if [[ $(package_version) =~ .*-dev ]]; \
then \
  echo Error: Development versions should not be uploaded to PyPI: $(package_version); \
  false; \
else \
  echo No Development version; \
fi \
"
	python setup.py upload
	@echo '$@ done; uploaded package to PyPI.'

publish: builddoc
	rm -Rf $(doc_publish_dir)
	mkdir -p $(doc_publish_dir)
	cp -rp $(doc_build_dir)/* $(doc_publish_dir)/
	@echo '$@ done; published documentation to: $(doc_publish_dir)'

# Note: distutils depends on the right files specified in MANIFEST.in, even when
# they are already specified e.g. in 'package_data' in setup.py.
# We generate the MANIFEST.in file automatically, to have a single point of
# control (this makefile) for what gets into the distribution archive.
MANIFEST.in: makefile
	echo '# file GENERATED by makefile, do NOT edit' >$@
	echo '$(dist_manifest_in_files)' | xargs -r -n 1 echo include >>$@

# Distribution archives.
# Note: Deleting MANIFEST causes distutils (setup.py) to read MANIFEST.in and to
# regenerate MANIFEST. Otherwise, changes in MANIFEST.in will not be used.
$(dist_file): setup.py MANIFEST.in $(dist_dependent_files) $(moftab_files)
	rm -f MANIFEST
	python setup.py sdist -d $(dist_dir) --formats=zip

$(win64_dist_file): setup.py MANIFEST.in $(dist_dependent_files)
	rm -f MANIFEST
	python setup.py bdist_wininst -d $(dist_dir) -o -t "PyWBEM v$(package_version)"

$(moftab_files): $(moftab_dependent_files)
	rm -f $(package_name)/mofparsetab.py* $(package_name)/moflextab.py*
	sh -c "PYTHONPATH=. python -c \"from $(package_name) import mof_compiler; mof_compiler._build()\""

# Documentation for package (generates more .html files than just this target)
$(doc_build_dir)/index.html: $(doc_dependent_files)
	rm -Rf $(doc_build_dir)
	mkdir -p $(doc_build_dir)
	bash -c "set -o pipefail; PYTHONPATH=. $(doc_cmd) 2>&1 |tee epydoc.log"
	cp -p $(package_name)/NEWS $(doc_build_dir)/NEWS.txt

# TODO: Once pylint has no more errors, remove the dash "-"
pylint.log: $(pylint_rc_file) setup.py os_setup.py $(package_name)/*.py testsuite/*.py
	rm -f pylint.log
	-bash -c "set -o pipefail; PYTHONPATH=. pylint --rcfile=$(pylint_rc_file) --ignore=moflextab.py,mofparsetab.py,yacc.py,lex.py,twisted_client.py,cim_provider.py,cim_provider2.py --output-format=text setup.py os_setup.py $(package_name) testsuite/test*.py testsuite/validate.py 2>&1 |tee pylint.tmp.log"
	mv -f pylint.tmp.log pylint.log

$(test_log_file): $(package_name)/*.py testsuite/*.py coveragerc
	rm -f $(test_log_file)
	bash -c "set -o pipefail; PYTHONPATH=. py.test --cov $(package_name) --cov-config coveragerc --ignore=releases -s 2>&1 |tee $(test_tmp_file)"
	mv -f $(test_tmp_file) $(test_log_file)

