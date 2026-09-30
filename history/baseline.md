# optim-bench report: `baseline` (bcaddb6ea6)

- solver: HiGHS 1.15.1
- date: 2026-09-29T13:22:27+00:00, mode `default` (300 s per instance, 4 threads), evaluation wall 54.2 min
- hardware: AMD EPYC 9V74 80-Core Processor; 4 cpus; Linux 6.17.0-1022-azure; isolation: unshare -n
- baseline: HiGHS record `baseline` from 2026-09-29 on the same hardware

## feedback set — 61 instances

**Solved 47/61, wrong answers 0, SGM-10 74.42 s (HiGHS: 47/61, 0, 74.42 s)**

### By application area

| area | n | solved | wrong | SGM-10 (s) | end-gap unsolved | HiGHS solved | HiGHS SGM-10 |
|---|---|---|---|---|---|---|---|
| auction | 4 | 4 | 0 | 53.83 | - | 4 | 53.83 |
| energy | 4 | 1 | 0 | 157.38 | 0.0% | 1 | 157.38 |
| facility-location | 5 | 5 | 0 | 110.44 | - | 5 | 110.44 |
| lot-sizing | 5 | 5 | 0 | 68.3 | - | 5 | 68.3 |
| network-design | 5 | 4 | 0 | 54.77 | 10.1% | 4 | 54.77 |
| packing | 8 | 8 | 0 | 51.01 | - | 8 | 51.01 |
| routing | 11 | 9 | 0 | 55.83 | 11.5% | 9 | 55.83 |
| scheduling | 9 | 4 | 0 | 102.3 | 16.5% | 4 | 102.3 |
| set-covering | 6 | 5 | 0 | 57.13 | 4.2% | 5 | 57.13 |
| workforce | 4 | 2 | 0 | 145.64 | 25.9% | 2 | 145.64 |

### By family

| family | n | solved | wrong | SGM-10 (s) | end-gap unsolved | HiGHS solved | HiGHS SGM-10 |
|---|---|---|---|---|---|---|---|
| bin-packing | 4 | 4 | 0 | 20.17 | - | 4 | 20.17 |
| cap-facility-loc | 4 | 4 | 0 | 117.65 | - | 4 | 117.65 |
| comb-auction | 4 | 4 | 0 | 53.83 | - | 4 | 53.83 |
| cumulative-sched | 1 | 0 | 0 | 300.0 | 16.2% | 0 | 300.0 |
| cutting | 1 | 1 | 0 | 35.71 | - | 1 | 35.71 |
| cvrp-compact | 4 | 3 | 0 | 57.0 | 18.8% | 3 | 57.0 |
| fixed-charge-flow | 2 | 2 | 0 | 25.33 | - | 2 | 25.33 |
| fixed-charge-transport | 1 | 1 | 0 | 26.06 | - | 1 | 26.06 |
| job-shop | 4 | 2 | 0 | 92.99 | 11.5% | 2 | 92.99 |
| knapsack | 3 | 3 | 0 | 161.74 | - | 3 | 161.74 |
| lot-sizing | 4 | 4 | 0 | 48.82 | - | 4 | 48.82 |
| lot-sizing-mip | 1 | 1 | 0 | 235.74 | - | 1 | 235.74 |
| multicommodity-design | 2 | 1 | 0 | 149.14 | 10.1% | 1 | 149.14 |
| p-median | 1 | 1 | 0 | 85.45 | - | 1 | 85.45 |
| production-sched | 1 | 0 | 0 | 300.0 | 42.6% | 0 | 300.0 |
| rail-timetabling | 1 | 0 | 0 | 300.0 | 0.5% | 0 | 300.0 |
| set-covering | 4 | 3 | 0 | 65.23 | 4.2% | 3 | 65.23 |
| set-partitioning | 2 | 2 | 0 | 43.45 | - | 2 | 43.45 |
| shift-scheduling | 4 | 2 | 0 | 145.64 | 25.9% | 2 | 145.64 |
| sports-schedule | 1 | 1 | 0 | 2.05 | - | 1 | 2.05 |
| swath-routing | 1 | 1 | 0 | 17.12 | - | 1 | 17.12 |
| timetabling | 1 | 1 | 0 | 60.34 | - | 1 | 60.34 |
| tsp-compact | 4 | 3 | 0 | 70.58 | 4.3% | 3 | 70.58 |
| unit-commitment | 4 | 1 | 0 | 157.38 | 0.0% | 1 | 157.38 |
| vrp-compact | 1 | 1 | 0 | 40.89 | - | 1 | 40.89 |
| vrp-set-part | 1 | 1 | 0 | 75.85 | - | 1 | 75.85 |

