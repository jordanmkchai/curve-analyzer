param(
    [string]$Version = "1.0.0"
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$ReleaseDir = Join-Path $Root "release"
$DistDir = Join-Path $Root "dist"
$BuildDir = Join-Path $Root "build"
$Spec = Join-Path $Root "curve_analyzer.spec"
$AppDist = Join-Path $DistDir "Curve Analyzer"
$ZipPath = Join-Path $ReleaseDir "Curve_Analyzer_Portable_v$Version.zip"

if (!(Test-Path -LiteralPath $Python)) {
    Write-Host "Creating virtual environment..."
    Push-Location $Root
    try {
        py -3.13 -m venv .venv
    }
    finally {
        Pop-Location
    }
}

New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null

Write-Host "Installing/updating build dependencies..."
& $Python -m pip install --upgrade pip
& $Python -m pip install -r (Join-Path $Root "requirements.txt")
& $Python -m pip install pyinstaller

Write-Host "Cleaning old build outputs..."
Remove-Item -LiteralPath $BuildDir -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $AppDist -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $ZipPath -Force -ErrorAction SilentlyContinue

Write-Host "Building application with PyInstaller..."
Push-Location $Root
try {
    & $Python -m PyInstaller --noconfirm --clean $Spec
}
finally {
    Pop-Location
}

$ExePath = Join-Path $AppDist "Curve Analyzer.exe"
if (!(Test-Path -LiteralPath $ExePath)) {
    throw "Build failed: executable not found in $AppDist"
}

Write-Host "Creating portable zip..."
Compress-Archive -Path (Join-Path $AppDist "*") -DestinationPath $ZipPath -Force
Write-Host "Portable zip: $ZipPath"
Write-Host "Release build complete."
