#!/usr/bin/env python3
"""Sandboxed evaluation of an external solver repository against the suite.

    python sandbox/evaluate.py --repo https://github.com/org/solver --ref v0.3.0
    python sandbox/evaluate.py --repo ../my-solver --ref local --mode quick --families set-covering
    python sandbox/evaluate.py --repo sandbox/baseline-solver --ref baseline --shard 0/4

Steps: checkout the tag into a scratch dir -> fresh venv -> run `build` from
bench.yaml (network allowed, 20 min cap) -> for every instance run `run` with a
minimal environment, no network where the OS allows it (`unshare -n` via sudo),
and a hard kill 10 s past the time limit -> verify every result independently
(sandbox/verify.py) -> write one JSON record (history/<tag>.json or --out).

Shards (`--shard i/N`) take every N-th instance so CI can run in parallel;
sandbox/merge.py joins the shard files. The record contains per-instance rows
and per-family / per-area aggregates for the feedback and holdout splits.
"""
import argparse
import datetime
import json
import math
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "sandbox"))
import verify  # noqa: E402

MODES = {"quick": 60, "default": 300, "thorough": 900}
BUILD_TIMEOUT = 1200
KILL_GRACE = 10


def sh(cmd, cwd=None, env=None, timeout=None, shell=True):
    return subprocess.run(cmd, cwd=cwd, env=env, shell=shell, capture_output=True,
                          text=True, timeout=timeout)


def checkout(repo, ref, dest):
    """Clone `repo` at `ref` (tag/branch/sha) into dest; local paths are copied."""
    src = Path(repo)
    if src.exists():
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__"))
        sha = "local"
        try:
            r = sh("git rev-parse HEAD", cwd=src)
            if r.returncode == 0:
                sha = r.stdout.strip()
        except Exception:  # noqa: BLE001
            pass
        return sha
    r = sh(f"git clone --quiet --depth 1 --branch {ref} {repo} {dest}")
    if r.returncode != 0:
        raise RuntimeError(f"clone failed: {r.stderr.strip()}")
    return sh("git rev-parse HEAD", cwd=dest).stdout.strip()


def make_venv(workdir):
    venv = workdir / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    return venv


def minimal_env(venv, workdir):
    return {"PATH": f"{venv / 'bin'}:/usr/local/bin:/usr/bin:/bin",
            "HOME": str(workdir / "home"), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
            "VIRTUAL_ENV": str(venv), "TMPDIR": str(workdir / "tmp"),
            "OMP_NUM_THREADS": "4", "PYTHONDONTWRITEBYTECODE": "1"}


def isolation_prefix(user):
    """Network isolation for the solve step: Linux + passwordless sudo -> unshare -n."""
    if sys.platform != "linux" or shutil.which("unshare") is None or shutil.which("sudo") is None:
        return [], "none (not Linux or no unshare/sudo)"
    if subprocess.run(["sudo", "-n", "true"], capture_output=True).returncode != 0:
        return [], "none (sudo needs a password)"
    return ["sudo", "-n", "unshare", "-n", "--", "sudo", "-n", "-u", user, "--"], "unshare -n"


def run_instance(run_tmpl, src, env, prefix, inst_path, time_limit, threads, out_path):
    cmd = run_tmpl.format(instance=str(inst_path), time_limit=time_limit, threads=threads, out=str(out_path))
    full = prefix + ["env", "-i"] + [f"{k}={v}" for k, v in env.items()] + ["bash", "-c", cmd]
    t0 = time.time()
    proc = subprocess.Popen(full, cwd=src, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                            text=True, start_new_session=True)
    killed = False
    try:
        _, err = proc.communicate(timeout=time_limit + KILL_GRACE)
    except subprocess.TimeoutExpired:
        killed = True
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        _, err = proc.communicate()
    wall = time.time() - t0
    result = None
    if out_path.exists():
        try:
            result = json.loads(out_path.read_text())
        except Exception:  # noqa: BLE001
            result = None
    return result, round(wall, 2), killed, proc.returncode, (err or "")[-2000:]


def sgm(times, limit, shift=10.0):
    vals = [min(t, limit) + shift for t in times]
    return math.exp(sum(math.log(v) for v in vals) / len(vals)) - shift if vals else None


