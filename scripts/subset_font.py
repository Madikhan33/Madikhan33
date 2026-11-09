import argparse
import json
import sys
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

CONTENT_PATH = Path(__file__).resolve().parent / "profile_content.json"
PRINTABLE_ASCII = {chr(cp) for cp in range(0x20, 0x7F)}


def collect_strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for value in node.values():
            yield from collect_strings(value)
    elif isinstance(node, list):
        for item in node:
            yield from collect_strings(item)


def main():
    parser = argparse.ArgumentParser(description="Subset VT323 to the characters the profile actually renders.")
    parser.add_argument("src", type=Path, help="source .ttf")
    parser.add_argument("out", type=Path, help="output .woff2")
    parser.add_argument("--content", type=Path, default=CONTENT_PATH)
    args = parser.parse_args()

    content = json.loads(args.content.read_text(encoding="utf-8"))
    used = {ch for s in collect_strings(content) for ch in s}
    cmap = TTFont(args.src).getBestCmap()

    extra = sorted(ch for ch in used - PRINTABLE_ASCII if ch.isprintable())
    missing = [ch for ch in extra if ord(ch) not in cmap]
    kept = [ch for ch in extra if ord(ch) in cmap]
    if missing:
        print("WARNING: not in font cmap, will render with fallback: " + " ".join(f"{c!r} U+{ord(c):04X}" for c in missing), file=sys.stderr)

    unicodes = sorted({ord(c) for c in PRINTABLE_ASCII} | {ord(c) for c in kept})
    options = subset.Options()
    options.flavor = "woff2"
    options.layout_features = []
    options.name_IDs = [0, 1, 2]
    options.name_languages = [0x409]
    options.notdef_outline = True
    options.hinting = False
    options.desubroutinize = True

    font = subset.load_font(str(args.src), options)
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=unicodes)
    subsetter.subset(font)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    subset.save_font(font, str(args.out), options)

    print(f"{args.out}: {args.out.stat().st_size} bytes, {len(unicodes)} codepoints, extra: {' '.join(kept) or '-'}")


if __name__ == "__main__":
    main()
