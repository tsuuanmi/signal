"""Tests for exact recurrent-locus post-poly-C phase context."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.validation_corpus.filesystem import file_sha256
from scripts.validation_corpus.model import (
    PHASE_HYPOTHESIS_SCHEMA_VERSION,
    PHASE_RECURRENT_LOCUS_SCHEMA_VERSION,
    POLYC_PHASE_SCHEMA_VERSION,
)
from scripts.validation_corpus.phase_hypotheses import publish_phase_hypotheses
from scripts.validation_corpus.phase_recurrent_loci import (
    CANDIDATE_COLUMNS,
    LOCUS_COLUMNS,
    WINDOW_COLUMNS,
    publish_phase_recurrent_loci,
)
from scripts.validation_corpus.polyc_phase import OBSERVATION_COLUMNS, SUMMARY_COLUMNS

BASES = ("A", "C", "G", "T")


class PhaseRecurrentLocusResearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="signal-phase-recurrent-locus-test-"
        )
        self.root = Path(self.temporary.name)
        self.phase = self.root / "phase"
        self.hypotheses = self.root / "hypotheses"
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
        weights = {base: 0.0 for base in BASES}
        weights[current] = 0.60
        weights[shifted] = 0.30
        remaining = next(base for base in BASES if base not in {current, shifted})
        weights[remaining] = 0.10
        return weights["A"], weights["C"], weights["G"], weights["T"]

    @staticmethod
    def position(distance: int) -> int:
        positions = {
            1: 302,
            2: 301,
            3: 300,
            4: 299,
            5: 298,
            6: 297,
            7: 296,
            8: 295,
            9: 294,
            10: 293,
            11: 253,
            12: 252,
        }
        return positions[distance]

    def source_row(self, distance: int) -> dict[str, str]:
        has_profile = distance != 11
        values = self.profile(distance) if has_profile else None
        row = {column: "" for column in OBSERVATION_COLUMNS}
        row.update(
            {
                "validation_case_id": "case-1",
                "source_group_id": "source-1",
                "specimen_group_id": "specimen-1",
                "read_sha256": self.read_sha256,
                "amplicon_id": "HV3",
                "declared_direction": "reverse",
                "orientation": "reverse",
                "tract_id": "HV2_C",
                "tract_start_1based": "303",
                "tract_end_1based": "315",
                "interrupt_position_1based": "310",
                "position_1based": str(self.position(distance)),
                "path_region": "after",
                "read_order_distance_from_tract": str(distance),
                "call_index_0based": str(100 + distance),
                "call_distance_from_tract": str(distance),
                "reference_base": self.reference_base(distance),
                "state": "reference",
                "aligned_base": self.reference_base(distance),
                "quality": "60",
                "in_noisy_region": "false",
                "interrupt_state": "alternate",
                "interrupt_aligned_base": "C",
                "interrupt_call_index_0based": "100",
                "interrupt_in_noisy_region": "false",
            }
        )
        if values is not None:
            row.update(
                {
                    "profile_a": str(values[0]),
                    "profile_c": str(values[1]),
                    "profile_g": str(values[2]),
                    "profile_t": str(values[3]),
                    "profile_impurity": "0.4",
                    "reference_base_mass": "0.6",
                }
            )
        return row

    def write_phase(self) -> None:
        observations = self.phase / "observations.csv"
        with observations.open("w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(
                target,
                fieldnames=list(OBSERVATION_COLUMNS),
                lineterminator="\n",
            )
            writer.writeheader()
            for distance in range(1, 13):
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
            "observations_rows": 12,
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

    def prepare_sources(self) -> None:
        self.write_phase()
        publish_phase_hypotheses(
            self.phase,
            self.hypotheses,
            window_size=5,
            window_step=5,
            max_offset=1,
        )
        hypothesis_index = json.loads(
            (self.hypotheses / "index.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            hypothesis_index["schema_version"],
            PHASE_HYPOTHESIS_SCHEMA_VERSION,
        )

    def test_publishes_exact_locus_window_and_candidate_context(self) -> None:
        self.prepare_sources()
        output = self.root / "recurrent"
        publish_phase_recurrent_loci(self.phase, self.hypotheses, output)

        index = json.loads((output / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(
            index["schema_version"],
            PHASE_RECURRENT_LOCUS_SCHEMA_VERSION,
        )
        self.assertEqual(index["method"]["recurrent_positions_1based"], [253, 297, 302, 16194, 16197])
        self.assertEqual(index["method"]["candidate_offsets"], [-1, 1])
        self.assertEqual(index["method"]["candidate_selection"], "none; every source offset retained")
        self.assertEqual(index["loci_rows"], 3)
        self.assertEqual(index["windows_rows"], 2)
        self.assertEqual(index["candidates_rows"], 4)

        with (output / "loci.csv").open("r", encoding="utf-8", newline="") as source:
            loci = list(csv.DictReader(source))
        self.assertEqual(tuple(loci[0]), LOCUS_COLUMNS)
        locus_302 = next(row for row in loci if row["position_1based"] == "302")
        locus_297 = next(row for row in loci if row["position_1based"] == "297")
        locus_253 = next(row for row in loci if row["position_1based"] == "253")
        self.assertEqual(locus_302["containing_windows"], "1")
        self.assertEqual(locus_297["containing_windows"], "1")
        self.assertEqual(locus_253["containing_windows"], "0")
        self.assertEqual(locus_253["profile_impurity"], "")
        self.assertEqual(locus_253["reference_base_mass"], "")

        with (output / "windows.csv").open("r", encoding="utf-8", newline="") as source:
            windows = list(csv.DictReader(source))
        self.assertEqual(tuple(windows[0]), WINDOW_COLUMNS)
        window_302 = next(row for row in windows if row["position_1based"] == "302")
        window_297 = next(row for row in windows if row["position_1based"] == "297")
        self.assertEqual(window_302["window_start_distance_after_tract"], "1")
        self.assertEqual(window_302["window_end_distance_after_tract"], "5")
        self.assertEqual(window_297["window_start_distance_after_tract"], "6")
        self.assertEqual(window_297["window_end_distance_after_tract"], "10")

        with (output / "candidates.csv").open(
            "r", encoding="utf-8", newline=""
        ) as source:
            candidates = list(csv.DictReader(source))
        self.assertEqual(tuple(candidates[0]), CANDIDATE_COLUMNS)
        self.assertEqual(
            {
                (
                    row["position_1based"],
                    row["reference_offset_in_read_order"],
                )
                for row in candidates
            },
            {("302", "-1"), ("302", "1"), ("297", "-1"), ("297", "1")},
        )
        plus_one_302 = next(
            row
            for row in candidates
            if row["position_1based"] == "302"
            and row["reference_offset_in_read_order"] == "1"
        )
        minus_one_302 = next(
            row
            for row in candidates
            if row["position_1based"] == "302"
            and row["reference_offset_in_read_order"] == "-1"
        )
        self.assertEqual(plus_one_302["locus_informative_for_candidate"], "true")
        self.assertEqual(plus_one_302["locus_shifted_reference_base"], "C")
        self.assertAlmostEqual(
            float(plus_one_302["locus_shifted_reference_mass"]),
            0.30,
        )
        self.assertAlmostEqual(float(plus_one_302["locus_residual_mass"]), 0.10)
        self.assertEqual(minus_one_302["locus_informative_for_candidate"], "false")
        self.assertEqual(minus_one_302["locus_shifted_reference_mass"], "")

    def test_rejects_phase_hypothesis_source_mismatch_and_no_overwrite(self) -> None:
        self.prepare_sources()
        output = self.root / "recurrent"
        publish_phase_recurrent_loci(self.phase, self.hypotheses, output)
        with self.assertRaisesRegex(ValueError, "already exists"):
            publish_phase_recurrent_loci(self.phase, self.hypotheses, output)

        phase_index_path = self.phase / "index.json"
        phase_index = json.loads(phase_index_path.read_text(encoding="utf-8"))
        phase_index["crossing_reads"] = 2
        phase_index_path.write_text(
            json.dumps(phase_index, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "source poly-C phase SHA-256 mismatch"):
            publish_phase_recurrent_loci(
                self.phase,
                self.hypotheses,
                self.root / "mismatch",
            )


if __name__ == "__main__":
    unittest.main()
