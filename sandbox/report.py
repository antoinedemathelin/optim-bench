#!/usr/bin/env python3
"""Render the feedback report (Markdown) for one evaluation record, next to the
HiGHS baseline record from the same hardware.

    python sandbox/report.py history/v0.3.0.json --baseline history/baseline.json [--holdout]

Only per-family / per-area aggregates of the *feedback* split are shown (plus
overall numbers); instance names never appear. --holdout adds the holdout
tables (for the dashboard, not for the solver author).
"""
import argparse
import json
from pathlib import Path


def fmt_gap(g):
    return "-" if g is None else f"{g:.1%}"


def table(agg, base_agg, key_label):
    lines = [f"| {key_label} | n | solved | no solution | wrong | SGM-10 (s) | end-gap unsolved | HiGHS solved | HiGHS SGM-10 |",
             "|---|---|---|---|---|---|---|---|---|"]
    for g, a in agg.items():
        b = (base_agg or {}).get(g)
        wrong = f"{a['wrong']} ({', '.join(a['wrong_kinds'])})" if a["wrong"] else "0"
        lines.append(f"| {g} | {a['n']} | {a['solved']} | {a.get('no_solution', 0)} | {wrong} | {a['sgm10']} | {fmt_gap(a['mean_gap_unsolved'])} | "
                     f"{b['solved'] if b else '-'} | {b['sgm10'] if b else '-'} |")
    return lines


def render(rec, base=None, holdout=False):
    if rec.get("status") != "ok":
        return (f"# optim-bench: evaluation of `{rec.get('ref')}` failed\n\n"
                f"```\n{rec.get('error', 'unknown error')}\n```\n\n"
                f"Build/run details: {json.dumps(rec.get('build', {}), indent=1)[:1500]}\n")
    s = rec["summary"]
    solver = rec.get("solver") or {}
    lines = [f"# optim-bench report: `{rec['ref']}` ({rec.get('sha', '')[:10]})", "",
             f"- solver: {solver.get('name', '?')} {solver.get('version', '')}".rstrip(),
             f"- date: {rec['date']}, mode `{rec['mode']}` ({rec['time_limit']:.0f} s per instance, "
             f"{rec['threads']} threads), evaluation wall {rec.get('wall_minutes', '?')} min",
             f"- hardware: {rec['hardware']}; isolation: {rec.get('isolation', '?')}"]
    if base:
        lines.append(f"- baseline: HiGHS record `{base['ref']}` from {base['date'][:10]} on the same hardware")
    for split in (["feedback", "holdout"] if holdout else ["feedback"]):
        o = s[split]["overall"]
        if not o:
            lines += ["", f"## {split} set — no instances in this run"]
            continue
        bo = base["summary"][split]["overall"] if base and base["summary"][split].get("overall") else None
        lines += ["", f"## {split} set — {o['n']} instances", "",
                  f"**Solved {o['solved']}/{o['n']}, wrong answers {o['wrong']}, SGM-10 {o['sgm10']} s"
                  + (f" (HiGHS: {bo['solved']}/{bo['n']}, {bo['wrong']}, {bo['sgm10']} s)" if bo else "") + "**", ""]
        if o["wrong"]:
            lines += [f"Wrong-answer categories: {', '.join(o['wrong_kinds'])}. "
                      "A wrong answer is an infeasible or misreported solution, a false optimality claim, "
                      "or a bound that excludes the true optimum — see the contract, section 4.", ""]
        lines += ["### By application area", ""] + table(s[split]["by_area"], base["summary"][split]["by_area"] if base else None, "area")
        lines += ["", "### By family", ""] + table(s[split]["by_family"], base["summary"][split]["by_family"] if base else None, "family")
    lines += ["", "Scoring: SGM-10 = shifted geometric mean of wall time (10 s shift), unsolved counted at the "
              "limit; an instance is solved only if the returned solution is verified feasible and within 1e-4 "
              "of the reference optimum. 'no solution' counts unsolved instances where no feasible point was "
              "returned at all; 'end-gap' averages |objective - bound| / |objective| over the unsolved instances "
              "that did return one. Lower SGM-10 is better. Wrong answers must be zero before speed matters."]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--baseline")
    ap.add_argument("--holdout", action="store_true")
    ap.add_argument("--out")
    args = ap.parse_args()
    rec = json.loads(Path(args.record).read_text())
    base = json.loads(Path(args.baseline).read_text()) if args.baseline and Path(args.baseline).exists() else None
    md = render(rec, base, args.holdout)
    if args.out:
        Path(args.out).write_text(md)
    else:
        print(md)


if __name__ == "__main__":
    main()
