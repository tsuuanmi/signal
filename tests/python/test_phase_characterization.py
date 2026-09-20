"""Tests for descriptive post-poly-C phase-hypothesis characterization."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.validation_corpus.filesystem import file_sha256
from scripts.validation_corpus.model import (
    PHASE_CHARACTERIZATION_SCHEMA_VERSION,
    PHASE_HYPOTHESIS_SCHEMA_VERSION,
)
from scripts.validation_corpus.phase_characterization import (
    PERSISTENCE_COLUMNS,
    STRATA_COLUMNS,
    TRAJECTORY_COLUMNS,
    publish_phase_characterization,
)
from scripts.validation_corpus.phase_hypotheses import (
    HYPOTHESIS_COLUMNS,
    WINDOW_COLUMNS,
)


class PhaseCharacterizationResearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="signal-phase-characterization-test-"
        )
        self.root = Path(self.temporary.name)
        self.source = self.root / "hypotheses"
        self.source.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def window_row(
        window_id: str,
        read_sha256: str,
        interrupt: str,
        start: int,
    ) -> dict[str, str]:
        row = {column: "" for column in WINDOW_COLUMNS}
        row.update(
            {
                "window_id": window_id,
                "validation_case_id": f"case-{interrupt}",
                "read_sha256": read_sha256,
                "tract_id": "HV2_C",
                "amplicon_id": "HV2",
                "orientation": "forward",
                "interrupt_aligned_base": interrupt,
                "start_distance_after_tract": str(start),
                "end_distance_after_tract": str(start + 24),
                "start_call_index_0based": str(100 + start),
                "end_call_index_0based": str(124 + start),
                "profile_observations": "25",
                "noisy_observations": "5",
                "mean_profile_impurity": "0.25",
                "mean_zero_reference_mass": "0.75",
            }
        )
        return row

    @staticmethod
    def hypothesis_row(
        window_id: str,
        offset: int,
        zero: float,
        shifted: float,
        residual: float,
    ) -> dict[str, str]:
        return {
            "window_id": window_id,
            "reference_offset_in_read_order": str(offset),
            "informative_positions": "20",
            "mean_zero_reference_mass": str(zero),
            "mean_shifted_reference_mass": str(shifted),
            "mean_residual_mass": str(residual),
        }

    def write_source(self) -> None:
        windows = [
            self.window_row("c-1", "1" * 64, "C", 1),
            self.window_row("c-2", "1" * 64, "C", 6),
            self.window_row("c-3", "1" * 64, "C", 11),
            self.window_row("t-1", "2" * 64, "T", 1),
        ]
        hypotheses = [
            self.hypothesis_row("c-1", -1, 0.80, 0.08, 0.12),
            self.hypothesis_row("c-1", 1, 0.65, 0.30, 0.05),
            self.hypothesis_row("c-2", -1, 0.80, 0.09, 0.11),
            self.hypothesis_row("c-2", 1, 0.64, 0.32, 0.04),
            self.hypothesis_row("c-3", -1, 0.80, 0.07, 0.13),
            self.hypothesis_row("c-3", 1, 0.63, 0.31, 0.06),
            self.hypothesis_row("t-1", -1, 0.80, 0.05, 0.15),
            self.hypothesis_row("t-1", 1, 0.80, 0.10, 0.10),
        ]

        windows_path = self.source / "windows.csv"
        with windows_path.open("w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(
                target,
                fieldnames=list(WINDOW_COLUMNS),
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(windows)

        hypotheses_path = self.source / "hypotheses.csv"
        with hypotheses_path.open("w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(
                target,
                fieldnames=list(HYPOTHESIS_COLUMNS),
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(hypotheses)

        index = {
            "schema_version": PHASE_HYPOTHESIS_SCHEMA_VERSION,
            "source_polyc_phase_sha256": "a" * 64,
            "source_corpus_sha256": "b" * 64,
            "signal_version": "0.1.0",
            "manifest_sha256": "c" * 64,
            "reference_sha256": "d" * 64,
            "configuration_sha256": "e" * 64,
            "method": {
                "window_size_profile_observations": 25,
                "window_step_profile_observations": 5,
                "max_reference_offset_in_read_order": 1,
                "candidate_offsets": [-1, 1],
                "informative_position_rule": (
                    "unshifted and candidate-shifted reference bases differ"
                ),
                "candidate_evidence": "synthetic test evidence",
                "candidate_selection": "none; complete candidate curve retained",
            },
            "windows_file": "windows.csv",
            "windows_sha256": file_sha256(windows_path),
            "windows_rows": len(windows),
            "windows_columns": list(WINDOW_COLUMNS),
            "hypotheses_file": "hypotheses.csv",
            "hypotheses_sha256": file_sha256(hypotheses_path),
            "hypotheses_rows": len(hypotheses),
            "hypotheses_columns": list(HYPOTHESIS_COLUMNS),
        }
        (self.source / "index.json").write_text(
            json.dumps(index, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def test_publishes_persistence_trajectory_and_interrupt_strata(self) -> None:
        self.write_source()
        output = self.root / "characterization"
        publish_phase_characterization(self.source, output)

        index = json.loads((output / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(index["schema_version"], PHASE_CHARACTERIZATION_SCHEMA_VERSION)
        self.assertEqual(
            index["source_phase_hypotheses_sha256"],
            file_sha256(self.source / "index.json"),
        )
        self.assertEqual(index["persistence_rows"], 4)
        self.assertEqual(index["trajectory_rows"], 8)
        self.assertEqual(index["strata_rows"], 4)
        self.assertEqual(index["method"]["candidate_offsets"], [-1, 1])
        self.assertEqual(
            index["method"]["candidate_selection"],
            "none; every source candidate retained independently",
        )
        self.assertEqual(index["method"]["thresholds"], "none")

        with (output / "persistence.csv").open(
            "r", encoding="utf-8", newline=""
        ) as source:
            persistence = list(csv.DictReader(source))
        first_plus_one = next(
            row
            for row in persistence
            if row["left_window_id"] == "c-1"
            and row["reference_offset_in_read_order"] == "1"
        )
        self.assertAlmostEqual(
            float(first_plus_one["absolute_shifted_reference_mass_delta"]), 0.02
        )
        self.assertAlmostEqual(
            float(first_plus_one["absolute_residual_mass_delta"]), 0.01
        )

        with (output / "strata.csv").open(
            "r", encoding="utf-8", newline=""
        ) as source:
            strata = list(csv.DictReader(source))
        c_plus_one = next(
            row
            for row in strata
            if row["interrupt_aligned_base"] == "C"
            and row["reference_offset_in_read_order"] == "1"
        )
        self.assertEqual(c_plus_one["windows"], "3")
        self.assertEqual(c_plus_one["informative_windows"], "3")
        self.assertAlmostEqual(float(c_plus_one["mean_shifted_reference_mass"]), 0.31)
        self.assertAlmostEqual(float(c_plus_one["mean_residual_mass"]), 0.05)
        self.assertAlmostEqual(float(c_plus_one["mean_window_noisy_fraction"]), 0.2)

        with (output / "trajectory.csv").open(
            "r", encoding="utf-8", newline=""
        ) as source:
            trajectory = list(csv.DictReader(source))
        c_distance_six = next(
            row
            for row in trajectory
            if row["interrupt_aligned_base"] == "C"
            and row["start_distance_after_tract"] == "6"
            and row["reference_offset_in_read_order"] == "1"
        )
        self.assertAlmostEqual(
            float(c_distance_six["mean_shifted_reference_mass"]), 0.32
        )

        self.assertEqual(tuple(persistence[0]), PERSISTENCE_COLUMNS)
        self.assertEqual(tuple(trajectory[0]), TRAJECTORY_COLUMNS)
        self.assertEqual(tuple(strata[0]), STRATA_COLUMNS)
        self.assertNotIn("best_shift", index)
        self.assertNotIn("phase_state", index)
        self.assertNotIn("recovery_distance", index)

    def test_rejects_incomplete_candidate_curve(self) -> None:
        self.write_source()
        hypotheses_path = self.source / "hypotheses.csv"
        with hypotheses_path.open("r", encoding="utf-8", newline="") as source:
            rows = list(csv.DictReader(source))
        with hypotheses_path.open("w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(
                target,
                fieldnames=list(HYPOTHESIS_COLUMNS),
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(rows[:-1])

        index_path = self.source / "index.json"
        index = json.loads(index_path.read_text(encoding="utf-8"))
        index["hypotheses_sha256"] = file_sha256(hypotheses_path)
        index["hypotheses_rows"] = len(rows) - 1
        index_path.write_text(
            json.dumps(index, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "candidate curve differs"):
            publish_phase_characterization(self.source, self.root / "output")

    def test_source_hash_mismatch_is_rejected(self) -> None:
        self.write_source()
        with (self.source / "hypotheses.csv").open("a", encoding="utf-8") as target:
            target.write("\n")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            publish_phase_characterization(self.source, self.root / "hash-mismatch")

    def test_no_overwrite_is_rejected(self) -> None:
        self.write_source()
        output = self.root / "characterization"
        publish_phase_characterization(self.source, output)
        with self.assertRaisesRegex(ValueError, "already exists"):
            publish_phase_characterization(self.source, output)


if __name__ == "__main__":
    unittest.main()
