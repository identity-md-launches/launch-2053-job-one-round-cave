# Crewfit

Crewfit finds the **smallest worker count** (up to four) that can complete a
dependency graph within a final time budget and meet named handoff deadlines.
It returns a complete offline schedule. It runs the inherited exact Gateplan
solver for each count from one upward and checks each resulting schedule with
Plancheck and Gatecheck through Gateplan. No task label is executed.

From the repository root, run:

```sh
python3 -B line-1/tools/crewfit/crewfit.py --demo
```

Observed in round 35: the demo proves that one worker cannot finish by minute
4, and that two workers can finish at minute 4 with the handoff at minute 3.
The output status is `minimum_proven`, `workers` is 2, and `plan` contains the
full worker-by-worker schedule.

For your own files:

```sh
python3 -B line-1/tools/crewfit/crewfit.py --tasks tasks.json --gates gates.json --budget 12 --max-workers 4
```

Tasks use Gateplan's `{"tasks":[{"id":"build","minutes":4,"after":[]}]}`
shape. Gates use `{"gates":[{"id":"review","tasks":["build"],"due":9}]}`.
An intermediate gate is required. The budget and due times are minutes from
the start of the plan. The caller supplies estimates and assumes identical,
continuously available workers.

Each `attempts` row records a count's proved feasibility or infeasibility. If
a search hits `--max-states`, its count becomes `unknown_state_limit`; a larger
feasible count is then only a `candidate`, with `minimum_proven: false`. With no
feasible count, the tool returns `infeasible_up_to_max_workers` only if every
searched count was proved infeasible; otherwise it returns `inconclusive`.
Exit 0 means a proved minimum, 2 means a valid request without that proof,
and 1 means invalid input or an I/O error. No partial proof is called final.

Limits: 1–10 positive-duration tasks, 1–4 workers, integer minutes from 0 to
10,000 for budgets and gates, integer task durations from 1 to 10,000, and
`--max-states` from 1 to 500,000 **per count**. Search can be exponential.
Input JSON must be an ordinary workspace-local file of at most 100 KB with
unique keys, as enforced by Plancheck. Python 3.9+ standard library only;
keep sibling `gateplan`, `gatecheck`, and `plancheck` folders beside this one.
No network, environment variable, wallet, key, coin, payment or transaction is
needed. Estimated duration is not a forecast of actual completion.

Checks: `python3 -B line-1/tools/crewfit/selftest.py`. The suite verifies the
minimum and returned plan, impossible budgets, bounded-search honesty, input
validation and CLI exits, including small graphs checked against an independent
minute-grid scheduler. The local results appear in `line-1/check-results-35.json`.
