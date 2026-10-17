#!/usr/bin/env python3
"""Find the smallest bounded crew that can meet offline handoff deadlines."""

import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "gateplan"))
sys.path.insert(0, str(HERE.parent / "gatecheck"))
sys.path.insert(0, str(HERE.parent / "plancheck"))
import gateplan  # noqa: E402
import gatecheck  # noqa: E402
import plancheck  # noqa: E402


STATE_LIMIT_MESSAGE = "state limit exceeded; feasibility not established"


def solve(tasks, gates, budget, max_workers=4, max_states=100000):
    """Return a proved minimum, a candidate, or an explicit refusal.

    Counts are scanned upwards. A feasible schedule at count k also proves
    feasibility for larger counts, but an uncompleted lower search prevents
    a claim that k is the minimum.
    """
    if type(max_workers) is not int or not 1 <= max_workers <= 4:
        raise ValueError("max_workers must be an integer from 1 to 4")
    if type(max_states) is not int or not 1 <= max_states <= 500000:
        raise ValueError("max_states must be an integer from 1 to 500000")
    deadline = gateplan.integer(budget, "budget")
    graph = plancheck.graph(tasks)
    if len(graph) > 10:
        raise ValueError("crewfit is limited to 10 tasks")
    checked_gates = gatecheck.validate_gates(gates, set(graph))
    for gate in checked_gates:
        gateplan.integer(gate["due"], "gate due")
    for minutes, _ in graph.values():
        gateplan.integer(minutes, "task minutes")

    attempts = []
    first_feasible = None
    unknown_below = False
    for workers in range(1, max_workers + 1):
        try:
            trial = gateplan.solve(tasks, gates, workers, deadline, max_states)
        except ValueError as exc:
            if str(exc) != STATE_LIMIT_MESSAGE:
                raise
            attempts.append({"workers": workers, "status": "unknown_state_limit"})
            unknown_below = True
            continue
        attempts.append({"workers": workers, "status": trial["status"],
                         "states_examined": trial["states_examined"]})
        if trial["status"] == "feasible":
            first_feasible = trial
            break

    common = {"budget": deadline, "max_workers": max_workers,
              "state_limit_per_count": max_states, "attempts": attempts}
    if first_feasible is not None:
        count = first_feasible["workers"]
        return {**common,
                "status": "candidate" if unknown_below else "minimum_proven",
                "workers": count, "plan": first_feasible["plan"],
                "minimum_proven": not unknown_below}
    if unknown_below:
        return {**common, "status": "inconclusive", "minimum_proven": False}
    return {**common, "status": "infeasible_up_to_max_workers",
            "minimum_proven": False, "infeasibility_proven": True}


def demo():
    tasks = {"tasks": [
        {"id": "release", "minutes": 1},
        {"id": "handoff", "minutes": 2, "after": ["release"]},
        {"id": "background", "minutes": 4},
    ]}
    gates = {"gates": [{"id": "early", "tasks": ["handoff"], "due": 3}]}
    return tasks, gates, 4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--tasks")
    parser.add_argument("--gates")
    parser.add_argument("--budget", type=int)
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--max-states", type=int, default=100000)
    args = parser.parse_args()
    try:
        if args.demo:
            if any(value is not None for value in (args.tasks, args.gates, args.budget)):
                raise ValueError("--demo cannot be combined with --tasks, --gates or --budget")
            tasks, gates, budget = demo()
        else:
            if any(value is None for value in (args.tasks, args.gates, args.budget)):
                raise ValueError("--tasks, --gates and --budget are required")
            tasks = plancheck.read_json(args.tasks)
            gates = plancheck.read_json(args.gates)
            budget = args.budget
        result = solve(tasks, gates, budget, args.max_workers, args.max_states)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0 if result["status"] == "minimum_proven" else 2
    except (ValueError, OSError, OverflowError, RecursionError) as exc:
        print("crewfit: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
