@echo off
setlocal

set "REPO_ROOT=%~dp0"
set "VENV_PYTHON=%REPO_ROOT%.venv-win\Scripts\python.exe"
set "BOOTSTRAP_LOG=%TEMP%\shadow-ai-windows-install.log"

if not exist "%VENV_PYTHON%" (
    echo Shadow AI is not installed yet. Running the Windows bootstrap first...
    echo First launch can take a few minutes while Python packages are installed.
    echo Bootstrap log: %BOOTSTRAP_LOG%
    powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO_ROOT%install_windows.ps1" -AutoInstallPython
    if errorlevel 1 (
        echo.
        echo Shadow AI bootstrap failed.
        echo Check this log for details: %BOOTSTRAP_LOG%
        exit /b %errorlevel%
    )
)

"%VENV_PYTHON%" "%REPO_ROOT%main.py" %*