## holdout set — 27 instances

**Solved 22/27, wrong answers 1, SGM-10 73.93 s (HiGHS: 22/27, 1, 73.93 s)**

Wrong-answer categories: BOUND_EXCEEDS_REFERENCE. A wrong answer is an infeasible or misreported solution, a false optimality claim, or a bound that excludes the true optimum — see the contract, section 4.

### By application area

| area | n | solved | wrong | SGM-10 (s) | end-gap unsolved | HiGHS solved | HiGHS SGM-10 |
|---|---|---|---|---|---|---|---|
| auction | 2 | 2 | 0 | 92.15 | - | 2 | 92.15 |
| energy | 2 | 2 | 0 | 63.24 | - | 2 | 63.24 |
| facility-location | 3 | 3 | 0 | 84.95 | - | 3 | 84.95 |
| lot-sizing | 2 | 2 | 0 | 61.74 | - | 2 | 61.74 |
| network-design | 2 | 2 | 0 | 35.23 | - | 2 | 35.23 |
| packing | 3 | 2 | 0 | 41.97 | 6.2% | 2 | 41.97 |
| routing | 5 | 3 | 0 | 74.59 | 14.3% | 3 | 74.59 |
| scheduling | 3 | 1 | 1 (BOUND_EXCEEDS_REFERENCE) | 242.73 | 11.0% | 1 | 242.73 |
| set-covering | 3 | 3 | 0 | 37.88 | - | 3 | 37.88 |
| workforce | 2 | 2 | 0 | 117.47 | - | 2 | 117.47 |

### By family

| family | n | solved | wrong | SGM-10 (s) | end-gap unsolved | HiGHS solved | HiGHS SGM-10 |
|---|---|---|---|---|---|---|---|
| bin-packing | 2 | 1 | 0 | 63.13 | 6.2% | 1 | 63.13 |
| cap-facility-loc | 2 | 2 | 0 | 86.21 | - | 2 | 86.21 |
| comb-auction | 2 | 2 | 0 | 92.15 | - | 2 | 92.15 |
| cumulative-sched | 1 | 1 | 0 | 157.98 | - | 1 | 157.98 |
| cvrp-compact | 2 | 1 | 0 | 77.18 | 27.1% | 1 | 77.18 |
| fixed-charge-transport | 1 | 1 | 0 | 30.31 | - | 1 | 30.31 |
| job-shop | 2 | 0 | 1 (BOUND_EXCEEDS_REFERENCE) | 300.0 | 11.0% | 0 | 300.0 |
| knapsack | 1 | 1 | 0 | 16.25 | - | 1 | 16.25 |
| lot-sizing | 2 | 2 | 0 | 61.74 | - | 2 | 61.74 |
| multicommodity-design | 1 | 1 | 0 | 40.76 | - | 1 | 40.76 |
| p-median | 1 | 1 | 0 | 82.47 | - | 1 | 82.47 |
| set-covering | 2 | 2 | 0 | 29.05 | - | 2 | 29.05 |
| set-partitioning | 1 | 1 | 0 | 61.99 | - | 1 | 61.99 |
| shift-scheduling | 2 | 2 | 0 | 117.47 | - | 2 | 117.47 |
| swath-routing | 1 | 1 | 0 | 156.18 | - | 1 | 156.18 |
| tsp-compact | 2 | 1 | 0 | 48.55 | 1.6% | 1 | 48.55 |
| unit-commitment | 2 | 2 | 0 | 63.24 | - | 2 | 63.24 |

Scoring: SGM-10 = shifted geometric mean of wall time (10 s shift), unsolved counted at the limit; an instance is solved only if the returned solution is verified feasible and within 1e-4 of the reference optimum. Lower is better. Wrong answers must be zero before speed matters.
