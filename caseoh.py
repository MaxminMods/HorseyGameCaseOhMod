#!/usr/bin/env python3
"""Easter Egg support for the CaseOh90000 local mod branch.

Branch-only and reversible. The public UI intentionally does not describe what
this toggle does.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple
import json
import shutil
import xml.etree.ElementTree as ET

# Easter Egg target list. Kept intentionally terse.
CASEOH_TARGETS: Dict[str, Dict[str, Any]] = {

    "SIZE": {"mode": "max"},
    "GIANT_DWARF": {"mode": "max"},
    "SKINNY": {"mode": "min"},
    "ASPECT": {"mode": "max"},
    "CHEST_BIG": {"mode": "max"},
    "CHEST_SMALL": {"mode": "min"},
    "GUT": {"mode": "max"},
    "DERRIERE": {"mode": "max"},
    "BONES": {"mode": "max"},
    "BONES2": {"mode": "max"},
    "OSTODERM": {"mode": "max"},
    "OSTO_SIZE": {"mode": "max"},

    "LEG_COUNT": {"mode": "max"},
    "LEG_LENGTH": {"mode": "max"},
    "LEG_STRETCH": {"mode": "max"},
    "LEG_STRETCH2": {"mode": "max"},
    "LEG_PENCIL": {"mode": "min"},
    "LEG_HAS_FOOT": {"mode": "max"},
    "HAS_FOOT": {"mode": "max"},
    "FOOT_SIZE": {"mode": "max"},
    "FOOT_CLOWN": {"mode": "max"},
    "FOOT_THICKNESS": {"mode": "max"},
    "FOOT_TOE": {"mode": "max"},

    "ARM_LENGTH": {"mode": "max"},
    "ARM_STRETCH": {"mode": "max"},
    "ARM_STRETCH2": {"mode": "max"},
    "ARM_NODE_SCALE": {"mode": "max"},
    "ARM_HAS_HAND": {"mode": "max"},
    "HAS_HAND": {"mode": "max"},
    "HAND_WIDTH": {"mode": "max"},
    "HAND_LENGTH": {"mode": "max"},
    "HAND_FINGER": {"mode": "max"},

    "NECK_LENGTH": {"mode": "max"},
    "NECK_GIRAFFE": {"mode": "max"},
    "NECK_THICKNESS": {"mode": "max"},
    "NECK_ONTOP": {"mode": "max"},
    "NECK_SLOUCH": {"mode": "max"},
    "HEAD_SIZE": {"mode": "max"},
    "HEAD_GIANT": {"mode": "max"},
    "HEAD_SHRUNK": {"mode": "min"},
    "HEAD_X_GROWTH": {"mode": "max"},
    "HEAD_Y_GROWTH": {"mode": "max"},
    "HEAD_ASPECT": {"mode": "max"},
    "HEAD_SQUARE": {"mode": "max"},
    "HEAD_THICK_SKULL": {"mode": "max"},
    "BUGEYE": {"mode": "max"},
    "EYEBOX_SIZE": {"mode": "max"},
    "EYE_SIZE": {"mode": "max"},
    "PUPIL_SIZE": {"mode": "max"},
    "BROW_SIZE": {"mode": "max"},
    "EAR_SIZE": {"mode": "max"},
    "EAR_ASPECT": {"mode": "max"},
    "EAR_X": {"mode": "max"},
    "EAR_FLOP": {"mode": "max"},
    "MOUTH_SIZE": {"mode": "max"},
    "NOSE_SIZE": {"mode": "max"},
    "NOSE_Y": {"mode": "max"},

    "TAIL_EXISTS": {"mode": "max"},
    "TAIL_SIZE": {"mode": "max"},
    "TAIL_SHORT": {"mode": "min"},
    "TAIL_ASPECT": {"mode": "max"},
    "TAIL_SEGMENTS": {"mode": "max"},
    "TAIL_BOTTOM": {"mode": "max"},
    "HAS_ANTLERS": {"mode": "max"},
    "ANTLER_W": {"mode": "max"},
    "ANTLER_H": {"mode": "max"},
    "ANTLER_TAPER": {"mode": "max"},
    "ANTLER_POM": {"mode": "max"},
    "ANTLER_SCALEH": {"mode": "max"},
    "ANTLER_SCALEW": {"mode": "max"},
    "ANTLER_T1": {"mode": "max"},
    "ANTLER_T2": {"mode": "max"},
    "HAT_EXISTS": {"mode": "max"},
    "HAT_SIZE": {"mode": "max"},
    "HAT_ASPECT": {"mode": "max"},
    "HAT_TAPER": {"mode": "max"},
    "HAT_POM": {"mode": "max"},
    "HAT_BACK_SCALE": {"mode": "max"},
    "HAT_FRONT_SCALE": {"mode": "max"},
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
        "version": "CaseOh90000-1.3-easter-egg",
        "patched_gene_count": patched,
        "missing_gene_count": len(missing),
    }
    (branch / "caseoh_mode_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return {"enabled": True, "restored": False, "patched": True, "patched_gene_count": patched}


def caseoh_status(branch: Path) -> Dict[str, Any]:
    genes, backup = _paths(Path(branch))
    return {"genes_xml_exists": genes.exists(), "backup_exists": backup.exists(), "target_gene_count": len(CASEOH_TARGETS)}
