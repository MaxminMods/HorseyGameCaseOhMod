# Codex handoff — CaseOh90000

Use this repo with Codex App, Codex IDE extension, or Codex CLI. This project is a better fit for Codex than one-off chat zips because it has many connected files, UI logic, tests, release packaging, and safety rules.

## Recommended local layout

```text
C:\Users\maxwi\OneDrive\Desktop\projects\HorseyGameCaseOhMod
```

Keep Horsey Game itself outside the repo, for example:

```text
C:\Program Files (x86)\Steam\steamapps\common\Horsey Game
```

## Recommended workflow

1. Commit the current working build.
2. Create a feature branch for each Codex task.
3. Ask Codex for one focused change at a time.
4. Run compile/tests locally.
5. Test the live Windows UI/game branch manually.
6. Merge only when the branch is stable.

## Suggested first Codex task

```text
Read AGENTS.md, README.md, CaseOh90000Panel.py, horseymod.py, sim_gene_profiles.py, caseoh.py, and exploding_seed.py.

Task: audit the current v2.0 UI/control logic for mismatches between what a control says and what it actually patches. Do not add features yet. Produce a short report listing:
1. controls that directly patch Horsey.exe or genes.xml,
2. controls that only affect saved config,
3. controls that affect save/DNA locks,
4. possible confusing UI wording,
5. tests that should be added.

Do not include any Horsey game files or copied branch folders.
```

## Suggested second Codex task

```text
Implement the highest-priority UI cleanup from the audit.
Keep the panel compact.
Do not reveal caseOh mOde behavior.
Do not add extra enable checkboxes.
Run py_compile and update README/CHANGELOG if behavior changes.
```

## Suggested third Codex task

```text
Improve Direct DNA locks.
Make sure any edited H00–H19 A/T/C/G position is recorded as an active SIM output lock automatically.
Add or update tests that prove the lock enforcer changes genome-like save blocks in a copied branch.
```
