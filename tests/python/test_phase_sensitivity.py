"""Tests for post-poly-C phase parameter-sensitivity research."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.validation_corpus.filesystem import file_sha256
from scripts.validation_corpus.model import (
    PHASE_SENSITIVITY_SCHEMA_VERSION,
    POLYC_PHASE_SCHEMA_VERSION,
)
from scripts.validation_corpus.phase_sensitivity import (
    PARAMETER_COLUMNS,
    STRATA_COLUMNS,
    parameter_grid,
    publish_phase_sensitivity,
)
from scripts.validation_corpus.polyc_phase import OBSERVATION_COLUMNS, SUMMARY_COLUMNS


class PhaseSensitivityResearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="signal-phase-sensitivity-test-"
        )
        self.root = Path(self.temporary.name)
        self.phase = self.root / "phase"
        self.phase.mkdir()
        self.read_sha256 = "1" * 64

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def reference_base(distance: int) -> str:
        return "ACGT"[(distance - 1) % 4]

    def source_row(self, distance: int) -> dict[str, object]:
        reference = self.reference_base(distance)
        shifted = self.reference_base(distance + 1)
        masses = {base: 0.02 for base in "ACGT"}
        masses[reference] = 0.60
        masses[shifted] = 0.34
        remaining = 1.0 - sum(masses.values())
        if remaining:
            residual_base = next(
                base for base in "ACGT" if base not in {reference, shifted}
            )
            masses[residual_base] += remaining

        row: dict[str, object] = {column: None for column in OBSERVATION_COLUMNS}
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
                "tract_start_1based": 303,
                "tract_end_1based": 315,
                "interrupt_position_1based": 310,
                "position_1based": 315 + distance,
                "path_region": "after",
                "read_order_distance_from_tract": distance,
                "call_index_0based": 100 + distance,
                "call_distance_from_tract": distance,
                "reference_base": reference,
                "state": "reference",
                "aligned_base": reference,
                "quality": 60,
                "in_noisy_region": "false",
                "profile_a": masses["A"],
                "profile_c": masses["C"],
                "profile_g": masses["G"],
                "profile_t": masses["T"],
                "profile_impurity": 1.0 - max(masses.values()),
                "interrupt_state": "alternate",
                "interrupt_aligned_base": "C",
                "interrupt_call_index_0based": 100,
                "interrupt_in_noisy_region": "false",
            }
        )
        return row

    def write_source(self, count: int = 45) -> None:
        observations = self.phase / "observations.csv"
        columns: list[str] = list(OBSERVATION_COLUMNS)
        with observations.open("w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(target, fieldnames=columns, lineterminator="\n")
            writer.writeheader()
            for distance in range(1, count + 1):
                writer.writerow(self.source_row(distance))

        summary = self.phase / "summary.csv"
        summary_columns: list[str] = list(SUMMARY_COLUMNS)
        with summary.open("w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(
                target,
                fieldnames=summary_columns,
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

    def test_publishes_full_factorial_candidate_strata(self) -> None:
        self.write_source()
        output = self.root / "sensitivity"
        publish_phase_sensitivity(
            self.phase,
            output,
            window_sizes=(10, 15),
            window_steps=(5,),
            max_offsets=(1, 2),
        )

        index = json.loads((output / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(index["schema_version"], PHASE_SENSITIVITY_SCHEMA_VERSION)
        self.assertEqual(index["parameter_sets_rows"], 4)
        self.assertEqual(index["method"]["grid"], "full factorial")
        self.assertEqual(
            index["method"]["candidate_selection"],
            "none; every candidate retained independently",
        )
        self.assertEqual(index["method"]["thresholds"], "none")
        self.assertEqual(
            index["source_polyc_phase_sha256"],
            file_sha256(self.phase / "index.json"),
        )

        with (output / "parameter_sets.csv").open(
            "r", encoding="utf-8", newline=""
        ) as source:
            parameters = list(csv.DictReader(source))
        self.assertEqual(tuple(parameters[0]), PARAMETER_COLUMNS)
        self.assertEqual(
            {row["parameter_set_id"] for row in parameters},
            {"w10-s5-o1", "w10-s5-o2", "w15-s5-o1", "w15-s5-o2"},
        )
        offset_two = next(
            row for row in parameters if row["parameter_set_id"] == "w10-s5-o2"
        )
        self.assertEqual(offset_two["candidate_offsets"], "-2,-1,1,2")
        self.assertEqual(
            int(offset_two["hypotheses"]),
            int(offset_two["windows"]) * 4,
        )

        with (output / "strata.csv").open("r", encoding="utf-8", newline="") as source:
            strata = list(csv.DictReader(source))
        self.assertEqual(tuple(strata[0]), STRATA_COLUMNS)
        plus_one = [
            row for row in strata if row["reference_offset_in_read_order"] == "1"
        ]
        self.assertEqual(len(plus_one), 4)
        for row in plus_one:
            self.assertEqual(row["interrupt_aligned_base"], "C")
            self.assertGreater(float(row["mean_shifted_reference_mass"]), 0.30)
            self.assertLess(float(row["mean_residual_mass"]), 0.10)

    def test_records_parameter_sets_with_no_complete_windows(self) -> None:
        self.write_source(count=20)
        output = self.root / "sparse-sensitivity"
        publish_phase_sensitivity(
            self.phase,
            output,
            window_sizes=(25,),
            window_steps=(5,),
            max_offsets=(1,),
        )

        with (output / "parameter_sets.csv").open(
            "r", encoding="utf-8", newline=""
        ) as source:
            parameters = list(csv.DictReader(source))
        self.assertEqual(parameters[0]["windows"], "0")
        self.assertEqual(parameters[0]["hypotheses"], "0")

        with (output / "strata.csv").open("r", encoding="utf-8", newline="") as source:
            self.assertEqual(list(csv.DictReader(source)), [])

    def test_parameter_grid_rejects_invalid_or_duplicate_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be unique"):
            parameter_grid((15, 15), (5,), (3,))
        with self.assertRaisesRegex(ValueError, "must be positive"):
            parameter_grid((15,), (0,), (3,))
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            parameter_grid((), (5,), (3,))

    def test_no_overwrite_and_source_hash_mismatch_are_rejected(self) -> None:
        self.write_source()
        output = self.root / "sensitivity"
        publish_phase_sensitivity(
            self.phase,
            output,
            window_sizes=(10,),
            window_steps=(5,),
            max_offsets=(1,),
        )
        with self.assertRaisesRegex(ValueError, "already exists"):
            publish_phase_sensitivity(
                self.phase,
                output,
                window_sizes=(10,),
                window_steps=(5,),
                max_offsets=(1,),
            )

        with (self.phase / "observations.csv").open("a", encoding="utf-8") as target:
            target.write("\n")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            publish_phase_sensitivity(
                self.phase,
                self.root / "hash-mismatch",
                window_sizes=(10,),
                window_steps=(5,),
                max_offsets=(1,),
            )


if __name__ == "__main__":
    unittest.main()
