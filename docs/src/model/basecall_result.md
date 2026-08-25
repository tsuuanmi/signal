# `src/model/basecall_result.rs`

## Purpose

Defines the serializable `signal.basecalls/v1` reference-free result contract.

## Responsibilities

- Represent software/input/configuration provenance.
- Represent complete primary, ambiguity, and retained sequences with call count
  and trim bounds.
- Reuse shared interval and merged signal-quality result types.
- Expose unresolved-primary and multi-channel-unresolved counts, plus vendor
  disagreement counts when optional vendor calls are available.

## Non-responsibilities

No scientific computation, filesystem access, serialization logic, reference,
alignment, variant, per-call peak, vendor, or calibrated-quality output.

## Dependencies

- `model::result` for shared input, interval, and signal-quality result records.
- `serde` for deterministic serialization.

## Tests

`tests/basecall.rs` and the basecall schema validator exercise the contract.
