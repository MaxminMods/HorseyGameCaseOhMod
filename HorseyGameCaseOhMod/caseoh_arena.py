#!/usr/bin/env python3
"""Branch-only CaseOh arena support for HorseyGameCaseOhMod.

This module prepares the copied branch for the arena features and launches
Horsey with the bundled native runtime that owns the in-game timer and 40f
race selector. It never edits the normal Steam install.
"""
from __future__ import annotations

import binascii
import ctypes
import json
import os
import shutil
import struct
import sys
import time
import zlib
from ctypes import wintypes
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET

STEAM_APPID = "3602570"
STEAM_DEFAULT = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Horsey Game")
STEAM_SUFFIX = r"\steamapps\common\horsey game"
BRANCH_MARKER = ".HorseyGameArenaBranch"
NATIVE_DLL_NAME = "HorseyGameArenaNative.dll"
PATCH_MANIFEST = "caseoh_arena_patch.json"

ARENA_LABEL_ORIGINAL = b"Old Abandoned Track"
ARENA_LABEL_VISIBLE = b"The Caseoh Arena"
ARENA_LABEL_PATCHED = ARENA_LABEL_VISIBLE + b"\x00" * (len(ARENA_LABEL_ORIGINAL) - len(ARENA_LABEL_VISIBLE))
ARENA_LABEL_OLD_CASEOH = b"The CaseOh Arena" + b"\x00" * (len(ARENA_LABEL_ORIGINAL) - len(b"The CaseOh Arena"))

BIO_LABEL_ORIGINAL = b"Bio-Hacker"
BIO_LABEL_VISIBLE = b"CaseohHaus"

SPRITE_XML = Path("data") / "sprites.xml"
SPRITE_PNG = Path("data") / "sprites.png"
SOUND_DIR = Path("sound")
FURLONG20_RECT = (458, 150, 52, 10)
FURLONG4_RECT = (458, 161, 47, 10)
FURLONG40_RECT = (458, 172, 52, 10)
CASEOH_ARENA_SIGN_RECT = (335, 395, 81, 14)
CASEOH_ARENA_SIGN_BOUNDS = (335, 394, 83, 17)
CASEOH_ARENA_SIGN_TEXT = "CASEOH ARENA"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
OGG_SIGNATURE = b"OggS"
RACE_MUSIC_TARGET_SECONDS = 600.0
RACE_MUSIC_FILES = ("Music_TheBigRace.ogg", "Music_TheBigRace2.ogg")

Color = Tuple[int, int, int, int]

SIGN_FONT: Dict[str, Tuple[str, ...]] = {
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
}


def module_dir() -> Path:
    return Path(__file__).resolve().parent


def is_steam_install_path(path: Path) -> bool:
    try:
        normalized = str(path.resolve()).rstrip("\\/").lower()
    except Exception:
        normalized = str(path).rstrip("\\/").lower()
    return normalized == str(STEAM_DEFAULT).lower() or normalized.endswith(STEAM_SUFFIX)


def validate_branch(branch: Path) -> Path:
    branch = branch.resolve()
    if is_steam_install_path(branch):
        raise RuntimeError(f"Refusing to modify or launch the normal Steam install:\n{branch}")
    if not (branch / "Horsey.exe").exists():
        raise FileNotFoundError(f"Horsey.exe was not found in the copied branch:\n{branch}")
    return branch


def ensure_backup(path: Path, suffix: str) -> Path:
    backup = path.with_name(path.name + suffix)
    if not backup.exists():
        shutil.copy2(path, backup)
    return backup


def write_text_if_changed(path: Path, text: str, encoding: str = "utf-8") -> None:
    if path.exists():
        try:
            if path.read_text(encoding=encoding, errors="ignore") == text:
                return
        except Exception:
            pass
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding=encoding)


def copy_file_if_changed(src: Path, dst: Path) -> str:
    if dst.exists():
        try:
            if dst.read_bytes() == src.read_bytes():
                return "already_installed"
        except Exception:
            pass
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return "installed"


def patch_label_file(path: Path, replacements: List[Tuple[str, bytes, bytes]], backup_suffix: str) -> Dict[str, Any]:
    report: Dict[str, Any] = {"path": str(path), "changes": []}
    if not path.exists():
        report["changes"].append({"name": "labels", "status": "missing"})
        return report
    data = bytearray(path.read_bytes())
    changed = False
    for name, old, new in replacements:
        if len(old) != len(new):
            raise ValueError(f"{name} replacement must stay the same byte length")
        count = 0
        start = 0
        while True:
            off = data.find(old, start)
            if off < 0:
                break
            data[off : off + len(old)] = new
            changed = True
            count += 1
            start = off + len(new)
        if count:
            report["changes"].append({"name": name, "status": "patched", "count": count})
        elif new in data:
            report["changes"].append({"name": name, "status": "already_patched"})
        else:
            report["changes"].append({"name": name, "status": "not_found"})
    if changed:
        ensure_backup(path, backup_suffix)
        path.write_bytes(data)
    return report


