"""Tests for threshold-free post-poly-C phase explainability."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.validation_corpus.filesystem import file_sha256
from scripts.validation_corpus.model import (
    PHASE_EXPLAINABILITY_SCHEMA_VERSION,
    PHASE_HYPOTHESIS_SCHEMA_VERSION,
)
from scripts.validation_corpus.phase_explainability import (
    READ_COLUMNS,
    STRATA_COLUMNS,
    WINDOW_COLUMNS,
    publish_phase_explainability,
)
from scripts.validation_corpus.phase_hypotheses import (
    HYPOTHESIS_COLUMNS,
    WINDOW_COLUMNS as SOURCE_WINDOW_COLUMNS,
)


class PhaseExplainabilityResearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="signal-phase-explainability-test-"
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
        impurity: float,
        zero_mass: float,
    ) -> dict[str, str]:
        row = {column: "" for column in SOURCE_WINDOW_COLUMNS}
        row.update(
            {
                "window_id": window_id,
                "validation_case_id": f"case-{read_sha256[0]}",
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
                "mean_profile_impurity": str(impurity),
                "mean_zero_reference_mass": str(zero_mass),
            }
        )
        return row

    @staticmethod
    def hypothesis_row(
        window_id: str,
        offset: int,
        informative: int,
        zero: float | None,
        shifted: float | None,
        residual: float | None,
    ) -> dict[str, str]:
        return {
            "window_id": window_id,
            "reference_offset_in_read_order": str(offset),
            "informative_positions": str(informative),
            "mean_zero_reference_mass": "" if zero is None else str(zero),
            "mean_shifted_reference_mass": "" if shifted is None else str(shifted),
            "mean_residual_mass": "" if residual is None else str(residual),
        }

    def write_source(self) -> None:
        windows = [
            self.window_row("c-1", "1" * 64, "C", 1, 0.30, 0.65),
            self.window_row("c-2", "1" * 64, "C", 6, 0.20, 0.75),
            self.window_row("t-1", "2" * 64, "T", 1, 0.02, 0.97),
        ]
        hypotheses = [
            self.hypothesis_row("c-1", -1, 20, 0.60, 0.30, 0.10),
            self.hypothesis_row("c-1", 1, 20, 0.60, 0.10, 0.30),
            self.hypothesis_row("c-2", -1, 20, 0.50, 0.20, 0.30),
            self.hypothesis_row("c-2", 1, 20, 0.50, 0.15, 0.35),
            self.hypothesis_row("t-1", -1, 0, None, None, None),
            self.hypothesis_row("t-1", 1, 0, None, None, None),
        ]

        windows_path = self.source / "windows.csv"
        window_columns: list[str] = list(SOURCE_WINDOW_COLUMNS)
        with windows_path.open("w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(
                target,
                fieldnames=window_columns,
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(windows)

        hypotheses_path = self.source / "hypotheses.csv"
        hypothesis_columns: list[str] = list(HYPOTHESIS_COLUMNS)
        with hypotheses_path.open("w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(
                target,
                fieldnames=hypothesis_columns,
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
            "windows_columns": list(SOURCE_WINDOW_COLUMNS),
            "hypotheses_file": "hypotheses.csv",
            "hypotheses_sha256": file_sha256(hypotheses_path),
            "hypotheses_rows": len(hypotheses),
            "hypotheses_columns": list(HYPOTHESIS_COLUMNS),
        }
        (self.source / "index.json").write_text(
            json.dumps(index, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def test_publishes_window_read_and_strata_envelopes(self) -> None:
        self.write_source()
        output = self.root / "explainability"
        publish_phase_explainability(self.source, output)

        index = json.loads((output / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(
            index["schema_version"],
            PHASE_EXPLAINABILITY_SCHEMA_VERSION,
        )
        self.assertEqual(
            index["source_phase_hypotheses_sha256"],
            file_sha256(self.source / "index.json"),
        )
        self.assertEqual(index["windows_rows"], 3)
        self.assertEqual(index["reads_rows"], 2)
        self.assertEqual(index["strata_rows"], 2)
        self.assertEqual(index["method"]["candidate_selection"], "none; no winning offset or identity is emitted")
        self.assertEqual(index["method"]["thresholds"], "none")

        with (output / "windows.csv").open(
            "r", encoding="utf-8", newline=""
        ) as source:
            windows = list(csv.DictReader(source))
        self.assertEqual(tuple(windows[0]), WINDOW_COLUMNS)
        c1 = next(row for row in windows if row["window_id"] == "c-1")
        self.assertEqual(c1["candidate_count"], "2")
        self.assertEqual(c1["informative_candidates"], "2")
        self.assertEqual(c1["explainability_candidates"], "2")
        self.assertAlmostEqual(
            float(c1["candidate_shifted_reference_mass_min"]),
            0.10,
        )
        self.assertAlmostEqual(
            float(c1["candidate_shifted_reference_mass_max"]),
            0.30,
        )
        self.assertAlmostEqual(
            float(c1["candidate_shifted_reference_mass_range"]),
            0.20,
        )
        self.assertAlmostEqual(float(c1["candidate_residual_mass_min"]), 0.10)
        self.assertAlmostEqual(float(c1["candidate_residual_mass_max"]), 0.30)
        self.assertAlmostEqual(
            float(c1["candidate_explainable_nonzero_fraction_max"]),
            0.75,
        )
        self.assertNotIn("reference_offset_in_read_order", c1)

        t1 = next(row for row in windows if row["window_id"] == "t-1")
        self.assertEqual(t1["informative_candidates"], "0")
        self.assertEqual(t1["explainability_candidates"], "0")
        self.assertEqual(t1["candidate_shifted_reference_mass_max"], "")
        self.assertEqual(t1["candidate_residual_mass_min"], "")
        self.assertEqual(t1["candidate_explainable_nonzero_fraction_max"], "")

        with (output / "reads.csv").open("r", encoding="utf-8", newline="") as source:
            reads = list(csv.DictReader(source))
        self.assertEqual(tuple(reads[0]), READ_COLUMNS)
        c_read = next(row for row in reads if row["read_sha256"] == "1" * 64)
        self.assertEqual(c_read["windows"], "2")
        self.assertAlmostEqual(float(c_read["mean_window_profile_impurity"]), 0.25)
        self.assertAlmostEqual(float(c_read["max_window_profile_impurity"]), 0.30)
        self.assertAlmostEqual(
            float(c_read["mean_candidate_shifted_reference_mass_max"]),
            0.25,
        )
        self.assertAlmostEqual(
            float(c_read["max_candidate_residual_mass_min"]),
            0.30,
        )
        self.assertAlmostEqual(
            float(c_read["mean_candidate_explainable_nonzero_fraction_max"]),
            0.575,
        )
        self.assertAlmostEqual(
            float(c_read["min_candidate_explainable_nonzero_fraction_max"]),
            0.40,
        )

        t_read = next(row for row in reads if row["read_sha256"] == "2" * 64)
        self.assertEqual(t_read["windows_without_informative_candidates"], "1")
        self.assertEqual(t_read["windows_without_explainability_candidates"], "1")
        self.assertEqual(t_read["mean_candidate_residual_mass_min"], "")

        with (output / "strata.csv").open(
            "r", encoding="utf-8", newline=""
        ) as source:
            strata = list(csv.DictReader(source))
        self.assertEqual(tuple(strata[0]), STRATA_COLUMNS)
        c_stratum = next(
            row for row in strata if row["interrupt_aligned_base"] == "C"
        )
        self.assertEqual(c_stratum["reads"], "1")
        self.assertEqual(c_stratum["windows"], "2")
        self.assertAlmostEqual(
            float(c_stratum["mean_candidate_shifted_reference_mass_max"]),
            0.25,
        )

    def test_no_overwrite_and_source_hash_mismatch_are_rejected(self) -> None:
        self.write_source()
        output = self.root / "explainability"
        publish_phase_explainability(self.source, output)
        with self.assertRaisesRegex(ValueError, "already exists"):
            publish_phase_explainability(self.source, output)

        with (self.source / "hypotheses.csv").open("a", encoding="utf-8") as target:
            target.write("\n")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            publish_phase_explainability(self.source, self.root / "hash-mismatch")


if __name__ == "__main__":
    unittest.main()
