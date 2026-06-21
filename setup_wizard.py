#!/usr/bin/env python3
"""First-run setup and safe launcher for CaseOh90000 v1.0.

The wizard stores user-selected paths in CaseOh90000_paths.json so the BAT files
and the CaseOh90000 panel do not need hardcoded local paths.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

CONFIG_NAME = "CaseOh90000_paths.json"
STEAM_DEFAULT = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Horsey Game")


def tool_dir() -> Path:
    return Path(__file__).resolve().parent


def config_path() -> Path:
    return tool_dir() / CONFIG_NAME


def default_branch() -> Path:
    return tool_dir().parent / "CaseOh90000_BRANCH"


def normalize_user_path(text: str) -> Path:
    text = text.strip().strip('"').strip("'")
    text = os.path.expandvars(os.path.expanduser(text))
    return Path(text)


def prompt_path(label: str, default: Optional[Path], must_have_exe: bool = False) -> Path:
    while True:
        if default:
            raw = input(f"{label}\n[{default}]\n> ").strip()
            p = default if not raw else normalize_user_path(raw)
        else:
            raw = input(f"{label}\n> ").strip()
            p = normalize_user_path(raw)
        if must_have_exe and not (p / "Horsey.exe").exists():
            print(f"\nI could not find Horsey.exe at:\n  {p}\nPick the folder that directly contains Horsey.exe.\n")
            continue
        return p


def load_config(required: bool = True) -> Dict[str, Any]:
    path = config_path()
    if not path.exists():
        if required:
            raise FileNotFoundError(f"No {CONFIG_NAME} found. Run 00_START_HERE_CaseOh90000.bat first.")
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_config(cfg: Dict[str, Any]) -> None:
    cfg = dict(cfg)
    cfg["tool_folder"] = str(tool_dir())
    cfg["updated_at"] = datetime.now().isoformat(timespec="seconds")
    config_path().write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def validate_paths(source: Path, branch: Path) -> None:
    source_r = source.resolve()
    branch_r = branch.resolve()
    if not (source_r / "Horsey.exe").exists():
        raise FileNotFoundError(source_r / "Horsey.exe")
    if source_r == branch_r:
        raise ValueError("The mod branch folder cannot be the same as the normal game folder.")
    try:
        branch_r.relative_to(source_r)
        raise ValueError("Do not put the mod branch inside the normal Horsey Game folder. Pick a Desktop/projects folder instead.")
    except ValueError as e:
        if str(e).startswith("Do not put"):
            raise
    if branch_r.exists() and branch_r.is_file():
        raise ValueError(f"The branch path points to a file, not a folder: {branch_r}")


def run_py(args: list[str]) -> int:
    cmd = [sys.executable, str(tool_dir() / "horseymod.py"), *args]
    print("\n> " + " ".join(f'"{c}"' if " " in c else c for c in cmd))
    return subprocess.call(cmd, cwd=str(tool_dir()))


def make_branch_from_config(overwrite: bool = True) -> int:
    cfg = load_config()
    source = Path(cfg["source"])
    branch = Path(cfg["branch"])
    validate_paths(source, branch)
    args = ["make-branch", "--source", str(source), "--branch", str(branch)]
    if overwrite:
        args.append("--overwrite")
    return run_py(args)


def run_branch_from_config() -> int:
    cfg = load_config()
    branch = Path(cfg["branch"])
    return run_py(["run", "--branch", str(branch)])


def restore_from_config() -> int:
    cfg = load_config()
    branch = Path(cfg["branch"])
    return run_py(["restore", "--branch", str(branch)])


def open_panel_from_config(detached: bool = False) -> int:
    cfg = load_config()
    branch = Path(cfg["branch"])
    cmd = [sys.executable, str(tool_dir() / "CaseOh90000Panel.py"), "--branch", str(branch)]
    print("\n> " + " ".join(f'"{c}"' if " " in c else c for c in cmd))
    if detached:
        subprocess.Popen(cmd, cwd=str(tool_dir()))
        return 0
    return subprocess.call(cmd, cwd=str(tool_dir()))


def open_folder(path: Path) -> int:
    if sys.platform.startswith("win"):
        subprocess.Popen(["explorer", str(path)])
        return 0
    if sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
        return 0
    subprocess.Popen(["xdg-open", str(path)])
    return 0


def ps_quote(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def powershell_single_quote(s: str) -> str:
    """Quote a string for a PowerShell single-quoted literal."""
    return "'" + s.replace("'", "''") + "'"


def windows_desktop_path() -> Path:
    """Return the user's actual Desktop path, including OneDrive Desktop when enabled."""
    if sys.platform.startswith("win"):
        try:
            ps = "[Environment]::GetFolderPath([Environment+SpecialFolder]::Desktop)"
            r = subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                check=True,
                capture_output=True,
                text=True,
            )
            candidate = r.stdout.strip()
            if candidate:
                return Path(candidate)
        except Exception:
            pass
        # Fallbacks for machines where Desktop is redirected but PowerShell is blocked.
        for key in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
            root = os.environ.get(key)
            if root:
                p = Path(root) / "Desktop"
                if p.exists():
                    return p
        return Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
    return Path.home() / "Desktop"


