# Configuration and Environment

Signal loads exactly one strict TOML file selected by `SIGNAL_CONFIG` or `config/signal.toml`. The binary does not parse `.env`, and environment variables do not override individual scientific values.

Unknown keys, missing sections, duplicate TOML keys, unsupported schema versions, non-finite numbers, invalid ranges, and config sources above 1 MiB are errors. No scientific value falls back silently.

## Schema version 1

| Section | Key | Value | Validation |
|---|---|---:|---|
| root | `schema_version` | `1` | exactly 1 |
| `reference` | `topology` | `circular` | `linear` or `circular` |
| `basecalling` | `secondary_peak_ratio` | `0.33` | finite `(0,1]` |
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

The compact JSON records the raw config checksum and versioned method IDs. Effective values remain in the strict TOML selected for the run; the local path is omitted.

## `.env`

`.env.example` is a shell-tooling template containing only `SIGNAL_CONFIG=config/signal.toml`. Local `.env` remains ignored. Shells, IDEs, and containers may export it; Signal itself never reads dotenv files.
