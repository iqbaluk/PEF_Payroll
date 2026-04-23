Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "Installing build dependencies..."
python -m pip install --upgrade pip
python -m pip install pyinstaller

Write-Host "Cleaning previous builds..."
if (Test-Path -LiteralPath ".\build") { Remove-Item -LiteralPath ".\build" -Recurse -Force }
if (Test-Path -LiteralPath ".\dist") { Remove-Item -LiteralPath ".\dist" -Recurse -Force }

Write-Host "Building desktop executable..."
python -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --onedir `
  --name "PEF_Payroll" `
  --add-data "templates;templates" `
  --add-data "static;static" `
  .\desktop_launcher.py

Write-Host "Running packaged self-test..."
& ".\dist\PEF_Payroll\PEF_Payroll.exe" --self-test
if ($LASTEXITCODE -ne 0) {
  throw "Packaged self-test failed with exit code $LASTEXITCODE"
}

Write-Host "Compiling installer..."
$iscc = (Get-Command iscc -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)
if (-not $iscc) {
  $fallback = ".\tools\InnoSetup\ISCC.exe"
  if (Test-Path -LiteralPath $fallback) {
    $iscc = (Resolve-Path $fallback).Path
  } else {
    throw "Inno Setup Compiler (iscc) not found. Install Inno Setup and run again."
  }
}

& $iscc ".\installer.iss"
if ($LASTEXITCODE -ne 0) {
  throw "Installer compilation failed with exit code $LASTEXITCODE"
}

Write-Host "Done. Installer is in .\dist-installer"
