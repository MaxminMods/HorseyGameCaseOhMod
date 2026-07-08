# AGENTS.md - CaseOh90000 / HorseyGameCaseOhMod

This repository contains **CaseOh90000**, a local safe-branch mod tool for Horsey Game.

## Hard Safety Rules

- Do not commit or include Horsey Game itself.
- Do not commit or include `Horsey.exe`, `data/`, `sound/`, `save/`, `save*.dat`, `settings.xml`, copied branch folders, or Steam files.
- Do not patch the user's normal Steam install directly.
- All game modifications must happen only inside a copied branch folder created by the tool.
- Keep streamer/privacy mode on by default when showing paths in UI.
- Keep `caseOh mOde` described only as `Easter Egg`; do not explain the behavior in UI, README, or release notes.
- Avoid adding extra "enable" checkboxes for controls unless there is a clear safety reason. Visible controls should do what they say.

## Product Goals

- Make SIM9000 experimentation easy for normal users.
- Keep the original Horsey install and normal save untouched.
- Keep the UI compact, clear, and understandable.
- Keep Direct DNA editing as the recommended workflow for exact A/T/C/G changes.
- Describe the lock/apply workflow as **DNA locks** in player-facing UI and docs.
- Direct DNA locks should apply cleanly to pasted SIM result DNA while the panel is open.
- Parameters controls should patch directly without an extra checkbox.
- Gene Lab controls are advanced and experimental; make that clear.
- Exploding finisher mode should override no-glitch/intact protections and use fast SIM settings aimed at sub-2s part-launch results.
- caseOh mOde should override other settings, favor slow/large novelty outputs, and stay undescribed.

## Preferred Checks

Fast local check:

```powershell
.\scripts\run_basic_checks.ps1
```

If a testable export with tests exists:

```powershell
.\tests\01_RUN_V20_FAST_TESTS.bat
.\tests\02_RUN_V20_TESTS_DEFAULT_STEAM.bat
```

If tests are renamed in future versions, update this file and README together.

## Release Hygiene

Public release zips must not include:

- `__pycache__/`
- `*.pyc`
- `Horsey.exe`
- `Horsey Game/`
- `save/`
- `data/`
- `sound/`
- test workspaces
- copied branch folders
- local configs containing personal paths

## Review Checklist Before Release

- README version and wording match the app.
- CHANGELOG includes the current user-facing changes.
- Release notes exist under `docs/releases/`.
- `.gitignore` blocks game files, saves, copied branches, caches, and release artifacts.
- UI opens without requiring horizontal scrolling for normal controls.
- Paths are hidden by default in the panel.
- No game files are included in the release zip.
