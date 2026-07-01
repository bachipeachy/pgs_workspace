# PGS Invariant Core (v0)

The behavioral baseline of correctness for the Protocol-Governed Systems authoring pipeline —
expressed as **invariants**, system-wide.

This is the "golden contract." It is deliberately **not** a golden copy of outputs. A language-based
golden (frozen artifact text) explodes on any wording or model change; a behavior-based golden
survives model swaps and surface expansion. So this document freezes the **definition of
correctness**, not the prose that happens to satisfy it.

## What this is — and is not

| This IS | This is NOT |
|---|---|
| System-wide invariants, at the level of *behavior* | Blockchain-specific, or specific to any one domain |
| The contract every CR under every seed must satisfy | A frozen set of artifacts, register rows, or FQDNs |
| Gate outcomes, deterministic mappings, structural properties | A run trace, or any particular run |
| Versioned by this contract (v0) over the compiler + engine gates | Bound to a seed hash (that binds a per-run *instance*, below) |

A **run instance** (a concrete CR authored from a concrete seed) records its seed-specific values —
belief count, gap count, the FQDNs reused/authored — in its own dossier and handoffs. The instance
*conforms to* this core; it does not *define* it. Nothing seed-specific belongs in this document.

## The foundational partition

Correctness rests on a three-way, non-overlapping ownership of knowledge. Every invariant below is a
consequence of it.

> **Human → Authority. Compiler → Deterministic knowledge. Worker → Transformation & judgment.**
> No overlap. The compiler derives everything derivable; the human provides everything that is not;
> the worker transforms between them and disposes evidence.

Two boundaries follow (field manual / ledger SPP.0a–0b):
- **Boundary 1 — Knowledge Partition:** you cannot compute *meaning* from *structure*. Semantic
  relevance is the worker's, never the platform's.
- **Boundary 2 — Authority/Authorship:** you cannot compute *authority* from *meaning*. A human-owned
  field is supplied by a human or the pipeline stops — never invented.

---

## Cross-cutting invariants (hold at every stage, for every CR)

- **CI-1 · Admissibility.** A stage output that violates its register schema (unknown column, wrong
  enum, business/​code column typing) is **rejected at the mutation boundary** before the engine runs.
  *(ingress validator)*
- **CI-2 · Determinism.** Identical inputs produce an identical `prompt_hash` (and identical trace).
  Re-export is byte-stable. *(prompt_hash; export)*
- **CI-3 · Provenance completeness.** Every emitted register row carries traceability; a conforming
  stage is **governed 100% · audit 100%**. No orphan rows. *(governed/audit coverage)*
- **CI-4 · Transport parity.** A clean artifact scores **identically** across the three transports
  (Automated / Guided / Offline). Process-convergence never outranks artifact-correctness; the
  observability difference lives in the Worker Protocol Trace, not the quality score. *(rating();
  trifecta selftest)*
- **CI-5 · No fabrication.** A referenced protocol identifier either exists in the snapshot (cited as
  baseline) or is declared as new in this CR. A fabricated FQDN is a hard defect. *(identity /
  E_FABRICATION)*
- **CI-6 · Authoring Completeness (Boundary 2).** Every human-owned, non-derivable field (declared in
  `authoring_fields.json`) is supplied by a human **before the first stage that depends on it**. A
  missing field halts with `AUTHORING_INCOMPLETE`; the platform states what is missing and why, and
  never manufactures it. *(authoring-completeness gate)*
- **CI-7 · Single-Producer / Semantic Derivation.** Every deterministic fact has exactly one
  authoritative producer (the compiler); consumers interpret it, never re-derive it. No two consumers
  can disagree about a deterministic fact because neither computed it. *(compiler authority)*
- **CI-8 · Fail-hard, no silent skip.** A missing artifact, an undisposed neighbourhood element, an
  unresolved required field → an explicit halt with a named reason. Never a silent default or fallback.

---

## Per-stage behavioral invariants

Each stage's *contract* — what must be true of its output regardless of wording, seed, or model.

- **S1 · Change Request.** Every register row traces to a seed section; no belief promoted to fact; no
  design invented. The CR is capture, not authorship.
- **S2 · Domain Model.** **Disposition Completeness = 100%** — every element of the Computed Semantic
  Neighborhood is disposed (RELEVANT / EXCLUDED / NOT_APPLICABLE / GAP / REPRESENTED); none undisposed.
  Every System Belief is verified against the snapshot (the **belief spine** = the count of S1
  beliefs). *(disposition gate; belief spine)*
- **S3 · Analysis.** **Belief preservation** — every S2 belief is re-verified (CONFIRMED / OVERTURNED);
  an OVERTURNED belief carries grounded evidence; every belief-derived CRITICAL gap is decided
  (AUTHOR_NEW / EXTEND); a REUSE cites an existing baseline FQDN. Judgment carries forward, never
  silently drops. *(belief-preservation gate)*
- **S4 · Business Model.** Transformation-only: every capability, entity, dependency and gap traces to
  an S3 decision or an S2/S1 finding — no new discovery, no new machinery. Scope-boundary clean (a
  deferred item never appears as a modeled capability). *(scope oracle)*
- **S5 · Business Intent.** The subdomain-purpose narrative is **sourced from the seed**, injected at
  render — never authored at S5 (Boundary 2). Provisional codes are well-formed; intent (invariants +
  reasons), not a restatement of S4 structure.
- **S6 · Governance Intent.** Ownership is single-valued per capability; boundary rules keep authority
  clean (one owner writes a store; proposal and commit stay separated).
- **S6b · Design Intent.** **Binding-FQDN discipline:** every assigned code is well-formed
  (`domain::PREFIX_NAME_V<n>`), assigned exactly once, reused verbatim; every code referenced in
  topology/RB is declared in `new_artifacts`; a new code is genuinely absent from the snapshot; the
  business-language rule is **column-scoped** (only the named column forbids FQDNs; code columns carry
  them). NEW counts reconcile with `new_artifacts`. *(structural oracle; bl_columns)*
- **S7 · Authoring Mandate.** The build order is a **topological sort** of S6b's artifacts over their
  dependencies — S7 adds no design and drops nothing. NEW/REPLACE/EXTEND counts equal S6b's; every
  code is present in S6b.

---

## Conformance

A run **conforms** to this core iff **all** cross-cutting invariants and **all** applicable per-stage
invariants hold — checked by the pipeline's own gates, not by comparison to any reference text. The
star rating is a convenience signal, **not** a conformance criterion (per CI-4, gate outcomes are).

A **conformance instance** (optional, per seed) records the seed-specific facts a run produced —
`seed_hash`, belief/gap counts, the reused and authored FQDNs — as a small manifest alongside the
dossier. It pins *what this seed yielded*; this core pins *what any run must satisfy*. When a new
surface is added (a new seed), it gets a new instance; this core is unchanged unless an invariant
itself changes.

## Explicitly excluded from the contract

Artifact wording · specific FQDNs or register rows · the star rating as a number · run traces ·
heading phrasing · anything a different-but-conforming model would legitimately vary.

## Versioning

This contract is **v0**. Its version advances only when an **invariant** is added, removed, or
changed — never when an artifact, a seed, or a run changes. Conformance is evaluated against the
compiler + change-management engine gates that enforce these invariants; a run should record the
(compiler, engine) versions it was checked under.
