#!/usr/bin/env python3
"""Generate og-image.png (1200x630) using only the standard library."""

import struct
import zlib
from pathlib import Path

WIDTH, HEIGHT = 1200, 630

# Brand colors
INK = (26, 26, 46)
CREAM = (255, 249, 240)
YELLOW = (255, 217, 61)
CORAL = (255, 107, 107)
TEAL = (78, 205, 196)
VIOLET = (155, 93, 229)
PINK = (241, 91, 181)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def put_pixel(buf, x, y, color):
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        idx = (y * WIDTH + x) * 3
        buf[idx:idx + 3] = bytes(color)


def fill_rect(buf, x0, y0, x1, y1, color):
    x0 = max(0, x0); y0 = max(0, y0)
    x1 = min(WIDTH, x1); y1 = min(HEIGHT, y1)
    for y in range(y0, y1):
        row = y * WIDTH
        for x in range(x0, x1):
            idx = (row + x) * 3
            buf[idx:idx + 3] = bytes(color)


def fill_circle(buf, cx, cy, r, color):
    r2 = r * r
    for y in range(max(0, cy - r), min(HEIGHT, cy + r + 1)):
        dy = y - cy
        for x in range(max(0, cx - r), min(WIDTH, cx + r + 1)):
            dx = x - cx
            if dx * dx + dy * dy <= r2:
                idx = (y * WIDTH + x) * 3
                buf[idx:idx + 3] = bytes(color)


def write_png(path, raw):
    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 2, 0, 0, 0)
    raw_bytes = bytes(raw)
    stride = WIDTH * 3
    lines = bytearray()
    for y in range(HEIGHT):
        lines.append(0)
        lines.extend(raw_bytes[y * stride:(y + 1) * stride])
    idat = zlib.compress(bytes(lines), 9)
    Path(path).write_bytes(sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b""),)


def main():
    buf = bytearray(WIDTH * HEIGHT * 3)
    # Cream background
    fill_rect(buf, 0, 0, WIDTH, HEIGHT, CREAM)
    # Corner color blobs (radial-ish via stacked circles)
    fill_circle(buf, 120, 110, 280, lerp(CREAM, YELLOW, 0.35))
    fill_circle(buf, 120, 110, 220, lerp(CREAM, YELLOW, 0.55))
    fill_circle(buf, 1080, 520, 300, lerp(CREAM, TEAL, 0.30))
    fill_circle(buf, 1080, 520, 240, lerp(CREAM, TEAL, 0.50))
    fill_circle(buf, 1020, 110, 220, lerp(CREAM, CORAL, 0.35))
    fill_circle(buf, 180, 540, 240, lerp(CREAM, PINK, 0.30))
    # Central ink card
    pad = 90
    fill_rect(buf, pad, pad, WIDTH - pad, HEIGHT - pad, INK)
    # Colored top bar
    fill_rect(buf, pad, pad, WIDTH - pad, pad + 16, YELLOW)
    fill_rect(buf, pad, pad + 16, WIDTH - pad, pad + 26, CORAL)
    fill_rect(buf, pad, pad + 26, WIDTH - pad, pad + 34, TEAL)
    fill_rect(buf, pad, pad + 34, WIDTH - pad, pad + 40, VIOLET)
    # Bone glyph (stylized) - two circles + bar, in yellow on ink
    cx, cy = WIDTH // 2, 300
    fill_circle(buf, cx - 70, cy - 40, 46, YELLOW)
    fill_circle(buf, cx - 70, cy + 40, 46, YELLOW)
    fill_circle(buf, cx + 70, cy - 40, 46, YELLOW)
    fill_circle(buf, cx + 70, cy + 40, 46, YELLOW)
    fill_rect(buf, cx - 95, cy - 22, cx + 95, cy + 22, YELLOW)
    # Wordmark bar
    fill_rect(buf, cx - 260, 470, cx + 260, 545, YELLOW)
    write_png("og-image.png", buf)
    print("Wrote og-image.png (1200x630)")


if __name__ == "__main__":
    main()