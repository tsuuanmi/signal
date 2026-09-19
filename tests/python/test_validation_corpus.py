"""Tests for manifest-driven local validation corpus orchestration."""

from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.validation_corpus.manifest import load_manifest
from scripts.validation_corpus.measurements import measurement_summary
from scripts.validation_corpus.model import (
    CORPUS_SCHEMA_VERSION,
    MANIFEST_COLUMNS,
    MEASUREMENT_SCHEMA_VERSION,
)
from scripts.validation_corpus.runner import run_corpus


class ValidationCorpusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="signal-validation-test-")
        self.root = Path(self.temporary.name)
        self.data = self.root / "data"
        self.data.mkdir()
        self.reference = self.root / "reference.fa"
        self.reference.write_text(">r\nACGT\n", encoding="utf-8")
        self.config = self.root / "signal.toml"
        self.config.write_text("schema_version = 5\n", encoding="utf-8")
        self.binary = self.root / "signal-validation"
        self.binary.write_bytes(b"binary")
        self.manifest = self.data / "manifest.csv"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def trace(self, name: str, content: bytes) -> tuple[Path, str]:
        path = self.data / name
        path.write_bytes(content)
        return path, hashlib.sha256(content).hexdigest()

    def row(self, trace_name: str, trace_sha256: str, **updates: str) -> dict[str, str]:
        row = {
            "validation_case_id": "case-1",
            "trace_path": trace_name,
            "trace_sha256": trace_sha256,
            "source_group_id": "source-1",
            "specimen_group_id": "specimen-1",
            "pcr_replicate_id": "pcr-1",
            "sequencing_run_id": "run-1",
            "instrument_id": "instrument-1",
            "amplicon_id": "HV1",
            "declared_direction": "forward",
            "truth_class": "clean_homoplasmic",
            "truth_method": "synthetic",
            "truth_locus": "",
            "truth_reference": "",
            "truth_alternate": "",
            "known_mixture_fraction": "0",
            "artifact_tags": "clean",
            "include_in_threshold_fit": "true",
            "holdout_group": "development",
            "approval_record": "synthetic-test",
            "redistribution_status": "synthetic",
            "notes": "",
        }
        row.update(updates)
        return row

    def write_manifest(self, rows: list[dict[str, str]]) -> None:
        with self.manifest.open("w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(target, fieldnames=MANIFEST_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)

    def measurement_row(
        self, case_id: str, reads: list[str], position: int
    ) -> dict[str, object]:
        return {
            "schema_version": MEASUREMENT_SCHEMA_VERSION,
            "signal_version": "0.1.0",
            "sample_id": case_id,
            "reference_sha256": "a" * 64,
            "configuration_sha256": "b" * 64,
            "position_1based": position,
            "reads": len(reads),
            "observations": [{"read_sha256": read_sha256} for read_sha256 in reads],
        }

    def test_manifest_hash_checks_and_groups_trace_rows(self) -> None:
        _, sha1 = self.trace("a.ab1", b"a")
        _, sha2 = self.trace("b.ab1", b"b")
        self.write_manifest(
            [
                self.row("a.ab1", sha1),
                self.row(
                    "b.ab1",
                    sha2,
                    declared_direction="reverse",
                    sequencing_run_id="run-2",
                ),
            ]
        )

        cases = load_manifest(self.manifest)

        self.assertEqual(len(cases), 1)
        self.assertEqual(len(cases[0].traces), 2)
        self.assertEqual(cases[0].traces[1].declared_direction, "reverse")
        self.assertEqual(cases[0].metadata.known_mixture_fraction, 0.0)

    def test_manifest_rejects_hash_mismatch(self) -> None:
        self.trace("a.ab1", b"a")
        self.write_manifest([self.row("a.ab1", "0" * 64)])

        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            load_manifest(self.manifest)

    def test_manifest_rejects_case_level_metadata_changes(self) -> None:
        _, sha1 = self.trace("a.ab1", b"a")
        _, sha2 = self.trace("b.ab1", b"b")
        self.write_manifest(
            [
                self.row("a.ab1", sha1),
                self.row("b.ab1", sha2, truth_class="known_point_mixture"),
            ]
        )

        with self.assertRaisesRegex(ValueError, "case-level metadata changed"):
            load_manifest(self.manifest)

    def test_manifest_rejects_trace_reuse_across_cases(self) -> None:
        _, sha = self.trace("a.ab1", b"a")
        self.write_manifest(
            [
                self.row("a.ab1", sha),
                self.row(
                    "a.ab1",
                    sha,
                    validation_case_id="case-2",
                    source_group_id="source-2",
                ),
            ]
        )

        with self.assertRaisesRegex(ValueError, "already belongs to case-1"):
            load_manifest(self.manifest)

    def test_measurement_validation_rejects_unexpected_read(self) -> None:
        _, sha1 = self.trace("a.ab1", b"a")
        self.write_manifest([self.row("a.ab1", sha1)])
        case = load_manifest(self.manifest)[0]
        path = self.root / "bad.jsonl"
        path.write_text(
            json.dumps(self.measurement_row("case-1", ["f" * 64], 1)) + "\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "unexpected read SHA-256"):
            measurement_summary(path, case)

    def test_run_corpus_publishes_only_after_all_cases_succeed(self) -> None:
        _, sha1 = self.trace("a.ab1", b"a")
        _, sha2 = self.trace("b.ab1", b"b")
        self.write_manifest(
            [
                self.row("a.ab1", sha1),
                self.row(
                    "b.ab1",
                    sha2,
                    validation_case_id="case-2",
                    source_group_id="source-2",
                ),
            ]
        )
        cases = load_manifest(self.manifest)
        output = self.root / "validation-results" / "corpus"

        def execute(
            command: list[str],
            *,
            cwd: Path,
            env: dict[str, str],
            check: bool,
            capture_output: bool,
            text: bool,
        ) -> SimpleNamespace:
            self.assertFalse(check)
            self.assertTrue(capture_output)
            self.assertTrue(text)
            case_id = command[1]
            case = next(c for c in cases if c.metadata.validation_case_id == case_id)
            generated = cwd / "validation-results" / f"{case_id}.jsonl"
            generated.parent.mkdir()
            reads = [trace.trace_sha256 for trace in case.traces]
            generated.write_text(
                json.dumps(self.measurement_row(case_id, reads, 1)) + "\n",
                encoding="utf-8",
            )
            log_dir = Path(env["SIGNAL_LOG_DIR"])
            log_dir.mkdir(parents=True, exist_ok=True)
            (log_dir / f"{case_id}.validation.log").write_text(
                "log", encoding="utf-8"
            )
            return SimpleNamespace(returncode=0, stderr="")

        with patch(
            "scripts.validation_corpus.runner.subprocess.run", side_effect=execute
        ):
            run_corpus(
                self.manifest.resolve(),
                cases,
                self.reference.resolve(),
                self.config.resolve(),
                self.binary.resolve(),
                output.resolve(),
            )

        self.assertTrue((output / "cases" / "case-1.jsonl").is_file())
        self.assertTrue((output / "cases" / "case-2.jsonl").is_file())
        self.assertTrue((output / "logs" / "case-1.validation.log").is_file())
        index_text = (output / "index.json").read_text(encoding="utf-8")
        index = json.loads(index_text)
        self.assertEqual(index["schema_version"], CORPUS_SCHEMA_VERSION)
        self.assertEqual(index["case_count"], 2)
        self.assertEqual(index["trace_count"], 2)
        self.assertNotIn(str(self.data), index_text)

    def test_failed_case_leaves_no_published_corpus(self) -> None:
        _, sha1 = self.trace("a.ab1", b"a")
        self.write_manifest([self.row("a.ab1", sha1)])
        cases = load_manifest(self.manifest)
        output = self.root / "validation-results" / "corpus"

        with patch(
            "scripts.validation_corpus.runner.subprocess.run",
            return_value=SimpleNamespace(returncode=1, stderr="boom"),
        ):
            with self.assertRaisesRegex(RuntimeError, "boom"):
                run_corpus(
                    self.manifest.resolve(),
                    cases,
                    self.reference.resolve(),
                    self.config.resolve(),
                    self.binary.resolve(),
                    output.resolve(),
                )

        self.assertFalse(output.exists())

    def test_existing_output_is_never_replaced(self) -> None:
        _, sha1 = self.trace("a.ab1", b"a")
        self.write_manifest([self.row("a.ab1", sha1)])
        cases = load_manifest(self.manifest)
        output = self.root / "validation-results" / "corpus"
        output.mkdir(parents=True)
        marker = output / "keep.txt"
        marker.write_text("keep", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "already exists"):
            run_corpus(
                self.manifest.resolve(),
                cases,
                self.reference.resolve(),
                self.config.resolve(),
                self.binary.resolve(),
                output.resolve(),
            )
        self.assertEqual(marker.read_text(encoding="utf-8"), "keep")


if __name__ == "__main__":
    unittest.main()
