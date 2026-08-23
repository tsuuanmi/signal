# `src/trace/abif.rs`

## Purpose

Parses the ABIF header and root directory and provides exact tag lookup.

## Responsibilities

- Verify the `ABIF` signature and header version.
- Parse the root `tdir` directory and every directory entry with bounds checking.
- Provide `required`/`optional` tag lookup and validated payload access.

## Non-responsibilities

No tag semantics or chromatogram construction.

## Key types and functions

- `AbifEntry`: tag, number, element type/size/count, data size/offset, and entry
  offset.
- `AbifFile`: owned bytes and parsed entries.
- `parse(bytes) -> Result<AbifFile>`: parses the header and full root directory.
- `AbifFile::required`/`optional`: exact tag lookup, rejecting duplicates.
- `AbifFile::payload(entry) -> Result<&[u8]>`: validated payload, including
  inline values.

## Invariants and errors

- The signature must be `ABIF`; otherwise `Error::Abif`.
- The root directory tag must be `tdir` with the expected entry size.
- Every entry must have non-zero element size and count, and its data size must
  equal the element-size product.
- All offsets and lengths are checked before slicing; malformed input returns
  `Error::Abif`, never a panic.
- Duplicate tags return `Error::Abif`.

## Dependencies

- `reader` for `Reader`.
- `error` for `Error`/`Result`.

## Biological semantics

None; this is the ABIF container format layer.

## Tests

No dedicated unit tests; behavior is exercised through `decode` and the
integration tests.

## Status

Implemented.
