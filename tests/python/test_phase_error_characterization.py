"""Tests for development-only phase error characterization."""

from __future__ import annotations

import unittest

from scripts.validation_corpus.phase_error_characterization import (
    build_features,
    candidate_rows,
    strata_rows,
    transition_rows,
    window_row,
)
from scripts.validation_corpus.phase_hypotheses import HYPOTHESIS_COLUMNS
from scripts.validation_corpus.phase_interpretation_dataset import (
    DEVELOPMENT_WINDOW_COLUMNS,
)


def development_window(
    *,
    window_id: str,
    start: int,
    zero: float,
    impurity: float,
) -> dict[str, str]:
    row = {column: "" for column in DEVELOPMENT_WINDOW_COLUMNS}
    row.update(
        {
            "window_id": window_id,
            "validation_case_id": "AB0001",
            "source_group_id": "AB0001",
            "specimen_group_id": "AB0001",
            "truth_class": "unknown",
            "truth_method": "reviewer_proxy",
            "include_in_threshold_fit": "true",
            "holdout_group": "phase-development-v1",
            "read_sha256": "a" * 64,
            "sequencing_run_id": "run-1",
            "amplicon_id": "HV1",
            "declared_direction": "F",
            "orientation": "forward",
            "tract_id": "HV1_C",
            "interrupt_aligned_base": "C",
            "start_distance_after_tract": str(start),
            "end_distance_after_tract": str(start + 24),
            "start_call_index_0based": str(100 + start),
            "end_call_index_0based": str(124 + start),
            "profile_observations": "25",
            "noisy_observations": "0",
            "mean_profile_impurity": str(impurity),
            "mean_zero_reference_mass": str(zero),
        }
    )
    return row


def candidate(
    window_id: str,
    offset: int,
    informative: int,
    zero: float,
    shifted: float,
    residual: float,
) -> dict[str, str]:
    row = {column: "" for column in HYPOTHESIS_COLUMNS}
    row.update(
        {
            "window_id": window_id,
            "reference_offset_in_read_order": str(offset),
            "informative_positions": str(informative),
            "mean_zero_reference_mass": str(zero),
            "mean_shifted_reference_mass": str(shifted),
            "mean_residual_mass": str(residual),
        }
    )
    return row


def difference(difference_id: str, kind: str) -> dict[str, str]:
    return {
        "difference_id": difference_id,
        "sample_id": "LN_26_AB0001",
        "validation_case_id": "AB0001",
        "difference": kind,
        "event_kind": "SNV",
        "event_position_1based": "16209",
        "event_reference": "T",
        "event_alternate": "A",
        "reference_footprint_start_1based": "16209",
        "reference_footprint_end_1based": "16209",
        "insertion_boundary_after_1based": "",
        "source_events": "SNV:16209:T>A",
        "phase_observations": "1",
        "phase_reads": "1",
        "exact_phase_windows": "1",
    }


def link(difference_id: str, window_id: str, position: int) -> dict[str, str]:
    return {
        "difference_id": difference_id,
        "validation_case_id": "AB0001",
        "read_sha256": "a" * 64,
        "tract_id": "HV1_C",
        "position_1based": str(position),
        "read_order_distance_from_tract": "16",
        "window_id": window_id,
        "window_start_distance_after_tract": "1",
        "window_end_distance_after_tract": "25",
        "window_start_call_index_0based": "101",
        "window_end_call_index_0based": "125",
        "window_profile_observations": "25",
        "window_noisy_observations": "0",
        "window_mean_profile_impurity": "0.2",
        "window_mean_zero_reference_mass": "0.6",
    }


