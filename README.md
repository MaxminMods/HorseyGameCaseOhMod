# CaseOh90000 v1.6.1 — Direct DNA Editor


## v1.6.1 clean/fast pass

This build keeps the Direct DNA Editor as the recommended workflow. The editor is lazy-loaded so large A/T/C/G controls are only created when you expand a helix, and it includes fast-open buttons for the common racing groups: speed core, wheels, tail, and timing. The old SIM Gene Lab remains available as an advanced branch-wide experiment, but exact horse creation should use the Direct DNA Editor.

CaseOh90000 is a local safe-branch mod tool for **Horsey Game**. It does not include the game, does not patch your Steam install directly, and does not modify your normal save while you experiment.

It copies your installed game into a separate branch, applies the CaseOh90000 SIM9000 changes there, and lets you copy any useful genome back into your normal unmodded game.

## What is new in v1.6.1

The old SIM Gene Lab presets were too vague: they changed how `genes.xml` expresses traits, which could make wildly different creatures than the preset name implied.

v1.6.1 keeps the old expression-profile tools, but adds a new **Direct DNA Editor** tab that is much more honest and useful:

- paste or load any 40-line Horsey DNA;
- validate and normalize it;
- expand any helix from `H00` through `H19`;
- choose `A`, `T`, `C`, or `G` for each gene position on each strand;
- set both strands quickly with one click;
- apply small transparent DNA presets that change visible bases, not hidden expression tables;
- copy the finished DNA to clipboard;
- save the finished DNA as a `.txt` file inside the copied branch.

This means you can actually see what is being changed instead of guessing what a preset did.

## What it changes in the temporary branch

- Removes SIM9000's 5.0-second acceptance barrier.
- Changes the SIM9000 `T` readout to 3 decimals.
- Keeps SIM9000's normal search/scoring behavior by default.
- Includes the CaseOh90000 panel.
- Includes `caseOh mOde` as an Easter Egg.
- Includes the Direct DNA Editor for exact A/T/C/G editing.

## Recommended workflow

1. Run `00_START_HERE_CaseOh90000.bat`.
2. Choose your normal Horsey Game folder.
3. Choose where the copied branch should live.
4. Use the copied branch to experiment with SIM9000.
5. Open the CaseOh90000 panel.
6. Use **Direct DNA Editor** to build or tweak genomes.
7. Copy the genome and paste it into CRISPR / SIM9000 / Notepad / your normal game.

## Start here

```powershell
.\00_START_HERE_CaseOh90000.bat
```

The setup wizard asks for:

1. the folder that contains your normal `Horsey.exe`; and
2. where the CaseOh90000 branch should live.

The tool can also create a desktop shortcut.

## Daily use

```powershell
.\CaseOh90000_RUN_FROM_LATEST_SAVE.bat
```

That rebuilds the copied branch from your latest normal save, applies the mod, launches the branch, and opens the CaseOh90000 panel.

## Direct DNA Editor

The Direct DNA Editor is the tab to use when you want precise control.

- **DNA text** is the normal 40-line format.
- **Transparent DNA presets** apply a few visible base edits.
- **Partial direct DNA injection** remembers edited bases as locks.
- **Paste SIM result + apply locks** injects only those locked bases into a fresh SIM result DNA.
- **Expand helixes H00–H19** lets you choose each base manually.
- **Copy DNA** puts the normalized genome on your clipboard.
- **Save DNA .txt to branch** writes the genome to `CaseOh90000_seed_dna` in the copied branch.

The editor does not change your normal save. It creates pasteable DNA strings, and the panel remembers your last selected presets/options when it closes.

## SIM Gene Lab

SIM Gene Lab is still included, but it edits branch `data/genes.xml` expression values. That can be useful for strange experiments, but it is less predictable than direct DNA editing.

Use Direct DNA Editor when you want exact `A/T/C/G` control.

## Useful files

```text
00_START_HERE_CaseOh90000.bat              Setup wizard, branch build, launch.
CaseOh90000_RUN_FROM_LATEST_SAVE.bat       Rebuild branch from latest save, launch game, open panel.
CaseOh90000_OPEN_PANEL.bat                 Open the panel manually.
CaseOh90000_CREATE_DESKTOP_SHORTCUT.bat    Create/recreate the desktop shortcut.
CaseOh90000_OPEN_BRANCH_FOLDER.bat         Open the copied branch folder.
CaseOh90000_RESTORE_BRANCH_ORIGINAL.bat    Restore the copied branch's original executable/data.
CaseOh90000_ENABLE_CASEOH_MODE.bat         Enable the Easter Egg in the branch.
CaseOh90000_DISABLE_CASEOH_MODE.bat        Disable the Easter Egg in the branch.
```

## Safety

CaseOh90000 is designed around a copied branch. Your normal Steam install and normal save are not supposed to be modified by the branch tool.

Back up your save anyway before using mods.
