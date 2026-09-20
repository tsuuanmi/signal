"""Tests for descriptive post-poly-C validation research."""

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
    POLYC_PHASE_SCHEMA_VERSION,
)
from scripts.validation_corpus.polyc_geometry import (
    TRACTS,
    TractCallSpan,
    covers_complete_tract,
)
from scripts.validation_corpus.polyc_phase import (
    ReadContext,
    observation_record,
    publish_polyc_phase,
)

HV2_REFERENCE = "ACCCCCCCTCCCCCG"
HV2_POSITIONS = tuple(range(302, 317))


class PolyCPhaseResearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="signal-polyc-test-")
        self.root = Path(self.temporary.name)
        self.corpus = self.root / "corpus"
        (self.corpus / "cases").mkdir(parents=True)
        self.forward_sha = "1" * 64
        self.reverse_sha = "2" * 64
        self.reference_sha256 = "a" * 64
        self.configuration_sha256 = "b" * 64
        self.manifest_sha256 = "c" * 64

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def reference_base(position: int) -> str:
        return HV2_REFERENCE[position - HV2_POSITIONS[0]]

    @staticmethod
    def reference_profile(base: str, previous: str | None = None) -> list[float]:
        weights = {"A": 0.02, "C": 0.02, "G": 0.02, "T": 0.02}
        weights[base] = 0.92
        if previous is not None and previous != base:
            weights[base] = 0.70
            weights[previous] = 0.24
        total = sum(weights.values())
        return [weights[base_name] / total for base_name in ("A", "C", "G", "T")]

    def observation(
        self,
        position: int,
        orientation: str,
        read_sha256: str,
    ) -> dict[str, object]:
        base = self.reference_base(position)
        call_index = (
            position - HV2_POSITIONS[0]
            if orientation == "forward"
            else HV2_POSITIONS[-1] - position
        )
        previous_position = position - 1 if orientation == "forward" else position + 1
        previous = (
            self.reference_base(previous_position)
            if previous_position in HV2_POSITIONS
            else None
        )
        profile = self.reference_profile(
            base, previous if position in {302, 316} else None
        )
        return {
            "read_sha256": read_sha256,
            "orientation": orientation,
            "state": "reference",
            "aligned_base": base,
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
            "corrected_amplitudes_acgt_reference": [value * 100.0 for value in profile],
            "snrs_acgt_reference": [10.0, 10.0, 10.0, 10.0],
            "profile_acgt_reference": profile,
            "in_noisy_region": position == 302 and orientation == "reverse",
        }

    def locus(self, position: int) -> dict[str, object]:
        base = self.reference_base(position)
        forward = self.observation(position, "forward", self.forward_sha)
        reverse = self.observation(position, "reverse", self.reverse_sha)
        return {
            "schema_version": MEASUREMENT_SCHEMA_VERSION,
            "signal_version": "0.1.0",
            "sample_id": "case-1",
            "reference_sha256": self.reference_sha256,
            "configuration_sha256": self.configuration_sha256,
            "position_1based": position,
            "reference_base": base,
            "reads": 2,
            "forward_reads": 1,
            "reverse_reads": 1,
            "reference_reads": 2,
            "alternate_reads": 0,
            "unresolved_reads": 0,
            "deletion_reads": 0,
            "profile_reads": 2,
            "profile_forward_reads": 1,
            "profile_reverse_reads": 1,
            "contributors": 2,
            "forward_contributors": 1,
            "reverse_contributors": 1,
            "mean_a": 0.25,
            "mean_c": 0.25,
            "mean_g": 0.25,
            "mean_t": 0.25,
            "within_profile_impurity": 0.08,
            "between_profile_dispersion": 0.0,
            "total_profile_heterogeneity": 0.08,
            "forward_within_profile_impurity": 0.08,
            "forward_between_profile_dispersion": 0.0,
            "forward_total_profile_heterogeneity": 0.08,
            "reverse_within_profile_impurity": 0.08,
            "reverse_between_profile_dispersion": 0.0,
            "reverse_total_profile_heterogeneity": 0.08,
            "directional_profile_distance": 0.0,
            "noisy_observations": int(
                bool(reverse["in_noisy_region"]) or bool(forward["in_noisy_region"])
            ),
            "missing_profile_observations": 0,
            "deletion_observations": 0,
            "observations": [forward, reverse],
        }

    def write_corpus(self) -> None:
        rows = [self.locus(position) for position in HV2_POSITIONS]
        measurement = self.corpus / "cases" / "case-1.jsonl"
        measurement.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8",
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
            "reads": [
                {
                    "trace_sha256": self.forward_sha,
                    "pcr_replicate_id": None,
                    "sequencing_run_id": "run-1",
                    "instrument_id": None,
                    "amplicon_id": "HV2",
                    "declared_direction": "forward",
                    "artifact_tags": [],
                },
                {
                    "trace_sha256": self.reverse_sha,
                    "pcr_replicate_id": None,
                    "sequencing_run_id": "run-1",
                    "instrument_id": None,
                    "amplicon_id": "HV3",
                    "declared_direction": "reverse",
                    "artifact_tags": [],
                },
            ],
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
            "trace_count": 2,
            "cases": [case],
        }
        (self.corpus / "index.json").write_text(
            json.dumps(index, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def test_crossing_requires_actual_tract_positions(self) -> None:
        hv2 = TRACTS[0]
        context = ReadContext(
            validation_case_id="case-1",
            source_group_id="source-1",
            specimen_group_id="specimen-1",
            read_sha256=self.forward_sha,
            amplicon_id="HV2",
            declared_direction="forward",
            orientation="forward",
        )
        context.tract_positions.update(range(hv2.start_1based, hv2.end_1based + 1))
        self.assertTrue(covers_complete_tract(context.tract_positions, hv2))

        context.tract_positions.remove(310)
        context.tract_positions.update({1, 16569})
        self.assertFalse(covers_complete_tract(context.tract_positions, hv2))

    def test_observation_record_preserves_post_hv1_path_across_origin(self) -> None:
        hv1 = TRACTS[1]
        context = ReadContext(
            validation_case_id="case-1",
            source_group_id="source-1",
            specimen_group_id="specimen-1",
            read_sha256=self.forward_sha,
            amplicon_id="HV1",
            declared_direction="forward",
            orientation="forward",
        )
        row = {
            "position_1based": 253,
            "call_index_0based": 738,
            "reference_base": "A",
            "state": "reference",
            "aligned_base": "A",
            "quality": 60,
            "in_noisy_region": False,
            "profile_a": 0.90,
            "profile_c": 0.05,
            "profile_g": 0.03,
            "profile_t": 0.02,
        }
        record = observation_record(
            row,
            context,
            hv1,
            TractCallSpan(100, 109),
            {252: "C", 253: "A", 254: "G"},
        )
        self.assertEqual(record["path_region"], "after")
        self.assertEqual(record["read_order_distance_from_tract"], 629)
        self.assertEqual(record["call_distance_from_tract"], 629)
        self.assertEqual(record["read_order_previous_reference_base"], "C")
        self.assertEqual(record["read_order_next_reference_base"], "G")

    def test_publishes_directional_raw_features_without_phase_score(self) -> None:
        self.write_corpus()
        output = self.root / "research" / "polyc"

        publish_polyc_phase(self.corpus, output)

        index = json.loads((output / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(index["schema_version"], POLYC_PHASE_SCHEMA_VERSION)
        self.assertEqual(index["observations_rows"], 30)
        self.assertEqual(index["crossing_reads"], 2)
        self.assertEqual(len(index["method"]["tracts"]), 1)
        self.assertEqual(index["method"]["tracts"][0]["tract_id"], "HV2_C")
        self.assertEqual(
            index["method"]["read_crossing_rule"],
            "the read has a validation observation at every reference position "
            "from tract start through tract end",
        )
        self.assertIn("circular rCRS", index["method"]["distance_rule"])
        self.assertEqual(
            index["source_corpus_sha256"],
            file_sha256(self.corpus / "index.json"),
        )

        with (output / "observations.csv").open(
            "r", encoding="utf-8", newline=""
        ) as source:
            rows = list(csv.DictReader(source))
        forward_after = next(
            row
            for row in rows
            if row["read_sha256"] == self.forward_sha
            and row["position_1based"] == "316"
        )
        reverse_after = next(
            row
            for row in rows
            if row["read_sha256"] == self.reverse_sha
            and row["position_1based"] == "302"
        )

        self.assertEqual(forward_after["path_region"], "after")
        self.assertEqual(forward_after["read_order_distance_from_tract"], "1")
        self.assertEqual(forward_after["call_distance_from_tract"], "1")
        self.assertEqual(forward_after["read_order_previous_reference_base"], "C")
        self.assertGreater(float(forward_after["previous_reference_base_mass"]), 0.2)
        self.assertEqual(forward_after["interrupt_aligned_base"], "T")

        self.assertEqual(reverse_after["path_region"], "after")
        self.assertEqual(reverse_after["read_order_distance_from_tract"], "1")
        self.assertEqual(reverse_after["call_distance_from_tract"], "1")
        self.assertEqual(reverse_after["read_order_previous_reference_base"], "C")
        self.assertGreater(float(reverse_after["previous_reference_base_mass"]), 0.2)
        self.assertEqual(reverse_after["in_noisy_region"], "true")

    def test_partial_rcrs_tract_is_rejected(self) -> None:
        self.write_corpus()
        measurement = self.corpus / "cases" / "case-1.jsonl"
        rows = [
            json.loads(line)
            for line in measurement.read_text(encoding="utf-8").splitlines()
        ]
        rows = [row for row in rows if row["position_1based"] != 315]
        measurement.write_text(
            "".join(json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )
        index_path = self.corpus / "index.json"
        index = json.loads(index_path.read_text(encoding="utf-8"))
        index["cases"][0]["loci"] = len(rows)
        index_path.write_text(json.dumps(index), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "partially represents"):
            publish_polyc_phase(self.corpus, self.root / "research" / "polyc")

    def test_no_overwrite_and_publication_failure_rollback(self) -> None:
        self.write_corpus()
        output = self.root / "research" / "polyc"
        publish_polyc_phase(self.corpus, output)

        with self.assertRaisesRegex(ValueError, "already exists"):
            publish_polyc_phase(self.corpus, output)

        rollback = self.root / "research" / "rollback"
        from scripts.validation_corpus import polyc_phase

        real_rename = polyc_phase.os.rename

        def rename(source: Path, destination: Path) -> None:
            if source.name == "index.json":
                raise OSError("publication failed")
            real_rename(source, destination)

        with (
            patch(
                "scripts.validation_corpus.polyc_phase.os.rename",
                side_effect=rename,
            ),
            self.assertRaisesRegex(OSError, "publication failed"),
        ):
            publish_polyc_phase(self.corpus, rollback)

        self.assertFalse(rollback.exists())


if __name__ == "__main__":
    unittest.main()