class PhaseErrorCharacterizationTests(unittest.TestCase):
    def test_build_features_keeps_absolute_nonzero_and_deduplicates_links(self) -> None:
        windows = [
            development_window(window_id="w1", start=1, zero=0.60, impurity=0.20),
            development_window(window_id="w2", start=6, zero=0.92, impurity=0.04),
        ]
        candidates = [
            candidate("w1", -1, 20, 0.60, 0.30, 0.10),
            candidate("w1", 1, 20, 0.60, 0.10, 0.30),
            candidate("w2", -1, 20, 0.90, 0.09, 0.01),
            candidate("w2", 1, 20, 0.90, 0.02, 0.08),
        ]
        differences = [difference("d-extra", "extra")]
        links = [
            link("d-extra", "w1", 16209),
            link("d-extra", "w1", 16210),
        ]

        features = build_features(windows, candidates, differences, links)

        self.assertEqual(len(features), 2)
        first, second = features
        self.assertEqual(first.overlap_context, "extra")
        self.assertEqual(len(first.difference_ids), 1)
        self.assertEqual(second.overlap_context, "none")

        first_row = window_row(first)
        second_row = window_row(second)
        self.assertAlmostEqual(float(first_row["candidate_nonzero_mass_max"]), 0.40)
        self.assertAlmostEqual(
            float(first_row["candidate_structured_fraction_max"]),
            0.75,
        )
        self.assertAlmostEqual(float(second_row["candidate_nonzero_mass_max"]), 0.10)
        self.assertAlmostEqual(
            float(second_row["candidate_structured_fraction_max"]),
            0.90,
        )
        self.assertGreater(
            float(second_row["candidate_structured_fraction_max"]),
            float(first_row["candidate_structured_fraction_max"]),
        )
        self.assertLess(
            float(second_row["candidate_nonzero_mass_max"]),
            float(first_row["candidate_nonzero_mass_max"]),
        )

        candidate_output = candidate_rows(features)
        high_ratio = next(
            row
            for row in candidate_output
            if row["window_id"] == "w2" and row["reference_offset_in_read_order"] == -1
        )
        self.assertAlmostEqual(float(high_ratio["nonzero_mass"]), 0.10)
        self.assertAlmostEqual(float(high_ratio["structured_fraction"]), 0.90)

    def test_transitions_are_ordered_signed_deltas_without_recovery_label(self) -> None:
        features = build_features(
            [
                development_window(window_id="w1", start=1, zero=0.60, impurity=0.20),
                development_window(window_id="w2", start=6, zero=0.90, impurity=0.05),
            ],
            [
                candidate("w1", -1, 20, 0.60, 0.30, 0.10),
                candidate("w1", 1, 20, 0.60, 0.10, 0.30),
                candidate("w2", -1, 20, 0.90, 0.08, 0.02),
                candidate("w2", 1, 20, 0.90, 0.02, 0.08),
            ],
            [difference("d-extra", "extra")],
            [link("d-extra", "w1", 16209)],
        )
        windows = [window_row(item) for item in features]

        transitions = transition_rows(windows)

        self.assertEqual(len(transitions), 1)
        row = transitions[0]
        self.assertEqual(row["left_window_id"], "w1")
        self.assertEqual(row["right_window_id"], "w2")
        self.assertEqual(row["start_distance_delta"], 5)
        self.assertEqual(row["left_overlap_context"], "extra")
        self.assertEqual(row["right_overlap_context"], "none")
        self.assertAlmostEqual(float(row["zero_reference_mass_delta"]), 0.30)
        self.assertLess(float(row["candidate_nonzero_mass_max_delta"]), 0.0)
        self.assertNotIn("recovered", row)
        self.assertNotIn("state", row)

        strata = strata_rows(windows, features)
        by_context = {row["overlap_context"]: row for row in strata}
        self.assertEqual(by_context["extra"]["biological_differences"], 1)
        self.assertEqual(by_context["none"]["biological_differences"], 0)

    def test_context_window_must_exist_in_development_dataset(self) -> None:
        with self.assertRaisesRegex(ValueError, "absent from development dataset"):
            build_features(
                [development_window(window_id="w1", start=1, zero=0.9, impurity=0.1)],
                [
                    candidate("w1", -1, 20, 0.9, 0.05, 0.05),
                    candidate("w1", 1, 20, 0.9, 0.05, 0.05),
                ],
                [difference("d-extra", "extra")],
                [link("d-extra", "unknown-window", 16209)],
            )


if __name__ == "__main__":
    unittest.main()
