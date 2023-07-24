#!/bin/bash
#
# (C) Copyright 2017 IBM Corp.
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
# Author: Andreas Maier <maiera@de.ibm.com>
#

# Script that installs OS-level prerequisites for pywbem on Linux, MacOS, and
# Windows with UNIX-like environments (Cygwin).
#
# Prerequisite commands for running this script:
#     python (This script uses the active Python environment, virtual Python
#       environments are supported)
#     pip (with support for download subcommand, is installed by makefile)
#     uname
#     The package installer for your OS (yum, dnf, apt, zypper, brew, ...)

arg1="${1:-install}"
arg2="${2:-}"
myname=$(basename $0)

if [[ "$arg1" == "--help" || "$arg1" == "-h" ]]; then
  echo ""
  echo "$myname: Install OS-level packages needed by pywbem."
  echo ""
  echo "Usage:"
  echo "  $myname [PURPOSE]"
  echo ""
  echo "Where:"
  echo "  PURPOSE     Purpose of the OS-level package installation, with values:"
  echo "                install: Packages needed for installing pywbem (default)."
  echo "                develop: Additional packages needed for developing pywbem."
  echo ""
  exit 2
fi
if [[ "$arg2" != "" ]]; then
  echo "$myname: Error: Too many arguments; Invoke with --help for usage." >&2
  exit 2
fi

purpose="$arg1"
if [[ "$purpose" != "install" && "$purpose" != "develop" ]]; then
  echo "$myname: Error: Invalid purpose: $purpose; Invoke with --help for usage." >&2
  exit 2
fi

if [[ "$purpose" == "install" ]]; then
  echo "$myname:"
  echo "$myname: ================================================================"
  echo "$myname:"
  echo "$myname: Starting with pywbem 1.0.0, the installation of pywbem does not"
  echo "$myname: need any OS-level prerequisite packages anymore, and therefore"
  echo "$myname: no longer needs to run the pywbem_os_setup.sh script. Because"
  echo "$myname: this script cannot determine the version of pywbem, it will"
  echo "$myname: install the prerequisites needed for pywbem before 1.0.0."
  echo "$myname:"
  echo "$myname: ================================================================"
  echo "$myname:"
fi

function run_cmd() {
  cmd="$1"
  echo "$cmd"
  eval "$cmd"
  rc=$?
  if [[ $rc != 0 ]]; then
    echo "$myname: Error: Command failed with rc=$rc: $cmd"
    exit 2
  fi
}

function install_redhat() {
  installer="$1"
  pkg="$2"
  echo "$myname: Installing package: $pkg"
  run_cmd "sudo $installer -y install $pkg"
  run_cmd "sudo $installer list installed $pkg"
  echo "$myname: Done installing package: $pkg"
}

function install_debian() {
  pkg="$1"
  echo "$myname: Installing package: $pkg"
  # Note: The python:2.7.18-buster Docker container has no sudo
  apt -qq list $pkg
  if [[ "$(apt -qq list $pkg)" != *"installed"* ]]; then
    if which sudo >/dev/null; then
      echo "Installing $pkg package"
      run_cmd "sudo apt-get --yes install $pkg"
      run_cmd "sudo apt list --installed | grep $pkg"
    else
      echo "Warning: Not installing $pkg package due to missing sudo"
    fi
  else
    echo "$pkg package is already installed"
  fi
  echo "$myname: Done installing package: $pkg"
}

function install_suse() {
  pkg="$1"
  echo "$myname: Installing package: $pkg"
  run_cmd "sudo zypper install -y $pkg"
  run_cmd "sudo zypper pa -i | grep $pkg"
  echo "$myname: Done installing package: $pkg"
}

function install_osx() {
  pkg="$1"
  echo "$myname: Upgrading or installing package: $pkg"
  run_cmd "brew upgrade $pkg || brew install $pkg"
  run_cmd "brew info $pkg"
  echo "$myname: Done installing package: $pkg"
}

