#!/usr/bin/env python3
"""
CaseOh90000 v1.0 panel.

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
from tkinter import messagebox, ttk
from typing import Any, Dict, List, Tuple

from caseoh import apply_caseoh_mode


DEFAULT_BRANCH = str(Path.home() / "Desktop" / "projects" / "CaseOh90000_BRANCH")


def configured_default_branch() -> str:
    cfg_path = Path(__file__).with_name("CaseOh90000_paths.json")
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
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
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
PAGE_EXECUTE_READWRITE = 0x40
PAGE_READWRITE = 0x04

CORE_KEYS = ["min_finish_frames", "no_progress_frames", "max_sim_frames", "valid_result_max"]
SEARCH_I32 = ["initial_generation_limit", "initial_genepool_size", "sim_work_per_ui_update"]
SEARCH_U8 = ["elite_parent_percent", "min_generation_for_disk"]
SEARCH_KEYS = SEARCH_I32 + SEARCH_U8
ADVANCED_FLOAT_KEYS = ["finish_metric_threshold", "display_time_divisor", "result_score_scale", "invalid_score_sentinel"]

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
        "Raising it mostly lets slow horses finish; it does not make fast horses faster."
    ),
    "valid_result_max": (
        "A broad internal cutoff for what SIM9000 is allowed to keep. The original value is usually best. "
        "If this is too loose, slow or strange results can slip through."
    ),
    "display_precision": (
        "How many decimals the T readout shows. Three decimals makes close results easier to compare."
    ),
    "caseoh_mode": "Easter Egg",
    "enable_search_controls": (
        "Lets you experiment with SIM9000's search loop. Leave this off for the proven baseline behavior."
    ),
    "initial_generation_limit": (
        "How many generations SIM9000 runs during its internal search. More is not always better, so treat this as experimental."
    ),
    "initial_genepool_size": (
        "How many horses SIM9000 starts with. Bigger pools explore more DNA but use more work. Multiples of 4 are safest."
    ),
    "sim_work_per_ui_update": (
        "How much SIM9000 work happens between screen refreshes. Higher values can make the sim finish sooner on screen, "
        "but the window may look frozen while it crunches."
    ),
    "elite_parent_percent": (
        "How much of the better population gets to parent the next generation. Lower is greedier; higher keeps more variety."
    ),
    "min_generation_for_disk": (
        "The earliest generation that can produce a result disk. Setting this too low can output weak DNA before the search improves."
    ),
    "hotkey": (
        "Optional hide/show shortcut. If Windows will not bind it on your machine, the Hide panel button does the same job."
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
    Module32FirstW = kernel32.Module32FirstW
    Module32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
    Module32FirstW.restype = wintypes.BOOL
    Module32NextW = kernel32.Module32NextW
    Module32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
    Module32NextW.restype = wintypes.BOOL
    OpenProcess = kernel32.OpenProcess
    OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    OpenProcess.restype = wintypes.HANDLE
    WriteProcessMemory = kernel32.WriteProcessMemory
    WriteProcessMemory.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.LPCVOID, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    WriteProcessMemory.restype = wintypes.BOOL
    VirtualProtectEx = kernel32.VirtualProtectEx
    VirtualProtectEx.argtypes = [wintypes.HANDLE, wintypes.LPVOID, ctypes.c_size_t, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    VirtualProtectEx.restype = wintypes.BOOL
    CloseHandle = kernel32.CloseHandle
    CloseHandle.argtypes = [wintypes.HANDLE]
    CloseHandle.restype = wintypes.BOOL
else:
    kernel32 = None


def find_horsey_process() -> Tuple[int, int, str]:
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
    pid = candidates[0]
    msnap = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    if msnap == INVALID_HANDLE_VALUE:
        raise RuntimeError(f"CreateToolhelp32Snapshot module failed for pid {pid}: {last_error()}")
    try:
        me = MODULEENTRY32W(); me.dwSize = ctypes.sizeof(me)
        ok = Module32FirstW(msnap, ctypes.byref(me))
        while ok:
            if me.szModule.lower() == "horsey.exe":
                base = ctypes.cast(me.modBaseAddr, ctypes.c_void_p).value
                return pid, int(base), me.szExePath
            ok = Module32NextW(msnap, ctypes.byref(me))
    finally:
        CloseHandle(msnap)
    raise RuntimeError(f"Horsey.exe process {pid} found, but module base was not found")


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


def read_profile(branch: Path) -> Dict[str, Any]:
    p = branch / "sim9000_mod_profile.json"
    if not p.exists():
        raise FileNotFoundError(f"Missing {p}. Run 01_CREATE_OR_UPDATE_BRANCH.bat first.")
    return json.loads(p.read_text(encoding="utf-8"))



# Optional window docking helpers. They only run on Windows and only move this
# control panel, never the Horsey game window.
class RECT(ctypes.Structure):
    _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG), ("right", wintypes.LONG), ("bottom", wintypes.LONG)]


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", POINT),
    ]


WM_HOTKEY = 0x0312
PM_REMOVE = 0x0001
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
HOTKEY_KEYS = ["F6", "F7", "F8", "F9", "F10", "F11", "F12", "G", "H", "J", "K", "Home", "End", "PageUp", "PageDown"]
VK_BY_NAME = {
    "Home": 0x24,
    "End": 0x23,
    "PageUp": 0x21,
    "PageDown": 0x22,
}


def vk_from_key_name(name: str) -> int:
    key = str(name).strip()
    if len(key) == 1 and key.upper() in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
        return ord(key.upper())
    if key.upper().startswith("F") and key[1:].isdigit():
        n = int(key[1:])
        if 1 <= n <= 24:
            return 0x70 + n - 1
    if key in VK_BY_NAME:
        return VK_BY_NAME[key]
    raise ValueError(f"Unsupported hotkey key: {name!r}")

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
    RegisterHotKey = user32.RegisterHotKey
    RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
    RegisterHotKey.restype = wintypes.BOOL
    UnregisterHotKey = user32.UnregisterHotKey
    UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
    UnregisterHotKey.restype = wintypes.BOOL
    PeekMessageW = user32.PeekMessageW
    PeekMessageW.argtypes = [ctypes.POINTER(MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT]
    PeekMessageW.restype = wintypes.BOOL
else:
    user32 = None


def find_horsey_window_rect() -> Tuple[int, int, int, int] | None:
    """Return the main visible Horsey.exe window rectangle if available."""
    if os.name != "nt":
        return None
    try:
        pid, _, _ = find_horsey_process()
    except Exception:
        return None
    found: List[Tuple[int, int, int, int]] = []

    def _cb(hwnd: int, _lparam: int) -> bool:
        if not IsWindowVisible(hwnd):
            return True
        proc = wintypes.DWORD(0)
        GetWindowThreadProcessId(hwnd, ctypes.byref(proc))
        if int(proc.value) == int(pid):
            r = RECT()
            if GetWindowRect(hwnd, ctypes.byref(r)):
                if (r.right - r.left) > 100 and (r.bottom - r.top) > 100:
                    found.append((int(r.left), int(r.top), int(r.right), int(r.bottom)))
        return True

    EnumWindows(EnumWindowsProc(_cb), 0)
    return found[0] if found else None

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
        "enable_search_controls": False,
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
        # UI preferences, stored with the branch settings. These do not patch the game.
        "hotkey_enabled": True,
        "hotkey_ctrl": True,
        "hotkey_alt": True,
        "hotkey_shift": False,
        "hotkey_win": False,
        "hotkey_key": "G",
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
    s["enable_search_controls"] = bool(s.get("enable_search_controls"))
    s["caseoh_mode"] = bool(s.get("caseoh_mode", False))
    s["initial_generation_limit"] = max(1, int(s.get("initial_generation_limit", original(profile, "initial_generation_limit", 16))))
    gp = max(4, int(s.get("initial_genepool_size", original(profile, "initial_genepool_size", 40))))
    s["initial_genepool_size"] = max(4, (gp // 4) * 4)
    s["sim_work_per_ui_update"] = max(1, int(s.get("sim_work_per_ui_update", original(profile, "sim_work_per_ui_update", 240))))
    s["elite_parent_percent"] = max(1, min(100, int(s.get("elite_parent_percent", original(profile, "elite_parent_percent", 25)))))
    s["min_generation_for_disk"] = max(0, min(127, int(s.get("min_generation_for_disk", original(profile, "min_generation_for_disk", 9)))))
    for key in ADVANCED_FLOAT_KEYS:
        if key in s:
            s[key] = float(s[key])
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
    for key in SEARCH_U8:
        add_u8(key, search_values[key])
    for key in ADVANCED_FLOAT_KEYS:
        if key in s:
            add_f32(key, s[key])
    return out


def patch_exe_file(branch: Path, profile: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
    exe = branch / "Horsey.exe"
    data = bytearray(exe.read_bytes())
    for key, payload in patch_payloads(profile, settings):
        if key not in profile["patches"]:
            continue
        off = int(profile["patches"][key]["file_off"])
        data[off:off + len(payload)] = payload
    exe.write_bytes(data)
    settings = normalize_settings(profile, settings)
    if not settings.get("enable_search_controls"):
        for key in SEARCH_KEYS:
            settings[key] = int(original(profile, key, settings.get(key, 0)))
    apply_caseoh_mode(branch, bool(settings.get("caseoh_mode", False)))
    write_settings(branch, settings)
    return settings



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
    apply_caseoh_mode(branch, bool(s.get("caseoh_mode", False)))
    write_settings(branch, s)
    return s

def patch_running_process(profile: Dict[str, Any], settings: Dict[str, Any]) -> str:
    pid, base, path = find_horsey_process()
    for key, payload in patch_payloads(profile, settings):
        if key not in profile["patches"]:
            continue
        addr = base + int(profile["patches"][key]["rva"])
        write_process(pid, addr, payload)
    return f"Patched running Horsey.exe pid={pid}, base={base:#x}\n{path}"


class Scrollable(ttk.Frame):
    def __init__(self, parent: tk.Widget):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        ybar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.frame = ttk.Frame(self.canvas)
        self.frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.frame, anchor="nw")
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
        self.profile = read_profile(branch)
        self.settings = read_settings(branch, self.profile)
        self.vars: Dict[str, Any] = {}
        self.scale_widgets: List[Any] = []
        self.scrollables: List[Scrollable] = []
        self.hotkey_id = 0x4847
        self.hotkey_registered = False
        self.title("CaseOh90000")
        self.geometry("640x780")
        self.topmost_var = tk.BooleanVar(value=False)
        self.follow_var = tk.BooleanVar(value=False)
        self.attributes("-topmost", False)
        self.resizable(True, True)
        self._build_ui()
        self._update_labels()
        self._bind_mousewheel()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self._startup_dock_attempts = 0
        self.after(700, self._startup_dock_retry)
        self.after(500, self.register_hotkey_from_ui)
        self.after(120, self._poll_hotkey)

    def _startup_dock_retry(self) -> None:
        if find_horsey_window_rect() is not None:
            self.dock_next_to_horsey()
            return
        self._startup_dock_attempts += 1
        if self._startup_dock_attempts < 12:
            self.after(900, self._startup_dock_retry)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=10)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="CaseOh90000", font=("Segoe UI", 15, "bold")).pack(anchor="w")
        ttk.Label(outer, text="A small control panel for the copied CaseOh90000 branch. Make horses in the branch, then copy any genome you like back into your normal game by hand.", wraplength=600).pack(anchor="w", pady=(2, 4))
        ttk.Label(outer, text=f"Branch: {self.branch}", wraplength=600).pack(anchor="w", pady=(0, 8))
        self.status = tk.StringVar(value="Ready. Patch running game for immediate changes. Patch disk + restart for changes that load at startup.")
        ttk.Label(outer, textvariable=self.status, wraplength=600).pack(anchor="w", pady=(0, 8))

        window_row = ttk.Frame(outer)
        window_row.pack(fill="x", pady=(0, 8))
        ttk.Button(window_row, text="Dock beside Horsey", command=self.dock_next_to_horsey).pack(side="left", padx=(0, 6))
        ttk.Checkbutton(window_row, text="Stay on top", variable=self.topmost_var, command=self.toggle_topmost).pack(side="left", padx=(0, 6))
        ttk.Checkbutton(window_row, text="Follow Horsey", variable=self.follow_var, command=self._maybe_follow).pack(side="left", padx=(0, 6))
        ttk.Button(window_row, text="Hide panel", command=self.toggle_panel_visibility).pack(side="left")

        self._build_hotkey_box(outer)

        nb = ttk.Notebook(outer)
        nb.pack(fill="both", expand=True)
        self.core_tab = Scrollable(nb); nb.add(self.core_tab, text="Main")
        self.search_tab = Scrollable(nb); nb.add(self.search_tab, text="Experiments")
        self.scrollables = [self.core_tab, self.search_tab]

        self._build_core(self.core_tab.frame)
        self._build_search(self.search_tab.frame)

        btns = ttk.Frame(outer)
        btns.pack(fill="x", pady=8)
        ttk.Button(btns, text="Apply to running game", command=self.patch_live).pack(side="left", padx=3)
        ttk.Button(btns, text="Save to branch files", command=self.patch_disk).pack(side="left", padx=3)
        ttk.Button(btns, text="Load baseline", command=self.preset_baseline).pack(side="left", padx=3)
        ttk.Button(btns, text="Restore normal search", command=self.preset_stock_search).pack(side="left", padx=3)

    def _build_hotkey_box(self, parent: tk.Widget) -> None:
        hot = ttk.LabelFrame(parent, text="Optional keyboard shortcut", padding=8)
        hot.pack(fill="x", pady=(0, 8))
        row = ttk.Frame(hot)
        row.pack(fill="x")
        self.vars["hotkey_enabled"] = tk.BooleanVar(value=bool(self.settings.get("hotkey_enabled", True)))
        self.vars["hotkey_ctrl"] = tk.BooleanVar(value=bool(self.settings.get("hotkey_ctrl", True)))
        self.vars["hotkey_alt"] = tk.BooleanVar(value=bool(self.settings.get("hotkey_alt", True)))
        self.vars["hotkey_shift"] = tk.BooleanVar(value=bool(self.settings.get("hotkey_shift", False)))
        self.vars["hotkey_win"] = tk.BooleanVar(value=bool(self.settings.get("hotkey_win", False)))
        self.vars["hotkey_key"] = tk.StringVar(value=str(self.settings.get("hotkey_key", "G")))
        ttk.Checkbutton(row, text="Enable", variable=self.vars["hotkey_enabled"]).pack(side="left", padx=(0, 8))
        ttk.Checkbutton(row, text="Ctrl", variable=self.vars["hotkey_ctrl"]).pack(side="left")
        ttk.Checkbutton(row, text="Alt", variable=self.vars["hotkey_alt"]).pack(side="left")
        ttk.Checkbutton(row, text="Shift", variable=self.vars["hotkey_shift"]).pack(side="left")
        ttk.Checkbutton(row, text="Win", variable=self.vars["hotkey_win"]).pack(side="left", padx=(0, 8))
        ttk.OptionMenu(row, self.vars["hotkey_key"], self.vars["hotkey_key"].get(), *HOTKEY_KEYS).pack(side="left", padx=(0, 8))
        ttk.Button(row, text="Bind / update", command=self.register_hotkey_from_ui).pack(side="left", padx=(0, 6))
        ttk.Button(row, text="Test toggle", command=self.toggle_panel_visibility).pack(side="left")
        ttk.Label(hot, text=DESCRIPTIONS["hotkey"], wraplength=600, foreground="#333333").pack(anchor="w", pady=(6, 0))

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

    def _hotkey_modifiers(self) -> int:
        mods = MOD_NOREPEAT
        if bool(self.vars.get("hotkey_ctrl", tk.BooleanVar(value=False)).get()):
            mods |= MOD_CONTROL
        if bool(self.vars.get("hotkey_alt", tk.BooleanVar(value=False)).get()):
            mods |= MOD_ALT
        if bool(self.vars.get("hotkey_shift", tk.BooleanVar(value=False)).get()):
            mods |= MOD_SHIFT
        if bool(self.vars.get("hotkey_win", tk.BooleanVar(value=False)).get()):
            mods |= MOD_WIN
        return mods

    def unregister_hotkey(self) -> None:
        if os.name == "nt" and self.hotkey_registered:
            try:
                UnregisterHotKey(None, self.hotkey_id)
            except Exception:
                pass
        self.hotkey_registered = False

    def register_hotkey_from_ui(self) -> None:
        self.unregister_hotkey()
        self.settings = self._collect()
        write_settings(self.branch, self.settings)
        if not bool(self.vars.get("hotkey_enabled", tk.BooleanVar(value=False)).get()):
            self.status.set("Optional keyboard shortcut disabled. Settings saved.")
            return
        if os.name != "nt":
            self.status.set("Global hotkeys are only available on Windows. The panel still works normally.")
            return
        try:
            key_name = str(self.vars["hotkey_key"].get())
            vk = vk_from_key_name(key_name)
            mods = self._hotkey_modifiers()
            if not RegisterHotKey(None, self.hotkey_id, mods, vk):
                self.status.set(f"Could not bind {self._hotkey_label()}. You can still use the Hide panel button.")
                return
            self.hotkey_registered = True
            self.status.set(f"Optional keyboard shortcut active: {self._hotkey_label()}. Press it to hide/show the CaseOh90000 panel.")
        except Exception as e:
            self.status.set(f"Could not bind hotkey: {e}")

    def _hotkey_label(self) -> str:
        parts: List[str] = []
        if bool(self.vars.get("hotkey_ctrl", tk.BooleanVar(value=False)).get()):
            parts.append("Ctrl")
        if bool(self.vars.get("hotkey_alt", tk.BooleanVar(value=False)).get()):
            parts.append("Alt")
        if bool(self.vars.get("hotkey_shift", tk.BooleanVar(value=False)).get()):
            parts.append("Shift")
        if bool(self.vars.get("hotkey_win", tk.BooleanVar(value=False)).get()):
            parts.append("Win")
        parts.append(str(self.vars.get("hotkey_key", tk.StringVar(value="G")).get()))
        return "+".join(parts)

    def _poll_hotkey(self) -> None:
        if os.name == "nt" and self.hotkey_registered:
            msg = MSG()
            try:
                while PeekMessageW(ctypes.byref(msg), None, WM_HOTKEY, WM_HOTKEY, PM_REMOVE):
                    if int(msg.wParam) == int(self.hotkey_id):
                        self.toggle_panel_visibility()
            except Exception:
                pass
        self.after(120, self._poll_hotkey)

    def toggle_panel_visibility(self) -> None:
        if self.state() == "iconic":
            self.deiconify()
            if bool(getattr(self, "follow_var", tk.BooleanVar(value=False)).get()):
                self.dock_next_to_horsey()
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
        self.unregister_hotkey()
        self.destroy()

    def toggle_topmost(self) -> None:
        self.attributes("-topmost", bool(self.topmost_var.get()))

    def dock_next_to_horsey(self) -> None:
        rect = find_horsey_window_rect()
        if rect is None:
            self.status.set("Horsey window not found yet. Start the mod branch, then press 'Dock beside Horsey'.")
            return
        left, top, right, bottom = rect
        self.update_idletasks()
        panel_w = max(520, self.winfo_width())
        panel_h = max(620, self.winfo_height())
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = right + 10
        if x + panel_w > screen_w:
            x = max(0, left - panel_w - 10)
        y = max(0, min(top, screen_h - panel_h - 40))
        self.geometry(f"{panel_w}x{panel_h}+{x}+{y}")
        self.status.set("Docked beside Horsey. This panel is not always-on-top unless you enable it.")
        self._maybe_follow()

    def _maybe_follow(self) -> None:
        if bool(getattr(self, "follow_var", tk.BooleanVar(value=False)).get()):
            rect = find_horsey_window_rect()
            if rect is not None:
                left, top, right, bottom = rect
                self.update_idletasks()
                panel_w = max(520, self.winfo_width())
                panel_h = max(620, self.winfo_height())
                screen_w = self.winfo_screenwidth()
                screen_h = self.winfo_screenheight()
                x = right + 10
                if x + panel_w > screen_w:
                    x = max(0, left - panel_w - 10)
                y = max(0, min(top, screen_h - panel_h - 40))
                self.geometry(f"{panel_w}x{panel_h}+{x}+{y}")
            self.after(1200, self._maybe_follow)

    def _add_desc(self, parent: tk.Widget, key: str) -> None:
        ttk.Label(parent, text=DESCRIPTIONS.get(key, ""), wraplength=680, foreground="#333333").pack(anchor="w", pady=(2, 2))

    def _add_scale(self, parent: tk.Widget, key: str, label: str, lo: int, hi: int) -> None:
        var = tk.IntVar(value=int(self.settings.get(key, lo)))
        self.vars[key] = var
        box = ttk.LabelFrame(parent, text=label, padding=8)
        box.pack(fill="x", padx=4, pady=5)
        value = ttk.Label(box, text="")
        value.pack(anchor="w")
        ttk.Scale(box, from_=lo, to=hi, variable=var, orient="horizontal", command=lambda _=None: self._update_labels()).pack(fill="x")
        self._add_desc(box, key)
        box.key = key  # type: ignore[attr-defined]
        box.value_label = value  # type: ignore[attr-defined]
        self.scale_widgets.append(box)

    def _build_core(self, root: tk.Widget) -> None:
        ttk.Label(root, text="Start here. These are the practical SIM9000 settings that matter most. The proven baseline keeps SIM9000's normal search behavior.", wraplength=680).pack(anchor="w", padx=4, pady=6)
        self._add_scale(root, "min_finish_frames", "Minimum accepted finish frames / 5.0 barrier", 0, 600)
        self._add_scale(root, "no_progress_frames", "Stall/no-progress cull frames", 0, 1800)
        self._add_scale(root, "max_sim_frames", "Maximum SIM9000 candidate frame budget", 300, 21600)
        self._add_scale(root, "valid_result_max", "Valid-result score max", 1000, 30000)

        precision = ttk.LabelFrame(root, text="Display precision", padding=8)
        precision.pack(fill="x", padx=4, pady=5)
        self.vars["display_precision"] = tk.IntVar(value=int(self.settings.get("display_precision", 3)))
        for text, val in [("T:%.1f — original", 1), ("T:%.2f", 2), ("T:%.3f — recommended", 3)]:
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

    def _build_search(self, root: tk.Widget) -> None:
        self.vars["enable_search_controls"] = tk.BooleanVar(value=bool(self.settings.get("enable_search_controls", False)))
        box = ttk.LabelFrame(root, text="Experimental master switch", padding=8)
        box.pack(fill="x", padx=4, pady=6)
        ttk.Checkbutton(box, text="Enable experimental search-control patching", variable=self.vars["enable_search_controls"]).pack(anchor="w")
        self._add_desc(box, "enable_search_controls")
        ttk.Label(box, text="When this is OFF, patching restores SIM9000's normal search values. This is the recommended baseline.", wraplength=680, foreground="#333333").pack(anchor="w", pady=(4, 0))

        self._add_scale(root, "initial_generation_limit", "Generations per SIM9000 run", 1, 256)
        self._add_scale(root, "initial_genepool_size", "Gene-pool / population size", 4, 512)
        self._add_scale(root, "sim_work_per_ui_update", "SIM work batches per UI update", 30, 3000)
        self._add_scale(root, "elite_parent_percent", "Elite parent / diversity percent", 1, 100)
        self._add_scale(root, "min_generation_for_disk", "Earliest generation for result disk", 0, 127)

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
        # Advanced float controls are intentionally hidden in v1.0; keep those values pinned to scanned originals.
        for key in ADVANCED_FLOAT_KEYS:
            if key in self.profile.get("patches", {}):
                s[key] = float(self.profile["patches"][key]["original"])
        return s

    def _update_labels(self) -> None:
        for widget in self.scale_widgets:
            key = widget.key  # type: ignore[attr-defined]
            val = int(self.vars[key].get())
            if key in {"min_finish_frames", "no_progress_frames", "max_sim_frames"}:
                text = f"{val} frames ≈ {val / 60.0:.3f}s"
            elif key == "valid_result_max":
                text = f"{val} score cutoff"
            elif key == "initial_generation_limit":
                text = f"{val} generations"
            elif key == "initial_genepool_size":
                val = max(4, (val // 4) * 4)
                text = f"{val} horses (rounded to multiple of 4)"
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
        self.status.set("Faster UI-only preset loaded. It should mainly affect how fast the sim screen advances, not scoring. Patch before a fresh SIM run.")

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
            self.status.set("Patched branch EXE on disk. Restart the mod branch for disk changes to take effect.")
        except Exception as e:
            messagebox.showerror("Patch failed", str(e))

    def patch_live(self) -> None:
        try:
            self.settings = self._collect()
            msg = patch_running_process(self.profile, self.settings)
            # Match file behavior: when experimental is disabled, store stock search values.
            if not self.settings.get("enable_search_controls"):
                for key in SEARCH_KEYS:
                    self.settings[key] = int(original(self.profile, key, self.settings.get(key, 0)))
            apply_caseoh_mode(self.branch, bool(self.settings.get("caseoh_mode", False)))
            write_settings(self.branch, self.settings)
            if self.settings.get("caseoh_mode"):
                msg += "\ncaseOh mOde updated on disk; restart Horsey for the Easter Egg to load."
            else:
                msg += "\ncaseOh mOde disabled on disk if a backup existed; restart Horsey for the change to load."
            self.status.set(msg)
        except Exception as e:
            messagebox.showerror("Live patch failed", str(e))


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
