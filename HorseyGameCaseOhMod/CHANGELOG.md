# Changelog

## HorseyGameCaseOhMod v2 - Friendlier Direct DNA and repo cleanup

- Reworded the README around the normal player flow: start setup, run from latest save, use Direct DNA, then copy/save DNA.
- Moved Codex-only notes into `docs/codex/`.
- Moved release notes into `docs/releases/`.
- Increased the panel font size and default window width for easier reading.
- Moved the main tabs directly under the header and moved privacy/hotkey controls into a Settings tab.
- Reworked the tabs into a colored, bordered top strip with the default order: Parameters, Intensity, Gene Lab, Direct DNA, Settings.
- Added simple unique tab icons so each panel area is easier to recognize at a glance.
- Added drag-to-reorder tabs, with the order saved between panel launches.
- Moved the four main action buttons above the tabs and gave them distinct colors so Apply, Save, Baseline, and Restore are always visible.
- Split dense SIM slider sections into columns to reduce scrolling.
- Added an automatic side-by-side window fit so Horsey opens non-fullscreen beside the panel for SIM9000 testing.
- Panel-only launchers now detach the panel so the command window does not stay open while the panel is running.
- The Intensity tab now labels gene-pool size as horses/race slots so `R:x/10` style totals are easier to understand.
- Apply to running game now updates the active SIM9000 state block when it can safely find it, so generation and race-slot changes can take effect without restarting Horsey.
- The SIM9000 `G:x/total` and `R:x/total` readouts now use the live SIM state after Apply instead of a display-only counter workaround.
- Added generated branch-only garage art: a taped CaseOh sign inside the garage.
- First-run setup now defaults to no desktop shortcut when pressing Enter.
- Download/release zips now open to `00_START_HERE_CaseOh90000.bat`, `01_LAUNCH_PANEL_CaseOh90000.bat`, `README.md`, and the `HorseyGameCaseOhMod/` app folder.
- Launchers now check for a real Python 3 + Tkinter install instead of only checking that `py.exe` exists.
- Fixed the larger-font panel style so the window opens correctly on Python 3.13/Tk 8.6.
- Renamed the injection-style wording to **DNA locks**.
- Kept launchers at the repo root so double-click workflows stay obvious.
- Panel choices are now saved when the window closes, including presets that were selected but not yet patched.
- Direct DNA preset and strand choices are restored on the next open.
- Direct DNA edits and presets now create partial base locks.
- Added a one-click flow for applying only locked A/T/C/G positions to a pasted SIM result DNA.
- Moved Direct DNA Editor before the advanced SIM Gene Lab tab.
- Added fast-open buttons for common helix groups: speed core, wheels, tail, and timing.
- Added Collapse all for the expanded helix editor.
- Kept helix controls lazy-loaded so the panel opens quickly.
- Added stronger automated tests for DNA parsing, preset output, branch scan/apply, and release hygiene.

## v1.6.0 - Direct DNA Editor

- Adds a Direct DNA Editor tab.
- Lets users expand helixes H00-H19.
- Lets users choose A/T/C/G for each gene position on each strand.
- Adds transparent DNA presets that edit visible DNA bases instead of hidden genes.xml values.
- Keeps the old SIM Gene Lab expression-profile system but labels it as experimental.
- Keeps streamer privacy, exploding finisher tools, and hidden Easter Egg behavior from v1.5.

## v1.5.0 - Privacy + Exploding Finisher

- Adds streamer privacy/path hiding to the CaseOh90000 panel.
- Adds exploding finisher preset and seed DNA helper.
- Keeps caseOh mOde private as an Easter Egg.
