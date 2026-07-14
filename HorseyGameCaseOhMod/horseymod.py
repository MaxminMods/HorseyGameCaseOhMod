#!/usr/bin/env python3
"""
HorseyGameCaseOhMod v2 Mod Branch Tool

Creates and patches a COPY of Horsey Game. It never redistributes game files and
keeps Horsey.exe.original in the mod branch for restore.

HorseyGameCaseOhMod v2 philosophy:
- Keep the proven effective behavior by default: remove the 5.0s barrier and improve
  displayed precision.
- Start with the visible SIM9000 Intensity controls enabled so fresh branches apply
  the selected generation/race-slot values right away.
- If experimental search controls are disabled, CaseOh90000 writes those search bytes back
  to stock/original values when patching, so it can recover from a too-aggressive
  over-tuned branch.
- Add an optional branch-only Easter Egg toggle.
"""
from __future__ import annotations

import argparse
import json
import shutil
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sim_gene_profiles import apply_gene_stack, restore_gene_xml, default_gene_lab_settings, SPECIES_PROFILES, RACING_PRESETS, force_caseoh_override_settings
from exploding_seed import apply_exploding_sim_overrides, is_exploding_requested, write_exploding_seed_files
from caseoh_art import apply_caseoh_art, restore_caseoh_art
from caseoh_arena import prepare_caseoh_arena_branch, restore_caseoh_arena_branch, launch_horsey_branch_with_native

STEAM_APPID = "3602570"
DEFAULT_SOURCE = r"C:\Program Files (x86)\Steam\steamapps\common\Horsey Game"
DEFAULT_BRANCH = str(Path.home() / "Desktop" / "projects" / "CaseOh90000_BRANCH")

# Byte signatures are version-specific to the uploaded/current build, but scanned
# rather than applied at blind offsets.
SIG_EARLY_FINISH = "8B 87 84 02 00 00 3D ?? ?? ?? ?? 7D 62 C7 86 28 02 00 00 20 4E 00 00 48 8D 0D"
SIG_NO_PROGRESS = "41 81 7C 06 04 ?? ?? ?? ?? 7E 2B 48 8B 87 A0 02 00 00"
SIG_MAX_SIM_FRAMES = "81 BF 84 02 00 00 ?? ?? ?? ?? 0F 8D 2B 03 00 00"
SIG_VALID_RESULT_MAX = "81 B8 28 02 00 00 ?? ?? ?? ?? 7D 28"

# Optional search/optimizer knobs. CaseOh90000 scans these and restores stock
# values when Intensity controls are disabled.
SIG_INIT_SEARCH_BUDGETS = "C7 86 A8 06 00 00 ?? ?? ?? ?? C7 86 AC 06 00 00 ?? ?? ?? ??"
SIG_RAM_GATED_SEARCH_BUDGETS = (
    "BA ?? ?? ?? ?? 89 83 94 06 00 00 "
    "B8 ?? ?? ?? ?? 0F 45 C2 "
    "BA ?? ?? ?? ?? 89 83 A8 06 00 00 "
    "B8 ?? ?? ?? ?? 0F 45 C2 48 8D 15 ?? ?? ?? ?? 89 83 AC 06 00 00"
)
SIG_SIM_WORK_PER_UI_UPDATE = "8B 45 67 FF C0 89 45 67 3D ?? ?? ?? ?? 0F 8C C3 FE FF FF"
SIG_ELITE_PARENT_PERCENT = "44 8B 87 AC 06 00 00 41 6B C8 ?? B8 1F 85 EB 51"
SIG_MIN_GENERATION_FOR_DISK = "44 8B 87 88 02 00 00 41 83 F8 ?? 0F 8C"
SIG_RACE_DISPLAY_LIMIT = "8B 87 AC 06 00 00 99 83 E2 03 44 8D 0C 02 41 C1 F9 02"
SIG_GENERATION_DISPLAY_LIMIT = "44 8B 87 88 02 00 00 41 FF C0 44 8B 8F A8 06 00 00 48 8D 15 ?? ?? ?? ?? 48 8D 4D ?? E8"
SIG_RACE_DISPLAY_CURRENT = "44 8B 87 78 02 00 00 41 FF C0 48 8D 15"
SIG_GENERATION_DISPLAY_CURRENT = "44 8B 87 88 02 00 00 41 FF C0 44 8B 8F A8 06 00 00 48 8D 15"

FMT_ORIGINAL = b"T:%.1f\x00"
FMT_BY_PRECISION = {1: b"T:%.1f\x00", 2: b"T:%.2f\x00", 3: b"T:%.3f\x00"}

SEARCH_KEYS_I32 = [
    "initial_generation_limit",
    "initial_genepool_size",
    "sim_work_per_ui_update",
]
SEARCH_KEYS_U8 = [
    "elite_parent_percent",
    "min_generation_for_disk",
]
ADVANCED_FLOAT_KEYS = [
    "finish_metric_threshold",
    "display_time_divisor",
    "result_score_scale",
    "invalid_score_sentinel",
]
DISPLAY_NUMERATOR_KEYS = ["generation_display_current"]


@dataclass
class Section:
    name: str
    rva: int
    vsize: int
    raw: int
    raw_size: int