def aggregate(rows, limit, key):
    out = {}
    for g in sorted({r[key] for r in rows}):
        fr = [r for r in rows if r[key] == g]
        solved = [r for r in fr if r["outcome"] == "solved"]
        wrong = [r for r in fr if r["wrong"]]
        gaps = [r["gap"] for r in fr if r["outcome"] != "solved" and r["gap"] is not None]
        deltas = [r["obj_delta"] for r in fr if r.get("obj_delta") is not None]
        out[g] = {"n": len(fr), "solved": len(solved), "wrong": len(wrong),
                  "wrong_kinds": sorted({r["wrong"] for r in wrong}),
                  "obj_better": sum(1 for d in deltas if d < -1e-9),
                  "obj_equal": sum(1 for d in deltas if abs(d) <= 1e-9),
                  "obj_worse": sum(1 for d in deltas if d > 1e-9),
                  "mean_obj_delta": (round(sum(deltas) / len(deltas), 5) if deltas else None),
                  "sgm10": round(sgm([r["runtime_s"] if r["outcome"] == "solved" else limit for r in fr], limit), 2),
                  "mean_gap_unsolved": (round(sum(gaps) / len(gaps), 4) if gaps else None),
                  "no_solution": sum(1 for r in fr if r["outcome"] != "solved"
                                     and not r.get("has_solution", r.get("verified_objective") is not None))}
    return out


def summarize(rows, limit):
    return {split: {"instances": len(sr),
                    "by_family": aggregate(sr, limit, "family"),
                    "by_area": aggregate(sr, limit, "area"),
                    "overall": aggregate(sr, limit, "track_all")["all"] if sr else None}
            for split in ("feedback", "holdout")
            for sr in [[dict(r, track_all="all") for r in rows if r["split"] == split]]}


def public_id(name):
    """Keyed hash of an instance name with BENCH_KEY when set (plain hash
    otherwise), so the same instance maps to the same 10-character id across runs
    and nothing public can be turned back into a name without the key."""
    import hashlib
    import hmac
    key = os.environ.get("BENCH_KEY", "").encode()
    if key:
        return hmac.new(key, name.encode(), hashlib.sha256).hexdigest()[:10]
    return hashlib.sha256(name.encode()).hexdigest()[:10]


def anonymize(row):
    """Public records must not identify instances (a MIPLIB name or an objective
    value is enough to find and tune on the file)."""
    ident = public_id(row["name"])
    keep = {"family", "area", "track", "split", "runtime_s", "killed", "claimed_status", "outcome",
            "wrong", "note", "gap", "max_col_violation", "max_int_violation", "max_row_violation"}
    out = {k: v for k, v in row.items() if k in keep}
    out["has_solution"] = row.get("verified_objective") is not None
    out["name"] = ident
    out["note"] = ""  # notes may quote solver stderr
    return out


