param(
    [switch]$SkipDependencyInstall,
    [switch]$InstallOptionalBackends,
    [switch]$AutoInstallPython
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $RepoRoot ".venv-win"
$CoreRequirementsPath = Join-Path $RepoRoot "requirements-windows-core.txt"
$OptionalRequirementsPath = Join-Path $RepoRoot "requirements-windows-optional.txt"
$InstallLogPath = Join-Path $env:TEMP "shadow-ai-windows-install.log"

function Write-Status {
    param(
        [string]$Message,
        [ConsoleColor]$Color = [ConsoleColor]::Gray
    )

    $timestamped = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Write-Host $Message -ForegroundColor $Color
    Add-Content -LiteralPath $InstallLogPath -Value $timestamped
}

Set-Content -LiteralPath $InstallLogPath -Value ("[{0}] Shadow AI Windows install started." -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))

function Invoke-Python {
    param(
        [string[]]$PythonCommand,
        [string[]]$Arguments
    )

    if ($PythonCommand.Length -gt 1) {
        & $PythonCommand[0] @($PythonCommand[1..($PythonCommand.Length - 1)]) @Arguments
        return
    }

    & $PythonCommand[0] @Arguments
}

function Refresh-ProcessPath {
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machinePath;$userPath"
}

function Test-IsWindowsStoreAlias {
    param(
        [string]$CommandPath
    )

    if (-not $CommandPath) {
        return $false
    }

    $normalized = $CommandPath.ToLowerInvariant()
    return $normalized -like "*\\microsoft\\windowsapps\\python.exe"
}

function Install-PythonWithWinget {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "Python 3.10+ was not found, and winget is not available for automatic install."
    }

    Write-Host "Python 3.11 was not found. Installing it with winget..." -ForegroundColor Yellow
    & winget install --id Python.Python.3.11 -e --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "Automatic Python install failed. Install Python 3.10+ manually, then rerun install_windows.ps1."
    }

    Refresh-ProcessPath
    Start-Sleep -Seconds 2
}

function Get-PythonCommand {
    $pyCommand = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCommand) {
        return @($pyCommand.Source, "-3")
    }

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand -and -not (Test-IsWindowsStoreAlias -CommandPath $pythonCommand.Source)) {
        return @($pythonCommand.Source)
    }

    throw "Python 3.10+ was not found."
}

try {
    $PythonCommand = Get-PythonCommand
} catch {
    if ($AutoInstallPython) {
        Write-Status "Python 3.10+ was not found. Trying winget-based Python install..." Yellow
        Install-PythonWithWinget
        $PythonCommand = Get-PythonCommand
    } else {
        Add-Content -LiteralPath $InstallLogPath -Value ("[{0}] ERROR: Python 3.10+ was not found." -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
        throw "Python 3.10+ was not found. Rerun with -AutoInstallPython or install Python manually."
    }
}

Write-Status "Installing Shadow AI for Windows..." Cyan
Write-Status ("Using Python command: {0}" -f ($PythonCommand -join " ")) DarkGray
Write-Status ("Install log: {0}" -f $InstallLogPath) DarkGray

if (-not (Test-Path -LiteralPath $VenvDir)) {
    Write-Status "Creating .venv-win..." Yellow
    Invoke-Python -PythonCommand $PythonCommand -Arguments @("-m", "venv", $VenvDir)
    Write-Status ".venv-win created." DarkGray
}

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $VenvPython)) {
    Add-Content -LiteralPath $InstallLogPath -Value ("[{0}] ERROR: Virtual environment python was not created correctly." -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
    throw "Virtual environment python was not created correctly."
}

if (-not $SkipDependencyInstall) {
    Write-Status "Upgrading pip/setuptools/wheel..." Yellow
    & $VenvPython -m pip install --upgrade pip setuptools wheel

    Write-Status "Installing core Windows runtime dependencies. This can take a few minutes on first run..." Yellow
    & $VenvPython -m pip install -r $CoreRequirementsPath
    Write-Status "Core Windows runtime dependencies installed." DarkGray

    if ($InstallOptionalBackends) {
        try {
            Write-Status "Installing optional Windows backends..." Yellow
            & $VenvPython -m pip install -r $OptionalRequirementsPath
            Write-Status "Optional Windows backends installed." DarkGray
        } catch {
            Add-Content -LiteralPath $InstallLogPath -Value ("[{0}] WARNING: Optional backend install failed." -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
            Write-Warning "Optional backend install failed. Shadow core will still run, but GGUF support may need manual llama-cpp-python setup later."
        }
    } else {
        Write-Status "Skipping optional GGUF backend install for the thin Windows setup." DarkYellow
    }
} else {
    Write-Status "Skipping dependency install as requested." Yellow
}

Write-Host ""
Write-Status "Shadow AI is ready." Green
Write-Status "Core runtime installed from: $CoreRequirementsPath"
if ($InstallOptionalBackends) {
    Write-Status "Optional backends requested from: $OptionalRequirementsPath"
} else {
    Write-Status "Optional GGUF backend was left out of the default Windows install."
}
Write-Status "Run: .\run_windows.bat"
