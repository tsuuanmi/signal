from __future__ import annotations

import unittest
from pathlib import Path

from scripts.validation_corpus.phase_interpretation_dataset import PartitionPlan
from scripts.validation_corpus.research_model import ResearchCase, ResearchCorpus
from scripts.validation_corpus.variant_phase_context import (
    build_rows,
    event_footprint,
    parse_event,
    selected_event,
)


def difference(
    *,
    case_id: str,
    kind: str,
    reviewer_events: str = "",
    signal_events: str = "",
) -> dict[str, str]:
    return {
        "sample_id": f"LN_26_{case_id}",
        "validation_case_id": case_id,
        "difference": kind,
        "reviewer_tokens": "",
        "reviewer_positions": "",
        "reviewer_events": reviewer_events,
        "signal_positions": "",
        "signal_events": signal_events,
        "reviewer_event_count": "1" if reviewer_events else "0",
        "signal_event_count": "1" if signal_events else "0",
    }


def case(case_id: str, holdout_group: str, fit: bool) -> ResearchCase:
    return ResearchCase(
        metadata={
            "validation_case_id": case_id,
            "source_group_id": f"source-{case_id}",
            "specimen_group_id": None,
            "holdout_group": holdout_group,
            "include_in_threshold_fit": fit,
        },
        measurement_file=Path(f"{case_id}.jsonl"),
        loci=1,
        reads={},
    )


class VariantPhaseContextTest(unittest.TestCase):
    def test_parse_event_preserves_normalized_event(self) -> None:
        event = parse_event("DEL:512:AGC>A")

        self.assertEqual(event.kind, "DEL")
        self.assertEqual(event.position, 512)
        self.assertEqual(event.reference, "AGC")
        self.assertEqual(event.alternate, "A")

    def test_event_footprint_uses_reference_span_and_insertion_boundary(self) -> None:
        deletion = parse_event("DEL:512:AGC>A")
        insertion = parse_event("INS:310:A>AC")

        self.assertEqual(event_footprint(deletion, 16569), (512, 514, None))
        self.assertEqual(event_footprint(insertion, 16569), (310, 310, 310))

    def test_selected_event_uses_biological_side_of_difference(self) -> None:
        missing, _ = selected_event(
            difference(
                case_id="AB0001",
                kind="missing",
                reviewer_events="SNV:73:A>G",
            )
        )
        extra, _ = selected_event(
            difference(
                case_id="AB0001",
                kind="extra",
                signal_events="SNV:263:A>G",
            )
        )

        self.assertEqual((missing.position, missing.alternate), (73, "G"))
        self.assertEqual((extra.position, extra.alternate), (263, "G"))

    def test_build_rows_excludes_representation_and_holdout_details(self) -> None:
        corpus = ResearchCorpus(
            index_path=Path("index.json"),
            signal_version="test",
            manifest_sha256="a" * 64,
            reference_sha256="b" * 64,
            configuration_sha256="c" * 64,
            cases=[
                case("AB0001", "development", True),
                case("AB0002", "holdout", True),
            ],
        )
        rows = [
            difference(
                case_id="AB0001",
                kind="extra",
                signal_events="SNV:100:A>G",
            ),
            difference(
                case_id="AB0001",
                kind="representation",
                reviewer_events="DEL:100:AA>A",
                signal_events="DEL:101:AA>A",
            ),
            difference(
                case_id="AB0002",
                kind="missing",
                reviewer_events="SNV:200:C>T",
            ),
        ]
        plan = PartitionPlan(
            development=("development",),
            holdout=("holdout",),
        )

        detailed, observations, windows, candidates, readiness = build_rows(
            corpus,
            rows,
            16569,
            plan,
            {},
            [],
            {},
            {},
            (),
        )

        self.assertEqual(len(detailed), 1)
        self.assertEqual(detailed[0]["validation_case_id"], "AB0001")
        self.assertEqual(detailed[0]["difference"], "extra")
        self.assertEqual(observations, [])
        self.assertEqual(windows, [])
        self.assertEqual(candidates, [])

        readiness_by_key = {
            (row["partition"], row["difference"]): row for row in readiness
        }
        self.assertEqual(
            readiness_by_key[("development", "extra")]["biological_differences"],
            1,
        )
        self.assertEqual(
            readiness_by_key[("holdout", "missing")]["biological_differences"],
            1,
        )
        self.assertEqual(
            readiness_by_key[("holdout", "missing")]["fit_eligible_differences"],
            0,
        )


if __name__ == "__main__":
    unittest.main()