def parse_pe_sections(data: bytes) -> Tuple[int, List[Section]]:
    if data[:2] != b"MZ":
        raise ValueError("not a PE/MZ executable")
    peoff = struct.unpack_from("<I", data, 0x3C)[0]
    if data[peoff:peoff + 4] != b"PE\0\0":
        raise ValueError("bad PE signature")
    coff = peoff + 4
    _, nsec, _, _, _, opt_size, _ = struct.unpack_from("<HHIIIHH", data, coff)
    opt = coff + 20
    magic = struct.unpack_from("<H", data, opt)[0]
    if magic == 0x20B:
        image_base = struct.unpack_from("<Q", data, opt + 24)[0]
    elif magic == 0x10B:
        image_base = struct.unpack_from("<I", data, opt + 28)[0]
    else:
        raise ValueError(f"unknown optional header magic {magic:#x}")
    sec0 = opt + opt_size
    sections: List[Section] = []
    for i in range(nsec):
        off = sec0 + 40 * i
        name = data[off:off + 8].split(b"\0", 1)[0].decode("ascii", errors="replace")
        vsize, rva, raw_size, raw = struct.unpack_from("<IIII", data, off + 8)
        sections.append(Section(name=name, rva=rva, vsize=vsize, raw=raw, raw_size=raw_size))
    return image_base, sections


def file_to_rva(file_off: int, sections: List[Section]) -> int:
    for s in sections:
        if s.raw <= file_off < s.raw + max(s.raw_size, 1):
            return s.rva + (file_off - s.raw)
    raise ValueError(f"file offset {file_off:#x} is not inside any section")


def parse_sig(sig: str) -> Tuple[bytes, bytes]:
    vals: List[int] = []
    mask: List[int] = []
    for tok in sig.split():
        if tok in {"?", "??"}:
            vals.append(0)
            mask.append(0)
        else:
            vals.append(int(tok, 16))
            mask.append(0xFF)
    return bytes(vals), bytes(mask)


def find_pattern(data: bytes, sig: str) -> List[int]:
    vals, mask = parse_sig(sig)
    n = len(vals)
    hits: List[int] = []
    for i in range(0, len(data) - n + 1):
        if mask[0] and data[i] != vals[0]:
            continue
        for j in range(n):
            if mask[j] and data[i + j] != vals[j]:
                break
        else:
            hits.append(i)
    return hits


def require_one(name: str, hits: List[int]) -> int:
    if len(hits) != 1:
        raise RuntimeError(f"expected exactly one match for {name}, found {len(hits)}: {[hex(h) for h in hits[:10]]}")
    return hits[0]


def maybe_one(name: str, hits: List[int], warnings: List[str]) -> Optional[int]:
    if len(hits) == 1:
        return hits[0]
    warnings.append(f"optional patch point not used: {name}; matches={len(hits)}")
    return None


def read_i32(data: bytes, off: int) -> int:
    return struct.unpack_from("<i", data, off)[0]


def read_f32(data: bytes, off: int) -> float:
    return struct.unpack_from("<f", data, off)[0]


def make_patch_entry(name: str, desc: str, file_off: int, sections: List[Section], kind: str, original: Any) -> Dict[str, Any]:
    return {
        "name": name,
        "description": desc,
        "file_off": file_off,
        "rva": file_to_rva(file_off, sections),
        "kind": kind,
        "original": original,
    }


