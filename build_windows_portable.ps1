param(
    [string]$Version = "v1.00"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$DistRoot = Join-Path $RepoRoot "dist"
$StageDir = Join-Path $DistRoot "shadow-ai-windows-$Version"
$ZipPath = Join-Path $DistRoot "shadow-ai-windows-$Version-portable.zip"
$TinyLmRoot = Join-Path (Split-Path $RepoRoot -Parent) "Shadow training"
$TinyLmModel = Join-Path $TinyLmRoot "shadow_tiny_lm.pt"
$TinyLmTokenizer = Join-Path $TinyLmRoot "tokenizer_metadata.json"

$excludeDirs = @(
    ".git",
    ".venv",
    ".venv-win",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "build",
    "debian-package",
    "dist",
    "docs",
    "tests",
    "training",
    "windows"
)

$excludePathFragments = @(
    "debian-package\shadow-ai-2.0.1",
    "debian-package\shadow-ai-2.0.2",
    "debian-package\shadow-ai-2.0.35",
    "debian-package\shadow-ai-2.0.36",
    "debian-package\shadow-ai-2.50",
    "training\runtime_",
    "Shadow training\output"
)

$excludeFiles = @(
    "_tmp_sils_eval_smoke.json",
    "build_windows_portable.ps1",
    "build_windows_release.ps1",
    "build_windows_thin_release.ps1",
    "COMPLETION_SUMMARY.md",
    "CONTRIBUTING.md",
    "deploy_v2.0.2.sh",
    "DOCUMENTATION_INDEX.md",
    "ENHANCED_LEARNING.md",
    "FIXES.md",
    "GITHUB_RELEASE_CHECKLIST.md",
    "memory.json",
    "QUICK_REFERENCE.md",
    "RELEASE_NOTES_v2.0.35.md",
    "RELEASE_NOTES_v2.0.36.md",
    "RELEASE_NOTES_v2.50.md",
    "RELEASE_NOTES_v2.75.md",
    "ROADMAP_v2.0.3.md",
    "shadow-ai-2.0.35.deb",
    "shadow-ai-2.0.36.deb",
    "ship_it.py",
    "SUMMARY.md",
    "test_fixes.py"
)

function Should-SkipPath {
    param([System.IO.FileSystemInfo]$Item)

    foreach ($name in $excludeDirs) {
        if ($Item.Name -ieq $name) {
            return $true
        }
    }

    foreach ($fragment in $excludePathFragments) {
        if ($Item.FullName -like "*$fragment*") {
            return $true
        }
    }

    if ($Item.PSIsContainer) {
        return $false
    }

    foreach ($name in $excludeFiles) {
        if ($Item.Name -ieq $name) {
            return $true
        }
    }

    if ($Item.Extension -ieq ".md" -and $Item.Name -ine "README.md") {
        return $true
    }

    if ($Item.Extension -in @(".deb", ".pyc", ".pyo", ".pyd")) {
        return $true
    }

    return $false
}

function Copy-ShadowItem {
    param(
        [System.IO.FileSystemInfo]$Item,
        [string]$DestinationRoot
    )

    if (Should-SkipPath -Item $Item) {
        return
    }

    $destination = Join-Path $DestinationRoot $Item.Name
    if ($Item.PSIsContainer) {
        New-Item -ItemType Directory -Path $destination -Force | Out-Null
        foreach ($child in Get-ChildItem -LiteralPath $Item.FullName -Force) {
            Copy-ShadowItem -Item $child -DestinationRoot $destination
        }
        return
    }

    Copy-Item -LiteralPath $Item.FullName -Destination $destination -Force
}

Write-Host "Building Shadow AI Windows portable package..." -ForegroundColor Cyan

if (Test-Path -LiteralPath $StageDir) {
    Remove-Item -LiteralPath $StageDir -Recurse -Force
}
if (Test-Path -LiteralPath $ZipPath) {
    Remove-Item -LiteralPath $ZipPath -Force
}
New-Item -ItemType Directory -Path $StageDir | Out-Null

$items = Get-ChildItem -LiteralPath $RepoRoot -Force
foreach ($item in $items) {
    Copy-ShadowItem -Item $item -DestinationRoot $StageDir
}

$trainingDir = Join-Path $StageDir "training"
New-Item -ItemType Directory -Path $trainingDir -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $RepoRoot "training\tokenizer.py") -Destination (Join-Path $trainingDir "tokenizer.py") -Force

$modelsDir = Join-Path $StageDir "models"
New-Item -ItemType Directory -Path $modelsDir -Force | Out-Null
if (Test-Path -LiteralPath $TinyLmModel) {
    Copy-Item -LiteralPath $TinyLmModel -Destination (Join-Path $modelsDir "shadow_tiny_lm.pt") -Force
}
if (Test-Path -LiteralPath $TinyLmTokenizer) {
    Copy-Item -LiteralPath $TinyLmTokenizer -Destination (Join-Path $modelsDir "tokenizer_metadata.json") -Force
}

Compress-Archive -Path (Join-Path $StageDir "*") -DestinationPath $ZipPath -Force

Write-Host "Done." -ForegroundColor Green
Write-Host "Folder: $StageDir"
Write-Host "Zip:    $ZipPath"
