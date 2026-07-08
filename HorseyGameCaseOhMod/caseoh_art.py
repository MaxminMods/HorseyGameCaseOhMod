#!/usr/bin/env python3
"""Branch-only pixel art patches for HorseyGameCaseOhMod.

This module edits copied-branch art in place. It does not ship or track game
art; it redraws a few small pixels from code.
"""
from __future__ import annotations

import binascii
import shutil
import struct
import zlib
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


PNG_SIG = b"\x89PNG\r\n\x1a\n"
FURNITURE_BACKUP = "furniture.png.caseoh90000_original"


Color = Tuple[int, int, int, int]
ImageData = Tuple[int, int, bytearray]


FONT: Dict[str, Tuple[str, ...]] = {
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "10001", "01110"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "a": ("00000", "01110", "00001", "01111", "10001", "10011", "01101"),
    "e": ("00000", "01110", "10001", "11111", "10000", "10001", "01110"),
    "h": ("10000", "10000", "10110", "11001", "10001", "10001", "10001"),
    "s": ("00000", "01111", "10000", "01110", "00001", "11110", "00000"),
}

SMALL_FONT: Dict[str, Tuple[str, ...]] = {
    " ": ("000", "000", "000", "000", "000"),
    "0": ("111", "101", "101", "101", "111"),
    "9": ("111", "101", "111", "001", "111"),
    "A": ("010", "101", "111", "101", "101"),
    "C": ("111", "100", "100", "100", "111"),
    "E": ("111", "100", "110", "100", "111"),
    "H": ("101", "101", "111", "101", "101"),
    "O": ("111", "101", "101", "101", "111"),
    "S": ("111", "100", "111", "001", "111"),
}


