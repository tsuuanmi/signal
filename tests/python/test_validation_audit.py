"""Tests for observational validation audit strata."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.validation_corpus.audit_analysis import (
    audit_mixed_observations,
    load_locus_context,
    locus_audit_rows,
    read_audit_rows,
    read_boundaries,
)
from scripts.validation_corpus.audit_logs import parse_case_log
from scripts.validation_corpus.audit_model import (
    AUDIT_SCHEMA_VERSION,
    LOCUS_AUDIT_COLUMNS,
    MINIMUM_STRATUM_READS,
    RawReadAudit,
)
from scripts.validation_corpus.audit_runner import publish_audit
from scripts.validation_corpus.filesystem import file_sha256
from scripts.validation_corpus.model import (
    CORPUS_SCHEMA_VERSION,
    MANIFEST_SCHEMA_VERSION,
    MEASUREMENT_SCHEMA_VERSION,
    RESEARCH_SCHEMA_VERSION,
)
from scripts.validation_corpus.research_model import (
    LOCUS_TABLE_COLUMNS,
    OBSERVATION_TABLE_COLUMNS,
)


class ValidationAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="signal-audit-test-")
        self.root = Path(self.temporary.name)
        self.corpus = self.root / "corpus"
        self.research = self.root / "research"
        (self.corpus / "logs").mkdir(parents=True)
        (self.corpus / "cases").mkdir()
        self.research.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def raw_read(
        self,
        index: int,
        *,
        identity: float = 0.99,
        noise_rate: float = 0.10,
        retained_fraction: float = 0.90,
        callable_columns: int = 400,
    ) -> RawReadAudit:
        calls = 500
        return RawReadAudit(
            validation_case_id="case-1",
            read_sha256=f"{index + 1:064x}",
            sequencing_run_id="run-1",
            amplicon_id="HV1",
            declared_direction="forward",
            inferred_orientation="forward",
            calls=calls,
            profiled_loci=calls,
            noisy_calls=round(noise_rate * calls),
            trim_start_0based=0,
            trim_end_0based_exclusive=450,
            retained=round(retained_fraction * calls),
            retained_fraction=retained_fraction,
            callable_columns=callable_columns,
            callable_identity=identity,
            mismatches=2,
            gap_opens=1,
            excluded_variant_candidates=0,
        )

    def test_read_flags_use_benchmarked_stratum_tails(self) -> None:
        records = [
            self.raw_read(
                0,
                identity=0.90,
                noise_rate=0.50,
                retained_fraction=0.30,
                callable_columns=50,
            ),
            self.raw_read(
                1,
                identity=0.91,
                noise_rate=0.49,
                retained_fraction=0.30,
                callable_columns=50,
            ),
            *(self.raw_read(index) for index in range(2, MINIMUM_STRATUM_READS)),
        ]

        boundaries = read_boundaries(records)
        rows = read_audit_rows(records, boundaries)

        self.assertEqual(rows[0]["stratum_n"], MINIMUM_STRATUM_READS)
        self.assertTrue(rows[0]["alignment_challenge"])
        self.assertTrue(rows[0]["high_noise"])
        self.assertTrue(rows[0]["aggressive_trim"])
        self.assertTrue(rows[0]["short_coverage"])
        self.assertFalse(rows[0]["unbenchmarked_stratum"])
        self.assertFalse(rows[-1]["alignment_challenge"])

    def test_small_stratum_is_unbenchmarked(self) -> None:
        records = [self.raw_read(index) for index in range(3)]

        rows = read_audit_rows(records, read_boundaries(records))

        self.assertTrue(all(row["unbenchmarked_stratum"] for row in rows))
        self.assertTrue(all(row["identity_p05"] is None for row in rows))
        self.assertTrue(all(not row["high_noise"] for row in rows))

    def test_log_parser_binds_complete_read_metrics(self) -> None:
        read_sha256 = "1" * 64
        log = self.root / "case-1.validation.log"
        log.write_text(
            "\n".join(
                [
                    f"2026 | INFO | x - event=sample_read_started "
                    f'trace_name="trace.ab1" trace_sha256={read_sha256}',
                    "2026 | INFO | x - event=basecalling_completed calls=500",
                    "2026 | INFO | x - event=signal_processing_completed "
                    "profiled_loci=499 noisy_calls=25",
                    "2026 | INFO | x - event=quality_control_completed "
                    "trim=10..460 retained=450 retained_fraction=0.9000",
                    "2026 | INFO | x - event=alignment_completed "
                    "orientation=Forward callable_columns=440 "
                    "callable_identity=0.9875 mismatches=5 gap_opens=1",
                    "2026 | WARN | x - event=warning_summary "
                    "excluded_variant_candidates=3",
                    f"2026 | INFO | x - event=sample_read_completed "
                    f"trace_sha256={read_sha256} orientation=Forward",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        expected = {
            read_sha256: {
                "sequencing_run_id": "run-1",
                "amplicon_id": "HV1",
                "declared_direction": "forward",
            }
        }

        records = parse_case_log(log, "case-1", expected)

        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record.trim_start_0based, 10)
        self.assertEqual(record.trim_end_0based_exclusive, 460)
        self.assertAlmostEqual(record.callable_identity, 0.9875)
        self.assertEqual(record.excluded_variant_candidates, 3)

    def write_csv(
        self,
        path: Path,
        columns: tuple[str, ...],
        rows: list[dict[str, object]],
    ) -> None:
        with path.open("w", encoding="utf-8", newline="") as target:
            fieldnames: list[str] = list(columns)
            writer = csv.DictWriter(target, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def locus_row(self) -> dict[str, object]:
        row: dict[str, object] = {column: "" for column in LOCUS_TABLE_COLUMNS}
        row.update(
            {
                "validation_case_id": "case-1",
                "source_group_id": "source-1",
                "specimen_group_id": "specimen-1",
                "position_1based": 100,
                "reference_base": "A",
                "reads": 2,
                "reference_reads": 1,
                "alternate_reads": 1,
                "contributors": 2,
                "forward_contributors": 2,
                "reverse_contributors": 0,
                "noisy_observations": 1,
                "within_profile_impurity": 0.1,
                "between_profile_dispersion": 0.2,
                "total_profile_heterogeneity": 0.3,
                "directional_profile_distance": "",
            }
        )
        return row

    def observation_row(
        self,
        read_sha256: str,
        state: str,
        call_index: int,
        noisy: bool,
    ) -> dict[str, object]:
        row: dict[str, object] = {column: "" for column in OBSERVATION_TABLE_COLUMNS}
        row.update(
            {
                "validation_case_id": "case-1",
                "position_1based": 100,
                "reference_base": "A",
                "read_sha256": read_sha256,
                "orientation": "forward",
                "state": state,
                "call_index_0based": call_index,
                "in_noisy_region": "true" if noisy else "false",
            }
        )
        return row

    def test_edge_discordance_uses_retained_call_edge(self) -> None:
        loci = self.root / "loci.csv"
        observations = self.root / "observations.csv"
        read1 = self.raw_read(0)
        read2 = self.raw_read(1)
        self.write_csv(loci, LOCUS_TABLE_COLUMNS, [self.locus_row()])
        self.write_csv(
            observations,
            OBSERVATION_TABLE_COLUMNS,
            [
                self.observation_row(read1.read_sha256, "alternate", 5, True),
                self.observation_row(read2.read_sha256, "reference", 20, False),
            ],
        )

        _, mixed = load_locus_context(loci)
        audit_mixed_observations(
            observations,
            mixed,
            {read1.read_sha256: read1, read2.read_sha256: read2},
        )
        rows = locus_audit_rows(mixed)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["minimum_alternate_edge_distance_calls"], 5)
        self.assertTrue(rows[0]["edge_discordance"])
        self.assertFalse(rows[0]["cross_orientation_alternate"])

    def write_fixture(self) -> None:
        hashes = [f"{index + 1:064x}" for index in range(MINIMUM_STRATUM_READS)]
        reads = [
            {
                "trace_sha256": read_sha256,
                "pcr_replicate_id": None,
                "sequencing_run_id": "run-1",
                "instrument_id": None,
                "amplicon_id": "HV1",
                "declared_direction": "forward",
                "artifact_tags": [],
            }
            for read_sha256 in hashes
        ]
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
            "loci": 1,
            "reads": reads,
        }
        corpus_index = {
            "schema_version": CORPUS_SCHEMA_VERSION,
            "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
            "measurement_schema_version": MEASUREMENT_SCHEMA_VERSION,
            "signal_version": "0.1.0",
            "manifest_sha256": "a" * 64,
            "reference_sha256": "b" * 64,
            "configuration_sha256": "c" * 64,
            "case_count": 1,
            "trace_count": len(hashes),
            "cases": [case],
        }
        (self.corpus / "index.json").write_text(
            json.dumps(corpus_index, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        log_lines: list[str] = []
        for index, read_sha256 in enumerate(hashes):
            extreme = index < 2
            identity = 0.90 if extreme else 0.99
            noise = 250 if extreme else 50
            retained_fraction = 0.30 if extreme else 0.90
            retained = 150 if extreme else 450
            callable_columns = 50 if extreme else 400
            log_lines.extend(
                [
                    f"2026 | INFO | x - event=sample_read_started "
                    f'trace_name="trace-{index}.ab1" trace_sha256={read_sha256}',
                    "2026 | INFO | x - event=basecalling_completed calls=500",
                    "2026 | INFO | x - event=signal_processing_completed "
                    f"profiled_loci=500 noisy_calls={noise}",
                    "2026 | INFO | x - event=quality_control_completed "
                    f"trim=0..450 retained={retained} "
                    f"retained_fraction={retained_fraction:.4f}",
                    "2026 | INFO | x - event=alignment_completed "
                    f"orientation=Forward callable_columns={callable_columns} "
                    f"callable_identity={identity:.4f} mismatches=2 gap_opens=1",
                    "2026 | WARN | x - event=warning_summary "
                    "excluded_variant_candidates=0",
                    f"2026 | INFO | x - event=sample_read_completed "
                    f"trace_sha256={read_sha256} orientation=Forward",
                ]
            )
        (self.corpus / "logs" / "case-1.validation.log").write_text(
            "\n".join(log_lines) + "\n",
            encoding="utf-8",
        )

        locus = self.locus_row()
        locus["reads"] = len(hashes)
        locus["reference_reads"] = len(hashes) - 1
        locus["alternate_reads"] = 1
        locus["contributors"] = len(hashes)
        locus["forward_contributors"] = len(hashes)
        loci_path = self.research / "loci.csv"
        self.write_csv(loci_path, LOCUS_TABLE_COLUMNS, [locus])

        observation_rows = [
            self.observation_row(
                read_sha256,
                "alternate" if index == 0 else "reference",
                5 if index == 0 else 20 + index,
                index == 0,
            )
            for index, read_sha256 in enumerate(hashes)
        ]
        observations_path = self.research / "observations.csv"
        self.write_csv(
            observations_path,
            OBSERVATION_TABLE_COLUMNS,
            observation_rows,
        )
        research_index = {
            "schema_version": RESEARCH_SCHEMA_VERSION,
            "source_corpus_sha256": file_sha256(self.corpus / "index.json"),
            "signal_version": "0.1.0",
            "manifest_sha256": "a" * 64,
            "reference_sha256": "b" * 64,
            "configuration_sha256": "c" * 64,
            "loci_file": "loci.csv",
            "loci_sha256": file_sha256(loci_path),
            "loci_rows": 1,
            "loci_columns": list(LOCUS_TABLE_COLUMNS),
            "observations_file": "observations.csv",
            "observations_sha256": file_sha256(observations_path),
            "observations_rows": len(observation_rows),
            "observations_columns": list(OBSERVATION_TABLE_COLUMNS),
            "statistics": {},
        }
        (self.research / "index.json").write_text(
            json.dumps(research_index, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def test_publish_audit_is_hash_bound_and_no_overwrite(self) -> None:
        self.write_fixture()
        output = self.root / "audit"

        publish_audit(self.corpus, self.research, output)

        index = json.loads((output / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(index["schema_version"], AUDIT_SCHEMA_VERSION)
        self.assertEqual(index["read_audit_rows"], MINIMUM_STRATUM_READS)
        self.assertEqual(index["locus_audit_rows"], 1)
        self.assertEqual(index["case_audit_rows"], 1)
        self.assertEqual(index["locus_flag_counts"]["edge_discordance"], 1)
        self.assertEqual(index["case_flag_counts"]["short_coverage_cluster"], 1)
        for name in ("read-audit.csv", "locus-audit.csv", "case-audit.csv"):
            self.assertTrue((output / name).is_file())

        with self.assertRaisesRegex(ValueError, "already exists"):
            publish_audit(self.corpus, self.research, output)

    def test_rejects_research_from_another_corpus(self) -> None:
        self.write_fixture()
        index_path = self.research / "index.json"
        index = json.loads(index_path.read_text(encoding="utf-8"))
        index["source_corpus_sha256"] = "f" * 64
        index_path.write_text(json.dumps(index), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "does not match"):
            publish_audit(self.corpus, self.research, self.root / "audit")

    def test_publication_failure_rolls_back(self) -> None:
        self.write_fixture()
        output = self.root / "audit"

        from scripts.validation_corpus import audit_runner

        real_rename = audit_runner.os.rename

        def rename(source: Path, destination: Path) -> None:
            if source.name == "index.json":
                raise OSError("publication failed")
            real_rename(source, destination)

        with (
            patch(
                "scripts.validation_corpus.audit_runner.os.rename",
                side_effect=rename,
            ),
            self.assertRaisesRegex(OSError, "publication failed"),
        ):
            publish_audit(self.corpus, self.research, output)

        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
