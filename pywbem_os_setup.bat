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

echo %myname%:
echo %myname%: ================================================================
echo %myname%:
echo %myname%: Starting with pywbem 1.0.0, the installation of pywbem does not
echo %myname%: need any OS-level prerequisite packages anymore, and therefore
echo %myname%: no longer needs to run the pywbem_os_setup.bat script. Because
echo %myname%: this script cannot determine the version of pywbem, it will
echo %myname%: install the prerequisites needed for pywbem before 1.0.0.
echo %myname%:
echo %myname%: ================================================================
echo %myname%:

echo %myname%: Installing OS-level prerequisite packages for install on platform Windows_native ...

if not exist tmp_pywbem_os_setup mkdir tmp_pywbem_os_setup
pushd tmp_pywbem_os_setup

if not %PYTHON_M_VERSION%==2 goto install_no_py2

where swig >nul
if %errorlevel%==0 (
    echo %myname%: Swig is already installed ... showing details
    echo where swig
    where swig
    echo swig -version
    swig -version
    echo %myname%: Swig is already installed ... skipping
    goto done_swig
)

echo %myname%: Installing Swig ...

:: The following installation of swig installs swig but without generating
:: the swig.exe shim file (using GenShim).
:: See GenShim issue https://github.com/chocolatey/shimgen/issues/43
:: Therefore, we install swig in appveyor.yml in order to create the swig.exe
:: shim file.
:: We install it here again for users of pywbem.
:: TODO: Remove the circumvention once it works in pywbem_os_setup.bat.

:: swig 4.0.2 (at least when used with M2Crypto) is missing the swig.swg file,
:: so we stay with 4.0.1.
set _CMD=choco install -y swig --version 4.0.1
:: The following test ensures that this script still works when downloaded standalone.
if exist ..\tools\retry.bat set _CMD=..\tools\retry.bat %_CMD%
echo %_CMD%
call %_CMD%
set _RC=%errorlevel%
if not "%_RC%"=="0" echo %myname%: Warning: choco returned rc=%_RC%

set _CMD=where swig
echo %_CMD%
call %_CMD%
set _RC=%errorlevel%
if not "%_RC%"=="0" goto error1

echo %myname%: Done installing Swig
:done_swig

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

echo %myname%: Installing Win32OpenSSL ...

:: The version of Win32OpenSSL to be downloaded.
:: Note that the Win32OpenSSL project at https://slproweb.com/ removes
:: the previously available version when a new version is released. Whenever
:: that happens, this version here must be updated.
set _WIN32OPENSSL_VERSION_UNDERSCORED=1_1_1i
set _WIN32OPENSSL_VERSION_DASHED=1-1-1i

:: The bit size of Win32OpenSSL must match the bit size of the Python env.
set _WIN32OPENSSL_BITSIZE=%PYTHON_ARCH%
set _WIN32OPENSSL_BASENAME=Win%_WIN32OPENSSL_BITSIZE%OpenSSL-%_WIN32OPENSSL_VERSION_UNDERSCORED%
set _WIN32OPENSSL_INSTALL_DIR=C:\OpenSSL-%_WIN32OPENSSL_VERSION_DASHED%-Win%_WIN32OPENSSL_BITSIZE%
if exist %_WIN32OPENSSL_INSTALL_DIR% (
    echo %myname%: %_WIN32OPENSSL_BASENAME% is already installed in %_WIN32OPENSSL_INSTALL_DIR% ... skipping
    goto done_winopenssl
)

if exist %_WIN32OPENSSL_BASENAME%.exe (
    echo %myname%: %_WIN32OPENSSL_BASENAME% has already been downloaded - using it.
    goto install_winopenssl
)

set _CMD=curl -o %_WIN32OPENSSL_BASENAME%.exe -sSL https://slproweb.com/download/%_WIN32OPENSSL_BASENAME%.exe --retry 3 --retry-connrefused --retry-delay 10
echo %_CMD%
call %_CMD%
set _RC=%errorlevel%
if not "%_RC%"=="0" goto error1