def _chunk(kind: bytes, payload: bytes) -> bytes:
    crc = binascii.crc32(kind + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", crc)


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def read_png_rgba(path: Path) -> ImageData:
    raw = path.read_bytes()
    if not raw.startswith(PNG_SIG):
        raise ValueError(f"{path} is not a PNG")
    pos = len(PNG_SIG)
    width = height = bit_depth = color_type = interlace = None
    idat = bytearray()
    palette: List[Tuple[int, int, int]] = []
    transparency: bytes = b""
    while pos < len(raw):
        size = struct.unpack(">I", raw[pos:pos + 4])[0]
        kind = raw[pos + 4:pos + 8]
        payload = raw[pos + 8:pos + 8 + size]
        pos += 12 + size
        if kind == b"IHDR":
            width, height, bit_depth, color_type, _compression, _filter, interlace = struct.unpack(">IIBBBBB", payload)
        elif kind == b"IDAT":
            idat.extend(payload)
        elif kind == b"PLTE":
            palette = [tuple(payload[i:i + 3]) for i in range(0, len(payload), 3)]  # type: ignore[list-item]
        elif kind == b"tRNS":
            transparency = payload
        elif kind == b"IEND":
            break

    if width is None or height is None or bit_depth is None or color_type is None or interlace is None:
        raise ValueError(f"{path} has no valid PNG header")
    if bit_depth != 8 or interlace != 0 or color_type not in {2, 3, 6}:
        raise ValueError(f"{path} uses an unsupported PNG format")

    channels = {2: 3, 3: 1, 6: 4}[color_type]
    stride = width * channels
    decompressed = zlib.decompress(bytes(idat))
    rows: List[bytearray] = []
    src = 0
    prev = bytearray(stride)
    for _y in range(height):
        filt = decompressed[src]
        src += 1
        row = bytearray(decompressed[src:src + stride])
        src += stride
        for x in range(stride):
            left = row[x - channels] if x >= channels else 0
            up = prev[x]
            up_left = prev[x - channels] if x >= channels else 0
            if filt == 1:
                row[x] = (row[x] + left) & 0xFF
            elif filt == 2:
                row[x] = (row[x] + up) & 0xFF
            elif filt == 3:
                row[x] = (row[x] + ((left + up) // 2)) & 0xFF
            elif filt == 4:
                row[x] = (row[x] + _paeth(left, up, up_left)) & 0xFF
            elif filt != 0:
                raise ValueError(f"unsupported PNG filter {filt}")
        rows.append(row)
        prev = row

    rgba = bytearray(width * height * 4)
    for y, row in enumerate(rows):
        for x in range(width):
            dst = (y * width + x) * 4
            if color_type == 6:
                src4 = x * 4
                rgba[dst:dst + 4] = row[src4:src4 + 4]
            elif color_type == 2:
                src3 = x * 3
                rgba[dst:dst + 4] = row[src3:src3 + 3] + b"\xff"
            else:
                idx = row[x]
                r, g, b = palette[idx]
                a = transparency[idx] if idx < len(transparency) else 255
                rgba[dst:dst + 4] = bytes((r, g, b, a))
    return width, height, rgba


def write_png_rgba(path: Path, image: ImageData) -> None:
    width, height, rgba = image
    rows = bytearray()
    row_len = width * 4
    for y in range(height):
        rows.append(0)
        start = y * row_len
        rows.extend(rgba[start:start + row_len])
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    data = PNG_SIG + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(bytes(rows), 9)) + _chunk(b"IEND", b"")
    path.write_bytes(data)


def _blend(dst: Iterable[int], src: Color) -> bytes:
    dr, dg, db, da = dst
    sr, sg, sb, sa = src
    if sa >= 255:
        return bytes((sr, sg, sb, 255))
    alpha = sa / 255.0
    inv = 1.0 - alpha
    return bytes((int(sr * alpha + dr * inv), int(sg * alpha + dg * inv), int(sb * alpha + db * inv), max(da, sa)))


def pixel(image: ImageData, x: int, y: int, color: Color) -> None:
    width, height, rgba = image
    if x < 0 or y < 0 or x >= width or y >= height:
        return
    i = (y * width + x) * 4
    rgba[i:i + 4] = _blend(rgba[i:i + 4], color)


def rect(image: ImageData, x: int, y: int, w: int, h: int, color: Color) -> None:
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            pixel(image, xx, yy, color)


def rough_rect(image: ImageData, x: int, y: int, w: int, h: int, base: Color, fleck: Color) -> None:
    rect(image, x, y, w, h, base)
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            if (xx * 17 + yy * 31) % 23 == 0:
                pixel(image, xx, yy, fleck)


def line(image: ImageData, x1: int, y1: int, x2: int, y2: int, color: Color, thickness: int = 1) -> None:
    dx = abs(x2 - x1)
    dy = -abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx + dy
    x, y = x1, y1
    while True:
        rect(image, x - thickness // 2, y - thickness // 2, thickness, thickness, color)
        if x == x2 and y == y2:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


def draw_text(image: ImageData, x: int, y: int, text: str, color: Color) -> None:
    cursor = x
    for ch in text:
        glyph = FONT.get(ch) or FONT.get(ch.upper()) or FONT[" "]
        for gy, row in enumerate(glyph):
            for gx, val in enumerate(row):
                if val == "1":
                    pixel(image, cursor + gx, y + gy, color)
        cursor += 6


def draw_small_text(image: ImageData, x: int, y: int, text: str, color: Color) -> None:
    cursor = x
    for ch in text.upper():
        glyph = SMALL_FONT.get(ch) or SMALL_FONT[" "]
        for gy, row in enumerate(glyph):
            for gx, val in enumerate(row):
                if val == "1":
                    pixel(image, cursor + gx, y + gy, color)
        cursor += 4


def draw_caseoh_sign(image: ImageData, x: int, y: int) -> None:
    sign_w, sign_h = 91, 14
    rect(image, x + 2, y + 2, sign_w, sign_h, (0, 0, 0, 70))
    rect(image, x, y, sign_w, sign_h, (224, 57, 75, 255))
    rough_rect(image, x + 2, y + 2, sign_w - 4, sign_h - 4, (238, 221, 180, 255), (215, 194, 145, 255))
    rect(image, x + 3, y - 1, 12, 3, (207, 177, 123, 235))
    rect(image, x + sign_w - 15, y - 1, 12, 3, (207, 177, 123, 235))
    draw_text(image, x + 6, y + 4, "CaseOh 900000", (35, 25, 20, 255))


def draw_compact_caseoh_sign(image: ImageData, x: int, y: int) -> None:
    sign_w, sign_h = 67, 11
    rect(image, x + 1, y + 1, sign_w, sign_h, (0, 0, 0, 70))
    rect(image, x, y, sign_w, sign_h, (224, 57, 75, 255))
    rough_rect(image, x + 2, y + 2, sign_w - 4, sign_h - 4, (238, 221, 180, 255), (215, 194, 145, 255))
    rect(image, x + 4, y - 1, 9, 3, (207, 177, 123, 235))
    rect(image, x + sign_w - 13, y - 1, 9, 3, (207, 177, 123, 235))
    draw_small_text(image, x + 6, y + 3, "CASEOH 900000", (35, 25, 20, 255))


def draw_garage_caseoh_sign(image: ImageData, x: int, y: int) -> None:
    sign_w, sign_h = 87, 14
    rect(image, x + 2, y + 2, sign_w, sign_h, (0, 0, 0, 70))
    rect(image, x, y, sign_w, sign_h, (224, 57, 75, 255))
    rough_rect(image, x + 2, y + 2, sign_w - 4, sign_h - 4, (238, 221, 180, 255), (215, 194, 145, 255))
    rect(image, x + 6, y - 1, 12, 3, (207, 177, 123, 235))
    rect(image, x + sign_w - 18, y - 1, 12, 3, (207, 177, 123, 235))
    draw_text(image, x + 5, y + 4, "CASEOH 900000", (35, 25, 20, 255))


def draw_caseoh_garage_art(image: ImageData) -> None:
    gx, gy = 512, 288

    # Tucked inside the open garage so the closed door hides it.
    draw_garage_caseoh_sign(image, gx + 82, gy + 68)


def apply_caseoh_art(branch: Path) -> Dict[str, object]:
    furniture = branch / "data" / "furniture.png"
    if not furniture.exists():
        return {"applied": False, "reason": "missing furniture.png"}
    backup = furniture.with_name(FURNITURE_BACKUP)
    if not backup.exists():
        shutil.copy2(furniture, backup)
    image = read_png_rgba(backup)
    draw_caseoh_garage_art(image)
    write_png_rgba(furniture, image)
    return {"applied": True, "file": str(furniture), "backup": str(backup)}


def restore_caseoh_art(branch: Path) -> Dict[str, object]:
    furniture = branch / "data" / "furniture.png"
    backup = furniture.with_name(FURNITURE_BACKUP)
    if not backup.exists():
        return {"restored": False, "reason": "no backup yet"}
    shutil.copy2(backup, furniture)
    return {"restored": True, "file": str(furniture), "backup": str(backup)}
