"""Tests for direct Rust/Python phase-runtime parity checking."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.validation_corpus.filesystem import file_sha256
from scripts.validation_corpus.model import PHASE_HYPOTHESIS_SCHEMA_VERSION
from scripts.validation_corpus.phase_hypotheses import (
    HYPOTHESIS_COLUMNS,
    WINDOW_COLUMNS,
)
from scripts.validation_corpus.phase_runtime_parity import (
    RUNTIME_CANDIDATE_COLUMNS,
    RUNTIME_SCHEMA_VERSION,
    RUNTIME_SOURCE_METHOD,
    RUNTIME_WINDOW_COLUMNS,
    compare_phase_runtime,
)


class PhaseRuntimeParityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="signal-phase-parity-test-")
        self.root = Path(self.temporary.name)
        self.research = self.root / "research"
        self.runtime_root = self.root / "runtime"
        self.runtime = self.runtime_root / "case-1.phase-runtime"
        self.research.mkdir()
        self.runtime.mkdir(parents=True)
        self.read_sha256 = "1" * 64
        self.reference_sha256 = "a" * 64
        self.configuration_sha256 = "b" * 64

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def offsets() -> list[int]:
        return [*range(-5, 0), *range(1, 6)]

    def research_window(self) -> dict[str, str]:
        row = {column: "" for column in WINDOW_COLUMNS}
        row.update(
            {
                "window_id": f"HV2_C:{self.read_sha256}:1-25",
                "validation_case_id": "case-1",
                "read_sha256": self.read_sha256,
                "tract_id": "HV2_C",
                "amplicon_id": "HV2",
                "orientation": "forward",
                "interrupt_aligned_base": "T",
                "start_distance_after_tract": "1",
                "end_distance_after_tract": "25",
                "start_call_index_0based": "100",
                "end_call_index_0based": "124",
                "profile_observations": "25",
                "noisy_observations": "0",
                "mean_profile_impurity": "0.2",
                "mean_zero_reference_mass": "0.8",
            }
        )
        return row

    def research_candidate(self, offset: int) -> dict[str, str]:
        return {
            "window_id": f"HV2_C:{self.read_sha256}:1-25",
            "reference_offset_in_read_order": str(offset),
            "informative_positions": "20",
            "mean_zero_reference_mass": "0.6",
            "mean_shifted_reference_mass": "0.3",
            "mean_residual_mass": "0.1",
        }

    def runtime_window(self, *, start_call: str = "100") -> dict[str, str]:
        return {
            "read_sha256": self.read_sha256,
            "tract_id": "HV2_C",
            "start_distance_after_tract": "1",
            "end_distance_after_tract": "25",
            "start_call_index_0based": start_call,
            "end_call_index_0based": "124",
            "profile_observations": "25",
            "mean_profile_impurity": "0.2",
            "mean_zero_reference_mass": "0.8",
        }

    def runtime_candidate(
        self,
        offset: int,
        *,
        informative: str = "20",
        shifted: str = "0.3",
    ) -> dict[str, str]:
        return {
            "read_sha256": self.read_sha256,
            "tract_id": "HV2_C",
            "start_distance_after_tract": "1",
            "end_distance_after_tract": "25",
            "reference_offset_in_read_order": str(offset),
            "informative_positions": informative,
            "mean_zero_reference_mass": "0.6",
            "mean_shifted_reference_mass": shifted,
            "mean_residual_mass": "0.1",
        }

    @staticmethod
    def write_csv(
        path: Path,
        columns: tuple[str, ...],
        rows: list[dict[str, str]],
    ) -> None:
        with path.open("w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(
                target, fieldnames=list(columns), lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(rows)

    def write_research(self, *, window_size: int = 25) -> None:
        windows = [self.research_window()]
        candidates = [self.research_candidate(offset) for offset in self.offsets()]
        windows_path = self.research / "windows.csv"
        hypotheses_path = self.research / "hypotheses.csv"
        self.write_csv(windows_path, WINDOW_COLUMNS, windows)
        self.write_csv(hypotheses_path, HYPOTHESIS_COLUMNS, candidates)
        index = {
            "schema_version": PHASE_HYPOTHESIS_SCHEMA_VERSION,
            "source_polyc_phase_sha256": "c" * 64,
            "source_corpus_sha256": "d" * 64,
            "signal_version": "0.1.0",
            "manifest_sha256": "e" * 64,
            "reference_sha256": self.reference_sha256,
            "configuration_sha256": self.configuration_sha256,
            "method": {
                "window_size_profile_observations": window_size,
                "window_step_profile_observations": 5,
                "max_reference_offset_in_read_order": 5,
                "candidate_offsets": self.offsets(),
            },
            "windows_file": "windows.csv",
            "windows_sha256": file_sha256(windows_path),
            "windows_rows": len(windows),
            "windows_columns": list(WINDOW_COLUMNS),
            "hypotheses_file": "hypotheses.csv",
            "hypotheses_sha256": file_sha256(hypotheses_path),
            "hypotheses_rows": len(candidates),
            "hypotheses_columns": list(HYPOTHESIS_COLUMNS),
        }
        (self.research / "index.json").write_text(
            json.dumps(index, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def write_runtime(
        self,
        *,
        start_call: str = "100",
        informative: str = "20",
        shifted: str = "0.3",
    ) -> None:
        windows = [self.runtime_window(start_call=start_call)]
        candidates = [
            self.runtime_candidate(
                offset,
                informative=informative,
                shifted=shifted,
            )
            for offset in self.offsets()
        ]
        windows_path = self.runtime / "windows.csv"
        candidates_path = self.runtime / "candidates.csv"
        self.write_csv(windows_path, RUNTIME_WINDOW_COLUMNS, windows)
        self.write_csv(candidates_path, RUNTIME_CANDIDATE_COLUMNS, candidates)
        index = {
            "schema_version": RUNTIME_SCHEMA_VERSION,
            "source_method": RUNTIME_SOURCE_METHOD,
            "signal_version": "0.1.0",
            "sample_id": "case-1",
            "reference_sha256": self.reference_sha256,
            "configuration_sha256": self.configuration_sha256,
            "read_count": 1,
            "window_count": len(windows),
            "candidate_count": len(candidates),
            "files": {
                "windows": {
                    "path": "windows.csv",
                    "sha256": file_sha256(windows_path),
                    "rows": len(windows),
                },
                "candidates": {
                    "path": "candidates.csv",
                    "sha256": file_sha256(candidates_path),
                    "rows": len(candidates),
                },
            },
            "reads": [
                {
                    "read_sha256": self.read_sha256,
                    "applicability": "applicable",
                    "tracts": [],
                }
            ],
        }
        (self.runtime / "index.json").write_text(
            json.dumps(index, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def compare(self, *, tolerance: float = 1e-12):
        return compare_phase_runtime(
            self.research,
            [self.runtime],
            tolerance=tolerance,
        )

    def test_exact_structure_and_numeric_evidence_pass(self) -> None:
        self.write_research()
        self.write_runtime()

        summary = self.compare()

        self.assertTrue(summary.passed)
        self.assertEqual(summary.missing_windows, 0)
        self.assertEqual(summary.extra_windows, 0)
        self.assertEqual(summary.call_index_diffs, 0)
        self.assertEqual(summary.candidate_count_diff, 0)
        self.assertEqual(summary.informative_count_diff, 0)
        self.assertEqual(summary.max_numeric_delta, 0.0)

    def test_call_index_mismatch_is_not_hidden_as_window_identity_mismatch(
        self,
    ) -> None:
        self.write_research()
        self.write_runtime(start_call="101")

        summary = self.compare()

        self.assertFalse(summary.passed)
        self.assertEqual(summary.missing_windows, 0)
        self.assertEqual(summary.extra_windows, 0)
        self.assertEqual(summary.call_index_diffs, 1)

    def test_informative_count_mismatch_fails_exact_parity(self) -> None:
        self.write_research()
        self.write_runtime(informative="19")

        summary = self.compare()

        self.assertFalse(summary.passed)
        self.assertEqual(summary.informative_count_diff, len(self.offsets()))

    def test_numeric_delta_uses_explicit_tolerance(self) -> None:
        self.write_research()
        self.write_runtime(shifted="0.3000000000005")

        within = self.compare(tolerance=1e-12)
        outside = self.compare(tolerance=1e-14)

        self.assertTrue(within.passed)
        self.assertFalse(outside.passed)
        self.assertGreater(within.max_numeric_delta, 0.0)
        self.assertLessEqual(within.max_numeric_delta, 1e-12)

    def test_rejects_research_method_that_differs_from_runtime_v1(self) -> None:
        self.write_research(window_size=15)
        self.write_runtime()

        with self.assertRaisesRegex(ValueError, "does not match"):
            self.compare()


if __name__ == "__main__":
    unittest.main()
