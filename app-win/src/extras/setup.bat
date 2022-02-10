@echo off
:: Copied from the link below
::::::::::::::::::::::::::::::::::::::::::::
:: Elevate.cmd - Version 4
:: Automatically check & get admin rights
:: see "https://stackoverflow.com/a/12264592/1016343" for description
::::::::::::::::::::::::::::::::::::::::::::
 @echo off
 CLS
 ECHO.
 ECHO =============================
 ECHO Running Admin shell
 ECHO =============================

:init
 setlocal DisableDelayedExpansion
 set cmdInvoke=1
 set winSysFolder=System32
 set "batchPath=%~0"
 for %%k in (%0) do set batchName=%%~nk
 set "vbsGetPrivileges=%temp%\OEgetPriv_%batchName%.vbs"
 setlocal EnableDelayedExpansion

:checkPrivileges
  NET FILE 1>NUL 2>NUL
  if '%errorlevel%' == '0' ( goto gotPrivileges ) else ( goto getPrivileges )

:getPrivileges
  if '%1'=='ELEV' (echo ELEV & shift /1 & goto gotPrivileges)
  ECHO.
  ECHO **************************************
  ECHO Invoking UAC for Privilege Escalation
  ECHO **************************************

  ECHO Set UAC = CreateObject^("Shell.Application"^) > "%vbsGetPrivileges%"
  ECHO args = "ELEV " >> "%vbsGetPrivileges%"
  ECHO For Each strArg in WScript.Arguments >> "%vbsGetPrivileges%"
  ECHO args = args ^& strArg ^& " "  >> "%vbsGetPrivileges%"
  ECHO Next >> "%vbsGetPrivileges%"

  if '%cmdInvoke%'=='1' goto InvokeCmd 

  ECHO UAC.ShellExecute "!batchPath!", args, "", "runas", 1 >> "%vbsGetPrivileges%"
  goto ExecElevation

:InvokeCmd
  ECHO args = "/c """ + "!batchPath!" + """ " + args >> "%vbsGetPrivileges%"
  ECHO UAC.ShellExecute "%SystemRoot%\%winSysFolder%\cmd.exe", args, "", "runas", 1 >> "%vbsGetPrivileges%"

:ExecElevation
 "%SystemRoot%\%winSysFolder%\WScript.exe" "%vbsGetPrivileges%" %*
 exit /B

:gotPrivileges
 setlocal & cd /d %~dp0
 if '%1'=='ELEV' (del "%vbsGetPrivileges%" 1>nul 2>nul  &  shift /1)

 ::::::::::::::::::::::::::::
 ::START
 ::::::::::::::::::::::::::::
 REM Run shell as admin (example) - put here code as you like
 echo "==> Killing running cassowary instance"
 taskkill /im cassowary.exe /f
 echo "==> Copying files to Program Files directory"
 Xcopy /E /I /Y cassowary "C:\Program Files\cassowary"
 echo "==> Copying no console script and hostopen.bat"
 Xcopy /I /Y cassowary_nw.vbs "C:\Program Files\cassowary\"
 Xcopy /I /Y nowindow.vbs "C:\Program Files\cassowary\"
 Xcopy /I /Y hostopen.bat "C:\Program Files\cassowary\"
 echo "==> Importing registry keys"
 reg import setup.reg
 echo "==> Setting up path variables"
 SETX /M PATH "%PATH%;C:\Program Files\cassowary\"
 echo "==> Creating scheduled task to run server after logon"
 schtasks /Create /XML cassowary-server.xml /tn cassowary-server /f
 echo "==> Allowing cassowary and RDP connection through firewall"
 netsh advfirewall firewall add rule name="Cassowary Server" dir=in action=allow program="C:\Program Files\cassowary\cassowary.exe" enable=yes
 netsh advfirewall firewall set rule group="remote desktop" new enable=Yes
 echo " ==> Setup complete, press any key to exit .... Restart for all changes to take place !"
 pause
