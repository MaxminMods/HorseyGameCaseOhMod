param(
    [string]$Version = "v1.6.1",
    [string]$OutZip = ""
)
$ErrorActionPreference = "Stop"
$root = Get-Location
$temp = Join-Path $env:TEMP "CaseOh90000_release_build"
if (Test-Path $temp) { Remove-Item $temp -Recurse -Force }
New-Item -ItemType Directory -Path $temp | Out-Null
if ([string]::IsNullOrWhiteSpace($OutZip)) {
    $OutZip = "CaseOh90000_$Version.zip"
}

$excludeDirs = @(".git", "__pycache__", ".pytest_cache", ".venv", "venv", "env", "tests", "build", "dist", "Horsey Game", "save", "data", "sound")
$excludeFiles = @("*.pyc", "*.pyo", "*.zip", "*.dat", "*.prev", "*.bak", "*.log", "*.tmp", "settings.xml", "Horsey.exe", "steam_appid.txt", "CaseOh90000_paths.json", "caseoh90000_config.json", "scan_profile_from_configured_install.json", "scan_profile_from_your_install.json")

Get-ChildItem -Path $root -Force | ForEach-Object {
    if ($excludeDirs -contains $_.Name) { return }
    if ($_.PSIsContainer -and ($_.Name -like "CaseOh90000_BRANCH*" -or $_.Name -like "*CaseOh90000*BRANCH*")) { return }
    $skip = $false
    foreach ($pat in $excludeFiles) { if ($_.Name -like $pat) { $skip = $true } }
    if ($skip) { return }
    Copy-Item $_.FullName -Destination $temp -Recurse -Force
}

if (Test-Path $OutZip) { Remove-Item $OutZip -Force }
Compress-Archive -Path (Join-Path $temp "*") -DestinationPath $OutZip -Force
Write-Host "Built release zip: $OutZip"