:: If the web site does not know the file, it returns an HTML page showing an
:: error, and curl succeeds downloading that HTML page.
:: Note: The desired regexp would be "^<html>", but grep 3.0 on Appveyor does
::       not support "^" and the Windows command shell has difficulties with
::       the angle brackets in "<html>".
set _CMD=grep ".html." %_WIN32OPENSSL_BASENAME%.exe
echo %_CMD%
call %_CMD%
set _RC=%errorlevel%
if "%_RC%"=="0" (
    echo %myname%: Error: The %_WIN32OPENSSL_BASENAME%.exe file does not exist on https://slproweb.com.
    echo %myname%: The https://slproweb.com web site says:
    type %_WIN32OPENSSL_BASENAME%.exe
    echo %myname%: End of https://slproweb.com web site
    echo %myname%: The most likely reason for this is that a new version of WinOpenSSL has been released.
    echo %myname%: You can deal with this as follows:
    echo %myname%: - Go to https://slproweb.com - Products - Win32/Win64 OpenSSL
    echo %myname%: - Download the latest fix version of %_WIN32OPENSSL_BASENAME%.exe into the current directory.
    echo %myname%:   That is the version with the same numeric version but a different fix letter.
    echo %myname%: - Re-run the pywbem_os_setup.bat script
    echo %myname%: Please also open an issue on https://github.com/pywbem/pywbem/issues
    rm %_WIN32OPENSSL_BASENAME%.exe
    set _RC=1
    goto error1
)

:install_winopenssl

:: Downloaded files may not have the execution right.
rem TODO: Find a way to set RX with the built-in icacls to remove dependency on chmod
rem set _CMD=icacls %_WIN32OPENSSL_BASENAME%.exe /grant "*S-1-1-0":F
set _CMD=chmod 755 %_WIN32OPENSSL_BASENAME%.exe
echo %_CMD%
call %_CMD%
set _RC=%errorlevel%
if not "%_RC%"=="0" goto error1

echo %myname%: ACL permissions of %_WIN32OPENSSL_BASENAME%.exe:
icacls %_WIN32OPENSSL_BASENAME%.exe

:: The installer has a GUI which is suppressed by /silent /verysilent
set _CMD=%_WIN32OPENSSL_BASENAME%.exe /silent /verysilent /suppressmsgboxes /dir="%_WIN32OPENSSL_INSTALL_DIR%"
echo %_CMD%
call %_CMD%
set _RC=%errorlevel%
if not "%_RC%"=="0" goto error1

echo %myname%: Done installing Win32OpenSSL
:done_winopenssl

pip show M2Crypto >nul 2>nul
if %errorlevel%==0 (
    echo %myname%: Python package M2Crypto is already installed ... skipping
    goto done_m2crypto
)

set _M2CRYPTO_VERSION=0.31.0
echo %myname%: Installing Python package M2Crypto version %_M2CRYPTO_VERSION% ...

set _CMD=pip download M2Crypto==%_M2CRYPTO_VERSION%
echo %_CMD%
call %_CMD%
set _RC=%errorlevel%
if not "%_RC%"=="0" goto error1

set _CMD=tar -xz -f M2Crypto-%_M2CRYPTO_VERSION%.tar.gz
echo %_CMD%
call %_CMD%
set _RC=%errorlevel%
if not "%_RC%"=="0" goto error1

pushd M2Crypto-%_M2CRYPTO_VERSION%

set _CMD=python setup.py build --openssl=%_WIN32OPENSSL_INSTALL_DIR%
echo %_CMD%
call %_CMD%
set _RC=%errorlevel%
if not "%_RC%"=="0" goto error2

set _CMD=python setup.py bdist_wheel
echo %_CMD%
call %_CMD%
set _RC=%errorlevel%
if not "%_RC%"=="0" goto error2

echo %myname%: Files in dist:
dir dist

if %PYTHON_ARCH%==32 (
    set _ARCH_SUFFIX=win32
) else (
    set _ARCH_SUFFIX=win_amd64
)
for %%i in (dist\M2Crypto-%_M2CRYPTO_VERSION%-*.whl) do set _M2CRYPTO_WHEEL=%%i

echo %myname%: File path of wheel archive:
echo %_M2CRYPTO_WHEEL%

set _CMD=pip install %_M2CRYPTO_WHEEL%
echo %_CMD%
call %_CMD%
set _RC=%errorlevel%
if not "%_RC%"=="0" goto error2

popd

echo %myname%: Done installing Python package M2Crypto
:done_m2crypto

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
