//! Strict ABIF directory parsing and exact tag lookup.

use crate::error::{Error, Result};
use crate::trace::reader::Reader;

const DIRECTORY_ENTRY_SIZE: usize = 28;
const ROOT_ENTRY_OFFSET: usize = 6;

/// One validated ABIF directory entry.
#[derive(Debug, Clone)]
pub(crate) struct AbifEntry {
    pub(crate) tag: [u8; 4],
    pub(crate) number: u32,
    pub(crate) element_type: u16,
    pub(crate) element_size: usize,
    pub(crate) element_count: usize,
    pub(crate) data_size: usize,
    pub(crate) data_offset: usize,
    pub(crate) entry_offset: usize,
}

/// Parsed ABIF directory over owned input bytes.
#[derive(Debug, Clone)]
pub(crate) struct AbifFile {
    pub(crate) bytes: Vec<u8>,
    pub(crate) entries: Vec<AbifEntry>,
}

impl AbifFile {
    /// Returns the unique requested entry.
    pub(crate) fn required(&self, tag: &[u8; 4], number: u32) -> Result<&AbifEntry> {
        self.optional(tag, number)?.ok_or_else(|| {
            Error::Abif(format!(
                "missing required tag {}.{number}",
                String::from_utf8_lossy(tag)
            ))
        })
    }

    /// Returns an optional unique entry and rejects duplicates.
    pub(crate) fn optional(&self, tag: &[u8; 4], number: u32) -> Result<Option<&AbifEntry>> {
        let mut matches = self
            .entries
            .iter()
            .filter(|entry| &entry.tag == tag && entry.number == number);
        let first = matches.next();
        if matches.next().is_some() {
            return Err(Error::Abif(format!(
                "duplicate tag {}.{number}",
                String::from_utf8_lossy(tag)
            )));
        }
        Ok(first)
    }

    /// Returns the validated payload, including inline values.
    pub(crate) fn payload(&self, entry: &AbifEntry) -> Result<&[u8]> {
        let offset = if entry.data_size <= 4 {
            entry.entry_offset + 20
        } else {
            entry.data_offset
        };
        Reader::new(&self.bytes).slice(offset, entry.data_size)
    }
}

/// Parses the ABIF header and full root directory.
pub(crate) fn parse(bytes: Vec<u8>) -> Result<AbifFile> {
    let reader = Reader::new(&bytes);
    if reader.slice(0, 4)? != b"ABIF" {
        return Err(Error::Abif("missing ABIF signature".into()));
    }
    let _version = reader.u16(4)?;
    let root = parse_entry(&reader, ROOT_ENTRY_OFFSET)?;
    if &root.tag != b"tdir" {
        return Err(Error::Abif("root directory tag is not tdir".into()));
    }
    if root.element_size != DIRECTORY_ENTRY_SIZE {
        return Err(Error::Abif(format!(
            "root directory entry size is {}; expected {DIRECTORY_ENTRY_SIZE}",
            root.element_size
        )));
    }
    let directory_bytes = root
        .element_count
        .checked_mul(DIRECTORY_ENTRY_SIZE)
        .ok_or_else(|| Error::Abif("root directory size overflow".into()))?;
    reader.slice(root.data_offset, directory_bytes)?;

    let mut entries = Vec::with_capacity(root.element_count);
    for index in 0..root.element_count {
        let delta = index
            .checked_mul(DIRECTORY_ENTRY_SIZE)
            .ok_or_else(|| Error::Abif("directory offset overflow".into()))?;
        let offset = root
            .data_offset
            .checked_add(delta)
            .ok_or_else(|| Error::Abif("directory offset overflow".into()))?;
        let entry = parse_entry(&reader, offset)?;
        let payload_offset = if entry.data_size <= 4 {
            entry.entry_offset + 20
        } else {
            entry.data_offset
        };
        reader.slice(payload_offset, entry.data_size)?;
        entries.push(entry);
    }

    Ok(AbifFile { bytes, entries })
}

fn parse_entry(reader: &Reader<'_>, offset: usize) -> Result<AbifEntry> {
    let tag_bytes = reader.slice(offset, 4)?;
    let tag = [tag_bytes[0], tag_bytes[1], tag_bytes[2], tag_bytes[3]];
    let number = reader.u32(offset + 4)?;
    let element_type = reader.u16(offset + 8)?;
    let element_size = usize::from(reader.u16(offset + 10)?);
    let element_count = usize::try_from(reader.u32(offset + 12)?)
        .map_err(|_| Error::Abif("element count does not fit memory size".into()))?;
    let data_size = usize::try_from(reader.u32(offset + 16)?)
        .map_err(|_| Error::Abif("data size does not fit memory size".into()))?;
    let data_offset = usize::try_from(reader.u32(offset + 20)?)
        .map_err(|_| Error::Abif("data offset does not fit memory size".into()))?;
    if element_size == 0 || element_count == 0 {
        return Err(Error::Abif(format!(
            "tag {}.{number} has zero element size or count",
            String::from_utf8_lossy(&tag)
        )));
    }
    let expected_size = element_size
        .checked_mul(element_count)
        .ok_or_else(|| Error::Abif("element payload size overflow".into()))?;
    if expected_size != data_size {
        return Err(Error::Abif(format!(
            "tag {}.{number} data size {data_size} differs from element size product {expected_size}",
            String::from_utf8_lossy(&tag)
        )));
    }
    Ok(AbifEntry {
        tag,
        number,
        element_type,
        element_size,
        element_count,
        data_size,
        data_offset,
        entry_offset: offset,
    })
}
