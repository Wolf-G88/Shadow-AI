param(
    [string]$Version = "v1.00"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PortableBuilder = Join-Path $RepoRoot "build_windows_portable.ps1"
$InnoScript = Join-Path $RepoRoot "windows\ShadowAIThin.iss"

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

if (-not (Test-Path -LiteralPath $PortableBuilder)) {
    throw "Portable builder not found: $PortableBuilder"
}

Write-Host "Building thin Windows Shadow package..." -ForegroundColor Cyan
powershell -ExecutionPolicy Bypass -File $PortableBuilder -Version $Version

$iscc = Get-InnoCompiler
if (-not $iscc) {
    throw "ISCC.exe was not found. Install Inno Setup first."
}

Write-Host "Building thin Windows installer..." -ForegroundColor Cyan
& $iscc $InnoScript

Write-Host "Thin Windows release build complete." -ForegroundColor Green
