"""Tests for development-only phase interpretation dataset preparation."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from scripts.validation_corpus.filesystem import file_sha256
from scripts.validation_corpus.model import (
    CORPUS_SCHEMA_VERSION,
    MANIFEST_SCHEMA_VERSION,
    MEASUREMENT_SCHEMA_VERSION,
    PHASE_HYPOTHESIS_SCHEMA_VERSION,
    PHASE_INTERPRETATION_DATASET_SCHEMA_VERSION,
)
from scripts.validation_corpus.phase_hypotheses import (
    HYPOTHESIS_COLUMNS,
    WINDOW_COLUMNS,
)
from scripts.validation_corpus.phase_interpretation_dataset import (
    DEVELOPMENT_WINDOW_COLUMNS,
    READINESS_COLUMNS,
    PartitionPlan,
    publish_phase_interpretation_dataset,
)


class PhaseInterpretationDatasetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="signal-phase-interpretation-dataset-test-"
        )
        self.root = Path(self.temporary.name)
        self.corpus = self.root / "corpus"
        self.hypotheses = self.root / "hypotheses"
        (self.corpus / "cases").mkdir(parents=True)
        self.hypotheses.mkdir()
        self.reference_sha256 = "a" * 64
        self.configuration_sha256 = "b" * 64
        self.manifest_sha256 = "c" * 64

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def offsets() -> list[int]:
        return [*range(-5, 0), *range(1, 6)]

    def observation(
        self,
        read_sha256: str,
        orientation: str,
    ) -> dict[str, Any]:
        return {
            "read_sha256": read_sha256,
            "orientation": orientation,
            "state": "reference",
            "aligned_base": "A",
            "quality": 60,
            "call_index_0based": 0,
            "source_primary": "A",
            "source_ambiguity": "A",
            "ploc_0based": 10,
            "window_start_0based": 9,
            "window_end_0based_exclusive": 12,
            "primary_peak_position_0based": 10,
            "primary_peak_offset_from_ploc": 0,
            "event_position_0based": 10,
            "event_offset_from_ploc": 0,
            "event_offset_from_primary_peak": 0,
            "channel_peak_positions_acgt_reference": [10, 10, 10, 10],
            "channel_peak_heights_acgt_reference": [100, 5, 3, 2],
            "channel_peak_sources_acgt_reference": [
                "local_maximum",
                "local_maximum",
                "local_maximum",
                "local_maximum",
            ],
            "primary_peak_heights_acgt_reference": [100, 5, 3, 2],
            "corrected_amplitudes_acgt_reference": [90.0, 4.0, 3.0, 1.0],
            "snrs_acgt_reference": [20.0, 1.0, 0.8, 0.4],
            "profile_acgt_reference": [0.92, 0.04, 0.03, 0.01],
            "in_noisy_region": False,
        }

    def locus(
        self,
        case_id: str,
        read_sha256: str,
        orientation: str,
    ) -> dict[str, Any]:
        return {
            "schema_version": MEASUREMENT_SCHEMA_VERSION,
            "signal_version": "0.1.0",
            "sample_id": case_id,
            "reference_sha256": self.reference_sha256,
            "configuration_sha256": self.configuration_sha256,
            "position_1based": 100,
            "reference_base": "A",
            "reads": 1,
            "forward_reads": int(orientation == "forward"),
            "reverse_reads": int(orientation == "reverse"),
            "reference_reads": 1,
            "alternate_reads": 0,
            "unresolved_reads": 0,
            "deletion_reads": 0,
            "profile_reads": 1,
            "profile_forward_reads": int(orientation == "forward"),
            "profile_reverse_reads": int(orientation == "reverse"),
            "contributors": 1,
            "forward_contributors": int(orientation == "forward"),
            "reverse_contributors": int(orientation == "reverse"),
            "mean_a": 0.92,
            "mean_c": 0.04,
            "mean_g": 0.03,
            "mean_t": 0.01,
            "within_profile_impurity": 0.1,
            "between_profile_dispersion": 0.0,
            "total_profile_heterogeneity": 0.1,
            "forward_within_profile_impurity": (
                0.1 if orientation == "forward" else None
            ),
            "forward_between_profile_dispersion": (
                0.0 if orientation == "forward" else None
            ),
            "forward_total_profile_heterogeneity": (
                0.1 if orientation == "forward" else None
            ),
            "reverse_within_profile_impurity": (
                0.1 if orientation == "reverse" else None
            ),
            "reverse_between_profile_dispersion": (
                0.0 if orientation == "reverse" else None
            ),
            "reverse_total_profile_heterogeneity": (
                0.1 if orientation == "reverse" else None
            ),
            "directional_profile_distance": None,
            "noisy_observations": 0,
            "missing_profile_observations": 0,
            "deletion_observations": 0,
            "observations": [self.observation(read_sha256, orientation)],
        }

    def case_record(
        self,
        case_id: str,
        read_sha256: str,
        *,
        source_group: str,
        holdout_group: str,
        fit: bool,
        orientation: str = "forward",
        amplicon: str = "HV2",
    ) -> dict[str, Any]:
        measurement = self.corpus / "cases" / f"{case_id}.jsonl"
        measurement.write_text(
            json.dumps(
                self.locus(case_id, read_sha256, orientation),
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return {
            "validation_case_id": case_id,
            "source_group_id": source_group,
            "specimen_group_id": f"specimen-{source_group}",
            "truth_class": "clean_reference",
            "truth_method": "synthetic",
            "truth_locus": None,
            "truth_reference": None,
            "truth_alternate": None,
            "known_mixture_fraction": None,
            "include_in_threshold_fit": fit,
            "holdout_group": holdout_group,
            "approval_record": "synthetic-test",
            "redistribution_status": "synthetic",
            "notes": None,
            "measurement_file": f"cases/{case_id}.jsonl",
            "loci": 1,
            "reads": [
                {
                    "trace_sha256": read_sha256,
                    "pcr_replicate_id": f"pcr-{source_group}",
                    "sequencing_run_id": f"run-{source_group}",
                    "instrument_id": "instrument-1",
                    "amplicon_id": amplicon,
                    "declared_direction": orientation,
                    "artifact_tags": ["clean"],
                }
            ],
        }

    def write_corpus(
        self,
        *,
        include_nonfit_development: bool = False,
        holdout_group: str = "holdout",
    ) -> list[dict[str, Any]]:
        cases = [
            self.case_record(
                "dev-fit",
                "1" * 64,
                source_group="dev-1",
                holdout_group="development",
                fit=True,
            ),
            self.case_record(
                "holdout",
                "2" * 64,
                source_group="holdout-1",
                holdout_group=holdout_group,
                fit=True,
            ),
        ]
        if include_nonfit_development:
            cases.append(
                self.case_record(
                    "dev-review",
                    "3" * 64,
                    source_group="dev-2",
                    holdout_group="development",
                    fit=False,
                )
            )

        index = {
            "schema_version": CORPUS_SCHEMA_VERSION,
            "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
            "measurement_schema_version": MEASUREMENT_SCHEMA_VERSION,
            "signal_version": "0.1.0",
            "manifest_sha256": self.manifest_sha256,
            "reference_sha256": self.reference_sha256,
            "configuration_sha256": self.configuration_sha256,
            "case_count": len(cases),
            "trace_count": len(cases),
            "cases": cases,
        }
        (self.corpus / "index.json").write_text(
            json.dumps(index, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return cases

    def window_row(
        self,
        case_id: str,
        read_sha256: str,
        *,
        orientation: str = "forward",
        amplicon: str = "HV2",
    ) -> dict[str, str]:
        window_id = f"HV2_C:{read_sha256}:1-25"
        row = {column: "" for column in WINDOW_COLUMNS}
        row.update(
            {
                "window_id": window_id,
                "validation_case_id": case_id,
                "read_sha256": read_sha256,
                "tract_id": "HV2_C",
                "amplicon_id": amplicon,
                "orientation": orientation,
                "interrupt_aligned_base": "T",
                "start_distance_after_tract": "1",
                "end_distance_after_tract": "25",
                "start_call_index_0based": "100",
                "end_call_index_0based": "124",
                "profile_observations": "25",
                "noisy_observations": "0",
                "mean_profile_impurity": "0.1",
                "mean_zero_reference_mass": "0.9",
            }
        )
        return row

    @staticmethod
    def candidate_row(window_id: str, offset: int) -> dict[str, str]:
        return {
            "window_id": window_id,
            "reference_offset_in_read_order": str(offset),
            "informative_positions": "20",
            "mean_zero_reference_mass": "0.6",
            "mean_shifted_reference_mass": "0.3",
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
                target,
                fieldnames=list(columns),
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(rows)

    def write_hypotheses(
        self,
        cases: list[dict[str, Any]],
        *,
        orientation_overrides: dict[str, str] | None = None,
        source_corpus_sha256: str | None = None,
        window_size: int = 25,
    ) -> None:
        orientation_overrides = orientation_overrides or {}
        windows: list[dict[str, str]] = []
        candidates: list[dict[str, str]] = []
        for case in cases:
            case_id = str(case["validation_case_id"])
            read = case["reads"][0]
            if not isinstance(read, dict):
                raise TypeError("synthetic read must be an object")
            read_sha256 = str(read["trace_sha256"])
            orientation = orientation_overrides.get(
                case_id,
                str(read["declared_direction"]),
            )
            amplicon = str(read["amplicon_id"])
            window = self.window_row(
                case_id,
                read_sha256,
                orientation=orientation,
                amplicon=amplicon,
            )
            windows.append(window)
            candidates.extend(
                self.candidate_row(window["window_id"], offset)
                for offset in self.offsets()
            )

        windows_path = self.hypotheses / "windows.csv"
        hypotheses_path = self.hypotheses / "hypotheses.csv"
        self.write_csv(windows_path, WINDOW_COLUMNS, windows)
        self.write_csv(hypotheses_path, HYPOTHESIS_COLUMNS, candidates)

        index = {
            "schema_version": PHASE_HYPOTHESIS_SCHEMA_VERSION,
            "source_polyc_phase_sha256": "d" * 64,
            "source_corpus_sha256": (
                source_corpus_sha256
                if source_corpus_sha256 is not None
                else file_sha256(self.corpus / "index.json")
            ),
            "signal_version": "0.1.0",
            "manifest_sha256": self.manifest_sha256,
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
        (self.hypotheses / "index.json").write_text(
            json.dumps(index, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def plan() -> PartitionPlan:
        return PartitionPlan(
            development=("development",),
            holdout=("holdout",),
        )

    def test_exports_only_fit_development_measurements_and_holdout_counts(self) -> None:
        cases = self.write_corpus(include_nonfit_development=True)
        self.write_hypotheses(cases)
        output = self.root / "dataset"

        publish_phase_interpretation_dataset(
            self.corpus,
            self.hypotheses,
            output,
            self.plan(),
        )

        index = json.loads((output / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(
            index["schema_version"],
            PHASE_INTERPRETATION_DATASET_SCHEMA_VERSION,
        )
        self.assertEqual(
            index["source_corpus_sha256"],
            file_sha256(self.corpus / "index.json"),
        )
        self.assertEqual(
            index["source_phase_hypotheses_sha256"],
            file_sha256(self.hypotheses / "index.json"),
        )
        self.assertFalse(index["method"]["holdout_phase_measurements_exported"])
        self.assertEqual(index["development_windows_rows"], 1)
        self.assertEqual(index["development_candidates_rows"], 10)
        self.assertEqual(index["partition_summary"]["development"]["cases"], 2)
        self.assertEqual(index["partition_summary"]["development"]["fit_cases"], 1)
        self.assertEqual(index["partition_summary"]["holdout"]["cases"], 1)
        self.assertEqual(index["partition_summary"]["holdout"]["windows"], 1)

        with (output / "development-windows.csv").open(
            "r", encoding="utf-8", newline=""
        ) as source:
            windows = list(csv.DictReader(source))
        self.assertEqual(tuple(windows[0]), DEVELOPMENT_WINDOW_COLUMNS)
        self.assertEqual([row["validation_case_id"] for row in windows], ["dev-fit"])
        self.assertEqual(windows[0]["source_group_id"], "dev-1")
        self.assertEqual(windows[0]["artifact_tags"], "clean")
        self.assertEqual(windows[0]["orientation"], "forward")

        with (output / "development-candidates.csv").open(
            "r", encoding="utf-8", newline=""
        ) as source:
            candidates = list(csv.DictReader(source))
        self.assertEqual(tuple(candidates[0]), HYPOTHESIS_COLUMNS)
        self.assertEqual(len(candidates), 10)
        self.assertTrue(
            all(candidate["window_id"] == windows[0]["window_id"] for candidate in candidates)
        )

        with (output / "readiness.csv").open(
            "r", encoding="utf-8", newline=""
        ) as source:
            readiness = list(csv.DictReader(source))
        self.assertEqual(tuple(readiness[0]), READINESS_COLUMNS)
        self.assertEqual(
            {row["partition"] for row in readiness},
            {"development", "holdout"},
        )
        self.assertNotIn("mean_profile_impurity", readiness[0])
        self.assertNotIn("mean_shifted_reference_mass", readiness[0])

        development_text = (output / "development-windows.csv").read_text()
        development_text += (output / "development-candidates.csv").read_text()
        self.assertNotIn("holdout", development_text)
        self.assertNotIn("dev-review", development_text)

    def test_rejects_unknown_partition_and_provenance_drift(self) -> None:
        cases = self.write_corpus(holdout_group="locked")
        self.write_hypotheses(cases)

        with self.assertRaisesRegex(ValueError, "no declared study partition"):
            publish_phase_interpretation_dataset(
                self.corpus,
                self.hypotheses,
                self.root / "unknown-group",
                self.plan(),
            )

    def test_rejects_source_corpus_and_orientation_mismatch(self) -> None:
        cases = self.write_corpus()
        self.write_hypotheses(cases, source_corpus_sha256="e" * 64)

        with self.assertRaisesRegex(ValueError, "source corpus SHA-256 differs"):
            publish_phase_interpretation_dataset(
                self.corpus,
                self.hypotheses,
                self.root / "corpus-mismatch",
                self.plan(),
            )

        for path in self.hypotheses.iterdir():
            path.unlink()
        self.write_hypotheses(cases, orientation_overrides={"dev-fit": "reverse"})
        with self.assertRaisesRegex(ValueError, "selected orientation differs"):
            publish_phase_interpretation_dataset(
                self.corpus,
                self.hypotheses,
                self.root / "orientation-mismatch",
                self.plan(),
            )

    def test_rejects_nonproduction_phase_method(self) -> None:
        cases = self.write_corpus()
        self.write_hypotheses(cases, window_size=15)

        with self.assertRaisesRegex(ValueError, "does not match"):
            publish_phase_interpretation_dataset(
                self.corpus,
                self.hypotheses,
                self.root / "method-mismatch",
                self.plan(),
            )

    def test_no_overwrite_and_publication_failure_rolls_back(self) -> None:
        cases = self.write_corpus()
        self.write_hypotheses(cases)
        output = self.root / "dataset"

        publish_phase_interpretation_dataset(
            self.corpus,
            self.hypotheses,
            output,
            self.plan(),
        )
        with self.assertRaisesRegex(ValueError, "already exists"):
            publish_phase_interpretation_dataset(
                self.corpus,
                self.hypotheses,
                output,
                self.plan(),
            )

        rollback = self.root / "rollback"
        from scripts.validation_corpus import phase_interpretation_dataset

        real_rename = phase_interpretation_dataset.os.rename
        calls = 0

        def fail_second_rename(source: Path, target: Path) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("synthetic publication failure")
            real_rename(source, target)

        with (
            patch(
                "scripts.validation_corpus.phase_interpretation_dataset.os.rename",
                side_effect=fail_second_rename,
            ),
            self.assertRaisesRegex(OSError, "synthetic publication failure"),
        ):
            publish_phase_interpretation_dataset(
                self.corpus,
                self.hypotheses,
                rollback,
                self.plan(),
            )
        self.assertFalse(rollback.exists())


if __name__ == "__main__":
    unittest.main()
