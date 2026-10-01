#!/usr/bin/env python3
"""Independent verification of a solver's result JSON against the MPS model.

    python sandbox/verify.py instance.mps.gz result.json [--reference OPT] [--sense 1|-1]

Never trusts the reported objective: the solution vector is checked against
column bounds, integrality and every row, and the objective is recomputed.
Returns a dict (and prints JSON) with the verified outcome; used by evaluate.py.
"""
import argparse
import json
import math
import sys
from pathlib import Path

FEAS_TOL = 1e-6      # absolute, scaled by max(1, |bound|)
INT_TOL = 1e-6
GAP_TOL = 1e-4       # relative, for optimality / bound claims vs reference


def load_model(mps_path):
    import highspy
    import numpy as np
    h = highspy.Highs()
    h.setOptionValue("output_flag", False)
    if h.readModel(str(mps_path)) != highspy.HighsStatus.kOk:
        raise RuntimeError(f"cannot read {mps_path}")
    lp = h.getLp()
    a = lp.a_matrix_
    sense = -1 if h.getObjectiveSense()[1] == highspy.ObjSense.kMaximize else 1
    integrality = np.array([int(v) for v in lp.integrality_], dtype=int) if len(lp.integrality_) \
        else np.zeros(lp.num_col_, dtype=int)
    return {
        "n": lp.num_col_, "m": lp.num_row_, "names": list(lp.col_names_),
        "cost": np.array(lp.col_cost_, dtype=float), "offset": float(lp.offset_),
        "col_lo": np.array(lp.col_lower_, dtype=float), "col_hi": np.array(lp.col_upper_, dtype=float),
        "row_lo": np.array(lp.row_lower_, dtype=float), "row_hi": np.array(lp.row_upper_, dtype=float),
        "is_int": integrality == 1,
        "a_start": np.array(a.start_, dtype=int), "a_index": np.array(a.index_, dtype=int),
        "a_value": np.array(a.value_, dtype=float), "colwise": int(a.format_) == 1,
        "sense": sense,
    }


def _solution_vector(model, sol):
    import numpy as np
    n = model["n"]
    if sol is None:
        return None, "no solution"
    if isinstance(sol, list):
        if len(sol) != n:
            return None, f"solution list has {len(sol)} entries, model has {n} columns"
        return np.array(sol, dtype=float), None
    if isinstance(sol, dict):
        idx = {name: i for i, name in enumerate(model["names"])}
        x = np.zeros(n)
        unknown = 0
        for k, v in sol.items():
            i = idx.get(k)
            if i is None:
                unknown += 1
                continue
            x[i] = float(v)
        note = f"{unknown} unknown variable names ignored" if unknown else None
        return x, note
    return None, "solution must be a list or a dict"


def check_solution(model, x):
    """Return (max_violation, details) for a candidate x."""
    import numpy as np
    lo, hi = model["col_lo"], model["col_hi"]
    scale = np.maximum(1.0, np.maximum(np.abs(np.where(np.isfinite(lo), lo, 0)),
                                       np.abs(np.where(np.isfinite(hi), hi, 0))))
    col_viol = np.maximum(np.maximum(lo - x, x - hi), 0) / scale
    int_viol = np.where(model["is_int"], np.abs(x - np.round(x)), 0.0)
    act = np.zeros(model["m"])
    st, ix, vals = model["a_start"], model["a_index"], model["a_value"]
    if model["colwise"]:
        for j in range(model["n"]):
            if x[j] != 0.0:
                sl = slice(st[j], st[j + 1])
                np.add.at(act, ix[sl], vals[sl] * x[j])
    else:
        for i in range(model["m"]):
            sl = slice(st[i], st[i + 1])
            act[i] = float(np.dot(vals[sl], x[ix[sl]]))
    rlo, rhi = model["row_lo"], model["row_hi"]
    rscale = np.maximum(1.0, np.maximum(np.abs(np.where(np.isfinite(rlo), rlo, 0)),
                                        np.abs(np.where(np.isfinite(rhi), rhi, 0))))
    row_viol = np.maximum(np.maximum(rlo - act, act - rhi), 0) / rscale
    obj = float(np.dot(model["cost"], x)) + model["offset"]
    return {
        "objective": obj,
        "max_col_violation": float(col_viol.max()) if len(col_viol) else 0.0,
        "max_int_violation": float(int_viol.max()) if len(int_viol) else 0.0,
        "max_row_violation": float(row_viol.max()) if len(row_viol) else 0.0,
    }


