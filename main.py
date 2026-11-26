#!/usr/bin/env python3
"""News Image 25 Nov 2026 -- sum up 25 November's world news in one image.

Renders a 1024x1024 PNG to /output/entry.png (or $MAKEFUN_OUTPUT_DIR)
using only the Python standard library: no network, no model calls, no
third-party packages, fully deterministic -- the same bytes every run.

The image is a newspaper front page for Wednesday 25 November 2026 with
five stories, each attributed as reported that day:
  1. Strait of Hormuz -- two oil tankers struck by naval mines, on fire
  2. Saudi Arabia -- Houthi attack on the Ras Tanura refinery, and a
     Riyadh skyscraper strike that injured 11
  3. Huawei convicted in a US trial -- trade-secret conspiracy and bank
     fraud, not racketeering
  4. Nvidia -- Jensen Huang returns as CEO amid the AI-chip debate
  5. SpaceX -- approval to launch one million satellites for orbital
     data centres

Text is drawn with a built-in 5x7 bitmap font, scaled up, so the program
needs no font files and no image assets at all.
"""

import os
import struct
import zlib
from binascii import crc32

WIDTH = 1024
HEIGHT = 1024

# --- palette -------------------------------------------------------------
INK = (10, 17, 40)        # deep navy background
PANEL = (19, 28, 58)      # story panel
PANEL_ALT = (16, 24, 48)  # alternating story panel
WHITE = (245, 246, 250)
MUTED = (168, 178, 205)
GOLD = (255, 209, 102)
RED = (230, 57, 70)
TEAL = (56, 189, 248)
ORANGE = (251, 146, 60)
PURPLE = (192, 132, 252)
GREEN = (74, 222, 128)
YELLOW = (250, 204, 21)

