"""Tests for reviewer-derived sample variant-profile comparison."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.validation_corpus.variant_profile import (
    compare_profiles,
    load_signal_variants,
    parse_reviewer_variants,
    sequence_sha256,
)


class VariantProfileComparisonTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="signal-variant-profile-test-"
        )
        self.root = Path(self.temporary.name)
        self.reference_name = "rCRS"
        self.reference = "AACCCCGTTT"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def sample(self, variants: list[dict[str, object]]) -> Path:
        path = self.root / "sample.json"
        path.write_text(
            json.dumps(
                {
                    "schema_version": "signal.sample_evidence/v8",
                    "sample_id": "case-1",
                    "provenance": {
                        "reference": {
                            "name": self.reference_name,
                            "topology": "circular",
                            "sha256": sequence_sha256(self.reference),
                        },
                        "configuration_sha256": "a" * 64,
                    },
                    "reads": [],
                    "coverage": [],
                    "overlaps": [],
                    "locus_differences": [],
                    "variants": variants,
                }
            ),
            encoding="utf-8",
        )
        return path

    @staticmethod
    def variant(
        position: int,
        reference: str,
        alternate: str,
        kind: str,
        eligible_reads: int = 1,
    ) -> dict[str, object]:
        return {
            "position": position,
            "reference": reference,
            "alternate": alternate,
            "kind": kind,
            "support_topology": {
                "reads": 1,
                "eligible_reads": eligible_reads,
                "forward_reads": 1,
                "reverse_reads": 0,
                "eligible_forward_reads": eligible_reads,
                "eligible_reverse_reads": 0,
            },
            "support": [],
        }

    def test_parses_reviewer_snv_iupac_insertion_and_deletion(self) -> None:
        events = parse_reviewer_variants(
            ["2G", "7R", "4.1A", "4.2C", "8DEL", "9DEL"],
            self.reference,
        )
        self.assertEqual(len(events), 4)
        insertion = next(event for event in events if event.kind == "INS")
        deletion = next(event for event in events if event.kind == "DEL")
        iupac = next(event for event in events if event.tokens == ("7R",))
        self.assertEqual(insertion.tokens, ("4.1A", "4.2C"))
        self.assertEqual(insertion.position, 4)
        self.assertEqual(insertion.alternates, frozenset({"CAC"}))
        self.assertEqual(deletion.tokens, ("8DEL", "9DEL"))
        self.assertEqual(deletion.position, 7)
        self.assertEqual(deletion.reference, "GTT")
        self.assertEqual(deletion.alternates, frozenset({"G"}))
        self.assertEqual(iupac.alternates, frozenset({"A"}))

    def test_ignores_sample_variant_without_eligible_support(self) -> None:
        path = self.sample(
            [
                self.variant(2, "A", "G", "SNV", eligible_reads=1),
                self.variant(7, "G", "A", "SNV", eligible_reads=0),
            ]
        )
        variants = load_signal_variants(path, self.reference_name, self.reference)
        self.assertEqual(
            [(variant.position, variant.alternate) for variant in variants],
            [(2, "G")],
        )

    def test_compares_exact_missing_and_extra_variants(self) -> None:
        reviewer = parse_reviewer_variants(["2G", "7A"], self.reference)
        signal = load_signal_variants(
            self.sample(
                [
                    self.variant(2, "A", "G", "SNV"),
                    self.variant(8, "T", "C", "SNV"),
                ]
            ),
            self.reference_name,
            self.reference,
        )
        comparison = compare_profiles(reviewer, signal, self.reference)
        self.assertEqual(comparison.matched, 1)
        self.assertEqual([event.tokens for event in comparison.missing], [("7A",)])
        self.assertEqual(
            [(event.position, event.alternate) for event in comparison.extra],
            [(8, "C")],
        )

    def test_matches_equivalent_indel_representation_separately(self) -> None:
        reference = "CAAAAGTT"
        reviewer = parse_reviewer_variants(["4.1A"], reference)
        signal_path = self.sample([])
        # Build directly because this test uses a different synthetic reference.
        from scripts.validation_corpus.variant_profile import SignalVariant

        signal = (SignalVariant("INS", 5, "A", "AA"),)
        comparison = compare_profiles(reviewer, signal, reference)
        self.assertEqual(comparison.matched, 1)
        self.assertEqual(len(comparison.representation_disagreements), 1)
        self.assertFalse(comparison.missing)
        self.assertFalse(comparison.extra)

    def test_rejects_unsupported_reviewer_notation(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported reviewer variant token"):
            parse_reviewer_variants(["2+G"], self.reference)


if __name__ == "__main__":
    unittest.main()
