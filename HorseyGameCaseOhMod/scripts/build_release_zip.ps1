param(
    [string]$Version = "v2",
    [string]$OutZip = ""
)
$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$appSource = Resolve-Path (Join-Path $repoRoot "HorseyGameCaseOhMod")
$temp = Join-Path $env:TEMP "CaseOh90000_release_build"
$resolvedTempParent = [System.IO.Path]::GetFullPath($env:TEMP).TrimEnd('\')
$resolvedTemp = [System.IO.Path]::GetFullPath($temp).TrimEnd('\')
if ($resolvedTemp -ne (Join-Path $resolvedTempParent "CaseOh90000_release_build")) {
    throw "Refusing to clear unexpected release temp folder: $resolvedTemp"
}
if (Test-Path $resolvedTemp) { Remove-Item -LiteralPath $resolvedTemp -Recurse -Force }
New-Item -ItemType Directory -Path $temp | Out-Null
if ([string]::IsNullOrWhiteSpace($OutZip)) {
    $OutZip = "HorseyGameCaseOhMod_$Version.zip"
}

$appDirName = "HorseyGameCaseOhMod"
$appDir = Join-Path $temp $appDirName
New-Item -ItemType Directory -Path $appDir | Out-Null

$excludeDirs = @(".git", "__pycache__", ".pytest_cache", ".venv", "venv", "env", "tests", "build", "dist", "Horsey Game", "save", "data", "sound")
$excludeFiles = @("*.pyc", "*.pyo", "*.zip", "*.dat", "*.prev", "*.bak", "*.log", "*.tmp", "settings.xml", "Horsey.exe", "steam_appid.txt", "CaseOh90000_paths.json", "caseoh90000_config.json", "scan_profile_from_configured_install.json", "scan_profile_from_your_install.json", "README.md")

Get-ChildItem -Path $appSource -Force | ForEach-Object {
    if ($excludeDirs -contains $_.Name) { return }
    if ($_.PSIsContainer -and ($_.Name -like "CaseOh90000_BRANCH*" -or $_.Name -like "*CaseOh90000*BRANCH*")) { return }
    $skip = $false
    foreach ($pat in $excludeFiles) { if ($_.Name -like $pat) { $skip = $true } }
    if ($skip) { return }
    Copy-Item $_.FullName -Destination $appDir -Recurse -Force
}

$internalDocs = Join-Path $appDir "docs\codex"
if (Test-Path $internalDocs) {
    $resolvedInternalDocs = [System.IO.Path]::GetFullPath($internalDocs)
    $resolvedAppDir = [System.IO.Path]::GetFullPath($appDir).TrimEnd('\') + '\'
    if (-not $resolvedInternalDocs.StartsWith($resolvedAppDir, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to clear unexpected internal docs folder: $resolvedInternalDocs"
    }
    Remove-Item -LiteralPath $resolvedInternalDocs -Recurse -Force
}

Copy-Item (Join-Path $repoRoot "README.md") -Destination (Join-Path $temp "README.md") -Force
Copy-Item (Join-Path $repoRoot "00_START_HERE_CaseOh90000.bat") -Destination (Join-Path $temp "00_START_HERE_CaseOh90000.bat") -Force
Copy-Item (Join-Path $repoRoot "01_LAUNCH_PANEL_CaseOh90000.bat") -Destination (Join-Path $temp "01_LAUNCH_PANEL_CaseOh90000.bat") -Force

if (Test-Path $OutZip) { Remove-Item $OutZip -Force }
Compress-Archive -Path (Join-Path $temp "*") -DestinationPath $OutZip -Force
Write-Host "Built release zip: $OutZip"
Write-Host "Zip root contains README.md, 00_START_HERE_CaseOh90000.bat, and 01_LAUNCH_PANEL_CaseOh90000.bat. App files are inside $appDirName/."
