"""Tests for reviewer-derived sample variant-profile evaluation."""

from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.validation_corpus.model import (
    REVIEWER_VARIANT_GROUND_TRUTH_SCHEMA_VERSION,
    VARIANT_PROFILE_EVALUATION_SCHEMA_VERSION,
)
from scripts.validation_corpus.reviewer_variants import (
    extract_ground_truth,
    load_ground_truth,
    parse_reviewer_variants,
)
from scripts.validation_corpus.variant_profile_evaluation import (
    compare_variants,
    load_signal_variants,
    publish_evaluation,
)


class ReviewerVariantEvaluationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="signal-reviewer-variant-test-"
        )
        self.root = Path(self.temporary.name)
        self.reference = self.root / "reference.fasta"
        self.reference_sequence = "CAAAAGTCCG"
        self.reference.write_text(
            f">rCRS\n{self.reference_sequence}\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_ground_truth(
        self,
        variants_raw: str,
        *,
        case_id: str = "AB0001",
    ) -> Path:
        path = self.root / "ground-truth.json"
        path.write_text(
            json.dumps(
                {
                    "schema_version": REVIEWER_VARIANT_GROUND_TRUTH_SCHEMA_VERSION,
                    "truth_status": "reviewer_derived_proxy",
                    "description": "test",
                    "source": {
                        "file_name": "review.tsv",
                        "sha256": "a" * 64,
                        "sample_id_column": "Sample ID",
                        "variant_column": "Variants (Sequencher)",
                        "analyzed_range_column": "Analyzed Range (Sequencher)",
                        "batches": ["batch"],
                    },
                    "record_count": 1,
                    "records": [
                        {
                            "source_row": 2,
                            "sample_id": f"LN_26_{case_id}",
                            "validation_case_id": case_id,
                            "batch": "batch",
                            "analyzed_range": "FULL REGION",
                            "variants_raw": variants_raw,
                            "variants": variants_raw.split(),
                        }
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return path

    def write_sample(
        self,
        variants: list[dict[str, object]],
        *,
        case_id: str = "AB0001",
        configuration_sha256: str = "b" * 64,
    ) -> Path:
        result = self.root / "results" / case_id / f"{case_id}.json"
        result.parent.mkdir(parents=True, exist_ok=True)
        result.write_text(
            json.dumps(
                {
                    "schema_version": "signal.sample_evidence/v8",
                    "sample_id": case_id,
                    "provenance": {
                        "reference": {
                            "name": "rCRS",
                            "topology": "circular",
                            "sha256": hashlib.sha256(
                                self.reference_sequence.encode()
                            ).hexdigest(),
                        },
                        "configuration_sha256": configuration_sha256,
                    },
                    "reads": [],
                    "coverage": [],
                    "overlaps": [],
                    "locus_differences": [],
                    "variants": variants,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return result

    @staticmethod
    def signal_variant(
        position: int,
        reference: str,
        alternate: str,
        kind: str,
        *,
        eligible_reads: int = 1,
    ) -> dict[str, object]:
        return {
            "position": position,
            "reference": reference,
            "alternate": alternate,
            "kind": kind,
            "support_topology": {
                "reads": max(1, eligible_reads),
                "eligible_reads": eligible_reads,
                "forward_reads": 1,
                "reverse_reads": 0,
                "eligible_forward_reads": int(eligible_reads > 0),
                "eligible_reverse_reads": 0,
            },
            "support": [],
        }

    def test_extract_preserves_reviewer_notation_verbatim(self) -> None:
        source = self.root / "review.tsv"
        with source.open("w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(
                target,
                fieldnames=[
                    "Sample ID",
                    "Batch",
                    "Analyzed Range (Sequencher)",
                    "Variants (Sequencher)",
                ],
                delimiter="\t",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerow(
                {
                    "Sample ID": "LN_26_AB0001",
                    "Batch": "batch",
                    "Analyzed Range (Sequencher)": "FULL REGION",
                    "Variants (Sequencher)": "3.1C 5DEL 7A",
                }
            )

        output = self.root / "reviewer.json"
        extract_ground_truth(source, output)
        artifact = load_ground_truth(output)
        record = artifact["records"][0]

        self.assertEqual(record["variants_raw"], "3.1C 5DEL 7A")
        self.assertEqual(record["variants"], ["3.1C", "5DEL", "7A"])

    def test_reviewer_notation_maps_to_insertion_deletion_and_snv(self) -> None:
        variants = parse_reviewer_variants(
            ["3.1C", "5DEL", "7A"],
            self.reference_sequence,
        )

        insertion = next(variant for variant in variants if variant.kind == "INS")
        deletion = next(variant for variant in variants if variant.kind == "DEL")
        snv = next(variant for variant in variants if variant.kind == "SNV")

        self.assertEqual(insertion.tokens, ("3.1C",))
        self.assertEqual(insertion.position, 3)
        self.assertEqual(insertion.reference, "A")
        self.assertEqual(insertion.alternates, frozenset({"AC"}))

        self.assertEqual(deletion.tokens, ("5DEL",))
        self.assertEqual(deletion.position, 4)
        self.assertEqual(deletion.reference, "AA")
        self.assertEqual(deletion.alternates, frozenset({"A"}))

        self.assertEqual(snv.tokens, ("7A",))
        self.assertEqual(snv.position, 7)
        self.assertEqual(snv.reference, "T")
        self.assertEqual(snv.alternates, frozenset({"A"}))

    def test_multiple_insertion_tokens_form_one_ordered_insertion(self) -> None:
        variants = parse_reviewer_variants(
            ["3.1C", "3.2G"],
            self.reference_sequence,
        )

        self.assertEqual(len(variants), 1)
        self.assertEqual(variants[0].kind, "INS")
        self.assertEqual(variants[0].tokens, ("3.1C", "3.2G"))
        self.assertEqual(variants[0].alternates, frozenset({"ACG"}))

    def test_consecutive_deletions_form_one_sequence_event(self) -> None:
        variants = parse_reviewer_variants(
            ["4DEL", "5DEL"],
            self.reference_sequence,
        )

        self.assertEqual(len(variants), 1)
        self.assertEqual(variants[0].kind, "DEL")
        self.assertEqual(variants[0].tokens, ("4DEL", "5DEL"))
        self.assertEqual(variants[0].position, 3)
        self.assertEqual(variants[0].reference, "AAA")
        self.assertEqual(variants[0].alternates, frozenset({"A"}))

    def test_iupac_snv_accepts_each_non_reference_component(self) -> None:
        variants = parse_reviewer_variants(["7W"], self.reference_sequence)

        self.assertEqual(len(variants), 1)
        self.assertEqual(variants[0].reference, "T")
        self.assertEqual(variants[0].alternates, frozenset({"A"}))

    def test_signal_evaluation_uses_only_eligible_sample_variants(self) -> None:
        path = self.write_sample(
            [
                self.signal_variant(7, "T", "A", "SNV", eligible_reads=1),
                self.signal_variant(8, "C", "G", "SNV", eligible_reads=0),
            ]
        )

        variants, configuration_sha256 = load_signal_variants(
            path,
            "AB0001",
            "rCRS",
            self.reference_sequence,
        )

        self.assertEqual(configuration_sha256, "b" * 64)
        self.assertEqual(len(variants), 1)
        self.assertEqual(variants[0].position, 7)
        self.assertEqual(variants[0].alternate, "A")

    def test_exact_snv_match_has_no_difference(self) -> None:
        reviewer = parse_reviewer_variants(["7A"], self.reference_sequence)
        sample_path = self.write_sample(
            [self.signal_variant(7, "T", "A", "SNV")]
        )
        signal, _ = load_signal_variants(
            sample_path,
            "AB0001",
            "rCRS",
            self.reference_sequence,
        )

        matches, missing, extra = compare_variants(
            reviewer,
            signal,
            self.reference_sequence,
        )

        self.assertEqual(matches, [(0, 0, False)])
        self.assertEqual(missing, [])
        self.assertEqual(extra, [])

    def test_repeat_shifted_insertion_is_representation_disagreement_not_error(
        self,
    ) -> None:
        reviewer = parse_reviewer_variants(["3.1A"], self.reference_sequence)
        sample_path = self.write_sample(
            [self.signal_variant(4, "A", "AA", "INS")]
        )
        signal, _ = load_signal_variants(
            sample_path,
            "AB0001",
            "rCRS",
            self.reference_sequence,
        )

        matches, missing, extra = compare_variants(
            reviewer,
            signal,
            self.reference_sequence,
        )

        self.assertEqual(matches, [(0, 0, True)])
        self.assertEqual(missing, [])
        self.assertEqual(extra, [])

    def test_representation_equivalence_is_matched_but_not_exact_profile(self) -> None:
        truth = self.write_ground_truth("3.1A")
        self.write_sample([self.signal_variant(4, "A", "AA", "INS")])
        output = self.root / "evaluation"

        publish_evaluation(
            truth,
            self.root / "results",
            self.reference,
            output,
        )

        index = json.loads((output / "index.json").read_text(encoding="utf-8"))
        summary = index["summary"]
        self.assertEqual(summary["proxy_true_positive_variants"], 1)
        self.assertEqual(summary["proxy_false_positive_variants"], 0)
        self.assertEqual(summary["proxy_false_negative_variants"], 0)
        self.assertEqual(summary["representation_disagreements"], 1)
        self.assertEqual(summary["exact_profiles"], 0)

    def test_reports_false_positive_and_false_negative_proxy_counts(self) -> None:
        truth = self.write_ground_truth("7A 9T")
        self.write_sample(
            [
                self.signal_variant(7, "T", "A", "SNV"),
                self.signal_variant(8, "C", "G", "SNV"),
            ]
        )
        output = self.root / "evaluation"

        publish_evaluation(
            truth,
            self.root / "results",
            self.reference,
            output,
        )

        index = json.loads((output / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(
            index["schema_version"],
            VARIANT_PROFILE_EVALUATION_SCHEMA_VERSION,
        )
        self.assertEqual(index["configuration_sha256"], "b" * 64)
        with (output / "samples.csv").open(newline="", encoding="utf-8") as source:
            sample_rows = list(csv.DictReader(source))
        self.assertEqual(len(sample_rows), 1)
        self.assertEqual(
            sample_rows[0]["signal_result_sha256"],
            hashlib.sha256(
                (self.root / "results/AB0001/AB0001.json").read_bytes()
            ).hexdigest(),
        )

        summary = index["summary"]
        self.assertEqual(summary["proxy_true_positive_variants"], 1)
        self.assertEqual(summary["proxy_false_positive_variants"], 1)
        self.assertEqual(summary["proxy_false_negative_variants"], 1)
        self.assertEqual(summary["exact_profiles"], 0)
        self.assertEqual(summary["proxy_precision"], 0.5)
        self.assertEqual(summary["proxy_recall"], 0.5)
        self.assertIsNone(summary["true_negatives"])
        self.assertIsNone(summary["specificity"])

    def test_mixed_sample_configurations_are_rejected(self) -> None:
        truth = self.root / "ground-truth.json"
        truth.write_text(
            json.dumps(
                {
                    "schema_version": REVIEWER_VARIANT_GROUND_TRUTH_SCHEMA_VERSION,
                    "truth_status": "reviewer_derived_proxy",
                    "description": "test",
                    "source": {
                        "file_name": "review.tsv",
                        "sha256": "a" * 64,
                        "sample_id_column": "Sample ID",
                        "variant_column": "Variants (Sequencher)",
                        "analyzed_range_column": "Analyzed Range (Sequencher)",
                        "batches": ["batch"],
                    },
                    "record_count": 2,
                    "records": [
                        {
                            "source_row": 2,
                            "sample_id": "LN_26_AB0001",
                            "validation_case_id": "AB0001",
                            "batch": "batch",
                            "analyzed_range": "FULL REGION",
                            "variants_raw": "7A",
                            "variants": ["7A"],
                        },
                        {
                            "source_row": 3,
                            "sample_id": "LN_26_AB0002",
                            "validation_case_id": "AB0002",
                            "batch": "batch",
                            "analyzed_range": "FULL REGION",
                            "variants_raw": "7A",
                            "variants": ["7A"],
                        },
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        self.write_sample(
            [self.signal_variant(7, "T", "A", "SNV")],
            case_id="AB0001",
            configuration_sha256="b" * 64,
        )
        self.write_sample(
            [self.signal_variant(7, "T", "A", "SNV")],
            case_id="AB0002",
            configuration_sha256="c" * 64,
        )

        with self.assertRaisesRegex(
            ValueError,
            "do not share one configuration_sha256",
        ):
            publish_evaluation(
                truth,
                self.root / "results",
                self.reference,
                self.root / "evaluation",
            )

    def test_output_is_no_overwrite(self) -> None:
        truth = self.write_ground_truth("7A")
        self.write_sample([self.signal_variant(7, "T", "A", "SNV")])
        output = self.root / "evaluation"

        publish_evaluation(
            truth,
            self.root / "results",
            self.reference,
            output,
        )

        with self.assertRaisesRegex(ValueError, "already exists"):
            publish_evaluation(
                truth,
                self.root / "results",
                self.reference,
                output,
            )


if __name__ == "__main__":
    unittest.main()
