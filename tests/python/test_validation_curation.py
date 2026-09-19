"""Tests for deterministic validation curation queue preparation."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.validation_corpus.audit_analysis import (
    AUDIT_SCHEMA_VERSION,
    CASE_AUDIT_COLUMNS,
    LOCUS_AUDIT_COLUMNS,
    READ_AUDIT_COLUMNS,
)
from scripts.validation_corpus.curation import (
    CURATION_QUEUE_SCHEMA_VERSION,
    DECISION_COLUMNS,
    QUEUE_COLUMNS,
    publish_curation_queue,
)
from scripts.validation_corpus.filesystem import file_sha256


class ValidationCurationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="signal-curation-test-")
        self.root = Path(self.temporary.name)
        self.audit = self.root / "audit"
        self.audit.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def write_csv(
        path: Path,
        columns: tuple[str, ...],
        rows: list[dict[str, object]],
    ) -> None:
        with path.open("w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(target, fieldnames=list(columns))
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def read_row(
        case_id: str,
        read_sha256: str,
        flags: str,
    ) -> dict[str, object]:
        row: dict[str, object] = {column: "" for column in READ_AUDIT_COLUMNS}
        row.update(
            {
                "validation_case_id": case_id,
                "read_sha256": read_sha256,
                "amplicon_id": "HV1",
                "declared_direction": "forward",
                "callable_identity": "0.95",
                "noise_rate": "0.20",
                "retained_fraction": "0.70",
                "callable_columns": "300",
                "audit_flags": flags,
            }
        )
        return row

    @staticmethod
    def locus_row(
        case_id: str,
        position: int,
        *,
        edge: bool,
        noisy: int,
    ) -> dict[str, object]:
        row: dict[str, object] = {column: "" for column in LOCUS_AUDIT_COLUMNS}
        row.update(
            {
                "validation_case_id": case_id,
                "position_1based": position,
                "reference_base": "A",
                "alternate_observations": 1,
                "alternate_noisy_observations": noisy,
                "alternate_near_read_edge_observations": int(edge),
                "cross_orientation_alternate": "false",
                "minimum_alternate_edge_distance_calls": 5 if edge else 20,
                "edge_discordance": "true" if edge else "false",
                "audit_flags": "edge_discordance" if edge else "",
            }
        )
        return row

    @staticmethod
    def case_row(
        case_id: str,
        mixed_loci: int,
        edge_loci: int,
    ) -> dict[str, object]:
        row: dict[str, object] = {column: "" for column in CASE_AUDIT_COLUMNS}
        row.update(
            {
                "validation_case_id": case_id,
                "mixed_loci": mixed_loci,
                "edge_discordance_loci": edge_loci,
            }
        )
        return row

    def write_audit(self) -> None:
        read_path = self.audit / "read-audit.csv"
        locus_path = self.audit / "locus-audit.csv"
        case_path = self.audit / "case-audit.csv"
        self.write_csv(
            read_path,
            READ_AUDIT_COLUMNS,
            [
                self.read_row("case-1", "1" * 64, "alignment_challenge"),
                self.read_row("case-2", "2" * 64, ""),
            ],
        )
        self.write_csv(
            locus_path,
            LOCUS_AUDIT_COLUMNS,
            [
                self.locus_row("case-1", 253, edge=False, noisy=0),
                self.locus_row("case-2", 253, edge=True, noisy=1),
                self.locus_row("case-2", 302, edge=False, noisy=1),
            ],
        )
        self.write_csv(
            case_path,
            CASE_AUDIT_COLUMNS,
            [
                self.case_row("case-1", 1, 0),
                self.case_row("case-2", 2, 1),
            ],
        )
        index = {
            "schema_version": AUDIT_SCHEMA_VERSION,
            "source_corpus_sha256": "a" * 64,
            "source_research_sha256": "b" * 64,
            "signal_version": "0.1.0",
            "manifest_sha256": "c" * 64,
            "reference_sha256": "d" * 64,
            "configuration_sha256": "e" * 64,
            "method": {},
            "read_strata": [],
            "read_audit_file": "read-audit.csv",
            "read_audit_sha256": file_sha256(read_path),
            "read_audit_rows": 2,
            "read_audit_columns": list(READ_AUDIT_COLUMNS),
            "read_flag_counts": {"alignment_challenge": 1},
            "locus_audit_file": "locus-audit.csv",
            "locus_audit_sha256": file_sha256(locus_path),
            "locus_audit_rows": 3,
            "locus_audit_columns": list(LOCUS_AUDIT_COLUMNS),
            "locus_flag_counts": {"edge_discordance": 1},
            "case_audit_file": "case-audit.csv",
            "case_audit_sha256": file_sha256(case_path),
            "case_audit_rows": 2,
            "case_audit_columns": list(CASE_AUDIT_COLUMNS),
            "case_flag_counts": {},
            "research_loci_rows": 3,
            "research_observations_rows": 4,
        }
        (self.audit / "index.json").write_text(
            json.dumps(index, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def test_queue_contains_all_mixed_loci_and_only_flagged_reads(self) -> None:
        self.write_audit()
        output = self.root / "curation"

        publish_curation_queue(self.audit, output)

        with (output / "curation-queue.csv").open(
            "r", encoding="utf-8", newline=""
        ) as source:
            rows = list(csv.DictReader(source))
        self.assertEqual(len(rows), 4)
        self.assertEqual([row["item_type"] for row in rows], [
            "mixed_locus",
            "mixed_locus",
            "mixed_locus",
            "read",
        ])
        self.assertEqual([row["position_1based"] for row in rows[:2]], ["253", "253"])
        self.assertEqual(rows[0]["recurrence_cases"], "2")
        self.assertIn("recurrent_mixed_locus", rows[0]["review_reasons"])
        self.assertIn("edge_discordance", rows[1]["review_reasons"])
        self.assertIn("noisy_alternate", rows[1]["review_reasons"])
        self.assertEqual(rows[-1]["read_sha256"], "1" * 64)
        self.assertEqual(rows[-1]["review_reasons"], "alignment_challenge")

    def test_decisions_template_is_separate_and_blank(self) -> None:
        self.write_audit()
        output = self.root / "curation"

        publish_curation_queue(self.audit, output)

        with (output / "curation-decisions-template.csv").open(
            "r", encoding="utf-8", newline=""
        ) as source:
            rows = list(csv.DictReader(source))
        self.assertEqual(tuple(rows[0]), DECISION_COLUMNS)
        self.assertEqual(len(rows), 4)
        for row in rows:
            self.assertTrue(row["review_item_id"])
            self.assertEqual(row["review_status"], "")
            self.assertEqual(row["truth_source"], "")
            self.assertEqual(row["curation_decision"], "")
            self.assertEqual(row["curation_notes"], "")

    def test_index_hash_binds_source_and_outputs(self) -> None:
        self.write_audit()
        output = self.root / "curation"

        publish_curation_queue(self.audit, output)

        index = json.loads((output / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(index["schema_version"], CURATION_QUEUE_SCHEMA_VERSION)
        self.assertEqual(
            index["source_audit_sha256"],
            file_sha256(self.audit / "index.json"),
        )
        self.assertEqual(index["queue_rows"], 4)
        self.assertEqual(index["queue_columns"], list(QUEUE_COLUMNS))
        self.assertEqual(
            index["item_counts"],
            {"mixed_locus": 3, "read": 1},
        )
        self.assertEqual(
            index["queue_sha256"],
            file_sha256(output / "curation-queue.csv"),
        )

    def test_rejects_modified_audit_table(self) -> None:
        self.write_audit()
        with (self.audit / "read-audit.csv").open("a", encoding="utf-8") as target:
            target.write("\n")

        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            publish_curation_queue(self.audit, self.root / "curation")

    def test_no_overwrite(self) -> None:
        self.write_audit()
        output = self.root / "curation"
        publish_curation_queue(self.audit, output)

        with self.assertRaisesRegex(ValueError, "already exists"):
            publish_curation_queue(self.audit, output)

    def test_publication_failure_rolls_back(self) -> None:
        self.write_audit()
        output = self.root / "curation"

        from scripts.validation_corpus import curation

        real_rename = curation.os.rename

        def rename(source: Path, destination: Path) -> None:
            if source.name == "index.json":
                raise OSError("publication failed")
            real_rename(source, destination)

        with (
            patch(
                "scripts.validation_corpus.curation.os.rename",
                side_effect=rename,
            ),
            self.assertRaisesRegex(OSError, "publication failed"),
        ):
            publish_curation_queue(self.audit, output)

        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
