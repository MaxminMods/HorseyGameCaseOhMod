#!/usr/bin/env python3
"""
HorseyGameCaseOhMod v2 panel with community racing archetypes, exploding finisher preset, Direct DNA, and a hidden Easter egg.

No third-party packages. It can patch a branch on disk and, on Windows, patch the
currently running Horsey.exe process. The panel is not always-on-top by default and can dock beside Horsey.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import struct
import sys
import tkinter as tk
from tkinter import font as tkfont
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, List, Tuple

from sim_gene_profiles import (
    apply_gene_stack, default_gene_lab_settings, SPECIES_PROFILES, RACING_PRESETS,
    HELIX_PRESETS, HELIX_RANGES, profile_status, restore_gene_xml,
    force_caseoh_override_settings,
)
from exploding_seed import (
    EXPLODING_FINISHER_SEED_DNA, apply_exploding_sim_overrides, is_exploding_requested,
    write_exploding_seed_files, copy_seed_to_clipboard,
)
from caseoh_art import apply_caseoh_art
from dna_designer import (
    BASES as DNA_BASES, DIRECT_PRESETS, DIRECT_PRESET_NAMES, HELIX_LENGTHS as DNA_HELIX_LENGTHS,
    HELIX_GENE_NAMES as DNA_HELIX_GENE_NAMES, apply_direct_preset, apply_dna_locks, blank_genome,
    dna_hash, format_dna, load_exploding_seed, normalize_dna, normalize_dna_locks,
    set_dna_lock, write_dna_file,
)


DEFAULT_BRANCH = str(Path.home() / "Desktop" / "projects" / "CaseOh90000_BRANCH")


def configured_default_branch() -> str:
    cfg_path = Path(__file__).with_name("CaseOh90000_paths.json")
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
            branch = cfg.get("branch")
            if branch:
                return str(branch)
        except Exception:
            pass
    return DEFAULT_BRANCH


FMT_BY_PRECISION = {1: b"T:%.1f\x00", 2: b"T:%.2f\x00", 3: b"T:%.3f\x00"}

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
PROCESS_ALL_PATCH = PROCESS_QUERY_INFORMATION | PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION
TH32CS_SNAPPROCESS = 0x00000002
TH32CS_SNAPTHREAD = 0x00000004
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
THREAD_SUSPEND_RESUME = 0x0002
PAGE_EXECUTE_READWRITE = 0x40
PAGE_READWRITE = 0x04
MEM_COMMIT = 0x1000
MEM_PRIVATE = 0x20000
PAGE_GUARD = 0x100
SW_RESTORE = 9
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
READABLE_PAGE_PROTECTIONS = {0x02, 0x04, 0x08, 0x20, 0x40, 0x80}

SIM_RACE_CURRENT_OFFSET = 0x278
SIM_STATE_HINT_OFFSET = 0x27C
SIM_GENERATION_CURRENT_OFFSET = 0x288
SIM_GENERATION_LIMIT_OFFSET = 0x6A8
SIM_GENEPOOL_SIZE_OFFSET = 0x6AC
SIM_STATE_SCAN_SIZE = SIM_GENEPOOL_SIZE_OFFSET + 4
LAST_SIM_STATE_ADDR: int | None = None

CORE_KEYS = ["min_finish_frames", "no_progress_frames", "max_sim_frames", "valid_result_max"]
SEARCH_I32 = ["initial_generation_limit", "initial_genepool_size", "sim_work_per_ui_update"]
SEARCH_U8 = ["elite_parent_percent", "min_generation_for_disk"]
SEARCH_KEYS = SEARCH_I32 + SEARCH_U8
ADVANCED_FLOAT_KEYS = ["finish_metric_threshold", "display_time_divisor", "result_score_scale", "invalid_score_sentinel"]
DISPLAY_NUMERATOR_KEYS = ["generation_display_current"]
LIVE_GUARDED_PATCH_LABELS = "frame budget, valid-score max, earliest disk generation, stall/cull values, display format, and startup search controls"
VERIFY_PATCH_KEYS = ["max_sim_frames", "valid_result_max", "min_generation_for_disk"]
VERIFY_PATCH_LABELS = {
    "max_sim_frames": "frame budget",
    "valid_result_max": "valid score max",
    "min_generation_for_disk": "earliest disk generation",
}
WINDOW_CHROME_HEIGHT_GUESS = 40
OLD_TAB_ORDER = ["dna", "main", "gene_lab", "search", "settings"]
TAB_ORDER = ["main", "search", "gene_lab", "dna", "settings"]
TAB_META = {
    "main": {"title": "Parameters", "color": "#d94747", "pale": "#fff4f4"},
    "search": {"title": "Intensity", "color": "#e58a2a", "pale": "#fff7ed"},
    "gene_lab": {"title": "Gene Lab", "color": "#2f9b59", "pale": "#f1fff6"},
    "dna": {"title": "Direct DNA", "color": "#2f72d6", "pale": "#f1f6ff"},
    "settings": {"title": "Settings", "color": "#777d86", "pale": "#f6f7f8"},
}

DESCRIPTIONS = {
    "min_finish_frames": (
        "Controls the old 5-second SIM9000 cutoff. The normal game uses 300 frames, or 5.000 seconds. "
        "Leave this at 0 for CaseOh90000's uncapped behavior."
    ),
    "no_progress_frames": (
        "How long SIM9000 lets a horse struggle before calling it stuck. Lower values clear bad attempts sooner; "
        "higher values give weird builds more time to get moving."
    ),
    "max_sim_frames": (
        "The longest a test horse is allowed to run. Lower this if SIM9000 starts handing you very slow winners. "
        "Raising it mostly lets slow horses finish; it does not make fast horses faster. Save to branch files for this startup-level value."
    ),
    "valid_result_max": (
        "A broad internal cutoff for what SIM9000 is allowed to keep. The original value is usually best. "
        "If this is too loose, slow or strange results can slip through. Save to branch files for this startup-level value."
    ),
    "display_precision": (
        "How many decimals the T readout shows. Three decimals makes close results easier to compare."
    ),
    "caseoh_mode": "Easter Egg.",
    "enable_search_controls": (
        "Lets you experiment with SIM9000's search loop. Leave this off for the proven baseline behavior."
    ),
    "initial_generation_limit": (
        "How many generations SIM9000 runs during its internal search. More is not always better, so treat this as experimental."
    ),
    "initial_genepool_size": (
        "How many horses SIM9000 starts with. Bigger pools explore more DNA but use more work. "
        "The visible R total is tied to this: 40 horses = 10 race slots, 80 horses = 20."
    ),
    "sim_work_per_ui_update": (
        "How much SIM9000 work happens between screen refreshes. Higher values can make the sim finish sooner on screen, "
        "but the window may look frozen while it crunches."
    ),
    "elite_parent_percent": (
        "How much of the better population gets to parent the next generation. Lower is greedier; higher keeps more variety."
    ),
    "min_generation_for_disk": (
        "The earliest generation that can produce a result disk. Setting this too low can output weak DNA before the search improves. Save to branch files for this startup-level value."
    ),
    "streamer_privacy": (
        "Hides full folder paths in this window so screen sharing does not reveal your Windows username or project folders."
    ),

    "gene_lab_enabled": (
        "Turns on branch-only genes.xml profile patching. This does not rewrite DNA strings; it changes how selected genes express during SIM9000 runs."
    ),
    "species_profile": (
        "Locks or biases body-plan/species traits. Use Any/no lock to let the normal gene pool mix species freely."
    ),
    "racing_preset": (
        "Applies a racing archetype across the whole gene table: car, roll, tail power, tiny horse, and other discovery modes."
    ),
    "helix_presets": (
        "Old expression preset controls. These edit branch genes.xml. For exact A/T/C/G base choices, use the Direct DNA Editor tab instead."
    ),
    "dna_editor": (
        "Direct DNA editor. This makes normal 40-line Horsey DNA strings by choosing A/T/C/G for each gene position. It does not patch genes.xml. You can expand any helix and see every base it changes."
    ),
    "finish_metric_threshold": "Internal finish logic value. Kept stock in this UI.",
    "display_time_divisor": "Displayed time conversion. Kept stock in this UI.",
    "result_score_scale": "Internal score conversion. Kept stock in this UI.",
    "invalid_score_sentinel": "Internal invalid-result value. Kept stock in this UI.",
}


def last_error() -> str:
    if os.name != "nt":
        return "not on Windows"
    return f"WinError {ctypes.get_last_error()}"


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)), ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD), ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG), ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260),
    ]


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD), ("th32ModuleID", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
        ("GlblcntUsage", wintypes.DWORD), ("ProccntUsage", wintypes.DWORD),
        ("modBaseAddr", ctypes.POINTER(ctypes.c_byte)), ("modBaseSize", wintypes.DWORD),
        ("hModule", wintypes.HMODULE), ("szModule", wintypes.WCHAR * 256), ("szExePath", wintypes.WCHAR * 260),
    ]


class THREADENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ThreadID", wintypes.DWORD),
        ("th32OwnerProcessID", wintypes.DWORD), ("tpBasePri", wintypes.LONG), ("tpDeltaPri", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
    ]


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wintypes.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wintypes.DWORD),
        ("Protect", wintypes.DWORD),
        ("Type", wintypes.DWORD),
    ]


if os.name == "nt":
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    CreateToolhelp32Snapshot = kernel32.CreateToolhelp32Snapshot
    CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    Process32FirstW = kernel32.Process32FirstW
    Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    Process32FirstW.restype = wintypes.BOOL
    Process32NextW = kernel32.Process32NextW
    Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    Process32NextW.restype = wintypes.BOOL
    Thread32First = kernel32.Thread32First
    Thread32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(THREADENTRY32)]
    Thread32First.restype = wintypes.BOOL
    Thread32Next = kernel32.Thread32Next
    Thread32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(THREADENTRY32)]
    Thread32Next.restype = wintypes.BOOL
    Module32FirstW = kernel32.Module32FirstW
    Module32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
    Module32FirstW.restype = wintypes.BOOL
    Module32NextW = kernel32.Module32NextW
    Module32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
    Module32NextW.restype = wintypes.BOOL
    OpenProcess = kernel32.OpenProcess
    OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    OpenProcess.restype = wintypes.HANDLE
    OpenThread = kernel32.OpenThread
    OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    OpenThread.restype = wintypes.HANDLE
    SuspendThread = kernel32.SuspendThread
    SuspendThread.argtypes = [wintypes.HANDLE]
    SuspendThread.restype = wintypes.DWORD
    ResumeThread = kernel32.ResumeThread
    ResumeThread.argtypes = [wintypes.HANDLE]
    ResumeThread.restype = wintypes.DWORD
    ReadProcessMemory = kernel32.ReadProcessMemory
    ReadProcessMemory.argtypes = [wintypes.HANDLE, wintypes.LPCVOID, wintypes.LPVOID, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    ReadProcessMemory.restype = wintypes.BOOL
    WriteProcessMemory = kernel32.WriteProcessMemory
    WriteProcessMemory.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.LPCVOID, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    WriteProcessMemory.restype = wintypes.BOOL
    VirtualQueryEx = kernel32.VirtualQueryEx
    VirtualQueryEx.argtypes = [wintypes.HANDLE, wintypes.LPCVOID, ctypes.POINTER(MEMORY_BASIC_INFORMATION), ctypes.c_size_t]
    VirtualQueryEx.restype = ctypes.c_size_t
    VirtualProtectEx = kernel32.VirtualProtectEx
    VirtualProtectEx.argtypes = [wintypes.HANDLE, wintypes.LPVOID, ctypes.c_size_t, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    VirtualProtectEx.restype = wintypes.BOOL
    CloseHandle = kernel32.CloseHandle
    CloseHandle.argtypes = [wintypes.HANDLE]
    CloseHandle.restype = wintypes.BOOL
else:
    kernel32 = None


def _same_windows_path(left: str | Path, right: str | Path) -> bool:
    try:
        return os.path.normcase(os.path.abspath(str(left))) == os.path.normcase(os.path.abspath(str(right)))
    except Exception:
        return str(left).lower() == str(right).lower()


def find_horsey_process(preferred_exe: Path | None = None) -> Tuple[int, int, str]:
    if os.name != "nt":
        raise RuntimeError("live process patching only works on Windows")
    snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == INVALID_HANDLE_VALUE:
        raise RuntimeError(f"CreateToolhelp32Snapshot process failed: {last_error()}")
    try:
        pe = PROCESSENTRY32W(); pe.dwSize = ctypes.sizeof(pe)
        ok = Process32FirstW(snap, ctypes.byref(pe))
        candidates: List[int] = []
        while ok:
            if pe.szExeFile.lower() == "horsey.exe":
                candidates.append(pe.th32ProcessID)
            ok = Process32NextW(snap, ctypes.byref(pe))
    finally:
        CloseHandle(snap)
    if not candidates:
        raise RuntimeError("No running Horsey.exe process found. Start the mod branch first.")
    fallback: Tuple[int, int, str] | None = None
    preferred = Path(preferred_exe) if preferred_exe else None
    for pid in candidates:
        msnap = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
        if msnap == INVALID_HANDLE_VALUE:
            continue
        try:
            me = MODULEENTRY32W(); me.dwSize = ctypes.sizeof(me)
            ok = Module32FirstW(msnap, ctypes.byref(me))
            while ok:
                if me.szModule.lower() == "horsey.exe":
                    base = ctypes.cast(me.modBaseAddr, ctypes.c_void_p).value
                    result = (pid, int(base), me.szExePath)
                    if fallback is None:
                        fallback = result
                    if preferred is not None and _same_windows_path(me.szExePath, preferred):
                        return result
                    break
                ok = Module32NextW(msnap, ctypes.byref(me))
        finally:
            CloseHandle(msnap)
    if fallback is not None:
        return fallback
    raise RuntimeError(f"Horsey.exe process found, but module base was not found")


def write_process(pid: int, addr: int, payload: bytes) -> None:
    h = OpenProcess(PROCESS_ALL_PATCH, False, pid)
    if not h:
        raise RuntimeError(f"OpenProcess({pid}) failed: {last_error()}")
    try:
        old = wintypes.DWORD(0)
        if not VirtualProtectEx(h, ctypes.c_void_p(addr), len(payload), PAGE_EXECUTE_READWRITE, ctypes.byref(old)):
            if not VirtualProtectEx(h, ctypes.c_void_p(addr), len(payload), PAGE_READWRITE, ctypes.byref(old)):
                raise RuntimeError(f"VirtualProtectEx({addr:#x}) failed: {last_error()}")
        n = ctypes.c_size_t(0)
        buf = ctypes.create_string_buffer(payload)
        if not WriteProcessMemory(h, ctypes.c_void_p(addr), buf, len(payload), ctypes.byref(n)):
            raise RuntimeError(f"WriteProcessMemory({addr:#x}) failed: {last_error()}")
        if n.value != len(payload):
            raise RuntimeError(f"short write at {addr:#x}: {n.value}/{len(payload)}")
        tmp = wintypes.DWORD(0)
        VirtualProtectEx(h, ctypes.c_void_p(addr), len(payload), old.value, ctypes.byref(tmp))
    finally:
        CloseHandle(h)


def read_process_memory(h: wintypes.HANDLE, addr: int, size: int) -> bytes | None:
    buf = (ctypes.c_ubyte * size)()
    n = ctypes.c_size_t(0)
    if not ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size, ctypes.byref(n)):
        return None
    return bytes(buf[:n.value])


def write_process_i32(h: wintypes.HANDLE, addr: int, value: int) -> None:
    old = wintypes.DWORD(0)
    if not VirtualProtectEx(h, ctypes.c_void_p(addr), 4, PAGE_READWRITE, ctypes.byref(old)):
        if not VirtualProtectEx(h, ctypes.c_void_p(addr), 4, PAGE_EXECUTE_READWRITE, ctypes.byref(old)):
            raise RuntimeError(f"VirtualProtectEx({addr:#x}) failed: {last_error()}")
    payload = struct.pack("<i", int(value))
    buf = ctypes.create_string_buffer(payload)
    n = ctypes.c_size_t(0)
    if not WriteProcessMemory(h, ctypes.c_void_p(addr), buf, 4, ctypes.byref(n)):
        raise RuntimeError(f"WriteProcessMemory({addr:#x}) failed: {last_error()}")
    if n.value != 4:
        raise RuntimeError(f"short write at {addr:#x}: {n.value}/4")
    tmp = wintypes.DWORD(0)
    VirtualProtectEx(h, ctypes.c_void_p(addr), 4, old.value, ctypes.byref(tmp))


def _process_thread_ids(pid: int) -> List[int]:
    snap = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
    if snap == INVALID_HANDLE_VALUE:
        raise RuntimeError(f"CreateToolhelp32Snapshot thread failed: {last_error()}")
    tids: List[int] = []
    try:
        te = THREADENTRY32(); te.dwSize = ctypes.sizeof(te)
        ok = Thread32First(snap, ctypes.byref(te))
        while ok:
            if int(te.th32OwnerProcessID) == int(pid):
                tids.append(int(te.th32ThreadID))
            ok = Thread32Next(snap, ctypes.byref(te))
    finally:
        CloseHandle(snap)
    return tids


def _suspend_process_threads(pid: int) -> List[wintypes.HANDLE]:
    suspended: List[wintypes.HANDLE] = []
    for tid in _process_thread_ids(pid):
        h_thread = OpenThread(THREAD_SUSPEND_RESUME, False, tid)
        if not h_thread:
            continue
        previous_count = SuspendThread(h_thread)
        if previous_count == 0xFFFFFFFF:
            CloseHandle(h_thread)
            continue
        suspended.append(h_thread)
    if not suspended:
        raise RuntimeError("Could not pause Horsey threads for a safe live SIM update.")
    return suspended


def _resume_thread_handles(handles: List[wintypes.HANDLE]) -> None:
    for h_thread in reversed(handles):
        ResumeThread(h_thread)
        CloseHandle(h_thread)


def _read_sim_state_values(h: wintypes.HANDLE, obj: int) -> Dict[str, int] | None:
    data = read_process_memory(h, obj, SIM_STATE_SCAN_SIZE)
    if data is None or len(data) < SIM_STATE_SCAN_SIZE:
        return None
    return {
        "race_current": struct.unpack_from("<i", data, SIM_RACE_CURRENT_OFFSET)[0],
        "state_hint": struct.unpack_from("<i", data, SIM_STATE_HINT_OFFSET)[0],
        "generation_current": struct.unpack_from("<i", data, SIM_GENERATION_CURRENT_OFFSET)[0],
        "generation_limit": struct.unpack_from("<i", data, SIM_GENERATION_LIMIT_OFFSET)[0],
        "genepool_size": struct.unpack_from("<i", data, SIM_GENEPOOL_SIZE_OFFSET)[0],
    }


def _plausible_sim_state(values: Dict[str, int], target_generation_limit: int, target_genepool_size: int) -> bool:
    generation_limit = int(values["generation_limit"])
    genepool_size = int(values["genepool_size"])
    if not (1 <= generation_limit <= 4096):
        return False
    if genepool_size < 4 or genepool_size > 4096 or genepool_size % 4 != 0:
        return False
    race_slots = max(1, genepool_size // 4, target_genepool_size // 4)
    generation_cap = max(generation_limit, target_generation_limit, 16)
    return (
        -2 <= int(values["state_hint"]) <= 20
        and 0 <= int(values["race_current"]) <= race_slots + 8
        and -1 <= int(values["generation_current"]) <= generation_cap + 8
    )


def _scan_sim_state_candidates(
    h: wintypes.HANDLE,
    target_generation_limit: int,
    target_genepool_size: int,
    original_generation_limit: int,
    original_genepool_size: int,
    extra_pairs: List[Tuple[int, int]] | None = None,
) -> List[Tuple[int, Dict[str, int]]]:
    candidates: Dict[int, Dict[str, int]] = {}
    pair_needles = {
        (int(original_generation_limit), int(original_genepool_size)),
        (int(target_generation_limit), int(target_genepool_size)),
    }
    for gen_limit, pool_size in extra_pairs or []:
        pair_needles.add((int(gen_limit), int(pool_size)))

    def add_candidate(obj: int) -> None:
        if obj in candidates or obj % 16 != 0:
            return
        values = _read_sim_state_values(h, obj)
        if values and _plausible_sim_state(values, target_generation_limit, target_genepool_size):
            candidates[obj] = values

    mbi = MEMORY_BASIC_INFORMATION()
    addr = 0
    while VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
        region_base = int(mbi.BaseAddress or 0)
        region_size = int(mbi.RegionSize or 0)
        protect = int(mbi.Protect) & 0xFF
        if (
            int(mbi.State) == MEM_COMMIT
            and int(mbi.Type) == MEM_PRIVATE
            and not (int(mbi.Protect) & PAGE_GUARD)
            and protect in READABLE_PAGE_PROTECTIONS
            and region_size > 0
        ):
            pos = region_base
            end = region_base + region_size
            while pos < end:
                chunk_size = min(4 * 1024 * 1024, end - pos)
                data = read_process_memory(h, pos, chunk_size)
                if data:
                    for gen_limit, pool_size in pair_needles:
                        needle = struct.pack("<ii", gen_limit, pool_size)
                        start = 0
                        while True:
                            hit = data.find(needle, start)
                            if hit < 0:
                                break
                            obj = pos + hit - SIM_GENERATION_LIMIT_OFFSET
                            if obj >= region_base:
                                add_candidate(obj)
                            start = hit + 1
                pos += chunk_size
        next_addr = region_base + region_size
        if next_addr <= addr:
            break
        addr = next_addr
    return sorted(candidates.items())


def _live_sim_target_values(
    profile: Dict[str, Any],
    settings: Dict[str, Any],
    previous_settings: Dict[str, Any] | None = None,
) -> Tuple[int, int, int, int, List[Tuple[int, int]]]:
    s = normalize_settings(profile, settings)
    if s.get("enable_search_controls"):
        target_generation_limit = int(s["initial_generation_limit"])
        target_genepool_size = int(s["initial_genepool_size"])
    else:
        target_generation_limit = int(original(profile, "initial_generation_limit", 16))
        target_genepool_size = int(original(profile, "initial_genepool_size", 40))
    original_generation_limit = int(original(profile, "initial_generation_limit", 16))
    original_genepool_size = int(original(profile, "initial_genepool_size", 40))
    extra_pairs: List[Tuple[int, int]] = []
    base_generation_limit = int(original(profile, "ram_generation_limit_base", 8))
    base_genepool_size = int(original(profile, "ram_genepool_size_base", 20))
    extra_pairs.append((base_generation_limit, base_genepool_size))
    if previous_settings:
        previous = normalize_settings(profile, previous_settings)
        if previous.get("enable_search_controls"):
            extra_pairs.append((int(previous["initial_generation_limit"]), int(previous["initial_genepool_size"])))
    return target_generation_limit, target_genepool_size, original_generation_limit, original_genepool_size, extra_pairs


def _live_sim_state_candidates(
    h: wintypes.HANDLE,
    profile: Dict[str, Any],
    settings: Dict[str, Any],
    previous_settings: Dict[str, Any] | None = None,
) -> List[Tuple[int, Dict[str, int]]]:
    target_generation_limit, target_genepool_size, original_generation_limit, original_genepool_size, extra_pairs = _live_sim_target_values(
        profile,
        settings,
        previous_settings,
    )
    candidates: List[Tuple[int, Dict[str, int]]] = []
    if LAST_SIM_STATE_ADDR is not None:
        cached_values = _read_sim_state_values(h, LAST_SIM_STATE_ADDR)
        if cached_values and _plausible_sim_state(cached_values, target_generation_limit, target_genepool_size):
            candidates = [(LAST_SIM_STATE_ADDR, cached_values)]
    if not candidates:
        candidates = _scan_sim_state_candidates(
            h,
            target_generation_limit,
            target_genepool_size,
            original_generation_limit,
            original_genepool_size,
            extra_pairs,
        )
    return candidates


def _sim9000_appears_active(
    pid: int,
    profile: Dict[str, Any],
    settings: Dict[str, Any],
    previous_settings: Dict[str, Any] | None = None,
) -> Tuple[bool, str]:
    h = OpenProcess(PROCESS_ALL_PATCH, False, pid)
    if not h:
        raise RuntimeError(f"OpenProcess({pid}) failed while checking SIM9000 activity: {last_error()}")
    try:
        candidates = _live_sim_state_candidates(h, profile, settings, previous_settings)
    finally:
        CloseHandle(h)
    if not candidates:
        return False, "no active SIM state found"

    active = [
        values for _obj, values in candidates
        if int(values["race_current"]) > 0 or int(values["generation_current"]) > 0
    ]
    if not active:
        return True, "SIM state found; guarded as active"
    values = active[0]
    return (
        True,
        f"G {values['generation_current']}/{values['generation_limit']}, "
        f"R {values['race_current']}/{max(1, int(values['genepool_size']) // 4)}",
    )


def patch_live_sim_state(pid: int, profile: Dict[str, Any], settings: Dict[str, Any], previous_settings: Dict[str, Any] | None = None) -> str:
    global LAST_SIM_STATE_ADDR
    target_generation_limit, target_genepool_size, _original_generation_limit, _original_genepool_size, _extra_pairs = _live_sim_target_values(
        profile,
        settings,
        previous_settings,
    )

    h = OpenProcess(PROCESS_ALL_PATCH, False, pid)
    if not h:
        raise RuntimeError(f"OpenProcess({pid}) failed while updating live SIM state: {last_error()}")
    try:
        candidates = _live_sim_state_candidates(h, profile, settings, previous_settings)
        if not candidates:
            return "\nLive SIM state was not found yet. Apply from the world map or before starting SIM9000 if the counters do not change."
        if len(candidates) > 1:
            active_candidates = [
                (obj, values)
                for obj, values in candidates
                if int(values["race_current"]) != 0 or int(values["generation_current"]) != 0
            ]
            if len(active_candidates) == 1:
                candidates = active_candidates
            else:
                return "\nLive SIM state was ambiguous, so the active SIM limits were not changed."
        obj, before = candidates[0]
        suspended_threads = _suspend_process_threads(pid)
        try:
            before = _read_sim_state_values(h, obj) or before
            if not _plausible_sim_state(before, target_generation_limit, target_genepool_size):
                return "\nLive SIM state changed while applying, so this update was skipped safely. Press Apply again."
            write_process_i32(h, obj + SIM_GENERATION_LIMIT_OFFSET, target_generation_limit)
            write_process_i32(h, obj + SIM_GENEPOOL_SIZE_OFFSET, target_genepool_size)
            after = _read_sim_state_values(h, obj) or before
        finally:
            _resume_thread_handles(suspended_threads)
    finally:
        CloseHandle(h)
    LAST_SIM_STATE_ADDR = int(obj)

    before_slots = max(1, int(before["genepool_size"]) // 4)
    after_slots = max(1, int(after["genepool_size"]) // 4)
    msg = (
        "\nLive SIM state updated: "
        f"G total {before['generation_limit']} -> {after['generation_limit']}, "
        f"R slots {before_slots} -> {after_slots}."
    )
    if (
        int(before["generation_current"]) >= int(before["generation_limit"]) - 1
        and (
            int(before["generation_limit"]) != int(after["generation_limit"])
            or int(before["genepool_size"]) != int(after["genepool_size"])
        )
    ):
        msg += " If that SIM run had already stopped at the old limit, start another SIM9000 run in the same Horsey session; no game restart is needed."
    return msg


def read_profile(branch: Path) -> Dict[str, Any]:
    p = branch / "sim9000_mod_profile.json"
    if not p.exists():
        raise FileNotFoundError(f"Missing {p}. Run 00_START_HERE_CaseOh90000.bat to create or refresh the mod branch first.")
    profile = json.loads(p.read_text(encoding="utf-8"))
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
            scan_target = branch / "Horsey.exe"
        if scan_target.exists():
            try:
                from horseymod import scan_exe
                refreshed = scan_exe(scan_target)
                profile["patches"] = refreshed.get("patches", profile.get("patches", {}))
                profile["sections"] = refreshed.get("sections", profile.get("sections", []))
                profile["image_base"] = refreshed.get("image_base", profile.get("image_base"))
                profile["warnings"] = refreshed.get("warnings", profile.get("warnings", []))
                p.write_text(json.dumps(profile, indent=2), encoding="utf-8")
            except Exception:
                pass
    return profile



# Optional window docking helpers. They only run on Windows and only move this
# control panel, never the Horsey game window.
class RECT(ctypes.Structure):
    _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG), ("right", wintypes.LONG), ("bottom", wintypes.LONG)]


if os.name == "nt":
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    EnumWindows = user32.EnumWindows
    EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]
    EnumWindows.restype = wintypes.BOOL
    IsWindowVisible = user32.IsWindowVisible
    IsWindowVisible.argtypes = [wintypes.HWND]
    IsWindowVisible.restype = wintypes.BOOL
    GetWindowThreadProcessId = user32.GetWindowThreadProcessId
    GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    GetWindowThreadProcessId.restype = wintypes.DWORD
    GetWindowRect = user32.GetWindowRect
    GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
    GetWindowRect.restype = wintypes.BOOL
    ShowWindow = user32.ShowWindow
    ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    ShowWindow.restype = wintypes.BOOL
    SetWindowPos = user32.SetWindowPos
    SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
    SetWindowPos.restype = wintypes.BOOL
else:
    user32 = None


def find_horsey_window(preferred_exe: Path | None = None) -> Tuple[int, Tuple[int, int, int, int]] | None:
    """Return the main visible Horsey.exe window handle and rectangle if available."""
    if os.name != "nt":
        return None
    try:
        pid, _, _ = find_horsey_process(preferred_exe)
    except Exception:
        return None
    found: List[Tuple[int, Tuple[int, int, int, int]]] = []

    def _cb(hwnd: int, _lparam: int) -> bool:
        if not IsWindowVisible(hwnd):
            return True
        proc = wintypes.DWORD(0)
        GetWindowThreadProcessId(hwnd, ctypes.byref(proc))
        if int(proc.value) == int(pid):
            r = RECT()
            if GetWindowRect(hwnd, ctypes.byref(r)):
                if (r.right - r.left) > 100 and (r.bottom - r.top) > 100:
                    rect = (int(r.left), int(r.top), int(r.right), int(r.bottom))
                    found.append((int(hwnd), rect))
        return True

    EnumWindows(EnumWindowsProc(_cb), 0)
    return found[0] if found else None


def find_horsey_window_rect(preferred_exe: Path | None = None) -> Tuple[int, int, int, int] | None:
    result = find_horsey_window(preferred_exe)
    return result[1] if result else None


def position_horsey_window(x: int, y: int, width: int, height: int, preferred_exe: Path | None = None) -> bool:
    result = find_horsey_window(preferred_exe)
    if result is None:
        return False
    hwnd, _rect = result
    ShowWindow(hwnd, SW_RESTORE)
    return bool(SetWindowPos(hwnd, None, int(x), int(y), int(width), int(height), SWP_NOZORDER | SWP_NOACTIVATE))

def original(profile: Dict[str, Any], key: str, fallback: Any) -> Any:
    return profile.get("patches", {}).get(key, {}).get("original", fallback)


def default_settings(profile: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "min_finish_frames": 0,
        "display_precision": 3,
        "always_accept_early_finish": False,
        "no_progress_frames": int(original(profile, "no_progress_frames", 300)),
        "max_sim_frames": int(original(profile, "max_sim_frames", 10800)),
        "valid_result_max": int(original(profile, "valid_result_max", 10000)),
        "enable_search_controls": True,
        "initial_generation_limit": int(original(profile, "initial_generation_limit", 16)),
        "initial_genepool_size": int(original(profile, "initial_genepool_size", 40)),
        "sim_work_per_ui_update": int(original(profile, "sim_work_per_ui_update", 240)),
        "elite_parent_percent": int(original(profile, "elite_parent_percent", 25)),
        "min_generation_for_disk": int(original(profile, "min_generation_for_disk", 9)),
        "finish_metric_threshold": float(original(profile, "finish_metric_threshold", 25.0)),
        "display_time_divisor": float(original(profile, "display_time_divisor", 60.0)),
        "result_score_scale": float(original(profile, "result_score_scale", 400.0)),
        "invalid_score_sentinel": float(original(profile, "invalid_score_sentinel", 20000.0)),
        "caseoh_mode": False,
        "exploding_mode": False,
        **default_gene_lab_settings(),
        # UI preferences, stored with the branch settings. These do not patch the game.
        "streamer_privacy": True,
        "show_file_paths": False,
        "window_topmost": False,
        "window_follow": False,
        "window_auto_layout": False,
        "dna_editor_text": "",
        "dna_preset": "Do not change",
        "dna_preset_strands": "both",
        "dna_output_locks": {},
        "tab_order": list(TAB_ORDER),
    }


def read_settings(branch: Path, profile: Dict[str, Any]) -> Dict[str, Any]:
    p = branch / "sim9000_mod_settings.json"
    s = default_settings(profile)
    if p.exists():
        try:
            s.update(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            pass
    return normalize_settings(profile, s)


def write_settings(branch: Path, settings: Dict[str, Any]) -> None:
    (branch / "sim9000_mod_settings.json").write_text(json.dumps(settings, indent=2), encoding="utf-8")


def normalize_settings(profile: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
    s = dict(default_settings(profile)); s.update(settings)
    s["min_finish_frames"] = max(0, int(s["min_finish_frames"]))
    s["no_progress_frames"] = max(0, int(s["no_progress_frames"]))
    s["max_sim_frames"] = max(1, int(s["max_sim_frames"]))
    s["valid_result_max"] = max(1, int(s["valid_result_max"]))
    s["display_precision"] = int(s["display_precision"])
    s["always_accept_early_finish"] = False
    s["enable_search_controls"] = bool(s.get("enable_search_controls", True))
    s["caseoh_mode"] = bool(s.get("caseoh_mode", False))
    s["streamer_privacy"] = bool(s.get("streamer_privacy", True))
    s["show_file_paths"] = bool(s.get("show_file_paths", False))
    s["window_topmost"] = bool(s.get("window_topmost", False))
    s["window_follow"] = False
    s["window_auto_layout"] = False
    s["dna_editor_text"] = str(s.get("dna_editor_text", "") or "")
    if s.get("dna_preset") not in DIRECT_PRESET_NAMES:
        s["dna_preset"] = "Do not change"
    if s.get("dna_preset_strands") not in {"both", "top", "bottom"}:
        s["dna_preset_strands"] = "both"
    s["dna_output_locks"] = normalize_dna_locks(s.get("dna_output_locks", {}))
    saved_tabs = s.get("tab_order", [])
    if saved_tabs == OLD_TAB_ORDER:
        saved_tabs = list(TAB_ORDER)
    ordered_tabs: List[str] = []
    if isinstance(saved_tabs, list):
        for key in saved_tabs:
            key = str(key)
            if key in TAB_ORDER and key not in ordered_tabs:
                ordered_tabs.append(key)
    for key in TAB_ORDER:
        if key not in ordered_tabs:
            ordered_tabs.append(key)
    s["tab_order"] = ordered_tabs
    gl_defaults = default_gene_lab_settings()
    s["gene_lab_enabled"] = bool(s.get("gene_lab_enabled", gl_defaults["gene_lab_enabled"]))
    if s.get("species_profile") not in SPECIES_PROFILES:
        s["species_profile"] = gl_defaults["species_profile"]
    if s.get("racing_preset") not in RACING_PRESETS:
        s["racing_preset"] = gl_defaults["racing_preset"]
    hp = dict(gl_defaults["helix_presets"])
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
    s = force_caseoh_override_settings(s)
    if s.get("caseoh_mode", False):
        # Easter egg mode: slow displayed winners, fast SIM turnaround.
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
    s = apply_exploding_sim_overrides(s)
    return s


def patch_payloads(profile: Dict[str, Any], settings: Dict[str, Any]) -> List[Tuple[str, bytes]]:
    p = profile["patches"]
    s = normalize_settings(profile, settings)
    out: List[Tuple[str, bytes]] = []

    def add_i32(key: str, value: int) -> None:
        if key in p:
            out.append((key, struct.pack("<i", int(value))))

    def add_u8(key: str, value: int) -> None:
        if key in p:
            out.append((key, bytes([max(0, min(255, int(value)))])))

    def add_f32(key: str, value: float) -> None:
        if key in p:
            out.append((key, struct.pack("<f", float(value))))

    def add_bytes(key: str, payload: bytes) -> None:
        if key in p:
            out.append((key, payload))

    def add_generation_display(value: int, enabled: bool) -> None:
        key = "generation_display_limit"
        if key not in p:
            return
        add_bytes(key, bytes.fromhex(str(p[key]["original"])))

    def add_race_display(value: int, enabled: bool) -> None:
        key = "race_display_limit"
        current_key = "race_display_current"
        if key not in p or current_key not in p:
            return
        payload = bytes.fromhex(str(p[key]["original"])) + bytes.fromhex(str(p[current_key]["original"]))
        add_bytes(key, payload)

    add_i32("min_finish_frames", s["min_finish_frames"])
    add_i32("no_progress_frames", s["no_progress_frames"])
    add_i32("max_sim_frames", s["max_sim_frames"])
    add_i32("valid_result_max", s["valid_result_max"])

    original_branch = bytes.fromhex(str(p["early_finish_branch"]["original"]))
    out.append(("early_finish_branch", (b"\xEB" + original_branch[1:2]) if s.get("always_accept_early_finish") else original_branch))
    out.append(("time_format", FMT_BY_PRECISION[int(s["display_precision"])]))

    if s.get("enable_search_controls"):
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
        s.update(search_values)

    for key in SEARCH_I32:
        add_i32(key, search_values[key])
    if s.get("enable_search_controls"):
        add_i32("ram_generation_limit_upgraded", search_values["initial_generation_limit"])
        add_i32("ram_generation_limit_base", search_values["initial_generation_limit"])
        add_i32("ram_genepool_size_upgraded", search_values["initial_genepool_size"])
        add_i32("ram_genepool_size_base", search_values["initial_genepool_size"])
    else:
        add_i32("ram_generation_limit_upgraded", int(original(profile, "ram_generation_limit_upgraded", original(profile, "initial_generation_limit", 16))))
        add_i32("ram_generation_limit_base", int(original(profile, "ram_generation_limit_base", 8)))
        add_i32("ram_genepool_size_upgraded", int(original(profile, "ram_genepool_size_upgraded", original(profile, "initial_genepool_size", 40))))
        add_i32("ram_genepool_size_base", int(original(profile, "ram_genepool_size_base", 20)))
    for key in SEARCH_U8:
        add_u8(key, search_values[key])
    add_generation_display(search_values["initial_generation_limit"], bool(s.get("enable_search_controls")))
    add_race_display(search_values["initial_genepool_size"] // 4, bool(s.get("enable_search_controls")))
    for key in DISPLAY_NUMERATOR_KEYS:
        if key in p:
            add_bytes(key, bytes.fromhex(str(p[key]["original"])))
    for key in ADVANCED_FLOAT_KEYS:
        if key in s:
            add_f32(key, s[key])
    return out


def patch_exe_file(branch: Path, profile: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
    exe = branch / "Horsey.exe"
    if not exe.exists():
        raise FileNotFoundError(exe)
    data = bytearray(exe.read_bytes())
    for key, payload in patch_payloads(profile, settings):
        if key not in profile["patches"]:
            continue
        off = int(profile["patches"][key]["file_off"])
        data[off:off + len(payload)] = payload
    exe.write_bytes(data)
    s = normalize_settings(profile, settings)
    if not s.get("enable_search_controls"):
        for key in SEARCH_KEYS:
            s[key] = int(original(profile, key, s.get(key, 0)))
    apply_gene_stack(branch, s)
    apply_caseoh_art(branch)
    write_settings(branch, s)
    return s


def branch_patch_verification(branch: Path, profile: Dict[str, Any], settings: Dict[str, Any]) -> str:
    exe = branch / "Horsey.exe"
    if not exe.exists():
        return ""
    try:
        data = exe.read_bytes()
        payloads = dict(patch_payloads(profile, dict(settings)))
    except Exception as exc:
        return f"\nCould not verify branch bytes: {exc}"
    results: List[str] = []
    for key in VERIFY_PATCH_KEYS:
        patch = profile.get("patches", {}).get(key)
        payload = payloads.get(key)
        if not patch or payload is None:
            continue
        off = int(patch["file_off"])
        actual = data[off:off + len(payload)]
        label = VERIFY_PATCH_LABELS.get(key, key)
        results.append(f"{label} {'OK' if actual == payload else 'needs save'}")
    if not results:
        return ""
    return "\nVerified branch bytes: " + "; ".join(results) + "."


def patch_running_process(
    profile: Dict[str, Any],
    settings: Dict[str, Any],
    preferred_exe: Path | None = None,
    previous_settings: Dict[str, Any] | None = None,
) -> str:
    pid, base, path = find_horsey_process(preferred_exe)
    sim_active, sim_detail = _sim9000_appears_active(pid, profile, settings, previous_settings)
    msg = f"Found running Horsey.exe pid={pid}, base={base:#x}\n{path}"
    if sim_active:
        msg += (
            f"\nSIM9000 is active ({sim_detail}). Skipped live rewriting {LIVE_GUARDED_PATCH_LABELS} "
            "to avoid crashing the current SIM run. Use Save to branch files for those startup-level settings."
        )
    else:
        for key, payload in patch_payloads(profile, settings):
            if key not in profile["patches"]:
                continue
            addr = base + int(profile["patches"][key]["rva"])
            write_process(pid, addr, payload)
        msg += f"\nStartup-level SIM patch bytes updated in the running game ({sim_detail})."
    msg += patch_live_sim_state(pid, profile, settings, previous_settings)
    return msg


class Scrollable(ttk.Frame):
    def __init__(self, parent: tk.Widget):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        ybar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.frame = ttk.Frame(self.canvas)
        self.frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.window_id = self.canvas.create_window((0, 0), window=self.frame, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.window_id, width=e.width))
        self.canvas.configure(yscrollcommand=ybar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        ybar.pack(side="right", fill="y")

    def contains(self, widget: tk.Widget) -> bool:
        """True when the mouse wheel event came from this scroll area or one of its children."""
        widget_name = str(widget)
        return widget_name == str(self.canvas) or widget_name.startswith(str(self.frame))

    def scroll_units(self, units: int) -> None:
        self.canvas.yview_scroll(units, "units")


class OverlayApp(tk.Tk):
    def __init__(self, branch: Path):
        super().__init__()
        self.branch = branch
        self.horsey_exe = self.branch / "Horsey.exe"
        self.profile = read_profile(branch)
        self.settings = read_settings(branch, self.profile)
        self.vars: Dict[str, Any] = {}
        self.scale_widgets: List[Any] = []
        self.scrollables: List[Scrollable] = []
        self._live_patch_running = False
        self.live_apply_button: tk.Button | None = None
        self.title("HorseyGameCaseOhMod v2")
        icon_path = Path(__file__).resolve().parent / "assets" / "HorseyGameCaseOhMod.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(default=str(icon_path))
            except Exception:
                pass
        self.geometry("920x760")
        self.minsize(760, 620)
        self._configure_fonts()
        self.topmost_var = tk.BooleanVar(value=bool(self.settings.get("window_topmost", False)))
        self.attributes("-topmost", bool(self.topmost_var.get()))
        self.resizable(True, True)
        self._build_ui()
        self._update_labels()
        self._bind_mousewheel()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _configure_fonts(self) -> None:
        self.option_add("*Font", "{Segoe UI} 11")
        self.option_add("*Text.Font", "Consolas 11")
        for font_name in ["TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkTooltipFont"]:
            try:
                font = tkfont.nametofont(font_name)
            except tk.TclError:
                continue
            if font_name == "TkTextFont":
                font.configure(family="Consolas", size=11)
            else:
                font.configure(family="Segoe UI", size=11)
        style = ttk.Style(self)
        style.configure(".", font="{Segoe UI} 11")
        style.configure("TButton", padding=(8, 5))
        style.configure("TCheckbutton", padding=(2, 3))
        style.configure("TRadiobutton", padding=(2, 3))
        style.configure("TNotebook", tabposition="n")
        style.configure("TNotebook.Tab", font="{Segoe UI} 11 bold", padding=(16, 8))
        style.configure("TLabelframe.Label", font="{Segoe UI} 11 bold")
        style.configure("Title.TLabel", font="{Segoe UI} 20 bold")
        style.configure("Subtle.TLabel", foreground="#444444")
        style.configure("Status.TLabel", foreground="#1f3a5f")

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)

        self.vars["streamer_privacy"] = tk.BooleanVar(value=bool(self.settings.get("streamer_privacy", True)))
        self.vars["show_file_paths"] = tk.BooleanVar(value=bool(self.settings.get("show_file_paths", False)))

        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 8))
        title_area = ttk.Frame(header)
        title_area.pack(side="left", fill="x", expand=True)
        ttk.Label(title_area, text="HorseyGameCaseOhMod v2", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            title_area,
            text="Direct DNA, SIM9000 tuning, and copied-branch tools for Horsey Game.",
            style="Subtle.TLabel",
            wraplength=680,
        ).pack(anchor="w", pady=(1, 2))
        self.branch_label_var = tk.StringVar(value="")
        self.branch_label = ttk.Label(title_area, textvariable=self.branch_label_var, style="Subtle.TLabel", wraplength=720)
        self.branch_label.pack(anchor="w")
        self._refresh_privacy()
        self.status = tk.StringVar(value="Ready. Patch running game for immediate changes. Patch disk + restart for changes that load at startup.")

        header_actions = ttk.Frame(header)
        header_actions.pack(side="right", anchor="ne", padx=(12, 0))
        ttk.Button(header_actions, text="Fit", command=self.dock_next_to_horsey).pack(side="left", padx=(0, 6))
        ttk.Button(header_actions, text="Hide", command=self.toggle_panel_visibility).pack(side="left")
        ttk.Checkbutton(header_actions, text="Top", variable=self.topmost_var, command=self.toggle_topmost).pack(side="left", padx=(8, 0))

        status_row = ttk.Frame(outer)
        status_row.pack(fill="x", pady=(0, 8))
        ttk.Label(status_row, textvariable=self.status, style="Status.TLabel", wraplength=840).pack(anchor="w")

        self._build_action_bar(outer)

        self.current_tab_key = ""
        saved_order = self.settings.get("tab_order", TAB_ORDER)
        self.tab_order = [key for key in saved_order if key in TAB_ORDER]
        for key in TAB_ORDER:
            if key not in self.tab_order:
                self.tab_order.append(key)

        self.tab_strip = tk.Frame(outer, bg="#c5cad1", highlightthickness=1, highlightbackground="#aeb5bf")
        self.tab_strip.pack(fill="x")
        content_shell = tk.Frame(outer, bg="#aeb5bf")
        content_shell.pack(fill="both", expand=True)
        self.tab_content = ttk.Frame(content_shell, padding=4)
        self.tab_content.pack(fill="both", expand=True, padx=1, pady=(0, 1))

        self.dna_tab = Scrollable(self.tab_content)
        self.core_tab = Scrollable(self.tab_content)
        self.gene_lab_tab = Scrollable(self.tab_content)
        self.search_tab = Scrollable(self.tab_content)
        self.settings_tab = Scrollable(self.tab_content)
        self.tab_widgets: Dict[str, Scrollable] = {
            "dna": self.dna_tab,
            "main": self.core_tab,
            "gene_lab": self.gene_lab_tab,
            "search": self.search_tab,
            "settings": self.settings_tab,
        }
        self.scrollables = list(self.tab_widgets.values())

        self._build_core(self.core_tab.frame)
        self._build_gene_lab(self.gene_lab_tab.frame)
        self._build_dna_editor(self.dna_tab.frame)
        self._build_search(self.search_tab.frame)
        self._build_settings(self.settings_tab.frame)
        self._render_tab_strip()
        self._show_tab(self.tab_order[0] if self.tab_order else "main")

    def _build_action_bar(self, parent: tk.Widget) -> None:
        bar = tk.Frame(parent, bg="#d4d9df", padx=4, pady=4, highlightthickness=1, highlightbackground="#aeb5bf")
        bar.pack(fill="x", pady=(0, 8))
        actions = [
            ("Apply to running game", self.patch_live, "#16784f", "#f0fff6"),
            ("Save to branch files", self.patch_disk, "#b76512", "#fff7ec"),
            ("Load baseline", self.preset_baseline, "#2f72d6", "#f1f6ff"),
            ("Restore normal search", self.preset_stock_search, "#6f747c", "#f6f7f8"),
        ]
        for index, (text, command, color, pale) in enumerate(actions):
            bar.grid_columnconfigure(index, weight=1, uniform="actions")
            button = tk.Button(
                bar,
                text=text,
                command=command,
                font=("Segoe UI", 11, "bold"),
                fg="#111111",
                bg=pale,
                activeforeground="#000000",
                activebackground="#ffffff",
                relief="raised",
                bd=2,
                highlightthickness=2,
                highlightbackground=color,
                highlightcolor=color,
                padx=8,
                pady=8,
                wraplength=160,
                justify="center",
                cursor="hand2",
                takefocus=True,
            )
            button.configure(
                default="active" if index == 0 else "normal",
                borderwidth=2,
            )
            button.grid(row=0, column=index, sticky="ew", padx=4, pady=2)
            if text == "Apply to running game":
                self.live_apply_button = button
            stripe = tk.Frame(bar, bg=color, height=4)
            stripe.grid(row=1, column=index, sticky="ew", padx=4, pady=(0, 2))

    def _masked_branch_text(self) -> str:
        if bool(self.vars.get("streamer_privacy", tk.BooleanVar(value=True)).get()) and not bool(self.vars.get("show_file_paths", tk.BooleanVar(value=False)).get()):
            return "Branch: <hidden for streaming>"
        return f"Branch: {self.branch}"

    def _refresh_privacy(self) -> None:
        try:
            self.branch_label_var.set(self._masked_branch_text())
            self.settings["streamer_privacy"] = bool(self.vars.get("streamer_privacy", tk.BooleanVar(value=True)).get())
            self.settings["show_file_paths"] = bool(self.vars.get("show_file_paths", tk.BooleanVar(value=False)).get())
            write_settings(self.branch, self.settings)
        except Exception:
            pass

    def _build_settings(self, root: tk.Widget) -> None:
        ttk.Label(
            root,
            text="Panel settings live here so the main tabs stay at the top. Drag the tabs to reorder them; the order is saved.",
            wraplength=840,
        ).pack(anchor="w", padx=4, pady=6)

        window = ttk.LabelFrame(root, text="Window", padding=10)
        window.pack(fill="x", padx=4, pady=6)
        ttk.Button(window, text="Fit side by side", command=self.dock_next_to_horsey).pack(side="left", padx=(0, 8))
        ttk.Checkbutton(window, text="Stay on top", variable=self.topmost_var, command=self.toggle_topmost).pack(side="left", padx=(0, 8))
        ttk.Button(window, text="Hide panel", command=self.toggle_panel_visibility).pack(side="left")

        privacy = ttk.LabelFrame(root, text="Streaming privacy", padding=10)
        privacy.pack(fill="x", padx=4, pady=6)
        ttk.Checkbutton(privacy, text="Hide folder paths", variable=self.vars["streamer_privacy"], command=self._refresh_privacy).pack(side="left", padx=(0, 8))
        ttk.Checkbutton(privacy, text="Temporarily show paths", variable=self.vars["show_file_paths"], command=self._refresh_privacy).pack(side="left")
        self._add_desc(privacy, "streamer_privacy")

    def _render_tab_strip(self) -> None:
        for child in self.tab_strip.winfo_children():
            child.destroy()
        self.tab_button_widgets: Dict[str, tk.Widget] = {}
        for key in self._current_tab_order():
            meta = TAB_META[key]
            active = key == getattr(self, "current_tab_key", "")
            bg = "#ffffff" if active else meta["pale"]
            holder = tk.Frame(
                self.tab_strip,
                bg=meta["color"],
                highlightthickness=1,
                highlightbackground=meta["color"],
            )
            holder.pack(side="left", padx=(0, 3), pady=(0, 0))
            tab_face = tk.Frame(holder, bg=bg, relief="solid", bd=1, cursor="hand2")
            tab_face.pack(fill="both", expand=True, padx=2, pady=(4, 0))
            icon = tk.Canvas(tab_face, width=24, height=24, bg=bg, highlightthickness=0, cursor="hand2")
            icon.pack(side="left", padx=(12, 6), pady=7)
            self._draw_tab_icon(icon, key, meta["color"])
            label = tk.Label(
                tab_face,
                text=meta["title"],
                bg=bg,
                fg="#121417",
                font=("Segoe UI", 12, "bold"),
                padx=0,
                pady=10,
                cursor="hand2",
            )
            label.pack(side="left", padx=(0, 14), pady=0)
            for widget in (holder, tab_face, icon, label):
                widget._tab_key = key  # type: ignore[attr-defined]
                widget.bind("<ButtonPress-1>", self._on_tab_press, add="+")
                widget.bind("<B1-Motion>", self._on_tab_drag, add="+")
                widget.bind("<ButtonRelease-1>", self._on_tab_release, add="+")
            self.tab_button_widgets[key] = holder
        tk.Frame(self.tab_strip, bg="#c5cad1").pack(side="left", fill="x", expand=True)

    def _draw_tab_icon(self, canvas: tk.Canvas, key: str, color: str) -> None:
        dark = "#14171a"
        canvas.delete("all")
        if key == "main":
            for y, knob_x in [(6, 15), (12, 8), (18, 17)]:
                canvas.create_line(4, y, 20, y, fill=dark, width=2, capstyle="round")
                canvas.create_oval(knob_x - 3, y - 3, knob_x + 3, y + 3, fill=color, outline=dark, width=1)
        elif key == "search":
            canvas.create_polygon(13, 2, 5, 13, 12, 13, 9, 22, 20, 9, 13, 9, fill=color, outline=dark, width=1)
        elif key == "gene_lab":
            canvas.create_line(7, 3, 17, 21, fill=color, width=2, smooth=True)
            canvas.create_line(17, 3, 7, 21, fill=color, width=2, smooth=True)
            for y in (6, 10, 14, 18):
                canvas.create_line(8, y, 16, y, fill=dark, width=1)
                canvas.create_oval(6, y - 2, 10, y + 2, fill="#ffffff", outline=color, width=1)
                canvas.create_oval(14, y - 2, 18, y + 2, fill="#ffffff", outline=color, width=1)
        elif key == "dna":
            canvas.create_line(7, 4, 7, 20, fill=color, width=2)
            canvas.create_line(17, 4, 17, 20, fill=color, width=2)
            for y in (6, 11, 16):
                canvas.create_line(7, y, 17, y + 2, fill=dark, width=2)
        else:
            cx = cy = 12
            for x, y in [(12, 2), (12, 22), (2, 12), (22, 12), (5, 5), (19, 19), (5, 19), (19, 5)]:
                canvas.create_line(cx, cy, x, y, fill=color, width=2)
            canvas.create_oval(5, 5, 19, 19, fill="#ffffff", outline=dark, width=2)
            canvas.create_oval(9, 9, 15, 15, fill=color, outline=dark, width=1)

    def _show_tab(self, key: str) -> None:
        if key not in self.tab_widgets:
            key = "main"
        for widget in self.tab_widgets.values():
            widget.pack_forget()
        self.tab_widgets[key].pack(fill="both", expand=True)
        self.current_tab_key = key
        self._render_tab_strip()

    def _current_tab_order(self) -> List[str]:
        order = [key for key in getattr(self, "tab_order", list(TAB_ORDER)) if key in TAB_ORDER]
        for key in TAB_ORDER:
            if key not in order:
                order.append(key)
        self.tab_order = order
        return list(order)

    def _save_tab_order(self) -> None:
        try:
            self.settings["tab_order"] = self._current_tab_order()
            write_settings(self.branch, self.settings)
        except Exception:
            pass

    def _event_tab_key(self, event: tk.Event) -> str | None:
        widget = event.widget
        while widget is not None:
            key = getattr(widget, "_tab_key", None)
            if key in TAB_ORDER:
                return key
            widget = getattr(widget, "master", None)
        return None

    def _tab_key_at_screen_position(self, x_root: int, y_root: int) -> str | None:
        widget = self.winfo_containing(x_root, y_root)
        while widget is not None:
            key = getattr(widget, "_tab_key", None)
            if key in TAB_ORDER:
                return key
            widget = getattr(widget, "master", None)
        return None

    def _on_tab_press(self, event: tk.Event) -> None:
        key = self._event_tab_key(event)
        self._drag_tab_key = key
        self._drag_tab_moved = False

    def _on_tab_drag(self, event: tk.Event) -> None:
        source = getattr(self, "_drag_tab_key", None)
        target = self._tab_key_at_screen_position(int(event.x_root), int(event.y_root))
        if source is None or target is None or source == target:
            return
        order = self._current_tab_order()
        if source not in order or target not in order:
            return
        order.remove(source)
        target_index = order.index(target)
        order.insert(target_index, source)
        self.tab_order = order
        self._drag_tab_moved = True
        self._save_tab_order()
        self._render_tab_strip()

    def _on_tab_release(self, _event: tk.Event) -> None:
        key = getattr(self, "_drag_tab_key", None)
        if key and not getattr(self, "_drag_tab_moved", False):
            self._show_tab(key)
        if key:
            self._save_tab_order()
        self._drag_tab_key = None
        self._drag_tab_moved = False

    def _bind_mousewheel(self) -> None:
        # Bind once at the window level so the wheel works over labels, sliders,
        # buttons, and nested frames inside the active tab.
        self.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
        self.bind_all("<Button-4>", self._on_mousewheel, add="+")
        self.bind_all("<Button-5>", self._on_mousewheel, add="+")

    def _on_mousewheel(self, event: tk.Event) -> str | None:
        for scrollable in getattr(self, "scrollables", []):
            if scrollable.contains(event.widget):
                if getattr(event, "num", None) == 4:
                    units = -3
                elif getattr(event, "num", None) == 5:
                    units = 3
                else:
                    delta = int(getattr(event, "delta", 0))
                    if delta == 0:
                        return None
                    units = -max(-5, min(5, delta // 120 if abs(delta) >= 120 else (1 if delta > 0 else -1)))
                scrollable.scroll_units(units)
                return "break"
        return None

    def toggle_panel_visibility(self) -> None:
        if self.state() == "iconic":
            self.deiconify()
            self.lift()
            self.focus_force()
            # Brief topmost pulse helps it appear above the game without making
            # Stay on top permanent.
            if not bool(self.topmost_var.get()):
                self.attributes("-topmost", True)
                self.after(250, lambda: self.attributes("-topmost", False))
            self.status.set("CaseOh90000 panel restored.")
        else:
            self.iconify()

    def on_close(self) -> None:
        try:
            self.settings = self._collect()
            write_settings(self.branch, self.settings)
        except Exception:
            pass
        self.destroy()

    def toggle_topmost(self) -> None:
        self.attributes("-topmost", bool(self.topmost_var.get()))
        self.settings["window_topmost"] = bool(self.topmost_var.get())
        write_settings(self.branch, self.settings)

    def dock_next_to_horsey(self) -> None:
        result = find_horsey_window(self.horsey_exe)
        if result is None:
            self.status.set("Horsey window not found yet. Start the mod branch, then press 'Fit'.")
            return
        _hwnd, _rect = result
        self.update_idletasks()
        panel_rect, horsey_rect = self._side_by_side_layout()
        if os.name == "nt":
            position_horsey_window(*horsey_rect, preferred_exe=self.horsey_exe)
        self._place_panel(panel_rect)
        self.status.set("Fit Horsey and the CaseOh90000 panel side by side.")

    def _side_by_side_layout(self) -> Tuple[Tuple[int, int, int, int], Tuple[int, int, int, int]]:
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        panel_w = min(780, max(720, int(screen_w * 0.40)))
        panel_x = 0
        overlap = 8
        horsey_x = max(0, panel_w - overlap)
        horsey_y = max(72, min(108, screen_h // 10))
        horsey_w = max(760, screen_w - horsey_x)
        horsey_h = max(620, screen_h - horsey_y - 92)
        panel_y = horsey_y
        panel_h = max(620, horsey_h - WINDOW_CHROME_HEIGHT_GUESS)
        return (panel_w, panel_h, panel_x, panel_y), (horsey_x, horsey_y, horsey_w, horsey_h)

    def _place_panel(self, panel_rect: Tuple[int, int, int, int]) -> None:
        panel_w, panel_h, x, y = panel_rect
        self.geometry(f"{panel_w}x{panel_h}+{x}+{y}")

    def _dock_panel_to_horsey_rect(self, rect: Tuple[int, int, int, int]) -> None:
        left, top, right, bottom = rect
        self.update_idletasks()
        panel_w = max(760, self.winfo_width())
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        panel_h = max(620, min(max(620, bottom - top - WINDOW_CHROME_HEIGHT_GUESS), screen_h - top - 56))
        x = right + 10
        if x + panel_w > screen_w:
            x = max(0, left - panel_w - 10)
        y = max(0, min(top, screen_h - panel_h - 40))
        self.geometry(f"{panel_w}x{panel_h}+{x}+{y}")

    def _add_desc(self, parent: tk.Widget, key: str, wraplength: int = 820) -> None:
        label = ttk.Label(parent, text=DESCRIPTIONS.get(key, ""), wraplength=wraplength, foreground="#333333")
        label.pack(anchor="w", fill="x", pady=(2, 2))
        self._wrap_with_container(label)

    def _wrap_with_container(self, label: ttk.Label, minimum: int = 160) -> None:
        def rewrap(event: tk.Event, target: ttk.Label = label) -> None:
            width = max(minimum, int(getattr(event, "width", minimum)) - 8)
            target.configure(wraplength=width)

        label.bind("<Configure>", rewrap, add="+")

    def _add_scale(self, parent: tk.Widget, key: str, label: str, lo: int, hi: int, wraplength: int = 820) -> None:
        var = tk.IntVar(value=int(self.settings.get(key, lo)))
        self.vars[key] = var
        box = ttk.LabelFrame(parent, text=label, padding=8)
        box.pack(fill="x", padx=4, pady=5)
        value = ttk.Label(box, text="")
        value.pack(anchor="w")
        ttk.Scale(box, from_=lo, to=hi, variable=var, orient="horizontal", command=lambda _=None: self._update_labels()).pack(fill="x")
        self._add_desc(box, key, wraplength=wraplength)
        box.key = key  # type: ignore[attr-defined]
        box.value_label = value  # type: ignore[attr-defined]
        self.scale_widgets.append(box)

    def _build_core(self, root: tk.Widget) -> None:
        ttk.Label(root, text="Start here. These are the practical SIM9000 settings that matter most. The proven baseline keeps SIM9000's normal search behavior.", wraplength=840).pack(anchor="w", padx=4, pady=6)
        columns = ttk.Frame(root)
        columns.pack(fill="x")
        left = ttk.Frame(columns)
        right = ttk.Frame(columns)
        left.pack(side="left", fill="both", expand=True)
        right.pack(side="left", fill="both", expand=True)
        self._add_scale(left, "min_finish_frames", "Minimum accepted finish frames / 5.0 barrier", 0, 600, wraplength=390)
        self._add_scale(right, "no_progress_frames", "Stall/no-progress cull frames", 0, 1800, wraplength=390)
        self._add_scale(left, "max_sim_frames", "Maximum SIM9000 candidate frame budget", 300, 21600, wraplength=390)
        self._add_scale(right, "valid_result_max", "Valid-result score max", 1000, 30000, wraplength=390)

        precision = ttk.LabelFrame(root, text="Display precision", padding=8)
        precision.pack(fill="x", padx=4, pady=5)
        self.vars["display_precision"] = tk.IntVar(value=int(self.settings.get("display_precision", 3)))
        for text, val in [("T:%.1f - original", 1), ("T:%.2f", 2), ("T:%.3f - recommended", 3)]:
            ttk.Radiobutton(precision, text=text, value=val, variable=self.vars["display_precision"]).pack(anchor="w")
        self._add_desc(precision, "display_precision")


        caseoh = ttk.LabelFrame(root, text="Easter Egg", padding=8)
        caseoh.pack(fill="x", padx=4, pady=5)
        self.vars["caseoh_mode"] = tk.BooleanVar(value=bool(self.settings.get("caseoh_mode", False)))
        ttk.Checkbutton(caseoh, text="caseOh mOde", variable=self.vars["caseoh_mode"]).pack(anchor="w")
        self._add_desc(caseoh, "caseoh_mode")

        presets = ttk.LabelFrame(root, text="Safe presets", padding=8)
        presets.pack(fill="x", padx=4, pady=5)
        ttk.Button(presets, text="Baseline: uncap only", command=self.preset_baseline).pack(side="left", padx=3)
        ttk.Button(presets, text="Reject very slow winners", command=self.preset_reject_slow).pack(side="left", padx=3)
        ttk.Label(presets, text="Use 'Reject very slow winners' only if SIM9000 starts returning huge times; it can filter slow-start outliers.", wraplength=680).pack(anchor="w", pady=(8, 0))

    def _build_gene_lab(self, root: tk.Widget) -> None:
        ttk.Label(
            root,
            text="SIM Gene Lab is an advanced expression-table experiment. It can be fun for branch-wide testing, but it is not the recommended way to make exact horses. Use Direct DNA Editor for precise A/T/C/G changes.",
            wraplength=680,
        ).pack(anchor="w", padx=4, pady=6)

        box = ttk.LabelFrame(root, text="Global SIM gene profile", padding=8)
        box.pack(fill="x", padx=4, pady=5)
        self.vars["gene_lab_enabled"] = tk.BooleanVar(value=bool(self.settings.get("gene_lab_enabled", False)))
        ttk.Checkbutton(box, text="Enable SIM Gene Lab profile patching", variable=self.vars["gene_lab_enabled"]).pack(anchor="w")
        self.vars["exploding_mode"] = tk.BooleanVar(value=bool(self.settings.get("exploding_mode", False)))
        ttk.Checkbutton(box, text="Exploding finisher mode", variable=self.vars["exploding_mode"]).pack(anchor="w", pady=(4, 0))
        ttk.Label(box, text="Anything-goes preset: applies fast-finish SIM settings, overwrites no-glitch protections, and prepares seed DNA.", wraplength=680, foreground="#333333").pack(anchor="w", pady=(2, 0))
        self._add_desc(box, "gene_lab_enabled")

        row = ttk.Frame(box); row.pack(fill="x", pady=(8, 2))
        ttk.Label(row, text="Species/body-plan lock", width=24).pack(side="left")
        self.vars["species_profile"] = tk.StringVar(value=str(self.settings.get("species_profile", "Any / no species lock")))
        ttk.OptionMenu(row, self.vars["species_profile"], self.vars["species_profile"].get(), *SPECIES_PROFILES).pack(side="left", fill="x", expand=True)
        self._add_desc(box, "species_profile")

        row = ttk.Frame(box); row.pack(fill="x", pady=(8, 2))
        ttk.Label(row, text="Racing archetype", width=24).pack(side="left")
        self.vars["racing_preset"] = tk.StringVar(value=str(self.settings.get("racing_preset", "None / normal genes")))
        ttk.OptionMenu(row, self.vars["racing_preset"], self.vars["racing_preset"].get(), *RACING_PRESETS).pack(side="left", fill="x", expand=True)
        self._add_desc(box, "racing_preset")

        quick = ttk.LabelFrame(root, text="Quick archetype buttons", padding=8)
        quick.pack(fill="x", padx=4, pady=5)
        for label, species, race in [
            ("Clean speed horse", "Horse", "Clean speed horse"),
            ("Fast wheeled horse", "Alligator", "Fast wheeled horse"),
            ("Tank / multi-wheel", "Car", "Tank / multi-wheel"),
            ("Oval wheel roller", "Car", "Oval wheel roller"),
            ("Living Segway", "Car", "Living Segway"),
            ("Tail launcher", "Any / no species lock", "Tail launcher"),
            ("Exploding finisher", "Freak / mixed", "Exploding finisher"),
            ("Tiny car", "Tiny critter", "Tiny car"),
            ("No-glitch intact", "Horse", "No-glitch intact racer"),
        ]:
            ttk.Button(quick, text=label, command=lambda sp=species, rp=race: self.preset_gene_lab(sp, rp)).pack(side="left", padx=3, pady=2)
        ttk.Button(quick, text="Clear Gene Lab", command=self.clear_gene_lab).pack(side="left", padx=3, pady=2)
        ttk.Button(quick, text="Copy exploding seed DNA", command=self.copy_exploding_seed).pack(side="left", padx=3, pady=2)

        per = ttk.LabelFrame(root, text="Per-helix controls - test one chromosome at a time", padding=8)
        per.pack(fill="x", padx=4, pady=5)
        self._add_desc(per, "helix_presets")
        self.helix_vars: Dict[str, tk.StringVar] = {}
        hp = dict(default_gene_lab_settings()["helix_presets"])
        hp.update(self.settings.get("helix_presets") or {})
        for i in range(20):
            h = f"{i:02d}"
            row = ttk.Frame(per); row.pack(fill="x", pady=1)
            start, end = HELIX_RANGES[h]
            ttk.Label(row, text=f"H{h}", width=5).pack(side="left")
            ttk.Label(row, text=f"P00-P{end-1:02d}", width=14, foreground="#555555").pack(side="left")
            var = tk.StringVar(value=hp.get(h, "Unchanged"))
            self.helix_vars[h] = var
            ttk.OptionMenu(row, var, var.get(), *HELIX_PRESETS).pack(side="left", fill="x", expand=True)

        status = ttk.LabelFrame(root, text="Gene Lab status", padding=8)
        status.pack(fill="x", padx=4, pady=5)
        ttk.Button(status, text="Show branch Gene Lab report", command=self.show_gene_lab_report).pack(side="left", padx=3)
        ttk.Button(status, text="Restore stock genes.xml", command=self.restore_gene_lab_now).pack(side="left", padx=3)
        ttk.Label(status, text="Saving to branch files writes data/genes.xml. Restart Horsey for these changes to load.", wraplength=680).pack(anchor="w", pady=(8, 0))


    def _build_dna_editor(self, root: tk.Widget) -> None:
        ttk.Label(
            root,
            text="Direct DNA Editor makes pasteable 40-line Horsey DNA. Expand H00-H19 to choose A/T/C/G for each gene on each strand. This is exact DNA editing, not genes.xml expression patching.",
            wraplength=680,
        ).pack(anchor="w", padx=4, pady=6)
        info = ttk.LabelFrame(root, text="DNA text", padding=8)
        info.pack(fill="x", padx=4, pady=5)
        self._add_desc(info, "dna_editor")
        self.dna_text = tk.Text(info, height=8, wrap="none", undo=True)
        saved = str(self.settings.get("dna_editor_text", "") or "")
        if saved.strip():
            self.dna_text.insert("1.0", saved.strip())
        self.dna_text.pack(fill="x", expand=True, pady=(6, 4))
        self.dna_status = tk.StringVar(value="Paste DNA, load a preset, or expand a helix below.")
        ttk.Label(info, textvariable=self.dna_status, wraplength=660).pack(anchor="w", pady=(0, 4))
        buttons = ttk.Frame(info); buttons.pack(fill="x")
        ttk.Button(buttons, text="Validate and load", command=self.dna_load_text_into_editor).pack(side="left", padx=3, pady=2)
        ttk.Button(buttons, text="Update DNA text", command=self.dna_update_text_from_controls).pack(side="left", padx=3, pady=2)
        ttk.Button(buttons, text="Copy DNA", command=self.dna_copy_text).pack(side="left", padx=3, pady=2)
        ttk.Button(buttons, text="Save DNA text file", command=self.dna_save_to_branch).pack(side="left", padx=3, pady=2)
        buttons2 = ttk.Frame(info); buttons2.pack(fill="x")
        ttk.Button(buttons2, text="Paste DNA", command=self.dna_paste_clipboard).pack(side="left", padx=3, pady=2)
        ttk.Button(buttons2, text="Paste SIM result + locks", command=self.dna_paste_apply_locks).pack(side="left", padx=3, pady=2)
        ttk.Button(buttons2, text="Load .txt file", command=self.dna_load_file).pack(side="left", padx=3, pady=2)
        ttk.Button(buttons2, text="Load exploding seed", command=self.dna_load_exploding_seed).pack(side="left", padx=3, pady=2)
        ttk.Button(buttons2, text="Clear DNA to A/A", command=self.dna_clear_blank).pack(side="left", padx=3, pady=2)

        preset_box = ttk.LabelFrame(root, text="Small DNA presets", padding=8)
        preset_box.pack(fill="x", padx=4, pady=5)
        ttk.Label(preset_box, text="Presets change a small number of visible A/T/C/G bases. You can see each edit, adjust it, or clear the locked bases later.", wraplength=660).pack(anchor="w", pady=(0, 4))
        row = ttk.Frame(preset_box); row.pack(fill="x")
        preset = str(self.settings.get("dna_preset", "Do not change"))
        if preset not in DIRECT_PRESET_NAMES:
            preset = "Do not change"
        self.dna_preset_var = tk.StringVar(value=preset)
        ttk.OptionMenu(row, self.dna_preset_var, self.dna_preset_var.get(), *DIRECT_PRESET_NAMES, command=lambda _=None: self.dna_save_editor_settings()).pack(side="left", fill="x", expand=True, padx=(0, 6))
        strand = str(self.settings.get("dna_preset_strands", "both"))
        if strand not in {"both", "top", "bottom"}:
            strand = "both"
        self.dna_strand_var = tk.StringVar(value=strand)
        ttk.OptionMenu(row, self.dna_strand_var, self.dna_strand_var.get(), "both", "top", "bottom", command=lambda _=None: self.dna_save_editor_settings()).pack(side="left", padx=(0, 6))
        ttk.Button(row, text="Apply preset", command=self.dna_apply_direct_preset).pack(side="left")

        lock_box = ttk.LabelFrame(root, text="DNA locks for SIM results", padding=8)
        lock_box.pack(fill="x", padx=4, pady=5)
        ttk.Label(lock_box, text="Edited bases are remembered here. Paste a new SIM result, then apply the locked bases to keep only your chosen changes.", wraplength=660).pack(anchor="w", pady=(0, 4))
        self.dna_output_locks = normalize_dna_locks(self.settings.get("dna_output_locks", {}))
        self.dna_lock_status = tk.StringVar(value="")
        lock_row = ttk.Frame(lock_box); lock_row.pack(fill="x")
        ttk.Button(lock_row, text="Apply locked bases", command=self.dna_apply_locks_to_text).pack(side="left", padx=3, pady=2)
        ttk.Button(lock_row, text="Clear locked bases", command=self.dna_clear_locks).pack(side="left", padx=3, pady=2)
        ttk.Label(lock_box, textvariable=self.dna_lock_status, wraplength=660, foreground="#333333").pack(anchor="w", pady=(4, 0))
        self.dna_update_lock_status()

        self.dna_editor_box = ttk.LabelFrame(root, text="Expandable helix editor H00-H19", padding=8)
        self.dna_editor_box.pack(fill="x", padx=4, pady=5)
        quick_open = ttk.Frame(self.dna_editor_box)
        quick_open.pack(fill="x", pady=(0, 6))
        ttk.Label(quick_open, text="Fast open:").pack(side="left", padx=(0, 4))
        ttk.Button(quick_open, text="Speed H18", command=lambda: self.dna_open_helixes(["18"])).pack(side="left", padx=2)
        ttk.Button(quick_open, text="Wheels H01/H08/H09", command=lambda: self.dna_open_helixes(["01", "08", "09"])).pack(side="left", padx=2)
        ttk.Button(quick_open, text="Tail H07/H02", command=lambda: self.dna_open_helixes(["07", "02"])).pack(side="left", padx=2)
        ttk.Button(quick_open, text="Timing H19", command=lambda: self.dna_open_helixes(["19"])).pack(side="left", padx=2)
        ttk.Button(quick_open, text="Collapse all", command=self.dna_collapse_all_helixes).pack(side="right", padx=2)
        self.dna_position_vars: Dict[Tuple[str, int, int], tk.StringVar] = {}
        self.dna_helix_body: Dict[str, ttk.Frame] = {}
        self.dna_helix_open: Dict[str, bool] = {}
        self.dna_genome_cache = blank_genome("A")
        ok, _msg, parsed = normalize_dna(saved)
        if ok:
            self.dna_genome_cache = parsed
        for i in range(20):
            h = f"{i:02d}"
            holder = ttk.Frame(self.dna_editor_box)
            holder.pack(fill="x", pady=2)
            head = ttk.Frame(holder); head.pack(fill="x")
            ttk.Button(head, text=f"Expand H{h}", width=14, command=lambda helix=h: self.dna_toggle_helix(helix)).pack(side="left", padx=(0, 6))
            ttk.Label(head, text=f"{len(DNA_HELIX_GENE_NAMES[i])} genes", foreground="#555555").pack(side="left")
            body = ttk.Frame(holder)
            self.dna_helix_body[h] = body
            self.dna_helix_open[h] = False

    def dna_current_text(self) -> str:
        return self.dna_text.get("1.0", "end").strip()

    def dna_save_editor_settings(self) -> None:
        try:
            self.settings["dna_editor_text"] = self.dna_current_text() if hasattr(self, "dna_text") else str(self.settings.get("dna_editor_text", ""))
            if hasattr(self, "dna_preset_var"):
                preset = str(self.dna_preset_var.get())
                self.settings["dna_preset"] = preset if preset in DIRECT_PRESET_NAMES else "Do not change"
            if hasattr(self, "dna_strand_var"):
                strand = str(self.dna_strand_var.get())
                self.settings["dna_preset_strands"] = strand if strand in {"both", "top", "bottom"} else "both"
            self.settings["dna_output_locks"] = normalize_dna_locks(getattr(self, "dna_output_locks", {}))
            write_settings(self.branch, self.settings)
        except Exception:
            pass

    def dna_set_text(self, text: str) -> None:
        self.dna_text.delete("1.0", "end")
        self.dna_text.insert("1.0", text.strip())
        self.dna_save_editor_settings()

    def dna_update_lock_status(self) -> None:
        locks = normalize_dna_locks(getattr(self, "dna_output_locks", {}))
        self.dna_output_locks = locks
        count = len(locks)
        sample = []
        for key, base in sorted(locks.items())[:5]:
            h, pos, strand = key.split(":")
            side = "top" if strand == "0" else "bottom"
            sample.append(f"H{h} P{int(pos):02d} {side}={base}")
        suffix = "" if count <= 5 else f" + {count - 5} more"
        text = f"{count} locked base{'s' if count != 1 else ''}"
        if sample:
            text += ": " + ", ".join(sample) + suffix
        if hasattr(self, "dna_lock_status"):
            self.dna_lock_status.set(text)

    def dna_record_lock(self, helix: str, pos: int, strand: int, base: str) -> None:
        try:
            set_dna_lock(self.dna_output_locks, helix, pos, strand, base)
            self.dna_update_lock_status()
            self.dna_save_editor_settings()
        except Exception:
            pass

    def dna_apply_locks_to_genome(self, genome: Dict[str, List[str]]) -> int:
        self.dna_output_locks = normalize_dna_locks(getattr(self, "dna_output_locks", {}))
        return apply_dna_locks(genome, self.dna_output_locks)

    def dna_parse_current(self, apply_locks: bool = False) -> Tuple[bool, str, Dict[str, List[str]]]:
        ok, msg, genome = normalize_dna(self.dna_current_text())
        changed = self.dna_apply_locks_to_genome(genome) if ok and apply_locks else 0
        self._dna_last_lock_changes = changed
        self.dna_status.set(msg if ok else f"DNA problem: {msg}")
        if ok:
            self.dna_genome_cache = genome
            if changed:
                self.dna_set_text(format_dna(genome))
                self.dna_status.set(f"DNA is valid. Applied {changed} locked base{'s' if changed != 1 else ''}. Hash {dna_hash(format_dna(genome))}.")
        return ok, msg, genome

    def dna_load_text_into_editor(self, apply_locks: bool = False) -> None:
        ok, msg, genome = self.dna_parse_current(apply_locks=apply_locks)
        if ok:
            self.dna_genome_cache = genome
            self.dna_refresh_controls()
            locked = len(getattr(self, "dna_output_locks", {}))
            changed = int(getattr(self, "_dna_last_lock_changes", 0))
            if changed:
                extra = f" Applied {changed} locked base{'s' if changed != 1 else ''}. Active locks: {locked}."
            else:
                extra = f" Active locks: {locked}." if locked else ""
            self.dna_status.set(f"Loaded valid DNA into editor. Hash {dna_hash(format_dna(genome))}.{extra}")
        else:
            messagebox.showwarning("DNA validation", msg)

    def dna_refresh_controls(self) -> None:
        for (h, pos, strand), var in getattr(self, "dna_position_vars", {}).items():
            try:
                var.set(self.dna_genome_cache[h][strand][pos])
            except Exception:
                pass

    def dna_toggle_helix(self, helix: str) -> None:
        body = self.dna_helix_body[helix]
        if self.dna_helix_open.get(helix):
            body.pack_forget()
            self.dna_helix_open[helix] = False
            return
        if not body.winfo_children():
            self.dna_build_helix_body(helix, body)
        body.pack(fill="x", pady=(2, 6))
        self.dna_helix_open[helix] = True
        self.dna_refresh_controls()

    def dna_open_helixes(self, helixes: List[str]) -> None:
        for h in helixes:
            if h in self.dna_helix_body and not self.dna_helix_open.get(h):
                self.dna_toggle_helix(h)

    def dna_collapse_all_helixes(self) -> None:
        for h, body in self.dna_helix_body.items():
            if self.dna_helix_open.get(h):
                body.pack_forget()
                self.dna_helix_open[h] = False

    def dna_build_helix_body(self, helix: str, body: ttk.Frame) -> None:
        header = ttk.Frame(body); header.pack(fill="x")
        ttk.Label(header, text="Pos", width=5).pack(side="left")
        ttk.Label(header, text="Gene", width=26).pack(side="left")
        ttk.Label(header, text="Top", width=8).pack(side="left")
        ttk.Label(header, text="Bottom", width=8).pack(side="left")
        ttk.Label(header, text="Set both", width=20).pack(side="left")
        for pos, gene in enumerate(DNA_HELIX_GENE_NAMES[int(helix)]):
            row = ttk.Frame(body); row.pack(fill="x", pady=1)
            ttk.Label(row, text=f"P{pos:02d}", width=5).pack(side="left")
            ttk.Label(row, text=gene, width=26).pack(side="left")
            for strand in (0, 1):
                current = self.dna_genome_cache.get(helix, ["A" * DNA_HELIX_LENGTHS[helix]] * 2)[strand][pos]
                var = tk.StringVar(value=current)
                self.dna_position_vars[(helix, pos, strand)] = var
                ttk.OptionMenu(row, var, var.get(), *DNA_BASES, command=lambda value, h=helix, p=pos, s=strand: self.dna_position_changed(h, p, s, value)).pack(side="left", padx=(0, 4))
            quick = ttk.Frame(row); quick.pack(side="left")
            for base in DNA_BASES:
                ttk.Button(quick, text=base, width=2, command=lambda h=helix, p=pos, b=base: self.dna_set_both(h, p, b)).pack(side="left", padx=1)

    def dna_set_both(self, helix: str, pos: int, base: str) -> None:
        for strand in (0, 1):
            var = self.dna_position_vars.get((helix, pos, strand))
            if var:
                var.set(base)
            self.dna_record_lock(helix, pos, strand, base)
        self.dna_update_text_from_controls(status=f"Locked H{helix} P{pos:02d} to {base}/{base}.")

    def dna_position_changed(self, helix: str, pos: int, strand: int, base: str) -> None:
        base = str(base or "").upper()[:1]
        if base not in DNA_BASES:
            return
        self.dna_record_lock(helix, pos, strand, base)
        side = "top" if int(strand) == 0 else "bottom"
        self.dna_update_text_from_controls(status=f"Locked H{helix} P{pos:02d} {side} to {base}.")

    def dna_update_text_from_controls(self, status: str = "") -> None:
        ok, _msg, genome = normalize_dna(self.dna_current_text())
        if not ok:
            genome = self.dna_genome_cache
        for (h, pos, strand), var in getattr(self, "dna_position_vars", {}).items():
            seq = list(genome[h][strand])
            base = var.get().upper()
            if base in DNA_BASES:
                seq[pos] = base
            genome[h][strand] = ''.join(seq)
        text = format_dna(genome)
        self.dna_genome_cache = genome
        self.dna_set_text(text)
        self.dna_status.set(status or f"DNA text updated from editor controls. Hash {dna_hash(text)}.")

    def dna_apply_direct_preset(self) -> None:
        preset = self.dna_preset_var.get()
        if preset == "Do not change":
            return
        if preset == "Exploding finisher seed":
            self.dna_load_exploding_seed()
            return
        ok, _msg, genome = normalize_dna(self.dna_current_text())
        if not ok:
            genome = self.dna_genome_cache
        strands = self.dna_strand_var.get()
        changed = apply_direct_preset(genome, preset, strands=strands)
        target_strands = [0, 1] if strands == "both" else ([0] if strands == "top" else [1])
        for (helix, pos), base in DIRECT_PRESETS.get(preset, {}).items():
            for strand in target_strands:
                self.dna_record_lock(helix, pos, strand, base)
        text = format_dna(genome)
        self.dna_genome_cache = genome
        self.dna_set_text(text)
        self.dna_refresh_controls()
        self.dna_status.set(f"Applied {preset}: {len(changed)} positions changed and locked. Hash {dna_hash(text)}.")

    def dna_paste_clipboard(self) -> None:
        try:
            text = self.clipboard_get()
        except Exception as e:
            messagebox.showerror("Paste DNA", str(e))
            return
        self.dna_set_text(str(text).strip())
        self.dna_load_text_into_editor(apply_locks=False)

    def dna_paste_apply_locks(self) -> None:
        try:
            text = self.clipboard_get()
        except Exception as e:
            messagebox.showerror("Paste SIM result", str(e))
            return
        self.dna_set_text(str(text).strip())
        self.dna_load_text_into_editor(apply_locks=True)

    def dna_apply_locks_to_text(self) -> None:
        ok, msg, genome = normalize_dna(self.dna_current_text())
        if not ok:
            messagebox.showwarning("Apply DNA locks", msg)
            return
        changed = self.dna_apply_locks_to_genome(genome)
        text = format_dna(genome)
        self.dna_genome_cache = genome
        self.dna_set_text(text)
        self.dna_refresh_controls()
        if changed:
            self.dna_status.set(f"Applied {changed} locked base{'s' if changed != 1 else ''}. Hash {dna_hash(text)}.")
        else:
            self.dna_status.set(f"No DNA bases changed; locks already match this DNA. Hash {dna_hash(text)}.")

    def dna_clear_locks(self) -> None:
        self.dna_output_locks = {}
        self.dna_update_lock_status()
        self.dna_save_editor_settings()
        self.dna_status.set("Cleared DNA locks. Presets and manual edits will create new locked bases.")

    def dna_copy_text(self) -> None:
        text = self.dna_current_text()
        ok, msg, genome = normalize_dna(text)
        if not ok:
            messagebox.showwarning("DNA copy", msg)
            return
        normalized = format_dna(genome)
        self.clipboard_clear(); self.clipboard_append(normalized)
        self.dna_set_text(normalized)
        self.dna_status.set(f"Copied valid DNA to clipboard. Hash {dna_hash(normalized)}.")

    def dna_save_to_branch(self) -> None:
        text = self.dna_current_text()
        name = f"caseoh90000_dna_{dna_hash(text)}.txt"
        try:
            out = write_dna_file(self.branch, text, name)
            shown = out.name if bool(self.settings.get("streamer_privacy", True)) and not bool(self.settings.get("show_file_paths", False)) else str(out)
            self.dna_status.set(f"Saved DNA file: {shown}")
            messagebox.showinfo("Save DNA", f"Saved DNA file:\n{shown}")
        except Exception as e:
            messagebox.showerror("Save DNA", str(e))

    def dna_load_file(self) -> None:
        path = filedialog.askopenfilename(title="Load Horsey DNA text", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8")
            ok, msg, genome = normalize_dna(text)
            if not ok:
                messagebox.showwarning("Load DNA", msg)
                return
            normalized = format_dna(genome)
            self.dna_genome_cache = genome
            self.dna_set_text(normalized)
            self.dna_refresh_controls()
            self.dna_status.set(f"Loaded DNA file. Hash {dna_hash(normalized)}.")
        except Exception as e:
            messagebox.showerror("Load DNA", str(e))

    def dna_load_exploding_seed(self) -> None:
        text = load_exploding_seed()
        ok, msg, genome = normalize_dna(text)
        if not ok:
            messagebox.showerror("Exploding seed", msg)
            return
        normalized = format_dna(genome)
        self.dna_genome_cache = genome
        self.dna_set_text(normalized)
        self.dna_refresh_controls()
        self.dna_status.set(f"Loaded exploding finisher seed DNA. Hash {dna_hash(normalized)}.")

    def dna_clear_blank(self) -> None:
        genome = blank_genome("A")
        text = format_dna(genome)
        self.dna_genome_cache = genome
        self.dna_set_text(text)
        self.dna_refresh_controls()
        self.dna_status.set("Cleared DNA editor to A/A on every helix position.")

    def copy_exploding_seed(self) -> None:
        try:
            write_exploding_seed_files(self.branch)
            ok = copy_seed_to_clipboard()
            msg = "Exploding seed DNA written to the branch seed folder"
            if ok:
                msg += " and copied to clipboard."
            else:
                msg += ". Clipboard copy was unavailable."
            self.status.set(msg)
            messagebox.showinfo("Exploding seed DNA", msg)
        except Exception as e:
            messagebox.showerror("Exploding seed DNA", str(e))

    def _build_search(self, root: tk.Widget) -> None:
        self.vars["enable_search_controls"] = tk.BooleanVar(value=bool(self.settings.get("enable_search_controls", True)))
        box = ttk.LabelFrame(root, text="Experimental master switch", padding=8)
        box.pack(fill="x", padx=4, pady=6)
        ttk.Checkbutton(box, text="Enable experimental search-control patching", variable=self.vars["enable_search_controls"]).pack(anchor="w")
        self._add_desc(box, "enable_search_controls")
        ttk.Label(box, text="When this is OFF, patching restores SIM9000's normal search values. This is the recommended baseline.", wraplength=680, foreground="#333333").pack(anchor="w", pady=(4, 0))

        columns = ttk.Frame(root)
        columns.pack(fill="x")
        left = ttk.Frame(columns)
        right = ttk.Frame(columns)
        left.pack(side="left", fill="both", expand=True)
        right.pack(side="left", fill="both", expand=True)
        self._add_scale(left, "initial_generation_limit", "Generations per SIM9000 run", 1, 256, wraplength=390)
        self._add_scale(right, "initial_genepool_size", "Gene-pool / race slots", 4, 512, wraplength=390)
        self._add_scale(left, "sim_work_per_ui_update", "SIM work batches per UI update", 30, 3000, wraplength=390)
        self._add_scale(right, "elite_parent_percent", "Elite parent / diversity percent", 1, 100, wraplength=390)
        self._add_scale(left, "min_generation_for_disk", "Earliest generation for result disk", 0, 127, wraplength=390)
        ttk.Label(
            root,
            text="Apply updates the running SIM when it can find the active SIM9000 state. R and G counters use the live SIM values, so changing race slots or generations should be visible without restarting Horsey.",
            wraplength=680,
            foreground="#333333",
        ).pack(anchor="w", padx=8, pady=(4, 8))

        presets = ttk.LabelFrame(root, text="Experimental presets", padding=8)
        presets.pack(fill="x", padx=4, pady=5)
        ttk.Button(presets, text="Normal search", command=self.preset_stock_search).pack(side="left", padx=3)
        ttk.Button(presets, text="Faster UI only", command=self.preset_faster_ui).pack(side="left", padx=3)
        ttk.Button(presets, text="Careful deeper search", command=self.preset_careful_deeper).pack(side="left", padx=3)
        ttk.Label(presets, text="Avoid very early disk output and huge valid-result cutoffs; those can output slow DNA.", wraplength=680).pack(anchor="w", pady=(8, 0))

    def _build_advanced(self, root: tk.Widget) -> None:
        ttk.Label(root, text="Leave these stock unless testing a specific hypothesis. They can change reported units or scoring in confusing ways.", wraplength=680).pack(anchor="w", padx=4, pady=6)
        for key, label in [
            ("finish_metric_threshold", "Finish metric threshold"),
            ("display_time_divisor", "Displayed T divisor"),
            ("result_score_scale", "Result score scale"),
            ("invalid_score_sentinel", "Invalid/cull score sentinel"),
        ]:
            frame = ttk.LabelFrame(root, text=label, padding=8)
            frame.pack(fill="x", padx=4, pady=5)
            self.vars[key] = tk.DoubleVar(value=float(self.settings.get(key, 0.0)))
            ttk.Entry(frame, textvariable=self.vars[key], width=12).pack(anchor="w")
            self._add_desc(frame, key)

    def _collect(self) -> Dict[str, Any]:
        s = dict(self.settings)
        for key, var in self.vars.items():
            try:
                s[key] = var.get()
            except Exception:
                pass
        for key in CORE_KEYS + SEARCH_KEYS + ["display_precision"]:
            if key in s:
                s[key] = int(s[key])
        if "initial_genepool_size" in s:
            s["initial_genepool_size"] = max(4, (int(s["initial_genepool_size"]) // 4) * 4)
        for key in ADVANCED_FLOAT_KEYS:
            if key in s:
                s[key] = float(s[key])
        s["always_accept_early_finish"] = False
        s["enable_search_controls"] = bool(s.get("enable_search_controls"))
        s["caseoh_mode"] = bool(s.get("caseoh_mode", False))
        s["gene_lab_enabled"] = bool(s.get("gene_lab_enabled", False))
        s["exploding_mode"] = bool(s.get("exploding_mode", False))
        if s.get("exploding_mode"):
            s["gene_lab_enabled"] = True
            s["species_profile"] = "Freak / mixed"
            s["racing_preset"] = "Exploding finisher"
        if s.get("caseoh_mode"):
            # Easter egg mode is deliberately not stackable with the Gene Lab or experimental search controls.
            s = normalize_settings(self.profile, s)
        if s.get("species_profile") not in SPECIES_PROFILES:
            s["species_profile"] = "Any / no species lock"
        if s.get("racing_preset") not in RACING_PRESETS:
            s["racing_preset"] = "None / normal genes"
        if hasattr(self, "helix_vars"):
            hp = {}
            for h, var in self.helix_vars.items():
                v = var.get()
                hp[h] = v if v in HELIX_PRESETS else "Unchanged"
            s["helix_presets"] = hp
        s["streamer_privacy"] = bool(s.get("streamer_privacy", True))
        s["show_file_paths"] = bool(s.get("show_file_paths", False))
        s["window_topmost"] = bool(getattr(self, "topmost_var", tk.BooleanVar(value=False)).get())
        s["window_follow"] = False
        s["window_auto_layout"] = False
        # If the exploding finisher is selected, it is an anything-goes mode and
        # should also force the SIM settings that only keep very early finishes.
        s = apply_exploding_sim_overrides(s)
        if hasattr(self, "dna_text"):
            s["dna_editor_text"] = self.dna_current_text()
        if hasattr(self, "dna_preset_var"):
            preset = str(self.dna_preset_var.get())
            s["dna_preset"] = preset if preset in DIRECT_PRESET_NAMES else "Do not change"
        if hasattr(self, "dna_strand_var"):
            strand = str(self.dna_strand_var.get())
            s["dna_preset_strands"] = strand if strand in {"both", "top", "bottom"} else "both"
        s["dna_output_locks"] = normalize_dna_locks(getattr(self, "dna_output_locks", {}))
        if hasattr(self, "tab_order"):
            s["tab_order"] = self._current_tab_order()
        # Advanced float controls are intentionally hidden in HorseyGameCaseOhMod v2; keep those values pinned to scanned originals.
        for key in ADVANCED_FLOAT_KEYS:
            if key in self.profile.get("patches", {}):
                s[key] = float(self.profile["patches"][key]["original"])
        return s

    def _update_labels(self) -> None:
        for widget in self.scale_widgets:
            key = widget.key  # type: ignore[attr-defined]
            val = int(self.vars[key].get())
            if key in {"min_finish_frames", "no_progress_frames", "max_sim_frames"}:
                text = f"{val} frames / {val / 60.0:.3f}s"
            elif key == "valid_result_max":
                text = f"{val} score cutoff"
            elif key == "initial_generation_limit":
                text = f"{val} generations"
            elif key == "initial_genepool_size":
                val = max(4, (val // 4) * 4)
                text = f"{val} horses / {val // 4} race slots"
            elif key == "sim_work_per_ui_update":
                text = f"{val} batches/update"
            elif key == "elite_parent_percent":
                text = f"{val}%"
            elif key == "min_generation_for_disk":
                text = f"generation {val}"
            else:
                text = str(val)
            widget.value_label.configure(text=text)  # type: ignore[attr-defined]

    def _set_original_search(self) -> None:
        for key in SEARCH_KEYS:
            if key in self.vars and key in self.profile.get("patches", {}):
                self.vars[key].set(int(self.profile["patches"][key]["original"]))

    def preset_gene_lab(self, species: str, racing: str) -> None:
        if "gene_lab_enabled" in self.vars:
            self.vars["gene_lab_enabled"].set(True)
        if "species_profile" in self.vars:
            self.vars["species_profile"].set(species)
        if "racing_preset" in self.vars:
            self.vars["racing_preset"].set(racing)
        for var in getattr(self, "helix_vars", {}).values():
            var.set("Unchanged")
        self.status.set(f"Loaded Gene Lab preset: {species} + {racing}. Save to branch files, then restart Horsey.")

    def clear_gene_lab(self) -> None:
        if "gene_lab_enabled" in self.vars:
            self.vars["gene_lab_enabled"].set(False)
        if "species_profile" in self.vars:
            self.vars["species_profile"].set("Any / no species lock")
        if "racing_preset" in self.vars:
            self.vars["racing_preset"].set("None / normal genes")
        for var in getattr(self, "helix_vars", {}).values():
            var.set("Unchanged")
        self.status.set("Gene Lab cleared. Save to branch files to restore normal genes.xml unless the Easter Egg is enabled.")

    def show_gene_lab_report(self) -> None:
        report = self.branch / "sim_gene_lab_report.json"
        if not report.exists():
            messagebox.showinfo("Gene Lab report", "No Gene Lab report exists yet. Save to branch files first.")
            return
        text = report.read_text(encoding="utf-8", errors="replace")[:6000]
        messagebox.showinfo("Gene Lab report", text)

    def restore_gene_lab_now(self) -> None:
        try:
            result = restore_gene_xml(self.branch)
            self.status.set("Restored branch genes.xml from backup. Restart Horsey for this to load.")
            messagebox.showinfo("Restore stock genes.xml", json.dumps(result, indent=2))
        except Exception as e:
            messagebox.showerror("Restore failed", str(e))

    def preset_baseline(self) -> None:
        self.vars["min_finish_frames"].set(0)
        self.vars["display_precision"].set(3)
        self.vars["enable_search_controls"].set(False)
        if "caseoh_mode" in self.vars:
            self.vars["caseoh_mode"].set(False)
        for key in ["no_progress_frames", "max_sim_frames", "valid_result_max"]:
            self.vars[key].set(int(self.profile["patches"][key]["original"]))
        self._set_original_search()
        for key in ADVANCED_FLOAT_KEYS:
            if key in self.vars and key in self.profile.get("patches", {}):
                self.vars[key].set(float(self.profile["patches"][key]["original"]))
        self._update_labels()
        self.status.set("Loaded baseline: uncapped 5.0 barrier, 3-decimal display, normal search/scoring. Apply live or save to branch files.")

    def preset_reject_slow(self) -> None:
        self.preset_baseline()
        self.vars["no_progress_frames"].set(180)
        self.vars["max_sim_frames"].set(3600)
        self._update_labels()
        self.status.set("Loaded slow-winner filter: normal search, but stricter stall/max-time limits. Use only if you see huge T winners.")

    def preset_stock_search(self) -> None:
        self.vars["enable_search_controls"].set(False)
        self._set_original_search()
        self._update_labels()
        self.status.set("Experimental search controls disabled. Patching will restore stock/original search bytes.")

    def preset_faster_ui(self) -> None:
        self.vars["enable_search_controls"].set(True)
        self._set_original_search()
        if "sim_work_per_ui_update" in self.vars:
            self.vars["sim_work_per_ui_update"].set(600)
        self._update_labels()
        self.status.set("Faster UI-only preset loaded. It should mainly affect how fast the sim screen advances, not scoring. Use Apply to running game.")

    def preset_careful_deeper(self) -> None:
        self.vars["enable_search_controls"].set(True)
        self.vars["initial_generation_limit"].set(32)
        self.vars["initial_genepool_size"].set(80)
        self.vars["sim_work_per_ui_update"].set(600)
        self.vars["elite_parent_percent"].set(int(self.profile.get("patches", {}).get("elite_parent_percent", {}).get("original", 25)))
        self.vars["min_generation_for_disk"].set(int(self.profile.get("patches", {}).get("min_generation_for_disk", {}).get("original", 9)))
        self._update_labels()
        self.status.set("Careful deeper search loaded. It keeps disk generation at stock and does not loosen valid-result scoring.")

    def patch_disk(self) -> None:
        try:
            self.settings = patch_exe_file(self.branch, self.profile, self._collect())
            verify_msg = branch_patch_verification(self.branch, self.profile, self.settings)
            if is_exploding_requested(self.settings):
                write_exploding_seed_files(self.branch)
                copy_seed_to_clipboard()
                self.status.set("Patched branch EXE on disk. Exploding seed DNA was written/copied. Restart the mod branch before testing." + verify_msg)
            else:
                self.status.set("Patched branch EXE on disk. Restart the mod branch for disk changes to take effect." + verify_msg)
        except Exception as e:
            messagebox.showerror("Patch failed", str(e))

    def patch_live(self) -> None:
        if self._live_patch_running:
            self.status.set("Apply is already working. It will unlock as soon as the current update finishes.")
            return
        self._live_patch_running = True
        if self.live_apply_button is not None:
            self.live_apply_button.configure(state="disabled", text="Applying...")
        try:
            previous_settings = dict(self.settings)
            self.settings = self._collect()
            msg = patch_running_process(self.profile, self.settings, self.horsey_exe, previous_settings)
            # Match file behavior: when experimental is disabled, store stock search values.
            if not self.settings.get("enable_search_controls"):
                for key in SEARCH_KEYS:
                    self.settings[key] = int(original(self.profile, key, self.settings.get(key, 0)))
            apply_gene_stack(self.branch, self.settings)
            write_settings(self.branch, self.settings)
            if is_exploding_requested(self.settings):
                write_exploding_seed_files(self.branch)
                copy_seed_to_clipboard()
                msg += "\nExploding finisher active: fast-finish SIM settings applied, seed DNA written/copied, and Gene Lab changes were written. Restart Horsey before testing this preset."
            elif self.settings.get("gene_lab_enabled") or self.settings.get("caseoh_mode"):
                msg += "\nGene Lab changes were written to genes.xml; restart Horsey for those to load. If the Easter Egg is checked, it overrides other profile/search settings."
            else:
                msg += "\nGene Lab disabled; branch genes.xml restored to stock unless the Easter Egg is enabled."
            try:
                apply_caseoh_art(self.branch)
                msg += "\nCaseOh90000 garage art is ready; restart Horsey if the garage sign is not visible yet."
            except Exception as art_error:
                msg += f"\nGarage art could not be refreshed: {art_error}"
            self.status.set(msg)
        except Exception as e:
            messagebox.showerror("Live patch failed", str(e))
        finally:
            self._live_patch_running = False
            if self.live_apply_button is not None:
                self.live_apply_button.configure(state="normal", text="Apply to running game")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--branch", default=None)
    args = ap.parse_args()
    try:
        app = OverlayApp(Path(args.branch or configured_default_branch()))
        app.mainloop()
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