function install_cygwin() {
  pkg="$1"
  echo "$myname: Installing package: $pkg"
  if [[ "$(uname -m)" == "x86_64" ]]; then
    run_cmd "/cygdrive/c/cygwin64/setup-x86_64.exe --no-shortcuts --quiet-mode --packages $pkg"
  else
    run_cmd "/cygdrive/c/cygwin/setup-x86.exe --no-shortcuts --quiet-mode --packages $pkg"
  fi
  echo "$myname: Done installing package: $pkg"
}

if [[ "$OS" == "Windows_NT" ]]; then
  # Note: Native Windows and CygWin are hard to distinguish: The native Windows
  # envvars are set in CygWin as well. Using uname will display CYGWIN_NT-.. on
  # both platforms. If the CygWin make is used on native Windows, most of the
  # CygWin behavior is then visible in context of that make (e.g. a SHELL envvar
  # is set, the PATH envvar gets converted to UNIX syntax, execution of batch
  # files requires execute permission, etc.).
  if [[ -n $PWD ]]; then
    distro_id="cygwin"
    distro_family="cygwin"
    platform="Windows_CygWin"
  else
    distro_id="windows"
    distro_family="windows"
    platform="Windows_native"
  fi
# If you need support for more Unix-like environments on Windows (e.g. MinGW)
# please provide the code for detecting them here.
elif [[ "$(uname -s)" == "Linux" ]]; then
  distro_id=$(python -c "import distro; print(distro.id())" 2>/dev/null)
  if [[ $? != 0 ]]; then
    echo "$myname: Installing the Python 'distro' package into the current Python environment."
    pip install distro
    if [[ $? != 0 ]]; then
      echo "$myname: Error: Cannot install Python 'distro' package into current Python environment." >&2
      exit  1
    fi
    distro_id=$(python -c "import distro; print(distro.id())")
  fi
  if [[ -z $distro_id ]]; then
    echo "$myname: Error: Cannot determine Linux distro." >&2
    exit  1
  fi
  case $distro_id in
    rhel|centos|fedora)
      distro_family="redhat";;
    debian|ubuntu)
      distro_family="debian";;
    sles|opensuse)
      distro_family="suse";;
    *)
      distro_family=$distro_id;;
  esac
  platform="Linux (distro: $distro_id, family: $distro_family)"
elif [[ "$(uname -s)" == "Darwin" ]]; then
  distro_id="osx"
  distro_family=$distro_id
  platform="OS-X"
else
  echo "$myname: Error: Cannot determine operating system. Diagnostic info:" >&2
  echo ". uname -a: $(uname -a)" >&2
  echo ". uname -s: $(uname -s)" >&2
  echo ". OS env.var: $OS" >&2
  exit 1
fi

py_m=$(python -c "import sys; print(sys.version_info[0])")
py_mn=$(python -c "import sys; print('%s.%s' % (sys.version_info[0], sys.version_info[1]))")

echo "$myname: Installing OS-level prerequisite packages for $purpose on platform ${platform}..."

if [[ "$distro_family" == "redhat" ]]; then

  if which dnf >/dev/null 2>/dev/null; then
    installer=dnf
  else
    installer=yum
  fi
  echo "$myname: Using installer: $installer"

  if [[ "$installer" == "dnf" ]]; then
    sudo $installer makecache
  else
    sudo $installer makecache fast
  fi

  if [[ "$purpose" == "install" ]]; then
    if [[ "$py_m" == "2" ]]; then
      # For M2Crypto:
      install_redhat $installer openssl-devel
      install_redhat $installer gcc-c++
      install_redhat $installer swig
      install_redhat $installer python-devel
    fi
  fi

  if [[ "$purpose" == "develop" ]]; then
    # For lxml:
    install_redhat $installer libxml2
    install_redhat $installer libxslt
  fi

