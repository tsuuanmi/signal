# Architecture

- [System overview](overview.md): module boundaries, data flow, dependency direction, resource bounds, and publication model.
- [System invariants](invariants.md): cross-cutting truths every module must preserve.
- [Architecture decisions](../adr/README.md): accepted/proposed/superseded decisions.
- [Source manuals](../src/README.md): same-relative-path implementation ownership for `src/**/*.rs`.

Architecture describes where responsibilities belong. Detailed scientific
algorithms live in method documentation; implementation-level ownership lives
with the mirrored source manuals rather than a duplicated source-layout note.
