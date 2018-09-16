@setlocal enableextensions
@echo off
rem Windows batch script that runs the run_uprint.py script in different
rem scenarios. If the tests succeed, this script exits with exit code 0.

set mydir=%~d0%~p0
set err_log=%mydir%test_uprint_err.log
set out_log=%mydir%test_uprint_out.log

call :run_test -         python %mydir%run_uprint.py small
call :run_test nul       python %mydir%run_uprint.py small
call :run_test %out_log% python %mydir%run_uprint.py small

call :run_test nul       python %mydir%run_uprint.py ucs2
call :run_test %out_log% python %mydir%run_uprint.py ucs2

call :run_test nul       python %mydir%run_uprint.py all
call :run_test %out_log% python %mydir%run_uprint.py all

endlocal
exit /b 0

:run_test
set out=%1
set cmd=%2 %3 %4 %5
if "%out%"=="-" (
  set cmd_out=%cmd%
) else (
  set cmd_out=%cmd% ^>%out%
)
echo Running: %cmd%    %out%
call %cmd_out% 2>%err_log%
set rc=%errorlevel%
if errorlevel 1 (
  echo Error: Test failed with rc=%rc% for: %cmd%    %out%
  echo === begin of stderr ===
  type %err_log%
  echo === end of stderr ===
  exit /b %rc%
) else (
  echo Success.
  echo Debug messages in this run:
  type %err_log%
)
exit /b 0
