# CaseOh90000 v1.0

CaseOh90000 is a local, safe-branch mod tool for **Horsey Game**. It does not include the game, does not patch your Steam install directly, and does not touch your normal save while you are experimenting.

It copies your installed game into a separate mod branch, applies the CaseOh90000 mod there, and launches that copied branch with the CaseOh90000 panel. If you are new to using mods, it is still a good idea to test with a copied Horsey Game folder first.

Use the temporary modded branch to create horses, copy any genome you like from the CRISPR/manual gene view, then recreate or paste that genome in your normal unmodded game. You can put the disk from the computer output into the CRISPR lab computer, use the copy function, paste the genome into Notepad to save it, or paste it into your normal Horsey save's CRISPR lab computer to use it immediately.

Heres a youtube preview showing how it works: https://www.youtube.com/watch?v=Rc4P1nUHum4&t=4s

## What it changes in the temporary branch game version

- Removes SIM9000's 5.0-second acceptance barrier, allowing it to go as low as 0.0.
- Changes the SIM9000 `T` readout to 3 decimals for more precise time readings.
- Keeps SIM9000's normal search/scoring behavior by default.
- Includes `caseOh mOde` as an Easter Egg for fun.
- Includes the **CaseOh90000 panel** for changing simulator settings while using the branch.

## First step after downloading and unzipping

Double-click:

```text
00_START_HERE_CaseOh90000.bat
```

The setup wizard asks for:

1. the folder that contains your normal `Horsey.exe`; and
2. where the CaseOh90000 mod branch should live/run from.

Press Enter to accept the default values, or type your own paths if you already set up a specific location.

The wizard can also create a desktop shortcut. The shortcut starts CaseOh90000 from your latest normal save and opens the **CaseOh90000 panel** by default. It uses Windows' real Desktop path, including OneDrive Desktop setups.

## Daily use

Use the desktop shortcut, or double-click:

```text
CaseOh90000_RUN_FROM_LATEST_SAVE.bat
```

That rebuilds the copied branch from your latest normal save, applies the mod, launches the branch, and opens the CaseOh90000 panel.

## Important workflow

1. Play/save normally in your unmodded Steam copy.
2. Launch CaseOh90000 from the latest save.
3. Use the modded SIM9000 branch to create a horse.
4. Copy the genome from the CRISPR view, which is easier, or from the manual gene view, which is harder.
5. Paste or recreate that genome in your normal unmodded game.

Your normal install and normal save are not modified by the branch tool.

## CaseOh90000 panel

Open the panel manually with:

```text
CaseOh90000_OPEN_PANEL.bat
```

The panel is not always-on-top by default. Use the buttons in the panel to dock it beside Horsey, hide it, or keep it on top if you want. The optional keyboard shortcut is still included, but if Windows refuses the bind on your machine, the **Hide panel** button does the same job.

Changes made in the panel live-update the mod branch version of SIM9000. Some disk/data changes, like the Easter Egg toggle, may require restarting the modded branch before the visual effect appears.

## Included files

```text
00_START_HERE_CaseOh90000.bat              First-time setup, branch build, launch.
CaseOh90000_RUN_FROM_LATEST_SAVE.bat       Daily launcher: refresh branch, launch game, open panel.
CaseOh90000_OPEN_PANEL.bat                 Open the CaseOh90000 panel manually.
CaseOh90000_CREATE_DESKTOP_SHORTCUT.bat    Create or repair the desktop shortcut.
CaseOh90000_OPEN_BRANCH_FOLDER.bat         Open the copied mod branch folder.
CaseOh90000_RESTORE_BRANCH_ORIGINAL.bat    Restore the copied branch's original executable/data.
CaseOh90000_ENABLE_CASEOH_MODE.bat         Enable the Easter Egg in the branch.
CaseOh90000_DISABLE_CASEOH_MODE.bat        Disable the Easter Egg in the branch.
```

## Notes

SIM9000 is a discovery tool, not final proof of real track speed. Very fast SIM results can still behave differently in actual races, so validate your favorite genomes in the normal game. The old test track at 20 furlongs is a good place to compare results, but the normal track works too.

## Disclaimer

CaseOh90000 is an unofficial fan-made mod tool for local/offline experimentation with Horsey Game.

It does not include Horsey Game, Horsey.exe, game assets, or save files.

Use at your own risk and back up your save before using mods.
