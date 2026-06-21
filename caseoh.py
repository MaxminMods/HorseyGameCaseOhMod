#!/usr/bin/env python3
"""caseOh mOde support for the CaseOh90000 local mod branch.

CaseOh90000 keeps the surprise/easter-egg presentation and retuned the phenotype
patch so it concentrates on stomach/body/limb scale instead of spreading across
head, tail, hat, antler, face, and other unrelated shape genes.

The patch is branch-only and reversible. Disabling restores the exact backup.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple
import json
import shutil
import xml.etree.ElementTree as ET

# caseOh target list.
#
# Design goal from testing feedback:
#   - keep the working SIM9000 mechanics unchanged;
#   - make the gag phenotype more obvious;
#   - force stomach/body/limb scale strongly upward;
#   - leave most other traits variable so each result still has surprise/variety.
#
# Values here intentionally go beyond the vanilla allele max for the core body /
# stomach / limb genes. An earlier caseOh test merely flattened each target gene
# to its normal maximum, which was funny but not dramatic enough.
#
# The mode field controls how alleles are rewritten:
#   explicit = set every allele to the listed target value
#   min      = set every allele to the original minimum value
#   max      = set every allele to the original maximum value
CASEOH_TARGETS: Dict[str, Dict[str, Any]] = {
    # Core body / torso / stomach.
    "SIZE": {"mode": "explicit", "value": 220},
    "GIANT_DWARF": {"mode": "explicit", "value": 220},
    "SKINNY": {"mode": "explicit", "value": 35},
    "CHEST_BIG": {"mode": "explicit", "value": 180},
    "CHEST_SMALL": {"mode": "explicit", "value": 130},
    "GUT": {"mode": "explicit", "value": 180},
    "DERRIERE": {"mode": "explicit", "value": 160},

    # Limb scale. Avoid locomotion timing/strength genes so fast SIM builds can
    # still emerge naturally from the genome search.
    "LEG_LENGTH": {"mode": "explicit", "value": 190},
    "LEG_STRETCH": {"mode": "explicit", "value": 28},
    "LEG_STRETCH2": {"mode": "explicit", "value": 32},
    "LEG_PENCIL": {"mode": "explicit", "value": 0},

    "ARM_LENGTH": {"mode": "explicit", "value": 190},
    "ARM_STRETCH": {"mode": "explicit", "value": 28},
    "ARM_STRETCH2": {"mode": "explicit", "value": 32},
    "ARM_NODE_SCALE": {"mode": "explicit", "value": 190},

    # Extremities count as limb size, but existence/count/type stay variable.
    "FOOT_SIZE": {"mode": "explicit", "value": 80},
    "FOOT_CLOWN": {"mode": "explicit", "value": 80},
    "FOOT_THICKNESS": {"mode": "explicit", "value": 70},
    "FOOT_TOE": {"mode": "explicit", "value": 160},
    "HAND_WIDTH": {"mode": "explicit", "value": 70},
    "HAND_LENGTH": {"mode": "explicit", "value": 80},
    "HAND_FINGER": {"mode": "explicit", "value": 180},
}

# Compatibility alias for older imports/status wording.
CASEOH_SIZE_TARGETS = {k: v.get("mode", "explicit") for k, v in CASEOH_TARGETS.items()}


def _paths(branch: Path) -> Tuple[Path, Path]:
    genes = branch / "data" / "genes.xml"
    backup = branch / "data" / "genes.xml.caseoh_original"
    return genes, backup


def ensure_caseoh_backup(branch: Path) -> Path:
    genes, backup = _paths(branch)
    if not genes.exists():
        raise FileNotFoundError(genes)
    if not backup.exists():
        shutil.copy2(genes, backup)
    return backup


def restore_caseoh(branch: Path) -> int:
    genes, backup = _paths(branch)
    if backup.exists():
        shutil.copy2(backup, genes)
        for report_name in ("caseoh_mode_report.json", "caseoh_size_mode_report.json"):
            report = branch / report_name
            if report.exists():
                report.unlink()
        return 1
    return 0


def _target_value(elem: ET.Element, spec: Dict[str, Any]) -> int:
    vals = [int(elem.attrib[f"g{i}"]) for i in range(4)]
    mode = str(spec.get("mode", "explicit")).lower()
    if mode == "min":
        return min(vals)
    if mode == "max":
        return max(vals)
    return int(spec["value"])


def apply_caseoh_mode(branch: Path, enabled: bool) -> Dict[str, Any]:
    branch = Path(branch)
    genes, backup = _paths(branch)
    if not genes.exists():
        raise FileNotFoundError(genes)

    if not enabled:
        restored = restore_caseoh(branch)
        return {"enabled": False, "restored": bool(restored), "patched_genes": 0, "missing_genes": []}

    ensure_caseoh_backup(branch)
    tree = ET.parse(backup)
    root = tree.getroot()
    by_name = {elem.attrib.get("name", ""): elem for elem in root.findall("gene")}

    patched = 0
    missing = []
    changed = []
    for gene, spec in CASEOH_TARGETS.items():
        elem = by_name.get(gene)
        if elem is None:
            missing.append(gene)
            continue
        try:
            original_vals = [int(elem.attrib[f"g{i}"]) for i in range(4)]
            target = _target_value(elem, spec)
        except Exception:
            missing.append(gene)
            continue

        for i in range(4):
            elem.attrib[f"g{i}"] = str(target)
        elem.attrib["caseoh"] = "CaseOh90000"
        changed.append({
            "gene": gene,
            "target_value": target,
            "original_values": original_vals,
            "mode": spec.get("mode", "explicit"),
        })
        patched += 1

    try:
        ET.indent(tree, space="    ")
    except Exception:
        pass
    tree.write(genes, encoding="unicode", short_empty_elements=True)

    # Keep the report deliberately minimal. It verifies that the toggle applied
    # without dumping the visual recipe into the UI.
    report = {
        "enabled": True,
        "patched": True,
        "version": "CaseOh90000-1.0",
        "patched_gene_count": patched,
        "missing_gene_count": len(missing),
    }
    (branch / "caseoh_mode_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return {"enabled": True, "restored": False, "patched": True, "patched_gene_count": patched}


def caseoh_status(branch: Path) -> Dict[str, Any]:
    genes, backup = _paths(Path(branch))
    return {"genes_xml_exists": genes.exists(), "backup_exists": backup.exists(), "target_gene_count": len(CASEOH_TARGETS)}
