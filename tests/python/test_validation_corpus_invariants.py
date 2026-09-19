"""Additional corpus leakage and publication invariants."""

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
from scripts.validation_corpus.model import MANIFEST_COLUMNS, MEASUREMENT_SCHEMA_VERSION
from scripts.validation_corpus.runner import run_corpus


class ValidationCorpusInvariantTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="signal-validation-invariant-"
        )
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

    def trace(self, name: str, content: bytes) -> str:
        path = self.data / name
        path.write_bytes(content)
        return hashlib.sha256(content).hexdigest()

    def row(
        self,
        case_id: str,
        trace_name: str,
        trace_sha256: str,
        holdout_group: str,
    ) -> dict[str, str]:
        return {
            "validation_case_id": case_id,
            "trace_path": trace_name,
            "trace_sha256": trace_sha256,
            "source_group_id": "source-1",
            "specimen_group_id": "specimen-1",
            "pcr_replicate_id": "pcr-1",
            "sequencing_run_id": "run-1",
            "instrument_id": "instrument-1",
            "amplicon_id": "HV1",
            "declared_direction": "",
            "truth_class": "clean_homoplasmic",
            "truth_method": "synthetic",
            "truth_locus": "",
            "truth_reference": "",
            "truth_alternate": "",
            "known_mixture_fraction": "0",
            "artifact_tags": "clean",
            "include_in_threshold_fit": "true",
            "holdout_group": holdout_group,
            "approval_record": "synthetic-test",
            "redistribution_status": "synthetic",
            "notes": "",
        }

    def write_manifest(self, rows: list[dict[str, str]]) -> None:
        with self.manifest.open("w", encoding="utf-8", newline="") as target:
            fieldnames: list[str] = list(MANIFEST_COLUMNS)
            writer = csv.DictWriter(target, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def test_rejects_source_group_split_across_holdout_groups(self) -> None:
        sha1 = self.trace("a.ab1", b"a")
        sha2 = self.trace("b.ab1", b"b")
        self.write_manifest(
            [
                self.row("case-1", "a.ab1", sha1, "development"),
                self.row("case-2", "b.ab1", sha2, "holdout"),
            ]
        )

        with self.assertRaisesRegex(ValueError, "spans holdout groups"):
            load_manifest(self.manifest)

    def test_publication_failure_rolls_back_new_output(self) -> None:
        sha = self.trace("a.ab1", b"a")
        self.write_manifest([self.row("case-1", "a.ab1", sha, "development")])
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
            generated = cwd / "validation-results" / f"{case_id}.jsonl"
            generated.parent.mkdir()
            generated.write_text(
                json.dumps(
                    {
                        "schema_version": MEASUREMENT_SCHEMA_VERSION,
                        "signal_version": "0.1.0",
                        "sample_id": case_id,
                        "reference_sha256": "a" * 64,
                        "configuration_sha256": "b" * 64,
                        "position_1based": 1,
                        "reads": 1,
                        "observations": [{"read_sha256": sha}],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            Path(env["SIGNAL_LOG_DIR"]).mkdir(parents=True, exist_ok=True)
            return SimpleNamespace(returncode=0, stderr="")

        from scripts.validation_corpus import runner

        real_rename = runner.os.rename

        def rename(source: Path, destination: Path) -> None:
            if Path(source).name == "index.json":
                raise OSError("publication failed")
            real_rename(source, destination)

        with (
            patch(
                "scripts.validation_corpus.runner.subprocess.run",
                side_effect=execute,
            ),
            patch(
                "scripts.validation_corpus.runner.os.rename",
                side_effect=rename,
            ),
            self.assertRaisesRegex(OSError, "publication failed"),
        ):
            run_corpus(
                self.manifest.resolve(),
                cases,
                self.reference.resolve(),
                self.config.resolve(),
                self.binary.resolve(),
                output.resolve(),
            )

        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
