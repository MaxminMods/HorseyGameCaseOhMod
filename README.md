# HorseyGameCaseOhMod 3.0

HorseyGameCaseOhMod 3.0 is a local mod panel for **Horsey Game**. It creates a separate CaseOh parallel dimension, applies the mod there, and keeps your normal Steam install separate.

This download does not include Horsey Game, `Horsey.exe`, game assets, or save files.

## Install

1. Extract the zip.
2. Close normal Horsey Game if it is open.
3. Double-click:

```powershell
.\00_START_HERE_CaseOh90000.bat
```

Start Here automatically uses the recommended setup when it can find Horsey Game. It creates the CaseOh parallel dimension, copies your current normal save into it, hides folder paths in the panel for streaming, starts CaseOh Horsey, and opens the panel.

If Horsey cannot be found automatically, it will ask you to pick the folder that contains `Horsey.exe`.

## Run Each Time

First close all other running copies of normal or modded Horsey.

After setup, run the mod with the desktop shortcut or:

```powershell
.\02_PLAY_CASEOH_HORSEY.bat
```

This opens the existing CaseOh parallel dimension. It does not rebuild the folder, so horses, disks, and saves made in the CaseOh dimension stay there.

To reopen only the panel without starting Horsey:

```powershell
.\01_LAUNCH_PANEL_CaseOh90000.bat
```

### Save Safety

- Normal Horsey and the CaseOh parallel dimension have separate saves.
- First install copies your current normal save into the CaseOh dimension.
- Normal play should use the desktop shortcut or `02_PLAY_CASEOH_HORSEY.bat`.
- Only use `HorseyGameCaseOhMod\CaseOh90000_RUN_FROM_LATEST_SAVE.bat` if you intentionally want to rebuild the CaseOh dimension from your latest normal save.
- Rebuilding from the latest normal save can replace progress made inside the CaseOh dimension, so copy out any important DNA first.

## Requirements

- Windows
- Horsey Game installed locally
- Python 3 with Tkinter

If the setup window or panel does not open, install Python 3 from [python.org](https://www.python.org/downloads/) and enable **Add python.exe to PATH** during installation.

## Main Tabs

The first two tabs are the main everyday controls.

### Parameters

- **Minimum accepted finish frames**: set to `0` for the CaseOh baseline. This removes the old 5-second SIM9000 acceptance barrier.
- **Stall/no-progress cull frames**: how long SIM9000 lets a stuck test keep trying. Lower values clear bad attempts faster; higher values let strange slow attempts continue.
- **Maximum candidate frame budget**: the longest a test horse can run. Raising this does not make horses faster; it only gives slow candidates more time to finish.
- **Valid-result score max**: the broad internal result filter. The original value is usually safest.
- **Display precision**: `T:%.3f` shows more timing detail.

### Intensity

- **Generations per SIM9000 run**: how many generations SIM9000 searches.
- **Gene-pool / race slots**: how many horses SIM9000 starts with, and how many race slots that represents.
- **SIM work batches per UI update**: how much SIM work happens between screen refreshes. Higher can finish sooner but may look frozen while it works.
- **Elite parent / diversity percent**: how much of the better population survives into the next generation. Lower is greedier; higher keeps more variety.
- **Earliest generation for result disk**: the first generation allowed to output a disk. Around `9` is a good starting point.
- **Presets**: quick starting points. Normal search is safest; deeper searches are for experimenting.

Good starting values are `75-128` generations and `152-256` horses. Raise values gradually.

### Main Buttons

- **Apply to running game** changes live SIM9000 values while CaseOh Horsey is open.
- **Save for next launch** writes settings into the CaseOh dimension files on disk. Close CaseOh Horsey before pressing it, then launch again.
- **Load baseline** returns to the recommended CaseOh defaults.
- **Restore normal search** returns SIM9000 search values toward the original game behavior.

## DNA Workflow

Direct DNA and Gene Lab are beta tools. They are useful, but they are for careful experimenting.

To save DNA outside the game:

1. Open the horse DNA in CRISPR.
2. Select the DNA text and copy it.
3. Paste it into Notepad.
4. Save it as a `.txt` file with a name you will recognize.

To use saved DNA again, copy the DNA text from Notepad and paste it back into CRISPR or the Direct DNA tab. Keep the DNA as plain text and avoid adding notes inside the DNA block.

## Caseoh Arena

The CaseOh parallel dimension includes:

- **The Caseoh Arena** replacing the old Abandoned Track label;
- a 40-furlong arena race option;
- an in-game race timer triggered from Horsey's race sounds;
- longer arena race music;
- **CaseohHaus** replacing the old Bio-Hacker map label.

The timer loads when Horsey is started through Start Here, the desktop shortcut, or `02_PLAY_CASEOH_HORSEY.bat`. Opening the copied dimension's `Horsey.exe` directly may skip the timer.

## Folder Layout

The release zip opens to:

```text
README.md
00_START_HERE_CaseOh90000.bat
01_LAUNCH_PANEL_CaseOh90000.bat
02_PLAY_CASEOH_HORSEY.bat
HorseyGameCaseOhMod/
```

Everything else lives inside the `HorseyGameCaseOhMod` app folder.

## Safety

HorseyGameCaseOhMod is designed to work inside the CaseOh parallel dimension. The normal Steam install is not meant to be modified.

Public releases should never include copied game folders, `Horsey.exe`, saves, CaseOh dimension folders, local config files, logs, or game asset folders.

## Mod Notice

All mods are used at your own risk. HorseyGameCaseOhMod is intended to be as safe as possible by working through a separate CaseOh parallel dimension, but there can never be guarantees. Back up anything important before experimenting.
