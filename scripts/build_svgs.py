import argparse
import base64
import json
import os
import random
import re
import subprocess
import textwrap
import urllib.request
from dataclasses import dataclass
from datetime import date
from html import escape
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_PATH = REPO_ROOT / "scripts" / "profile_content.json"
CONTRIBUTIONS_PATH = REPO_ROOT / "scripts" / "contributions.json"
FONT_PATH = REPO_ROOT / "assets" / "fonts" / "VT323-subset.woff2"
ASSETS_DIR = REPO_ROOT / "assets"

GRAPHQL_URL = "https://api.github.com/graphql"
CONTRIBUTIONS_QUERY = (
    "query($login: String!) { user(login: $login) { contributionsCollection { contributionCalendar { "
    "totalContributions weeks { contributionDays { date weekday contributionCount contributionLevel } } } } } }"
)

# VT323 is strictly monospaced: every glyph has hmtx advanceWidth 400 on a 1000-unit em
# (head.unitsPerEm), so one character cell is 400 / 1000 * font-size wide.
CELL_RATIO = 400 / 1000
FONT_STACK = "'VT323','Courier New',Consolas,monospace"

BG_DEEP = "#070400"
BG = "#120a00"
GLOW_CORE = "#2a1700"
AMBER = "#ffb000"
AMBER_HI = "#ffd27a"
AMBER_MID = "#c98a00"
AMBER_DIM = "#7a5200"
AMBER_FAINT = "#3a2600"
PLASTIC_TOP = "#2b2620"
PLASTIC_BOTTOM = "#16130f"
PLASTIC_INK = "#6b5f50"
NEOFETCH_SWATCHES = ["#3a2600", "#5c3d00", "#7a5200", "#a06c00", "#c98a00", "#e69e00", "#ffb000", "#ffd27a"]
HEATMAP_LEVELS = {
    "NONE": "#1a0f00",
    "FIRST_QUARTILE": "#4d2e00",
    "SECOND_QUARTILE": "#7a5200",
    "THIRD_QUARTILE": "#c98a00",
    "FOURTH_QUARTILE": AMBER,
}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

TERM_SIZE = 20
TERM_LINE = 24
TITLE_BAR = 32
CURSOR_PERIOD = 1.06

PIXEL_FONT = {
    "A": ".###.|#...#|#...#|#####|#...#|#...#|#...#",
    "B": "####.|#...#|#...#|####.|#...#|#...#|####.",
    "C": ".###.|#...#|#....|#....|#....|#...#|.###.",
    "D": "####.|#...#|#...#|#...#|#...#|#...#|####.",
    "E": "#####|#....|#....|####.|#....|#....|#####",
    "F": "#####|#....|#....|####.|#....|#....|#....",
    "G": ".###.|#...#|#....|#.###|#...#|#...#|.####",
    "H": "#...#|#...#|#...#|#####|#...#|#...#|#...#",
    "I": ".###.|..#..|..#..|..#..|..#..|..#..|.###.",
    "J": "..###|...#.|...#.|...#.|...#.|#..#.|.##..",
    "K": "#...#|#..#.|#.#..|##...|#.#..|#..#.|#...#",
    "L": "#....|#....|#....|#....|#....|#....|#####",
    "M": "#...#|##.##|#.#.#|#.#.#|#...#|#...#|#...#",
    "N": "#...#|#...#|##..#|#.#.#|#..##|#...#|#...#",
    "O": ".###.|#...#|#...#|#...#|#...#|#...#|.###.",
    "P": "####.|#...#|#...#|####.|#....|#....|#....",
    "Q": ".###.|#...#|#...#|#...#|#.#.#|#..#.|.##.#",
    "R": "####.|#...#|#...#|####.|#.#..|#..#.|#...#",
    "S": ".####|#....|#....|.###.|....#|....#|####.",
    "T": "#####|..#..|..#..|..#..|..#..|..#..|..#..",
    "U": "#...#|#...#|#...#|#...#|#...#|#...#|.###.",
    "V": "#...#|#...#|#...#|#...#|#...#|.#.#.|..#..",
    "W": "#...#|#...#|#...#|#.#.#|#.#.#|#.#.#|.#.#.",
    "X": "#...#|#...#|.#.#.|..#..|.#.#.|#...#|#...#",
    "Y": "#...#|#...#|.#.#.|..#..|..#..|..#..|..#..",
    "Z": "#####|....#|...#.|..#..|.#...|#....|#####",
    "0": ".###.|#...#|#..##|#.#.#|##..#|#...#|.###.",
    "1": "..#..|.##..|..#..|..#..|..#..|..#..|.###.",
    "2": ".###.|#...#|....#|...#.|..#..|.#...|#####",
    "3": ".###.|#...#|....#|..##.|....#|#...#|.###.",
    "4": "...#.|..##.|.#.#.|#..#.|#####|...#.|...#.",
    "5": "#####|#....|####.|....#|....#|#...#|.###.",
    "6": "..##.|.#...|#....|####.|#...#|#...#|.###.",
    "7": "#####|....#|...#.|..#..|.#...|.#...|.#...",
    "8": ".###.|#...#|#...#|.###.|#...#|#...#|.###.",
    "9": ".###.|#...#|#...#|.####|....#|...#.|.##..",
    "-": ".....|.....|.....|#####|.....|.....|.....",
    "_": ".....|.....|.....|.....|.....|.....|#####",
    ".": ".....|.....|.....|.....|.....|.##..|.##..",
    " ": ".....|.....|.....|.....|.....|.....|.....",
}

PAPER_PLANE_ICON = [
    "#........",
    "###......",
    "#####....",
    ".#######.",
    "..#######",
    ".#######.",
    "#####....",
    "###......",
    "#........",
]

LINKEDIN_ICON = [
    "##.......",
    "##.......",
    ".........",
    "##.####..",
    "##.##.##.",
    "##.##.##.",
    "##.##.##.",
    "##.##.##.",
    "##.##.##.",
]

WORD_RUN = re.compile(r"\S+(?: \S+)*")


