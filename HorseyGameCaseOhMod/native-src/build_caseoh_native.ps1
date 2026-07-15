$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$source = Join-Path $PSScriptRoot "CaseOhArenaNative.cpp"
$outDir = Join-Path $root "native"
$outDll = Join-Path $outDir "HorseyGameArenaNative.dll"
$objDir = Join-Path $PSScriptRoot "obj"
$objFile = Join-Path $objDir "CaseOhArenaNative.obj"

if (!(Test-Path -LiteralPath $source)) {
    throw "Missing CaseOh native source: $source"
}

New-Item -ItemType Directory -Force -Path $outDir | Out-Null
New-Item -ItemType Directory -Force -Path $objDir | Out-Null

$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (!(Test-Path -LiteralPath $vswhere)) {
    throw "Could not find vswhere.exe. Install Visual Studio Build Tools or Visual Studio Community with C++ build tools."
}

$vsRoot = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (!$vsRoot) {
    throw "Could not find Visual Studio C++ build tools."
}

$devCmd = Join-Path $vsRoot "Common7\Tools\VsDevCmd.bat"
if (!(Test-Path -LiteralPath $devCmd)) {
    throw "Could not find VsDevCmd.bat at $devCmd"
}

$rsp = Join-Path $objDir "caseoh_native.rsp"
@"
/nologo
/std:c++17
/EHsc
/O2
/MD
/LD
/DNDEBUG
/Fe:"$outDll"
/Fo"$objFile"
"$source"
user32.lib
gdi32.lib
winmm.lib
psapi.lib
/link
/INCREMENTAL:NO
/DEBUG:NONE
"@ | Set-Content -LiteralPath $rsp -Encoding ASCII

$compile = "call `"$devCmd`" -arch=x64 -host_arch=x64 >nul && cl @`"$rsp`""
cmd.exe /d /s /c $compile
if ($LASTEXITCODE -ne 0) {
    throw "CaseOh native build failed."
}

$bytes = [System.IO.File]::ReadAllBytes($outDll)
$unicode = [System.Text.Encoding]::Unicode.GetString($bytes)
$ascii = [System.Text.Encoding]::ASCII.GetString($bytes)
$banned = @(
    ("F" + "7"),
    ("F" + "8 HUD"),
    ("Online " + "0/5"),
    ("Save " + "to Room"),
    ("Room " + "chat"),
    ("Host " + "feed"),
    ("Arena " + "server"),
    ("Ready" + ": Yes"),
    ("Horsey" + "Multiplayer")
)

$hits = foreach ($pattern in $banned) {
    if ($unicode.Contains($pattern) -or $ascii.Contains($pattern)) {
        $pattern
    }
}

if ($hits) {
    throw "Built DLL still contains banned multiplayer text: $($hits -join ', ')"
}

Write-Host "Built clean CaseOh native timer DLL:"
Write-Host $outDll
