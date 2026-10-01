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


def _delta_fields(aggs):
    b = sum(a.get("obj_better", 0) for a in aggs)
    e = sum(a.get("obj_equal", 0) for a in aggs)
    w = sum(a.get("obj_worse", 0) for a in aggs)
    total = b + e + w
    weighted = sum(a["mean_obj_delta"] * (a.get("obj_better", 0) + a.get("obj_equal", 0)
                                          + a.get("obj_worse", 0))
                   for a in aggs if a.get("mean_obj_delta") is not None)
    return {"obj_better": b, "obj_equal": e, "obj_worse": w,
            "mean_obj_delta": round(weighted / total, 5) if total else None}


def merge_obj_delta(summary, shard_summaries):
    """Overlay the objective-difference aggregate, summed over the shards."""
    for split, s in summary.items():
        for level in ("by_family", "by_area"):
            for g, agg in s.get(level, {}).items():
                agg.update(_delta_fields([ss[split][level][g] for ss in shard_summaries
                                          if g in ss.get(split, {}).get(level, {})]))
        if s.get("overall"):
            s["overall"].update(_delta_fields([ss[split]["overall"] for ss in shard_summaries
                                               if ss.get(split, {}).get("overall")]))


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
    # Everything except the objective difference recomputes from the rows. The
    # per-instance difference is deliberately absent from public rows (it is a
    # channel an adversarial solver could use to read back stored objectives), so
    # its aggregate is carried over from the shards instead.
    base["summary"] = summarize(base["rows"], base["time_limit"])
    merge_obj_delta(base["summary"], [p["summary"] for p in parts if p.get("summary")])
    Path(args.out).write_text(json.dumps(base, indent=1))
    print(f"{len(base['rows'])} rows from {len(parts)} shards -> {args.out}")


if __name__ == "__main__":
    main()