def create_shortcut() -> bool:
    """Create the Desktop launcher reliably, including OneDrive Desktop setups.

    The old version used %USERPROFILE%\\Desktop and sometimes created the link in a
    folder Windows was not actually showing as the Desktop. This version asks Windows
    for the real Desktop location and points the .lnk at cmd.exe with the BAT as an
    argument, which is more reliable than making the BAT itself the target.
    """
    if not sys.platform.startswith("win"):
        print("Desktop .lnk shortcut creation is Windows-only. The BAT file can still be run manually.")
        return False

    cfg = load_config()
    target_bat = tool_dir() / "CaseOh90000_RUN_FROM_LATEST_SAVE.bat"
    icon_source = Path(cfg.get("source", "")) / "Horsey.exe"
    icon = str(icon_source) if icon_source.exists() else str(target_bat)
    description = "Start CaseOh90000 from the latest normal save and open the CaseOh90000 panel"

    ps = f"""
$ErrorActionPreference = 'Stop'
$desktop = [Environment]::GetFolderPath([Environment+SpecialFolder]::Desktop)
if ([string]::IsNullOrWhiteSpace($desktop)) {{ throw 'Could not resolve Desktop folder.' }}
$link = Join-Path $desktop 'CaseOh90000 - Latest Save.lnk'
$w = New-Object -ComObject WScript.Shell
$s = $w.CreateShortcut($link)
$s.TargetPath = $env:ComSpec
$s.Arguments = '/d /c ""{str(target_bat).replace("'", "''")}""'
$s.WorkingDirectory = {powershell_single_quote(str(tool_dir()))}
$s.IconLocation = {powershell_single_quote(icon)}
$s.Description = {powershell_single_quote(description)}
$s.Save()
Write-Output $link
"""
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            check=True,
            capture_output=True,
            text=True,
        )
        link_path = result.stdout.strip() or str(windows_desktop_path() / "CaseOh90000 - Latest Save.lnk")
        print(f"Created desktop shortcut:\n  {link_path}")
        return True
    except Exception as e:
        print(f"Could not create .lnk shortcut: {e}")
        # Fallback: create a visible Desktop BAT launcher in the real Desktop folder.
        desktop = windows_desktop_path()
        desktop.mkdir(parents=True, exist_ok=True)
        fallback = desktop / "CaseOh90000 - Latest Save.bat"
        fallback.write_text(
            f'@echo off\r\ncd /d "{tool_dir()}"\r\ncall "{target_bat}"\r\n',
            encoding="utf-8",
        )
        print(f"Created fallback desktop launcher:\n  {fallback}")
        return False