def verify(mps_path, result, reference=None, sense=None, runtime_s=None, time_limit=None):
    """Score one instance. `result` is the parsed result JSON (or None if the
    solver produced nothing). Returns the verified record.

    `reference` is a *measured* objective: the best feasible solution the bench
    knew of before this run (a HiGHS run for Track B, the published value for
    Track A). It is not treated as an optimum. Nothing proves an optimum, and a
    reference that came from a solver can simply be wrong -- it has been. The only
    sound comparison point is an objective someone has actually exhibited, so a
    solution better than the reference is a better solution, never a fault.
    """
    out = {"claimed_status": None, "claimed_objective": None, "claimed_bound": None,
           "verified_objective": None, "outcome": "unsolved", "wrong": "", "note": "",
           "gap": None, "obj_delta": None}
    if result is None or not isinstance(result, dict):
        out["note"] = "no result file"
        return out
    status = str(result.get("status", "unknown")).lower()
    out["claimed_status"] = status
    obj_claim, bound = result.get("objective"), result.get("bound")
    out["claimed_objective"], out["claimed_bound"] = obj_claim, bound

    model = load_model(mps_path)
    sgn = sense if sense is not None else model["sense"]
    x, note = _solution_vector(model, result.get("solution"))
    if note:
        out["note"] = note
    verified = None
    if x is not None:
        chk = check_solution(model, x)
        worst = max(chk["max_col_violation"], chk["max_int_violation"], chk["max_row_violation"])
        out.update({k: chk[k] for k in ("max_col_violation", "max_int_violation", "max_row_violation")})
        if worst > FEAS_TOL:
            out["wrong"] = "INFEASIBLE_SOLUTION"
            return out
        verified = chk["objective"]
        out["verified_objective"] = verified
        if obj_claim is not None and abs(verified - float(obj_claim)) > GAP_TOL * max(1.0, abs(verified)):
            out["wrong"] = "OBJECTIVE_MISREPORTED"
            return out
    elif obj_claim is not None or status in ("optimal", "feasible"):
        out["wrong"] = "MISSING_SOLUTION"
        return out

    # Best objective anyone has actually exhibited for this instance: the stored
    # measurement, or this run's own verified solution when that is better.
    best = reference
    if verified is not None and (best is None or sgn * (verified - best) < 0):
        best = verified
    if best is not None:
        tol = GAP_TOL * max(1.0, abs(best))
        # A lower bound can never be better than a solution someone has exhibited.
        if bound is not None and sgn * (float(bound) - best) > tol:
            out["wrong"] = "INVALID_BOUND"
            return out
        # Claiming optimality asserts a bound equal to the returned objective.
        if status == "optimal" and verified is not None and sgn * (verified - best) > tol:
            out["wrong"] = "FALSE_OPTIMALITY_CLAIM"
            return out
        if status in ("infeasible", "unbounded"):
            out["wrong"] = "FALSE_INFEASIBILITY_CLAIM"
            return out
    if reference is not None and verified is not None:
        out["obj_delta"] = round(sgn * (verified - reference) / max(1.0, abs(reference)), 6)
    if status == "optimal" and verified is not None:
        out["outcome"] = "solved"  # claimed optimal, nothing contradicts it

    if verified is not None and bound is not None:
        out["gap"] = abs(verified - float(bound)) / max(1e-9, abs(verified))
    if out["outcome"] != "solved" and runtime_s is not None and time_limit is not None \
            and runtime_s < time_limit - 1 and status != "optimal":
        out["note"] = (out["note"] + "; " if out["note"] else "") + "stopped before the limit without a proof"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("instance")
    ap.add_argument("result")
    ap.add_argument("--reference", type=float)
    ap.add_argument("--sense", type=int)
    args = ap.parse_args()
    try:
        result = json.loads(Path(args.result).read_text())
    except Exception as e:  # noqa: BLE001
        result = None
        print(f"cannot parse result: {e}", file=sys.stderr)
    print(json.dumps(verify(args.instance, result, args.reference, args.sense), indent=1))


if __name__ == "__main__":
    main()