def num(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def key_time(v):
    return f"{v:.4f}".rstrip("0").rstrip(".") or "0"


@dataclass(frozen=True)
class Term:
    x0: float
    size: float = TERM_SIZE
    line: float = TERM_LINE

    @property
    def cell(self):
        return self.size * CELL_RATIO

    def x(self, col):
        return self.x0 + col * self.cell

    def baseline(self, top):
        # centre the em box (ascender .8 / descender .2) inside the row
        return top + (self.line - self.size) / 2 + 0.8 * self.size

    def mid(self, top):
        return self.baseline(top) - 0.3 * self.size

    def cursor_rect(self, col, top, fill=AMBER, extra=""):
        h = self.line * 0.85
        return rect(self.x(col), top + (self.line - h) / 2, self.cell, h, fill, extra)


def rect(x, y, w, h, fill, extra=""):
    return f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" fill="{fill}"{extra}/>'


def text_el(x, y, s, size, fill=None, extra=""):
    width = len(s) * size * CELL_RATIO
    fill_attr = f' fill="{fill}"' if fill else ""
    return (
        f'<text x="{num(x)}" y="{num(y)}" font-size="{num(size)}"{fill_attr} '
        f'textLength="{num(width)}" lengthAdjust="spacingAndGlyphs"{extra}>{escape(s, quote=False)}</text>'
    )


def spans(term, col, top, s, fill):
    """One <text> per run of single-spaced words, so wide gaps stay on exact columns."""
    y = term.baseline(top)
    return "".join(text_el(term.x(col + m.start()), y, m.group(), term.size, fill) for m in WORD_RUN.finditer(s))


def line(term, col, top, *parts):
    out = []
    for s, fill in parts:
        out.append(spans(term, col, top, s, fill))
        col += len(s)
    return "".join(out)


def appear(t, body):
    return f'<g class="p" style="animation-delay:{num(t)}s">{body}</g>'


def visible_between(t0, t1, body):
    return f'<g class="w" style="animation-delay:{num(t0)}s;animation-duration:{num(t1 - t0)}s">{body}</g>'


def discrete(attr, frames):
    """SMIL step animation that always starts at 0s; frames are (time, value) with the first at 0."""
    end = frames[-1][0]
    keys = ";".join(key_time(t / end) for t, _ in frames)
    values = ";".join(num(v) for _, v in frames)
    dur = f"{end:.3f}".rstrip("0").rstrip(".")
    return (
        f'<animate attributeName="{attr}" calcMode="discrete" begin="0s" dur="{dur}s" '
        f'fill="freeze" keyTimes="{keys}" values="{values}"/>'
    )


def keystroke_times(text, t0, pace, jitter=0.45):
    rng = random.Random(text)
    times, t = [], t0
    for ch in text:
        t += pace * (1 + jitter * (rng.random() * 2 - 1))
        if ch == " ":
            t += pace * 0.6
        times.append(t)
    return times


def typed(term, col, top, parts, t0, uid, *, pace=0.075, jitter=0.45, cursor_from=None, cursor_hold=0.22):
    """Reveals `parts` char by char through an animated clip; returns (svg, time of the last keystroke)."""
    text = "".join(s for s, _ in parts)
    times = keystroke_times(text, t0, pace, jitter)
    x0, cell, n = term.x(col), term.cell, len(text)
    width = discrete("width", [(0, 0)] + [(t, (i + 1) * cell) for i, t in enumerate(times)])
    svg = (
        f'<clipPath id="{uid}"><rect x="{num(x0)}" y="{num(top)}" width="{num(n * cell)}" '
        f'height="{num(term.line)}">{width}</rect></clipPath>'
        f'<g clip-path="url(#{uid})">{line(term, col, top, *parts)}</g>'
    )
    if cursor_from is not None:
        move = discrete("x", [(0, x0)] + [(t, x0 + (i + 1) * cell) for i, t in enumerate(times)])
        shown = discrete("opacity", [(0, 0), (cursor_from, 1), (times[-1] + cursor_hold, 0)])
        svg += term.cursor_rect(col + n, top, AMBER, ' opacity="0"')[:-2] + f">{move}{shown}</rect>"
    return svg, times[-1]


def blinking_cursor(term, col, top, t):
    return appear(t, term.cursor_rect(col, top, AMBER, ' class="blink"'))


def command_line(term, top, prompt, command, t_prompt, t_type, uid, pace=0.075):
    body = appear(t_prompt, line(term, 0, top, (prompt, AMBER)))
    typed_svg, end = typed(term, len(prompt), top, [(command, AMBER_HI)], t_type, uid, pace=pace, cursor_from=t_prompt)
    return body + typed_svg, end


def pixel_rects(rows, x, y, pitch, dot, palette):
    out = []
    inset = (pitch - dot) / 2
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            fill = palette.get(ch)
            if fill is None:
                continue
            fill_attr = f' fill="{fill}"' if fill else ""
            out.append(
                f'<rect x="{num(x + c * pitch + inset)}" y="{num(y + r * pitch + inset)}" '
                f'width="{num(dot)}" height="{num(dot)}" rx="{num(dot * 0.14)}"{fill_attr}/>'
            )
    return "".join(out)


def raster_reveal(uid, x, y, w, row_h, rows, t0, t1):
    step = (t1 - t0) / rows
    frames = [(0, 0)] + [(t0 + (r + 1) * step, (r + 1) * row_h) for r in range(rows)]
    return (
        f'<clipPath id="{uid}"><rect x="{num(x)}" y="{num(y)}" width="{num(w)}" '
        f'height="{num(rows * row_h)}">{discrete("height", frames)}</rect></clipPath>'
    )


def render_bitmap_text(text, x, y, pitch, dot):
    glyphs = [PIXEL_FONT.get(ch, PIXEL_FONT[" "]).split("|") for ch in text.upper()]
    rows = [".".join(g[r] for g in glyphs) for r in range(7)]
    return pixel_rects(rows, x, y, pitch, dot, {"#": ""}), len(rows[0])


def font_css():
    font = base64.b64encode(FONT_PATH.read_bytes()).decode("ascii")
    return (
        f"@font-face{{font-family:'VT323';src:url(data:font/woff2;base64,{font}) format('woff2')}}"
        f"text{{font-family:{FONT_STACK}}}"
    )


def base_css(screen_h, extra=""):
    return (
        font_css()
        + ".p{animation:show .01s linear both}"
        ".w{opacity:0;animation:on 1s linear}"
        f".blink{{animation:blink {CURSOR_PERIOD}s step-end infinite}}"
        ".sweep{animation:sweep 6.6s linear infinite}"
        ".flicker{animation:flicker 5.3s linear infinite}"
        "@keyframes show{from{opacity:0}to{opacity:1}}"
        "@keyframes on{from,to{opacity:1}}"
        "@keyframes blink{0%{opacity:1}50%{opacity:0}}"
        f"@keyframes sweep{{to{{transform:translateY({num(screen_h + 90)}px)}}}}"
        "@keyframes flicker{0%,100%{opacity:0}7%{opacity:.03}8%{opacity:0}31%{opacity:0}32%{opacity:.022}"
        "33%{opacity:0}34%{opacity:.035}35.5%{opacity:0}63%{opacity:0}66%{opacity:.02}69%{opacity:0}"
        "88%{opacity:0}88.6%{opacity:.03}89.4%{opacity:0}}"
        f"{extra}"
        "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
    )


def screen_defs(x, y, w, h, radius, *, glow=2.0, bloom=7.0, bloom_alpha=0.35):
    fx, fy, fw, fh = x - 20, y - 20, w + 40, h + 40
    return (
        f'<clipPath id="screen"><rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" rx="{num(radius)}"/></clipPath>'
        '<radialGradient id="phosphor" cx=".5" cy=".46" r=".72">'
        f'<stop offset="0" stop-color="{GLOW_CORE}" stop-opacity=".85"/>'
        f'<stop offset=".55" stop-color="{BG}" stop-opacity=".7"/>'
        f'<stop offset="1" stop-color="{BG_DEEP}" stop-opacity="0"/></radialGradient>'
        '<radialGradient id="vignette" cx=".5" cy=".5" r=".72">'
        '<stop offset=".58" stop-color="#000" stop-opacity="0"/>'
        '<stop offset="1" stop-color="#000" stop-opacity=".55"/></radialGradient>'
        '<linearGradient id="sweep-band" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{AMBER}" stop-opacity="0"/>'
        f'<stop offset=".55" stop-color="{AMBER}" stop-opacity=".06"/>'
        f'<stop offset="1" stop-color="{AMBER}" stop-opacity="0"/></linearGradient>'
        '<linearGradient id="glare" x1="0" y1="0" x2=".55" y2="1">'
        '<stop offset="0" stop-color="#fff4e0" stop-opacity=".055"/>'
        '<stop offset=".4" stop-color="#fff4e0" stop-opacity=".012"/>'
        '<stop offset=".55" stop-color="#fff4e0" stop-opacity="0"/></linearGradient>'
        '<pattern id="scanlines" width="8" height="3" patternUnits="userSpaceOnUse">'
        '<rect width="8" height="1" fill="#000" opacity=".25"/></pattern>'
        f'<filter id="glow" x="{num(fx)}" y="{num(fy)}" width="{num(fw)}" height="{num(fh)}" '
        'filterUnits="userSpaceOnUse" color-interpolation-filters="sRGB">'
        f'<feGaussianBlur in="SourceGraphic" stdDeviation="{glow}" result="halo"/>'
        f'<feGaussianBlur in="SourceGraphic" stdDeviation="{bloom}" result="wide"/>'
        f'<feComponentTransfer in="wide" result="bloom"><feFuncA type="linear" slope="{bloom_alpha}"/></feComponentTransfer>'
        '<feMerge><feMergeNode in="bloom"/><feMergeNode in="halo"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        f'<filter id="edge" x="{num(fx)}" y="{num(fy)}" width="{num(fw)}" height="{num(fh)}" filterUnits="userSpaceOnUse">'
        '<feGaussianBlur stdDeviation="7"/></filter>'
    )


def crt_screen(x, y, w, h, radius, content, *, layer_class=None, layer_extra="", above_layer=""):
    full = f'x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}"'
    layer_open = f'<g class="{layer_class}">' if layer_class else "<g>"
    return (
        '<g clip-path="url(#screen)">'
        f'<rect {full} fill="{BG_DEEP}"/>'
        f"{layer_open}"
        f'<rect {full} fill="url(#phosphor)"/>'
        f'<g filter="url(#glow)">{content}</g>'
        f"{layer_extra}</g>{above_layer}"
        f'<rect class="sweep" x="{num(x)}" y="{num(y - 90)}" width="{num(w)}" height="90" fill="url(#sweep-band)"/>'
        f'<rect {full} fill="url(#scanlines)"/>'
        f'<rect {full} fill="url(#vignette)"/>'
        f'<rect class="flicker" {full} fill="#000" opacity="0"/>'
        f'<rect {full} rx="{num(radius)}" fill="none" stroke="#000" stroke-opacity=".7" stroke-width="14" filter="url(#edge)"/>'
        f'<rect {full} fill="url(#glare)"/>'
        "</g>"
    )


def svg_document(w, h, title, desc, css, defs, body):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{num(w)}" height="{num(h)}" viewBox="0 0 {num(w)} {num(h)}" '
        f'role="img" aria-labelledby="title desc">'
        f"<title id=\"title\">{escape(title)}</title><desc id=\"desc\">{escape(desc)}</desc>"
        f"<defs><style>{css}</style>{defs}</defs>{body}</svg>\n"
    )


