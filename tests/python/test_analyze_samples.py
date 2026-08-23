"""Focused tests for destructive selected-sample batch cleanup."""

from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import analyze_samples as batch


class AnalyzeSamplesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="signal-batch-test-")
        self.root = Path(self.temporary.name)
        self.trace_dir = self.root / "traces"
        self.output_dir = self.root / "results"
        self.log_dir = self.root / "logs"
        self.trace_dir.mkdir()
        self.output_dir.mkdir()
        self.log_dir.mkdir()
        self.manifest = self.root / "manifest.txt"
        self.reference = self.root / "reference.fa"
        self.config = self.root / "signal.toml"
        self.binary = self.root / "signal"
        self.reference.write_text(">reference\nACGT\n", encoding="utf-8")
        self.config.write_text("schema_version=4\n", encoding="utf-8")
        self.binary.write_bytes(b"binary")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def arguments(self, *, limit: int = 1, no_build: bool = True) -> list[str]:
        arguments = [
            "--manifest",
            str(self.manifest),
            "--trace-dir",
            str(self.trace_dir),
            "--reference",
            str(self.reference),
            "--config",
            str(self.config),
            "--output-dir",
            str(self.output_dir),
            "--log-dir",
            str(self.log_dir),
            "--binary",
            str(self.binary),
            "--limit",
            str(limit),
        ]
        if no_build:
            arguments.append("--no-build")
        return arguments

    def test_clean_run_removes_selected_outputs_and_logs_only(self) -> None:
        self.manifest.write_text("S1\nS2\n", encoding="utf-8")
        trace = self.trace_dir / "run_S1_a.ab1"
        trace.write_bytes(b"trace")
        selected = self.output_dir / "S1"
        unselected = self.output_dir / "S2"
        selected.mkdir()
        unselected.mkdir()
        (selected / "old.json").write_text("old", encoding="utf-8")
        (unselected / "keep.json").write_text("keep", encoding="utf-8")
        selected_log = self.log_dir / "run_S1_old.log"
        current_log = self.log_dir / f"{trace.stem}.log"
        unselected_log = self.log_dir / "run_S2_old.log"
        unrelated_log = self.log_dir / "service.log"
        for log in [selected_log, current_log, unselected_log, unrelated_log]:
            log.write_text("log", encoding="utf-8")

        workload = batch.discover_workload(self.trace_dir, ["S1"])
        cleaned = batch.clean_previous_results(self.output_dir, self.log_dir, workload)

        self.assertEqual(cleaned, (1, 2))
        self.assertFalse(selected.exists())
        self.assertFalse(selected_log.exists())
        self.assertFalse(current_log.exists())
        self.assertTrue((unselected / "keep.json").is_file())
        self.assertTrue(unselected_log.is_file())
        self.assertTrue(unrelated_log.is_file())

    def test_symlinked_result_directory_is_rejected_without_cleanup(self) -> None:
        self.manifest.write_text("S1\n", encoding="utf-8")
        trace = self.trace_dir / "run_S1_a.ab1"
        trace.write_bytes(b"trace")
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "keep.json").write_text("keep", encoding="utf-8")
        (self.output_dir / "S1").symlink_to(outside, target_is_directory=True)
        workload = batch.discover_workload(self.trace_dir, ["S1"])

        with self.assertRaisesRegex(ValueError, "symlinked result"):
            batch.clean_previous_results(self.output_dir, self.log_dir, workload)

        self.assertTrue((outside / "keep.json").is_file())

    def test_symlinked_log_is_rejected_without_cleanup(self) -> None:
        self.manifest.write_text("S1\n", encoding="utf-8")
        trace = self.trace_dir / "run_S1_a.ab1"
        trace.write_bytes(b"trace")
        selected = self.output_dir / "S1"
        selected.mkdir()
        previous = selected / "old.json"
        previous.write_text("old", encoding="utf-8")
        source = self.root / "outside.log"
        source.write_text("keep", encoding="utf-8")
        (self.log_dir / f"{trace.stem}.log").symlink_to(source)
        workload = batch.discover_workload(self.trace_dir, ["S1"])

        with self.assertRaisesRegex(ValueError, "symlinked log"):
            batch.clean_previous_results(self.output_dir, self.log_dir, workload)

        self.assertTrue(previous.is_file())
        self.assertEqual(source.read_text(encoding="utf-8"), "keep")

    def test_missing_trace_fails_before_cleanup(self) -> None:
        self.manifest.write_text("S1\n", encoding="utf-8")
        selected = self.output_dir / "S1"
        selected.mkdir()
        previous = selected / "old.json"
        previous.write_text("old", encoding="utf-8")

        with contextlib.redirect_stderr(io.StringIO()):
            status = batch.main(self.arguments())

        self.assertEqual(status, 2)
        self.assertTrue(previous.is_file())

    def test_symlinked_trace_fails_before_cleanup(self) -> None:
        self.manifest.write_text("S1\n", encoding="utf-8")
        source = self.root / "source.ab1"
        source.write_bytes(b"trace")
        (self.trace_dir / "run_S1_a.ab1").symlink_to(source)
        selected = self.output_dir / "S1"
        selected.mkdir()
        previous = selected / "old.json"
        previous.write_text("old", encoding="utf-8")

        with contextlib.redirect_stderr(io.StringIO()):
            status = batch.main(self.arguments())

        self.assertEqual(status, 2)
        self.assertTrue(previous.is_file())

    def test_trace_matching_multiple_samples_fails_before_cleanup(self) -> None:
        self.manifest.write_text("S1\nS2\n", encoding="utf-8")
        (self.trace_dir / "run_S1_S2_a.ab1").write_bytes(b"trace")
        selected = self.output_dir / "S1"
        selected.mkdir()
        previous = selected / "old.json"
        previous.write_text("old", encoding="utf-8")

        with contextlib.redirect_stderr(io.StringIO()):
            status = batch.main(self.arguments(limit=2))

        self.assertEqual(status, 2)
        self.assertTrue(previous.is_file())

    def test_build_failure_preserves_previous_results(self) -> None:
        self.manifest.write_text("S1\n", encoding="utf-8")
        (self.trace_dir / "run_S1_a.ab1").write_bytes(b"trace")
        selected = self.output_dir / "S1"
        selected.mkdir()
        previous = selected / "old.json"
        previous.write_text("old", encoding="utf-8")

        with patch.object(
            batch.subprocess, "run", return_value=SimpleNamespace(returncode=7)
        ):
            status = batch.main(self.arguments(no_build=False))

        self.assertEqual(status, 7)
        self.assertTrue(previous.is_file())

    def test_missing_binary_preserves_previous_results(self) -> None:
        self.manifest.write_text("S1\n", encoding="utf-8")
        (self.trace_dir / "run_S1_a.ab1").write_bytes(b"trace")
        selected = self.output_dir / "S1"
        selected.mkdir()
        previous = selected / "old.json"
        previous.write_text("old", encoding="utf-8")
        self.binary.unlink()

        with contextlib.redirect_stderr(io.StringIO()):
            status = batch.main(self.arguments())

        self.assertEqual(status, 2)
        self.assertTrue(previous.is_file())

    def test_publication_is_durable_and_never_overwrites(self) -> None:
        generated = self.root / "generated.json"
        generated.write_text("new", encoding="utf-8")
        destination = self.output_dir / "S1" / "trace.json"

        succeeded, detail = batch.publish_result(generated, destination)
        self.assertTrue(succeeded, detail)
        self.assertEqual(destination.read_text(encoding="utf-8"), "new")

        generated.write_text("replacement", encoding="utf-8")
        succeeded, detail = batch.publish_result(generated, destination)
        self.assertFalse(succeeded)
        self.assertIn("appeared while analysis was running", detail)
        self.assertEqual(destination.read_text(encoding="utf-8"), "new")

    def test_directory_sync_failure_rolls_back_publication(self) -> None:
        generated = self.root / "generated.json"
        generated.write_text("new", encoding="utf-8")
        destination = self.output_dir / "S1" / "trace.json"

        with patch.object(
            batch.os,
            "fsync",
            side_effect=[None, OSError("directory sync failed"), None],
        ):
            succeeded, detail = batch.publish_result(generated, destination)

        self.assertFalse(succeeded)
        self.assertIn("directory sync failed", detail)
        self.assertFalse(destination.exists())

    def test_existing_results_are_cleaned_and_every_trace_reruns(self) -> None:
        self.manifest.write_text("S1\n", encoding="utf-8")
        traces = [
            self.trace_dir / "run_S1_a.ab1",
            self.trace_dir / "run_S1_b.ab1",
        ]
        for trace in traces:
            trace.write_bytes(b"trace")
        selected = self.output_dir / "S1"
        selected.mkdir()
        (selected / f"{traces[0].stem}.json").write_text("old", encoding="utf-8")
        invoked: list[Path] = []

        def successful_run(
            _binary: Path,
            trace: Path,
            _reference: Path,
            _config: Path,
            _log_dir: Path,
            destination: Path,
        ) -> tuple[bool, str]:
            invoked.append(trace)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text("new", encoding="utf-8")
            return True, ""

        with (
            patch.object(batch, "run_analysis", side_effect=successful_run),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            status = batch.main(self.arguments())

        self.assertEqual(status, 0)
        self.assertEqual(invoked, [trace.resolve() for trace in traces])
        for trace in traces:
            self.assertEqual(
                (self.output_dir / "S1" / f"{trace.stem}.json").read_text(
                    encoding="utf-8"
                ),
                "new",
            )


if __name__ == "__main__":
    unittest.main()
