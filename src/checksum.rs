//! Stable SHA-256 identities for validated input bytes.

use sha2::{Digest, Sha256};

/// Returns a lowercase hexadecimal SHA-256 digest.
pub(crate) fn hex_sha256(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hashes_bytes_deterministically() {
        assert_eq!(
            hex_sha256(b"signal"),
            "d041924c15885af6d06530a425c6dbffc80520150c4dd264f40b4364b12421a8"
        );
    }
}
