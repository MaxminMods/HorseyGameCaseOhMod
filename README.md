# HorseyGameCaseOhMod v2

HorseyGameCaseOhMod v2 is a local branch mod panel for **Horsey Game**. It copies your game into a separate CaseOh90000 branch, applies the mod there, and keeps your normal Steam install and normal save separate.

The mod does not include Horsey Game, `Horsey.exe`, game assets, or save files.

## Quick Start

Extract the download, then run:

```powershell
.\00_START_HERE_CaseOh90000.bat
```

The first-run setup will look for your Horsey Game install, create the copied CaseOh90000 branch, and open the panel. If you press Enter through the default choices, setup uses the detected Horsey path, keeps the default branch location, skips the desktop shortcut, and starts the panel automatically.

After setup, use:

```powershell
.\01_LAUNCH_PANEL_CaseOh90000.bat
```

Use this when you want to rebuild the copied branch from your latest normal save, launch Horsey, and open the panel:

```powershell
.\HorseyGameCaseOhMod\CaseOh90000_RUN_FROM_LATEST_SAVE.bat
```

## Requirements

- Windows
- Horsey Game installed locally
- Python 3 with Tkinter

If the setup window or panel does not open, install Python 3 from [python.org](https://www.python.org/downloads/) and enable **Add python.exe to PATH** during installation.

## Main Features

- **Parameters** removes the old 5-second SIM9000 acceptance barrier, improves time display precision, and keeps the proven baseline easy to restore.
- **Intensity** controls optional SIM9000 search depth, generation count, horse count, and race-slot count.
- **Direct DNA** creates and edits normal 40-line Horsey DNA with exact `A`, `T`, `C`, and `G` base choices.
- **DNA locks** let you preserve selected base edits while applying them to newly pasted SIM results.
- **Gene Lab** edits branch `genes.xml` expression values for advanced experiments.
- **Settings** keeps window, privacy, and layout options out of the main workflow.
- The panel remembers window options, tab order, Direct DNA text, selected presets, strand choices, and active DNA locks.

## Recommended Workflow

Use Direct DNA as the main workflow.

1. Run SIM9000 until you get a promising disk.
2. Paste or load that DNA in the Direct DNA tab.
3. Make small base edits or apply a preset.
4. Use DNA locks to keep only the bases you intentionally changed.
5. Paste a fresh SIM result and apply the locks.
6. Copy or save the finished DNA back into the copied branch.

This is usually more useful than simply maxing every SIM9000 setting. Bigger searches can help, but controlled DNA edits make it easier to compare what actually improved the horse.

## Suggested Fast-Horse Settings

These are practical starting points, not guaranteed best values.

**Parameters**

- Minimum accepted finish frames: `0`
- Display precision: `T:%.3f`
- Valid-result score max: stock/original
- Stall/no-progress cull frames: stock or slightly lower if results get strange

**Intensity**

- Generations: `75-128`
- Horses/race slots: `152-256` horses, or `38-64` race slots
- SIM work batches/update: higher for speed, lower if the window feels frozen
- Elite parent percent: `20-30%`
- Earliest disk generation: around `9` unless you are intentionally testing unstable early DNA

## Caseoh Arena

The copied branch also includes the arena work from the multiplayer project:

- the old Abandoned Track is renamed **The Caseoh Arena**;
- the arena can run a **40-furlong** race;
- race music is extended for longer arena tests;
- the in-game timer starts from Horsey's real race-start sound and stops on the first finish sound;
- reset holds the last race result until you leave the arena or start another race;
- the old **Bio-Hacker** world-map label is renamed **CaseohHaus**.

These changes are branch-only. The bundled native timer runtime is copied into the mod branch and guarded so it does not run against the normal Steam install.

## Folder Layout

The release zip is intentionally simple at the top level:

```text
README.md
00_START_HERE_CaseOh90000.bat
01_LAUNCH_PANEL_CaseOh90000.bat
HorseyGameCaseOhMod/
```

Useful files inside `HorseyGameCaseOhMod/`:

```text
00_START_HERE_CaseOh90000.bat
CaseOh90000_RUN_FROM_LATEST_SAVE.bat
CaseOh90000_OPEN_PANEL.bat
CaseOh90000_OPEN_BRANCH_FOLDER.bat
CaseOh90000_CREATE_DESKTOP_SHORTCUT.bat
CaseOh90000_RESTORE_BRANCH_ORIGINAL.bat
CaseOh90000_ENABLE_CASEOH_MODE.bat
CaseOh90000_DISABLE_CASEOH_MODE.bat
```

## Safety

HorseyGameCaseOhMod is designed to work on a copied branch. The normal Steam install and normal save are not meant to be modified.

The panel hides full folder paths by default for stream privacy. First-time setup still asks for folders in a console window, so avoid running setup live on stream unless you are comfortable showing those paths.

Public releases should never include copied game folders, `Horsey.exe`, saves, branch folders, local config files, logs, or game asset folders.

## Mod Notice

All mods are used at your own risk. HorseyGameCaseOhMod is intended to be as safe as possible by working through a copied branch, but there can never be guarantees. Back up anything important before experimenting.
