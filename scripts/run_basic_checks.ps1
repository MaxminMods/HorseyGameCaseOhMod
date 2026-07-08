$ErrorActionPreference = "Stop"
Write-Host "Running basic CaseOh90000 checks..."
$python = $null

function Test-PythonCommand {
    param([string[]]$CommandParts)
    if (-not $CommandParts -or -not $CommandParts[0]) {
        return $false
    }
    $exe = $CommandParts[0]
    $baseArgs = @()
    if ($CommandParts.Count -gt 1) {
        $baseArgs = $CommandParts[1..($CommandParts.Count - 1)]
    }
    $oldErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $exe @baseArgs -c "import sys; raise SystemExit(0 if sys.version_info.major >= 3 else 1)" *> $null
    $ErrorActionPreference = $oldErrorActionPreference
    return $LASTEXITCODE -eq 0
}

function Invoke-SelectedPython {
    param([string[]]$PythonArgs)
    $exe = $python[0]
    $baseArgs = @()
    if ($python.Count -gt 1) {
        $baseArgs = $python[1..($python.Count - 1)]
    }
    & $exe @baseArgs @PythonArgs
}

if ($env:PYTHON -and (Test-PythonCommand @($env:PYTHON))) {
    $python = @($env:PYTHON)
}
if ($null -eq $python -and (Get-Command py -ErrorAction SilentlyContinue) -and (Test-PythonCommand @("py", "-3"))) {
    $python = @("py", "-3")
}
if ($null -eq $python -and (Get-Command python -ErrorAction SilentlyContinue) -and (Test-PythonCommand @("python"))) {
    $python = @("python")
}
if ($null -eq $python) {
    throw "Python 3 was not found. Install Python 3, or set the PYTHON environment variable to python.exe."
}
$compileScript = @"
from pathlib import Path
files = sorted(Path(".").glob("*.py"))
if not files:
    raise SystemExit("No Python files found to compile.")
for path in files:
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
print(f"Checked {len(files)} Python files.")
"@
$compileScript | Invoke-SelectedPython @("-B", "-")
Write-Host "Python compile check passed."
if (Test-Path ".\tests\01_RUN_V20_FAST_TESTS.bat") {
    .\tests\01_RUN_V20_FAST_TESTS.bat
} else {
    Write-Host "No fast test BAT found. Compile check only."
}
