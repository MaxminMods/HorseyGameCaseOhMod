#!/usr/bin/env python3
"""Exploding finisher seed support for CaseOh90000.

This module contains a public community DNA seed for the "explodes and wins"
archetype and small helpers to write/copy it from the branch tool. It does not
include game files and does not touch the normal Steam install.
"""
from __future__ import annotations

from pathlib import Path
import json
import time
from typing import Any, Dict

EXPLODING_FINISHER_SEED_NAME = "Community Exploding Finisher Seed"
EXPLODING_FINISHER_SEED_DNA = """00:TTATAGCATA
00:TTATAGCATA
01:AATTAGATCCTCA
01:TATTAGATCCTCA
02:CTGAGTCACCGAG
02:CAGAGTCACCAGG
03:CCCAAATCGTACGCC
03:CCCAAATCGTACGCC
04:CGCGGGATGGT
04:CGCGGGGTGGT
05:CATTATCA
05:CATTATCA
06:AGTATTCCGGC
06:AGTATTCCGGC
07:TGACCTCG
07:TGAGCTCG
08:TACGTACTAGC
08:TACGTACTAGC
09:TCGACACCAAG
09:TCGACACGAAG
10:TCATCTTCTCTTG
10:TCATCTGCTCTTG
11:TTACAGTTGCCACTA
11:TTACAGTTGCCACTA
12:TAATTACCGCTAC
12:TAATTACCGCTAC
13:TTCCCCCTGTA
13:TTCCCCCTGTA
14:AATCTAAAATC
14:AATCTAAAATC
15:AGTCACCTCGAAC
15:AGTCACCTCGAAT
16:ATTTCAATTAATATC
16:ATTTCAATTAATATC
17:TGCCGCCATGG
17:TGCCGCCATGG
18:TTAGCAACATC
18:TTAGCAACATC
19:TAAGACACCCGCGTCC
19:TAAGACACCCACGTCC"""

EXPLODING_SIM_OVERRIDES: Dict[str, Any] = {
    # Only very early/violent finishes should survive this mode.
    "min_finish_frames": 0,
    "no_progress_frames": 120,
    "max_sim_frames": 120,
    "valid_result_max": 1800,
    "display_precision": 3,
    "always_accept_early_finish": True,
    # Search faster and aggressively for outliers. Disk can appear immediately.
    "enable_search_controls": True,
    "initial_generation_limit": 96,
    "initial_genepool_size": 96,
    "sim_work_per_ui_update": 3000,
    "elite_parent_percent": 55,
    "min_generation_for_disk": 0,
}


def is_exploding_requested(settings: Dict[str, Any]) -> bool:
    if bool(settings.get("exploding_mode", False)):
        return True
    if not bool(settings.get("gene_lab_enabled", False)):
        return False
    if str(settings.get("racing_preset", "")) == "Exploding finisher":
        return True
    for v in (settings.get("helix_presets") or {}).values():
        if str(v) == "Exploding finisher":
            return True
    return False


def apply_exploding_sim_overrides(settings: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(settings or {})
    if is_exploding_requested(out):
        out.update(EXPLODING_SIM_OVERRIDES)
    return out


def write_exploding_seed_files(branch: Path) -> Dict[str, Any]:
    branch = Path(branch)
    out_dir = branch / "CaseOh90000_seed_dna"
    out_dir.mkdir(parents=True, exist_ok=True)
    dna_file = out_dir / "exploding_finisher_seed.txt"
    manifest = out_dir / "exploding_finisher_seed_manifest.json"
    dna_file.write_text(EXPLODING_FINISHER_SEED_DNA + "\n", encoding="utf-8")
    payload = {
        "name": EXPLODING_FINISHER_SEED_NAME,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "dna_file": str(dna_file),
        "purpose": "Exploding finisher seed DNA for branch-only SIM9000 experiments.",
        "note": "Paste or add this DNA to the SIM9000 vat if you want to bias the vat itself, not only gene expression.",
    }
    manifest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def copy_seed_to_clipboard() -> bool:
    try:
        import tkinter as tk
        root = tk.Tk(); root.withdraw()
        root.clipboard_clear(); root.clipboard_append(EXPLODING_FINISHER_SEED_DNA)
        root.update(); root.destroy()
        return True
    except Exception:
        return False
