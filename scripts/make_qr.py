import json
from pathlib import Path

import segno

CONTENT_PATH = Path(__file__).resolve().parent / "profile_content.json"
ERROR_LEVEL = "m"
INLINE_LIMIT = 100


def dump_json(value, depth=0):
    """Pretty JSON that keeps short lists of scalars on one line, like the hand-written file."""
    pad, inner = "  " * depth, "  " * (depth + 1)
    if isinstance(value, dict):
        items = [f"{inner}{json.dumps(k, ensure_ascii=False)}: {dump_json(v, depth + 1)}" for k, v in value.items()]
        return "{\n" + ",\n".join(items) + f"\n{pad}}}"
    if isinstance(value, list):
        inline = json.dumps(value, ensure_ascii=False)
        if all(not isinstance(v, (dict, list)) for v in value) and len(inline) <= INLINE_LIMIT:
            return inline
        return "[\n" + ",\n".join(f"{inner}{dump_json(v, depth + 1)}" for v in value) + f"\n{pad}]"
    return json.dumps(value, ensure_ascii=False)


def main():
    content = json.loads(CONTENT_PATH.read_text(encoding="utf-8"))
    url = content["contact"]["telegram"]["url"]
    qr = segno.make(url, error=ERROR_LEVEL, micro=False, boost_error=False)
    content["contact"]["qr"] = {
        "data": url,
        "version": qr.version,
        "error": qr.error,
        "matrix": ["".join(str(bit) for bit in row) for row in qr.matrix],
    }
    CONTENT_PATH.write_text(dump_json(content) + "\n", encoding="utf-8", newline="\n")
    print(f"QR for {url}: version {qr.version}, error level {qr.error}, {len(qr.matrix)}x{len(qr.matrix)} modules")


if __name__ == "__main__":
    main()
