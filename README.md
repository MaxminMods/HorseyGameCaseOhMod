# CaseOh90000

CaseOh90000 is a safe-branch mod panel for **Horsey Game**.

It copies your game into a separate branch folder, applies the CaseOh90000 SIM9000 changes there, and keeps your normal Steam install and normal save separate while you experiment.

## Start Here

Most players only need this file first:

```powershell
.\00_START_HERE_CaseOh90000.bat
```

In the release zip, the top level is intentionally simple: this start file and this README are the only two files you need to look at first. The rest of the app lives inside the `HorseyGameCaseOhMod` folder.

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

**SIM Engine** changes the copied branch so SIM9000 is easier to use. It removes the 5.0-second acceptance barrier, shows `T` with 3 decimals, and keeps normal search behavior by default.

**SIM Gene Lab** is advanced. It edits the copied branch's `data/genes.xml` expression values, which can be useful for strange experiments but is less predictable than direct DNA editing.

The main tabs can be dragged into the order you prefer. The panel remembers that tab order when it closes.

## Direct DNA Workflow

1. Paste DNA, load a `.txt`, or start from a blank A/A genome.
2. Apply a small DNA preset or expand helixes `H00` through `H19`.
3. Edit the exact `A`, `T`, `C`, or `G` bases you want.
4. Those edited bases become **DNA locks**.
5. Paste a SIM result and apply the locked bases to keep only your chosen changes.
6. Copy the final DNA or save it as a text file in the copied branch.

DNA locks remember only the bases you touched, then re-apply those bases to a fresh SIM result without replacing the whole horse.

The panel remembers your last selected Direct DNA preset, strand choice, DNA text, window options, and active DNA locks when it closes.

## Useful Launchers

```text
Release zip root:
00_START_HERE_CaseOh90000.bat              First-time setup, branch build, launch.
README.md                                  Player instructions.

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
CHANGELOG.md              Human-readable change history.
SECURITY.md               Safety and reporting notes.
AGENTS.md                 Rules for Codex or other coding agents.
scripts/                  Build and basic check helpers.
docs/releases/            Release notes.
docs/codex/               Codex handoff notes and task prompts.
```

Release zips keep the first view clean for newcomers. Developer-only notes live under `HorseyGameCaseOhMod/docs/`.

## Safety

CaseOh90000 does not include Horsey Game, game assets, `Horsey.exe`, or save files.

The tool is designed to patch only the copied branch. Back up your save before using mods anyway.
