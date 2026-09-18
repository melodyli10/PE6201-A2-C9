"""Offline regression checks for the D7 production fault injections."""

import json
import os
import unittest
from pathlib import Path

os.environ.setdefault("A2_SKIP_DOTENV", "1")

from eval import run_d7_failures


class D7FailureTests(unittest.TestCase):
    def test_fault_injections_and_recoveries(self):
        self.assertEqual(run_d7_failures.main(), 0)
        path = Path(run_d7_failures.OUTPUT) / "summary.json"
        summary = json.loads(path.read_text(encoding="utf-8"))

        loop = summary["loop_failure"]
        self.assertEqual(loop["before"]["turns"], 10)
        self.assertEqual(loop["after"]["turns"], 2)
        self.assertEqual(loop["before"]["writes"], 0)
        self.assertEqual(loop["after"]["writes"], 0)
        self.assertEqual(loop["d4_before"], loop["d4_after"])
        self.assertEqual(loop["d4_after"]["passing_cases"], 35)

        interface = summary["interface_failure"]
        self.assertEqual(interface["before"]["decision"], "escalate")
        self.assertEqual(interface["after"]["decision"], "request_document")
        self.assertEqual(interface["after"]["missing"], "itemised_bill for line 45378")


if __name__ == "__main__":
    unittest.main()