elif [[ "$distro_family" == "debian" ]]; then

  sudo apt-get --quiet update

  if [[ "$purpose" == "install" ]]; then
    if [[ "$py_m" == "2" ]]; then
      # For M2Crypto:
      install_debian libssl-dev
      install_debian g++
      install_debian swig
      install_debian python-dev
    fi
  fi

  if [[ "$purpose" == "develop" ]]; then
    # For lxml:
    install_debian libxml2-utils
    install_debian libxslt1-dev
  fi

elif [[ "$distro_family" == "suse" ]]; then

  sudo zypper refresh

  if [[ "$purpose" == "install" ]]; then
    if [[ "$py_m" == "2" ]]; then
      # For M2Crypto:
      install_suse openssl-devel
      install_suse gcc-c++
      install_suse swig
      install_suse python-devel
    fi
  fi

  if [[ "$purpose" == "develop" ]]; then
    # For lxml:
    install_suse libxml2
    install_suse libxslt
  fi

elif [[ "$distro_family" == "osx" ]]; then

  if [[ "$purpose" == "install" ]]; then
    # Python devel seems to be part of the python package.
    if [[ "$py_m" == "2" ]]; then
      # For M2Crypto:
      install_osx openssl
      install_osx gcc
      install_osx swig
    fi
  fi

  if [[ "$purpose" == "develop" ]]; then
    # For lxml:
    install_osx libxml2
    install_osx libxslt
  fi

elif [[ "$distro_family" == "windows" ]]; then

  if [[ "$purpose" == "install" ]]; then
    echo "$myname: Invoking 'pywbem_os_setup.bat install' on platform ${platform}." >&2
    cmd /d /c pywbem_os_setup.bat install
  fi
  if [[ "$purpose" == "develop" ]]; then
    echo "$myname: Invoking 'pywbem_os_setup.bat develop' on platform ${platform}." >&2
    cmd /d /c pywbem_os_setup.bat develop
  fi

elif [[ "$distro_family" == "cygwin" ]]; then

  if [[ "$purpose" == "install" ]]; then
    if [[ "$py_m" == "2" ]]; then
      # For M2Crypto:
      install_cygwin openssl
      install_cygwin libssl-devel
      install_cygwin openssl-devel
      install_cygwin gcc
      install_cygwin swig
      # For M2Crypto, pyzmq (used by Jupyter), lxml:
      install_cygwin python2-devel
      install_cygwin python2-cython
    fi
  fi

  if [[ "$purpose" == "develop" ]]; then
    # For lxml:
    install_cygwin libxml2
    install_cygwin libxslt
    install_cygwin libxml2-devel
    install_cygwin libxslt-devel
    install_cygwin libcrypt-devel
    # For pyzmq (used by Jupyter):
    install_cygwin libzmq-devel
    install_cygwin libffi-devel
    if [[ "$py_m" == "2" ]]; then
      # For pyzmq (used by Jupyter), lxml:
      install_cygwin python2-devel
      install_cygwin python2-cython
    fi
    if [[ "$py_m" == "3" ]]; then
      # For pyzmq, lxml:
      install_cygwin python3-devel
      install_cygwin python3-cython
    fi
  fi

else
  echo "$myname: Warning: Installation of OS-level packages not supported on platform ${platform}." >&2
  echo ". The equivalent packages for the Linux RedHat family are:" >&2
  echo ". For installing pywbem:" >&2
  echo ".   * openssl-devel (at least 1.0.1, only on Python 2)" >&2
  echo ".   * gcc-c++ (at least 4.4, only on Python 2)" >&2
  echo ".   * swig (>=2.0.0, only on Python 2)" >&2
  echo ".   * python-devel (only on Python 2" >&2
  echo ". In addition, for developing pywbem:" >&2
  echo ".   * libxml2 (>=2.7.0,!=2.7.4,!=2.7.5,!=2.7.6 on Python 2 and 3)" >&2
fi
