"""Tests for shared circular rCRS poly-C read-path geometry."""

from __future__ import annotations

import unittest

from scripts.validation_corpus.polyc_geometry import (
    RCRS_LENGTH,
    TRACTS,
    TractCallSpan,
    call_distance,
    covers_complete_tract,
    path_region,
    read_order_distance,
    reference_neighbor_positions,
    tract_call_span,
)


class PolyCGeometryTests(unittest.TestCase):
    def test_complete_tract_coverage_and_call_span_are_explicit(self) -> None:
        hv2 = TRACTS[0]
        positions = set(range(hv2.start_1based, hv2.end_1based + 1))
        self.assertTrue(covers_complete_tract(positions, hv2))
        positions.remove(310)
        self.assertFalse(covers_complete_tract(positions, hv2))

        call_indices: dict[int, int | None] = {
            position: position - hv2.start_1based + 20
            for position in range(hv2.start_1based, hv2.end_1based + 1)
        }
        call_indices[310] = None
        self.assertEqual(
            tract_call_span(call_indices, hv2, "read-1"),
            TractCallSpan(20, 32),
        )

    def test_hv1_forward_path_stays_after_across_rcrs_origin(self) -> None:
        hv1 = TRACTS[1]
        span = TractCallSpan(100, 109)

        for position, call_index in ((16194, 110), (16569, 485), (1, 486), (253, 738)):
            region = path_region(hv1, position, call_index, span)
            self.assertEqual(region, "after")
            reference_distance = read_order_distance(hv1, "forward", position, region)
            call_index_distance = call_distance(span, call_index, region)
            if reference_distance is None or call_index_distance is None:
                self.fail("call-backed post-tract distances must be present")
            self.assertGreater(reference_distance, 0)
            self.assertGreater(call_index_distance, 0)

        self.assertEqual(
            read_order_distance(hv1, "forward", 1, "after"),
            RCRS_LENGTH - hv1.end_1based + 1,
        )
        self.assertEqual(
            read_order_distance(hv1, "forward", 253, "after"),
            RCRS_LENGTH - hv1.end_1based + 253,
        )

    def test_hv2_reverse_path_stays_after_across_rcrs_origin(self) -> None:
        hv2 = TRACTS[0]
        span = TractCallSpan(200, 212)

        for position, call_index in ((302, 213), (1, 514), (16569, 515), (16197, 887)):
            region = path_region(hv2, position, call_index, span)
            self.assertEqual(region, "after")
            reference_distance = read_order_distance(hv2, "reverse", position, region)
            call_index_distance = call_distance(span, call_index, region)
            if reference_distance is None or call_index_distance is None:
                self.fail("call-backed post-tract distances must be present")
            self.assertGreater(reference_distance, 0)
            self.assertGreater(call_index_distance, 0)

    def test_before_and_after_are_call_order_properties(self) -> None:
        hv2 = TRACTS[0]
        span = TractCallSpan(20, 32)

        self.assertEqual(path_region(hv2, 302, 19, span), "before")
        self.assertEqual(path_region(hv2, 302, 33, span), "after")
        self.assertEqual(
            read_order_distance(hv2, "forward", 302, "before"),
            -1,
        )
        self.assertEqual(
            read_order_distance(hv2, "reverse", 302, "after"),
            1,
        )

    def test_non_call_backed_outside_tract_observation_is_unresolved(self) -> None:
        hv2 = TRACTS[0]
        span = TractCallSpan(20, 32)
        region = path_region(hv2, 316, None, span)
        self.assertEqual(region, "unresolved")
        self.assertIsNone(read_order_distance(hv2, "forward", 316, region))
        self.assertIsNone(call_distance(span, None, region))

    def test_reference_neighbors_wrap_rcrs_origin(self) -> None:
        self.assertEqual(
            reference_neighbor_positions("forward", 1),
            (RCRS_LENGTH, 2),
        )
        self.assertEqual(
            reference_neighbor_positions("forward", RCRS_LENGTH),
            (RCRS_LENGTH - 1, 1),
        )
        self.assertEqual(
            reference_neighbor_positions("reverse", 1),
            (2, RCRS_LENGTH),
        )
        self.assertEqual(
            reference_neighbor_positions("reverse", RCRS_LENGTH),
            (1, RCRS_LENGTH - 1),
        )


if __name__ == "__main__":
    unittest.main()