def scan_exe(exe: Path) -> Dict[str, Any]:
    data = exe.read_bytes()
    image_base, sections = parse_pe_sections(data)
    warnings: List[str] = []

    early = require_one("early finish 300-frame barrier", find_pattern(data, SIG_EARLY_FINISH))
    no_prog = require_one("no-progress cull frame threshold", find_pattern(data, SIG_NO_PROGRESS))
    max_frames = require_one("max sim frame budget", find_pattern(data, SIG_MAX_SIM_FRAMES))
    valid_max = require_one("valid result max threshold", find_pattern(data, SIG_VALID_RESULT_MAX))

    init_budgets = maybe_one("initial SIM9000 generation/genepool budgets", find_pattern(data, SIG_INIT_SEARCH_BUDGETS), warnings)
    ram_budgets = maybe_one("SIM9000 RAM-gated generation/genepool budgets", find_pattern(data, SIG_RAM_GATED_SEARCH_BUDGETS), warnings)
    work_per_update = maybe_one("SIM9000 work batches per UI update", find_pattern(data, SIG_SIM_WORK_PER_UI_UPDATE), warnings)
    elite_parent = maybe_one("SIM9000 elite parent percentage", find_pattern(data, SIG_ELITE_PARENT_PERCENT), warnings)
    min_gen_disk = maybe_one("SIM9000 minimum generation before disk/result", find_pattern(data, SIG_MIN_GENERATION_FOR_DISK), warnings)
    race_display = maybe_one("SIM9000 visible race-total display", find_pattern(data, SIG_RACE_DISPLAY_LIMIT), warnings)
    generation_display = maybe_one("SIM9000 visible generation-total display", find_pattern(data, SIG_GENERATION_DISPLAY_LIMIT), warnings)
    race_current = maybe_one("SIM9000 visible race-current display", find_pattern(data, SIG_RACE_DISPLAY_CURRENT), warnings)
    generation_current = maybe_one("SIM9000 visible generation-current display", find_pattern(data, SIG_GENERATION_DISPLAY_CURRENT), warnings)

    fmt_hits = [data.find(v) for v in FMT_BY_PRECISION.values()]
    fmt_hits = [x for x in fmt_hits if x >= 0]
    fmt = min(fmt_hits) if fmt_hits else -1
    if fmt < 0:
        raise RuntimeError("could not find SIM9000 time format string T:%.1f/T:%.2f/T:%.3f")

    # Nearby float values in/near the SIM9000 display/result path. These are advanced.
    window = data[fmt:fmt + 512]

    def near_float(value: float, start: int = 0) -> Optional[int]:
        needle = struct.pack("<f", value)
        rel = window.find(needle, start)
        return None if rel < 0 else fmt + rel

    finish_metric = near_float(25.0)
    time_divisor = near_float(60.0)
    score_scale = near_float(400.0)
    invalid_score = near_float(20000.0)

    patches: Dict[str, Dict[str, Any]] = {}
    patches["min_finish_frames"] = make_patch_entry(
        "min_finish_frames",
        "Minimum finish frames before SIM9000 accepts a horse. Original 300 = 5.0 seconds. Set 0 to remove the sub-5 cull.",
        early + 7,
        sections,
        "i32",
        read_i32(data, early + 7),
    )
    patches["early_finish_branch"] = make_patch_entry(
        "early_finish_branch",
        "Branch after the min-finish comparison. Usually leave unchanged; threshold=0 is enough.",
        early + 11,
        sections,
        "bytes2",
        data[early + 11:early + 13].hex(" "),
    )
    patches["no_progress_frames"] = make_patch_entry(
        "no_progress_frames",
        "Frames without enough progress before a sim horse is treated as stalled/glitchy. Original is normally 300.",
        no_prog + 5,
        sections,
        "i32",
        read_i32(data, no_prog + 5),
    )
    patches["max_sim_frames"] = make_patch_entry(
        "max_sim_frames",
        "Maximum frame budget for a candidate. Higher allows very slow finishers; lower rejects slow/late-starting outliers.",
        max_frames + 6,
        sections,
        "i32",
        read_i32(data, max_frames + 6),
    )
    patches["valid_result_max"] = make_patch_entry(
        "valid_result_max",
        "Internal cutoff for including results. Raising this can make SIM9000 accept bad/slow winners; original is usually best.",
        valid_max + 6,
        sections,
        "i32",
        read_i32(data, valid_max + 6),
    )
    patches["time_format"] = make_patch_entry(
        "time_format",
        "SIM9000 displayed time format. CaseOh90000 default is T:%.3f for more precision.",
        fmt,
        sections,
        "fmt6",
        data[fmt:fmt + 7].decode("ascii", errors="replace"),
    )

    if init_budgets is not None:
        patches["initial_generation_limit"] = make_patch_entry(
            "initial_generation_limit",
            "Experimental search depth: generations per SIM9000 run. Original 16. Higher searches longer but is not guaranteed to produce faster real racers.",
            init_budgets + 6,
            sections,
            "i32",
            read_i32(data, init_budgets + 6),
        )
        patches["initial_genepool_size"] = make_patch_entry(
            "initial_genepool_size",
            "Experimental sample width/population size. Original 40. Keep multiple of 4. More samples can help, but too high can slow/crash.",
            init_budgets + 16,
            sections,
            "i32",
            read_i32(data, init_budgets + 16),
        )
    if ram_budgets is not None:
        patches["ram_generation_limit_upgraded"] = make_patch_entry(
            "ram_generation_limit_upgraded",
            "SIM9000 RAM-upgrade generation limit used when a run resets/starts. CaseOh90000 mirrors the selected generation count here.",
            ram_budgets + 1,
            sections,
            "i32",
            read_i32(data, ram_budgets + 1),
        )
        patches["ram_generation_limit_base"] = make_patch_entry(
            "ram_generation_limit_base",
            "SIM9000 no-RAM-upgrade generation limit used when a run resets/starts. CaseOh90000 mirrors the selected generation count here.",
            ram_budgets + 12,
            sections,
            "i32",
            read_i32(data, ram_budgets + 12),
        )
        patches["ram_genepool_size_upgraded"] = make_patch_entry(
            "ram_genepool_size_upgraded",
            "SIM9000 RAM-upgrade horse pool used when a run resets/starts. CaseOh90000 mirrors the selected horse/race-slot count here.",
            ram_budgets + 20,
            sections,
            "i32",
            read_i32(data, ram_budgets + 20),
        )
        patches["ram_genepool_size_base"] = make_patch_entry(
            "ram_genepool_size_base",
            "SIM9000 no-RAM-upgrade horse pool used when a run resets/starts. CaseOh90000 mirrors the selected horse/race-slot count here.",
            ram_budgets + 31,
            sections,
            "i32",
            read_i32(data, ram_budgets + 31),
        )
    if work_per_update is not None:
        patches["sim_work_per_ui_update"] = make_patch_entry(
            "sim_work_per_ui_update",
            "Experimental speed knob: internal work batches per visible update. Original 240. Usually affects UI speed more than horse quality.",
            work_per_update + 9,
            sections,
            "i32",
            read_i32(data, work_per_update + 9),
        )
    if elite_parent is not None:
        patches["elite_parent_percent"] = make_patch_entry(
            "elite_parent_percent",
            "Experimental selection pressure/diversity. Original 25. Lower can over-converge; higher preserves diversity but may be slower.",
            elite_parent + 10,
            sections,
            "u8",
            data[elite_parent + 10],
        )
    if min_gen_disk is not None:
        patches["min_generation_for_disk"] = make_patch_entry(
            "min_generation_for_disk",
            "Experimental output gate. Original 9. Do not lower casually: generation 1 can output weak/slow horses before optimization improves.",
            min_gen_disk + 10,
            sections,
            "u8",
            data[min_gen_disk + 10],
        )
    if generation_display is not None:
        patches["generation_display_limit"] = make_patch_entry(
            "generation_display_limit",
            "Display-only total shown in the SIM9000 G:x/total readout. CaseOh90000 can mirror the selected generation limit here.",
            generation_display + 10,
            sections,
            "bytes7",
            data[generation_display + 10:generation_display + 17].hex(" "),
        )
    if race_display is not None:
        patches["race_display_limit"] = make_patch_entry(
            "race_display_limit",
            "Display-only total shown in the SIM9000 R:x/total readout. CaseOh90000 can mirror the selected race-slot total here.",
            race_display,
            sections,
            "bytes18",
            data[race_display:race_display + 18].hex(" "),
        )
    if race_current is not None:
        patches["race_display_current"] = make_patch_entry(
            "race_display_current",
            "Display-only current value shown in the SIM9000 R:current/total readout. CaseOh90000 restores this live-counter read so it follows real SIM progress.",
            race_current,
            sections,
            "bytes10",
            data[race_current:race_current + 10].hex(" "),
        )
    if generation_current is not None:
        patches["generation_display_current"] = make_patch_entry(
            "generation_display_current",
            "Display-only current value shown in the SIM9000 G:current/total readout. CaseOh90000 restores this live-counter read so it follows real SIM progress.",
            generation_current,
            sections,
            "bytes10",
            data[generation_current:generation_current + 10].hex(" "),
        )

    if finish_metric is not None:
        patches["finish_metric_threshold"] = make_patch_entry(
            "finish_metric_threshold",
            "Advanced float near finish/cull logic. Leave original unless testing a hypothesis.",
            finish_metric,
            sections,
            "f32",
            read_f32(data, finish_metric),
        )
    if time_divisor is not None:
        patches["display_time_divisor"] = make_patch_entry(
            "display_time_divisor",
            "Display-only time divisor. Original 60.0. Changing this changes units, not physics.",
            time_divisor,
            sections,
            "f32",
            read_f32(data, time_divisor),
        )
    if score_scale is not None:
        patches["result_score_scale"] = make_patch_entry(
            "result_score_scale",
            "Advanced result score scale. Leave original for baseline behavior.",
            score_scale,
            sections,
            "f32",
            read_f32(data, score_scale),
        )
    if invalid_score is not None:
        patches["invalid_score_sentinel"] = make_patch_entry(
            "invalid_score_sentinel",
            "Advanced invalid/cull sentinel. Leave original for baseline behavior.",
            invalid_score,
            sections,
            "f32",
            read_f32(data, invalid_score),
        )

    return {
        "tool_version": "HorseyGameCaseOhMod-v2",
        "exe": str(exe),
        "image_base": image_base,
        "sections": [s.__dict__ for s in sections],
        "patches": patches,
        "warnings": warnings,
        "notes": [
            "Confirmed barrier: min_finish_frames=300; 300/60 = 5.0 seconds.",
            "HorseyGameCaseOhMod v2 defaults: min_finish_frames=0, T precision=3, and Intensity controls enabled.",
            "Disabling Intensity controls restores the stock SIM9000 search values.",
        ],
    }


