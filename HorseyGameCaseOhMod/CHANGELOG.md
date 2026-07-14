# Changelog

## Documentation Cleanup

- Rebuilt the root README into a single player-facing guide.
- Removed duplicated setup text, rough notes, and outdated wording.
- Removed internal prompt and handoff documents from the public repository.
- Updated supporting docs and release notes to use consistent section names and formatting.

## HorseyGameCaseOhMod v2

### Panel and Layout

- Renamed the main tabs to **Parameters**, **Intensity**, **Gene Lab**, **Direct DNA**, and **Settings**.
- Added colored tab borders and unique tab icons.
- Added drag-to-reorder tabs and saved tab order between panel launches.
- Increased default font size and panel width.
- Moved the main action buttons above the tabs and gave them distinct colors.
- Moved privacy and window options into Settings.
- Split dense SIM slider sections into columns to reduce scrolling.
- Added automatic side-by-side fitting for Horsey and the panel.
- Detached panel launchers so the command window does not stay open.

### SIM9000 Controls

- Added optional live updates for SIM9000 generation and race-slot totals.
- Updated in-game `G:x/total` and `R:x/total` display values after live Apply.
- Relabeled gene-pool controls as horses/race slots.
- Fresh branches now start with Intensity controls enabled so the visible SIM9000 settings apply immediately.
- Patched both the base 8-generation SIM9000 path and the RAM-upgraded 16-generation path so Intensity settings apply either way.
- Kept the baseline restore flow available from the panel.

### Direct DNA

- Made Direct DNA the recommended workflow for exact `A`, `T`, `C`, and `G` edits.
- Renamed partial injection wording to **DNA locks**.
- Added a one-click flow for applying locked bases to pasted SIM result DNA.
- Added fast-open buttons for speed, wheels, tail, and timing helix groups.
- Added Collapse all for the expanded helix editor.
- Kept helix controls lazy-loaded for faster panel opening.
- Saved Direct DNA text, selected presets, strand choices, window options, and active DNA locks.

### Caseoh Arena

- Added branch-only Caseoh Arena support.
- Renamed the old Abandoned Track to **The Caseoh Arena** in the copied branch.
- Added a 40-furlong arena race option.
- Wrote the 40-furlong selector patch directly into the copied branch so the fifth option does not depend only on DLL runtime patching.
- Added the branch-only garage sign art.
- Added the bundled native arena timer runtime.
- Updated the timer to use Horsey's real race-start and finish sound events.
- Kept the last race result visible after reset until a new race starts or the player leaves the arena.
- Made the arena exit sound clear the timer display unconditionally when leaving the racetrack.
- Renamed the old **Bio-Hacker** map label to **CaseohHaus**.

### Setup and Release Packaging

- Made **Start Here** use an easy/default setup path that creates the mod branch, desktop shortcut, and panel launch with fewer questions.
- Added a bundled HorseyGameCaseOhMod v2 icon for the desktop shortcut and panel window so it is distinct from the normal Horsey executable.
- First-run setup keeps the detected Horsey path and default branch location unless changed.
- Custom setup still lets advanced users skip the shortcut with `--no-shortcut`.
- Launchers now show a clearer Python 3 + Tkinter install message if the panel cannot start.
- Release zips open to `README.md`, `00_START_HERE_CaseOh90000.bat`, `01_LAUNCH_PANEL_CaseOh90000.bat`, and one app folder.
- Release hygiene checks exclude copied game files, saves, branch folders, logs, and local config files.

## v1.6.0 - Direct DNA Editor

- Added the Direct DNA Editor tab.
- Added expandable helixes `H00-H19`.
- Added exact `A`, `T`, `C`, and `G` editing for each visible gene position.
- Added DNA presets that edit visible DNA bases instead of hidden `genes.xml` values.
- Kept the SIM Gene Lab expression-profile system as an advanced option.
- Kept streamer privacy, exploding finisher tools, and the Easter Egg behavior from v1.5.

## v1.5.0 - Privacy and Exploding Finisher

- Added streamer privacy/path hiding to the panel.
- Added the exploding finisher preset and seed DNA helper.
- Kept the Easter Egg behavior private in the UI.