def cmd_setup(args: argparse.Namespace) -> int:
    print("CaseOh90000 v1.0 — setup wizard")
    print("This does not patch your normal Steam install. It creates a separate mod branch.\n")

    existing = load_config(required=False)
    guessed_source = Path(existing.get("source", "")) if existing.get("source") else (STEAM_DEFAULT if STEAM_DEFAULT.exists() else None)
    guessed_branch = Path(existing.get("branch", "")) if existing.get("branch") else default_branch()

    source = prompt_path("1) Where is Horsey Game installed? Pick the folder that contains Horsey.exe.", guessed_source, must_have_exe=True)
    branch = prompt_path("2) Where should the modded branch live/run from? This folder will be created or rebuilt.", guessed_branch, must_have_exe=False)
    validate_paths(source, branch)

    cfg = {
        "source": str(source.resolve()),
        "branch": str(branch.resolve()),
        "created_at": existing.get("created_at") or datetime.now().isoformat(timespec="seconds"),
    }
    save_config(cfg)
    print(f"\nSaved config:\n  {config_path()}")
    print(f"Normal game folder:\n  {source.resolve()}")
    print(f"Mod branch folder:\n  {branch.resolve()}\n")

    if args.make_shortcut is None:
        answer = input("Create a desktop shortcut that refreshes from the latest normal save and starts the mod? [Y/n]\n> ").strip().lower()
        make_shortcut = answer not in {"n", "no"}
    else:
        make_shortcut = args.make_shortcut
    if args.open_panel is None:
        answer = input("Open the CaseOh90000 panel automatically when the mod starts? [Y/n]\n> ").strip().lower()
        open_panel = answer not in {"n", "no"}
    else:
        open_panel = args.open_panel
    cfg["open_panel_on_start"] = bool(open_panel)
    save_config(cfg)

    if make_shortcut:
        create_shortcut()

    if args.run is None:
        answer = input("Build/rebuild the mod branch from your latest normal save and run it now? [Y/n]\n> ").strip().lower()
        do_run = answer not in {"n", "no"}
    else:
        do_run = args.run
    if do_run:
        print("\nClose the normal Steam game first if you want the absolute latest save copied into the branch.")
        rc = make_branch_from_config(overwrite=True)
        if rc != 0:
            return rc
        rc = run_branch_from_config()
        if rc == 0 and bool(open_panel):
            import time
            time.sleep(1.0)
            open_panel_from_config(detached=True)
        return rc
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    cfg = load_config()
    source = Path(cfg["source"])
    validate_paths(source, Path(cfg["branch"]))
    out = tool_dir() / "scan_profile_from_configured_install.json"
    return run_py(["scan", "--exe", str(source / "Horsey.exe"), "--out", str(out)])


def cmd_show(args: argparse.Namespace) -> int:
    cfg = load_config()
    print(json.dumps(cfg, indent=2))
    return 0


def wants_panel(args: argparse.Namespace) -> bool:
    if hasattr(args, "open_panel") and args.open_panel is not None:
        return bool(args.open_panel)
    try:
        return bool(load_config().get("open_panel_on_start", True))
    except Exception:
        return True


def cmd_refresh_run(args: argparse.Namespace) -> int:
    print("Rebuilding the mod branch from the latest normal save, then launching it.")
    print("Close normal Horsey first if you need the newest save. Close the mod branch before rebuilding it.\n")
    rc = make_branch_from_config(overwrite=True)
    if rc != 0:
        return rc
    rc = run_branch_from_config()
    if rc == 0 and wants_panel(args):
        import time
        time.sleep(1.0)
        open_panel_from_config(detached=True)
    return rc


def cmd_rebuild(args: argparse.Namespace) -> int:
    print("Rebuilding the mod branch from the latest normal save.")
    return make_branch_from_config(overwrite=True)


def cmd_run(args: argparse.Namespace) -> int:
    rc = run_branch_from_config()
    if rc == 0 and wants_panel(args):
        import time
        time.sleep(1.0)
        open_panel_from_config(detached=True)
    return rc


def cmd_panel(args: argparse.Namespace) -> int:
    return open_panel_from_config(detached=False)


def cmd_restore(args: argparse.Namespace) -> int:
    return restore_from_config()


