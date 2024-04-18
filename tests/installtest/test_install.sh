#!/bin/bash
#
# Test the pywbem installation.
#
# This script can be run from any directory.
# This script peforms its tests using the 'python' command from the active
# Python environment, and it creates new virtualenvs for its tests. The
# Python command name can be customized in the PYTHON shell variable, below.

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

DEBUG="false"
VERBOSE="true"

MYNAME=$(basename "$0")
MYDIR=$(abspath $(dirname "$0"))  # Absolute path of directory of this script

# Repo root dir, as seen by caller
# Using MYDIR makes the script run with any caller's CWD.
ROOT_DIR="$MYDIR/../.."

# Detect and default PACKAGE_LEVEL (minimum/latest)
if [[ -z $PACKAGE_LEVEL ]]; then
  PACKAGE_LEVEL="latest"
fi
if [[ "$PACKAGE_LEVEL" == "latest" ]]; then
  PIP_OPTS="--upgrade"
elif [[ "$PACKAGE_LEVEL" == "minimum" ]]; then
  PIP_OPTS="-c $(abspath $ROOT_DIR/minimum-constraints.txt)"
fi

# Path of temporary test directory, as seen by caller.
# Must be a separate directory since it is deleted at the end.
# It is also used as the CWD by some tests.
TMP_TEST_DIR="$ROOT_DIR/tmp_installtest"

# Path of virtualenv directory, as seen by caller
VIRTUALENV_DIR="$TMP_TEST_DIR/virtualenvs"

# Unpack directory for source dist archive, as seen by caller
# Must be under TMP_TEST_DIR
SRC_DISTFILE_UNPACK_DIR="$TMP_TEST_DIR/src_dist"

# Top directory within source dist archive, in which there is setup.py
SRC_DISTFILE_TOP_DIR="pywbem-${PYWBEM_FULL}"

# Path of .egg file created in dist directory by setup.py, as seen by caller
EGG_FILE="$ROOT_DIR/dist/pywbem*.egg"

# Path of log file for each command, as seen by caller
CMD_LOG_FILE="$TMP_TEST_DIR/cmd.log"

# Prefix for Python virtualenv names
ENVPREFIX="pywbem_test_"

# Path of pywbem version file, as seen by caller
PYWBEM_VERSION_FILE="$ROOT_DIR/pywbem/_version.py"

# pywbem versions
PYWBEM_FULL=$(grep -E '^ *__version__ *= ' $PYWBEM_VERSION_FILE | sed -E "s/__version__ *= *'(.*)' */\1/")
PYWBEM_MNU=$(echo "$PYWBEM_FULL" | sed -E 's/\.dev[0-9]+//')
PYWBEM_MN=$(echo "$PYWBEM_MNU" | sed -E 's/([0-9]+\.[0-9]+).+$/\1/')
if [[ "$DEBUG" == "true" ]]; then
  echo "Debug: PYWBEM_FULL=$PYWBEM_FULL"
  echo "Debug: PYWBEM_MNU=$PYWBEM_MNU"
  echo "Debug: PYWBEM_MN=$PYWBEM_MN"
fi

yellow='\033[0;33m'
green='\033[0;32m'
red='\033[0;31m'
magenta='\033[0;35m'
endcolor='\033[0m'

function verbose()
{
  local msg
  msg="$1"
  if [[ "$VERBOSE" == "true" ]]; then
    echo "${msg}"
  fi
}

