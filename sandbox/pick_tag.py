#!/usr/bin/env python3
"""Decide what the next evaluation run should evaluate.

    python sandbox/pick_tag.py --agent-repo org/solver [--ref v0.3.0] [--baseline]

Prints KEY=VALUE lines (and appends them to $GITHUB_OUTPUT when set):
  kind=baseline|tag|none   repo=<clone url or local path>   ref=<tag>
Rules: if history/baseline.json is missing, the HiGHS baseline solver is
evaluated first (its numbers must come from the same hardware). Otherwise the
oldest solver-repo tag (by commit date) with no history/<tag>.json is chosen,
so a burst of tags is evaluated in order across scheduled runs. Tags are read
with `gh api`, which needs GH_TOKEN with read access to the solver repo.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def gh(path):
    r = subprocess.run(["gh", "api", "--paginate", path], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"gh api {path} failed: {r.stderr.strip()}")
    # --paginate concatenates JSON arrays; normalise
    txt = r.stdout.strip().replace("][", ",")
    return json.loads(txt)


def emit(**kv):
    lines = [f"{k}={v}" for k, v in kv.items()]
    print("\n".join(lines))
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent-repo", required=True, help="owner/name of the solver repository")
    ap.add_argument("--ref", default="", help="force this tag")
    ap.add_argument("--baseline", action="store_true", help="force a baseline evaluation")
    args = ap.parse_args()
    hist = ROOT / "history"
    clone_url = f"https://github.com/{args.agent_repo}.git"
    base = hist / "baseline.json"
    base_ok = base.exists() and json.loads(base.read_text()).get("status") == "ok"
    if args.baseline or not base_ok:
        emit(kind="baseline", repo="sandbox/baseline-solver", ref="baseline")
        return
    if args.ref:
        emit(kind="tag", repo=clone_url, ref=args.ref)
        return
    done = {p.stem for p in hist.glob("*.json") if ".shard" not in p.name}
    tags = gh(f"repos/{args.agent_repo}/tags")
    pending = [t for t in tags if t["name"] not in done]
    if not pending:
        emit(kind="none", repo="", ref="")
        return
    dated = []
    for t in pending:
        c = gh(f"repos/{args.agent_repo}/commits/{t['commit']['sha']}")
        dated.append((c["commit"]["committer"]["date"], t["name"]))
    dated.sort()
    emit(kind="tag", repo=clone_url, ref=dated[0][1])


if __name__ == "__main__":
    main()
