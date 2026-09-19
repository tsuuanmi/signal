"""Tests for deterministic joined validation research datasets."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.validation_corpus.model import (
    CORPUS_SCHEMA_VERSION,
    MANIFEST_SCHEMA_VERSION,
    MEASUREMENT_SCHEMA_VERSION,
    RESEARCH_SCHEMA_VERSION,
)
from scripts.validation_corpus.research_loader import (
    iter_research_rows,
    load_research_corpus,
)
from scripts.validation_corpus.research_runner import publish_research
from scripts.validation_corpus.research_statistics import (
    ResearchStatisticsAccumulator,
    nearest_rank,
)


class ValidationResearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="signal-research-test-")
        self.root = Path(self.temporary.name)
        self.corpus = self.root / "corpus"
        (self.corpus / "cases").mkdir(parents=True)
        self.read_sha256 = "1" * 64
        self.reference_sha256 = "a" * 64
        self.configuration_sha256 = "b" * 64
        self.manifest_sha256 = "c" * 64

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def observation(self, base: str, call_index: int) -> dict[str, object]:
        return {
            "read_sha256": self.read_sha256,
            "orientation": "forward",
            "state": "reference",
            "aligned_base": base,
            "quality": 60,
            "call_index_0based": call_index,
            "source_primary": base,
            "source_ambiguity": base,
            "ploc_0based": 10 + call_index,
            "window_start_0based": 9 + call_index,
            "window_end_0based_exclusive": 12 + call_index,
            "primary_peak_position_0based": 10 + call_index,
            "primary_peak_offset_from_ploc": 0,
            "event_position_0based": 10 + call_index,
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
        position: int,
        within: float,
        between: float,
        directional: float | None,
    ) -> dict[str, object]:
        total = within + between
        return {
            "schema_version": MEASUREMENT_SCHEMA_VERSION,
            "signal_version": "0.1.0",
            "sample_id": "case-1",
            "reference_sha256": self.reference_sha256,
            "configuration_sha256": self.configuration_sha256,
            "position_1based": position,
            "reference_base": "A",
            "reads": 1,
            "forward_reads": 1,
            "reverse_reads": 0,
            "reference_reads": 1,
            "alternate_reads": 0,
            "unresolved_reads": 0,
            "deletion_reads": 0,
            "profile_reads": 1,
            "profile_forward_reads": 1,
            "profile_reverse_reads": 0,
            "contributors": 1,
            "forward_contributors": 1,
            "reverse_contributors": 0,
            "mean_a": 0.92,
            "mean_c": 0.04,
            "mean_g": 0.03,
            "mean_t": 0.01,
            "within_profile_impurity": within,
            "between_profile_dispersion": between,
            "total_profile_heterogeneity": total,
            "forward_within_profile_impurity": within,
            "forward_between_profile_dispersion": between,
            "forward_total_profile_heterogeneity": total,
            "reverse_within_profile_impurity": None,
            "reverse_between_profile_dispersion": None,
            "reverse_total_profile_heterogeneity": None,
            "directional_profile_distance": directional,
            "noisy_observations": 0,
            "missing_profile_observations": 0,
            "deletion_observations": 0,
            "observations": [self.observation("A", position - 1)],
        }

    def case_record(self) -> dict[str, object]:
        return {
            "validation_case_id": "case-1",
            "source_group_id": "source-1",
            "specimen_group_id": "specimen-1",
            "truth_class": "known_point_mixture",
            "truth_method": "synthetic",
            "truth_locus": 2,
            "truth_reference": "A",
            "truth_alternate": "G",
            "known_mixture_fraction": 0.1,
            "include_in_threshold_fit": True,
            "holdout_group": "development",
            "approval_record": "synthetic-test",
            "redistribution_status": "synthetic",
            "notes": None,
            "measurement_file": "cases/case-1.jsonl",
            "loci": 2,
            "reads": [
                {
                    "trace_sha256": self.read_sha256,
                    "pcr_replicate_id": "pcr-1",
                    "sequencing_run_id": "run-1",
                    "instrument_id": "instrument-1",
                    "amplicon_id": "HV1",
                    "declared_direction": "forward",
                    "artifact_tags": ["clean"],
                }
            ],
        }

    def write_corpus(self) -> None:
        rows = [
            self.locus(1, 0.01, 0.00, None),
            self.locus(2, 0.20, 0.01, None),
        ]
        measurement = self.corpus / "cases" / "case-1.jsonl"
        measurement.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8",
        )
        index = {
            "schema_version": CORPUS_SCHEMA_VERSION,
            "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
            "measurement_schema_version": MEASUREMENT_SCHEMA_VERSION,
            "signal_version": "0.1.0",
            "manifest_sha256": self.manifest_sha256,
            "reference_sha256": self.reference_sha256,
            "configuration_sha256": self.configuration_sha256,
            "case_count": 1,
            "trace_count": 1,
            "cases": [self.case_record()],
        }
        (self.corpus / "index.json").write_text(
            json.dumps(index, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def test_joins_case_truth_and_read_provenance(self) -> None:
        self.write_corpus()

        corpus = load_research_corpus(self.corpus)
        joined = list(iter_research_rows(corpus))
        loci = [locus for locus, _ in joined]
        observations = [
            observation
            for _, locus_observations in joined
            for observation in locus_observations
        ]

        self.assertEqual(len(loci), 2)
        self.assertEqual(len(observations), 2)
        self.assertFalse(loci[0]["is_truth_locus"])
        self.assertTrue(loci[1]["is_truth_locus"])
        self.assertEqual(observations[0]["sequencing_run_id"], "run-1")
        self.assertEqual(observations[0]["artifact_tags"], "clean")
        self.assertEqual(observations[0]["profile_a"], 0.92)
        self.assertNotIn("trace_path", observations[0])

    def test_rejects_noncanonical_measurement_path(self) -> None:
        self.write_corpus()
        index_path = self.corpus / "index.json"
        index = json.loads(index_path.read_text(encoding="utf-8"))
        index["cases"][0]["measurement_file"] = "../case-1.jsonl"
        index_path.write_text(json.dumps(index), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "measurement_file must be exactly"):
            load_research_corpus(self.corpus)

    def test_rejects_measurement_identity_drift(self) -> None:
        self.write_corpus()
        measurement = self.corpus / "cases" / "case-1.jsonl"
        rows = [
            json.loads(line)
            for line in measurement.read_text(encoding="utf-8").splitlines()
        ]
        for row in rows:
            row["reference_sha256"] = "d" * 64
        measurement.write_text(
            "".join(json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )

        corpus = load_research_corpus(self.corpus)
        with self.assertRaisesRegex(ValueError, "reference SHA-256 differs"):
            list(iter_research_rows(corpus))

    def test_statistics_are_descriptive_and_nearest_rank(self) -> None:
        self.write_corpus()
        accumulator = ResearchStatisticsAccumulator()
        for locus, _ in iter_research_rows(load_research_corpus(self.corpus)):
            accumulator.add(locus)
        statistics = accumulator.result()

        self.assertEqual(statistics["quantile_method"], "empirical_nearest_rank")
        self.assertEqual(
            statistics["overall"]["metrics"]["within_profile_impurity"]["p50"], 0.01
        )
        self.assertEqual(
            statistics["overall"]["metrics"]["within_profile_impurity"]["p95"], 0.20
        )
        self.assertEqual(nearest_rank([0.01, 0.20], 0.95), 0.20)
        self.assertNotIn("threshold", statistics)

    def test_publishes_hash_bound_no_overwrite_dataset_without_paths(self) -> None:
        self.write_corpus()
        output = self.root / "research" / "baseline"

        publish_research(self.corpus, output)

        self.assertTrue((output / "loci.csv").is_file())
        self.assertTrue((output / "observations.csv").is_file())
        index_text = (output / "index.json").read_text(encoding="utf-8")
        index = json.loads(index_text)
        self.assertEqual(index["schema_version"], RESEARCH_SCHEMA_VERSION)
        self.assertEqual(index["loci_rows"], 2)
        self.assertEqual(index["observations_rows"], 2)
        self.assertEqual(len(index["loci_sha256"]), 64)
        self.assertNotIn(str(self.corpus), index_text)
        self.assertNotIn(
            str(self.corpus),
            (output / "loci.csv").read_text(encoding="utf-8"),
        )

        with self.assertRaisesRegex(ValueError, "already exists"):
            publish_research(self.corpus, output)

    def test_publication_failure_rolls_back_new_dataset(self) -> None:
        self.write_corpus()
        output = self.root / "research" / "baseline"

        from scripts.validation_corpus import research_runner

        real_rename = research_runner.os.rename

        def rename(source: Path, destination: Path) -> None:
            if source.name == "index.json":
                raise OSError("publication failed")
            real_rename(source, destination)

        with (
            patch(
                "scripts.validation_corpus.research_runner.os.rename",
                side_effect=rename,
            ),
            self.assertRaisesRegex(OSError, "publication failed"),
        ):
            publish_research(self.corpus, output)

        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