def patch_branch_exe_labels(branch: Path) -> Dict[str, Any]:
    return patch_label_file(
        branch / "Horsey.exe",
        [
            ("arena_world_label", ARENA_LABEL_ORIGINAL, ARENA_LABEL_PATCHED),
            ("arena_world_label_case_fix", ARENA_LABEL_OLD_CASEOH, ARENA_LABEL_PATCHED),
            ("biohacker_world_label", BIO_LABEL_ORIGINAL, BIO_LABEL_VISIBLE),
        ],
        ".caseoh_arena_labels.bak",
    )


def patch_branch_save_labels(branch: Path) -> Dict[str, Any]:
    save_dir = branch / "save"
    report: Dict[str, Any] = {"save_dir": str(save_dir), "files": []}
    if not save_dir.exists():
        report["files"].append({"path": str(save_dir), "changes": [{"name": "save_labels", "status": "save_dir_missing"}]})
        return report
    replacements = [
        ("arena_save_label", ARENA_LABEL_ORIGINAL, ARENA_LABEL_PATCHED),
        ("arena_save_label_case_fix", ARENA_LABEL_OLD_CASEOH, ARENA_LABEL_PATCHED),
        ("biohacker_save_label", BIO_LABEL_ORIGINAL, BIO_LABEL_VISIBLE),
    ]
    for save in sorted(save_dir.glob("save*.dat")):
        report["files"].append(patch_label_file(save, replacements, ".caseoh_arena_labels.bak"))
    if not report["files"]:
        report["files"].append({"path": str(save_dir), "changes": [{"name": "save_labels", "status": "no_save_dat_files"}]})
    return report


def png_chunk(kind: bytes, payload: bytes) -> bytes:
    crc = binascii.crc32(kind)
    crc = binascii.crc32(payload, crc) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", crc)


def read_png_chunks(path: Path) -> Tuple[bytes, List[Tuple[bytes, bytes]]]:
    raw = path.read_bytes()
    if not raw.startswith(PNG_SIGNATURE):
        raise RuntimeError(f"Unsupported PNG signature in {path}")
    chunks: List[Tuple[bytes, bytes]] = []
    pos = len(PNG_SIGNATURE)
    while pos + 8 <= len(raw):
        length = struct.unpack(">I", raw[pos : pos + 4])[0]
        kind = raw[pos + 4 : pos + 8]
        payload_start = pos + 8
        payload_end = payload_start + length
        crc_end = payload_end + 4
        if crc_end > len(raw):
            raise RuntimeError(f"Truncated PNG chunk {kind!r} in {path}")
        chunks.append((kind, raw[payload_start:payload_end]))
        pos = crc_end
        if kind == b"IEND":
            break
    return raw[: len(PNG_SIGNATURE)], chunks


def paeth_predictor(left: int, up: int, upper_left: int) -> int:
    p = left + up - upper_left
    pa = abs(p - left)
    pb = abs(p - up)
    pc = abs(p - upper_left)
    if pa <= pb and pa <= pc:
        return left
    if pb <= pc:
        return up
    return upper_left


