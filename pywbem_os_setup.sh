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

# This script installs the OS-level prerequisite package that users of
# pywbem need.

function install_redhat() {
  installer="$1"
  pkg="$2"
  echo "Installing package: $pkg"
  sudo $installer -y install $pkg
}

function install_debian() {
  pkg="$1"
  echo "Installing package: $pkg"
  sudo apt-get --yes install $pkg
}

function install_suse() {
  pkg="$1"
  echo "Installing package: $pkg"
  sudo zypper install -y $pkg
}

function install_osx() {
  pkg="$1"
  echo "Upgrading or installing package: $pkg"
  brew upgrade $pkg || brew install $pkg
}

if [[ "$OS" == "Windows_NT" ]]; then
  distro_id="windows"
  distro_family=$distro_id
  platform="Windows"
elif [[ "$(uname -s | sed -e 's/-.*//g')" == "CYGWIN_NT" ]]; then
  distro_id="cygwin"
  distro_family=$distro_id
  platform="CygWin"
elif [[ "$(uname -s)" == "Linux" ]]; then
  distro_id=$(python -c "import distro; print(distro.id())" 2>/dev/null)
  if [[ $? != 0 ]]; then
    pyenv=$(python -c "import sys; out='venv' if hasattr(sys, 'real_prefix') or getattr(sys, 'base_prefix', None) == sys.prefix else 'system'; print(out)")
    if [[ $pyenv == "venv" ]]; then
      echo "Installing the Python 'distro' package into the current virtual Python environment."
      pip install distro
      if [[ $? != 0 ]]; then
        echo "Error: Cannot install Python 'distro' package into current virtual Python environment."
        exit  1
      fi
      distro_id=$(python -c "import distro; print(distro.id())")
    else
      echo "Error: The Python 'distro' package is not installed, and you do not currently have a virtual Python environment active."
      exit  1
    fi
  fi
  if [[ -z $distro_id ]]; then
    echo "Error: Cannot determine Linux distro."
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
  echo "Error: Cannot determine operating system:"
  echo "  uname -a: $(uname -a)"
  echo "  uname -s: $(uname -s)"
  echo "  OS var.: $OS"
  exit  1
fi


py_m=$(python -c "import sys; print(sys.version_info[0])")
py_mn=$(python -c "import sys; print('%s.%s' % (sys.version_info[0], sys.version_info[1]))")

echo "Installing OS-level prerequisite packages on platform ${platform}..."

if [[ "$distro_family" == "redhat" ]]; then

  if which dnf >/dev/null 2>/dev/null; then
    installer=dnf
  else
    installer=yum
  fi
  echo "Using installer: $installer"

  sudo $installer makecache fast
  if [[ "$py_m" == "2" ]]; then
    # For M2Crypto:
    install_redhat $installer openssl-devel
    install_redhat $installer gcc-c++
    install_redhat $installer swig
    install_redhat $installer python-devel
  fi
  install_redhat $installer libxml2

elif [[ "$distro_family" == "debian" ]]; then

  sudo apt-get --quiet update
  if [[ "$py_m" == "2" ]]; then
    # For M2Crypto:
    install_debian libssl-dev
    install_debian g++
    install_debian swig
    install_debian python-dev
  fi
  install_debian libxml2-utils

elif [[ "$distro_family" == "suse" ]]; then

  # TODO: update zypper package list
  if [[ "$py_m" == "2" ]]; then
    # For M2Crypto:
    install_suse openssl-devel
    install_suse gcc-c++
    install_suse swig
    install_suse python-devel
  fi
  install_suse libxml2

elif [[ "$distro_family" == "osx" ]]; then

  brew update
  if [[ "$py_m" == "2" ]]; then
    # For M2Crypto:
    install_osx openssl
    install_osx gcc
    install_osx swig
  fi
  install_osx libxml2

else

  echo "Error: Installation of OS-level packages not supported on platform ${platform}."
  echo "The equivalent packages for the Redhat family of Linux distros are:"
  echo "  * openssl-devel (at least 1.0.1, only on Python 2)"
  echo "  * gcc-c++ (at least 4.4, only on Python 2)"
  echo "  * swig (at least 2.0, only on Python 2)"
  echo "  * python-devel (only on Python 2"
  echo "  * libxml2 (on Python 2 and 3)"

fi