def copy_branch(source: Path, branch: Path, overwrite: bool = False) -> None:
    source = source.resolve()
    branch = branch.resolve()
    if not source.exists():
        raise FileNotFoundError(source)
    if not (source / "Horsey.exe").exists():
        raise FileNotFoundError(source / "Horsey.exe")
    if source == branch:
        raise ValueError("branch folder cannot be the same as the source game folder")
    if source in branch.parents:
        raise ValueError("do not create the mod branch inside the normal Horsey Game folder")
    if branch in source.parents:
        raise ValueError("normal game folder cannot be inside the mod branch folder")
    branch.parent.mkdir(parents=True, exist_ok=True)
    if branch.exists():
        if not overwrite:
            raise FileExistsError(f"branch already exists: {branch}\nUse --overwrite to rebuild it.")
        shutil.rmtree(branch)
    ignore = shutil.ignore_patterns("*.tmp", "*.bak")
    shutil.copytree(source, branch, ignore=ignore)
    (branch / "steam_appid.txt").write_text(STEAM_APPID + "\n", encoding="ascii")


def backup_exe(exe: Path) -> Path:
    backup = exe.with_name("Horsey.exe.original")
    if not backup.exists():
        shutil.copy2(exe, backup)
    return backup


def write_at(buf: bytearray, off: int, payload: bytes) -> None:
    buf[off:off + len(payload)] = payload


