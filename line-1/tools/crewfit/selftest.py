#!/usr/bin/env python3
"""Behavioral checks for Crewfit, including an independent minute-grid oracle."""

from itertools import combinations
import json
from pathlib import Path
import random
import subprocess
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import crewfit  # noqa: E402


def minute_grid(tasks, gates, workers, budget):
    """Explore every ready-task start subset at every integer minute."""
    rows = tasks["tasks"]
    names = [row["id"] for row in rows]
    ids = {name: i for i, name in enumerate(names)}
    durations = [row["minutes"] for row in rows]
    deps = [sum(1 << ids[name] for name in row.get("after", [])) for row in rows]
    due = [budget] * len(rows)
    for gate in gates["gates"]:
        for name in gate["tasks"]:
            due[ids[name]] = min(due[ids[name]], gate["due"])
    all_done = (1 << len(rows)) - 1
    states = {(0, ())}
    for minute in range(budget + 1):
        if any(done == all_done for done, _ in states):
            return True
        if minute == budget:
            break
        next_states = set()
        for done, active in states:
            running_ids = {i for i, _ in active}
            ready = [i for i in range(len(rows)) if not done & (1 << i)
                     and i not in running_ids and deps[i] & ~done == 0]
            capacity = min(workers - len(active), len(ready))
            for size in range(capacity + 1):
                for chosen in combinations(ready, size):
                    if not chosen and not active:
                        continue
                    running = active + tuple((i, durations[i]) for i in chosen)
                    following_done, following_active = done, []
                    late = False
                    for i, remaining in running:
                        if remaining == 1:
                            following_done |= 1 << i
                            late |= minute + 1 > due[i]
                        else:
                            following_active.append((i, remaining - 1))
                    if not late:
                        next_states.add((following_done, tuple(sorted(following_active))))
        states = next_states
    return False


class CrewfitTests(unittest.TestCase):
    def test_demo_proven_and_plan_checked(self):
        tasks, gates, budget = crewfit.demo()
        result = crewfit.solve(tasks, gates, budget)
        self.assertEqual(result["status"], "minimum_proven")
        self.assertEqual(result["workers"], 2)
        self.assertEqual([row["status"] for row in result["attempts"]],
                         ["infeasible", "feasible"])
        self.assertEqual(result["plan"]["finish"], 4)
        self.assertTrue(crewfit.plancheck.check(tasks, result["plan"], 2, budget)["valid"])
        self.assertTrue(crewfit.gatecheck.check(tasks, result["plan"], gates, 2, budget)["valid"])

    def test_impossible_even_with_four(self):
        tasks, gates, _ = crewfit.demo()
        result = crewfit.solve(tasks, gates, 2)
        self.assertEqual(result["status"], "infeasible_up_to_max_workers")
        self.assertEqual(len(result["attempts"]), 4)
        self.assertTrue(result["infeasibility_proven"])

    def test_candidate_does_not_claim_minimum(self):
        tasks, gates, budget = crewfit.demo()
        real_solve = crewfit.gateplan.solve

        def capped_once(data, deadlines, workers, final, limit):
            if workers == 1:
                raise ValueError(crewfit.STATE_LIMIT_MESSAGE)
            return real_solve(data, deadlines, workers, final, limit)

        with patch.object(crewfit.gateplan, "solve", side_effect=capped_once):
            result = crewfit.solve(tasks, gates, budget)
        self.assertEqual(result["status"], "candidate")
        self.assertFalse(result["minimum_proven"])
        self.assertEqual(result["workers"], 2)

    def test_all_unknown_is_inconclusive(self):
        tasks, gates, budget = crewfit.demo()
        with patch.object(crewfit.gateplan, "solve",
                          side_effect=ValueError(crewfit.STATE_LIMIT_MESSAGE)):
            result = crewfit.solve(tasks, gates, budget, max_workers=2)
        self.assertEqual(result["status"], "inconclusive")
        self.assertNotIn("plan", result)

    def test_bad_inputs(self):
        tasks, gates, budget = crewfit.demo()
        for options in ({"max_workers": True}, {"max_workers": 5},
                        {"max_states": 0}, {"budget": 1.5}):
            call = {"tasks": tasks, "gates": gates, "budget": budget}
            call.update(options)
            with self.subTest(options=options), self.assertRaises(ValueError):
                crewfit.solve(**call)
        with self.assertRaises(ValueError):
            crewfit.solve(tasks, {"gates": []}, budget)
        with self.assertRaises(ValueError):
            crewfit.solve(tasks, {"gates": [{"id": "x", "tasks": ["missing"], "due": 1}]}, budget)

    def test_cli_demo_and_nonproof_exit(self):
        command = [sys.executable, "-B", str(HERE / "crewfit.py"), "--demo"]
        good = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertEqual(json.loads(good.stdout)["workers"], 2)
        refused = subprocess.run(command + ["--max-states", "1"],
                                 capture_output=True, text=True, check=False)
        self.assertEqual(refused.returncode, 2, refused.stderr)
        self.assertFalse(json.loads(refused.stdout)["minimum_proven"])

    def test_seeded_independent_minute_grid(self):
        rng = random.Random(3501)
        for case in range(60):
            count = rng.randint(2, 5)
            tasks = {"tasks": []}
            for i in range(count):
                after = [f"t{j}" for j in range(i) if rng.random() < 0.28]
                tasks["tasks"].append({"id": f"t{i}", "minutes": rng.randint(1, 3),
                                       "after": after})
            budget = rng.randint(2, 8)
            target = f"t{rng.randrange(count)}"
            gates = {"gates": [{"id": "handoff", "tasks": [target],
                                  "due": rng.randint(1, budget)}]}
            expected = next((workers for workers in range(1, 4)
                             if minute_grid(tasks, gates, workers, budget)), None)
            found = crewfit.solve(tasks, gates, budget, max_workers=3)
            with self.subTest(case=case):
                if expected is None:
                    self.assertEqual(found["status"], "infeasible_up_to_max_workers")
                else:
                    self.assertEqual(found["status"], "minimum_proven")
                    self.assertEqual(found["workers"], expected)
                    self.assertTrue(crewfit.gatecheck.check(
                        tasks, found["plan"], gates, expected, budget)["valid"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
