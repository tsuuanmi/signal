# Implemented Rust Source Layout

Every listed `.rs` file is implemented and has an exact same-path `.md` manual under `docs/src/`.

```text
src/
├── lib.rs
├── main.rs
├── cli/mod.rs
├── error/mod.rs
├── logger.rs
├── checksum.rs
├── config/{mod,defaults,types,load}.rs
├── model/{mod,coordinate,nucleotide,trace,basecalls,signal,quality,reference,alignment,variant,result}.rs
├── trace/{mod,reader,abif,decode}.rs
├── reference/{mod,fasta}.rs
├── basecalling/{mod,iupac,peak,call}.rs
├── signal_processing/{mod,features,regions}.rs
├── quality_control/{mod,penalty,quality,trim}.rs
├── alignment/{mod,scoring,gotoh,traceback,orient}.rs
├── variant_calling/{mod,mapping,extract,normalize,filter}.rs
├── report/{mod,json,variant,atomic}.rs
└── pipeline/{mod,input,analyze}.rs
```

## Dependency direction

```text
main -> cli -> lib dispatcher -> pipeline
pipeline -> config + trace + reference + basecalling + signal_processing + quality_control
pipeline -> alignment + variant_calling + report + logger
all stages -> model + error
model -> no filesystem, CLI, or algorithm module
report -> completed models; no scientific computation
```

## File ownership

- `reader`/`abif` parse generic binary structure; `decode` knows required scientific tags.
- `checksum` provides the shared stable SHA-256 identity used by config, trace, and reference loading.
- `peak` selects evidence; `call` classifies it; `iupac` maps ambiguity.
- `features` estimates rolling sample-domain SNR; `regions` merges candidate-noisy intervals without changing calls.
- `penalty`, `quality`, and `trim` keep distinct QC responsibilities.
- `gotoh` computes DP; `traceback` reconstructs rows; `orient` applies strand/topology policy; `scoring` centralizes arithmetic.
- `extract` finds events; `mapping` binds original calls to aligned reference positions; `normalize` defines canonical alleles/positions; `filter` applies configured region and supporting-signal eligibility.
- `logger` appends timestamped per-trace operational records without entering scientific stages or JSON.
- `json` assembles core results; `variant` joins mapped calls to peaks/quality; `atomic` publishes `results/<trace-stem>.json`.
- `input` loads one validated use case; `analyze` sequences stages.

VCF has no source file or compatibility path in the MVP.
