# ------------------------------------------------------------------------------
# Makefile for pywbem
#
# Supported platforms:
#   Windows
#   Linux
#
# Prerequisites for usage:
#   Python >=2.6.9, >=2.7.6
#   For Python packages, see requirements.txt
#
# Additional prerequisites for development:
#   Commands (On Windows, use CygWin to get these commands):
#     make (GNU make)
#     sh - makes sure commands are executed in a Unix shell when on Windows
#     rm, test, find, unzip, sed, xargs, tee, grep
#     pylint >=1.1.0
#   For Python packages, see build-requirements.txt
# ------------------------------------------------------------------------------

# Name of this Python package
package_name := pywbem

# Version of this Python package; it will have one of these formats:
#   M.N.U-dev  : During development of future M.N.U release
#   M.N.U-rc1  : Release candidate 1 of future M.N.U release
#   M.N.U      : The final M.N.U release
package_version := $(shell sh -c "grep __version__ pywbem/__init__.py | sed -r 's/__version__ *= *\x27(.*)\x27.*/\1/'")

# Package version as built by the setup script (it normalizes some elements)
package_built_version := $(if $(findstring -dev,$(package_version)),$(shell sh -c "echo $(package_version) |sed s/-dev/\.dev0/"),$(if $(findstring -rc,$(package_version)),$(shell sh -c "echo $(package_version) |sed s/-rc/\.rc/"),$(package_version)))

# Final version of this package (M.N.U)
package_final_version := $(shell sh -c "echo $(package_version) | sed s/-.*//")

# Directory for the generated distribution files
dist_dir := ../dist/$(package_name)-$(package_final_version)

# Distribution archive as created by setup script
dist_built_file := $(dist_dir)/$(package_name)-$(package_built_version).zip

# Distribution archive as finally kept in distribution directory
dist_file := $(dist_dir)/$(package_name)-$(package_version).zip

# Windows installable as created by setup script
win64_dist_built_file := $(dist_dir)/$(package_name)-$(package_built_version).win-amd64.exe

# Windows installable as finally kept in distribution directory
win64_dist_file := $(dist_dir)/$(package_name)-$(package_version).win-amd64.exe

# Lex/Yacc table files, generated from and by mof_compiler.py
moftab_files := $(package_name)/mofparsetab.py $(package_name)/moflextab.py

# Directory for generated API documentation
doc_out_dir := $(package_name)/docs

# Generated API documentation files, used as dependents
doc_html_files := \
    $(doc_out_dir)/index.html \

# Documentation generator command
doc_cmd := epydoc --verbose --simple-term --html --docformat=restructuredtext --no-private --name=PyWBEM --output=$(doc_out_dir) $(package_name)

# PyLint config file
pylint_rc_file := pylint.rc

# Files to be put into distribution archive.
# Keep in sync with dist_dependent_files.
# This is used for 'include' statements in MANIFEST.in. The wildcards are used
# as specified, without being expanded.
dist_manifest_in_files := \
    $(package_name)/LICENSE.txt \
    README \
    INSTALL \
    *.py \
    $(package_name)/*.py \
    $(package_name)/NEWS \
    $(doc_out_dir)/* \

# Files that are dependents of the distribution archive.
# Keep in sync with dist_manifest_in_files.
dist_dependent_files := \
    $(package_name)/LICENSE.txt \
    README \
    INSTALL \
    $(wildcard *.py) \
    $(wildcard $(package_name)/*.py) \
    $(package_name)/NEWS \
    $(doc_html_files) \

# No built-in rules needed:
.SUFFIXES:

.PHONY: build buildwin test install develop upload clean clobber all help

help:
	@echo 'makefile for $(package_name)'
	@echo 'Package version will be: $(package_version)'
	@echo 'Valid targets are:'
	@echo '  build    - Build the distribution archive: $(dist_file)'
	@echo '  buildwin - (On 64-bit Windows) Build the Windows installable: $(win64_dist_file)'
	@echo '  check    - Run PyLint on sources'
	@echo '  install  - build + install the distribution archive using "python setup.py install"'
	@echo '  develop  - prepare the development environment by installing prerequisites'
	@echo '  test     - install + run unit tests'
	@echo '  upload   - build + upload the distribution archive to PyPI'
	@echo '  clean    - Remove any temporary files'
	@echo '  clobber  - clean + remove any build products'
	@echo '  all      - build + check + test + install + clean (that is, no upload!)'

build: $(dist_file)
	@echo '$@ done; created: $(dist_file)'

buildwin: $(win64_dist_file)
	@echo '$@ done; created: $(win64_dist_file)'

check: pylint_report.html
	@echo '$@ done; for results see pylint_report.html'

test: install
	-sh -c "cd testsuite; ./runtests.sh 2>&1 |tee runtests.log"
	@echo '$@ done; for results see testsuite/runtests.log'

install: build
	unzip -q -o -d tmp_install $(dist_file)
	sh -c "cd tmp_install/$(package_name)-$(package_built_version) && python setup.py install"
	rm -Rf tmp_install
	@echo '$@ done.'

develop:
	python setup.py develop
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
	@echo '$@ done.'

clobber: clean
	rm -f MANIFEST.in pylint_report.html
	rm -Rf $(package_name).egg-info $(doc_out_dir)
	@echo '$@ done.'

clean:
	rm -f MANIFEST parser.out
	sh -c "find . -name \"*.pyc\" | xargs -r rm"
	rm -Rf build tmp_install testtmp testsuite/testtmp
	@echo '$@ done.'

all: build check test install develop clean
	@echo '$@ done.'

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
	mkdir -p $(dist_dir)
	mv $(dist_built_file) $(dist_file)

$(win64_dist_file): setup.py MANIFEST.in $(dist_dependent_files)
	rm -f MANIFEST
	python setup.py bdist_wininst -d $(dist_dir) -o -t "PyWBEM v$(package_version)" 
	mv $(win64_dist_built_file) $(win64_dist_file)

$(moftab_files): $(package_name)/mof_compiler.py
	rm -f $(package_name)/mofparsetab.py* $(package_name)/moflextab.py*
	python -c "from pywbem import mof_compiler; mof_compiler._build()"

# Documentation for package (generates more .html files than just this target)
$(doc_out_dir)/index.html: $(package_name)/*.py
	sh -c "PYTHONPATH=. $(doc_cmd)"

# PyLint report
pylint_report.html: $(pylint_rc_file) setup.py $(package_name)/*.py testsuite/*.py
	-sh -c "PYTHONPATH=. pylint --rcfile=$(pylint_rc_file) --ignore=moflextab.py,mofparsetab.py --output-format=html setup.py $(package_name) testsuite/*.py >$@"
