"""Read rendered colors from a screenshot PNG (stdlib only, no Pillow).

  png_colors.py SHOT.png X,Y ...            one pixel each
  png_colors.py SHOT.png X0,Y0,X1,Y1 ...    top 4 colors and the brightest pixel

macOS screenshots are Display P3: values land within a few units of the sRGB
hex in the theme files, close enough to tell a palette color from a leak.
Coordinates are pixels (2x points on Retina).
"""

from __future__ import annotations

import argparse
import struct
import sys
import zlib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

RGB = tuple[int, int, int]


@dataclass
class Image:
    width: int
    height: int
    bpp: int
    data: bytes

    def at(self, x: int, y: int) -> RGB:
        o = (y * self.width + x) * self.bpp
        return (self.data[o], self.data[o + 1], self.data[o + 2])


def paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def load(path: Path) -> Image:
    raw = path.read_bytes()
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    pos, idat, width, height, ctype, interlace = 8, b"", 0, 0, 0, 0
    while pos < len(raw):
        length, kind = struct.unpack(">I4s", raw[pos : pos + 8])
        chunk = raw[pos + 8 : pos + 8 + length]
        if kind == b"IHDR":
            width, height, depth, ctype, _, _, interlace = struct.unpack(
                ">IIBBBBB", chunk
            )
            if depth != 8 or ctype not in (2, 6) or interlace:
                raise ValueError("need 8-bit RGB/RGBA, non-interlaced")
        elif kind == b"IDAT":
            idat += chunk
        pos += 12 + length
    bpp = 3 if ctype == 2 else 4
    stream = zlib.decompress(idat)
    stride = width * bpp
    out = bytearray()
    prev = bytearray(stride)
    i = 0
    for _ in range(height):
        f = stream[i]
        line = bytearray(stream[i + 1 : i + 1 + stride])
        i += 1 + stride
        for x in range(stride):
            a = line[x - bpp] if x >= bpp else 0
            b = prev[x]
            c = prev[x - bpp] if x >= bpp else 0
            pred = (0, a, b, (a + b) // 2, paeth(a, b, c))[f]
            line[x] = (line[x] + pred) & 255
        out += line
        prev = line
    return Image(width, height, bpp, bytes(out))


def hexc(c: RGB) -> str:
    return "#{:02x}{:02x}{:02x}".format(*c)


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("png", type=Path)
    ap.add_argument("spots", nargs="+", help="X,Y or X0,Y0,X1,Y1 in pixels")
    args = ap.parse_args()
    try:
        img = load(args.png)
    except (OSError, ValueError, zlib.error) as err:
        print(f"FAIL: cannot read {args.png}: {err}")
        return 1
    for spot in args.spots:
        nums = [int(v) for v in spot.split(",")]
        if len(nums) == 2:
            print(f"{spot}: {hexc(img.at(nums[0], nums[1]))}")
            continue
        x0, y0, x1, y1 = nums
        cnt: Counter[RGB] = Counter(
            img.at(x, y)
            for y in range(y0, min(y1, img.height))
            for x in range(x0, min(x1, img.width))
        )
        top = ", ".join(f"{hexc(c)} x{n}" for c, n in cnt.most_common(4))
        print(f"{spot}: {top} | brightest {hexc(max(cnt, key=sum))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