def window_chrome(w, title, term):
    top = (TITLE_BAR - term.line) / 2 + 1
    mid = TITLE_BAR / 2 + 1
    sq = term.cell * 0.8
    parts = [
        rect(0, 0, w, TITLE_BAR, AMBER, ' opacity=".035"'),
        rect(0, TITLE_BAR, w, 1, AMBER_FAINT),
        line(term, 0, top, ("[", AMBER_DIM)),
        rect(term.x(1) + (term.cell - sq) / 2, mid - sq / 2, sq, sq, AMBER_DIM),
        line(term, 2, top, ("]", AMBER_DIM), (" " + title, AMBER_DIM)),
    ]
    right, box = w - term.x0, 10
    stroke = f'fill="none" stroke="{AMBER_DIM}" stroke-width="1.6"'
    close_x = right - box
    parts.append(
        f'<path d="M{num(close_x)} {num(mid - box / 2)}l{box} {box}m0 -{box}l-{box} {box}" {stroke} stroke-linecap="square"/>'
    )
    parts.append(f'<rect x="{num(close_x - 24 + 0.8)}" y="{num(mid - box / 2 + 0.8)}" width="{num(box - 1.6)}" height="{num(box - 1.6)}" {stroke}/>')
    parts.append(rect(close_x - 48, mid + box / 2 - 2, box, 1.8, AMBER_DIM))
    return "".join(parts)


def window_panel(w, h, title, desc, term, window_title, body_svg, extra_css="", extra_defs="", overlay=""):
    """`overlay` is drawn above the CRT effects (scanlines, sweep, vignette) and stays untouched by them."""
    radius = 14
    defs = screen_defs(1, 1, w - 2, h - 2, radius - 1) + extra_defs
    body = (
        crt_screen(1, 1, w - 2, h - 2, radius - 1, window_chrome(w, window_title, term) + body_svg)
        + (f'<g clip-path="url(#screen)">{overlay}</g>' if overlay else "")
        + f'<rect x=".5" y=".5" width="{num(w - 1)}" height="{num(h - 1)}" rx="{radius}" fill="none" stroke="{AMBER_FAINT}"/>'
    )
    return svg_document(w, h, title, desc, base_css(h, extra_css), defs, body)


