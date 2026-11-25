@echo off
rem Builds whisper.cpp (official source in src\) with Vulkan for the AMD GPU; output in bin\
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
for /d %%D in (C:\VulkanSDK\*) do set "VULKAN_SDK=%%D"
set "PATH=%~dp0buildenv\Scripts;%VULKAN_SDK%\Bin;%PATH%"
cmake -S "%~dp0src" -B "%~dp0build" -G Ninja -DCMAKE_BUILD_TYPE=Release -DGGML_VULKAN=ON -DWHISPER_BUILD_TESTS=OFF -DWHISPER_BUILD_EXAMPLES=ON -DWHISPER_BUILD_SERVER=ON || exit /b 1
cmake --build "%~dp0build" --config Release -j 8 --target whisper-server whisper-cli || exit /b 1
if not exist "%~dp0bin" mkdir "%~dp0bin"
copy /y "%~dp0build\bin\*.exe" "%~dp0bin\" >nul
copy /y "%~dp0build\bin\*.dll" "%~dp0bin\" >nul
echo BUILD OK
