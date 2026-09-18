# Profile-Aware Alignment

## 13. Priority 0: Profile-to-Reference Alignment

Signal currently aligns:

```text
retained primary sequence
```

against:

```text
reference sequence
```

Future Signal should support:

```text
evidence profile
```

against:

```text
reference sequence
```

The current Gotoh framework can remain.

Only the substitution score changes.

---

## 14. Profile-to-Base Scoring

Current canonical scoring resembles:

```text
query A vs reference A -> match_score
query A vs reference G -> mismatch_score
```

With an evidence profile:

```text
A = 0.70
C = 0.05
G = 0.20
T = 0.05
```

against reference `A`, score could be:

```text
0.70 * match(A,A)
+ 0.05 * mismatch(C,A)
+ 0.20 * mismatch(G,A)
+ 0.05 * mismatch(T,A)
```

More generally:

```text
score(profile_i, reference_base) =
    Σ_b weight_i[b] × base_score(b, reference_base)
```

This is similar in spirit to Tracy's profile-aware alignment.

---

## 15. Suggested Interface

Possible abstraction:

```rust
pub trait AlignmentSymbol {
    fn substitution_score(
        &self,
        reference: Nucleotide,
        scoring: &AlignmentScoring,
    ) -> i32;
}
```

or explicit profile scoring:

```rust
pub fn profile_reference_score(
    profile: &EvidenceProfile,
    reference: Nucleotide,
    scoring: &AlignmentScoring,
) -> i32
```

The dynamic-programming engine should not need to understand chromatograms.

It should only consume a deterministic score.

This keeps architecture clean:

```text
signal interpretation
       |
       v
EvidenceProfile
       |
       v
alignment scoring adapter
       |
       v
generic Gotoh
```

---

## 16. Why Profile Alignment Helps mtDNA

Profile-aware alignment is particularly useful for:

* noisy read ends;
* control-region poly-C sequence;
* indel boundaries;
* compressed peaks;
* mixed-base candidates;
* forward/reverse disagreement;
* positions where the primary call is wrong but the correct nucleotide has substantial secondary evidence.

Example:

```text
reference = G

trace evidence:
A = 0.52
G = 0.45
C = 0.02
T = 0.01
```

Primary-only alignment sees:

```text
A vs G
```

and applies a full mismatch penalty.

Profile alignment sees:

```text
strong competing G evidence
```

and can score the position less severely.

This may improve:

```text
orientation selection
alignment placement
gap placement
local indel interpretation
```

---

## 17. Profile Alignment Must Not Hide Poor Signal

A richer profile must not allow poor data to appear artificially compatible with every reference.

For example:

```text
A = 0.25
C = 0.25
G = 0.25
T = 0.25
```

should not become a moderately good match to every base.

Signal should retain an explicit unresolved or uncertainty component.

Possible design:

```rust
pub struct EvidenceProfile {
    pub weights: [f64; 4],
    pub unresolved_weight: f64,
}
```

Then scoring may penalize unresolved evidence separately.

Possible configuration:

```toml
[alignment.profile]

unresolved_score = -1

minimum_informative_weight = 0.60
```

Exact semantics require validation.

---

## 18. Priority 0: Profile-to-Profile Alignment

Tracy also demonstrates the value of comparing two chromatograms as profiles.

This is especially relevant for:

```text
forward read
vs
reverse read
```

from the same amplicon.

Instead of:

```text
forward primary sequence
        vs
reverse primary sequence
```

Signal can eventually compare:

```text
forward evidence profile
        vs
reverse-complement evidence profile
```

---

## 19. Profile-to-Profile Score

Conceptually:

```text
score(profile1, profile2) =
    Σ_i Σ_j
        weight1[i]
        × weight2[j]
        × base_score(i,j)
```

Example:

```text
Forward:
A 0.55
G 0.42

Reverse:
A 0.51
G 0.46
```

Primary sequences may disagree depending on tiny signal differences.

Profile comparison shows that both reads contain nearly identical biological evidence.

This is a much better basis for detecting reproducible mixed signal.

---

## 20. Bidirectional Evidence Interpretation

Consider four cases.

### Case 1 — clean agreement

```text
Forward:
A 0.95
G 0.03

Reverse:
A 0.92
G 0.05
```

Interpretation:

```text
strong bidirectional A support
```

---

### Case 2 — primary disagreement but shared ambiguity

```text
Forward:
A 0.51
G 0.47

Reverse:
A 0.48
G 0.50
```

Primary-only:

```text
Forward -> A
Reverse -> G
```

Profile-aware interpretation:

```text
both support reproducible A/G mixed evidence
```

This should not immediately be labeled heteroplasmy.

Suggested classification:

```text
bidirectionally_reproduced_mixed_signal
```

---

### Case 3 — one noisy read

```text
Forward:
A 0.95
G 0.03

Reverse:
A 0.40
G 0.35
C 0.15
T 0.10
```

Interpretation:

```text
forward strong
reverse low confidence
```

Consensus may still be A while retaining reverse-read uncertainty.

---

### Case 4 — true conflict

```text
Forward:
A 0.95

Reverse:
G 0.94
```

Interpretation:

```text
discordant independent observations
manual review required
```

A majority vote would not solve this safely.

---
