# Configuration and Environment

Both `analyze` and `basecall` load exactly one strict TOML file selected by `SIGNAL_CONFIG` or `config/signal.toml`. The binary does not parse `.env`, and environment variables do not override individual scientific values.

Unknown keys, missing sections, duplicate TOML keys, unsupported schema versions, non-finite numbers, invalid ranges, and config sources above 1 MiB are errors. No scientific value falls back silently.

## Schema version 4

| Section | Key | Value | Validation |
|---|---|---:|---|
| root | `schema_version` | `4` | exactly 4 |
| `reference` | `topology` | `circular` | `linear` or `circular` |
| `basecalling` | `secondary_peak_ratio` | `0.33` | finite `(0,1]` |
| `signal_processing` | `window_size_bases` | `10` | integer `5..=10` |
| | `minimum_primary_snr` | `3.0` | finite and positive |
| | `minimum_noisy_windows` | `2` | integer at least `2` |
| `quality_control` | `trim_window_size` | `10` | positive |
| | `best_section_fraction` | `0.10` | finite `(0,1]` |
| | `max_relative_quality_score` | `60` | positive `u8` |
| | `trim_stringency` | `7.0` | finite `[0,9]` |
| | `minimum_retained_bases` | `20` | positive |
| `alignment` | `match_score` | `3` | positive |
| | `mismatch_score` | `-5` | negative |
| | `ambiguous_score` | `0` | integer |
| | `gap_open_score` | `-10` | negative |
| | `gap_extension_score` | `-4` | negative |
| | `minimum_callable_bases` | `20` | positive |
| | `minimum_identity` | `0.80` | finite `(0,1]` |
| `variant_calling` | `max_indel_length` | `50` | `1..=50` |
| | `minimum_peak_height` | `150` | `1..=32767` |
| | `relative_quality_threshold` | `30` | less than `max_relative_quality_score`; comparison is strict `>` |
| | `regions` | `[[16024, 16365], [73, 340], [438, 576]]` | non-empty inclusive 1-based ranges within `1..=50000` |

`basecall` consumes the basecalling, signal-processing, and quality-control settings; it still validates the complete schema and records the complete configuration checksum. Reference, alignment, and variant-calling settings are used only by `analyze`. Signal-processing values control observation-only annotations and never change calls, trim bounds, alignments, or variants. The region list is treated as a union in the supplied reference coordinate system. Region order and overlap do not change eligibility. Compact output v5 records the raw configuration checksum but omits method constants and expanded effective values. Effective values and configuration schema version 4 remain in the strict TOML selected for the run; the local path is omitted.

## `.env`

`.env.example` is a shell-tooling template for `SIGNAL_CONFIG=config/signal.toml` and the operational `SIGNAL_LOG_DIR=logs`. `SIGNAL_LOG_DIR` changes only the append-only log destination; it does not alter scientific settings or their checksum. Local `.env` remains ignored. Shells, IDEs, and containers may export these values; Signal itself never reads dotenv files.
