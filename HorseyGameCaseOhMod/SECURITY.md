# Security and Safety Notes

HorseyGameCaseOhMod is designed to run in a separate CaseOh parallel dimension. The normal Steam install and normal save should not be modified by normal use.

## Never Commit

Do not commit or publish:

- `Horsey.exe`
- copied Horsey Game folders
- copied `data/`, `save/`, or `sound/` folders
- `save*.dat`, `*.dat.prev`, or personal save files
- generated CaseOh90000 dimension folders
- local config files containing personal paths, such as `CaseOh90000_paths.json`
- logs, temporary files, Python caches, or release zips
- PDB/debug files or local build artifacts

The bundled `native/HorseyGameArenaNative.dll` is the branch-side timer runtime and is allowed in releases. Rebuild it from `native-src/build_caseoh_native.ps1`.

## Privacy

The panel hides full folder paths by default for stream privacy. First-time setup still asks for folders in a console window, so avoid running first-time setup live on stream unless you are comfortable showing those paths.

## Release Check

Before publishing a release, confirm that the zip opens to:

```text
README.md
00_START_HERE_CaseOh90000.bat
01_LAUNCH_PANEL_CaseOh90000.bat
02_PLAY_CASEOH_HORSEY.bat
HorseyGameCaseOhMod/
```

The zip should not contain copied game files, save files, local CaseOh dimension folders, logs, caches, or local path config files.
