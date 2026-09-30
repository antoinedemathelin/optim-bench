"""highs-baseline INSTANCE --time-limit S --threads N --out RESULT.json

Minimal, contract-conforming solver: reads the MPS, runs HiGHS with the given
limit, always writes the result file (best incumbent as `feasible` on timeout).
"""
import argparse
import json
import math


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("instance")
    ap.add_argument("--time-limit", type=float, required=True)
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mip-gap", type=float, default=1e-4)
    args = ap.parse_args()

    result = {"status": "unknown", "objective": None, "bound": None, "solution": None,
              "solver": {"name": "HiGHS", "version": None}}
    try:
        import highspy
        h = highspy.Highs()
        result["solver"]["version"] = h.version()
        h.setOptionValue("output_flag", False)
        h.setOptionValue("time_limit", args.time_limit)
        h.setOptionValue("threads", args.threads)
        h.setOptionValue("mip_rel_gap", args.mip_gap)
        h.readModel(args.instance)
        h.run()
        status = h.modelStatusToString(h.getModelStatus())
        info = h.getInfo()
        has_sol = info.primal_solution_status == 2
        if has_sol:
            names = list(h.getLp().col_names_)
            result["solution"] = dict(zip(names, h.getSolution().col_value))
            result["objective"] = info.objective_function_value
        if math.isfinite(info.mip_dual_bound):
            result["bound"] = info.mip_dual_bound
        if status == "Optimal":
            result["status"] = "optimal"
        elif status == "Infeasible":
            result["status"] = "infeasible"
        elif status in ("Unbounded", "Primal infeasible or unbounded"):
            result["status"] = "unbounded" if status == "Unbounded" else "unknown"
        else:
            result["status"] = "feasible" if has_sol else "unknown"
    except Exception as e:  # noqa: BLE001
        result["error"] = str(e)
    finally:
        with open(args.out, "w") as f:
            json.dump(result, f)


if __name__ == "__main__":
    main()
