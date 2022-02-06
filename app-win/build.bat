@echo off
cd /D "%~dp0\src"
echo ==^> Using pyinstaller to make executable
python -m ensurepip
python -m pip install pyinstaller pywin32 icoextract
pyinstaller package.spec --noconfirm
echo ==^> Copying to setup directory
mkdir ..\bin
Xcopy /E /I /F /Y dist\cassowary ..\bin\cassowary
Xcopy /Y extras\* ..\bin\
cd ..\
echo ==^> Done...
