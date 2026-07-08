#!/usr/bin/env python3
"""Direct Horsey DNA editor helpers for CaseOh90000.

This module is deliberately separate from the genes.xml expression-profile system.
It edits/generates normal 40-line Horsey DNA strings that users can paste into
CRISPR, SIM9000/vat workflows, text files, Discord, or notepad.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from sim_gene_profiles import HELIX_GENE_NAMES

BASES = ["A", "T", "C", "G"]
HELIX_LENGTHS: Dict[str, int] = {f"{i:02d}": len(row) for i, row in enumerate(HELIX_GENE_NAMES)}
DNA_RE = re.compile(r"^\s*(\d{2})\s*:\s*([ATCGatcg]+)\s*$")

# Known direct DNA presets. These set *bases*, not genes.xml expression values.
# Many community archetypes are extremely launch-angle sensitive, so these are
# intentionally small/transparent. Users can expand the helix editor and see the
# exact bases that changed.
DIRECT_PRESETS: Dict[str, Dict[Tuple[str, int], str]] = {
    "Clean speed core": {
        ("18", 0): "T",   # narcolepsy safe/non-G is enough; T works well in known racers
        ("18", 1): "T",   # SPEED_FACTOR
        ("18", 4): "A",   # SPINAL_LOCO
        ("18", 10): "T",  # LOCO_SYNC
        ("08", 1): "T",   # LEG_LENGTH
        ("08", 4): "C",   # LEG_STRENGTH
        ("04", 9): "G",   # BREAK_FORCE low
    },
    "Fast wheeled horse": {
        ("18", 0): "T", ("18", 1): "T", ("18", 4): "A", ("18", 10): "T",
        ("08", 1): "T", ("08", 2): "A", ("08", 4): "C",
        ("01", 3): "T",  # circular legs
        ("01", 4): "A",  # circular feet in the user-tested foot-circle edit
        ("04", 9): "G",
    },
    "Oval wheel roller": {
        ("18", 0): "T", ("18", 1): "T", ("18", 4): "A", ("18", 10): "T",
        ("01", 3): "T", ("01", 4): "A",
        ("08", 1): "T", ("08", 2): "A", ("08", 3): "C", ("08", 4): "C",
        ("08", 7): "C", ("08", 8): "A", ("08", 9): "C",
        ("04", 9): "G",
    },
    "Tail launcher": {
        ("18", 0): "T", ("18", 1): "T", ("18", 4): "A", ("18", 10): "T",
        ("07", 1): "T", ("07", 2): "T", ("07", 3): "G", ("07", 7): "C",
        ("02", 1): "T", ("02", 4): "A", ("02", 5): "G",
        ("04", 9): "G",
    },
    "Tiny car": {
        ("18", 0): "T", ("18", 1): "T", ("18", 4): "A", ("18", 10): "T",
        ("01", 3): "T", ("01", 4): "A",
        ("08", 1): "T", ("08", 2): "A", ("08", 4): "C",
        ("09", 1): "A", ("09", 3): "A", ("04", 9): "G",
        ("06", 0): "A", ("06", 2): "A",
    },
    "Launch-angle tire racer": {
        # Small transparent seed inspired by the user's current best: keep wheel leg,
        # backwards/tiny foot contact, max speed core, low brake. This is not meant
        # to overwrite the whole horse; it gives the editor useful toggles.
        ("18", 0): "T", ("18", 1): "T", ("18", 4): "A",
        ("01", 3): "T", ("01", 4): "C",
        ("08", 1): "T", ("08", 2): "A", ("08", 4): "C",
        ("09", 1): "A", ("09", 5): "T",
        ("04", 3): "A", ("04", 9): "G",
    },
}


def blank_genome(fill: str = "A") -> Dict[str, List[str]]:
    fill = (fill or "A").upper()[0]
    if fill not in BASES:
        fill = "A"
    return {h: [fill * n, fill * n] for h, n in HELIX_LENGTHS.items()}


def normalize_dna(text: str) -> Tuple[bool, str, Dict[str, List[str]]]:
    """Parse a 40-line Horsey DNA string into {helix: [strand1, strand2]}.

    Returns (ok, message, genome). The returned genome is safe to edit even when
    ok is False; missing helixes are filled with A's.
    """
    genome = blank_genome("A")
    counts = {h: 0 for h in HELIX_LENGTHS}
    errors: List[str] = []
    for lineno, raw in enumerate((text or "").splitlines(), 1):
        if not raw.strip():
            continue
        m = DNA_RE.match(raw)
        if not m:
            errors.append(f"line {lineno}: expected 00:ATCG... format")
            continue
        h, seq = m.group(1), m.group(2).upper()
        if h not in HELIX_LENGTHS:
            errors.append(f"line {lineno}: unknown helix {h}")
            continue
        if len(seq) != HELIX_LENGTHS[h]:
            errors.append(f"line {lineno}: helix {h} expected length {HELIX_LENGTHS[h]}, got {len(seq)}")
            continue
        if any(ch not in BASES for ch in seq):
            errors.append(f"line {lineno}: only A/T/C/G are allowed")
            continue
        if counts[h] >= 2:
            errors.append(f"line {lineno}: helix {h} already has two strands")
            continue
        genome[h][counts[h]] = seq
        counts[h] += 1
    for h in sorted(HELIX_LENGTHS):
        if counts[h] != 2:
            errors.append(f"helix {h}: expected two strands, got {counts[h]}")
    if errors:
        return False, "; ".join(errors[:8]) + (" ..." if len(errors) > 8 else ""), genome
    return True, "DNA is valid.", genome


def format_dna(genome: Dict[str, List[str]]) -> str:
    lines: List[str] = []
    for i in range(20):
        h = f"{i:02d}"
        strands = genome.get(h, ["A" * HELIX_LENGTHS[h], "A" * HELIX_LENGTHS[h]])
        for strand in strands[:2]:
            seq = ''.join(ch if ch in BASES else 'A' for ch in str(strand).upper())
            seq = (seq + "A" * HELIX_LENGTHS[h])[:HELIX_LENGTHS[h]]
            lines.append(f"{h}:{seq}")
    return "\n".join(lines)


def dna_hash(text: str) -> str:
    ok, _msg, genome = normalize_dna(text)
    normalized = format_dna(genome)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def set_position(genome: Dict[str, List[str]], helix: str, pos: int, base: str, strands: str = "both") -> None:
    if helix not in HELIX_LENGTHS:
        raise KeyError(helix)
    if pos < 0 or pos >= HELIX_LENGTHS[helix]:
        raise IndexError(pos)
    base = base.upper()
    if base not in BASES:
        raise ValueError(base)
    targets = [0, 1] if strands == "both" else ([0] if strands in {"top", "0", 0} else [1])
    for idx in targets:
        seq = list(genome[helix][idx])
        seq[pos] = base
        genome[helix][idx] = ''.join(seq)


def dna_lock_key(helix: str, pos: int, strand: int) -> str:
    """Stable settings key for a single locked DNA base."""
    h = f"{int(helix):02d}"
    return f"{h}:{int(pos)}:{int(strand)}"


def parse_dna_lock_key(key: str) -> Tuple[str, int, int]:
    parts = str(key).split(":")
    if len(parts) != 3:
        raise ValueError(key)
    helix = f"{int(parts[0]):02d}"
    pos = int(parts[1])
    strand = int(parts[2])
    if helix not in HELIX_LENGTHS:
        raise ValueError(key)
    if pos < 0 or pos >= HELIX_LENGTHS[helix]:
        raise ValueError(key)
    if strand not in (0, 1):
        raise ValueError(key)
    return helix, pos, strand


def normalize_dna_locks(raw: Any) -> Dict[str, str]:
    """Return only valid partial DNA locks from saved/user data."""
    if not isinstance(raw, dict):
        return {}
    locks: Dict[str, str] = {}
    for key, value in raw.items():
        base = str(value or "").upper()[:1]
        if base not in BASES:
            continue
        try:
            helix, pos, strand = parse_dna_lock_key(str(key))
        except Exception:
            continue
        locks[dna_lock_key(helix, pos, strand)] = base
    return locks


def set_dna_lock(locks: Dict[str, str], helix: str, pos: int, strand: int, base: str) -> None:
    base = str(base or "").upper()[:1]
    if base not in BASES:
        raise ValueError(base)
    parse_dna_lock_key(dna_lock_key(helix, pos, strand))
    locks[dna_lock_key(helix, pos, strand)] = base


def apply_dna_locks(genome: Dict[str, List[str]], locks: Dict[str, str]) -> int:
    """Apply partial locked bases to a parsed genome and return changed count."""
    changed = 0
    for key, base in normalize_dna_locks(locks).items():
        helix, pos, strand = parse_dna_lock_key(key)
        seq = list(genome[helix][strand])
        if seq[pos] != base:
            seq[pos] = base
            genome[helix][strand] = ''.join(seq)
            changed += 1
    return changed


def apply_direct_preset(genome: Dict[str, List[str]], preset: str, strands: str = "both") -> List[str]:
    changed: List[str] = []
    for (helix, pos), base in DIRECT_PRESETS.get(preset, {}).items():
        gene = HELIX_GENE_NAMES[int(helix)][pos]
        set_position(genome, helix, pos, base, strands=strands)
        if strands == "both":
            label = f"{base}/{base}"
        elif strands in {"top", "0", 0}:
            label = f"{base}/unchanged"
        else:
            label = f"unchanged/{base}"
        changed.append(f"H{helix} P{pos:02d} {gene} -> {label}")
    return changed


def load_exploding_seed() -> str:
    try:
        from exploding_seed import EXPLODING_FINISHER_SEED_DNA
        return EXPLODING_FINISHER_SEED_DNA.strip()
    except Exception:
        return ""


def write_dna_file(branch: Path, text: str, name: str = "caseoh90000_custom_dna.txt") -> Path:
    out_dir = Path(branch) / "CaseOh90000_seed_dna"
    out_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("._") or "caseoh90000_custom_dna.txt"
    if not safe.lower().endswith(".txt"):
        safe += ".txt"
    out = out_dir / safe
    ok, msg, genome = normalize_dna(text)
    if not ok:
        raise ValueError(msg)
    out.write_text(format_dna(genome) + "\n", encoding="utf-8")
    return out


# Public labels used by the UI.
DIRECT_PRESET_NAMES = ["Do not change", *DIRECT_PRESETS.keys(), "Exploding finisher seed"]