def original(profile: Dict[str, Any], key: str, fallback: Any) -> Any:
    return profile.get("patches", {}).get(key, {}).get("original", fallback)


def default_settings(profile: Dict[str, Any]) -> Dict[str, Any]:
    return {
        # v2 default: remove the barrier, improve precision, and enable visible Intensity settings.
        "min_finish_frames": 0,
        "display_precision": 3,
        "always_accept_early_finish": False,
        "caseoh_mode": False,
        "exploding_mode": False,
        "no_progress_frames": int(original(profile, "no_progress_frames", 300)),
        "max_sim_frames": int(original(profile, "max_sim_frames", 10800)),
        "valid_result_max": int(original(profile, "valid_result_max", 10000)),
        # Experimental search controls start enabled in v2 so fresh installs load
        # the visible SIM9000 generation/race-slot settings right away.
        "enable_search_controls": True,
        "initial_generation_limit": int(original(profile, "initial_generation_limit", 16)),
        "initial_genepool_size": int(original(profile, "initial_genepool_size", 40)),
        "sim_work_per_ui_update": int(original(profile, "sim_work_per_ui_update", 240)),
        "elite_parent_percent": int(original(profile, "elite_parent_percent", 25)),
        "min_generation_for_disk": int(original(profile, "min_generation_for_disk", 9)),
        # Advanced floats.
        "finish_metric_threshold": float(original(profile, "finish_metric_threshold", 25.0)),
        "display_time_divisor": float(original(profile, "display_time_divisor", 60.0)),
        "result_score_scale": float(original(profile, "result_score_scale", 400.0)),
        "invalid_score_sentinel": float(original(profile, "invalid_score_sentinel", 20000.0)),
    }




