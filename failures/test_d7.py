"""Offline acceptance tests for D7."""

import unittest

from failures.run_d7 import build_results


class D7Tests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.result = build_results()

    def test_whole_set_distribution_is_complete(self):
        distribution = self.result["whole_evaluation_set"]
        self.assertEqual(distribution["trials"], 105)
        self.assertEqual(distribution["passed"], 105)
        self.assertEqual(distribution["median_turns"], 4)
        self.assertEqual(distribution["worst_turns"], 5)
        self.assertEqual(distribution["step_cap_hits"], 0)

    def test_loop_failure_is_reproduced_and_fixed(self):
        failure = self.result["failure_1_loop_control"]
        self.assertFalse(failure["before"]["outcome_passed"])
        self.assertEqual(
            failure["before"]["stopped_early"],
            "step cap (10 turns) reached",
        )
        self.assertTrue(failure["after"]["outcome_passed"])
        self.assertLess(failure["after"]["turns"], failure["before"]["turns"])
        self.assertLess(
            failure["after"]["estimated_cost_usd"],
            failure["before"]["estimated_cost_usd"],
        )

    def test_interface_failure_is_reproduced_and_fixed(self):
        failure = self.result["failure_2_tool_interface"]
        self.assertEqual(failure["before"]["record"]["trigger"], "coverage_expired")
        self.assertFalse(failure["before"]["outcome_passed"])
        self.assertEqual(
            failure["after"]["record"]["trigger"],
            "outside_policy_dates",
        )
        self.assertTrue(failure["after"]["outcome_passed"])

    def test_no_live_api_cost(self):
        self.assertEqual(self.result["metadata"]["live_api_calls"], 0)
        self.assertEqual(self.result["metadata"]["real_api_cost_usd"], 0.0)


if __name__ == "__main__":
    unittest.main()