def build_boot(content):
    boot = content["boot"]
    size, row_h, cols = 22.5, 26, 80
    cell = size * CELL_RATIO
    pad_x = 40
    W = 900
    glass_w = cols * cell + 2 * pad_x
    glass_x = (W - glass_w) / 2
    glass_y = 46
    term = Term(glass_x + pad_x, size, row_h)
    pitch, dot = 10, 8.4

    y = glass_y + 24
    rows = {"bios": y}
    y += row_h
    rule_y = y + 5
    y += 12
    rows["mem"] = y
    y += row_h
    rows["cpu"] = y
    y += row_h + 8
    rows["detect"] = y
    y += row_h
    device_rows = []
    for _ in boot["devices"]:
        device_rows.append(y)
        y += row_h
    y += 10
    rows["load"] = y
    y += row_h + 24
    title_top = y
    y += 7 * pitch + 22
    rows["tagline"] = y
    y += row_h + 10
    rows["prompt"] = y
    y += row_h + 20
    glass_h = y - glass_y

    out = []
    out.append(appear(0.4, line(term, 0, rows["bios"], (boot["bios_left"], AMBER_HI))))
    right = boot["bios_right"]
    out.append(appear(0.45, line(term, cols - len(right), rows["bios"], (right, AMBER_HI))))
    out.append(
        f'<rect class="rule" x="{num(term.x(0))}" y="{num(rule_y)}" width="{num(cols * cell)}" height="2" fill="{AMBER_DIM}"/>'
    )

    label_w = max(len(boot["memory_label"]), len(boot["cpu_label"]))
    value_col = label_w + 3
    mem_label = boot["memory_label"].ljust(label_w) + " :"
    out.append(appear(0.8, line(term, 0, rows["mem"], (mem_label, AMBER))))
    total_kb = boot["memory_kb"]
    steps = 8
    width = len(str(total_kb))
    for i in range(steps):
        kb = 4096 + round(i * (total_kb - 4096) / steps / 1024) * 1024
        t0 = 0.8 + i * 0.1
        out.append(visible_between(t0, t0 + 0.1, line(term, value_col, rows["mem"], (f"{kb:0{width}d}K", AMBER))))
    out.append(appear(1.6, line(term, value_col, rows["mem"], (f"{total_kb:0{width}d}K", AMBER))))
    out.append(appear(1.68, line(term, value_col + width + 2, rows["mem"], ("OK", AMBER_HI))))

    cpu_label = boot["cpu_label"].ljust(label_w) + " :"
    out.append(appear(1.7, line(term, 0, rows["cpu"], (cpu_label, AMBER), (" " + boot["cpu"], AMBER))))

    detect = boot["detecting"]
    out.append(appear(2.0, line(term, 0, rows["detect"], (detect, AMBER))))
    for i in range(3):
        out.append(appear(2.06 + i * 0.07, line(term, len(detect) + 1 + i, rows["detect"], (".", AMBER))))

    name_w = max(len(name) for name, _ in boot["devices"]) + 3
    device_step = min(0.3, 1.2 / len(boot["devices"]))
    for i, ((name, desc), top) in enumerate(zip(boot["devices"], device_rows)):
        t = 2.3 + i * device_step
        out.append(appear(t, line(term, 0, top, (name, AMBER_HI), (" " * (name_w - len(name)) + desc, AMBER))))
        out.append(appear(t + 0.2, line(term, cols - 6, top, ("[ ", AMBER), ("OK", AMBER_HI), (" ]", AMBER))))

    load_top = rows["load"]
    out.append(appear(3.6, line(term, 0, load_top, (boot["loading"], AMBER))))
    bar_x0, bar_x1 = term.x(len(boot["loading"]) + 2), term.x(cols - 6)
    segments = 32
    seg_pitch = (bar_x1 - bar_x0) / segments
    seg_h = 14
    seg_y = term.mid(load_top) - seg_h / 2
    rng = random.Random(boot["loading"])
    gaps = [0.3 + rng.random() * (2.2 if rng.random() < 0.15 else 1.0) for _ in range(segments)]
    scale = 1.2 / sum(gaps)
    seg_times, t = [], 3.7
    for g in gaps:
        t += g * scale
        seg_times.append(t)
    empty = "".join(rect(bar_x0 + i * seg_pitch, seg_y, seg_pitch - 3, seg_h, AMBER_FAINT) for i in range(segments))
    out.append(appear(3.6, empty))
    for i, t in enumerate(seg_times):
        out.append(appear(t, rect(bar_x0 + i * seg_pitch, seg_y, seg_pitch - 3, seg_h, AMBER)))
    percent_frames = [(3.6, 0)]
    for i, t in enumerate(seg_times):
        pct = (i + 1) * 100 // segments // 10 * 10
        if pct != percent_frames[-1][1]:
            percent_frames.append((t, pct))
    for (t0, pct), (t1, _) in zip(percent_frames, percent_frames[1:]):
        out.append(visible_between(t0, t1, line(term, cols - len(f"{pct}%"), load_top, (f"{pct}%", AMBER))))
    out.append(appear(percent_frames[-1][0], line(term, cols - 4, load_top, ("100%", AMBER_HI))))

    title_px, title_cols = render_bitmap_text(boot["title"], 0, 0, pitch, dot)
    title_w = title_cols * pitch
    title_x = W / 2 - title_w / 2
    title_h = 7 * pitch

    def band(r0, r1):
        return f'<rect x="{num(title_x - 40)}" y="{num(title_top + r0 * pitch)}" width="{num(title_w + 80)}" height="{num((r1 - r0) * pitch)}"/>'

    title_defs = (
        f'<g id="title-px" transform="translate({num(title_x)} {num(title_top)})">{title_px}</g>'
        f'<linearGradient id="title-fill" gradientUnits="userSpaceOnUse" x1="0" y1="{num(title_top)}" x2="0" y2="{num(title_top + title_h)}">'
        f'<stop offset="0" stop-color="{AMBER_HI}"/><stop offset=".45" stop-color="{AMBER}"/><stop offset="1" stop-color="#f0a000"/></linearGradient>'
        f'<clipPath id="title-top">{band(0, 2)}</clipPath>'
        f'<clipPath id="title-band">{band(2, 4)}</clipPath>'
        f'<clipPath id="title-bottom">{band(4, 7)}</clipPath>'
        + raster_reveal("title-reveal", title_x - 40, title_top, title_w + 80, pitch, 7, 5.1, 5.9)
        + '<filter id="glow-strong" x="0" y="0" width="900" height="700" filterUnits="userSpaceOnUse" color-interpolation-filters="sRGB">'
        '<feGaussianBlur in="SourceGraphic" stdDeviation="2.6" result="halo"/>'
        '<feGaussianBlur in="SourceGraphic" stdDeviation="11" result="wide"/>'
        '<feComponentTransfer in="wide" result="bloom"><feFuncA type="linear" slope=".75"/></feComponentTransfer>'
        '<feMerge><feMergeNode in="bloom"/><feMergeNode in="halo"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
    )
    beam_frames_y = [(0, title_top)] + [(5.1 + (r + 1) * 0.8 / 7, title_top + (r + 1) * pitch - 1) for r in range(7)]
    beam = (
        f'<rect x="{num(title_x - 12)}" y="{num(title_top + title_h - 1)}" width="{num(title_w + 24)}" height="2" fill="{AMBER_HI}" opacity="0">'
        + discrete("y", beam_frames_y)
        + discrete("opacity", [(0, 0), (5.1, 0.9), (6.0, 0)])
        + "</rect>"
    )
    title_layer = (
        '<g filter="url(#glow-strong)">'
        '<g clip-path="url(#title-reveal)">'
        f'<use href="#title-px" class="ghost" fill="{AMBER_MID}"/>'
        '<g class="glitch">'
        '<use href="#title-px" clip-path="url(#title-top)" fill="url(#title-fill)"/>'
        '<use href="#title-px" clip-path="url(#title-band)" class="slice" fill="url(#title-fill)"/>'
        '<use href="#title-px" clip-path="url(#title-bottom)" fill="url(#title-fill)"/>'
        "</g></g>"
        f"{beam}</g>"
    )

    tagline = boot["tagline"]
    tag_parts = [(piece, AMBER_DIM if piece.strip() in (">", "//") else AMBER) for piece in re.split(r"(>\s|//)", tagline) if piece]
    tag_svg, tag_end = typed(term, (cols - len(tagline)) // 2, rows["tagline"], tag_parts, 6.0, "type-tagline", pace=0.02, jitter=0.3, cursor_from=6.0, cursor_hold=0.12)
    out.append(tag_svg)

    prompt = content["prompt"]
    prompt_t = max(7.3, tag_end + 0.25)
    out.append(appear(prompt_t, line(term, 0, rows["prompt"], (prompt, AMBER))))
    out.append(blinking_cursor(term, len(prompt), rows["prompt"], prompt_t))

    glass_r = 22
    recess = 10
    rx, ry, rw, rh = glass_x - recess, glass_y - recess, glass_w + 2 * recess, glass_h + 2 * recess
    body_x, body_y, body_w = 2, 4, W - 4
    strip_top = ry + rh
    strip_h = 74
    body_h = strip_top + strip_h - body_y
    H = body_y + body_h + 16
    screen_cx, screen_cy = glass_x + glass_w / 2, glass_y + glass_h / 2

    defs = screen_defs(glass_x, glass_y, glass_w, glass_h, glass_r, glow=2.2, bloom=7.5, bloom_alpha=0.38) + title_defs
    defs += (
        '<linearGradient id="plastic" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{PLASTIC_TOP}"/><stop offset="1" stop-color="{PLASTIC_BOTTOM}"/></linearGradient>'
        '<linearGradient id="plastic-edge" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#fff2dc" stop-opacity=".16"/><stop offset=".12" stop-color="#fff2dc" stop-opacity=".03"/>'
        '<stop offset="1" stop-color="#000" stop-opacity=".5"/></linearGradient>'
        '<linearGradient id="recess-edge" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#000" stop-opacity=".9"/><stop offset=".7" stop-color="#000" stop-opacity=".4"/>'
        '<stop offset="1" stop-color="#5a5044" stop-opacity=".7"/></linearGradient>'
        '<radialGradient id="led-halo"><stop offset="0" stop-color="#ffc640" stop-opacity=".9"/>'
        f'<stop offset=".35" stop-color="{AMBER}" stop-opacity=".35"/><stop offset="1" stop-color="{AMBER}" stop-opacity="0"/></radialGradient>'
        '<radialGradient id="flash-glow" cx=".5" cy=".5" r=".6"><stop offset="0" stop-color="#ffefc4"/>'
        f'<stop offset=".45" stop-color="{AMBER}" stop-opacity=".8"/><stop offset="1" stop-color="{AMBER}" stop-opacity=".15"/></radialGradient>'
        '<radialGradient id="knob" cx=".4" cy=".35" r=".7"><stop offset="0" stop-color="#4a4238"/><stop offset="1" stop-color="#15120f"/></radialGradient>'
        '<filter id="soft-shadow" x="-10%" y="-50%" width="120%" height="200%"><feGaussianBlur stdDeviation="7"/></filter>'
        f'<g id="bezel-label">{bezel_label(boot["bezel_label"])}</g>'
    )

    flash = (
        f'<rect class="flash" x="{num(glass_x)}" y="{num(glass_y)}" width="{num(glass_w)}" height="{num(glass_h)}" fill="url(#flash-glow)" opacity="0"/>'
    )
    screen = crt_screen(
        glass_x, glass_y, glass_w, glass_h, glass_r, "".join(out),
        layer_class="crt", layer_extra=title_layer + flash,
        above_layer=(
            f'<rect class="power-line" x="{num(glass_x)}" y="{num(screen_cy - 1.5)}" width="{num(glass_w)}" height="3" '
            f'fill="{AMBER_HI}" opacity="0" filter="url(#glow)"/>'
        ),
    )

    strip_mid = strip_top + strip_h / 2 - 2
    vents = "".join(
        rect(W / 2 - 62.5 + i * 11, strip_mid - 9, 4, 18, "#0b0907", ' rx="2"')
        + rect(W / 2 - 62.5 + i * 11, strip_mid + 8, 4, 1.2, "#3b342b", ' opacity=".8"')
        for i in range(12)
    )
    controls = []
    for i, label in enumerate(("BRT", "CON")):
        kx = 712 + i * 44
        controls.append(
            f'<circle cx="{kx}" cy="{num(strip_mid - 5)}" r="9.5" fill="#0c0a08"/>'
            f'<circle cx="{kx}" cy="{num(strip_mid - 5.5)}" r="8.5" fill="url(#knob)"/>'
            f'<path d="M{kx} {num(strip_mid - 5.5)}l{-4.5 if i else 4.5} -5.5" stroke="#7a6d5c" stroke-width="1.6" stroke-linecap="round"/>'
            + text_el(kx - 6.6, strip_mid + 17, label, 11, PLASTIC_INK)
        )
    led_x = 842
    controls.append(
        f'<circle class="led-halo" cx="{led_x}" cy="{num(strip_mid - 5)}" r="14" fill="url(#led-halo)"/>'
        f'<circle cx="{led_x}" cy="{num(strip_mid - 5)}" r="4.6" fill="#1a1100"/>'
        f'<circle cx="{led_x}" cy="{num(strip_mid - 5)}" r="3.6" fill="{AMBER}"/>'
        f'<circle cx="{led_x - 1.1}" cy="{num(strip_mid - 6.2)}" r="1.2" fill="#fff1c9" opacity=".85"/>'
        + text_el(led_x - 6.6, strip_mid + 17, "PWR", 11, PLASTIC_INK)
    )
    label_y = strip_mid + 6
    monitor = (
        f'<ellipse cx="{W / 2}" cy="{num(body_y + body_h + 2)}" rx="{num(body_w / 2 - 30)}" ry="7" fill="#000" opacity=".45" filter="url(#soft-shadow)"/>'
        f'<rect x="{body_x}" y="{body_y}" width="{body_w}" height="{num(body_h)}" rx="30" fill="url(#plastic)"/>'
        f'<rect x="{body_x + 0.75}" y="{body_y + 0.75}" width="{body_w - 1.5}" height="{num(body_h - 1.5)}" rx="29.3" fill="none" stroke="url(#plastic-edge)" stroke-width="1.5"/>'
        f'<rect x="{num(rx)}" y="{num(ry)}" width="{num(rw)}" height="{num(rh)}" rx="{glass_r + 8}" fill="#0b0906"/>'
        f'<rect x="{num(rx + 1)}" y="{num(ry + 1)}" width="{num(rw - 2)}" height="{num(rh - 2)}" rx="{glass_r + 7}" fill="none" stroke="url(#recess-edge)" stroke-width="2"/>'
        f'<rect x="{num(glass_x)}" y="{num(glass_y)}" width="{num(glass_w)}" height="{num(glass_h)}" rx="{glass_r}" fill="#0d0a06"/>'
        f"{screen}"
        f'<rect x="{num(glass_x + 0.5)}" y="{num(glass_y + 0.5)}" width="{num(glass_w - 1)}" height="{num(glass_h - 1)}" rx="{glass_r}" fill="none" stroke="#000" stroke-opacity=".8"/>'
        f'<rect x="{body_x + 30}" y="{num(strip_top + 7)}" width="{body_w - 60}" height="1" fill="#000" opacity=".35"/>'
        f'<rect x="{body_x + 30}" y="{num(strip_top + 8)}" width="{body_w - 60}" height="1" fill="#fff2dc" opacity=".05"/>'
        f'<use href="#bezel-label" x="0" y="{num(label_y - 1)}" fill="#0a0907" opacity=".9"/>'
        f'<use href="#bezel-label" x="0" y="{num(label_y + 1)}" fill="#4a4136" opacity=".6"/>'
        f'<use href="#bezel-label" x="0" y="{num(label_y)}" fill="{PLASTIC_INK}"/>'
        f"{vents}{''.join(controls)}"
    )

    extra_css = (
        f".crt{{transform-origin:{num(screen_cx)}px {num(screen_cy)}px;animation:crt-on .5s cubic-bezier(.2,.75,.3,1) both}}"
        ".flash{animation:flash .6s ease-out both}"
        f".power-line{{transform-origin:{num(screen_cx)}px {num(screen_cy)}px;animation:power-line .42s ease-out both}}"
        f".rule{{transform-origin:{num(term.x(0))}px 0;animation:rule .22s steps(10,end) .6s both}}"
        ".led-halo{animation:led 2.8s ease-in-out infinite}"
        ".glitch{animation:glitch 8s steps(1,end) 9s infinite}"
        ".slice{animation:slice 8s steps(1,end) 9s infinite}"
        ".ghost{opacity:0;animation:ghost 8s steps(1,end) 9s infinite}"
        "@keyframes crt-on{0%{transform:scale(.015,.004)}22%{transform:scale(1,.006)}100%{transform:scale(1,1)}}"
        "@keyframes flash{0%{opacity:1}15%{opacity:.9}45%{opacity:.22}100%{opacity:0}}"
        "@keyframes power-line{0%{opacity:1;transform:scaleX(.02)}25%{opacity:1;transform:scaleX(1)}55%{opacity:.7}100%{opacity:0;transform:scaleX(1)}}"
        "@keyframes rule{from{transform:scaleX(0)}to{transform:scaleX(1)}}"
        "@keyframes led{0%,100%{opacity:.55}50%{opacity:1}}"
        "@keyframes glitch{0%{transform:translate(3px,0)}.6%{transform:translate(-2px,1px)}1.2%{transform:translate(2px,0)}1.9%,100%{transform:none}}"
        "@keyframes slice{0%{transform:translate(-6px,0)}.6%{transform:translate(9px,0)}1.3%{transform:translate(-4px,0)}1.9%,100%{transform:none}}"
        "@keyframes ghost{0%{opacity:.55;transform:translate(-6px,1px)}.7%{opacity:.45;transform:translate(6px,0)}1.4%{opacity:.5;transform:translate(-3px,0)}1.9%,100%{opacity:0;transform:none}}"
    )
    devices = ", ".join(f"{name.split('/')[-1]}: {desc}" for name, desc in boot["devices"])
    desc = (
        f"Animated amber CRT monitor booting {boot['bios_left']}. Devices detected - {devices}. "
        f"Big pixel title {boot['title']}, tagline: {tagline.lstrip('> ')}"
    )
    return svg_document(W, H, f"{boot['title']} - boot screen", desc, base_css(glass_h, extra_css), defs, monitor)


def bezel_label(label):
    """Fake small caps with per-letter tracking: word initials large, the rest small."""
    big, small, tracking = 17, 13, 3.2
    out, x, start_of_word = [], 54.0, True
    for ch in label:
        if ch == " ":
            x += big * CELL_RATIO + tracking
            start_of_word = True
            continue
        size = big if start_of_word or ch.isdigit() else small
        out.append(text_el(x, 0, ch, size))
        x += size * CELL_RATIO + tracking
        start_of_word = ch == "-"
    return "".join(out)


def wrap_columns(text, width):
    return textwrap.wrap(text, width=width, break_long_words=True)


def build_sysinfo(content):
    info = content["sysinfo"]
    W = 900
    term = Term(26)
    top = TITLE_BAR + 12
    out = []
    cmd_svg, _ = command_line(term, top, content["prompt"], info["command"], 0.05, 0.2, "type-neofetch", pace=0.07)
    out.append(cmd_svg)
    top += TERM_LINE + 12

    info_col = 31
    key_w = max(len(k) for k, _ in info["fields"]) + 6
    max_value = (W - 2 * term.x0) // term.cell - info_col - key_w
    row = TERM_LINE - 1
    info_top = top
    user, _, host = info["header"].partition("@")
    out.append(appear(1.0, line(term, info_col, top, (user, AMBER_HI), ("@", AMBER), (host, AMBER_HI))))
    top += row
    out.append(appear(1.05, rect(term.x(info_col), top + 2, len(info["header"]) * term.cell, 2, AMBER_DIM)))
    top += 10
    t = 1.1
    for key, value in info["fields"]:
        leader = " " + "." * (key_w - len(key) - 2) + " "
        lines = wrap_columns(value, int(max_value))
        body = line(term, info_col, top, (key, AMBER_HI), (leader, AMBER_DIM), (lines[0], AMBER))
        for extra in lines[1:]:
            top += row
            body += line(term, info_col + key_w, top, (extra, AMBER))
        out.append(appear(t, body))
        top += row
        t += 0.1
    top += 8
    swatch_w = term.cell * 3
    for i, colour in enumerate(NEOFETCH_SWATCHES):
        out.append(appear(2.3 + i * 0.035, rect(term.x(info_col) + i * swatch_w, top, swatch_w, 16, colour)))
    info_bottom = top + 16
    top = info_bottom + 14

    prompt = content["prompt"]
    out.append(appear(2.6, line(term, 0, top, (prompt, AMBER))))
    out.append(blinking_cursor(term, len(prompt), top, 2.6))
    H = top + TERM_LINE + 14

    grid = info["robot"]
    pitch, dot = 12, 10.2
    robot_w, robot_h = len(grid[0]) * pitch, len(grid) * pitch
    robot_x = (term.x0 + term.x(info_col - 3)) / 2 - robot_w / 2
    robot_y = (info_top + info_bottom) / 2 - robot_h / 2
    layers = {
        "body": pixel_rects(grid, robot_x, robot_y, pitch, dot, {"#": AMBER, "+": AMBER_DIM, "O": AMBER_HI}),
        "lids": pixel_rects(grid, robot_x, robot_y, pitch, dot, {"o": AMBER_HI}),
        "lights": pixel_rects(grid, robot_x, robot_y, pitch, dot, {"*": AMBER_HI}),
    }
    robot_defs = raster_reveal("robot-reveal", robot_x - 4, robot_y, robot_w + 8, pitch, len(grid), 0.9, 1.9)
    out.append(
        '<g clip-path="url(#robot-reveal)">'
        f'{layers["body"]}<g class="eyelids">{layers["lids"]}</g><g class="beacon">{layers["lights"]}</g></g>'
    )

    extra_css = (
        ".eyelids{animation:eyes 4.5s steps(1,end) 3s infinite}"
        ".beacon{animation:beacon 2.2s ease-in-out infinite}"
        "@keyframes eyes{0%{opacity:1}96.6%{opacity:0}}"
        "@keyframes beacon{0%,100%{opacity:1}50%{opacity:.35}}"
    )
    fields = "; ".join(f"{k}: {v}" for k, v in info["fields"])
    return window_panel(
        W, H, f"{info['header']} - system info", f"neofetch-style system info with a pixel robot. {fields}.",
        term, content["window_title"], "".join(out), extra_css, robot_defs,
    )


def build_services(content):
    svc = content["services"]
    W = 900
    term = Term(26)
    top = TITLE_BAR + 12
    out = []
    cmd_svg, _ = command_line(term, top, content["prompt"], svc["command"], 0.05, 0.2, "type-services", pace=0.05)
    out.append(cmd_svg)
    top += TERM_LINE + 12

    units = svc["units"]
    unit_col = 3
    state_col = unit_col + max(max(len(u[0]) for u in units), len(svc["columns"][0])) + 9
    desc_col = state_col + max(max(len(u[1]) for u in units), len(svc["columns"][1])) + 6
    right = W - term.x0

    head = svc["columns"]
    out.append(appear(1.0, line(term, unit_col, top, (head[0], AMBER_DIM)) + line(term, state_col, top, (head[1], AMBER_DIM)) + line(term, desc_col, top, (head[2], AMBER_DIM))))
    top += TERM_LINE
    out.append(appear(1.0, rect(term.x0, top + 1, right - term.x0, 1, AMBER_FAINT)))
    top += 6
    row_step = min(0.12, 1.0 / len(units))
    for i, (unit, state, desc) in enumerate(units):
        running = state.upper() == "RUNNING"
        cx, cy = term.x(1) - 2, term.mid(top)
        led = (
            f'<circle class="breathe" style="animation-delay:-{num(i * 0.37)}s" cx="{num(cx)}" cy="{num(cy)}" r="11" fill="url(#led-glow)"/>'
            f'<circle cx="{num(cx)}" cy="{num(cy)}" r="4.2" fill="{AMBER if running else AMBER_FAINT}"/>'
        )
        if not running:
            led = f'<circle cx="{num(cx)}" cy="{num(cy)}" r="4.2" fill="none" stroke="{AMBER_DIM}" stroke-width="1.4"/>'
        row_svg = (
            led
            + line(term, unit_col, top, (unit, AMBER))
            + line(term, state_col, top, (state, AMBER_HI if running else AMBER_DIM))
            + line(term, desc_col, top, (desc, AMBER))
        )
        out.append(appear(1.1 + i * row_step, row_svg))
        top += TERM_LINE
    summary_t = 1.1 + len(units) * row_step + 0.1
    top += 4
    out.append(appear(summary_t, rect(term.x0, top, right - term.x0, 1, AMBER_FAINT)))
    top += 6
    running = sum(1 for u in units if u[1].upper() == "RUNNING")
    failed = sum(1 for u in units if u[1].upper() == "FAILED")
    summary = f"{len(units)} units loaded, {running} running, {failed} failed"
    out.append(appear(summary_t + 0.05, line(term, unit_col, top, (summary, AMBER_DIM))))
    H = top + TERM_LINE + 14

    defs = (
        '<radialGradient id="led-glow"><stop offset="0" stop-color="#ffc640" stop-opacity=".95"/>'
        f'<stop offset=".4" stop-color="{AMBER}" stop-opacity=".35"/><stop offset="1" stop-color="{AMBER}" stop-opacity="0"/></radialGradient>'
    )
    extra_css = ".breathe{opacity:.6;animation:breathe 2.4s ease-in-out infinite}@keyframes breathe{0%,100%{opacity:.25}50%{opacity:.9}}"
    listing = "; ".join(f"{u[0]} {u[1].lower()} ({u[2]})" for u in units)
    return window_panel(
        W, H, "services --status", f"Terminal table of running services: {listing}. {summary}.",
        term, content["window_title"], "".join(out), extra_css, defs,
    )


CARD_W = 440
CARD_H = 264


def check_fits(name, bottom, height, pad=10):
    if bottom + pad > height:
        raise ValueError(f"{name}: content ends at {bottom:.0f}px but the panel is {height}px tall")


def qr_path(matrix, x, y, module):
    runs = []
    for r, row in enumerate(matrix):
        for m in re.finditer("1+", row):
            width = len(m.group()) * module
            runs.append(f"M{num(x + m.start() * module)} {num(y + r * module)}h{num(width)}v{num(module)}h{num(-width)}z")
    return "".join(runs)


def build_contact_card(content):
    contact = content["contact"]
    term = Term(24)
    top = TITLE_BAR + 12
    out = []
    cmd_svg, cmd_end = command_line(term, top, content["prompt"], contact["command"], 0.05, 0.2, "type-contact", pace=0.06)
    out.append(cmd_svg)
    top += TERM_LINE + 10

    matrix = contact["qr"]["matrix"]
    quiet = 4
    span = len(matrix) + 2 * quiet
    # whole hundredths keep every module edge on the same coordinates, so rows never seam
    module = int((CARD_H - 12 - top) / span * 100) / 100
    plate = module * span
    plate_x, plate_y = term.x0, top
    reveal_t = cmd_end + 0.25
    steps = 11
    margin = 16
    qr_defs = (
        raster_reveal("qr-reveal", plate_x - margin, plate_y - margin, plate + 2 * margin, (plate + 2 * margin) / steps, steps, reveal_t, reveal_t + 0.6)
        + '<filter id="qr-halo" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="7"/></filter>'
    )
    plate_box = f'x="{num(plate_x)}" y="{num(plate_y)}" width="{num(plate)}" height="{num(plate)}" rx="6"'
    overlay = (
        '<g clip-path="url(#qr-reveal)">'
        f'<rect class="qr-halo" {plate_box} fill="{AMBER}" filter="url(#qr-halo)"/>'
        f'<rect {plate_box} fill="{AMBER}"/>'
        f'<path d="{qr_path(matrix, plate_x + quiet * module, plate_y + quiet * module, module)}" fill="{BG}" shape-rendering="crispEdges"/>'
        "</g>"
    )

    side = Term(plate_x + plate + 18)
    handle_term = Term(side.x0, 22, 26)
    y = plate_y + 2
    t = reveal_t + 0.7
    for key, colour in (("telegram", AMBER_HI), ("linkedin", AMBER)):
        link = contact[key]
        out.append(appear(t, line(side, 0, y, (link["label"], AMBER_DIM))))
        y += TERM_LINE - 2
        out.append(appear(t + 0.08, line(handle_term, 0, y, (link["handle"], colour))))
        y += handle_term.line + 14
        t += 0.2
    cta = contact["call_to_action"]
    cta_top = plate_y + plate - TERM_LINE
    out.append(appear(t + 0.1, line(side, 0, cta_top, (cta, AMBER_HI))))
    out.append(blinking_cursor(side, len(cta), cta_top, t + 0.1))
    check_fits("contact card", cta_top + TERM_LINE, CARD_H)

    extra_css = ".qr-halo{opacity:.5;animation:breathe 3.2s ease-in-out infinite}@keyframes breathe{0%,100%{opacity:.35}50%{opacity:.6}}"
    tg, li = contact["telegram"], contact["linkedin"]
    desc = f"Contact card with a QR code for {contact['qr']['data']}. Telegram {tg['handle']}, LinkedIn {li['handle']}."
    return window_panel(
        CARD_W, CARD_H, "contact --list", desc, term, content["window_title"], "".join(out),
        extra_css, qr_defs, overlay=overlay,
    )


def build_project_classified(content):
    proj = content["projects"]["classified"]
    term = Term(24)
    cols = int((CARD_W - 2 * term.x0) // term.cell)
    top = TITLE_BAR + 12
    out = []
    cmd_svg, cmd_end = command_line(term, top, content["projects"]["prompt"], proj["command"], 0.05, 0.2, "type-cd", pace=0.06)
    out.append(cmd_svg)
    top += TERM_LINE + 10

    banner = proj["banner"]
    plate_term = Term(term.x0 + 14, 30, 40)
    plate_w = len(banner) * plate_term.cell + 28
    plate_t = cmd_end + 0.3
    plate = (
        f'<rect x="{num(term.x0 + 1)}" y="{num(top + 1)}" width="{num(plate_w - 2)}" height="38" fill="none" stroke="{AMBER}" stroke-width="2"/>'
        + line(plate_term, 0, top, (banner, AMBER))
        + '<g class="inverse">'
        + rect(term.x0, top, plate_w, 40, AMBER)
        + line(plate_term, 0, top, (banner, BG))
        + "</g>"
    )
    out.append(appear(plate_t, plate))
    top += 40 + 10

    out.append(appear(plate_t + 0.3, line(term, 0, top, (f"{proj['private_repos']} private repos", AMBER))))
    top += TERM_LINE + 4

    rng = random.Random(banner)
    bar_t = plate_t + 0.5
    widths = [cols - 4, cols - 9, cols - 2, cols // 2]
    for i, limit in enumerate(widths):
        col = 0
        words = []
        while col < limit - 3:
            n = min(rng.randint(2, 9), limit - col)
            words.append((col, n))
            col += n + 1
        bars = "".join(
            f'<rect class="redact" style="animation-delay:{num(bar_t + i * 0.14 + j * 0.03)}s" x="{num(term.x(c))}" y="{num(top + 3)}" '
            f'width="{num(n * term.cell - 2)}" height="11" fill="{AMBER_MID}"/>'
            for j, (c, n) in enumerate(words)
        )
        out.append(bars)
        top += 16
    top += 6

    out.append(appear(bar_t + 0.85, line(term, 0, top, (proj["note"], AMBER_DIM))))
    check_fits("classified card", top + TERM_LINE, CARD_H)

    extra_css = (
        ".inverse{animation:inverse 1.6s steps(1,end) infinite}"
        ".redact{transform-box:fill-box;transform-origin:0 50%;animation:redact .14s steps(6,end) both}"
        "@keyframes inverse{0%{opacity:1}62%{opacity:0}}"
        "@keyframes redact{from{transform:scaleX(0)}to{transform:scaleX(1)}}"
    )
    desc = f"{proj['private_repos']} private repositories behind an ACCESS DENIED screen with redacted lines. {proj['note']}."
    return window_panel(
        CARD_W, CARD_H, "classified projects", desc,
        term, content["window_title"], "".join(out), extra_css,
    )


def build_footer(content):
    foot = content["footer"]
    W = 900
    term = Term(26)
    top = TITLE_BAR + 16
    out = []
    cmd_svg, cmd_end = command_line(term, top, content["prompt"], foot["command"], 0.05, 0.25, "type-exit", pace=0.11)
    out.append(cmd_svg)
    top += TERM_LINE
    out.append(appear(cmd_end + 0.35, line(term, 0, top, (foot["farewell"], AMBER_DIM))))
    top += TERM_LINE
    out.append(appear(cmd_end + 0.75, line(term, 0, top, (foot["closing"], AMBER_HI))))
    out.append(blinking_cursor(term, len(foot["closing"]), top, cmd_end + 0.75))
    H = top + TERM_LINE + 22
    return window_panel(
        W, H, "exit", f"{foot['farewell']} {foot['closing']}",
        term, content["window_title"], "".join(out),
    )


def load_contributions():
    raw = json.loads(CONTRIBUTIONS_PATH.read_text(encoding="utf-8"))
    weeks = [[{"date": d, "weekday": wd, "count": n, "level": lv} for d, wd, n, lv in week] for week in raw["weeks"]]
    return raw["total"], weeks


def save_contributions(login, total, weeks):
    rows = ",\n".join("    " + json.dumps(week, separators=(",", ":")) for week in weeks)
    CONTRIBUTIONS_PATH.write_text(
        f'{{\n  "login": {json.dumps(login)},\n  "total": {total},\n  "weeks": [\n{rows}\n  ]\n}}\n',
        encoding="utf-8",
        newline="\n",
    )


def github_token():
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    return subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()


def refresh_contributions(login):
    body = json.dumps({"query": CONTRIBUTIONS_QUERY, "variables": {"login": login}}).encode("utf-8")
    request = urllib.request.Request(
        GRAPHQL_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"bearer {github_token()}",
            "Content-Type": "application/json",
            "User-Agent": f"{login}-profile-builder",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        reply = json.loads(response.read().decode("utf-8"))
    user = (reply.get("data") or {}).get("user")
    if reply.get("errors") or not user:
        raise RuntimeError(f"GitHub GraphQL request failed: {reply.get('errors') or reply}")
    calendar = user["contributionsCollection"]["contributionCalendar"]
    weeks = [
        [[d["date"], d["weekday"], d["contributionCount"], d["contributionLevel"]] for d in week["contributionDays"]]
        for week in calendar["weeks"]
    ]
    save_contributions(login, calendar["totalContributions"], weeks)
    return calendar["totalContributions"]


def short_date(iso):
    day = date.fromisoformat(iso)
    return f"{MONTHS[day.month - 1]} {day.day}"


def streaks(days):
    longest = run = 0
    for day in days:
        run = run + 1 if day["count"] else 0
        longest = max(longest, run)
    # today is still in progress, so an empty today does not break the current streak
    tail = days if days[-1]["count"] else days[:-1]
    current = 0
    for day in reversed(tail):
        if not day["count"]:
            break
        current += 1
    return current, longest


def month_label_columns(weeks):
    starts = [i for i in range(len(weeks)) if i == 0 or weeks[i][0]["date"][:7] != weeks[i - 1][0]["date"][:7]]
    return [
        col for k, col in enumerate(starts)
        if (k + 1 == len(starts) or starts[k + 1] - col >= 3) and len(weeks) - col >= 2
    ]


def heat_cell(x, y, size, level):
    if level == "NONE":
        return rect(x + 0.4, y + 0.4, size - 0.8, size - 0.8, HEATMAP_LEVELS["NONE"], f' rx="2" stroke="{AMBER_FAINT}" stroke-width=".8"')
    return rect(x, y, size, size, HEATMAP_LEVELS.get(level, AMBER_FAINT), ' rx="2"')


def build_contributions(content, total, weeks):
    heat = content["contributions"]
    W = 900
    term = Term(26)
    small = Term(term.x0, 16, 18)
    top = TITLE_BAR + 12
    out = []
    cmd_svg, cmd_end = command_line(term, top, content["prompt"], heat["command"], 0.05, 0.2, "type-heatmap", pace=0.03)
    out.append(cmd_svg)
    top += TERM_LINE + 10

    gap = 3
    grid_x = term.x0 + 4 * small.cell + 8
    pitch = (W - term.x0 - grid_x + gap) / len(weeks)
    size = pitch - gap
    months_top = top
    grid_y = top + small.line + 6
    grid_h = 7 * pitch - gap
    t0, sweep = cmd_end + 0.25, 1.1
    col_t = [t0 + sweep * i / max(len(weeks) - 1, 1) for i in range(len(weeks))]
    t_end = col_t[-1]

    for weekday, label in enumerate(heat["weekday_labels"]):
        if label:
            row_top = grid_y + weekday * pitch + size / 2 - small.line / 2
            out.append(appear(t0, line(small, 0, row_top, (label, AMBER_DIM))))

    labelled = set(month_label_columns(weeks))
    halos, columns = [], []
    for i, week in enumerate(weeks):
        x = grid_x + i * pitch
        cells = []
        for day in week:
            y = grid_y + day["weekday"] * pitch
            cells.append(heat_cell(x, y, size, day["level"]))
            if day["level"] == "FOURTH_QUARTILE":
                halos.append(appear(col_t[i], rect(x - 1, y - 1, size + 2, size + 2, AMBER)))
        if i in labelled:
            month = MONTHS[int(week[0]["date"][5:7]) - 1]
            cells.append(text_el(x, small.baseline(months_top), month, small.size, AMBER_DIM))
        columns.append(appear(col_t[i], "".join(cells)))
    out.append(f'<g filter="url(#hot)" opacity=".8">{"".join(halos)}</g>')
    out.extend(columns)

    head_x = [grid_x + i * pitch + size + 1 for i in range(len(weeks))]
    trail_w = 28
    shown = discrete("opacity", [(0, 0), (t0, 1), (t_end + 0.2, 0)])
    out.append(
        f'<rect x="{num(head_x[-1] - trail_w)}" y="{num(grid_y - 5)}" width="{trail_w}" height="{num(grid_h + 10)}" fill="url(#scan-trail)" opacity="0">'
        + discrete("x", [(0, head_x[0] - trail_w)] + [(t, hx - trail_w) for t, hx in zip(col_t, head_x)])
        + shown
        + "</rect>"
        f'<rect x="{num(head_x[-1])}" y="{num(grid_y - 5)}" width="2" height="{num(grid_h + 10)}" fill="{AMBER_HI}" opacity="0">'
        + discrete("x", [(0, head_x[0])] + list(zip(col_t, head_x)))
        + shown
        + "</rect>"
    )

    today = weeks[-1][-1]
    today_x, today_y = grid_x + (len(weeks) - 1) * pitch, grid_y + today["weekday"] * pitch
    out.append(appear(t_end + 0.25, rect(today_x, today_y, size, size, AMBER_HI, ' rx="2" class="today"')))

    top = round(grid_y + grid_h + 14)
    out.append(appear(t_end + 0.15, line(term, 0, top, (heat["total_line"].format(total=f"{total:,}"), AMBER_HI))))
    mid = term.mid(top)
    text_y = mid + 0.3 * small.size
    less, more = heat["legend"]
    x = W - term.x0 - len(more) * small.cell
    legend = [text_el(x, text_y, more, small.size, AMBER_DIM)]
    x -= 6 + len(HEATMAP_LEVELS) * pitch - gap
    legend += [heat_cell(x + k * pitch, mid - size / 2, size, level) for k, level in enumerate(HEATMAP_LEVELS)]
    x -= 6 + len(less) * small.cell
    legend.append(text_el(x, text_y, less, small.size, AMBER_DIM))
    out.append(appear(t_end + 0.15, "".join(legend)))

    days = [day for week in weeks for day in week]
    best = max(days, key=lambda day: (day["count"], day["date"]))
    current, longest = streaks(days)
    stats = heat["stats_line"].format(
        best_count=best["count"], best_date=short_date(best["date"]), current_streak=current, longest_streak=longest,
    )
    top += TERM_LINE
    out.append(appear(t_end + 0.3, line(term, 0, top, (stats, AMBER_DIM))))
    H = top + TERM_LINE + 14

    defs = (
        f'<filter id="hot" x="0" y="0" width="{W}" height="{num(H)}" filterUnits="userSpaceOnUse"><feGaussianBlur stdDeviation="3.5"/></filter>'
        '<linearGradient id="scan-trail" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{AMBER}" stop-opacity="0"/><stop offset="1" stop-color="{AMBER}" stop-opacity=".3"/></linearGradient>'
    )
    extra_css = ".today{animation:blink 1.7s step-end infinite}"
    desc = f"Amber heatmap of GitHub contributions over the last year: {total:,} contributions. {' '.join(stats.split())}."
    return window_panel(W, H, "contribution heatmap", desc, term, content["window_title"], "".join(out), extra_css, defs)


def build_button(link, icon, phase=0.0):
    W, H = 224, 56
    x, y, w, h, r = 8, 8, 208, 40, 9
    size = 22
    mid = y + h / 2
    pitch = 2.4
    box = f'x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}"'
    body = (
        f'<rect class="breathe" style="animation-delay:-{num(phase)}s" {box} fill="none" stroke="{AMBER}" stroke-width="3" filter="url(#key-glow)"/>'
        f'<rect {box} fill="url(#key-face)"/>'
        f'<rect {box} fill="url(#scanlines)"/>'
        + rect(x + r, y + 1.5, w - 2 * r, 1, AMBER_HI, ' opacity=".16"')
        + f'<rect {box} fill="none" stroke="{AMBER}" stroke-width="1.4"/>'
        '<g filter="url(#key-text)">'
        + pixel_rects(icon, x + 14, mid - len(icon) * pitch / 2, pitch, pitch, {"#": AMBER})
        + text_el(x + 46, mid + 0.3 * size, link["label"], size, AMBER_HI)
        + text_el(x + w - 14 - size * CELL_RATIO, mid + 0.3 * size, ">", size, AMBER_MID)
        + "</g>"
    )
    defs = (
        '<linearGradient id="key-face" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#1e1300"/><stop offset="1" stop-color="#0a0600"/></linearGradient>'
        '<pattern id="scanlines" width="8" height="3" patternUnits="userSpaceOnUse">'
        '<rect width="8" height="1" fill="#000" opacity=".22"/></pattern>'
        '<filter id="key-glow" x="-20%" y="-60%" width="140%" height="220%"><feGaussianBlur stdDeviation="3.5"/></filter>'
        '<filter id="key-text" x="-10%" y="-40%" width="120%" height="180%" color-interpolation-filters="sRGB">'
        '<feGaussianBlur in="SourceGraphic" stdDeviation="1.4" result="halo"/>'
        '<feMerge><feMergeNode in="halo"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
    )
    css = (
        font_css()
        + ".breathe{opacity:.6;animation:breathe 3.2s ease-in-out infinite}"
        "@keyframes breathe{0%,100%{opacity:.3}50%{opacity:.95}}"
        "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
    )
    desc = f"{link['label'].title()} button: {link['handle']} ({link['url']})"
    return svg_document(W, H, link["label"].title(), desc, css, defs, body)


def main():
    parser = argparse.ArgumentParser(description="Render the amber CRT profile SVGs into assets/.")
    parser.add_argument(
        "--refresh-contributions",
        action="store_true",
        help="re-fetch the contribution calendar from the GitHub GraphQL API into scripts/contributions.json first",
    )
    args = parser.parse_args()

    content = json.loads(CONTENT_PATH.read_text(encoding="utf-8"))
    if args.refresh_contributions:
        fetched = refresh_contributions(content["github_login"])
        print(f"{CONTRIBUTIONS_PATH.relative_to(REPO_ROOT)}  {fetched:,} contributions")
    total, weeks = load_contributions()
    contact = content["contact"]
    outputs = {
        "boot.svg": build_boot(content),
        "sysinfo.svg": build_sysinfo(content),
        "services.svg": build_services(content),
        "contributions.svg": build_contributions(content, total, weeks),
        "contact_telegram.svg": build_contact_card(content),
        "project_classified.svg": build_project_classified(content),
        "button_telegram.svg": build_button(contact["telegram"], PAPER_PLANE_ICON),
        "button_linkedin.svg": build_button(contact["linkedin"], LINKEDIN_ICON, phase=1.6),
        "footer.svg": build_footer(content),
    }
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    for name, svg in outputs.items():
        path = ASSETS_DIR / name
        path.write_text(svg, encoding="utf-8", newline="\n")
        print(f"{path.relative_to(REPO_ROOT)}  {path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
