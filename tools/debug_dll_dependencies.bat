rem This script is supposed to run on the Appveyor CI.
echo on
echo "debug_dll_dependencies: start"
set PATH=%PATH%;C:\Program Files (x86)\Microsoft Visual Studio 14.0\VC\bin
where dumpbin
dir /s /b .tox\pywin  | grep -E "\.(pyd|dll)$" | sed -e 's!\\\\!/!g' >py_bin.fl
dir /s /b C:\Python26 | grep -E "\.(pyd|dll)$" | sed -e 's!\\\\!/!g' >>py_bin.fl
cat py_bin.fl
cat py_bin.fl | xargs -n 1 dumpbin /dependents 
echo "debug_dll_dependencies: end"