def unfilter_png_rgba(payload: bytes, width: int, height: int) -> List[bytearray]:
    bpp = 4
    stride = width * bpp
    expected = (stride + 1) * height
    if len(payload) != expected:
        raise RuntimeError(f"Unexpected RGBA scanline size: got {len(payload)}, expected {expected}")
    rows: List[bytearray] = []
    prev = bytearray(stride)
    pos = 0
    for _y in range(height):
        filter_type = payload[pos]
        pos += 1
        row = bytearray(payload[pos : pos + stride])
        pos += stride
        if filter_type == 1:
            for i in range(stride):
                row[i] = (row[i] + (row[i - bpp] if i >= bpp else 0)) & 0xFF
        elif filter_type == 2:
            for i in range(stride):
                row[i] = (row[i] + prev[i]) & 0xFF
        elif filter_type == 3:
            for i in range(stride):
                left = row[i - bpp] if i >= bpp else 0
                row[i] = (row[i] + ((left + prev[i]) // 2)) & 0xFF
        elif filter_type == 4:
            for i in range(stride):
                left = row[i - bpp] if i >= bpp else 0
                up = prev[i]
                upper_left = prev[i - bpp] if i >= bpp else 0
                row[i] = (row[i] + paeth_predictor(left, up, upper_left)) & 0xFF
        elif filter_type != 0:
            raise RuntimeError(f"Unsupported PNG filter type {filter_type}")
        rows.append(row)
        prev = row
    return rows


def read_png_rgba(path: Path) -> Tuple[List[Tuple[bytes, bytes]], int, int, List[bytearray]]:
    _sig, chunks = read_png_chunks(path)
    ihdr = next((payload for kind, payload in chunks if kind == b"IHDR"), None)
    if ihdr is None or len(ihdr) != 13:
        raise RuntimeError(f"PNG IHDR not found in {path}")
    width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(">IIBBBBB", ihdr)
    if bit_depth != 8 or color_type != 6 or compression != 0 or filter_method != 0 or interlace != 0:
        raise RuntimeError("Unsupported sprites.png format. Expected 8-bit RGBA.")
    compressed = b"".join(payload for kind, payload in chunks if kind == b"IDAT")
    if not compressed:
        raise RuntimeError(f"PNG has no IDAT payload: {path}")
    return chunks, width, height, unfilter_png_rgba(zlib.decompress(compressed), width, height)


def write_png_rgba(path: Path, chunks: List[Tuple[bytes, bytes]], width: int, height: int, rows: List[bytearray]) -> None:
    stride = width * 4
    raw = bytearray()
    for row in rows:
        if len(row) != stride:
            raise RuntimeError("Internal PNG row width mismatch.")
        raw.append(0)
        raw.extend(row)
    compressed = zlib.compress(bytes(raw), level=9)
    out = bytearray(PNG_SIGNATURE)
    wrote_idat = False
    for kind, payload in chunks:
        if kind == b"IDAT":
            if not wrote_idat:
                out.extend(png_chunk(b"IDAT", compressed))
                wrote_idat = True
            continue
        if kind == b"IEND" and not wrote_idat:
            out.extend(png_chunk(b"IDAT", compressed))
            wrote_idat = True
        out.extend(png_chunk(kind, payload))
    path.write_bytes(out)


def rect_rows(rows: List[bytearray], x: int, y: int, w: int, h: int) -> List[bytes]:
    return [bytes(rows[y + yy][x * 4 : (x + w) * 4]) for yy in range(h)]


def paste_rect(rows: List[bytearray], x: int, y: int, source_rows: List[bytes]) -> None:
    for yy, source in enumerate(source_rows):
        start = x * 4
        rows[y + yy][start : start + len(source)] = source


def blend_rgba(dst: bytes | bytearray, color: Color) -> bytes:
    dr, dg, db, da = dst
    sr, sg, sb, sa = color
    if sa >= 255:
        return bytes((sr, sg, sb, 255))
    alpha = sa / 255.0
    inv = 1.0 - alpha
    return bytes((int(sr * alpha + dr * inv), int(sg * alpha + dg * inv), int(sb * alpha + db * inv), max(da, sa)))


def put_pixel(rows: List[bytearray], x: int, y: int, color: Color) -> None:
    if y < 0 or y >= len(rows) or not rows:
        return
    width = len(rows[0]) // 4
    if x < 0 or x >= width:
        return
    idx = x * 4
    rows[y][idx : idx + 4] = blend_rgba(rows[y][idx : idx + 4], color)


def fill_rect(rows: List[bytearray], x: int, y: int, w: int, h: int, color: Color) -> None:
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            put_pixel(rows, xx, yy, color)


def rough_fill_rect(rows: List[bytearray], x: int, y: int, w: int, h: int, base: Color, fleck: Color) -> None:
    fill_rect(rows, x, y, w, h, base)
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            if (xx * 17 + yy * 31) % 23 == 0:
                put_pixel(rows, xx, yy, fleck)


def draw_sign_text(rows: List[bytearray], x: int, y: int, text: str, color: Color) -> None:
    cursor = x
    for ch in text.upper():
        glyph = SIGN_FONT.get(ch) or SIGN_FONT[" "]
        for gy, line in enumerate(glyph):
            for gx, value in enumerate(line):
                if value == "1":
                    put_pixel(rows, cursor + gx, y + gy, color)
        cursor += 6


def draw_caseoh_arena_interior_sign(rows: List[bytearray]) -> None:
    x, y, w, h = CASEOH_ARENA_SIGN_RECT
    fill_rect(rows, x + 2, y + 2, w, h, (88, 76, 68, 255))
    fill_rect(rows, x, y, w, h, (224, 57, 75, 255))
    rough_fill_rect(rows, x + 2, y + 2, w - 4, h - 4, (238, 221, 180, 255), (215, 194, 145, 255))
    fill_rect(rows, x + 6, y - 1, 12, 3, (207, 177, 123, 255))
    fill_rect(rows, x + w - 18, y - 1, 12, 3, (207, 177, 123, 255))
    draw_sign_text(rows, x + 5, y + 4, CASEOH_ARENA_SIGN_TEXT, (35, 25, 20, 255))


def build_furlong40_rows(rows: List[bytearray]) -> List[bytes]:
    x20, y20, w20, h20 = FURLONG20_RECT
    x4, y4, _w4, _h4 = FURLONG4_RECT
    canvas = [bytearray(row) for row in rect_rows(rows, x20, y20, w20, h20)]
    digit4_rows = rect_rows(rows, x4, y4, 4, h20)
    for yy, digit in enumerate(digit4_rows):
        canvas[yy][0 : len(digit)] = digit
    return [bytes(row) for row in canvas]


def paint_furlong40_sign_png(png_path: Path) -> str:
    chunks, width, height, rows = read_png_rgba(png_path)
    x40, y40, w40, h40 = FURLONG40_RECT
    if width < x40 + w40 or height < y40 + h40:
        raise RuntimeError(f"sprites.png is too small for Furlong40 region: {width}x{height}")
    canvas = build_furlong40_rows(rows)
    if rect_rows(rows, x40, y40, w40, h40) == canvas:
        return "already_painted_Furlong40"
    paste_rect(rows, x40, y40, canvas)
    write_png_rgba(png_path, chunks, width, height, rows)
    return "painted_Furlong40"


def paint_caseoh_arena_sign_png(png_path: Path) -> str:
    chunks, width, height, rows = read_png_rgba(png_path)
    x, y, w, h = CASEOH_ARENA_SIGN_BOUNDS
    if width < x + w or height < y + h:
        raise RuntimeError(f"sprites.png is too small for CaseOh Arena sign region: {width}x{height}")
    expected = [bytearray(row) for row in rows]
    draw_caseoh_arena_interior_sign(expected)
    expected_rect = rect_rows(expected, x, y, w, h)
    if rect_rows(rows, x, y, w, h) == expected_rect:
        return "already_painted_CaseOhArenaInteriorSign"
    draw_caseoh_arena_interior_sign(rows)
    write_png_rgba(png_path, chunks, width, height, rows)
    return "painted_CaseOhArenaInteriorSign"


def patch_sprites(branch: Path) -> Dict[str, Any]:
    report: Dict[str, Any] = {"changes": []}
    xml_path = branch / SPRITE_XML
    png_path = branch / SPRITE_PNG
    if not xml_path.exists() or not png_path.exists():
        raise FileNotFoundError("Branch data/sprites.xml or data/sprites.png was not found.")
    ensure_backup(xml_path, ".caseoh_arena.bak")
    ensure_backup(png_path, ".caseoh_arena.bak")

    text = xml_path.read_text(encoding="utf-8")
    if 'n="Furlong40"' not in text:
        insert_after = '  <sprite n="Furlong20" x="458" y="150" w="52" h="10" hx="52" hy="10"/>'
        new_line = '  <sprite n="Furlong40" x="458" y="172" w="52" h="10" hx="52" hy="10"/>'
        if insert_after not in text:
            raise RuntimeError("Could not find Furlong20 sprite entry to place Furlong40 after it.")
        xml_path.write_text(text.replace(insert_after, insert_after + "\n" + new_line), encoding="utf-8")
        report["changes"].append({"name": "sprites_xml", "status": "added_Furlong40"})
    else:
        report["changes"].append({"name": "sprites_xml", "status": "already_has_Furlong40"})

    report["changes"].append({"name": "sprites_png_furlong40", "status": paint_furlong40_sign_png(png_path)})
    report["changes"].append({"name": "sprites_png_caseoh_arena_sign", "status": paint_caseoh_arena_sign_png(png_path)})
    return report


def ogg_crc_page(page: bytearray) -> None:
    page[22:26] = b"\x00\x00\x00\x00"
    page[22:26] = struct.pack("<I", binascii.crc32(page) & 0xFFFFFFFF)


def parse_ogg_pages(path: Path) -> List[bytearray]:
    raw = path.read_bytes()
    pages: List[bytearray] = []
    pos = 0
    while pos < len(raw):
        if raw[pos : pos + 4] != OGG_SIGNATURE:
            raise RuntimeError(f"Bad OGG page signature in {path} at byte {pos}")
        if pos + 27 > len(raw):
            raise RuntimeError(f"Truncated OGG page header in {path}")
        segments = raw[pos + 26]
        segment_table_end = pos + 27 + segments
        body_len = sum(raw[pos + 27 : segment_table_end])
        end = segment_table_end + body_len
        if end > len(raw):
            raise RuntimeError(f"Truncated OGG page body in {path}")
        pages.append(bytearray(raw[pos:end]))
        pos = end
    if not pages:
        raise RuntimeError(f"No OGG pages found in {path}")
    return pages


def ogg_page_granule(page: bytearray) -> int:
    return struct.unpack_from("<q", page, 6)[0]


def set_ogg_page_granule(page: bytearray, value: int) -> None:
    struct.pack_into("<q", page, 6, value)


def set_ogg_page_sequence(page: bytearray, value: int) -> None:
    struct.pack_into("<I", page, 18, value)


def vorbis_sample_rate_and_header_page_count(pages: List[bytearray]) -> Tuple[int, int]:
    sample_rate = 0
    completed_packets = 0
    for index, page in enumerate(pages):
        seg_count = page[26]
        body_start = 27 + seg_count
        body = bytes(page[body_start:])
        if sample_rate == 0 and len(body) >= 16 and body[0:7] == b"\x01vorbis":
            sample_rate = struct.unpack_from("<I", body, 12)[0]
        for seg in page[27:body_start]:
            if seg < 255:
                completed_packets += 1
                if completed_packets >= 3:
                    if sample_rate <= 0:
                        raise RuntimeError("Could not read Vorbis sample rate.")
                    return sample_rate, index + 1
    raise RuntimeError("Could not find all three Vorbis header packets.")


def ogg_duration_seconds(path: Path) -> float:
    pages = parse_ogg_pages(path)
    sample_rate, _header_pages = vorbis_sample_rate_and_header_page_count(pages)
    last_granule = max((ogg_page_granule(page) for page in pages if ogg_page_granule(page) >= 0), default=0)
    if sample_rate <= 0 or last_granule <= 0:
        raise RuntimeError(f"Could not measure OGG duration for {path}")
    return float(last_granule) / float(sample_rate)


def build_single_stream_ogg_loop(source: Path, target_seconds: float) -> Tuple[bytes, float, int]:
    pages = parse_ogg_pages(source)
    sample_rate, header_page_count = vorbis_sample_rate_and_header_page_count(pages)
    base_samples = max((ogg_page_granule(page) for page in pages if ogg_page_granule(page) >= 0), default=0)
    if base_samples <= 0:
        raise RuntimeError(f"Could not measure source race music samples: {source}")
    repeats = max(1, int((target_seconds * sample_rate + base_samples - 1) // base_samples))
    audio_pages = pages[header_page_count:]
    if not audio_pages:
        raise RuntimeError(f"No audio pages found after Vorbis headers: {source}")

    out = bytearray()
    seq = 0
    for repeat_index in range(repeats):
        offset = repeat_index * base_samples
        current_pages = pages if repeat_index == 0 else audio_pages
        for page_index, original in enumerate(current_pages):
            page = bytearray(original)
            flags = page[5]
            if repeat_index > 0:
                flags &= ~0x02
            if repeat_index < repeats - 1 or page_index < len(current_pages) - 1:
                flags &= ~0x04
            page[5] = flags
            granule = ogg_page_granule(page)
            if granule >= 0:
                set_ogg_page_granule(page, granule + offset)
            set_ogg_page_sequence(page, seq)
            seq += 1
            ogg_crc_page(page)
            out.extend(page)
    duration = float(base_samples * repeats) / float(sample_rate)
    return bytes(out), duration, repeats


def patch_race_music(branch: Path) -> Dict[str, Any]:
    report: Dict[str, Any] = {"target_seconds": RACE_MUSIC_TARGET_SECONDS, "changes": []}
    sound_dir = branch / SOUND_DIR
    if not sound_dir.exists():
        raise FileNotFoundError(f"Branch sound directory not found: {sound_dir}")
    for name in RACE_MUSIC_FILES:
        path = sound_dir / name
        if not path.exists():
            raise FileNotFoundError(f"Race music file not found: {path}")
        backup = ensure_backup(path, ".caseoh_arena_music.bak")
        try:
            current_duration = ogg_duration_seconds(path)
        except Exception:
            current_duration = 0.0
        if current_duration >= RACE_MUSIC_TARGET_SECONDS:
            report["changes"].append({"name": name, "status": "already_extended", "duration_seconds": round(current_duration, 2)})
            continue
        extended, duration, repeats = build_single_stream_ogg_loop(backup, RACE_MUSIC_TARGET_SECONDS)
        path.write_bytes(extended)
        report["changes"].append({
            "name": name,
            "status": "extended",
            "from_seconds": round(ogg_duration_seconds(backup), 2),
            "to_seconds": round(duration, 2),
            "repeats": repeats,
        })
    return report


def enable_branch_race_logging(branch: Path) -> Dict[str, Any]:
    settings = branch / "save" / "settings.xml"
    report: Dict[str, Any] = {"path": str(settings)}
    if not settings.exists():
        report["status"] = "settings_missing"
        return report
    ensure_backup(settings, ".caseoh_race_logging.bak")
    tree = ET.parse(settings)
    root = tree.getroot()
    keys = {
        "log_races": "1",
        "log_world": "1",
        "background_sim": "1",
        "autosave": "1",
    }
    changed = False
    for key, value in keys.items():
        if root.get(key) != value:
            root.set(key, value)
            changed = True
    if changed:
        tree.write(settings, encoding="utf-8", xml_declaration=False)
    report["status"] = "enabled" if changed else "already_enabled"
    report["keys"] = keys
    return report


def install_native_runtime(branch: Path) -> Dict[str, Any]:
    src = module_dir() / "native" / NATIVE_DLL_NAME
    if not src.exists():
        raise FileNotFoundError(f"Missing bundled native runtime:\n{src}")
    status = copy_file_if_changed(src, branch / NATIVE_DLL_NAME)
    write_text_if_changed(
        branch / BRANCH_MARKER,
        "HorseyGameArena copied branch marker.\nCreated by HorseyGameCaseOhMod v2.\n",
        encoding="ascii",
    )
    write_text_if_changed(branch / "steam_appid.txt", STEAM_APPID + "\n", encoding="ascii")
    return {"dll": str(branch / NATIVE_DLL_NAME), "status": status, "marker": BRANCH_MARKER}


def write_runtime_config(branch: Path) -> Dict[str, Any]:
    runtime = {
        "mode": "caseoh_arena",
        "branch": str(branch),
        "world_map_labels": {
            "abandoned_track": ARENA_LABEL_VISIBLE.decode("ascii"),
            "bio_hacker": BIO_LABEL_VISIBLE.decode("ascii"),
        },
        "race_lengths": [4, 8, 12, 20, 40],
        "timer": "Native in-game timer starts from the abandoned track race/start button and stops on finish.",
    }
    path = branch / "save" / "HorseyGameArenaRuntime.json"
    write_text_if_changed(path, json.dumps(runtime, indent=2), encoding="utf-8")
    return {"path": str(path), "status": "written"}


def prepare_caseoh_arena_branch(branch: Path) -> Dict[str, Any]:
    branch = validate_branch(branch)
    manifest: Dict[str, Any] = {
        "name": "HorseyGameCaseOhMod Caseoh Arena Branch Patch",
        "branch": str(branch),
        "features": {
            "arena_timer": True,
            "forty_furlong_abandoned_track": True,
            "abandoned_track_label": ARENA_LABEL_VISIBLE.decode("ascii"),
            "bio_hacker_label": BIO_LABEL_VISIBLE.decode("ascii"),
        },
        "native_runtime": install_native_runtime(branch),
        "branch_exe_labels": patch_branch_exe_labels(branch),
        "branch_save_labels": patch_branch_save_labels(branch),
    }
    try:
        manifest["sprites"] = patch_sprites(branch)
    except Exception as exc:
        manifest["sprites"] = {"status": "skipped", "reason": str(exc)}
    try:
        manifest["race_music"] = patch_race_music(branch)
    except Exception as exc:
        manifest["race_music"] = {"status": "skipped", "reason": str(exc)}
    try:
        manifest["race_logging"] = enable_branch_race_logging(branch)
    except Exception as exc:
        manifest["race_logging"] = {"status": "skipped", "reason": str(exc)}
    try:
        manifest["runtime_config"] = write_runtime_config(branch)
    except Exception as exc:
        manifest["runtime_config"] = {"status": "skipped", "reason": str(exc)}

    write_text_if_changed(branch / PATCH_MANIFEST, json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def restore_caseoh_arena_branch(branch: Path) -> Dict[str, Any]:
    branch = validate_branch(branch)
    restored: List[str] = []
    for rel, suffix in [
        (Path("Horsey.exe"), ".caseoh_arena_labels.bak"),
        (SPRITE_XML, ".caseoh_arena.bak"),
        (SPRITE_PNG, ".caseoh_arena.bak"),
        (Path("save") / "settings.xml", ".caseoh_race_logging.bak"),
    ]:
        path = branch / rel
        backup = path.with_name(path.name + suffix)
        if backup.exists():
            shutil.copy2(backup, path)
            restored.append(str(rel))
    for name in RACE_MUSIC_FILES:
        path = branch / SOUND_DIR / name
        backup = path.with_name(path.name + ".caseoh_arena_music.bak")
        if backup.exists():
            shutil.copy2(backup, path)
            restored.append(str(SOUND_DIR / name))
    for save in (branch / "save").glob("save*.dat") if (branch / "save").exists() else []:
        backup = save.with_name(save.name + ".caseoh_arena_labels.bak")
        if backup.exists():
            shutil.copy2(backup, save)
            restored.append(str(save.relative_to(branch)))
    for rel in [Path(PATCH_MANIFEST), Path(NATIVE_DLL_NAME), Path(BRANCH_MARKER), Path("save") / "HorseyGameArenaRuntime.json"]:
        path = branch / rel
        if path.exists():
            try:
                path.unlink()
            except Exception:
                pass
    return {"restored": restored}


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.c_void_p),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_void_p),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


def win_last_error(message: str) -> RuntimeError:
    err = ctypes.get_last_error()
    return RuntimeError(f"{message}: {ctypes.FormatError(err).strip()} ({err})")


def list_horsey_processes() -> List[Dict[str, Any]]:
    if not sys.platform.startswith("win"):
        return []
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32FirstW.restype = wintypes.BOOL
    kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32NextW.restype = wintypes.BOOL
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
    if snapshot == wintypes.HANDLE(-1).value:
        return []
    out: List[Dict[str, Any]] = []
    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
    try:
        ok = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while ok:
            if str(entry.szExeFile or "").lower() == "horsey.exe":
                path = ""
                handle = kernel32.OpenProcess(0x1000, False, entry.th32ProcessID)
                if handle:
                    try:
                        buffer = ctypes.create_unicode_buffer(32768)
                        size = wintypes.DWORD(len(buffer))
                        if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                            path = buffer.value
                    finally:
                        kernel32.CloseHandle(handle)
                out.append({"pid": int(entry.th32ProcessID), "path": path})
            ok = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot)
    return out


def normal_steam_horsey_processes() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for proc in list_horsey_processes():
        path = str(proc.get("path") or "")
        if path:
            try:
                if is_steam_install_path(Path(path).parent):
                    out.append(proc)
            except Exception:
                pass
    return out


def terminate_process_id(pid: int) -> None:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.TerminateProcess.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    handle = kernel32.OpenProcess(0x0001, False, int(pid))
    if handle:
        try:
            kernel32.TerminateProcess(handle, 1)
        finally:
            kernel32.CloseHandle(handle)


def guard_branch_launch(process_handle: int, normal_before: set[int]) -> None:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.TerminateProcess.restype = wintypes.BOOL

    exited_at: Optional[float] = None
    deadline = time.time() + 5.0
    while time.time() < deadline:
        redirected = [p for p in normal_steam_horsey_processes() if int(p["pid"]) not in normal_before]
        if redirected:
            for proc in redirected:
                terminate_process_id(int(proc["pid"]))
            if kernel32.WaitForSingleObject(process_handle, 0) != 0:
                kernel32.TerminateProcess(process_handle, 1)
            paths = ", ".join(str(p.get("path") or p.get("pid")) for p in redirected)
            raise RuntimeError(
                "Steam redirected the copied Horsey branch into the normal Steam install. "
                f"The normal game process was stopped for safety: {paths}"
            )
        wait = kernel32.WaitForSingleObject(process_handle, 0)
        if wait == 0:
            if exited_at is None:
                exited_at = time.time()
            elif time.time() - exited_at > 1.0:
                raise RuntimeError("The copied Horsey branch exited immediately before opening a playable window.")
        time.sleep(0.25)


def inject_dll_into_process(process_handle: int, dll_path: Path) -> None:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.VirtualAllocEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD]
    kernel32.VirtualAllocEx.restype = ctypes.c_void_p
    kernel32.WriteProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    kernel32.WriteProcessMemory.restype = wintypes.BOOL
    kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    kernel32.GetModuleHandleW.restype = wintypes.HMODULE
    kernel32.GetProcAddress.argtypes = [wintypes.HMODULE, ctypes.c_char_p]
    kernel32.GetProcAddress.restype = ctypes.c_void_p
    kernel32.CreateRemoteThread.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p]
    kernel32.CreateRemoteThread.restype = wintypes.HANDLE
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.GetExitCodeThread.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel32.GetExitCodeThread.restype = wintypes.BOOL
    kernel32.VirtualFreeEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD]
    kernel32.VirtualFreeEx.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    dll_buffer = ctypes.create_unicode_buffer(str(dll_path.resolve()))
    byte_count = ctypes.sizeof(dll_buffer)
    remote = kernel32.VirtualAllocEx(process_handle, None, byte_count, 0x1000 | 0x2000, 0x04)
    if not remote:
        raise win_last_error("VirtualAllocEx failed while preparing the in-game timer")
    thread = None
    try:
        written = ctypes.c_size_t(0)
        if not kernel32.WriteProcessMemory(process_handle, remote, ctypes.cast(dll_buffer, ctypes.c_void_p), byte_count, ctypes.byref(written)) or written.value != byte_count:
            raise win_last_error("WriteProcessMemory failed while loading the in-game timer")
        kernel32_handle = kernel32.GetModuleHandleW("kernel32.dll")
        load_library = kernel32.GetProcAddress(kernel32_handle, b"LoadLibraryW") if kernel32_handle else None
        if not load_library:
            raise RuntimeError("Could not find LoadLibraryW for in-game timer startup.")
        thread = kernel32.CreateRemoteThread(process_handle, None, 0, load_library, remote, 0, None)
        if not thread:
            raise win_last_error("CreateRemoteThread failed while starting the in-game timer")
        if kernel32.WaitForSingleObject(thread, 10000) != 0:
            raise RuntimeError("Timed out while waiting for the in-game timer to load.")
        exit_code = wintypes.DWORD(0)
        if kernel32.GetExitCodeThread(thread, ctypes.byref(exit_code)) and exit_code.value == 0:
            raise RuntimeError("Horsey did not load the in-game timer DLL.")
    finally:
        if thread:
            kernel32.CloseHandle(thread)
        kernel32.VirtualFreeEx(process_handle, remote, 0, 0x8000)


