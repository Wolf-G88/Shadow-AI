param(
    [string]$Version = "v1.00",
    [switch]$SkipInstaller
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $RepoRoot ".venv-win\Scripts\python.exe"
$SpecPath = Join-Path $RepoRoot "windows\ShadowAI.spec"
$DistRoot = Join-Path $RepoRoot "dist"
$BuildRoot = Join-Path $RepoRoot "build"
$InnoScript = Join-Path $RepoRoot "windows\ShadowAI.iss"

function Get-InnoCompiler {
    $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $localPrograms = Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"
    if (Test-Path -LiteralPath $localPrograms) {
        return $localPrograms
    }

    return $null
}

if (-not (Test-Path -LiteralPath $VenvPython)) {
    throw ".venv-win is missing. Run install_windows.ps1 first."
}

if (-not (Test-Path -LiteralPath $SpecPath)) {
    throw "PyInstaller spec not found: $SpecPath"
}

Write-Host "Ensuring PyInstaller is installed..." -ForegroundColor Cyan
& $VenvPython -m pip install pyinstaller

if (Test-Path -LiteralPath (Join-Path $DistRoot "ShadowAI")) {
    Remove-Item -LiteralPath (Join-Path $DistRoot "ShadowAI") -Recurse -Force
}
if (Test-Path -LiteralPath $BuildRoot) {
    Remove-Item -LiteralPath $BuildRoot -Recurse -Force
}

Write-Host "Building Shadow AI app bundle..." -ForegroundColor Cyan
& $VenvPython -m PyInstaller --noconfirm --clean $SpecPath

if (-not $SkipInstaller) {
    $iscc = Get-InnoCompiler
    if (-not $iscc) {
        throw "ISCC.exe was not found. Install Inno Setup or rerun with -SkipInstaller."
    }

    Write-Host "Building Shadow AI installer..." -ForegroundColor Cyan
    & $iscc $InnoScript
}

Write-Host "Windows release build complete." -ForegroundColor Green