def hardware():
    cpu = platform.processor() or platform.machine()
    try:
        if sys.platform == "darwin":
            cpu = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip()
        elif sys.platform.startswith("linux"):
            for line in open("/proc/cpuinfo"):
                if line.startswith("model name"):
                    cpu = line.split(":", 1)[1].strip()
                    break
    except Exception:  # noqa: BLE001
        pass
    return f"{cpu}; {os.cpu_count()} cpus; {platform.system()} {platform.release()}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True, help="git URL or local path of the solver repo")
    ap.add_argument("--ref", required=True, help="tag / branch / sha to evaluate (label for local paths)")
    ap.add_argument("--mode", choices=MODES, default="default")
    ap.add_argument("--time-limit", type=float)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--shard", default="0/1", help="i/N: evaluate every N-th instance starting at i")
    ap.add_argument("--families", nargs="+")
    ap.add_argument("--instances", nargs="+")
    ap.add_argument("--out", help="output JSON (default history/<ref>[.shardI].json)")
    ap.add_argument("--workdir", help="scratch directory (default: temp dir, deleted afterwards)")
    ap.add_argument("--keep", action="store_true", help="keep the scratch directory")
    ap.add_argument("--public", action="store_true",
                    help="record for a public repo: instance names replaced by keyed hashes, "
                         "objective/bound values dropped (family, outcome, time, gap, flags kept)")
    args = ap.parse_args()

    limit = args.time_limit or MODES[args.mode]
    manifest = json.loads((ROOT / "instances" / "manifest.json").read_text())
    if args.families:
        manifest = [e for e in manifest if e["family"] in args.families]
    if args.instances:
        manifest = [e for e in manifest if e["name"] in args.instances]
    i, n = (int(v) for v in args.shard.split("/"))
    manifest = manifest[i::n]
    if not manifest:
        sys.exit("no instances selected")

    suite = yaml.safe_load((ROOT / "instances.yaml").read_text())
    known = {e["name"]: (float(e["optimum"]) if e.get("optimum") is not None else None)
              for e in suite["track_a"]}
    ref_path = ROOT / "instances" / "reference.yaml"
    if ref_path.exists():
        for name, v in (yaml.safe_load(ref_path.read_text()) or {}).items():
            known.setdefault(name, float(v["optimum"] if isinstance(v, dict) else v))

    workdir = Path(args.workdir) if args.workdir else Path(tempfile.mkdtemp(prefix="optim-bench-"))
    workdir.mkdir(parents=True, exist_ok=True)
    for d in ("home", "tmp", "out"):
        (workdir / d).mkdir(exist_ok=True)
    src = workdir / "src"
    if src.exists():
        shutil.rmtree(src)
    repo_public = re.sub(r"//[^@/]+@", "//", args.repo)  # never store credentials
    record = {"repo": repo_public, "ref": args.ref,
              "date": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
              "mode": args.mode, "time_limit": limit, "threads": args.threads, "shard": args.shard,
              "hardware": hardware(), "bench_python": platform.python_version()}
    t_all = time.time()
    try:
        # never echo credentials embedded in the clone URL
        print(f"checkout {re.sub(r'//[^@/]+@', '//', args.repo)} @ {args.ref}", flush=True)
        record["sha"] = checkout(args.repo, args.ref, src)
        cfg = yaml.safe_load((src / "bench.yaml").read_text())
        if not isinstance(cfg, dict) or "run" not in cfg:
            raise RuntimeError("bench.yaml must define `run` (and optionally `build`)")
        venv = make_venv(workdir)
        env = minimal_env(venv, workdir)
        if cfg.get("build"):
            print(f"build: {cfg['build']}", flush=True)
            t0 = time.time()
            r = sh(cfg["build"], cwd=src, env=dict(env, PATH=env["PATH"] + ":" + os.environ.get("PATH", "")),
                   timeout=BUILD_TIMEOUT)
            record["build"] = {"returncode": r.returncode, "seconds": round(time.time() - t0, 1),
                               "stderr_tail": r.stderr[-2000:]}
            if r.returncode != 0:
                raise RuntimeError(f"build failed (exit {r.returncode}): {r.stderr[-800:]}")
        prefix, iso = isolation_prefix(os.environ.get("USER", "runner"))
        record["isolation"] = iso
        print(f"isolation: {iso}; {len(manifest)} instances, limit {limit:.0f}s, threads {args.threads}", flush=True)

        rows = []
        for k, e in enumerate(manifest, 1):
            out_path = workdir / "out" / f"{e['name']}.json"
            if out_path.exists():
                out_path.unlink()
            result, wall, killed, rc, err = run_instance(cfg["run"], src, env, prefix,
                                                         (ROOT / e["path"]).resolve(), limit, args.threads, out_path)
            sense = e.get("stats", {}).get("sense", 1)
            v = verify.verify(ROOT / e["path"], result, known.get(e["name"]), sense, wall, limit)
            if killed:
                v["note"] = (v["note"] + "; " if v["note"] else "") + "killed at limit"
            if result is None and rc not in (0, None):
                v["note"] = (v["note"] + "; " if v["note"] else "") + f"exit {rc}: {err.strip()[-300:]}"
            row = {"name": e["name"], "family": e["family"], "area": e["area"], "track": e["track"],
                   "split": e.get("split", "feedback"), "runtime_s": wall, "killed": killed, **v}
            if isinstance(result, dict) and isinstance(result.get("solver"), dict) and "solver" not in record:
                record["solver"] = result["solver"]
            rows.append(row)
            gap = f"{v['gap']:.2%}" if v["gap"] is not None else "-"
            # The progress line lands in the CI log, which is public on a public repo:
            # with --public show the keyed id, never the name, and drop the note
            # (it may quote solver stderr). The full row stays in the record.
            label = public_id(e["name"]) if args.public else e["name"]
            print(f"[{k:3d}/{len(manifest)}] {label:<26} {v['outcome']:<8} {wall:7.1f}s gap={gap} "
                  f"{v['wrong']}{'' if args.public else ' ' + v['note']}", flush=True)
        record["summary"] = summarize(rows, limit)
        if args.public:
            rows = [anonymize(r) for r in rows]
        record["rows"] = rows
        record["status"] = "ok"
    except Exception as ex:  # noqa: BLE001
        record["status"] = "error"
        record["error"] = str(ex)
        print(f"ERROR: {ex}", file=sys.stderr)
    record["wall_minutes"] = round((time.time() - t_all) / 60, 1)

    out = Path(args.out) if args.out else ROOT / "history" / (
        f"{args.ref}{'' if n == 1 else f'.shard{i}'}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=1))
    print(f"record -> {out}")
    if not args.keep and not args.workdir:
        shutil.rmtree(workdir, ignore_errors=True)
    sys.exit(0 if record["status"] == "ok" else 1)


if __name__ == "__main__":
    main()
