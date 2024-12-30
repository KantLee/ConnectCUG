
@echo off
cd /d "%~dp0"
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if %errorlevel% neq 0 (
    goto UACPrompt
) else (
    goto :runScript
)

:UACPrompt
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\runAsAdmin.vbs"
    echo UAC.ShellExecute "%~s0", "", "", "runas", 1 >> "%temp%\runAsAdmin.vbs"

    "%temp%\runAsAdmin.vbs"
    del "%temp%\runAsAdmin.vbs"
    exit /B

:runScript
    start G:\PyProjects\git_synchro\ConnectCUG\ConnectCUG.exe
    