# optim-bench

A laptop-scale benchmark for mixed-integer linear programming (MILP) solvers, and
the machinery to evaluate a solver repository against it without showing it the
instances. Results: [dashboard](https://antoinedemathelin.github.io/optim-bench/dashboard/)
and [`history/`](history/).

## The suite, in outline

88 instances across nine application areas, the problems people actually buy a
MILP solver for: routing, facility location, lot-sizing, energy (unit commitment),
scheduling, workforce rostering, packing, auctions, set covering / network design.
Every instance is a plain `.mps.gz` with a known optimum and a 300 s per-instance
budget.

- **Track A, 28 instances**: curated real instances from public libraries, chosen
  for application coverage and for being solvable on a laptop, at least two per
  area.
- **Track B, 60 instances**: ten generated application families, two sizes, three
  instances each, from parameterized generators with a private seed.

Scale, to give an idea rather than a specification: most instances have between a
few hundred and a few thousand rows and columns, the median is about a thousand
rows by fourteen hundred columns, and the largest reach roughly a hundred thousand
of each with about half a million nonzeros. Around 70 % of the suite has both
integer and continuous variables (fixed-charge and big-M structure); the rest is
pure binary. HiGHS at defaults, four threads, solves about three quarters of the
suite within the budget on the GitHub runner ([baseline](history/baseline.md)).

The suite is split into a **feedback** part (61 instances), whose per-family
results are reported back to the solver author, and a **held-out** part (27), which
appears only on the dashboard. A widening gap between the two is the overfitting
signal.

## Public repo, private suite

This repository is public so the evaluation workflow gets unlimited Actions
minutes. The suite is not public: instance files, their names, the reference
optima and the generator seed travel only inside `suite.enc`, an AES-256 bundle
whose key is the `BENCH_KEY` repository secret. Public history records carry
keyed-hash instance ids and no objective values, and the documentation names areas
and families only. Everything about how the suite was built (generators, curation,
calibration, design notes) lives in a separate private repository.

## Evaluating a solver

A solver repository declares a `build` and a `run` command in `bench.yaml` and
writes one result JSON per instance; see [sandbox/CONTRACT.md](sandbox/CONTRACT.md).
The loop, described in [sandbox/README.md](sandbox/README.md): the solver author
pushes a tag and dispatches the `evaluate` workflow → it evaluates the oldest
unevaluated tag in parallel shards, re-verifies every returned solution
independently, commits `history/<tag>.json` and `<tag>.md`, opens a feedback issue
on the solver repository with per-family aggregates, and dispatches itself again
while tags are waiting. The HiGHS baseline goes through the identical path on the
same hardware.

Scoring: per-area and per-family shifted geometric mean of runtime (10 s shift,
timeouts at the limit), solved counts, mean end-gap on unsolved instances, and a
count of *wrong answers* (infeasible solutions, misreported objectives, false
optimality or bound claims) that must be zero before speed matters.

## Setup

Repository secrets `BENCH_KEY` (bundle passphrase) and `AGENT_REPO_TOKEN`
(fine-grained token on the solver repository: Contents read, Issues write),
repository variable `AGENT_REPO` (`owner/name`), GitHub Pages from `main` at `/`.
The solver side gets a token on this repository with *Actions: write* only, to
start the workflow. Details in [sandbox/README.md](sandbox/README.md).

To run the evaluator locally with the key:

```bash
uv venv .venv && uv pip install --python .venv/bin/python -r sandbox/requirements.txt
BENCH_KEY=... .venv/bin/python sandbox/suite_bundle.py unpack     # -> instances/, instances.yaml
.venv/bin/python sandbox/evaluate.py --repo sandbox/baseline-solver --ref baseline --mode quick
```

## Layout

```
.github/workflows/evaluate.yml   # the evaluation workflow (workflow_dispatch only)
sandbox/                         # evaluator, verifier, report, contract, baseline solver
suite.enc                        # the encrypted suite
history/                         # one record + report per evaluated tag, index for the dashboard
dashboard/                       # static dashboard served by GitHub Pages
```
