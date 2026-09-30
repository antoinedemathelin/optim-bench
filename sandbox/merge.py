#!/usr/bin/env python3
"""Merge shard records written by evaluate.py --shard i/N into one record.

    python sandbox/merge.py history/v0.3.0.shard*.json --out history/v0.3.0.json
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate import summarize  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("shards", nargs="+")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    parts = [json.loads(Path(p).read_text()) for p in args.shards]
    base = dict(parts[0])
    base["shard"] = f"merged:{len(parts)}"
    base["rows"] = [r for p in parts for r in p.get("rows", [])]
    base["rows"].sort(key=lambda r: (r["track"], r["family"], r["name"]))
    base["wall_minutes"] = max(p.get("wall_minutes", 0) for p in parts)
    errors = [p["error"] for p in parts if p.get("status") != "ok"]
    base["status"] = "ok" if not errors else "error"
    if errors:
        base["error"] = " | ".join(errors)
    base["summary"] = summarize(base["rows"], base["time_limit"])
    Path(args.out).write_text(json.dumps(base, indent=1))
    print(f"{len(base['rows'])} rows from {len(parts)} shards -> {args.out}")


if __name__ == "__main__":
    main()
