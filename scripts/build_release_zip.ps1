param(
    [string]$Version = "v2",
    [string]$OutZip = ""
)
$ErrorActionPreference = "Stop"
$root = Get-Location
$temp = Join-Path $env:TEMP "CaseOh90000_release_build"
if (Test-Path $temp) { Remove-Item $temp -Recurse -Force }
New-Item -ItemType Directory -Path $temp | Out-Null
if ([string]::IsNullOrWhiteSpace($OutZip)) {
    $OutZip = "HorseyGameCaseOhMod_$Version.zip"
}

$appDirName = "HorseyGameCaseOhMod"
$appDir = Join-Path $temp $appDirName
New-Item -ItemType Directory -Path $appDir | Out-Null

$excludeDirs = @(".git", "__pycache__", ".pytest_cache", ".venv", "venv", "env", "tests", "build", "dist", "Horsey Game", "save", "data", "sound")
$excludeFiles = @("*.pyc", "*.pyo", "*.zip", "*.dat", "*.prev", "*.bak", "*.log", "*.tmp", "settings.xml", "Horsey.exe", "steam_appid.txt", "CaseOh90000_paths.json", "caseoh90000_config.json", "scan_profile_from_configured_install.json", "scan_profile_from_your_install.json", "README.md")

Get-ChildItem -Path $root -Force | ForEach-Object {
    if ($excludeDirs -contains $_.Name) { return }
    if ($_.PSIsContainer -and ($_.Name -like "CaseOh90000_BRANCH*" -or $_.Name -like "*CaseOh90000*BRANCH*")) { return }
    $skip = $false
    foreach ($pat in $excludeFiles) { if ($_.Name -like $pat) { $skip = $true } }
    if ($skip) { return }
    Copy-Item $_.FullName -Destination $appDir -Recurse -Force
}

Copy-Item (Join-Path $root "README.md") -Destination (Join-Path $temp "README.md") -Force

$startBat = @"
@echo off
setlocal
cd /d "%~dp0$appDirName"
if errorlevel 1 (
  echo Could not open the $appDirName folder.
  pause
  exit /b 1
)
where py >nul 2>nul
if errorlevel 1 (
  echo Python 3 was not found. Please install Python 3, then run this again.
  echo https://www.python.org/downloads/
  pause
  exit /b 1
)
py -3 setup_wizard.py setup --run
if errorlevel 1 pause
"@
Set-Content -Path (Join-Path $temp "00_START_HERE_CaseOh90000.bat") -Value $startBat -Encoding ASCII

if (Test-Path $OutZip) { Remove-Item $OutZip -Force }
Compress-Archive -Path (Join-Path $temp "*") -DestinationPath $OutZip -Force
Write-Host "Built release zip: $OutZip"
Write-Host "Zip root contains README.md and 00_START_HERE_CaseOh90000.bat. App files are inside $appDirName/."
