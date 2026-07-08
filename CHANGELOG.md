# Changelog

## HorseyGameCaseOhMod v2 - Friendlier Direct DNA and repo cleanup

- Reworded the README around the normal player flow: start setup, run from latest save, use Direct DNA, then copy/save DNA.
- Moved Codex-only notes into `docs/codex/`.
- Moved release notes into `docs/releases/`.
- Increased the panel font size and default window width for easier reading.
- Moved the main tabs directly under the header and moved privacy/hotkey controls into a Settings tab.
- Added drag-to-reorder tabs, with the order saved between panel launches.
- Split dense SIM slider sections into columns to reduce scrolling.
- First-run setup now defaults to no desktop shortcut when pressing Enter.
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
