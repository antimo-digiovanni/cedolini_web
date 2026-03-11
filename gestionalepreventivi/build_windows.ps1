$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$python = Join-Path $projectRoot '..\.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    $python = 'python'
}

New-Item -ItemType Directory -Force -Path (Join-Path $projectRoot 'generated_pdfs') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $projectRoot 'generated_excels') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $projectRoot 'assets') | Out-Null

& $python -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name GestionalePreventivi `
  --add-data "generated_pdfs;generated_pdfs" `
  --add-data "generated_excels;generated_excels" `
  --add-data "assets;assets" `
  app.py
