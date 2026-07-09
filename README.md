# CaseOh90000
Instructions:

How The Mod Works
The launcher runs setup_wizard.py, which finds the real Horsey install, copies it into a separate mod branch, and keeps the normal Steam install untouched. 

horseymod.py scans the copied Horsey.exe for known SIM9000 byte patterns, then patches only the copied branch. It controls things like the 5-second finish barrier, SIM frame limits, generation count, race-slot count, and display precision. 

CaseOh90000Panel.py is the friendly control window. Apply to running game patches the live Horsey process and now also updates the active SIM9000 state in memory, so generation/race-slot changes can work without restarting Horsey. Save to branch files writes those changes into the copied branch for later launches.

dna_designer.py handles Direct DNA editing and DNA locks. sim_gene_profiles.py handles advanced genes.xml experiments. caseoh_art.py adds the branch-only garage sign art.

How Vanilla SIM9000 Works
Without mods, SIM9000 starts with a small gene pool, runs candidate horses through simulated attempts, culls bad/stuck horses, breeds from better candidates, and repeats for a limited number of generations. The default behavior is conservative: about 40 horses, 10 visible race slots, and 16 generations. It also has the old 5-second acceptance barrier, which blocks very fast results from being accepted normally.

Best Strategy For Fast Horses
Use Direct DNA as the main workflow. Let SIM9000 find a promising result, then use DNA locks to preserve useful base edits while testing small controlled changes.

Good starting settings:
Parameters:
- Minimum accepted finish frames: 0
- Display precision: T:%.3f
- Valid-result score max: stock/original
- Stall/no-progress: stock or slightly lower if results get weird

Intensity:
- Generations: 75-128
- Horses / race slots: 152-256 horses, or 38-64 race slots
- SIM work batches/update: higher for speed, lower if the window feels frozen
- Elite parent percent: 20-30%
- Earliest disk generation: keep around 9 unless intentionally testing unstable early DNA
Best practical loop: run SIM, keep fast clean disks, compare tiny DNA changes, avoid lowering the disk generation too much, and don’t chase huge search numbers forever. More generations and more horses can help, but controlled DNA edits usually beat blindly maxing every slider. Remove old dna and combine best disk scores in the vat to further optimize them, but this does create instability. 

Im still experimenting with making it leave specific genes alone, or make horses that explode intentionally, coming soonish

README:

CaseOh90000 is a safe-branch mod panel for **Horsey Game**.

It copies your game into a separate branch folder, applies the CaseOh90000 SIM9000 changes there, and keeps your normal Steam install and normal save separate while you experiment.

## Start Here

Most players only need the two top launchers:

```powershell
.\00_START_HERE_CaseOh90000.bat
```

Use `00_START_HERE_CaseOh90000.bat` the first time. Use `01_LAUNCH_PANEL_CaseOh90000.bat` later when the branch is already set up and you only want the panel.

The top folder is intentionally simple: the start launcher, the panel launcher, this README, and the `HorseyGameCaseOhMod` app folder. Everything else lives one folder lower.

You need Python 3 with Tkinter installed for the setup window and panel. If the window does not open, install Python 3 from [python.org](https://www.python.org/downloads/) and enable `Add python.exe to PATH` during install.

The setup wizard asks for:

1. your normal Horsey Game folder, the one with `Horsey.exe`;
2. where the copied CaseOh90000 branch should live;
3. whether you want a desktop shortcut.

## Normal Use

After setup, use this when you want to rebuild the branch from your newest normal save, launch Horsey, and open the CaseOh90000 panel:

```powershell
.\HorseyGameCaseOhMod\CaseOh90000_RUN_FROM_LATEST_SAVE.bat
```

## What The Panel Is For

**Direct DNA Editor** is the recommended tab. It makes normal 40-line Horsey DNA that you can copy, save, paste into CRISPR, or use with SIM9000 results.

**Parameters** changes the copied branch so SIM9000 is easier to use. It removes the 5.0-second acceptance barrier, shows `T` with 3 decimals, and keeps normal search behavior by default.

**Intensity** contains the optional SIM9000 search-depth controls. When experimental search controls are enabled, **Apply to running game** updates the active SIM9000 generation and race-slot totals when the panel can safely find the live SIM state, so `G:x/total` and `R:x/total` reflect the real running values without restarting Horsey.

**Gene Lab** is advanced. It edits the copied branch's `data/genes.xml` expression values, which can be useful for strange experiments but is less predictable than direct DNA editing.

The main tabs use the default order **Parameters**, **Intensity**, **Gene Lab**, **Direct DNA**, **Settings**. They can be dragged into the order you prefer, and the panel remembers that tab order when it closes.

## Direct DNA Workflow

1. Paste DNA, load a `.txt`, or start from a blank A/A genome.
2. Apply a small DNA preset or expand helixes `H00` through `H19`.
3. Edit the exact `A`, `T`, `C`, or `G` bases you want.
4. Those edited bases become **DNA locks**.
5. Paste a SIM result and apply the locked bases to keep only your chosen changes.
6. Copy the final DNA or save it as a text file in the copied branch.

DNA locks remember only the bases you touched, then re-apply those bases to a fresh SIM result without replacing the whole horse.

The panel remembers your last selected Direct DNA preset, strand choice, DNA text, window options, and active DNA locks when it closes.

When the panel opens with Horsey running, it automatically fits Horsey into a non-fullscreen side-by-side layout so the SIM9000 area and the panel are visible together. Use the panel's **Fit** button if either window gets moved.

## Useful Launchers

```text
Release zip root:
00_START_HERE_CaseOh90000.bat              First-time setup, branch build, launch.
01_LAUNCH_PANEL_CaseOh90000.bat            Open only the panel after setup.
README.md                                  Player instructions.
HorseyGameCaseOhMod/                       App files and extra launchers.

HorseyGameCaseOhMod folder:
00_START_HERE_CaseOh90000.bat              First-time setup, branch build, launch.
CaseOh90000_RUN_FROM_LATEST_SAVE.bat       Rebuild from latest save, launch game, open panel.
CaseOh90000_OPEN_PANEL.bat                 Open only the panel.
CaseOh90000_CREATE_DESKTOP_SHORTCUT.bat    Create or refresh the desktop shortcut.
CaseOh90000_OPEN_BRANCH_FOLDER.bat         Open the copied branch folder.
CaseOh90000_RESTORE_BRANCH_ORIGINAL.bat    Restore original files inside the copied branch.
CaseOh90000_ENABLE_CASEOH_MODE.bat         Enable the Easter Egg in the branch.
CaseOh90000_DISABLE_CASEOH_MODE.bat        Disable the Easter Egg in the branch.
```

## Folder Map

```text
README.md                 Player instructions.
00_START_HERE_CaseOh90000.bat
01_LAUNCH_PANEL_CaseOh90000.bat
HorseyGameCaseOhMod/       App files, helper launchers, docs, and maintenance notes.
```

Download zips keep the first view clean for newcomers. Developer-only notes live under `HorseyGameCaseOhMod/docs/`.

## Safety

CaseOh90000 does not include Horsey Game, game assets, `Horsey.exe`, or save files.

The tool is designed to patch only the copied branch. Back up your save before using mods anyway.

## Mod Notice

All mods are used at your own risk. HorseyGameCaseOhMod is intended to be as safe as possible by working through a copied branch, but there can never be guarantees. Back up anything important before experimenting.
