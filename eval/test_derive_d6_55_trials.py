"""Offline checks for the local D6 65-to-55 trial selection."""

import unittest

from eval.derive_d6_55_trials import filter_judgement_results, keep_row, validate_source


class D6DerivationTests(unittest.TestCase):

    def test_selection_retains_negative_trials_one_to_three_only(self):
        ordinary = {"case_id": "ordinary", "case_type": "ordinary", "trial": 1}
        negative = [
            {"case_id": "negative", "case_type": "negative", "trial": trial}
            for trial in range(1, 5)
        ]
        self.assertTrue(keep_row(ordinary))
        self.assertEqual([row["trial"] for row in negative if keep_row(row)], [1, 2, 3])

    def test_judgement_results_are_selected_by_input_hash(self):
        rows = [
            {"judge_input_sha256": "keep"},
            {"judge_input_sha256": "exclude"},
        ]
        self.assertEqual(filter_judgement_results(rows, {"keep"}), [rows[0]])

    def test_source_shape_requires_the_completed_65_trial_battery(self):
        rows = [
            {"case_id": f"ordinary-{number}", "case_type": "ordinary", "trial": 1}
            for number in range(25)
        ]
        rows.extend(
            {"case_id": f"negative-{number}", "case_type": "negative", "trial": trial}
            for number in range(10)
            for trial in range(1, 5)
        )
        validate_source(rows, {"trial_count": 65})


if __name__ == "__main__":
    unittest.main()