# --- 5x7 bitmap font ------------------------------------------------------
# Each glyph is 7 rows of 5 cells; '1' is on, '.' is off. Only the
# characters this image needs are defined; anything else renders blank.
FONT = {
    'A': ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    'B': ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    'C': ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    'D': ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    'E': ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    'F': ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    'G': ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    'H': ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    'I': ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    'J': ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    'K': ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    'L': ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    'M': ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    'N': ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    'O': ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    'P': ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    'Q': ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    'R': ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    'S': ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    'T': ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    'U': ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    'V': ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    'W': ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    'X': ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    'Y': ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    'Z': ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    '0': ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    '1': ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    '2': ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    '3': ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    '4': ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    '5': ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    '6': ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    '7': ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    '8': ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    '9': ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    ' ': (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    '.': (".....", ".....", ".....", ".....", ".....", "01100", "01100"),
    ',': (".....", ".....", ".....", ".....", "01100", "00100", "01000"),
    ':': (".....", "01100", "01100", ".....", "01100", "01100", "....."),
    ';': (".....", "01100", "01100", ".....", "01100", "00100", "01000"),
    '-': (".....", ".....", ".....", "01110", ".....", ".....", "....."),
    "'": ("00100", "00100", "01000", ".....", ".....", ".....", "....."),
    '/': ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    '(': ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ')': ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    '%': ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    '&': ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    '!': ("00100", "00100", "00100", "00100", "00100", ".....", "00100"),
    '?': ("01110", "10001", "00001", "00110", "00100", ".....", "00100"),
    '+': (".....", "00100", "00100", "11111", "00100", "00100", "....."),
    '=': (".....", ".....", "11111", ".....", "11111", ".....", "....."),
}


# --- canvas ---------------------------------------------------------------
# A flat RGB bytearray, row-major, 3 bytes per pixel.
canvas = bytearray(WIDTH * HEIGHT * 3)


def set_pixel(x, y, color):
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        i = (y * WIDTH + x) * 3
        canvas[i], canvas[i + 1], canvas[i + 2] = color


def fill_rect(x, y, w, h, color):
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(WIDTH, x + w)
    y1 = min(HEIGHT, y + h)
    for yy in range(y0, y1):
        base = (yy * WIDTH + x0) * 3
        for xx in range(x0, x1):
            i = base + (xx - x0) * 3
            canvas[i], canvas[i + 1], canvas[i + 2] = color


def fill_circle(cx, cy, r, color):
    for yy in range(cy - r, cy + r + 1):
        for xx in range(cx - r, cx + r + 1):
            if (xx - cx) * (xx - cx) + (yy - cy) * (yy - cy) <= r * r:
                set_pixel(xx, yy, color)


def draw_text(text, x, y, scale, color):
    """Draw upper-case text left-aligned at (x, y); returns width used."""
    text = text.upper()
    cx = x
    for ch in text:
        glyph = FONT.get(ch, FONT[' '])
        for row in range(7):
            for col in range(5):
                if glyph[row][col] == '1':
                    fill_rect(cx + col * scale, y + row * scale,
                              scale, scale, color)
        cx += 6 * scale
    return cx - x


def text_width(text, scale):
    return len(text) * 6 * scale


def wrap_text(text, scale, max_width):
    """Greedy word wrap; returns a list of lines that fit max_width."""
    max_chars = max(1, max_width // (6 * scale))
    words = text.split(' ')
    lines = []
    line = ''
    for word in words:
        trial = word if not line else line + ' ' + word
        if len(trial) <= max_chars:
            line = trial
        else:
            if line:
                lines.append(line)
            # A single over-long word is split across lines.
            while len(word) > max_chars:
                lines.append(word[:max_chars])
                word = word[max_chars:]
            line = word
    if line:
        lines.append(line)
    return lines


def draw_wrapped(text, x, y, scale, max_width, color, line_gap=4):
    lines = wrap_text(text, scale, max_width)
    for i, line in enumerate(lines):
        draw_text(line, x, y + i * (7 * scale + line_gap), scale, color)
    return len(lines) * (7 * scale + line_gap)


# --- PNG encoding (stdlib only) -------------------------------------------
def png_chunk(kind, data):
    chunk = struct.pack('>I', len(data)) + kind + data
    chunk += struct.pack('>I', crc32(kind + data) & 0xFFFFFFFF)
    return chunk


def encode_png():
    raw = bytearray()
    stride = WIDTH * 3
    for y in range(HEIGHT):
        raw.append(0)  # filter: none
        raw += canvas[y * stride:(y + 1) * stride]
    ihdr = struct.pack('>IIBBBBB', WIDTH, HEIGHT, 8, 2, 0, 0, 0)
    return (b'\x89PNG\r\n\x1a\n'
            + png_chunk(b'IHDR', ihdr)
            + png_chunk(b'IDAT', zlib.compress(bytes(raw), 9))
            + png_chunk(b'IEND', b''))


# --- the five stories of 25 November 2026 ---------------------------------
# Headlines are short and factual; sublines attribute claims to the
# reporter, as the news was reported that day. No hype, no speculation.
STORIES = [
    {
        'num': '1',
        'color': TEAL,
        'tag': 'STRAIT OF HORMUZ',
        'headline': 'HORMUZ TANKERS HIT BY MINES',
        'sub': 'IRGC says two oil tankers struck naval mines and caught '
               'fire in the Strait of Hormuz',
    },
    {
        'num': '2',
        'color': ORANGE,
        'tag': 'SAUDI ARABIA',
        'headline': 'HOUTHI STRIKES HIT SAUDI ARABIA',
        'sub': 'Houthis say they attacked the Ras Tanura refinery; a '
               'Riyadh strike injured 11',
    },
    {
        'num': '3',
        'color': PURPLE,
        'tag': 'UNITED STATES',
        'headline': 'HUAWEI GUILTY IN U.S. TRIAL',
        'sub': 'Convicted of conspiracy to steal trade secrets and bank '
               'fraud - not racketeering',
    },
    {
        'num': '4',
        'color': GREEN,
        'tag': 'TECHNOLOGY',
        'headline': 'NVIDIA: HUANG RETURNS AS CEO',
        'sub': 'Jensen Huang is back at the helm as the AI-chip debate '
               'rages on',
    },
    {
        'num': '5',
        'color': YELLOW,
        'tag': 'SPACE',
        'headline': 'SPACEX CLEARED FOR 1M SATELLITES',
        'sub': 'Approval to launch one million satellites for orbital '
               'data centres',
    },
]


def draw_story(story, y, height, bg):
    x = 24
    w = WIDTH - 48
    fill_rect(x, y, w, height, bg)
    # Left accent bar and big number in a coloured disc.
    fill_rect(x, y, 12, height, story['color'])
    fill_circle(x + 62, y + 52, 34, story['color'])
    draw_text(story['num'], x + 62 - 12, y + 52 - 21, 6, INK)
    # Tag, headline, subline.
    tx = x + 116
    draw_text(story['tag'], tx, y + 16, 2, story['color'])
    draw_text(story['headline'], tx, y + 40, 4, WHITE)
    draw_wrapped(story['sub'], tx, y + 84, 3, w - 140, MUTED, line_gap=5)


def draw_image():
    fill_rect(0, 0, WIDTH, HEIGHT, INK)
    # Red masthead rule.
    fill_rect(0, 0, WIDTH, 12, RED)
    # Header.
    draw_text('WORLD NEWS', 24, 30, 3, GOLD)
    date = '25 NOVEMBER 2026'
    draw_text(date, 24, 58, 7, WHITE)
    draw_text('ONE DAY IN ONE IMAGE - FIVE STORIES THAT SHAPED THE WORLD',
              24, 122, 2, MUTED)
    fill_rect(24, 152, WIDTH - 48, 4, RED)
    # Five story panels.
    y = 176
    panel_h = 148
    gap = 10
    for i, story in enumerate(STORIES):
        bg = PANEL if i % 2 == 0 else PANEL_ALT
        draw_story(story, y, panel_h, bg)
        y += panel_h + gap
    # Footer: the date again, so the day is unmistakable.
    draw_text('25 NOVEMBER 2026', 24, 972, 3, GOLD)
    draw_text('REPORTED 25 NOVEMBER 2026', 1024 - 24 - text_width(
        'REPORTED 25 NOVEMBER 2026', 2), 978, 2, MUTED)


def main():
    draw_image()
    out_dir = os.environ.get('MAKEFUN_OUTPUT_DIR', '/output')
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, 'entry.png')
    with open(path, 'wb') as f:
        f.write(encode_png())
    os.chmod(path, 0o644)


if __name__ == '__main__':
    main()
