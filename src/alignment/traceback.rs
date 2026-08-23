//! Traceback decoding and alignment metrics.

use crate::alignment::scoring::{State, is_canonical};
use crate::error::{Error, Result};
use crate::model::alignment::AlignmentMetrics;

#[derive(Debug, Clone)]
pub(crate) struct RawColumn {
    pub(crate) query_base: char,
    pub(crate) reference_base: char,
    pub(crate) query_index: Option<usize>,
    pub(crate) reference_index: Option<usize>,
}

#[derive(Debug, Clone)]
pub(crate) struct RawAlignment {
    pub(crate) score: i64,
    pub(crate) start_reference: usize,
    pub(crate) end_reference: usize,
    pub(crate) gapped_query: String,
    pub(crate) gapped_reference: String,
    pub(crate) operation_runs: String,
    pub(crate) columns: Vec<RawColumn>,
    pub(crate) metrics: AlignmentMetrics,
}

pub(crate) struct TracebackInput<'a> {
    pub(crate) query: &'a [u8],
    pub(crate) reference: &'a [u8],
    pub(crate) trace: &'a [u8],
    pub(crate) row_width: usize,
    pub(crate) endpoint: usize,
    pub(crate) state: State,
    pub(crate) score: i64,
}

pub(crate) fn decode(input: TracebackInput<'_>) -> Result<RawAlignment> {
    let mut row = input.query.len();
    let mut column = input.endpoint;
    let end_reference = column;
    let mut state = input.state;
    let mut reversed = Vec::new();
    while row > 0 {
        let index = row
            .checked_mul(input.row_width)
            .and_then(|value| value.checked_add(column))
            .ok_or_else(|| Error::Alignment("traceback index overflow".into()))?;
        let packed = *input
            .trace
            .get(index)
            .ok_or_else(|| Error::Alignment("traceback index out of bounds".into()))?;
        match state {
            State::Match => {
                if column == 0 {
                    return Err(Error::Alignment(
                        "traceback reached match state at reference column zero".into(),
                    ));
                }
                reversed.push(RawColumn {
                    query_base: char::from(input.query[row - 1]),
                    reference_base: char::from(input.reference[column - 1]),
                    query_index: Some(row - 1),
                    reference_index: Some(column - 1),
                });
                state = State::from_bits(packed & 0b11);
                row -= 1;
                column -= 1;
            }
            State::Insertion => {
                reversed.push(RawColumn {
                    query_base: char::from(input.query[row - 1]),
                    reference_base: '-',
                    query_index: Some(row - 1),
                    reference_index: None,
                });
                state = if packed & 0b100 != 0 {
                    State::Insertion
                } else {
                    State::Match
                };
                row -= 1;
            }
            State::Deletion => {
                if column == 0 {
                    return Err(Error::Alignment(
                        "traceback reached deletion state at reference column zero".into(),
                    ));
                }
                reversed.push(RawColumn {
                    query_base: '-',
                    reference_base: char::from(input.reference[column - 1]),
                    query_index: None,
                    reference_index: Some(column - 1),
                });
                state = if packed & 0b1000 != 0 {
                    State::Deletion
                } else {
                    State::Match
                };
                column -= 1;
            }
        }
    }
    reversed.reverse();
    let gapped_query = reversed.iter().map(|item| item.query_base).collect();
    let gapped_reference = reversed.iter().map(|item| item.reference_base).collect();
    let (operation_runs, gap_opens) = operation_runs(&reversed);
    let mut exact_matches = 0;
    let mut mismatches = 0;
    let mut callable_columns = 0;
    let mut unresolved_query_bases = 0;
    for item in &reversed {
        if item.query_base == 'N' {
            unresolved_query_bases += 1;
        }
        if is_canonical(item.query_base as u8) && is_canonical(item.reference_base as u8) {
            callable_columns += 1;
            if item.query_base == item.reference_base {
                exact_matches += 1;
            } else {
                mismatches += 1;
            }
        }
    }
    let callable_identity = if callable_columns == 0 {
        0.0
    } else {
        exact_matches as f64 / callable_columns as f64
    };
    Ok(RawAlignment {
        score: input.score,
        start_reference: column,
        end_reference,
        gapped_query,
        gapped_reference,
        operation_runs,
        columns: reversed,
        metrics: AlignmentMetrics {
            exact_matches,
            mismatches,
            gap_opens,
            callable_columns,
            callable_identity,
            unresolved_query_bases,
        },
    })
}

fn operation_runs(columns: &[RawColumn]) -> (String, usize) {
    let mut output = String::new();
    let mut previous = None;
    let mut length = 0;
    let mut gap_opens = 0;
    for column in columns {
        let operation = if column.query_base == '-' {
            'D'
        } else if column.reference_base == '-' {
            'I'
        } else {
            'M'
        };
        if previous != Some(operation) {
            if let Some(previous) = previous {
                output.push_str(&format!("{length}{previous}"));
            }
            if matches!(operation, 'I' | 'D') {
                gap_opens += 1;
            }
            previous = Some(operation);
            length = 1;
        } else {
            length += 1;
        }
    }
    if let Some(previous) = previous {
        output.push_str(&format!("{length}{previous}"));
    }
    (output, gap_opens)
}
