# Copy/paste Codex task prompts

## 1. Repo audit

```text
Read AGENTS.md first. Audit this repository for release safety and UI/control consistency. Do not edit files yet. Report any mismatch between UI labels, README claims, and actual code behavior. Pay special attention to SIM Engine sliders, Direct DNA locks, Gene Lab archetypes, caseOh mOde privacy, exploding finisher behavior, and release hygiene.
```

## 2. Fix one bug safely

```text
Read AGENTS.md first. Fix the single highest-confidence bug from the audit. Keep the patch small. Add or update tests if possible. Do not include game files, saves, copied branches, or caches. Show the diff summary and commands run.
```

## 3. UI polish pass

```text
Read AGENTS.md first. Improve CaseOh90000Panel.py UI clarity without changing mechanics. Keep tabs compact, avoid excessive inline text, keep path hiding on by default, and keep caseOh mOde described only as Easter Egg. Run py_compile.
```

## 4. Release build check

```text
Read AGENTS.md first. Verify release hygiene. Confirm no game files, saves, copied branch folders, __pycache__, or pyc files are included. Update README/CHANGELOG/RELEASE_NOTES if needed. Do not change mechanics.
```

## 5. Native future task placeholder

```text
Read AGENTS.md first. Create a separate planning document for future native/in-process work. Do not implement injection. Document what would be needed to hook Horsey item UI for naming DNA flasks/floppy disks and to integrate chat/timer natively.
```
