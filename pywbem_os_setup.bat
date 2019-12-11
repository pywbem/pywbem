@rem ---------------------------------------------------------------------------
@rem Script that installs OS-level prerequisites for pywbem on native Windows
@rem
@rem Prerequisite commands for running this script:
@rem     python (This script uses the active Python environment, virtual Python
@rem       environments are supported)
@rem     pip>=8.0.0 (with support for download subcommand, is installed by makefile)
@rem     choco (Chocolatey package manager, from https://chocolatey.org)
@rem     tar
@rem     chmod

@setlocal enableextensions
@echo off
set errorlevel=
set myname=pywbem_os_setup.bat

:: Bit size of the Python env.
if defined PYTHON_ARCH goto arch_defined
python -c "import struct; print('@set PYTHON_ARCH=%%s' %% (struct.Struct('P').size * 8))" >tmp_arch.bat
call tmp_arch.bat
del tmp_arch.bat
:arch_defined

:: Python version
python -c "import sys; print('@set PYTHON_M_VERSION=%%s' %% sys.version_info[0])" >tmp_vers.bat
call tmp_vers.bat
del tmp_vers.bat

echo %myname%: Current Python is: Version %PYTHON_M_VERSION%, %PYTHON_ARCH%-bit

if "%1"=="" goto do_install
if "%1"=="install" goto do_install
if "%1"=="develop" goto do_develop
echo Usage: pywbem_os_setup.bat [develop / install]
goto end

:do_install

echo %myname%: Installing OS-level prerequisite packages for install on platform Windows_native ...

if not exist tmp_pywbem_os_setup mkdir tmp_pywbem_os_setup
pushd tmp_pywbem_os_setup

if not %PYTHON_M_VERSION%==2 goto install_no_py2

where curl >nul
if %errorlevel%==0 (
    echo %myname%: Curl is already installed ... showing details
    echo where curl
    where curl
    echo curl --version
    curl --version
    echo %myname%: Curl is already installed ... skipping
    goto done_curl
)

echo %myname%: Installing Curl ...

set _CMD=choco install -y curl
:: The following test ensures that this script still works when downloaded standalone.
if exist ..\tools\retry.bat set _CMD=..\tools\retry.bat %_CMD%
echo %_CMD%
call %_CMD%
set _RC=%errorlevel%
if not "%_RC%"=="0" echo %myname%: Warning: choco returned rc=%_RC%

set _CMD=where curl
echo %_CMD%
call %_CMD%
set _RC=%errorlevel%
if not "%_RC%"=="0" goto error1

echo %myname%: Done installing Curl
:done_curl

where grep >nul
if %errorlevel%==0 (
    echo %myname%: Grep is already installed ... showing details
    echo where grep
    where grep
    echo grep --version
    grep --version
    echo %myname%: Grep is already installed ... skipping
    goto done_grep
)

echo %myname%: Installing Grep ...

set _CMD=choco install -y grep
:: The following test ensures that this script still works when downloaded standalone.
if exist ..\tools\retry.bat set _CMD=..\tools\retry.bat %_CMD%
echo %_CMD%
call %_CMD%
set _RC=%errorlevel%
if not "%_RC%"=="0" echo %myname%: Warning: choco returned rc=%_RC%

set _CMD=where grep
echo %_CMD%
call %_CMD%
set _RC=%errorlevel%
if not "%_RC%"=="0" goto error1

echo %myname%: Done installing Grep
:done_grep

:install_no_py2

popd
goto end

:do_develop

echo %myname%: Installing OS-level prerequisite packages for develop on platform Windows_native ...

where xmllint >nul
if %errorlevel%==0 (
    echo %myname%: xmllint is already installed ... showing details
    echo where xmllint
    where xmllint
    echo xmllint --version
    xmllint --version
    echo %myname%: xmllint is already installed ... skipping
    goto done_xmllint
)

echo %myname%: Installing xmllint ...

set _CMD=choco install -y xsltproc
:: The following test ensures that this script still works when downloaded standalone.
if exist tools\retry.bat set _CMD=tools\retry.bat %_CMD%
echo %_CMD%
call %_CMD%
set _RC=%errorlevel%
if not "%_RC%"=="0" echo %myname%: Warning: choco returned rc=%_RC%

set _CMD=where xmllint
echo %_CMD%
call %_CMD%
set _RC=%errorlevel%
if not "%_RC%"=="0" goto error1

echo %myname%: Done installing xmllint
:done_xmllint

goto end

:error2
popd
:error1
popd
:error
echo %myname%: Error: Command returned rc=%_RC%
exit /b %_RC%

:end
rmdir /q /s tmp_pywbem_os_setup
endlocal
exit /b 0
