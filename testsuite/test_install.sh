#!/bin/bash

# Test the pywbem installation
# This script must be run from the directory where it is located.

DEBUG="false"
VERBOSE="true"

MYNAME=$(basename "$0")
MYDIR=$(dirname "$0")

function abspath()
{
    # generate absolute path from relative path
    # $1     : relative filename
    # return : absolute path
    if [ -d "$1" ]; then
        # dir
        (cd "$1"; pwd)
    elif [ -f "$1" ]; then
        # file
        if [[ $1 == */* ]]; then
            echo "$(cd "${1%/*}"; pwd)/${1##*/}"
        else
            echo "$(pwd)/$1"
        fi
    else
        error "Path does not exist: $1"
        exit 1
    fi
}

if [[ $(pwd) != $(abspath $MYDIR) ]]; then
  echo "Switching to the directory where this script is located: $MYDIR"
  cd $MYDIR
fi

PYTHON="python2.7"   # Python command / version to be used

ROOTDIR=".."         # relative path from here to repo root dir

# Versions for ply package and generated table modules
NEWPLY_VERSION="3.9"     # new = latest version released - keep up to date!
NEWPLY_TABVERSION="3.8"  # ply 3.9 produces the 3.8 table format
OLDPLY_VERSION="3.6"
OLDPLY_TABVERSION="3.5"  # ply 3.6 produces the 3.5 table format

# pywbem package versions
PYWBEM_VERSIONFILE="$ROOTDIR/pywbem/_version.py"
PYWBEM_SPECIFIED=$(grep -E '^ *__version__ *= ' $PYWBEM_VERSIONFILE |sed -r 's/__version__ *= *\x27(.*)\x27.*/\1/')
#echo "Debug: PYWBEM_SPECIFIED=$PYWBEM_SPECIFIED"
PYWBEM_FULL=$(echo "$PYWBEM_SPECIFIED" |sed 's/[.-]\?\(rc[0-9]\+\)$/\1/' |sed 's/[.]\?dev[0-9]\*$/\.dev0/')
#echo "Debug: PYWBEM_FULL=$PYWBEM_FULL"
PYWBEM_MNU=$(echo "$PYWBEM_FULL" |sed 's/rc[0-9]\+$//' |sed 's/\.dev0$//')
#echo "Debug: PYWBEM_MNU=$PYWBEM_MNU"
PYWBEM_MN=$(echo "$PYWBEM_MNU" |sed 's/\([0-9]\+\.[0-9]\+\).\+$/\1/')
#echo "Debug: PYWBEM_MN=$PYWBEM_MN"

# distribution archives built by make
SRC_DISTFILE="$ROOTDIR/dist/pywbem-${PYWBEM_FULL}.tar.gz"
WHL_DISTFILE="$ROOTDIR/dist/pywbem-${PYWBEM_FULL}-py2.py3-none-any.whl"

# Target directories for the dist. archives for testing 
TMP_DISTROOT="tmp_dist"
TMP_DISTDIR_OLDPLY="${TMP_DISTROOT}/ply-${OLDPLY_VERSION}"
TMP_DISTDIR_NEWPLY="${TMP_DISTROOT}/ply-${NEWPLY_VERSION}"

# distribution archives in temp directories:
SRC_DISTFILE_OLDPLY="$TMP_DISTDIR_OLDPLY/pywbem-${PYWBEM_FULL}.tar.gz"
SRC_DISTFILE_NEWPLY="$TMP_DISTDIR_NEWPLY/pywbem-${PYWBEM_FULL}.tar.gz"
WHL_DISTFILE_OLDPLY="$TMP_DISTDIR_OLDPLY/pywbem-${PYWBEM_FULL}-py2.py3-none-any.whl"
WHL_DISTFILE_NEWPLY="$TMP_DISTDIR_NEWPLY/pywbem-${PYWBEM_FULL}-py2.py3-none-any.whl"

BUILDDIR="$ROOTDIR"

ENVPREFIX="test_"  # prefix for Python virtual environment names

yellow='\e[0;33m'
green='\e[0;32m'
red='\e[0;31m'
magenta='\e[0;35m'
endcolor='\e[0m'

function verbose()
{
  local msg
  msg="$1"
  if [[ "$VERBOSE" == "true" ]]; then
    echo "${msg}"
  fi
}

function info()
{
  local msg
  msg="$1"
  echo -e "${green}${msg}${endcolor}"
}

function warning()
{
  local msg
  msg="$1"
  echo -e "${yellow}Warning: ${msg}${endcolor}"
}

function error()
{
  local msg
  msg="$1"
  echo -e "${red}Error: ${msg}${endcolor}"
}

function failure()
{
  # testcase failure (in contrast to runtime error)
  local msg
  msg="$1"
  echo -e "${magenta}Failure: ${msg}${endcolor}"
}

function setup_virtualenv()
{
  local wrapper_fn wrapper_pn

  wrapper_fn="virtualenvwrapper.sh"
  wrapper_pn=$(which $wrapper_fn)
  if [[ -z $wrapper_pn ]]; then
    wrapper_pn=$(find /usr -name "$wrapper_fn")
  fi
  if [[ -z $wrapper_pn ]]; then
    error "Cannot find virtualenvwrapper.sh script."
    exit 1
  fi
  verbose "Setting up for Python virtualenvwrapper"
  source $wrapper_pn
  if [[ -z $WORKON_HOME ]]; then
    error "WORKON_HOME env.var is not set"
    exit 1
  fi
}

function make_virtualenv()
{
  local envname envnamep envdir
  envname="$1"
  envnamep="${ENVPREFIX}$envname"
  envdir=$WORKON_HOME/$envnamep
  if [[ -d $envdir ]]; then
    remove_virtualenv $envname
  fi
  verbose "Creating $PYTHON virtual environment: $envnamep"
  run "mkvirtualenv -p $(which $PYTHON) $envnamep"
  run "pip install --upgrade pip"
}

function remove_virtualenv()
{
  local envname envnamep envdir
  envname="$1"
  envnamep="${ENVPREFIX}$envname"
  verbose "Removing $PYTHON virtual environment: $envnamep"
  envdir=$WORKON_HOME/$envnamep
  if [[ ! -d $envdir ]]; then
    error "Virtual environment directory does not exist: $envdir"
    exit 1
  fi
  rm -rf $envdir
}

function build_dist()
{
  local tgt_dir
  tgt_dir="$1"  # directory to move dist archives to
  call "cd $BUILDDIR; make clobber build" "Building freshly the dist. archives: $SRC_DISTFILE $WHL_DISTFILE"
  if [[ ! -f $SRC_DISTFILE ]]; then
    error "make build did not produce source dist. archive: $SRC_DISTFILE"
    exit 1
  fi 
  if [[ ! -f $WHL_DISTFILE ]]; then
    error "make build did not produce wheel dist. archive: $WHL_DISTFILE"
    exit 1
  fi 
  if [[ ! -d $tgt_dir ]]; then
    run "mkdir -p $tgt_dir" "Creating temp. dist. archive dir: $tgt_dir"
  fi
  run "mv -f $SRC_DISTFILE $tgt_dir" "Moving built source dist. archive to: $tgt_dir"
  run "mv -f $WHL_DISTFILE $tgt_dir" "Moving built wheel dist. archive to: $tgt_dir"
}

function assert_eq()
{
  local v1 v2
  v1="$1"
  v2="$2"
  msg="$3"
  if [[ "$v1" != "$v2" ]]; then
    if [[ -n $msg ]]; then
      failure "$msg: actual: $v1 / expected: $v2"
    else
      failure "Unexpected value: actual: $v1 / expected: $v2"
    fi
    exit 1
  fi  
}

function run()
{
  local cmd msg rc
  cmd="$1"
  msg="$2"
  if [[ -n $msg ]]; then
    verbose "$msg"
  fi
  if [[ "$DEBUG" == "true" ]]; then
    echo "Debug: running in this shell: $cmd"
    eval "$cmd"
    rc=$?
  else
    eval "$cmd" >cmd.log 2>&1
    rc=$?
  fi
  if [[ $rc != 0 ]]; then
    error "Command failed with rc=$rc: $cmd, output follows:"
    cat cmd.log
    exit 1
  fi
  rm -f cmd.log
}

function call()
{
  local cmd msg rc
  cmd="$1"
  msg="$2"
  if [[ -n $msg ]]; then
    verbose "$msg"
  fi
  if [[ "$DEBUG" == "true" ]]; then
    echo "Debug: running in sub-shell: $cmd"
    sh -c "$cmd"
    rc=$?
  else
    sh -c "$cmd" >cmd.log 2>&1
    rc=$?
  fi
  if [[ $rc != 0 ]]; then
    error "Command failed with rc=$rc: $cmd, output follows:"
    cat cmd.log
    exit 1
  fi
  rm -f cmd.log
}

function assert_run_ok()
{
  local cmd msg rc
  cmd="$1"
  msg="$2"
  if [[ "$DEBUG" == "true" ]]; then
    echo "Debug: running in this shell: $cmd"
    eval "$cmd"
    rc=$?
  else
    eval "$cmd" >cmd.log 2>&1
    rc=$?
  fi
  if [[ $rc != 0 ]]; then
    if [[ -n $msg ]]; then
      failure "$msg"
    else
      failure "Command failed with rc=$rc: $cmd, output follows:"
      cat cmd.log
    fi
    exit 1
  fi  
  rm -f cmd.log
}

function assert_run_fails()
{
  local cmd msg rc
  cmd="$1"
  msg="$2"
  if [[ "$DEBUG" == "true" ]]; then
    echo "Debug: running in this shell: $cmd"
    eval "$cmd"
    rc=$?
  else
    eval "$cmd" >cmd.log 2>&1
    rc=$?
  fi
  if [[ $rc == 0 ]]; then
    if [[ -n $msg ]]; then
      failure "$msg"
    else
      failure "Command succeeded: $cmd, output follows:<F2>"
      cat cmd.log
    fi
    exit 1
  fi  
  rm -f cmd.log
}

function ensure_uninstalled()
{
  local pkg
  pkg="$1"
  cmd="pip uninstall -y -q $pkg"
  if [[ "$DEBUG" == "true" ]]; then
    echo "Debug: running: $cmd"
  fi
  eval $cmd >/dev/null 2>/dev/null
}

function assert_import_ok()
{
  local module
  module="$1"
  if [[ "$DEBUG" == "true" ]]; then
    echo "Debug: module=$module"
    details=""
    #details="; sys.path=$(python -c 'import sys; print(sys.path)')"
  else
    details=""
  fi
  assert_run_ok "python -c \"import ${module}\"" "Python module '${module}' cannot be imported$details"
}

function assert_import_fails()
{
  local module
  module="$1"
  assert_run_fails "python -c \"import ${module}\"" "Python module '${module}' can be imported but should fail"
}

function get_ply_version()
{
  vers=$(pip show ply 2>/dev/null |grep "^Version:" |cut -d ' ' -f 2)
  rc=$?
  if [[ $rc != 0 ]]; then
    error "Cannot determine ply package version, rc=$rc"
    exit 1
  fi  
  echo $vers
}

function get_ply_tabversion()
{
  vers=$(python -c "from pywbem import mofparsetab; print(mofparsetab._tabversion)")
  rc=$?
  if [[ $rc != 0 ]]; then
    error "Cannot determine generated table version of mofparsetab.py: python returns rc=$rc"
    exit 1
  fi  
  echo $vers
}

function build_moftab()
{
  python -c "from pywbem import mof_compiler; mof_compiler._build()"
}

function assert_no_moftab_build()
{
  out=$(build_moftab)
  if [[ -n $out ]]; then
    failure "LEX/YACC table modules were unexpectedly generated. Output log:"
    echo $out
    exit 1
  fi
}
 
function assert_moftab_build()
{
  out=$(build_moftab)
  if [[ -z $out ]]; then
    failure "LEX/YACC table modules were unexpectedly not generated."
    exit 1
  fi
}
 
function ensure_fresh()
{
  verbose "Ensuring the relevant Python packages are uninstalled."
  ensure_uninstalled "six"
  ensure_uninstalled "ply"
  ensure_uninstalled "M2Crypto"
  ensure_uninstalled "pywbem"
}

#-------------------------------------------------

function prep()
{
  info "Preparing: Setup + build dist. archives."
  setup_virtualenv
  make_virtualenv "build"
  call "cd $BUILDDIR; python setup.py develop_os" "Establishing os-level package prerequisites"
  run "pip install ply==$OLDPLY_VERSION" "Installing old version of ply: $OLDPLY_VERSION"
  call "cd $BUILDDIR; python setup.py develop" "Establishing Python package prerequisites"
  build_dist "$TMP_DISTDIR_OLDPLY"
  run "pip install --upgrade ply==$NEWPLY_VERSION" "Upgrading ply to new version: $NEWPLY_VERSION"
  build_dist "$TMP_DISTDIR_NEWPLY"
  remove_virtualenv "build"
}

function cleanup()
{
  info "Cleaning up."
  rm -rf $TMP_DISTROOT
  rm -f cmd.log $ROOTDIR/dist/pywbem-${PYWBEM_FULL}-py2.7.egg
  # run "git checkout -- $SRC_DISTFILE $WHL_DISTFILE"
}

function test1s()
{
  info "Testcase test1s: Normal pip installation of source dist. archive"
  make_virtualenv "test1s"
  ensure_fresh

  run "pip install ${SRC_DISTFILE_NEWPLY}" "Installing with pip from source dist. archive: ${SRC_DISTFILE_NEWPLY}"

  assert_import_ok "six"
  assert_import_ok "ply"
  assert_import_ok "M2Crypto"
  assert_import_ok "pywbem"
  assert_eq "$(get_ply_version)" "$NEWPLY_VERSION" "Unexpected 'ply' package version"
  assert_eq "$(get_ply_tabversion)" "$NEWPLY_TABVERSION" "Unexpected ply table version in generated LEX/YACC table modules" 
  assert_no_moftab_build

  remove_virtualenv "test1s"
}

function test1w()
{
  info "Testcase test1w: Normal pip installation of wheel dist. archive"
  make_virtualenv "test1w"
  ensure_fresh

  run "pip install ${WHL_DISTFILE_NEWPLY}" "Installing with pip from wheel dist. archive: ${WHL_DISTFILE_NEWPLY}"

  assert_import_ok "six"
  assert_import_ok "ply"
  assert_import_ok "M2Crypto"
  assert_import_ok "pywbem"
  assert_eq "$(get_ply_version)" "$NEWPLY_VERSION" "Unexpected 'ply' package version"
  assert_eq "$(get_ply_tabversion)" "$NEWPLY_TABVERSION" "Unexpected ply table version in generated LEX/YACC table modules" 
  assert_no_moftab_build

  remove_virtualenv "test1w"
}

function test2s()
{
  info "Testcase test2s: pip installation of source archive, with old ply tables and new ply package"
  make_virtualenv "test2s"
  ensure_fresh

  run "pip install ${SRC_DISTFILE_OLDPLY}" "Installing with pip from source dist. archive: ${SRC_DISTFILE_OLDPLY}"

  assert_import_ok "six"
  assert_import_ok "ply"
  assert_import_ok "M2Crypto"
  assert_import_ok "pywbem"
  assert_eq "$(get_ply_version)" "$NEWPLY_VERSION" "Unexpected 'ply' package version"
  assert_eq "$(get_ply_tabversion)" "$OLDPLY_TABVERSION" "Unexpected ply table version in generated LEX/YACC table modules" 
  assert_moftab_build  # this shows the limitation with pip: It does not re-generate the tables upon install.

  remove_virtualenv "test2s"
}

function test2w()
{
  info "Testcase test2w: pip installation of wheel archive, with old ply tables and new ply package"
  make_virtualenv "test2w"
  ensure_fresh

  run "pip install ${WHL_DISTFILE_OLDPLY}" "Installing with pip from wheel dist. archive: ${WHL_DISTFILE_OLDPLY}"

  assert_import_ok "six"
  assert_import_ok "ply"
  assert_import_ok "M2Crypto"
  assert_import_ok "pywbem"
  assert_eq "$(get_ply_version)" "$NEWPLY_VERSION" "Unexpected 'ply' package version"
  assert_eq "$(get_ply_tabversion)" "$OLDPLY_TABVERSION" "Unexpected ply table version in generated LEX/YACC table modules" 
  assert_moftab_build  # this shows the limitation with pip: It does not re-generate the tables upon install.

  remove_virtualenv "test2w"
}

function test3()
{
  info "Testcase test3: Normal setup.py install (with missing ply tables)"
  make_virtualenv "test3"
  ensure_fresh
  call "cd $BUILDDIR; make clobber" "Removing any build artefacts"

  call "cd $BUILDDIR; python setup.py install" "Installing with setup.py from workdir"

  assert_import_ok "six"
  assert_import_ok "ply"
  assert_import_ok "M2Crypto"
  assert_import_ok "pywbem"
  assert_eq "$(get_ply_version)" "$NEWPLY_VERSION" "Unexpected 'ply' package version"
  assert_eq "$(get_ply_tabversion)" "$NEWPLY_TABVERSION" "Unexpected ply table version in generated LEX/YACC table modules" 
  assert_no_moftab_build

  remove_virtualenv "test3"
}

function test4()
{
  info "Testcase test4: setup.py installation with old ply package, upgrading ply afterwards"
  make_virtualenv "test4"
  ensure_fresh
  call "cd $BUILDDIR; make clobber" "Removing any build artefacts"
  run "pip install ply==$OLDPLY_VERSION" "Installing old version of ply: $OLDPLY_VERSION"

  call "cd $BUILDDIR; python setup.py install" "Installing with setup.py from workdir"

  assert_import_ok "six"
  assert_import_ok "ply"
  assert_import_ok "M2Crypto"
  assert_import_ok "pywbem"
  assert_eq "$(get_ply_version)" "$OLDPLY_VERSION" "Unexpected 'ply' package version"
  assert_eq "$(get_ply_tabversion)" "$OLDPLY_TABVERSION" "Unexpected ply table version in generated LEX/YACC table modules" 
  assert_no_moftab_build

  run "pip install --upgrade ply==$NEWPLY_VERSION" "Upgrading ply to new version: $NEWPLY_VERSION"

  assert_eq "$(get_ply_version)" "$NEWPLY_VERSION" "Unexpected 'ply' package version"
  assert_moftab_build

  remove_virtualenv "test4"
}

# TODO: More tests:
#       - pip install into system python
#       - setup.py install into system python

#----- main

cleanup
prep

test1s
test1w
test2s
test2w
test3
test4

cleanup

info "All testcases succeeded."

