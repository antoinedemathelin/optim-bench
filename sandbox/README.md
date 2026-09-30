# Sandbox: evaluating an external solver repo without showing it the suite

Two repositories:

- **bench** (this one, public so Actions minutes are unlimited): evaluator, history,
  dashboard and the workflow in clear; the suite (instances, names, reference optima,
  generator seed) only as the encrypted `suite.enc`.
- **solver** (the agent's, anywhere): must satisfy [CONTRACT.md](CONTRACT.md) —
  a `bench.yaml` with a `build` and a `run` command, and a result JSON per instance.

Loop: the solver author pushes a **tag** and dispatches the bench workflow (a
token with *Actions: write* on the bench repo and nothing else) → the workflow
picks the oldest unevaluated tag → clones it into a fresh
venv on a runner, builds, runs every instance under a hard kill, **verifies each
returned solution independently** → commits `history/<tag>.json` + `<tag>.md`,
rebuilds `history/index.json` for the dashboard → opens an issue on the solver
repo with per-family aggregates of the feedback set → if more tags are waiting it
dispatches itself again, so a burst drains in order. The held-out set (a third of
Track B and seven Track A instances) is scored on the dashboard only. There is no
schedule: GitHub runs cron workflows hours late under load (a 30-minute cron fired
six times in 26 h), so the solver side re-dispatches if no report arrives and
nothing is running.

## Setup

1. Pack the suite with a strong passphrase and commit `suite.enc` (never
   `instances/` or `instances.yaml`; they are git-ignored):
   `BENCH_KEY=... python sandbox/suite_bundle.py pack`.
2. Repository **secret** `BENCH_KEY` = that passphrase.
3. Repository **variable** `AGENT_REPO` = `owner/solver-repo`.
4. Repository **secret** `AGENT_REPO_TOKEN` = fine-grained PAT scoped to the solver
   repo only: *Contents: read*, *Issues: write*. The solver side never receives any
   credential or key for the bench repo, so it cannot read the instances.
5. Enable GitHub Pages from branch `main`, folder `/`. The dashboard is at
   `https://<owner>.github.io/<bench-repo>/dashboard/`.
6. For the solver side: a second fine-grained PAT scoped to the **bench** repo with
   *Actions: write* only (no Contents). It can start the workflow and list runs; it
   cannot read `suite.enc`'s key, history commits, secrets or code. Give it to the
   solver's environment as `OPTIM_BENCH_TOKEN`.
6. Run the workflow once by hand (`workflow_dispatch`): with no baseline recorded it
   evaluates `sandbox/baseline-solver` (HiGHS through the same contract) and commits
   `history/baseline.json`. Every later run evaluates solver tags.

Give the solver author `CONTRACT.md` and nothing else.

## Files

| file | role |
|---|---|
| `CONTRACT.md` | the interface the solver repo must implement (the only document shared) |
| `evaluate.py` | clone → venv → build → run each instance (no network, minimal env, hard kill) → verify → record |
| `verify.py` | independent feasibility / objective / bound check of a result JSON |
| `merge.py` | joins shard records from parallel CI jobs |
| `report.py` | Markdown feedback report (feedback set only unless `--holdout`) |
| `pick_tag.py` | chooses baseline-first, then the oldest unevaluated tag |
| `build_index.py` | `history/index.json` for the dashboard |
| `suite_bundle.py` | pack / unpack the encrypted suite (`suite.enc`) |
| `baseline-solver/` | HiGHS behind the contract: the baseline and a working example for authors |
| `../.github/workflows/evaluate.yml` | the pipeline: find → 4 shards → publish |
| `../dashboard/index.html` | static dashboard reading `../history/index.json` |

## Running an evaluation locally

```bash
.venv/bin/python sandbox/evaluate.py --repo sandbox/baseline-solver --ref baseline --mode quick
.venv/bin/python sandbox/evaluate.py --repo ../my-solver --ref v0.1.0 --families set-covering
.venv/bin/python sandbox/report.py history/v0.1.0.json --baseline history/baseline.json
.venv/bin/python sandbox/build_index.py && (cd . && python3 -m http.server 8000)  # dashboard at /dashboard/
```

Local runs on macOS have no network isolation (`unshare` is Linux-only); the
minimal environment and hard kill still apply.

## Budget on GitHub-hosted runners

4 vCPU / 16 GB runners, 4 shards of 22 instances, 300 s limit: worst case ~1.9 h
per shard, typically 30–60 min for a HiGHS-class solver. Each evaluation costs
roughly 2–4 runner-hours; on a private repo's free tier that is ~8–15 evaluations
a month. Use `mode: quick` (60 s) for cheap iterations and re-run `default` on
milestones, or attach a self-hosted runner.

## Anti-overfitting

- The solver author sees only per-family aggregates, never instance names; public
  history records (`--public`) carry keyed-hash ids and no objective values, and
  the public docs never name an instance (a MIPLIB name is a download link).
- The held-out set is scored but never reported back; a widening gap between
  feedback and held-out SGM on the dashboard is the overfitting signal.
- The Track B generators (kept in a private repository, like everything about
  how the suite is built) are seeded: a new master seed produces a fresh edition
  of Track B for a periodic re-roll.