def apply_caseoh_sim_overrides(profile: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
    """Apply the branch-only Easter Egg SIM override."""
    s = force_caseoh_override_settings(settings)
    if bool(s.get("caseoh_mode", False)):
        # Easter Egg-specific SIM behavior.
        s["min_finish_frames"] = 600
        s["display_precision"] = 3
        s["no_progress_frames"] = 840
        s["max_sim_frames"] = 840
        s["valid_result_max"] = 30000
        s["display_time_divisor"] = 6.0
        s["enable_search_controls"] = True
        s["initial_generation_limit"] = 4
        s["initial_genepool_size"] = 24
        s["sim_work_per_ui_update"] = 3000
        s["elite_parent_percent"] = 50
        s["min_generation_for_disk"] = 1
    return s

def write_profile(branch: Path, profile: Dict[str, Any]) -> None:
    (branch / "sim9000_mod_profile.json").write_text(json.dumps(profile, indent=2), encoding="utf-8")


def write_settings(branch: Path, settings: Dict[str, Any]) -> None:
    (branch / "sim9000_mod_settings.json").write_text(json.dumps(settings, indent=2), encoding="utf-8")


def read_branch_profile(branch: Path) -> Dict[str, Any]:
    profile_path = branch / "sim9000_mod_profile.json"
    exe = branch / "Horsey.exe"
    if profile_path.exists():
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        required = {
            "generation_display_limit",
            "race_display_limit",
            "generation_display_current",
            "race_display_current",
            "ram_generation_limit_upgraded",
            "ram_generation_limit_base",
            "ram_genepool_size_upgraded",
            "ram_genepool_size_base",
        }
        if not required.issubset(set(profile.get("patches", {}))):
            scan_target = branch / "Horsey.exe.original"
            if not scan_target.exists():
                scan_target = exe
            refreshed = scan_exe(scan_target)
            profile["patches"] = refreshed.get("patches", profile.get("patches", {}))
            profile["sections"] = refreshed.get("sections", profile.get("sections", []))
            profile["image_base"] = refreshed.get("image_base", profile.get("image_base"))
            profile["warnings"] = refreshed.get("warnings", profile.get("warnings", []))
            write_profile(branch, profile)
        return profile
    profile = scan_exe(exe)
    write_profile(branch, profile)
    return profile


def normalize_settings(profile: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
    s = dict(default_settings(profile))
    s.update(settings)
    # Keep sane types/ranges.
    s["min_finish_frames"] = max(0, int(s["min_finish_frames"]))
    s["no_progress_frames"] = max(0, int(s["no_progress_frames"]))
    s["max_sim_frames"] = max(1, int(s["max_sim_frames"]))
    s["valid_result_max"] = max(1, int(s["valid_result_max"]))
    s["display_precision"] = int(s["display_precision"])
    if s["display_precision"] not in FMT_BY_PRECISION:
        raise ValueError("display_precision must be 1, 2, or 3")
    s["always_accept_early_finish"] = bool(s.get("always_accept_early_finish", False))
    s["enable_search_controls"] = bool(s.get("enable_search_controls", True))
    s["caseoh_mode"] = bool(s.get("caseoh_mode", False))
    s["exploding_mode"] = bool(s.get("exploding_mode", False))
    defaults_gl = default_gene_lab_settings()
    s["gene_lab_enabled"] = bool(s.get("gene_lab_enabled", defaults_gl["gene_lab_enabled"]))
    if s.get("species_profile") not in SPECIES_PROFILES:
        s["species_profile"] = defaults_gl["species_profile"]
    if s.get("racing_preset") not in RACING_PRESETS:
        s["racing_preset"] = defaults_gl["racing_preset"]
    hp = dict(defaults_gl["helix_presets"])
    hp.update(s.get("helix_presets") or {})
    s["helix_presets"] = hp
    s["initial_generation_limit"] = max(1, int(s.get("initial_generation_limit", original(profile, "initial_generation_limit", 16))))
    gp = max(4, int(s.get("initial_genepool_size", original(profile, "initial_genepool_size", 40))))
    s["initial_genepool_size"] = max(4, (gp // 4) * 4)
    s["sim_work_per_ui_update"] = max(1, int(s.get("sim_work_per_ui_update", original(profile, "sim_work_per_ui_update", 240))))
    s["elite_parent_percent"] = max(1, min(100, int(s.get("elite_parent_percent", original(profile, "elite_parent_percent", 25)))))
    s["min_generation_for_disk"] = max(0, min(127, int(s.get("min_generation_for_disk", original(profile, "min_generation_for_disk", 9)))))
    for key in ADVANCED_FLOAT_KEYS:
        if key in s:
            s[key] = float(s[key])
    s = apply_caseoh_sim_overrides(profile, s)
    s = apply_exploding_sim_overrides(s)
    return s


def apply_values_to_exe(exe: Path, profile: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
    data = bytearray(exe.read_bytes())
    patches = profile["patches"]
    s = normalize_settings(profile, settings)

    def has(key: str) -> bool:
        return key in patches

    def write_i32(key: str, value: int) -> None:
        if not has(key):
            return
        write_at(data, int(patches[key]["file_off"]), struct.pack("<i", int(value)))

    def write_u8(key: str, value: int) -> None:
        if not has(key):
            return
        write_at(data, int(patches[key]["file_off"]), bytes([max(0, min(255, int(value)))]))

    def write_f32(key: str, value: float) -> None:
        if not has(key):
            return
        write_at(data, int(patches[key]["file_off"]), struct.pack("<f", float(value)))

    def write_bytes(key: str, payload: bytes) -> None:
        if not has(key):
            return
        write_at(data, int(patches[key]["file_off"]), payload)

    def write_generation_display(value: int, enabled: bool) -> None:
        key = "generation_display_limit"
        if not has(key):
            return
        write_bytes(key, bytes.fromhex(str(patches[key]["original"])))

    def write_race_display(value: int, enabled: bool) -> None:
        key = "race_display_limit"
        current_key = "race_display_current"
        if not has(key) or not has(current_key):
            return
        payload = bytes.fromhex(str(patches[key]["original"])) + bytes.fromhex(str(patches[current_key]["original"]))
        write_bytes(key, payload)

    # Baseline behavior.
    write_i32("min_finish_frames", s["min_finish_frames"])
    write_i32("no_progress_frames", s["no_progress_frames"])
    write_i32("max_sim_frames", s["max_sim_frames"])
    write_i32("valid_result_max", s["valid_result_max"])

    original_branch = bytes.fromhex(str(patches["early_finish_branch"]["original"]))
    if s.get("always_accept_early_finish", False):
        write_bytes("early_finish_branch", b"\xEB" + original_branch[1:2])
    else:
        write_bytes("early_finish_branch", original_branch)

    write_bytes("time_format", FMT_BY_PRECISION[int(s["display_precision"])])

    # Experimental search controls. If disabled, deliberately restore originals.
    if s.get("enable_search_controls", False):
        search_values = {
            "initial_generation_limit": s["initial_generation_limit"],
            "initial_genepool_size": s["initial_genepool_size"],
            "sim_work_per_ui_update": s["sim_work_per_ui_update"],
            "elite_parent_percent": s["elite_parent_percent"],
            "min_generation_for_disk": s["min_generation_for_disk"],
        }
    else:
        search_values = {
            "initial_generation_limit": int(original(profile, "initial_generation_limit", 16)),
            "initial_genepool_size": int(original(profile, "initial_genepool_size", 40)),
            "sim_work_per_ui_update": int(original(profile, "sim_work_per_ui_update", 240)),
            "elite_parent_percent": int(original(profile, "elite_parent_percent", 25)),
            "min_generation_for_disk": int(original(profile, "min_generation_for_disk", 9)),
        }
        # Mirror what was actually written in settings so users can see stock values.
        s.update(search_values)

    for key in SEARCH_KEYS_I32:
        write_i32(key, int(search_values[key]))
    if s.get("enable_search_controls", False):
        write_i32("ram_generation_limit_upgraded", int(search_values["initial_generation_limit"]))
        write_i32("ram_generation_limit_base", int(search_values["initial_generation_limit"]))
        write_i32("ram_genepool_size_upgraded", int(search_values["initial_genepool_size"]))
        write_i32("ram_genepool_size_base", int(search_values["initial_genepool_size"]))
    else:
        write_i32("ram_generation_limit_upgraded", int(original(profile, "ram_generation_limit_upgraded", original(profile, "initial_generation_limit", 16))))
        write_i32("ram_generation_limit_base", int(original(profile, "ram_generation_limit_base", 8)))
        write_i32("ram_genepool_size_upgraded", int(original(profile, "ram_genepool_size_upgraded", original(profile, "initial_genepool_size", 40))))
        write_i32("ram_genepool_size_base", int(original(profile, "ram_genepool_size_base", 20)))
    for key in SEARCH_KEYS_U8:
        write_u8(key, int(search_values[key]))
    write_generation_display(int(search_values["initial_generation_limit"]), bool(s.get("enable_search_controls", False)))
    write_race_display(int(search_values["initial_genepool_size"]) // 4, bool(s.get("enable_search_controls", False)))
    for key in DISPLAY_NUMERATOR_KEYS:
        if has(key):
            write_bytes(key, bytes.fromhex(str(patches[key]["original"])))

    # Advanced floats remain stock unless settings explicitly differ; default settings
    # already contain stock/original values.
    for key in ADVANCED_FLOAT_KEYS:
        if key in s:
            write_f32(key, float(s[key]))

    exe.write_bytes(data)
    return s


def cmd_scan(args: argparse.Namespace) -> None:
    exe = Path(args.exe)
    profile = scan_exe(exe)
    text = json.dumps(profile, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)


def cmd_make_branch(args: argparse.Namespace) -> None:
    source = Path(args.source)
    branch = Path(args.branch)
    copy_branch(source, branch, overwrite=args.overwrite)
    exe = branch / "Horsey.exe"
    backup_exe(exe)
    profile = scan_exe(exe)
    write_profile(branch, profile)
    settings = default_settings(profile)
    if not args.no_patch:
        settings = apply_values_to_exe(exe, profile, settings)
    apply_gene_stack(branch, settings)
    try:
        apply_caseoh_art(branch)
    except Exception as e:
        print(f"warning: could not apply CaseOh90000 garage art: {e}")
    try:
        arena_result = prepare_caseoh_arena_branch(branch)
        print("prepared Caseoh arena:", json.dumps(arena_result.get("features", {})))
    except Exception as e:
        print(f"warning: could not prepare Caseoh arena / in-game timer: {e}")
    write_settings(branch, settings)
    print(f"branch={branch}")
    print("created CaseOh90000 mod branch and wrote steam_appid.txt")
    print("copied the source game folder, including the current save folder, into the branch")
    if not args.no_patch:
        print("applied HorseyGameCaseOhMod v2 defaults: min_finish_frames=0, display T:%.3f, Intensity controls enabled")
    else:
        print("no patch applied yet")


def load_settings(branch: Path, profile: Dict[str, Any]) -> Dict[str, Any]:
    settings_path = branch / "sim9000_mod_settings.json"
    if settings_path.exists():
        return json.loads(settings_path.read_text(encoding="utf-8"))
    return default_settings(profile)


def cmd_apply(args: argparse.Namespace) -> None:
    branch = Path(args.branch)
    exe = branch / "Horsey.exe"
    if not exe.exists():
        raise FileNotFoundError(exe)
    backup_exe(exe)
    profile = read_branch_profile(branch)
    settings = load_settings(branch, profile)

    core_keys = [
        "min_finish_frames", "no_progress_frames", "max_sim_frames", "valid_result_max", "display_precision",
        "finish_metric_threshold", "display_time_divisor", "result_score_scale", "invalid_score_sentinel",
    ]
    for key in core_keys:
        val = getattr(args, key, None)
        if val is not None:
            settings[key] = val

    search_keys = ["initial_generation_limit", "initial_genepool_size", "sim_work_per_ui_update", "elite_parent_percent", "min_generation_for_disk"]
    search_arg_used = False
    for key in search_keys:
        val = getattr(args, key, None)
        if val is not None:
            settings[key] = val
            search_arg_used = True
    if args.enable_search_controls or search_arg_used:
        settings["enable_search_controls"] = True
    if args.disable_search_controls:
        settings["enable_search_controls"] = False

    # v1.4 keeps the stable baseline branch behavior fixed; the old core toggle is not exposed.
    settings["always_accept_early_finish"] = False

    if getattr(args, "caseoh_mode", False):
        settings["caseoh_mode"] = True
    if getattr(args, "no_caseoh_mode", False) or getattr(args, "disable_caseoh_mode", False):
        settings["caseoh_mode"] = False

    if getattr(args, "enable_gene_lab", False):
        settings["gene_lab_enabled"] = True
    if getattr(args, "disable_gene_lab", False):
        settings["gene_lab_enabled"] = False
    if getattr(args, "species_profile", None):
        settings["species_profile"] = args.species_profile
    if getattr(args, "racing_preset", None):
        settings["racing_preset"] = args.racing_preset
    if getattr(args, "exploding_mode", False):
        settings["exploding_mode"] = True
        settings["gene_lab_enabled"] = True
        settings["species_profile"] = "Freak / mixed"
        settings["racing_preset"] = "Exploding finisher"

    settings = apply_values_to_exe(exe, profile, settings)
    caseoh_result = apply_gene_stack(branch, settings)
    try:
        art_result = apply_caseoh_art(branch)
        print("CaseOh90000 garage art:", json.dumps(art_result))
    except Exception as e:
        print(f"warning: could not apply CaseOh90000 garage art: {e}")
    try:
        arena_result = prepare_caseoh_arena_branch(branch)
        print("Caseoh arena:", json.dumps(arena_result.get("features", {})))
    except Exception as e:
        print(f"warning: could not prepare Caseoh arena / in-game timer: {e}")
    if is_exploding_requested(settings):
        seed = write_exploding_seed_files(branch)
        print("Exploding finisher seed DNA written:", seed.get("dna_file"))
    write_settings(branch, settings)
    print(f"patched {exe}")
    print("Easter Egg:", json.dumps(caseoh_result))
    print(json.dumps(settings, indent=2))


def cmd_restore(args: argparse.Namespace) -> None:
    branch = Path(args.branch)
    exe = branch / "Horsey.exe"
    backup = branch / "Horsey.exe.original"
    if not backup.exists():
        raise FileNotFoundError(backup)
    try:
        arena_restore = restore_caseoh_arena_branch(branch)
        if arena_restore.get("restored"):
            print("Caseoh arena restored:", json.dumps(arena_restore))
    except Exception as e:
        print(f"warning: could not restore Caseoh arena files: {e}")
    shutil.copy2(backup, exe)
    try:
        restore_gene_xml(branch)
        restore_caseoh_art(branch)
        profile = read_branch_profile(branch)
        settings = load_settings(branch, profile)
        settings["caseoh_mode"] = False
        write_settings(branch, settings)
        print("Easter Egg disabled / branch data restored when backup exists")
    except Exception as e:
        print(f"warning: could not restore Easter Egg genes.xml: {e}")
    print(f"restored {exe} from {backup}")


def cmd_run(args: argparse.Namespace) -> None:
    branch = Path(args.branch)
    exe = branch / "Horsey.exe"
    if not exe.exists():
        raise FileNotFoundError(exe)
    launch_horsey_branch_with_native(branch)
    print(f"launched {exe} with Caseoh arena timer")


def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="HorseyGameCaseOhMod v2 local mod branch tool")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="scan an executable and print/write patch points")
    s.add_argument("--exe", default=str(Path(DEFAULT_SOURCE) / "Horsey.exe"))
    s.add_argument("--out")
    s.set_defaults(func=cmd_scan)

    s = sub.add_parser("make-branch", help="copy the game to a CaseOh90000 local mod branch and apply the baseline uncap")
    s.add_argument("--source", default=DEFAULT_SOURCE)
    s.add_argument("--branch", default=DEFAULT_BRANCH)
    s.add_argument("--overwrite", action="store_true")
    s.add_argument("--no-patch", action="store_true")
    s.set_defaults(func=cmd_make_branch)

    s = sub.add_parser("apply", help="apply settings to a mod branch executable")
    s.add_argument("--branch", default=DEFAULT_BRANCH)
    s.add_argument("--min-finish-frames", type=int, default=None)
    s.add_argument("--no-progress-frames", type=int, default=None)
    s.add_argument("--max-sim-frames", type=int, default=None)
    s.add_argument("--valid-result-max", type=int, default=None)
    s.add_argument("--display-precision", type=int, choices=[1, 2, 3], default=None)
    s.add_argument("--caseoh-mode", action="store_true", help="enable Easter Egg")
    s.add_argument("--no-caseoh-mode", "--disable-caseoh-mode", dest="no_caseoh_mode", action="store_true", help="disable Easter Egg and restore branch data file from backup")
    s.add_argument("--enable-gene-lab", action="store_true", help="enable SIM Gene Lab species/racing profile patching")
    s.add_argument("--disable-gene-lab", action="store_true", help="disable SIM Gene Lab and restore stock genes.xml except Easter Egg if enabled")
    s.add_argument("--species-profile", choices=SPECIES_PROFILES, default=None)
    s.add_argument("--racing-preset", choices=RACING_PRESETS, default=None)
    s.add_argument("--exploding-mode", action="store_true", help="enable exploding finisher mode")
    s.add_argument("--enable-search-controls", action="store_true")
    s.add_argument("--disable-search-controls", action="store_true")
    s.add_argument("--initial-generation-limit", type=int, default=None)
    s.add_argument("--initial-genepool-size", type=int, default=None)
    s.add_argument("--sim-work-per-ui-update", type=int, default=None)
    s.add_argument("--elite-parent-percent", type=int, default=None)
    s.add_argument("--min-generation-for-disk", type=int, default=None)
    s.add_argument("--finish-metric-threshold", type=float, default=None)
    s.add_argument("--display-time-divisor", type=float, default=None)
    s.add_argument("--result-score-scale", type=float, default=None)
    s.add_argument("--invalid-score-sentinel", type=float, default=None)
    s.set_defaults(func=cmd_apply)

    s = sub.add_parser("restore", help="restore Horsey.exe in the branch from Horsey.exe.original")
    s.add_argument("--branch", default=DEFAULT_BRANCH)
    s.set_defaults(func=cmd_restore)

    s = sub.add_parser("run", help="launch the mod branch Horsey.exe")
    s.add_argument("--branch", default=DEFAULT_BRANCH)
    s.set_defaults(func=cmd_run)

    return ap


def main(argv: Optional[List[str]] = None) -> int:
    ap = build_argparser()
    args = ap.parse_args(argv)
    try:
        args.func(args)
        return 0
    except Exception as e:
        print(f"ERROR: {e}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
