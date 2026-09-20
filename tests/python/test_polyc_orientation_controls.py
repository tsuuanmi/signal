"""Tests for matched opposite-orientation poly-C controls."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.validation_corpus.filesystem import file_sha256
from scripts.validation_corpus.model import (
    CORPUS_SCHEMA_VERSION,
    MANIFEST_SCHEMA_VERSION,
    MEASUREMENT_SCHEMA_VERSION,
    POLYC_ORIENTATION_CONTROL_SCHEMA_VERSION,
)
from scripts.validation_corpus.polyc_orientation_controls import (
    LOCUS_COLUMNS,
    OBSERVATION_COLUMNS,
    publish_polyc_orientation_controls,
)

HV2_REFERENCE = "ACCCCCCCTCCCCCG"
HV2_POSITIONS = tuple(range(302, 317))


class PolyCOrientationControlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="signal-polyc-orientation-control-test-"
        )
        self.root = Path(self.temporary.name)
        self.corpus = self.root / "corpus"
        (self.corpus / "cases").mkdir(parents=True)
        self.reference_sha256 = "a" * 64
        self.configuration_sha256 = "b" * 64
        self.manifest_sha256 = "c" * 64
        self.reads = (
            ("1" * 64, "forward", "forward", "PCR-1", "HV2-F"),
            ("2" * 64, "forward", "reverse", "PCR-2", "HV2-F2"),
            ("3" * 64, "reverse", "reverse", "PCR-1", "HV2-R"),
            ("4" * 64, "reverse", "reverse", "PCR-2", "HV2-R2"),
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def reference_base(position: int) -> str:
        return HV2_REFERENCE[position - HV2_POSITIONS[0]]

    @staticmethod
    def profile_for(
        base: str,
        orientation: str,
        position: int,
    ) -> list[float]:
        weights = {"A": 0.02, "C": 0.02, "G": 0.02, "T": 0.02}
        post_tract = (orientation == "forward" and position == 316) or (
            orientation == "reverse" and position == 302
        )
        if post_tract:
            shadow = "C" if base != "C" else "T"
            weights[base] = 0.58
            weights[shadow] = 0.36
        else:
            weights[base] = 0.94
        total = sum(weights.values())
        return [weights[channel] / total for channel in ("A", "C", "G", "T")]

    def observation(
        self,
        position: int,
        read_sha256: str,
        selected_orientation: str,
    ) -> dict[str, object]:
        base = self.reference_base(position)
        call_index = (
            position - HV2_POSITIONS[0]
            if selected_orientation == "forward"
            else HV2_POSITIONS[-1] - position
        )
        values = self.profile_for(base, selected_orientation, position)
        interrupt_aligned_base = (
            "C" if position == 310 and read_sha256 == "2" * 64 else base
        )
        post_tract = (selected_orientation == "forward" and position == 316) or (
            selected_orientation == "reverse" and position == 302
        )
        return {
            "read_sha256": read_sha256,
            "orientation": selected_orientation,
            "state": "alternate" if interrupt_aligned_base != base else "reference",
            "aligned_base": interrupt_aligned_base,
            "quality": 60,
            "call_index_0based": call_index,
            "source_primary": base,
            "source_ambiguity": base,
            "ploc_0based": 100 + call_index,
            "window_start_0based": 99 + call_index,
            "window_end_0based_exclusive": 102 + call_index,
            "primary_peak_position_0based": 100 + call_index,
            "primary_peak_offset_from_ploc": 0,
            "event_position_0based": 100 + call_index,
            "event_offset_from_ploc": 0,
            "event_offset_from_primary_peak": 0,
            "channel_peak_positions_acgt_reference": [100, 100, 100, 100],
            "channel_peak_heights_acgt_reference": [100, 100, 100, 100],
            "channel_peak_sources_acgt_reference": [
                "local_maximum",
                "local_maximum",
                "local_maximum",
                "local_maximum",
            ],
            "primary_peak_heights_acgt_reference": [100, 100, 100, 100],
            "corrected_amplitudes_acgt_reference": [value * 100.0 for value in values],
            "snrs_acgt_reference": [10.0, 10.0, 10.0, 10.0],
            "profile_acgt_reference": values,
            "in_noisy_region": post_tract,
        }

    def locus(
        self,
        position: int,
        selected_orientations: dict[str, str],
    ) -> dict[str, object]:
        observations = [
            self.observation(position, read_sha256, selected_orientations[read_sha256])
            for read_sha256, _, _, _, _ in self.reads
        ]
        forward_reads = sum(row["orientation"] == "forward" for row in observations)
        reverse_reads = len(observations) - forward_reads
        return {
            "schema_version": MEASUREMENT_SCHEMA_VERSION,
            "signal_version": "0.1.0",
            "sample_id": "case-1",
            "reference_sha256": self.reference_sha256,
            "configuration_sha256": self.configuration_sha256,
            "position_1based": position,
            "reference_base": self.reference_base(position),
            "reads": len(observations),
            "forward_reads": forward_reads,
            "reverse_reads": reverse_reads,
            "reference_reads": len(observations),
            "alternate_reads": 0,
            "unresolved_reads": 0,
            "deletion_reads": 0,
            "profile_reads": len(observations),
            "profile_forward_reads": forward_reads,
            "profile_reverse_reads": reverse_reads,
            "contributors": len(observations),
            "forward_contributors": forward_reads,
            "reverse_contributors": reverse_reads,
            "mean_a": 0.25,
            "mean_c": 0.25,
            "mean_g": 0.25,
            "mean_t": 0.25,
            "within_profile_impurity": 0.1,
            "between_profile_dispersion": 0.1,
            "total_profile_heterogeneity": 0.2,
            "forward_within_profile_impurity": 0.1,
            "forward_between_profile_dispersion": 0.1,
            "forward_total_profile_heterogeneity": 0.2,
            "reverse_within_profile_impurity": 0.1,
            "reverse_between_profile_dispersion": 0.1,
            "reverse_total_profile_heterogeneity": 0.2,
            "directional_profile_distance": 0.1,
            "noisy_observations": sum(
                row["in_noisy_region"] is True for row in observations
            ),
            "missing_profile_observations": 0,
            "deletion_observations": 0,
            "observations": observations,
        }

    def write_corpus(self, *, all_forward: bool = False) -> None:
        selected_orientations = {
            read_sha256: ("forward" if all_forward else selected_orientation)
            for read_sha256, selected_orientation, _, _, _ in self.reads
        }
        rows = [
            self.locus(position, selected_orientations) for position in HV2_POSITIONS
        ]
        measurement = self.corpus / "cases" / "case-1.jsonl"
        measurement.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8",
        )

        read_records = []
        for (
            read_sha256,
            _,
            declared_direction,
            pcr_replicate_id,
            amplicon_id,
        ) in self.reads:
            read_records.append(
                {
                    "trace_sha256": read_sha256,
                    "pcr_replicate_id": pcr_replicate_id,
                    "sequencing_run_id": "run-1",
                    "instrument_id": "instrument-1",
                    "amplicon_id": amplicon_id,
                    "declared_direction": declared_direction,
                    "artifact_tags": ["synthetic"],
                }
            )

        case = {
            "validation_case_id": "case-1",
            "source_group_id": "source-1",
            "specimen_group_id": "specimen-1",
            "truth_class": "unknown",
            "truth_method": "unreviewed",
            "truth_locus": None,
            "truth_reference": None,
            "truth_alternate": None,
            "known_mixture_fraction": None,
            "include_in_threshold_fit": False,
            "holdout_group": "unassigned",
            "approval_record": "synthetic-test",
            "redistribution_status": "synthetic",
            "notes": None,
            "measurement_file": "cases/case-1.jsonl",
            "loci": len(rows),
            "reads": read_records,
        }
        index = {
            "schema_version": CORPUS_SCHEMA_VERSION,
            "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
            "measurement_schema_version": MEASUREMENT_SCHEMA_VERSION,
            "signal_version": "0.1.0",
            "manifest_sha256": self.manifest_sha256,
            "reference_sha256": self.reference_sha256,
            "configuration_sha256": self.configuration_sha256,
            "case_count": 1,
            "trace_count": len(read_records),
            "cases": [case],
        }
        (self.corpus / "index.json").write_text(
            json.dumps(index, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def test_publishes_n_read_controls_without_cartesian_pairs(self) -> None:
        self.write_corpus()
        output = self.root / "controls"
        publish_polyc_orientation_controls(self.corpus, output)

        index = json.loads((output / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(
            index["schema_version"],
            POLYC_ORIENTATION_CONTROL_SCHEMA_VERSION,
        )
        self.assertEqual(index["matched_loci"], 2)
        self.assertEqual(index["observations_rows"], 8)
        self.assertEqual(
            index["source_corpus_sha256"],
            file_sha256(self.corpus / "index.json"),
        )
        self.assertEqual(index["method"]["thresholds"], "none")
        self.assertIn("retain every eligible read", index["method"]["read_selection"])

        with (output / "observations.csv").open(
            "r", encoding="utf-8", newline=""
        ) as source:
            observations = list(csv.DictReader(source))
        self.assertEqual(tuple(observations[0]), OBSERVATION_COLUMNS)

        forward_group = [
            row
            for row in observations
            if row["position_1based"] == "316" and row["post_orientation"] == "forward"
        ]
        self.assertEqual(len(forward_group), 4)
        self.assertEqual(
            sum(row["role"] == "post_tract" for row in forward_group),
            2,
        )
        self.assertEqual(
            sum(row["role"] == "pre_tract_opposite_control" for row in forward_group),
            2,
        )
        mismatched_declared = next(
            row for row in forward_group if row["read_sha256"] == "2" * 64
        )
        self.assertEqual(mismatched_declared["orientation"], "forward")
        self.assertEqual(mismatched_declared["declared_direction"], "reverse")
        self.assertEqual(mismatched_declared["role"], "post_tract")
        self.assertEqual(mismatched_declared["interrupt_aligned_base"], "C")
        self.assertEqual(mismatched_declared["pcr_replicate_id"], "PCR-2")
        self.assertEqual(mismatched_declared["amplicon_id"], "HV2-F2")

        with (output / "loci.csv").open("r", encoding="utf-8", newline="") as source:
            loci = list(csv.DictReader(source))
        self.assertEqual(tuple(loci[0]), LOCUS_COLUMNS)
        forward_locus = next(
            row
            for row in loci
            if row["position_1based"] == "316" and row["post_orientation"] == "forward"
        )
        self.assertEqual(forward_locus["post_interrupt_bases"], "C,T")
        self.assertEqual(forward_locus["control_interrupt_bases"], "T")
        self.assertEqual(forward_locus["post_reads"], "2")
        self.assertEqual(forward_locus["control_reads"], "2")
        self.assertEqual(forward_locus["post_profile_reads"], "2")
        self.assertEqual(forward_locus["control_profile_reads"], "2")
        self.assertEqual(forward_locus["post_noisy_observations"], "2")
        self.assertEqual(forward_locus["control_noisy_observations"], "0")
        self.assertGreater(float(forward_locus["mean_profile_total_variation"]), 0.0)

    def test_requires_opposite_selected_orientation(self) -> None:
        self.write_corpus(all_forward=True)
        with self.assertRaisesRegex(
            ValueError,
            "no matched opposite-orientation",
        ):
            publish_polyc_orientation_controls(
                self.corpus,
                self.root / "controls",
            )

    def test_no_overwrite_and_publication_failure_rollback(self) -> None:
        self.write_corpus()
        output = self.root / "controls"
        publish_polyc_orientation_controls(self.corpus, output)

        with self.assertRaisesRegex(ValueError, "already exists"):
            publish_polyc_orientation_controls(self.corpus, output)

        rollback = self.root / "rollback"
        from scripts.validation_corpus import polyc_orientation_controls

        real_rename = polyc_orientation_controls.os.rename

        def rename(source: Path, destination: Path) -> None:
            if source.name == "index.json":
                raise OSError("publication failed")
            real_rename(source, destination)

        with (
            patch(
                "scripts.validation_corpus.polyc_orientation_controls.os.rename",
                side_effect=rename,
            ),
            self.assertRaisesRegex(OSError, "publication failed"),
        ):
            publish_polyc_orientation_controls(self.corpus, rollback)

        self.assertFalse(rollback.exists())


if __name__ == "__main__":
    unittest.main()
