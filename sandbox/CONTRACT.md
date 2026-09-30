# Solver contract (what the bench expects from the solver repo)

This is the only document the solver author (human or agent) needs. The bench
instances, their names, and the reference optima are not shared.

## 1. Repository layout

The repository root must contain `bench.yaml`:

```yaml
build: pip install -e .            # run once per evaluation, with network access
run: milp-solve {instance} --time-limit {time_limit} --threads {threads} --out {out}
```

- `build` is run from the repository root, once, in a fresh checkout of the
  evaluated tag. It may install anything. It is limited to 20 minutes.
- `run` is run once per instance, from the repository root, **without network
  access and with a minimal environment**. Placeholders (all always supplied):

  | placeholder | meaning |
  |---|---|
  | `{instance}` | absolute path of a gzipped MPS file (`*.mps.gz`, free-format MPS) |
  | `{time_limit}` | wall-clock seconds available for this instance (float) |
  | `{threads}` | number of threads the solver may use |
  | `{out}` | absolute path where the solver must write its result JSON |

Any language is fine; only the command line matters.

## 2. Result file

The `run` command writes `{out}` as JSON:

```json
{
  "status": "optimal",                 // optimal | feasible | infeasible | unbounded | unknown
  "objective": 1234.5,                 // objective value of `solution` (null if no solution)
  "bound": 1230.1,                     // proven dual bound (null if none)
  "solution": {"x_1": 1.0, "x_2": 0.0, "...": 0.0},   // or a list in MPS column order
  "solver": {"name": "mylib", "version": "0.3.1"}    // optional, shown on the dashboard
}
```

Rules:

- `status: optimal` means *you claim `solution` is optimal within a relative
  gap of 1e-4*. `feasible` means you have a solution but no proof.
- `solution` is mandatory whenever `objective` is given. Variables missing from a
  dict are treated as 0; a list must have exactly one entry per MPS column.
- The bench **recomputes the objective and checks feasibility itself** (row
  bounds, column bounds, integrality, tolerance 1e-6 absolute on values up to 1 and
  relative above). A reported objective is never trusted.
- Objective sense is the MPS file's (an `OBJSENSE MAX` section may appear; most
  instances are minimization). Report the objective in the file's sense.

## 3. Time and resources

- The process is killed 10 s after `{time_limit}` if it has not exited. A killed
  run, a crash, a missing or malformed `{out}`, counts as unsolved at the full limit.
  **Write `{out}` before exiting under any circumstance** (write the best incumbent
  as `feasible` when you hit the limit).
- Memory: 12 GB. No network. No GPU.
- Instances are MPS files of up to ~100 k rows / ~100 k columns; most are far
  smaller (hundreds to tens of thousands).

## 4. How results are scored

Per instance, in order:

1. `solution` infeasible / integrality violated / objective misreported by more
   than the tolerance → **wrong answer** (worst outcome).
2. `status: optimal` but the verified objective is worse than the reference
   optimum by more than 1e-4 relative → **wrong answer** (false optimality claim).
3. `bound` better than the reference optimum by more than 1e-4 relative → **wrong
   answer** (false bound).
4. `status: optimal` and the verified objective is within 1e-4 relative of the
   reference optimum → **solved**, scored by wall time.
5. Otherwise → **unsolved**, scored at the time limit, with the end gap
   `|objective - bound| / |objective|` recorded (or "no solution").

Aggregates per problem family: number solved, wrong answers, shifted geometric
mean of runtime (10 s shift, unsolved at the limit), mean end gap on unsolved.
Lower SGM is better; wrong answers are reported separately and should be zero.

## 5. Feedback

After each evaluated tag, an issue is opened on the solver repository with the
per-family aggregates for the *feedback* part of the suite, the same numbers for
the HiGHS baseline on the same hardware, and the list of wrong-answer categories
(never instance names or files). A held-out part of the suite is scored on the
dashboard only and never reported back.
