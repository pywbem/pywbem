@setlocal enableextensions
@echo off
set errorlevel=

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

echo Current Python is: Version %PYTHON_M_VERSION%,  %PYTHON_ARCH%-bit

if "%1"=="" goto do_install
if "%1"=="install" goto do_install
if "%1"=="develop" goto do_develop
echo Usage: pywbem_os_setup.bat [develop / install]
goto end

:do_install

echo Installing OS-level prerequisite packages for install on platform Windows ...

if not exist ..\tmp_pywbem_os_setup mkdir ..\tmp_pywbem_os_setup
pushd ..\tmp_pywbem_os_setup

if not %PYTHON_M_VERSION%==2 goto install_no_py2

where swig >nul
if %errorlevel%==0 (
    echo Swig is already installed ... skipping
    goto done_swig
)

echo Installing Swig ...

:: The following installation of swig installs swig but without generating
:: the swig.exe shim file (using GenShim).
:: See GenShim issue https://github.com/chocolatey/shimgen/issues/43
:: Therefore, we install swig in appveyor.yml in order to create the swig.exe
:: shim file.
:: We install it here again for users of pywbem.
:: TODO: Remove the circumvention once it works in pywbem_os_setup.bat.

set _CMD=choco install -y swig
echo %_CMD%
%_CMD%
set _RC=%errorlevel%
if not "%_RC%"=="0" echo Warning: choco returned rc=%_RC%

set _CMD=where swig
echo %_CMD%
%_CMD%
set _RC=%errorlevel%
if not "%_RC%"=="0" goto error1

echo Done installing Swig
:done_swig

:: The bit size of Win32/64OpenSSL must match the bit size of the Python env.
set _WINOPENSSL_BITSIZE=%PYTHON_ARCH%
set _WINOPENSSL_BASENAME=Win%_WINOPENSSL_BITSIZE%OpenSSL-1_1_0i
set _WINOPENSSL_INSTALL_DIR=C:\OpenSSL-1-1-0i-Win%_WINOPENSSL_BITSIZE%
if exist %_WINOPENSSL_INSTALL_DIR% (
    echo %_WINOPENSSL_BASENAME% is already installed in %_WINOPENSSL_INSTALL_DIR% ... skipping
    goto done_winopenssl
)

echo Installing %_WINOPENSSL_BASENAME% ...

set _CMD=curl -o %_WINOPENSSL_BASENAME%.exe -sSL https://slproweb.com/download/%_WINOPENSSL_BASENAME%.exe
echo %_CMD%
%_CMD%
set _RC=%errorlevel%
if not "%_RC%"=="0" goto error1

:: If the web site does not know the file, it returns a HTML page showing an error, and curl succeeds downloading that
set _CMD=grep "^<html>" %_WINOPENSSL_BASENAME%.exe
echo %_CMD%
%_CMD%
set _RC=%errorlevel%
if "%_RC%"=="0" (
    echo Error: The %_WINOPENSSL_BASENAME%.exe file does not exist on https://slproweb.com:
    cat %_WINOPENSSL_BASENAME%.exe
    rm %_WINOPENSSL_BASENAME%.exe
    set _RC=1
    goto error1
)

:: Downloaded files may not have the execution right.
set _CMD=chmod 755 %_WINOPENSSL_BASENAME%.exe
echo %_CMD%
%_CMD%
set _RC=%errorlevel%
if not "%_RC%"=="0" goto error1

:: The installer has a GUI which is suppressed by /silent /verysilent
set _CMD=%_WINOPENSSL_BASENAME%.exe /silent /verysilent /suppressmsgboxes /dir="%_WINOPENSSL_INSTALL_DIR%"
echo %_CMD%
%_CMD%
set _RC=%errorlevel%
if not "%_RC%"=="0" goto error1

echo Done installing %_WINOPENSSL_BASENAME%
:done_winopenssl

pip show M2Crypto >nul 2>nul
if %errorlevel%==0 (
    echo Python package M2Crypto is already installed ... skipping
    goto done_m2crypto
)

set _M2CRYPTO_VERSION=0.30.1
echo Installing Python package M2Crypto version %_M2CRYPTO_VERSION% ...

set _CMD=pip download M2Crypto==%_M2CRYPTO_VERSION%
echo %_CMD%
%_CMD%
set _RC=%errorlevel%
if not "%_RC%"=="0" goto error1

set _CMD=tar -xz -f M2Crypto-%_M2CRYPTO_VERSION%.tar.gz
echo %_CMD%
%_CMD%
set _RC=%errorlevel%
if not "%_RC%"=="0" goto error1

pushd M2Crypto-%_M2CRYPTO_VERSION%

set _CMD=python setup.py build --openssl=%_WINOPENSSL_INSTALL_DIR%
echo %_CMD%
%_CMD%
set _RC=%errorlevel%
if not "%_RC%"=="0" goto error2

set _CMD=python setup.py bdist_wheel
echo %_CMD%
%_CMD%
set _RC=%errorlevel%
if not "%_RC%"=="0" goto error2

echo Files in dist:
ls -l dist

if %PYTHON_ARCH%==32 (
    set _ARCH_SUFFIX=win32
) else (
    set _ARCH_SUFFIX=win_amd64
)
set _M2CRYPTO_WHEEL=dist/M2Crypto-%_M2CRYPTO_VERSION%-cp27-cp27m-%_ARCH_SUFFIX%.whl
echo Wheel archive:
ls -l %_M2CRYPTO_WHEEL%

set _CMD=pip install %_M2CRYPTO_WHEEL%
echo %_CMD%
%_CMD%
set _RC=%errorlevel%
if not "%_RC%"=="0" goto error2

popd

echo Done installing Python package M2Crypto
:done_m2crypto

:install_no_py2

popd
goto end

:do_develop

echo Installing OS-level prerequisite packages for develop on platform Windows ...

echo Warning: Package 'libxml2' must be installed manually.
goto end

:error2
popd
:error1
popd
:error
echo Error: Command returned rc=%_RC%
exit /b %_RC%

:end
endlocal
exit /b 0
