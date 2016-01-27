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
#   These commands as well as any Python packages for development, can be
#   installed using the 'develop_os' and 'develop' commands of the setup.py
#   script.
# ------------------------------------------------------------------------------

# Name of this Python package
package_name := pywbem

# Package version as specified in pywbem/__init__.py
package_specified_version := $(shell sh -c "grep __version__ pywbem/__init__.py |sed -r 's/__version__ *= *\x27(.*)\x27.*/\1/'")

# Normalized package version (as normalized by setup.py during building)
package_version := $(shell sh -c "echo $(package_specified_version) |sed 's/[.-]\?\(rc[0-9]\+\)$$/\1/' |sed 's/[.]\?dev[0-9]\*$$/\.dev0/'")

# Final version of this package (M.N.U)
package_final_version := $(shell sh -c "echo $(package_version) |sed 's/rc[0-9]\+$$//' |sed 's/\.dev0$$//'")

# Directory for the generated distribution files
dist_dir := dist/$(package_name)-$(package_final_version)

# Distribution archive (as built by setup.py)
dist_file := $(dist_dir)/$(package_name)-$(package_version).zip

# Windows installable (as built by setup.py)
win64_dist_file := $(dist_dir)/$(package_name)-$(package_version).win-amd64.exe

# Lex/Yacc table files, generated from and by mof_compiler.py
moftab_files := $(package_name)/mofparsetab.py $(package_name)/moflextab.py

# Directory for generated API documentation
doc_build_dir := build_doc

# Documentation generator command
doc_cmd := epydoc --verbose --simple-term --html --docformat=restructuredtext --no-private --name=PyWBEM --output=$(doc_build_dir) $(package_name)

# Directory for documentation publishing
doc_publish_dir := ../pywbem.github.io/pywbem/doc/$(package_final_version)/doc

# PyLint config file
pylint_rc_file := pylint.rc

# Files to be put into distribution archive.
# Keep in sync with dist_dependent_files.
# This is used for 'include' statements in MANIFEST.in. The wildcards are used
# as specified, without being expanded.
dist_manifest_in_files := \
    $(package_name)/LICENSE.txt \
    README.md \
    INSTALL \
    *.py \
    $(package_name)/*.py \
    $(package_name)/NEWS \

# Files that are dependents of the distribution archive.
# Keep in sync with dist_manifest_in_files.
dist_dependent_files := \
    $(package_name)/LICENSE.txt \
    README.md \
    INSTALL \
    $(wildcard *.py) \
    $(wildcard $(package_name)/*.py) \
    $(package_name)/NEWS \

# No built-in rules needed:
.SUFFIXES:

.PHONY: build buildwin test install develop upload clean clobber all help

help:
	@echo 'makefile for $(package_name)'
	@echo 'Package version will be: $(package_version)'
	@echo 'Valid targets are:'
	@echo '  develop    - Prepare the development environment by installing prerequisites'
	@echo '  build      - Build the distribution archive: $(dist_file)'
	@echo '  buildwin   - Build the Windows installable: $(win64_dist_file) (on Win 64-bit)'
	@echo '  builddoc   - Build documentation in: $(doc_build_dir)'
	@echo '  check      - Run PyLint on sources and save results in: pylint.log'
	@echo '  install    - Install distribution archive to active Python environment'
	@echo '  test       - Run unit tests and save results in: test.log'
	@echo '  clean      - Remove any temporary files'
	@echo '  all        - Do everything locally (except publish/upload)'
	@echo '  upload     - Upload the distribution archive to PyPI'
	@echo '  publish    - Publish documentation to: $(doc_publish_dir)'
	@echo '  clobber    - Remove any build products'

develop:
	sudo python setup.py develop_os
	python setup.py develop
	@echo '$@ done.'

build: $(dist_file)
	@echo '$@ done; created: $(dist_file)'

buildwin: $(win64_dist_file)
	@echo '$@ done; created: $(win64_dist_file)'

builddoc: $(doc_build_dir)/index.html
	@echo '$@ done; created documentation in: $(doc_build_dir); build output is in epydoc.log'

check: pylint.log
	@echo '$@ done; results are in pylint.log'

install: build
	unzip -q -o -d tmp_install $(dist_file)
	sh -c "cd tmp_install/$(package_name)-$(package_version) && sudo python setup.py install_os && python setup.py install"
	rm -Rf tmp_install
	@echo '$@ done.'

test: test.log
	@echo '$@ done; results are in test.log'

clobber: clean
	rm -f MANIFEST.in pylint_done
	rm -Rf $(package_name).egg-info $(doc_build_dir)
	@echo '$@ done.'

clean:
	rm -f MANIFEST parser.out
	sh -c "find . -name \"*.pyc\" | xargs -r rm"
	rm -Rf build tmp_install testtmp testsuite/testtmp
	@echo '$@ done.'

all: build check install test builddoc clean
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

$(moftab_files): $(package_name)/mof_compiler.py
	rm -f $(package_name)/mofparsetab.py* $(package_name)/moflextab.py*
	python -c "from pywbem import mof_compiler; mof_compiler._build()"

# Documentation for package (generates more .html files than just this target)
$(doc_build_dir)/index.html: $(package_name)/*.py $(package_name)/NEWS
	rm -Rf $(doc_build_dir)
	mkdir -p $(doc_build_dir)
	sh -c "PYTHONPATH=. $(doc_cmd) >epydoc.log"
	cp -p $(package_name)/NEWS $(doc_build_dir)/NEWS.txt

pylint.log: $(pylint_rc_file) setup.py os_setup.py $(package_name)/*.py testsuite/*.py
	-sh -c "PYTHONPATH=. pylint --rcfile=$(pylint_rc_file) --ignore=moflextab.py,mofparsetab.py,yacc.py,lex.py,twisted_client.py,cim_provider.py,cim_provider2.py --output-format=text setup.py os_setup.py $(package_name) testsuite/test*.py testsuite/validate.py >pylint.log"

#test.log: install testsuite/runtests.sh testsuite/*.py
#	-sh -c "cd testsuite; ./runtests.sh 2>&1 |tee ../test.log"

test.log: develop install testsuite/*.py
	py.test --ignore=releases 2>&1 |tee test.log
