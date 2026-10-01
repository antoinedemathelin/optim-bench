#!/usr/bin/env python3
"""Build history/index.json (what the dashboard reads) from history/*.json."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def compact(rec):
    def split(s):
        if not s or not s.get("overall"):
            return None
        o = s["overall"]
        def group(v):
            return {"n": v["n"], "solved": v["solved"], "wrong": v["wrong"], "sgm10": v["sgm10"],
                    "mean_obj_delta": v.get("mean_obj_delta"),
                    "obj_better": v.get("obj_better"), "obj_worse": v.get("obj_worse")}
        return dict(group(o), wrong_kinds=o.get("wrong_kinds", []),
                    by_area={k: group(v) for k, v in s["by_area"].items()},
                    by_family={k: group(v) for k, v in s["by_family"].items()})
    summ = rec.get("summary") or {}
    return {"ref": rec["ref"], "sha": rec.get("sha", ""), "date": rec["date"], "status": rec.get("status"),
            "error": rec.get("error"), "solver": rec.get("solver"), "mode": rec.get("mode"),
            "time_limit": rec.get("time_limit"), "hardware": rec.get("hardware"),
            "wall_minutes": rec.get("wall_minutes"), "report": f"{rec['ref']}.md",
            "feedback": split(summ.get("feedback")), "holdout": split(summ.get("holdout"))}


def main():
    hist = ROOT / "history"
    recs = []
    baseline = None
    for p in sorted(hist.glob("*.json")):
        if p.name == "index.json" or ".shard" in p.name:
            continue
        rec = json.loads(p.read_text())
        c = compact(rec)
        if p.stem == "baseline":
            baseline = c
        else:
            recs.append(c)
    recs.sort(key=lambda r: r["date"])
    (hist / "index.json").write_text(json.dumps({"baseline": baseline, "evaluations": recs}, indent=1))
    print(f"index: {len(recs)} evaluations, baseline={'yes' if baseline else 'no'}")


if __name__ == "__main__":
    main()
