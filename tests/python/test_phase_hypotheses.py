"""Tests for Tracy-inspired post-poly-C candidate phase hypotheses."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.validation_corpus.filesystem import file_sha256
from scripts.validation_corpus.model import (
    PHASE_HYPOTHESIS_SCHEMA_VERSION,
    POLYC_PHASE_SCHEMA_VERSION,
)
from scripts.validation_corpus.phase_hypotheses import (
    PhaseObservation,
    candidate_metrics,
    phase_windows,
    publish_phase_hypotheses,
)
from scripts.validation_corpus.polyc_phase import (
    OBSERVATION_COLUMNS,
    SUMMARY_COLUMNS,
)

BASES = ("A", "C", "G", "T")


class PhaseHypothesisResearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="signal-phase-hypothesis-test-"
        )
        self.root = Path(self.temporary.name)
        self.phase = self.root / "phase"
        self.phase.mkdir()
        self.read_sha256 = "1" * 64

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def reference_base(distance: int) -> str:
        return BASES[(distance - 1) % len(BASES)]

    @classmethod
    def profile(cls, distance: int) -> tuple[float, float, float, float]:
        current = cls.reference_base(distance)
        shifted = cls.reference_base(distance + 1)
        opposite = cls.reference_base(distance + 2)
        weights = {base: 0.0 for base in BASES}
        weights[current] = 0.60
        weights[shifted] = 0.35
        weights[opposite] = 0.05
        return (
            weights["A"],
            weights["C"],
            weights["G"],
            weights["T"],
        )

    def source_row(self, distance: int) -> dict[str, str]:
        values = self.profile(distance)
        row = {column: "" for column in OBSERVATION_COLUMNS}
        row.update(
            {
                "validation_case_id": "case-1",
                "source_group_id": "source-1",
                "specimen_group_id": "specimen-1",
                "read_sha256": self.read_sha256,
                "amplicon_id": "HV2",
                "declared_direction": "forward",
                "orientation": "forward",
                "tract_id": "HV2_C",
                "tract_start_1based": "303",
                "tract_end_1based": "315",
                "interrupt_position_1based": "310",
                "position_1based": str(315 + distance),
                "path_region": "after",
                "read_order_distance_from_tract": str(distance),
                "call_index_0based": str(100 + distance),
                "call_distance_from_tract": str(distance),
                "reference_base": self.reference_base(distance),
                "state": "reference",
                "aligned_base": self.reference_base(distance),
                "quality": "60",
                "in_noisy_region": "false",
                "profile_a": str(values[0]),
                "profile_c": str(values[1]),
                "profile_g": str(values[2]),
                "profile_t": str(values[3]),
                "profile_impurity": "0.4",
                "interrupt_state": "alternate",
                "interrupt_aligned_base": "C",
                "interrupt_call_index_0based": "100",
                "interrupt_in_noisy_region": "false",
            }
        )
        return row

    def write_source(self, count: int = 40) -> None:
        observations = self.phase / "observations.csv"
        with observations.open("w", encoding="utf-8", newline="") as target:
            observation_columns: list[str] = list(OBSERVATION_COLUMNS)
            writer = csv.DictWriter(
                target,
                fieldnames=observation_columns,
                lineterminator="\n",
            )
            writer.writeheader()
            for distance in range(1, count + 1):
                writer.writerow(self.source_row(distance))

        summary = self.phase / "summary.csv"
        with summary.open("w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(
                target,
                fieldnames=list(SUMMARY_COLUMNS),
                lineterminator="\n",
            )
            writer.writeheader()

        index = {
            "schema_version": POLYC_PHASE_SCHEMA_VERSION,
            "source_corpus_sha256": "a" * 64,
            "signal_version": "0.1.0",
            "manifest_sha256": "b" * 64,
            "reference_sha256": "c" * 64,
            "configuration_sha256": "d" * 64,
            "method": {"reference_topology": "rCRS"},
            "crossing_reads": 1,
            "observations_file": "observations.csv",
            "observations_sha256": file_sha256(observations),
            "observations_rows": count,
            "observations_columns": list(OBSERVATION_COLUMNS),
            "summary_file": "summary.csv",
            "summary_sha256": file_sha256(summary),
            "summary_rows": 0,
            "summary_columns": list(SUMMARY_COLUMNS),
        }
        (self.phase / "index.json").write_text(
            json.dumps(index, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def test_candidate_curve_preserves_shift_and_residual_mass(self) -> None:
        self.write_source()
        output = self.root / "hypotheses"

        publish_phase_hypotheses(
            self.phase,
            output,
            window_size=25,
            window_step=25,
            max_offset=2,
        )

        index = json.loads((output / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(index["schema_version"], PHASE_HYPOTHESIS_SCHEMA_VERSION)
        self.assertEqual(index["windows_rows"], 1)
        self.assertEqual(index["hypotheses_rows"], 4)
        self.assertEqual(index["method"]["candidate_offsets"], [-2, -1, 1, 2])
        self.assertEqual(
            index["source_polyc_phase_sha256"],
            file_sha256(self.phase / "index.json"),
        )

        with (output / "windows.csv").open("r", encoding="utf-8", newline="") as source:
            windows = list(csv.DictReader(source))
        self.assertEqual(windows[0]["profile_observations"], "25")
        self.assertAlmostEqual(float(windows[0]["mean_zero_reference_mass"]), 0.60)

        with (output / "hypotheses.csv").open(
            "r", encoding="utf-8", newline=""
        ) as source:
            hypotheses = list(csv.DictReader(source))
        plus_one = next(
            row for row in hypotheses if row["reference_offset_in_read_order"] == "1"
        )
        minus_one = next(
            row for row in hypotheses if row["reference_offset_in_read_order"] == "-1"
        )
        self.assertEqual(plus_one["informative_positions"], "25")
        self.assertAlmostEqual(float(plus_one["mean_zero_reference_mass"]), 0.60)
        self.assertAlmostEqual(float(plus_one["mean_shifted_reference_mass"]), 0.35)
        self.assertAlmostEqual(float(plus_one["mean_residual_mass"]), 0.05)
        self.assertAlmostEqual(float(minus_one["mean_shifted_reference_mass"]), 0.0)
        self.assertAlmostEqual(float(minus_one["mean_residual_mass"]), 0.40)

    def test_same_reference_base_is_not_informative(self) -> None:
        observation = PhaseObservation(
            validation_case_id="case-1",
            read_sha256=self.read_sha256,
            tract_id="HV2_C",
            amplicon_id="HV2",
            orientation="forward",
            interrupt_aligned_base="C",
            position_1based=316,
            distance=1,
            call_index=101,
            reference_base="A",
            state="reference",
            aligned_base="A",
            in_noisy_region=False,
            profile=(0.7, 0.1, 0.1, 0.1),
            profile_impurity=0.3,
        )
        informative, zero, shifted, residual = candidate_metrics(
            (observation,),
            {1: "A", 2: "A"},
            1,
        )
        self.assertEqual(informative, 0)
        self.assertIsNone(zero)
        self.assertIsNone(shifted)
        self.assertIsNone(residual)

    def test_window_membership_uses_profiled_observations_only(self) -> None:
        profiled = [
            PhaseObservation(
                validation_case_id="case-1",
                read_sha256=self.read_sha256,
                tract_id="HV2_C",
                amplicon_id="HV2",
                orientation="forward",
                interrupt_aligned_base="C",
                position_1based=315 + distance,
                distance=distance,
                call_index=100 + distance,
                reference_base=self.reference_base(distance),
                state="reference",
                aligned_base=self.reference_base(distance),
                in_noisy_region=False,
                profile=self.profile(distance) if distance != 3 else None,
                profile_impurity=0.4 if distance != 3 else None,
            )
            for distance in range(1, 7)
        ]
        windows = phase_windows(
            {(self.read_sha256, "HV2_C"): profiled},
            window_size=5,
            window_step=5,
        )
        self.assertEqual(len(windows), 1)
        self.assertEqual(
            [row.distance for row in windows[0].observations],
            [1, 2, 4, 5, 6],
        )
        self.assertEqual(
            windows[0].window_id,
            f"HV2_C:{self.read_sha256}:1-6",
        )

    def test_source_hash_mismatch_is_rejected(self) -> None:
        self.write_source()
        with (self.phase / "observations.csv").open("a", encoding="utf-8") as target:
            target.write("\n")

        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            publish_phase_hypotheses(self.phase, self.root / "hypotheses")

    def test_no_overwrite_and_parameter_validation(self) -> None:
        self.write_source()
        output = self.root / "hypotheses"
        publish_phase_hypotheses(
            self.phase,
            output,
            window_size=25,
            window_step=25,
            max_offset=2,
        )

        with self.assertRaisesRegex(ValueError, "already exists"):
            publish_phase_hypotheses(self.phase, output)

        with self.assertRaisesRegex(ValueError, "must be positive"):
            publish_phase_hypotheses(
                self.phase,
                self.root / "invalid",
                window_size=0,
            )


if __name__ == "__main__":
    unittest.main()