def launch_horsey_branch_with_native(branch: Path) -> None:
    if not sys.platform.startswith("win"):
        raise RuntimeError("The in-game timer launcher is Windows-only.")
    branch = validate_branch(branch)
    prepare_caseoh_arena_branch(branch)
    dll_path = branch / NATIVE_DLL_NAME
    if not dll_path.exists():
        raise FileNotFoundError(f"Native timer DLL is not installed in the branch:\n{dll_path}")
    normal_before_processes = normal_steam_horsey_processes()
    if normal_before_processes:
        paths = ", ".join(str(p.get("path") or p.get("pid")) for p in normal_before_processes)
        raise RuntimeError(f"Close the normal Steam Horsey Game before launching the safe branch: {paths}")
    normal_before = {int(p["pid"]) for p in normal_before_processes}
    os.environ["SteamAppId"] = STEAM_APPID
    os.environ["SteamGameId"] = STEAM_APPID
    os.environ["SteamOverlayGameId"] = STEAM_APPID

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateProcessW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.BOOL,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.LPCWSTR,
        ctypes.POINTER(STARTUPINFOW),
        ctypes.POINTER(PROCESS_INFORMATION),
    ]
    kernel32.CreateProcessW.restype = wintypes.BOOL
    kernel32.ResumeThread.argtypes = [wintypes.HANDLE]
    kernel32.ResumeThread.restype = wintypes.DWORD
    kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.TerminateProcess.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    horsey = branch / "Horsey.exe"
    startup = STARTUPINFOW()
    startup.cb = ctypes.sizeof(startup)
    process = PROCESS_INFORMATION()
    cmd = ctypes.create_unicode_buffer(f'"{horsey}"')
    created = kernel32.CreateProcessW(
        str(horsey),
        cmd,
        None,
        None,
        False,
        0x00000004,
        None,
        str(branch),
        ctypes.byref(startup),
        ctypes.byref(process),
    )
    if not created:
        raise win_last_error("Could not start the safe Horsey branch")
    resumed = False
    try:
        inject_dll_into_process(process.hProcess, dll_path)
        if kernel32.ResumeThread(process.hThread) == 0xFFFFFFFF:
            raise win_last_error("Could not resume Horsey after loading the in-game timer")
        resumed = True
        guard_branch_launch(process.hProcess, normal_before)
    finally:
        if not resumed:
            kernel32.TerminateProcess(process.hProcess, 1)
        kernel32.CloseHandle(process.hThread)
        kernel32.CloseHandle(process.hProcess)
