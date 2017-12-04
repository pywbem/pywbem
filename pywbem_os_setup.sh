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


py_m=$(python -c "import sys; print(sys.version_info.major)")
py_mn=$(python -c "import sys; print('%s.%s' % (sys.version_info.major, sys.version_info.minor))")

echo "Installing OS-level prerequisite packages on platform ${platform}..."

if [[ "$distro_family" == "redhat" ]]; then

  if which dnf >/dev/null 2>/dev/null; then
    installer=dnf
  else
    installer=yum
  fi

  echo "Using installer: $installer"

  sudo $installer makecache fast

  sudo $installer -y install openssl-devel  # at least 1.0.1, for M2Crypto installation
  sudo $installer -y install gcc-c++  # at least 4.4, for M2Crypto installation
  sudo $installer -y install swig  # at least 2.0, for M2Crypto installation
  if [[ "$py_m" == "2" ]]; then
    sudo $installer -y install python-devel  # for M2Crypto installation
  else
    sudo $installer -y install python${py_mn}-devel  # for M2Crypto installation
  fi
  sudo $installer -y install libxml2  # for xmllint (for testing)

elif [[ "$distro_family" == "debian" ]]; then

  sudo apt-get --quiet update

  sudo apt-get --yes install libssl-dev  # at least 1.0.1, for M2Crypto installation
  sudo apt-get --yes install g++  # at least 4.4, for M2Crypto installation
  sudo apt-get --yes install swig  # at least 2.0, for M2Crypto installation
  if [[ "$py_m" == "2" ]]; then
    sudo apt-get --yes install python-dev  # for M2Crypto installation
  else
    sudo apt-get --yes install python${py_m}-dev  # for M2Crypto installation
  fi
  sudo apt-get --yes install libxml2-utils  # for xmllint (for testing)

elif [[ "$distro_family" == "suse" ]]; then

  # TODO: update zypper package list

  sudo zypper -y install openssl-devel  # at least 1.0.1, for M2Crypto installation
  sudo zypper -y install gcc-c++  # at least 4.4, for M2Crypto installation
  sudo zypper -y install swig  # at least 2.0, for M2Crypto installation
  if [[ "$py_m" == "2" ]]; then
    sudo zypper -y install python-devel  # for M2Crypto installation
  else
    sudo zypper -y install python${py_mn}-devel  # for M2Crypto installation
  fi
  sudo zypper -y install libxml2  # for xmllint (for testing)

else

  echo "Error: Installation of OS-level packages not supported on platform ${platform}."
  echo "The equivalent packages for the redhat family of Linux distros are:"
  echo "  * libxml2 (at least ?)"
  echo "  * openssl-devel (at least 1.0.1)"
  echo "  * gcc-c++ (at least 4.4)"
  echo "  * swig (at least 2.0)"
  if [[ "$py_m" == "2" ]]; then
    echo "  * python-devel"
  else
    echo "  * python${py_mn}-devel"
  fi

fi
