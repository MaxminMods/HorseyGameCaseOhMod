# Codex Handoff - CaseOh90000

Use this repo with Codex App, Codex IDE extension, or Codex CLI. This project is a better fit for Codex than one-off chat zips because it has connected UI logic, patching logic, release packaging, and safety rules.

## Recommended Local Layout

Keep the repo in a normal projects folder, outside the Horsey Game install.

Example:

```text
%USERPROFILE%\Documents\projects\HorseyGameCaseOhMod
```

Keep Horsey Game itself outside the repo.

Example:

```text
<your Steam library>\steamapps\common\Horsey Game
```

## Recommended Workflow

1. Commit the current working build.
2. Create a feature branch for each focused task.
3. Ask Codex for one focused change at a time.
4. Run compile checks and any available tests.
5. Test the live Windows UI and copied game branch manually.
6. Merge only when the branch is stable.

## Suggested First Codex Task

```text
Read AGENTS.md, README.md, CaseOh90000Panel.py, horseymod.py, sim_gene_profiles.py, caseoh.py, dna_designer.py, and exploding_seed.py.

Task: audit the current UI/control logic for mismatches between what a control says and what it actually patches. Do not add features yet. Produce a short report listing:
1. controls that directly patch Horsey.exe or genes.xml,
2. controls that only affect saved config,
3. controls that affect DNA text or DNA locks,
4. possible confusing UI wording,
5. tests that should be added.

Do not include any Horsey game files or copied branch folders.
```

## Suggested Second Codex Task

```text
Implement the highest-priority UI cleanup from the audit.
Keep the panel compact.
Do not reveal caseOh mOde behavior.
Do not add extra enable checkboxes.
Run the basic checks and update README/CHANGELOG if behavior changes.
```

## Suggested Third Codex Task

```text
Improve Direct DNA locks.
Make sure any edited H00-H19 A/T/C/G position is recorded as an active DNA lock automatically.
Add or update tests that prove the lock helper changes only the selected bases in a pasted SIM result.
```