function heading()
{
  local msg
  msg="$1"
  echo ""
  echo -e "${green}${msg}${endcolor}"
  echo ""
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

function make_virtualenv()
{
  local envname envnamep envdir
  envname="$1"
  envnamep="${ENVPREFIX}$envname"
  envdir=$VIRTUALENV_DIR/$envnamep

  if [[ -n $VIRTUAL_ENV ]]; then
    echo "Saving location of current virtualenv: $VIRTUAL_ENV"
    VIRTUAL_ENV_SAVED=$VIRTUAL_ENV
  fi

  if [[ -d $envdir ]]; then
    verbose "Removing leftover virtualenv from previous run: $envdir"
    remove_virtualenv $envname
  fi

  python_cmd_path=$(which $PYTHON_CMD)
  verbose "Before creating virtualenv: $envdir"
  verbose "Python version: $($PYTHON_CMD --version 2>&1) from $(which $PYTHON_CMD)"
  verbose "Pip version: $(pip --version 2>&1)"
  if [[ "$DEBUG" == "true" ]]; then
    echo "Debug: Python module path:"
    python -c "import sys, pprint; pprint.pprint(sys.path)"
    echo "Debug: Packages:"
    pip list --format=columns 2>/dev/null || pip list 2>/dev/null
  fi

  if [[ "$DEBUG" == "true" ]]; then
    virtualenv_debug_opts="-vvv"
  else
    virtualenv_debug_opts=""
  fi
  run "virtualenv -p $python_cmd_path $virtualenv_debug_opts $envdir" "Creating virtualenv: $envdir"
  run "source $envdir/bin/activate" "Activating virtualenv: $envdir"

  verbose "Virtualenv before reinstalling base packages:"
  verbose "Python version: $(python --version 2>&1) from $(which python)"
  verbose "Pip version: $(pip --version 2>&1)"
  if [[ "$DEBUG" == "true" ]]; then
    echo "Debug: Python module path:"
    python -c "import sys, pprint; pprint.pprint(sys.path)"
    echo "Debug: Packages:"
    pip list --format=columns 2>/dev/null || pip list 2>/dev/null
  fi

  pip_version=$(pip --version | sed -e 's/pip \([0-9.]*\) .*/\1/')
  verbose "Debug: pip_version='$pip_version'"
  if [[ $pip_version =~ (^[1-8]\..*) ]]; then
    run "pip install 'pip==9.0.1'" "Upgrading pip $pip_version to 9.0.1"
    run "pip --version"
  fi

  run "pip install pip $PIP_OPTS" "Reinstalling pip with PACKAGE_LEVEL=$PACKAGE_LEVEL"
  run "pip install setuptools $PIP_OPTS -c $(abspath $ROOT_DIR/requirements.txt)" "Reinstalling setuptools with PACKAGE_LEVEL=$PACKAGE_LEVEL and constraints from requirements.txt"
  run "pip install wheel $PIP_OPTS" "Reinstalling wheel with PACKAGE_LEVEL=$PACKAGE_LEVEL"
}

function remove_virtualenv()
{
  local envname envnamep envdir
  envname="$1"
  envnamep="${ENVPREFIX}$envname"
  envdir=$VIRTUALENV_DIR/$envnamep

  verbose "Removing virtualenv: $envdir"
  if [[ ! -d $envdir ]]; then
    error "Virtualenv directory does not exist: $envdir"
    exit 1
  fi
  rm -rf $envdir

  if [[ -n $VIRTUAL_ENV_SAVED ]]; then
    run "source $VIRTUAL_ENV_SAVED/bin/activate" "Re-activating saved virtualenv: $VIRTUAL_ENV_SAVED"
  else
    unset VIRTUAL_ENV
  fi
}

function list_virtualenv()
{
  local curdir msg
  curdir="$1"
  msg="$2"
  echo "$msg"
  sh -c "cd $curdir; pip list --format=columns || pip list"
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
    echo "Debug: Command: $cmd"
    eval "$cmd"
    rc=$?
    echo "Debug: command returns: rc=$rc"
  else
    verbose "Command: $cmd"
    eval "$cmd" >$CMD_LOG_FILE 2>&1
    rc=$?
  fi
  if [[ $rc != 0 ]]; then
    error "Command failed with rc=$rc: $cmd, output follows:"
    cat $CMD_LOG_FILE
    exit 1
  fi
  rm -f $CMD_LOG_FILE
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
    echo "Debug: Command (in subshell): $cmd"
    sh -c "$cmd"
    rc=$?
    echo "Debug: command returns: rc=$rc"
  else
    verbose "Command (in subshell): $cmd"
    sh -c "$cmd" >$CMD_LOG_FILE 2>&1
    rc=$?
  fi
  if [[ $rc != 0 ]]; then
    error "Command failed with rc=$rc: $cmd, output follows:"
    cat $CMD_LOG_FILE
    exit 1
  fi
  rm -f $CMD_LOG_FILE
}

function assert_run_ok()
{
  local cmd msg rc
  cmd="$1"
  msg="$2"
  if [[ "$DEBUG" == "true" ]]; then
    echo "Debug: Command: $cmd"
    eval "$cmd"
    rc=$?
    echo "Debug: command returns: rc=$rc"
  else
    verbose "Command: $cmd"
    eval "$cmd" >$CMD_LOG_FILE 2>&1
    rc=$?
  fi
  if [[ $rc != 0 ]]; then
    if [[ -n $msg ]]; then
      failure "$msg"
    fi
    failure "Command failed with rc=$rc: $cmd, output follows:"
    cat $CMD_LOG_FILE
    exit 1
  fi
  rm -f $CMD_LOG_FILE
}

function assert_run_fails()
{
  local cmd msg rc
  cmd="$1"
  msg="$2"
  if [[ "$DEBUG" == "true" ]]; then
    echo "Debug: Command: $cmd"
    eval "$cmd"
    rc=$?
    echo "Debug: command returns: rc=$rc"
  else
    verbose "Command: $cmd"
    eval "$cmd" >$CMD_LOG_FILE 2>&1
    rc=$?
  fi
  if [[ $rc == 0 ]]; then
    if [[ -n $msg ]]; then
      failure "$msg"
    fi
    failure "Command succeeded but should have failed: $cmd, output follows:"
    cat $CMD_LOG_FILE
    exit 1
  fi
  rm -f $CMD_LOG_FILE
}

function ensure_uninstalled()
{
  local pkg
  pkg="$1"
  cmd="pip uninstall -y -q $pkg"
  if [[ "$DEBUG" == "true" ]]; then
    echo "Debug: Command: $cmd"
    eval "$cmd"
    rc=$?
    echo "Debug: command returns: rc=$rc"
  else
    verbose "Command: $cmd"
    eval "$cmd" >/dev/null 2>/dev/null
  fi
}

function assert_import_ok()
{
  local module dir
  module="$1"
  dir="$2"
  verbose "Checking for successful import of module $module in directory $dir"
  assert_run_ok "cd ${dir}; python -c \"import ${module}\"" "Python module '${module}' cannot be imported in directory $dir"
}

function assert_import_fails()
{
  local module dir
  module="$1"
  dir="$2"
  verbose "Checking for failing import of module $module in directory $dir"
  assert_run_fails "cd ${dir}; python -c \"import ${module}\"" "Python module '${module}' can be imported in directory $dir but should have failed"
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
  vers=$(python -c "from pywbem import _mofparsetab; print(_mofparsetab._tabversion)")
  rc=$?
  if [[ $rc != 0 ]]; then
    error "Cannot determine generated table version of _mofparsetab.py: python returns rc=$rc"
    exit 1
  fi
  echo $vers
}

function build_moftab()
{
  python -c "from pywbem import _mof_compiler; _mof_compiler._build()"
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
  ensure_uninstalled "pywbem"
}

#-------------------------------------------------

function prep()
{
  heading "Preparing for the tests"

  if [[ -d $TMP_TEST_DIR ]]; then
    echo "Removing test directory: $TMP_TEST_DIR"
    rm -rf $TMP_TEST_DIR
  fi
  echo "Creating test directory: $TMP_TEST_DIR"
  mkdir -p $TMP_TEST_DIR

  if [[ ! -d $SRC_DISTFILE_UNPACK_DIR ]]; then
    echo "Creating source archive unpack directory: $SRC_DISTFILE_UNPACK_DIR"
    mkdir -p $SRC_DISTFILE_UNPACK_DIR
  fi

  if [[ ! -f $EGG_FILE ]]; then
    echo "Removing .egg file: $EGG_FILE"
    rm -f $EGG_FILE
  fi
}

function cleanup()
{
  heading "Cleaning up from the tests"

  if [[ "$DEBUG" == "true" ]]; then
    echo "Debug: Not removing $TMP_TEST_DIR for debug inspection"
  else
    echo "Removing test directory: $TMP_TEST_DIR"
    rm -rf $TMP_TEST_DIR
  fi

  cleanup_egg_file

  # Normally already deleted by function creating it
  rm -f $CMD_LOG_FILE
}

function cleanup_egg_file()
{
  if [[ ! -f $EGG_FILE ]]; then
    echo "Removing .egg file: $EGG_FILE"
    rm -f $EGG_FILE
  fi
}

function test1()
{
  testcase="test1"
  heading "Testcase $testcase: Pip install from repo root directory: $ROOT_DIR"
  make_virtualenv "$testcase"
  list_virtualenv "$TMP_TEST_DIR" "Python packages in virtualenv before installation (PACKAGE_LEVEL=$PACKAGE_LEVEL)"

  call "cd $ROOT_DIR; pip install . $PIP_OPTS" "Installing with pip from repo root directory (PACKAGE_LEVEL=$PACKAGE_LEVEL)"

  list_virtualenv "$TMP_TEST_DIR" "Python packages in virtualenv after installation (PACKAGE_LEVEL=$PACKAGE_LEVEL)"
  assert_import_ok "pywbem" "$TMP_TEST_DIR"
  assert_import_ok "pywbem_mock" "$TMP_TEST_DIR"
  assert_no_moftab_build
  remove_virtualenv "$testcase"
  cleanup_egg_file
}

function test3()
{
  testcase="test3"
  heading "Testcase $testcase: Pip install from wheel distribution archive: $WHL_DISTFILE"
  make_virtualenv "$testcase"
  list_virtualenv "$TMP_TEST_DIR" "Python packages in virtualenv before installation (PACKAGE_LEVEL=$PACKAGE_LEVEL)"

  call "cd $TMP_TEST_DIR; pip install $(abspath $WHL_DISTFILE) $PIP_OPTS" "Installing with pip from wheel distribution archive (PACKAGE_LEVEL=$PACKAGE_LEVEL)"

  list_virtualenv "$TMP_TEST_DIR" "Python packages in virtualenv after installation (PACKAGE_LEVEL=$PACKAGE_LEVEL)"
  assert_import_ok "pywbem" "$TMP_TEST_DIR"
  assert_import_ok "pywbem_mock" "$TMP_TEST_DIR"
  assert_no_moftab_build
  remove_virtualenv "$testcase"
  cleanup_egg_file
}

function test4()
{
  testcase="test4"
  heading "Testcase $testcase: Pip install from source distribution archive: $SRC_DISTFILE"
  make_virtualenv "$testcase"
  list_virtualenv "$TMP_TEST_DIR" "Python packages in virtualenv before installation (PACKAGE_LEVEL=$PACKAGE_LEVEL)"

  call "cd $TMP_TEST_DIR; pip install $(abspath $SRC_DISTFILE) $PIP_OPTS" "Installing with pip from source distribution archive (PACKAGE_LEVEL=$PACKAGE_LEVEL)"

  list_virtualenv "$TMP_TEST_DIR" "Python packages in virtualenv after installation (PACKAGE_LEVEL=$PACKAGE_LEVEL)"
  assert_import_ok "pywbem" "$TMP_TEST_DIR"
  assert_import_ok "pywbem_mock" "$TMP_TEST_DIR"
  assert_no_moftab_build
  remove_virtualenv "$testcase"
  cleanup_egg_file
}

#----- main

WHL_DISTFILE=$(abspath "$1")  # absolute or relative to caller's cwd
SRC_DISTFILE=$(abspath "$2")  # absolute or relative to caller's cwd
PYTHON_CMD="$3"    # Python command to use (outside of the created virtualenvs)

if [[ -z $PYTHON_CMD ]]; then
  error "Arguments missing. Usage: $MYNAME WHEEL_DIST_FILE SOURCE_DIST_FILE PYTHON_CMD"
  exit 2
fi
if [[ ! -f $WHL_DISTFILE ]]; then
  error "Wheel distribution archive does not exist: $WHL_DISTFILE"
  exit 1
fi
if [[ ! -f $SRC_DISTFILE ]]; then
  error "Source distribution archive does not exist: $SRC_DISTFILE"
  exit 1
fi
if ! which $PYTHON_CMD >/dev/null 2>&1; then
  error "Cannot find Python command: $PYTHON_CMD"
  exit 1
fi

prep

test1
test3
test4

cleanup

heading "All testcases succeeded."