def cmd_shortcut(args: argparse.Namespace) -> int:
    create_shortcut()
    return 0


def cmd_open_branch(args: argparse.Namespace) -> int:
    cfg = load_config()
    return open_folder(Path(cfg["branch"]))


def cmd_open_tool(args: argparse.Namespace) -> int:
    return open_folder(tool_dir())


def apply_to_configured_branch(extra_args: list[str]) -> int:
    cfg = load_config()
    branch = Path(cfg["branch"])
    return run_py(["apply", "--branch", str(branch), *extra_args])


def cmd_apply_baseline(args: argparse.Namespace) -> int:
    return apply_to_configured_branch(["--min-finish-frames", "0", "--display-precision", "3", "--disable-search-controls"])


def cmd_caseoh_on(args: argparse.Namespace) -> int:
    return apply_to_configured_branch(["--caseoh-mode"])


def cmd_caseoh_off(args: argparse.Namespace) -> int:
    return apply_to_configured_branch(["--no-caseoh-mode"])


def cmd_slow_filter(args: argparse.Namespace) -> int:
    return apply_to_configured_branch(["--min-finish-frames", "0", "--display-precision", "3", "--max-sim-frames", "1800", "--valid-result-max", "6000", "--disable-search-controls"])


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="CaseOh90000 v1.0 setup/config wizard")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("setup", help="choose game and mod branch folders")
    s.add_argument("--run", dest="run", action="store_true", default=None)
    s.add_argument("--no-run", dest="run", action="store_false")
    s.add_argument("--shortcut", dest="make_shortcut", action="store_true", default=None)
    s.add_argument("--no-shortcut", dest="make_shortcut", action="store_false")
    s.add_argument("--panel", dest="open_panel", action="store_true", default=None)
    s.add_argument("--no-panel", dest="open_panel", action="store_false")
    s.set_defaults(func=cmd_setup)

    sub.add_parser("show", help="show saved paths").set_defaults(func=cmd_show)
    sub.add_parser("scan", help="scan configured Horsey.exe and write patch profile").set_defaults(func=cmd_scan)
    s = sub.add_parser("refresh-run", help="rebuild branch from latest save and launch it")
    s.add_argument("--panel", dest="open_panel", action="store_true", default=None)
    s.add_argument("--no-panel", dest="open_panel", action="store_false")
    s.set_defaults(func=cmd_refresh_run)
    sub.add_parser("rebuild", help="rebuild branch from latest save but do not launch").set_defaults(func=cmd_rebuild)
    s = sub.add_parser("run", help="launch existing mod branch")
    s.add_argument("--panel", dest="open_panel", action="store_true", default=None)
    s.add_argument("--no-panel", dest="open_panel", action="store_false")
    s.set_defaults(func=cmd_run)
    sub.add_parser("panel", help="open the CaseOh90000 panel for the configured branch").set_defaults(func=cmd_panel)
    sub.add_parser("restore", help="restore branch original executable/data").set_defaults(func=cmd_restore)
    sub.add_parser("shortcut", help="create/recreate the Desktop CaseOh90000 shortcut").set_defaults(func=cmd_shortcut)
    sub.add_parser("open-branch", help="open configured branch folder").set_defaults(func=cmd_open_branch)
    sub.add_parser("open-tool", help="open this tool folder").set_defaults(func=cmd_open_tool)
    sub.add_parser("apply-baseline", help="apply the proven baseline uncap to the configured branch").set_defaults(func=cmd_apply_baseline)
    sub.add_parser("caseoh-on", help="enable caseOh mOde on the configured branch").set_defaults(func=cmd_caseoh_on)
    sub.add_parser("caseoh-off", help="disable caseOh mOde on the configured branch").set_defaults(func=cmd_caseoh_off)
    sub.add_parser("slow-filter", help="apply the optional reject-slow-winners filter to the configured branch").set_defaults(func=cmd_slow_filter)
    return p


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except KeyboardInterrupt:
        print("\nCanceled.")
        return 130
    except Exception as e:
        print(f"ERROR: {e}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
