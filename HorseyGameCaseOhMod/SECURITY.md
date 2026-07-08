# Security and Safety Notes

CaseOh90000 is designed as a local safe-branch tool.

## What should never be committed

Do not commit or publish:

- `Horsey.exe`
- copied `Horsey Game` folders
- `data/`, `save/`, or `sound/` copied from the game
- `save*.dat`, `*.dat.prev`, or personal save files
- `CaseOh90000_paths.json` because it contains local paths
- generated branch folders

## User safety model

CaseOh90000 should patch only a copied branch of the user's local Horsey Game install. The normal Steam install and normal save are not meant to be modified.

## Streaming privacy

The panel has streamer-path hiding enabled by default. First-time setup still asks for folders in a console, so do not run first-time setup live on stream unless you are comfortable showing those paths.
