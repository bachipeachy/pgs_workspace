# Pipeline Trifecta — Guided Authoring Mode Plan

**Branch:** `trifecta`.
**Role:** the durable **design ledger** for the Guided Authoring → Semantic Projection → Knowledge
Partition work — the substrate mined for the paper. Architectural results are stable and are stated as
results; increment-by-increment status, dates, and process narrative are intentionally being trimmed out
(git history holds the chronology). Read top-to-bottom it is: the trifecta (§1–§10), the Semantic
Projection Protocol (SPP.*), the Knowledge Partition Theorem (SPP.0a), and the Semantic Dimension Model.

---

## 1. Why (background — read first)

The local-model experiment is **complete and answered its real question**: *can PGS objectively evaluate
worker conformance independently of the worker?* — **yes**, with clean per-layer evidence (Worker
Observability Protocol). The dual-model probes established:

| Probe | Verdict (Worker Protocol Trace) |
|---|---|
| qwen3:14b · S1 | authoring-contract failure (emitted 0 registers) |
| deepseek-r1:14b · S2 | **Case D — model limitation** (no native/textual tool call; can't ground) |
| qwen3:14b · S2 | **Case C — query formation** (9 native calls, all phrase queries → 0 results) |
| Worker integration | **proven correct** by observability |

Conclusion: stop trying to make 14B models clear long governed authoring pipelines. The remaining
problem is **deployment**, not engineering. The pipeline (Authoring Protocol → Construction → Compiler
→ CSI → Runtime) is proven. The worker is almost incidental — *the protocol, not the model, is the
system of record.*

This plan elevates that into a first-class capability: **three execution modes** ("trifecta"), all
sharing identical validation / handoff / compiler / CSI / runtime. Only the transport between the
stage prompt and the model changes.

---

## 2. The trifecta (three modes, one interface)

```
                     StageBuilder (governance)
                              │
                              ▼
                        Stage Package
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   AUTOMATED              GUIDED                 OFFLINE
   ClaudeAPIWorker        InteractiveWorker      ReplayWorker
   OllamaWorker           (Claude Code / chat    (recorded response.md
   GeminiWorker            UI / human)            → deterministic replay)
        └─────────────────────┼─────────────────────┘
                              ▼
                         StageOutput
                              │
                              ▼
                    Validator (contracts) → handoff → CSI → compiler → runtime
```

- **Automated** — existing workers (`ClaudeWorker`, `OllamaWorker`, `GeminiWorker`). API/CI path.
- **Guided Authoring Mode** *(NEW, the focus)* — the human is the synchronization point between
  stages. PGS exports a governed **Stage Package**; the human runs it through Claude Code chat (or any
  conversational LLM), reviews, pastes the response back; PGS imports + validates. Zero API cost; human
  stays in governance; better long-form quality; every stage becomes a permanent artifact.
- **Offline replay** *(natural fallout)* — a recorded `response.md` replays deterministically for
  regression. Same interface.

**Key insight:** Claude Code is a *grounding-capable* worker — it has `pi`/Bash in its session, so
Guided Mode is a full grounding worker, not a degraded static-prompt path. The Stage Package's system
prompt mandates grounding via `pi` (never assert an ungrounded FQDN; mark NEW artifacts provisional).

---

## 3. Separation of concerns (do not violate)

| Component | Knows | Must NOT |
|---|---|---|
| `StageBuilder` | governance — builds the Stage Package from a `StageInput` | call any model |
| `Worker` (any) | transport only — turn a package/response into `StageOutput` | build prompts or judge contracts |
| `Validator` | contracts — registers, handoff, figure-of-merit, admissibility | know the transport |

The `Worker` interface stays **unchanged**: `execute_stage(StageInput) -> StageOutput`. `InteractiveWorker`
is just another implementation. This is textbook interface segregation and preserves worker
interchangeability (a hard-won invariant — see `worker/_loop.py` sovereignty doctrine).

Where the review patches sit in the SoC: **`PromptIR`** is `StageBuilder`'s structured output (still
governance). The **`InteractiveIngressValidator`** is a `Validator` concern placed at the human mutation
boundary (it knows contracts, not transport). **`parse_output(mode, raw)`** is transport-adjacent (it
normalizes a raw response into the contract object) and lives with the worker/authoring layer. None of
them move logic into the `Worker` interface or the sovereign loop.

---

## 4. Stage Package (the governed export artifact) — contract-safe

**Patched per architectural review:** the package is a machine-contract artifact, not human-readable
markdown that the Validator can't reason about. Markdown ≠ contract. The canonical, hashed
`prompt_bundle.json` is the source of truth; the `.md` files are *rendered views* for the human to
paste, hash-linked back to the bundle.

```
stage_<N>/
  manifest.json        # stage, domain/subdomain, seed, snapshot_hash, mode, governance_version, prompt_hash
  prompt_bundle.json   # CANONICAL CONTRACT (serialized PromptIR — see §4a). Shape:
                       #   { "system_prompt": "...", "user_prompt": "...",
                       #     "prompt_hash": "sha256:…", "governance_version": "0.7.0",
                       #     "allowed_tools": ["vocab_search", …],
                       #     "register_contract": { "fields": [...], "schema_hash": "sha256:…" } }
  system_prompt.md     # RENDERED VIEW of prompt_bundle.system_prompt (for pasting into a chat UI)
  user_prompt.md       # RENDERED VIEW of prompt_bundle.user_prompt
  context/
    handoff.json       # the bounded upstream gov_projection (exactly what THIS stage may read)
    grounding_spec.json # TYPED GROUNDING CONSTRAINT (§4a) — not optional "context". Shape:
                       #   { "required_tokens": ["BLOCK","TRANSACTION"], "query_rule": "exact protocol
                       #     identifiers, not phrases", "validation_mode": "strict" }
  expected_output.md   # the shape of the ```json registers block (field list + worked example)
  schema.json          # the stage's register emit-field schema (fields, types, required)
  response.md          # (human-pasted on import; absent on export)
```

Every stage becomes **reproducible forever** *and* **machine-verifiable**: `prompt_bundle → response →
ingress-validated → handoff` are all on disk with hashes. Governed Stage Package vs. "prompt → LLM →
hope" — and now with prompt integrity, schema alignment, and deterministic replay all checkable.

---

## 4a. Architectural-review patches (adopt at I1 — do not defer)

The human is a **mutation layer between stages**. Left untyped, that is the one place the pipeline
bypasses the compiler / CSI / structural oracle. These patches close it.

**(P1) Prompt Execution IR** — `engine/prompt_ir.py`, a minimal structured prompt object:
```python
@dataclass(frozen=True)
class PromptIR:
    system: dict            # the governed mandate, structured
    user: dict              # objective + governance rules + handoff pointer
    constraints: dict       # the grounding_spec (required_tokens, query_rule, validation_mode)
```
`StageBuilder` produces a `PromptIR`; `prompt_bundle.json` is its serialization (+ hashes); the `.md`
files are renderings. This makes prompts **structured, diffable, testable** and lets CSI extend upward
into the authoring layer later. *Tempering note: keep it a dataclass + serialization NOW — no diff
tooling/CSI-over-prompts yet; that's a future increment once the IR exists.*

**(P2) InteractiveIngressValidator** — `worker/interactive_ingress.py`. Runs BEFORE the engine sees a
guided response: parses the `response.md` json, validates the register schema (`schema_hash`/fields)
and grounding conformance (`grounding_spec.validation_mode`), and rejects malformed handoffs. The human
cannot become an untyped compiler bypass. (The engine's downstream structural oracle still runs — this
is an *additional*, fail-fast, transport-specific gate at the human boundary.)

**(P3) Mode-aware parsing** — `parse_output(mode, raw)` dispatch over a SHARED core, NOT three forked
parsers:
- `automated` — model content + tool-loop noise (today's `_parse_output`/`_last_json_block`).
- `interactive` — human-pasted text: tolerate copy-paste artifacts / surrounding chatter; still the
  same json-block extraction core.
- `replay` — strict deterministic json (recorded response).
*Tempering note: one core extractor + thin per-mode pre-normalizers (DRY); avoid three divergent copies.*

**(P4) grounding_spec as a typed constraint** (replaces the §7 "glossary" decision — now resolved as
*include, typed*). It declares the stage's protocol code-tokens + the query rule, and the ingress
validator can check conformance. This fixes the Case-C query-formation failure **by declaration, not
heuristic** (no `vocab_search` rewriting). *Design point: `required_tokens` are derived from the stage's
domain vocabulary (seed + handoff scope); they are a grounding *frontier*, not an answer key — the
worker must still confirm each via `pi`. How to derive the relevant set without over-/under-scoping is
an I1 design task.*

**(P5) Human Mutation Boundary marker** — the interactive `StageOutput` carries provenance metadata:
```json
{ "origin": "human_guided", "mutation_boundary": true, "validated_by": "ingress_validator",
  "prompt_hash": "sha256:…", "model_label": "<claude-code|chatgpt|…>" }
```
Critical for audit trails, CSI evaluation, and the reproducibility claim. (Ties into the provenance
ratchet work.)

---

## 5. Deliverables (files)

All in `pgs_change_mgmt`, on branch `trifecta`:

1. **`engine/prompt_ir.py`** *(P1)* — `PromptIR` dataclass (system/user/constraints) + serialize
   (`prompt_bundle.json` + `prompt_hash`/`schema_hash`) + render (`.md` views). The structured prompt
   source of truth.
2. **`engine/stage_package.py`** — `StagePackageBuilder`: `StageInput → PromptIR → stage_<N>/` package
   (manifest, prompt_bundle.json, rendered .md, context/handoff.json, context/grounding_spec.json,
   expected_output.md, schema.json). Pure governance/export, no LLM. Reuses `DossierEngine._stage_input`
   and the shared renderer.
3. **`worker/interactive.py`** — `InteractiveWorker(Worker)`: import-only. `execute_stage(task)` reads
   `stage_<N>/response.md`, parses via `parse_output("interactive", raw)`, attaches the **Human
   Mutation Boundary** metadata *(P5)*, returns `StageOutput`. Builds nothing. Clear error if
   `response.md` is missing. Emits Layer-1 `wpt_request` (transport=`interactive`) → Worker Protocol Trace.
4. **`worker/interactive_ingress.py`** *(P2)* — `InteractiveIngressValidator`: validates the pasted
   response's register schema (`schema_hash`/fields) + grounding conformance (`grounding_spec`) BEFORE
   the engine sees it. Rejects malformed handoffs at the human boundary.
5. **`engine/run_interactive.py`** — two-phase runner:
   - `--seed <s> --stage <N> --export [--dir <path>]` → writes `stage_<N>/`; prints next steps + the
     grounding affordance (Claude Code may run `pi …`).
   - `--seed <s> --stage <N> --import` → ingress-validate → run `DossierEngine` for stage N with
     `InteractiveWorker(dir)` → doc + `_handoff/<N>.json` + figure-of-merit, **identical** to Automated.
6. **Shared refactor (small):** extract `SYSTEM_PROMPT`, `_render_task`, and the parse core from
   `ollama_worker.py` into `worker/_authoring.py`; expose `parse_output(mode, raw)` *(P3)* (one core +
   per-mode pre-normalizers). No behavior change for existing workers (`OllamaWorker` calls
   `parse_output("automated", raw)`).
7. **`worker/_interactive_selftest.py`** — deterministic, **no live model**: export → stub a valid
   `response.md` → ingress-validate → import → assert handoff + figure-of-merit; assert a missing/
   malformed `response.md` is rejected by the ingress validator; assert `prompt_hash` round-trips.
8. **Docs:** `pgs_change_management_conceptual_model_v1` introduces Guided Authoring Mode + the Stage
   Package / Prompt IR as first-class; `pgs_change_mgmt/README.md` documents the three modes.

---

## 6. Increments (commit boundaries)

- **I1** — `PromptIR` + `StagePackageBuilder` (contract-safe `prompt_bundle.json` with hashes +
  `grounding_spec.json`) + shared-renderer refactor + export selftest (package complete, hashes stable,
  for S1 & S2). Resolve the `grounding_spec.required_tokens` sourcing rule.
- **I2** — `InteractiveIngressValidator` + `InteractiveWorker` (import, mutation-boundary metadata) +
  `run_interactive` two-phase + selftest: export → stub valid `response.md` → ingress-validate → import
  → handoff; plus malformed-response rejection + `prompt_hash` round-trip. No model.
- **I3** — Worker Observability integration (Guided stages emit a Worker Protocol Trace) + figure-of-
  merit parity (stubbed Guided S1 == automated stub S1) + `parse_output` mode-adapter proof (automated/
  interactive/replay over one core).
- **I4** — Docs (conceptual paper + README) + a live dry-run of S1→S2 in Guided Mode using Claude Code
  (the human/Claude grounds via `pi`, pastes registers, ingress-validates, imports).

---

## 7. Open decision — RESOLVED by P4

The former "glossary include vs minimal" question is resolved: **include, as a typed
`grounding_spec.json` constraint** (not optional context). It declares `required_tokens` + `query_rule`
+ `validation_mode`, the ingress validator checks conformance, and it fixes Case-C by declaration not
heuristic. The *only* sub-decision left for I1: **how `required_tokens` are derived** per stage from the
domain vocabulary (seed + handoff scope) without over-scoping (every token) or under-scoping (missing
the ones the stage needs). It is a grounding *frontier* the worker must still confirm via `pi`, never an
answer key.

---

## 8. Current-state references (so a fresh session can navigate)

- **Worker contract:** `pgs_change_mgmt/pgs_change_mgmt/contracts` — `Worker.execute_stage(StageInput)
  -> StageOutput`; `StageInput` carries `stage`, `objective`, `input_projection` (bounded handoff),
  `governance_rules`.
- **Automated worker to mirror:** `worker/ollama_worker.py` — `SYSTEM_PROMPT`, `_render_task`,
  `_parse_output` (accepts enveloped `{registers,...}` and bare contract object). Shared tool-loop in
  `worker/_loop.py` (sovereign; transport-agnostic).
- **Engine:** `engine/dossier.py` — `DossierEngine.run` / `_run_stage` (builds `StageInput`, calls the
  worker, renders the doc, runs the structural oracle, persists `_handoff/<N>.json`, computes the
  figure-of-merit). `_stage_input(cfg, stage, template)` builds the task. `DOSSIER_SEEDS["blockchain_chain"]`
  seed config (seed_path = the golden `chain/1_input_elicitation_*`).
- **Stage dispatch:** structured stages assemble via `STAGE_PROJECTORS` (S8 build sheet); worker-authored
  stages use `STAGE_BASENAME`. S9 is Construction evidence (`construct_chain.render_s9`), NOT a dossier
  stage.
- **Worker Observability Protocol (the 4th pillar, just built):** `worker/_diagnostics.py`
  (`WorkerProtocolTrace`, `Termination` enum, layer-ownership verdict), additive emits in `_loop.py`,
  `--diagnose` flag in `run_dossier.py`, `worker/_diagnostics_selftest.py`. Guided Mode should reuse it.
- **CSI / Semantic Preservation (3rd pillar):** `pgs_compiler/compiler/projections/{ipm,reverse}.py`,
  `pgs_change_mgmt/evaluator/roundtrip_equivalence.py`, `engine/semantic_preservation_gate.py`. Runs
  after compile; not part of authoring but the downstream gate Guided Mode feeds.
- **Run a stage (automated, for reference):**
  `PGS_WORKSPACE=/abs scripts/run_change_mgmt_dossier.sh --worker ollama --model <m> --stage 2 [--diagnose]`.

---

## 9. Release context (the 0.7.0 this branches from)

0.7.0 bundles: the entity model (governance + blockchain), CSI v1 + Semantic Preservation Gate
(compiler + change_mgmt), the `s1_extract` list-`governed_by` fix (CSI Finding #001, resolved), and the
Worker Observability Protocol. Versions: pgs_compiler / pgs_governance / pgs_blockchain / pgs_workspace /
pgs_change_mgmt → **0.7.0**; runtime / transport / capabilities / ai_governance stay **0.5.0**.
`COMPILER_VERSION` bumped to 0.7.0 and the snapshot recompiled so its stamp matches. Manifest:
`pgs_workspace/manifest.json`.

---

## 10. The thesis this strengthens

PGS verifies authored protocols (Authoring Protocol), transformation (Compiler), semantic preservation
(CSI), and worker behavior (Worker Observability). Guided Authoring Mode adds the deployment claim:
**the protocol is the system of record; automation is an optimization layered on top, not a
prerequisite.** Any conversational LLM — Claude API, Claude Code, ChatGPT, Gemini, a future open model,
or a human expert — is just another `Worker`. That is genuine worker independence.

---

# Successor RFC — Semantic Projection Protocol (SPP)

**Status:** PROPOSED — design artifact, no code. Successor to the trifecta above.
**Origin:** exposed by the Guided-Authoring S1→S2 experiment. S1 (transcription)
reproduced the golden Change Request **byte-for-byte**; S2 (discovery) came out **~half the depth**
of the golden domain model despite a well-grounded worker (Claude Code with `pi`). Row counts:
entities 7→5, business_processes 8→2, process_steps 14→2 — while the **belief-verification spine
matched exactly (9→9)**. The finding is not "the worker is shallow"; it is that **the platform does
not yet govern discovery completeness**. This RFC converts that gap into a protocol.

## SPP.0 The constitutional principle

> **Deterministic evidence acquisition shall be performed by the platform. Judgment over evidence
> shall be performed by governed workers.**

One sentence captures the leap. Evidence *acquisition* is deterministic and belongs to the platform;
evidence *disposition* is judgment and belongs to a governed worker; *completeness* of disposition is
validated by the oracle. Everything below is a consequence of this rule.

## SPP.0a Knowledge Partition Architecture (the theorem)

The core architectural law this work earned — a *Knowledge Partition* (epistemic partition, in the
body): the separation of deterministic knowledge from judgment.

> **Knowledge Partition Theorem.** A Protocol-Governed Computing system shall partition deterministic
> knowledge from judgment. The platform may **acquire, normalize, verify, and present** evidence, but
> may **never determine its semantic relevance** to a transformation. Semantic relevance belongs
> exclusively to the transformation author.

This is stronger than "you cannot pre-compute meaning from structure" (SPP.11c) — that statement is
true; the theorem explains *why* and makes it prescriptive. The frozen model:

| Engine | Responsibility | May infer meaning? |
|---|---|---|
| **Compiler / DP1** | acquire + normalize evidence (graph, identity, projections, evidence floors) | **No** |
| **Worker / DP4** | dispose evidence + author the transformation | **Yes** |
| **Runtime** | execute the compiled protocol | **No** |

Exactly **one** engine may make semantic judgments; everything else is deterministic. That precise
redefinition of the compiler follows: the compiler is a **deterministic knowledge producer** — it emits
governed outputs (Runtime Snapshot · Inspection Projections · Semantic Projections · Stage Packages ·
Evidence Floors) but **never interpretations**. PGS is not an AI-orchestration or workflow system; it is
a **Knowledge Partition Architecture** that enforces *where meaning is allowed to exist*. The only
failure mode left is **boundary creep** — DP1 drifting toward semantic filtering, or DP4 toward
structural inference. The invariant, enforced by construction (the disposition gate checks completeness,
never content):

> **DP1 = no meaning. DP4 = no structure manipulation.**

**The Single-Producer Law (Compiler Authority) — the dual of the Semantic Derivation Law.**

> The compiler is the *unique producer* of deterministic semantic knowledge. Consumers may **interpret**
> it, but never **recreate** it. No consumer independently re-derives a deterministic fact the compiler
> already produces.

Together the two laws close the loop: every deterministic fact has *exactly one authoritative producer*
(Single-Producer) and *carries its provenance* (Semantic Derivation). Runtime executes compiled
knowledge; PI inspects it; Stage Packages carry it; LLMs consume it — none recompute it. This eliminates
an entire class of drift: two consumers can never disagree about a deterministic fact, because neither
computed it. It is also directly falsifiable in the codebase — when the Semantic Model *inferred*
`subdomain` it was a consumer recreating deterministic knowledge (a drift surface); graduating it to a
compiler-emitted `owner_subdomain` that the model merely *reads* is the law being enforced.

## SPP.0b Authoring Completeness — the Authority/Authorship boundary (Boundary 2)

The Knowledge Partition (Boundary 1) says *you cannot compute meaning from structure*. Authoring the
Business Intent (S5) surfaced its companion — **Boundary 2**:

> **You cannot compute authority from meaning.** Even if a worker can produce a plausible business
> purpose, that choice carries no authority. Authority originates only with the human requestor.

This completes the partition into a **three-way**, non-overlapping ownership of knowledge:

| Owner | Provides | Derivable by anyone else? |
|---|---|---|
| **Human** | Authority — purpose, scope, intent, ownership, business decisions | **No** |
| **Compiler / DP** | Deterministic knowledge — structure, evidence, projections | No (single producer) |
| **Worker** | Transformation & judgment — disposition, modeling, authoring | — |

**A seed gap *is* an authoring gap** — it simply occurs at the earliest phase. There is one concept,
not two: a **human-owned authoring field** that must be supplied by a human. Each field is *declared*
(never discovered), carrying `owner · derivable:false · phase · type · required_before ·
renderer_target`. Because it is declared, the platform knows a gap exists at t0 — it never has to hit
a wall at S5 to *find* that Purpose is missing.

> **Authoring Completeness Invariant.** Every human-owned field must be complete **at the point of
> first use** — not at system entry. The seed is the *first* checkpoint, not the *global* one. A
> `phase:seed` field (Purpose, scope, intent) is caught before S1; a genuinely *stage-emergent*
> obligation (a decision that only exists because prior derivation produced structure) is caught at
> *its own* stage boundary. The gate is symmetric with ingress: `AUTHORING_INCOMPLETE : stage :: NACK
> : ingress`. It is **structural** — it checks presence, never content — so it stays inside the
> Knowledge-Partition guardrail. When a field is absent the platform **stops and states exactly what
> is missing and why**; it may offer a clearly-labelled draft for a *narrative* hole, enumerate
> options for a *decision* hole, but it **never manufactures authority**.

The `required_before` edges over the stage DAG are the embryonic **Authoring Obligation Graph** — the
compile-time product that maps each human obligation to the first stage that depends on it. This is
the mirror image of the compiler work: as deterministic knowledge moved *upstream into the compiler*,
foundational **intent moves upstream into the seed** — so S1–S4 *refine* intent rather than *discover*
its existence. Falsifiable in the codebase: **Subdomain Purpose** was an unfilled S5 prose placeholder
(the worker was being asked to originate authority); graduating it to a declared `subdomain_purpose`
seed field — validated by the Authoring Completeness gate and injected into S5 §1 at render — is
Boundary 2 being enforced. The declared registry lives in `change_mgmt/authoring_fields.json`; a new
human-owned field tomorrow is a *declaration there, not code*.

## SPP.1 Why (the finding, precisely)

Stage 2 implicitly does three jobs: (1) **acquire** the existing protocol neighborhood —
*deterministic*; (2) **interpret** it for this change — *judgment*; (3) **author** the new delta —
*judgment*. Only (2) and (3) need a worker. Job (1) currently lives in the worker, so discovery
breadth is a worker-effort variable: two workers over the same snapshot saturate the neighborhood
differently while both satisfy the contract. The structural oracle checks *correctness*, not
*completeness*. SPP moves job (1) into the platform.

## SPP.2 It is a Protocol, not a tool (Patch 2)

SPP is a **protocol**, independent of any tool. Roles:

| Actor | Relationship to SPP |
|---|---|
| **Compiler** | *implements* — it produces semantic projections as governed products |
| **PI** | *exposes / consumes* — one read surface over projections; not their owner |
| **Stage Package** | *exports* — carries a projection to any worker |
| **Runtime** | *may consume* — projections are available beyond authoring |

PI is merely one implementation surface. The protocol must never be defined in terms of PI.

## SPP.3 The Semantic Projection family (Patch 1)

The mechanism is bigger than Stage 2. SPP defines a **family**:

```
Semantic Projection
    ├── Discovery Projection        ← the first instance (this RFC's worked example)
    ├── Impact Projection
    ├── Authority Projection
    ├── Workflow Projection
    └── Transformation Projection
```

Each is a governed view over the protocol. Discovery Projection is defined here; the others are
future instances of the same protocol, reusing its contract, identity, and oracle.

## SPP.4 Projection Contract (Patch 7)

Every semantic projection declares a **Projection Contract** — the stable interface a projection
type must satisfy:

| Contract field | Meaning |
|---|---|
| **Purpose** | what question the projection answers |
| **Inputs** | the governed inputs it is computed from |
| **Authority** | what the projection is authoritative *about* (and what it is not) |
| **Output Schema** | the machine-readable shape it emits |
| **Invariants** | what must always hold of the output |
| **Determinism** | the reproducibility guarantee (see SPP.5) |
| **Completeness Guarantees** | what the projection promises to have enumerated |

Discovery Projection is simply one instance of this contract.

## SPP.5 Projection Identity — snapshot-addressable (Patch 3)

**Invariant:** every semantic projection is *reproducible from the same snapshot*. Each projection
carries an identity block:

```
Projection Identity
  ├── Source Snapshot ID
  ├── Projection Protocol Version
  ├── Projection Type + Identity
  ├── Generation Timestamp
  ├── CR Identity
  ├── Roots
  └── Bounds
```

This lets a paper state, as a theorem rather than a hope: *every semantic projection is reproducible
from the same snapshot.* Stronger than "generated." Ties into CSI determinism
([[project_csi_semantic_preservation]]).

## SPP.6 Discovery Projection (the first instance)

> **Discovery Projection** : Transformation Scope → **Governed Semantic Neighborhood**.

The protocol governs the **abstraction** (a *Governed Semantic Neighborhood*), never a traversal.
"1-hop", "graph walk", "depth-N" are implementation notes, not protocol — the compiler is free to
realize the neighborhood by one-hop today and typed / authority-aware expansion tomorrow without
changing the contract. Likewise the **roots are derived from the declared transformation scope**; the
compiler decides *how* (v0 realizes the scope as concept tokens from the CR's business vocabulary /
system beliefs / governance scope). It **never contains** proposed entities / the NEW delta, inferred
rules, or implementation suggestions.

**Evidence schema — negative and structural evidence are first-class peers of positive evidence:**

| Category | Meaning |
|---|---|
| `existing` | **positive** — neighborhood nodes that exist; each carries **inclusion provenance** |
| `absent` | **negative** — declared concepts that resolve to zero artifacts (e.g. `GENESIS→0`) |
| `structural` | structural observations the edge model supports **reliably** (orphans, dangling refs) |
| `relationships` | typed edges among neighborhood nodes |
| `authority` / `supporting_artifacts` | governance / test-and-assertion views over `existing` |

**Two invariants:**
- **Determinism** — same snapshot + same scope ⇒ identical `projection_id`.
- **Projection Closure** — every `existing` node carries a non-empty `included_because`
  (`root` / `dependency` / `reference`); nothing appears "because traversal happened."

**Reliability rule (learned in DP1):** the platform emits only structural claims the edge model
*supports* — it never over-claims. (DP1 dropped a naïve "missing-producer = event with no in-edges"
signal after it flagged **every** event: the graph materializes no producer→event edge, so the claim
was underivable. Negative evidence for a *concept* is sound; a per-event producer claim is not, yet.)

**DP1 result (validated against the blockchain/chain stage-2 test data):** the platform
deterministically acquired a **102-node neighborhood** (41 CC · 16 WF · 9 IN · 8 RB · 8 EV · …)
containing the golden-S2 neighborhood a shallow worker search missed, plus `GENESIS/LEDGER/BOOTSTRAP`
as first-class negative evidence — proving evidence *acquisition* is a platform capability.
`inspection/discovery.py` + `pi snapshot discover` + `_discovery_selftest.py` (ALL PASS).

**Exactly ONE governed Discovery Projection — not configurable** (SPP.12). Clean separation preserved:
**PI = "what is." · CR = "what is desired." · Worker = "how to transform what-is into what-is-desired."**

## SPP.7 Disposition belongs to the worker; not to PI (Patch 5)

The platform's vocabulary about the neighborhood is strictly **factual** and describes the *evidence*,
not traversal semantics:

- projection says only: **Existing · Absent · Structural · Relationships · Authority · Supporting**.

It must **never** say `RELEVANT` / `EXCLUDED` / `NEW` — those are *judgments*. Disposition is the
worker's job:

- Worker disposes each projected element: **`RELEVANT` · `EXCLUDED (reason)` · `NOT_APPLICABLE` ·
  `REQUIRES_CLARIFICATION` · `NEW`**.

This generalizes the belief-verification spine (every belief → a disposition) to the whole
neighborhood, and keeps the platform free of judgment.

## SPP.8 Disposition Completeness oracle (Patch 8)

The oracle principle is broader than "Discovery Saturation" — it is **Disposition Completeness**:

> Every element a semantic projection acquires must be **disposed** by the worker. No undisposed
> element is admissible.

Not a coverage percentage (`5/7`) but total disposition (`7/7 disposed`, any mix of dispositions
with reasons). Discovery is merely the first *consumer*; impact/authority/workflow projections reuse
the identical oracle pattern. This is [[project_provenance_ratchet]] ("no undisposed inference")
generalized across the projection family.

## SPP.9 Ship the projection inside the Stage Package

At export, the Stage Package carries `context/discovery_projection.json`. Consequence: **every
trifecta mode receives the identical evidence floor** — a no-tool chat UI, a local model, a frontier
API, and Claude Code all start from the same neighborhood. **Discovery quality is decoupled from tool
availability.** The trifecta's `grounding_spec.required_tokens` (I1/P4) is revealed as **v0 of this
idea** — a flat token frontier; the Discovery Projection is its governed successor.

## SPP.10 The compiler produces Protocol Products (Patch 4)

```
Authoring Artifacts → Compiler → Protocol Products
                                   ├── Runtime Snapshot      (the executable protocol)
                                   ├── Inspection Products    (artifact_index, stores, evidence views)
                                   ├── Semantic Projections   (discovery, impact, authority …)  ← NEW
                                   ├── Stage Packages         (now carrying a projection)
                                   └── Evidence Products      (the disposition/completeness record)
```

The compiler is a **producer of protocol products** for different consumers, not merely a snapshot
compiler. Strategically these are beginning to look like a coherent subsystem — *Compiler Semantic
Services*. Not formalized now; kept in mind as the compiler evolves.

## SPP.11 Increments — protocol before code (DP naming, Patch 10)

- **DP0 — Semantic Projection Protocol (no code).** Ratify the Projection Contract, Projection
  Identity, the `Existing/Absent/Structural/Relationships/Authority/Supporting` platform vocabulary,
  and the Disposition Completeness oracle principle. Pure specification. *(Embodied as code contracts
  in DP1: `TransformationScope`, the evidence schema, Projection Identity, the two invariants.)*
- **DP1 — Compiler emits the Discovery Projection.** Deterministic,
  snapshot-addressable, scope-seeded, one governed projection. `pgs_compiler/inspection/discovery.py`
  (`compute_discovery_projection` over `SemanticGraph`) + `pi snapshot discover` +
  `_discovery_selftest.py` (validated against blockchain/chain stage-2: 102-node neighborhood contains
  the golden set; `GENESIS/LEDGER/BOOTSTRAP` negative evidence; closure + determinism hold). **Review
  gate — stop here.**
- **DP2 — Stage Package exports it.** `StagePackageBuilder` computes the Computed
  Semantic Neighborhood (invoking the compiler product directly) and ships
  `context/discovery_projection.json`; the manifest carries `discovery_projection_id`. S1 is excluded
  (transcription, not discovery). All trifecta modes get the same evidence floor.
- **DP3 — Worker consumes it.** A `DISCOVERY_PROJECTION_DIRECTIVE`
  shifts the discovery stage from search to *disposition + delta* when a neighborhood ships.
  **Measured on the Guided S2 re-run (zero new `pi` lookups):** depth rose from ~50% → **94% of
  golden** (entities 5→7=golden, attributes 4→8=golden, processes 2→8=golden, pps 5→7>golden) with
  the **belief spine identical (9/9)** and governance 100%. The residual gap is *interpretation*
  depth (fewer observations), not *evidence* availability — exactly the split the projection creates.
- **DP4 — Disposition Completeness oracle.**
  `evaluator/disposition_completeness.py` (`assess` + `DispositionReport`) + `_disposition_completeness_selftest.py`
  (ALL PASS, measured on real chain S2). The belief-spine gate generalized to the whole neighborhood:
  every `existing` node + `absent` concept must be disposed — implicit RELEVANT (cited FQDN), explicit
  **group rules** (segment-pattern or `kind:<K>`, so adjacent-subdomain internals disposition in one
  line), or `absent`→GAP via the gaps register / REPRESENTED. An undisposed element ⇒ inadmissible.
  **Two results:** (1) 100% completeness is reachable (RELEVANT 34 · NOT_APPLICABLE 89 · GAP 3 ·
  REPRESENTED 2 · EXCLUDED 2); (2) the 71% NOT_APPLICABLE / 30-rule cost was investigated as an
  over-scope signal and **resolved as the boundary discovery** (SPP.11c) — it is *judgment*, not
  over-scope. **Wired:** `engine/disposition_gate.py` (`check_disposition`) runs at Guided
  import after ingress, before the engine, whenever a projection ships. Live proof: the real chain S2
  with no dispositions is **REJECTED** (26% coverage, 90 undisposed, engine not run); with
  `neighbourhood_disposition` group rules it is **ADMITTED** (100% coverage) and imports. The worker
  supplies dispositions as implicit RELEVANT (cited FQDN) + explicit group rules; the gate checks
  *completeness only* — see SPP.0a. `_disposition_gate_selftest.py` (ALL PASS).
- **DP5 — Prove the LAYER (second Semantic Projection).** The Semantic Projection
  Protocol is now a real, shared contract, not a one-off. `inspection/semantic_projection.py` holds it
  (`build_projection` + Projection Identity + determinism + snapshot fingerprint); Discovery Projection
  was refactored to *consume* it (proving instance-hood), and **Impact Projection**
  (`inspection/impact_projection.py`, `pi snapshot impact-projection`) is a second instance — the
  transitive-consumer blast radius of an artifact. `_impact_projection_selftest.py` (ALL PASS) proves
  Impact + Discovery share ONE identity contract, both deterministic + snapshot-addressable + closed.
  Critically, **the Public Semantic Surface works here** (SPP.11c) — because the subject *exists*, its
  cross-boundary consumers are its published contract. That is the property Discovery could not have,
  and its natural home. The compiler is now demonstrably a *deterministic knowledge producer* of a
  **family** of semantic projections.
- **DP6 — Guided Mode validation.** `engine/guided_validation.py`
  (`validate_guided_stage` + `GuidedValidationReport`) + `_guided_validation_selftest.py` (ALL PASS on
  the real chain S2). The DP3 one-off is now a deterministic four-axis report: **completeness** (consumer,
  GATED) · **judgment preservation** (the invariant — every S1 belief disposed, GATED) · **efficiency**
  (producer, DIAGNOSTIC — has a judgment floor, never gated) · **coverage vs golden** (evidence + depth,
  DIAGNOSTIC). Measured live: completeness 100% ✓, judgment 9/9 ✓, efficiency 29%, evidence coverage
  100%, depth 90% → **PASS**. The gate **encodes the Knowledge Partition Theorem as a metric**: a low
  efficiency does NOT fail it (efficiency is not judgment); losing one belief disposition DOES
  (judgment is the invariant). This is the thesis operationalized — the platform improves deterministic
  evidence while judgment stays invariant.
- **DP1.3 — Deterministic Evidence Floor Stabilization (reframed after a hard finding).**
  *Originally* "interface-bounded neighborhood" (exclude adjacent-subdomain internals via
  cross-boundary reference). **Empirically rejected** — see SPP.11c. Reframed to trim only what is
  STRUCTURAL or CR-DECLARED, never semantic: (1) scaffolding kinds (`TEST_DATA`/`ASSERT`); (2)
  CR-declared out-of-scope concepts (S1 §12), best-effort lexical. Result: scaffolding trimmed 5 nodes,
  out-of-scope 0 (word-form mismatch — the platform refuses to guess), coverage held 100%, efficiency
  24%→25%. Trimmed nodes recorded in `evidence.excluded` with a reason (never silently dropped). DP1
  is now **frozen** (evidence normalization).

**DP1.1 — Roots refinement (surfaced by the golden S2 evidence-overlap gap).** The
first DP3 run matched golden's register *counts* (94%) but its *evidence* overlap with golden was only
40% — the neighbourhood under-covered the belief-target subdomains because roots were derived from
vocabulary + lifecycle tokens only. Fix: (1) roots now harvest the CR's **declared governance scope**
(S1 §13 `scope_item` — consensus_pos, orchestration, wallet, transaction, mempool, identity), i.e.
roots from the *declared transformation scope* (SPP.6); (2) root matching is **whole-segment (with
plural tolerance)**, not substring — killing the `ONCE`→`NONCE` / `CHAIN`→`BLOCKCHAIN` false
positives; (3) **root-only belief-target seeds** — concepts named in the CR's system-belief prose
(S1 §5, e.g. `VALIDATOR`, `SLOT`) seed roots but never `absent` (prose can't manufacture false gaps).
Result: golden evidence coverage **40% → 90% → 100%** (8/20 → 18/20 → **20/20** FQDNs; 74 → 116 → 125
nodes). All golden citations verified present in the snapshot (0/14 stale).

**DP1.2 — Semantic concept classification (clean the absence frontier).** This is not
"token precision" — it is a semantic *type* refinement of the compiler. A harvested token's category
is the register column it came from (the register schema already declares meaning): **ENTITY/CONCEPT**
(term, entity, name, object, actor, event, attribute, scope_item) vs **LIFECYCLE** (state) vs
**RELATIONSHIP** (relationship) vs **VALUE** (certainty, enums). *Only ENTITY/CONCEPT-class tokens
participate in absence reasoning* — a lifecycle state or relationship value that matches no artifact is
a different category, not a gap. All-caps prose hints (MINT, ETH) seed roots only. Result: golden
coverage **holds at 100%** while `absent` drops 10 → 5, all genuine concepts
(`GENESIS`/`BOOTSTRAP`/`COMMIT` true gaps; `BACHICOIN`/`IDENTITY` concepts represented under other
artifacts — dispositionable, not false gaps). The noise (`ACTIVE`/`UNINITIALIZED`/`ONCE`/`ADJACENT`/
`POS`) is eliminated. This strengthens the compiler's semantic type system — the producer is fixed
once, so DP4's oracle consumes a high-quality floor rather than compensating for noise.

**SPP.11b — The architectural law this establishes.** *Protocol maturity increases by relocating
deterministic responsibilities from workers into semantic services.* The evidence, measured on one
stage across three runs:

| Capability | Initially owned by | Mature PGC owner |
|---|---|---|
| Reference resolution | Runtime | Compiler |
| Semantic verification | Human | CSI |
| Failure diagnosis | Human | Worker Observability |
| **Evidence acquisition** | **Worker** | **Discovery Projection** |

Guided S2 depth by run: **search ~50% → projection v0 94% → refined roots 100%**, belief spine
identical throughout. The platform improved not the worker, not the prompt, not the oracle — *its own
semantic understanding*. The milestone: **the compiler becomes a producer of deterministic semantic
knowledge products from a snapshot, not merely a translator.** If Runtime was the execution milestone
and CSI the verification milestone, Discovery Projection establishes the compiler as a *knowledge
producer* — the beginning of a semantic-services layer for PGC.

**SPP.11c — The boundary discovery (the epistemic cut).** DP1.3 was going to bound the neighborhood to
adjacent-subdomain *interfaces* (public semantic surface) via cross-boundary reference. A pre-build
empirical test **refuted it decisively**: of the worker's RELEVANT nodes, **0 were "public" and 30 were
"internal"**; filtering to the public surface would drop every RELEVANT node and keep NOT_APPLICABLE
ones. Two structural reasons: (a) subdomains here are *event-decoupled* (≈4 cross-subdomain functional
edges in the whole graph); (b) a NEW subdomain's relevant artifacts are *internal to their own
subdomains* and have no existing external consumer — because the consumer (the chain) is the thing
being authored. The law:

> **You cannot pre-compute meaning from structure — only structure from structure. Relevance lives in
> the transformation intent, not in the discovered graph.**

Consequences, adopted: **efficiency is a diagnostic signal only** (it has a *judgment floor*; the DP1.3
trim moved it 24%→25%, proving the floor is nearly all judgment); **relevance is DP4/worker domain**
(disposition, not acquisition — pre-bounding it would move judgment into the platform, violating SPP.0);
**Public Semantic Surface is a *future* projection concept** (Impact/Authority/Transformation, where the
consumer already exists in the graph — there it resolves; here it cannot). This is not a setback — it is
one of the cleanest cuts in the architecture: *DP1.3 is where DP1 stops being able to define DP3.*

**SPP.11a — Two properties this surfaced (worth the paper):**
- **A codified invariant:** *a semantic projection shall emit only claims the protocol graph
  supports.* The graph is the authority, not the author's intuition. Before, the platform "couldn't
  find" the orphan event; now it "correctly refuses to invent it" — scientifically stronger.
- **A compiler feedback loop:** DP1 could not reproduce the golden's "EV_BLOCK_COMMITTED is an orphan"
  claim because the evidence graph materializes no producer→event edge. Rather than reproduce an
  unverified inference, the platform withheld the claim — *revealing a deficiency in the compiler's
  own semantic model*. Semantic projections are therefore not only consumable artifacts but a
  mechanism for validating and improving the compiler's knowledge representation
  (`Compiler → Projection → finds missing semantics → Compiler evolves`). DP1 is also the first
  genuine **semantic service** — PI output another subsystem *consumes*, not merely a diagnostic view.

## SPP.12 Explicitly NOT configurable (initially)

The protocol defines **exactly one** governed Discovery Projection. **No** `depth=3`,
`include_workflows=true`, `exclude_authority=false`. Configurable projections would let every worker
request a different neighborhood — recreating prompt engineering in another form. Later protocol
versions may evolve the single definition; workers never parameterize it.

## SPP.13 Guardrails (not a kitchen sink)

Not the domain model — it is the *evidence floor* over which the model is built. Not authority over
what is *needed* — the CR owns that; the projection is authoritative only about *what exists*. No
proposed entities / inferred rules / implementation suggestions. Not a mandate to transcribe — the
worker *disposes* and *authors the delta*.

## SPP.14 Thesis — the coherent lineage

SPP is the fourth move in one narrative — **progressively relocating deterministic responsibility
from AI agents into governed platform services**:

- **Authoring / Transformation Protocol** — moved *process* out of prompts.
- **CSI** — moved *semantic validation* out of human judgment.
- **Worker Observability** — moved *diagnosis* out of intuition.
- **Semantic Projection Protocol** — moves *evidence acquisition* out of the worker.

Each leaves the worker only what genuinely needs judgment. Together they are a stronger long-term
story than any single feature: authority out of AI agents, into deterministic, protocol-governed
platform services.

---

# Successor — The Semantic Dimension Model (the substrate under the projections)

The DP series repeatedly surfaced the *same* shape of gap: a projection needed a semantic property the
compiler's model did not carry (scope→roots, concept type, the structure/meaning partition, subdomain).
Patching each as a special case (add a `subdomain` field, then `authority`, then `visibility`, …) ends in
an ad-hoc attribute database — the anti-pattern PGS exists to avoid. The right abstraction is to name the
general shape.

**The compiler is the semantic heart of PGS.** It no longer merely builds a Runtime Snapshot; it produces
a *canonical Semantic Model*, and everything else is a deterministic view over it:

```
        Protocol Compiler
               │
               ▼
        Semantic Model  (canonical — the DSD substrate)
               │
      ┌────────┼────────────┐
      ▼        ▼            ▼
 Runtime    Inspection   Semantic
 Snapshot   Queries      Projections
```

Runtime is now *one consumer* of the model, not the model's purpose. Inspection, transformation,
validation, impact/dependency analysis, migration planning, documentation and visualization all become
deterministic **queries over the same substrate**. PGS has quietly shifted from a *protocol execution
substrate* to a *protocol-governed semantic computing substrate*.

## The model — Deterministic Semantic Dimensions (DSDs)

The dimensions are named **Deterministic Semantic Dimensions** — the adjective is load-bearing: it excludes
the embeddings / ontology / latent-semantics reading. A DSD is *provenance-carrying, not learned* — every
value answers "derived_from what?".

- **Semantic dimensions (per artifact)** — the facets an artifact possesses: domain · subdomain · kind ·
  capability · ownership · lifecycle · authority · visibility · execution / persistence / transformation
  boundary · … Subdomain is *one* dimension, never privileged.
- **Typed semantic relationships (per edge)** — already present in the graph: contains · governs · binds ·
  routes · references · publishes · consumes · authorizes · persists · executes. The graph is already a
  *semantic* graph on the edge side; the gap is only node dimensions.
- **A semantic projection is a query over the model**, not an engineered traversal:
  - Discovery = project where `domain = X ∧ subdomain ∈ adjacency(scope) ∧ visibility = public`
  - Impact = project transformation through `execution · authority · persistence`
  - Authority = project `authority` through `capabilities`
  - Transformation = project `transformation` through `lifecycle`

  Discovery, Impact, Authority, Transformation, Governance, Security become *different queries over one
  substrate* rather than individually engineered features. This is what SPP.3 (the projection family)
  hinted at, given a foundation.

## The guardrail — the Semantic Derivation Law

The Knowledge Partition Theorem applied to the model itself, stated as a law:

> **Semantic Derivation Law.** Every semantic property in PGS must declare its derivation source — a
> structural fact or a governed declaration — never an inference. Not `subdomain = consensus_pos` but
> `subdomain derived_from workflow-membership`; `authority derived_from governance artifact`;
> `visibility derived_from cross-boundary relation`.

A property that would require judgment is not a dimension; it is a *disposition* (worker-owned, DP4) —
**`relevance` is disposition, not a dimension.** Two consequences:

- **The Knowledge Partition Theorem becomes recursive.** Because every property carries its derivation, each
  layer can consume the layer below *deterministically*, without re-inferring — so the partition holds at
  every boundary: Protocol → Semantic Model → Projection → Worker → Judgment. Derivation-provenance is the
  coupling that makes "recursive" structural rather than aspirational.
- **Semantic correctness becomes inspectable.** You can audit the model's *reasoning* (each value's
  `derived_from`), not merely its values — an unusual property for a compiler.

## Derivation coverage — the architectural-maturity metric

Because every dimension declares its derivation, the fraction of artifacts for which a dimension is
*determined* (vs `undetermined`) is a per-dimension **maturity gradient** — not a bug report, a prioritized
roadmap. `domain 100% · kind 100% · subdomain 25% · authority 0%` reads directly as: *subdomain still leaks
implementation; invest there next.* Most systems discover missing metadata by crashing; PGS discovers it by
measuring semantic completeness, and the compiler itself reports where the next investment belongs. As each
dimension graduates from *inferred* to *compiler-emitted*, the model becomes progressively self-describing
and future projections thin out — they query a richer canonical model instead of recreating derivation logic.

## The milestone

PGS acquires a **canonical semantic model**, and the compiler becomes its **semantic engine**. Once the
model exists, every projection engine — present and future — is a query over one shared semantic substrate.
That is a stronger foundation than any single attribute (`subdomain-first-class` becomes one derived
dimension, not a milestone). It reframes the research narrative from "solve one missing attribute" to
"define the semantic foundation all projection engines share."

## v0 realization — the substrate exists

The Semantic Model is realized as a computed layer over the graph (`inspection/semantic_model.py`,
`pi snapshot semantic-model`): every artifact carries its semantic dimensions, each annotated with the
**derivation source** that produced it, and projections become `select(...)` queries over the one model.

- **The guardrail is executable, not aspirational.** A `Dimension` cannot exist without a derivation; a
  value the protocol does not determine is recorded as `undetermined`, never guessed; and no judgment
  dimension (e.g. `relevance`) is ever produced. The Knowledge Partition Theorem holds at the model level
  by construction.
- **v0 dimensions and their derivation sources** — domain (`structural:fqdn`) · kind
  (`structural:graph_node`) · subdomain (`structural:wf_membership`) · visibility
  (`structural:cross_subdomain_reference`). Projections as queries: `{domain, kind}`, `{subdomain}` work
  directly.
- **Derivation coverage is the next-enrichment signal.** domain + kind are fully determined; subdomain +
  visibility are determined only where the workflow-membership derivation reaches (a large `undetermined`
  remainder). That count is the honest, quantified case for making **subdomain a first-class artifact
  property in the compiler** — no longer a special case bolted onto a projection, but one dimension whose
  derivation graduates from *inferred via WF-membership* to *emitted by the compiler*.
- **A finding surfaced deterministically:** `visibility = public` is (nearly) empty — this system is
  *event-decoupled* (subdomains communicate through events/data, not cross-boundary functional calls), so
  it has no functional public surface. That is a true architectural property of the snapshot, reported by
  the model rather than assumed away — the same rigor as SPP.11c, one layer up.

## Ownership vs participation — two dimensions, one concept each

The first dimension to graduate from *inferred* to *compiler-emitted* revealed a distinction the inference
had conflated. "Subdomain" is not one dimension but two:

- **`owner_subdomain`** — single-valued, **immutable**, governed *ownership* (who OWNS the artifact). It is
  **compiler-emitted** into `artifact_index`, derived from the artifact's `module_path`
  (`pgs_<pkg>.registry.<subdomain>.<kind>`) — a governed structural declaration, read with zero inference.
  Immutable by construction: `module_path` is part of the immutable versioned artifact, so a consumer in
  another subdomain cannot drift ownership; re-homing changes `module_path` and therefore requires a *new
  version*. `None` for domain-level shared artifacts (pure transforms/side-effects/entities belong to the
  domain) and federation-level artifacts (constitution/topology) — correctly *not* subdomain-owned.
- **`participating_subdomains`** — multi-valued, computed *participation* (which subdomains functionally
  USE the artifact), by reachability over functional edges on top of ownership. Ownership ⊆ participation.

Projections choose the right one: Authority/Governance query *ownership*; Discovery/Impact/Transformation
query *participation*. Overloading them into a single "subdomain" would have re-introduced ambiguity — the
same "one dimension = one concept" discipline the DSD model is built on. (Java analogy: `Wallet` stays
owned by `wallet`; `consensus` importing it changes participation, never ownership.)

**A property this unlocked:** with ownership emitted and participation computed, `visibility` becomes real
— `public` = an owned artifact a *different* subdomain functionally uses (the Public Semantic Surface).
Where the event-decoupling finding earlier made cross-boundary surface look empty, the ownership/reachability
formulation surfaces it (≈46 public artifacts in the current snapshot). The `artifact_index` is query
metadata (not part of the snapshot identity), so emitting a new dimension is additive and leaves the
snapshot hash unchanged — a semantic dimension can graduate to compiler-emitted without a behavioral recompile.

# The Construction Compiler grounds on contracts — candidate capability contracts

The Construction Compiler (S8) is a deterministic back-end: it turns the S1–S7 Construction Projection into
candidate protocol artifacts a second, independent compiler (the Protocol Compiler) admits. Proving that
end-to-end forced a sequence of concepts about *where semantics live* — each one the same discipline seen
elsewhere in this ledger (one dimension = one concept; one authority; propagate, never invent).

## Candidate capability contracts — the unifying artifact (D4 dissolves, it does not relocate)

The first honest thing the pipeline exposed was a scaffolding file ("D4", `capability_interfaces.json`): a
hand-authored side-table of typed capability interfaces the Construction Compiler read to seed and
propagate types. It looked like "the missing type declarations." It was not. Interrogated against *what is
the authoritative source of a capability contract?*, "typed interfaces" turned out to be a **conflation of
three distinct jobs**, each with a different rightful home:

- **operation vocabulary + I/O field names** for *existing* capabilities — already declared in the CS/CT
  contract (`core.operations`, `core.policy.operations`) and already read from the compiled snapshot. Not
  missing; duplicated.
- **field types** for existing CS capabilities — the CS contract declares op I/O *names* but not *types*;
  the type belongs *in the contract*.
- **interface + machine binding** for *new* capabilities — the capability does not exist yet, so there is
  no contract to read.

The wrong fix is to relocate D4 to a nicer place (an S6b "typed-interface register" — which would make the
composition stage author *capabilities*, violating separation of concerns; the composition stage composes
capabilities, it does not define them). The right fix is to recognize the missing artifact for what it is:
not a typed-interface blob but a **candidate capability contract** — the *same artifact shape* that will
eventually live in the canonical registry. A new CT is not special; it is a CC/WF/IN/RB that simply does
not exist yet. So S8 emits candidate CT and IN contracts exactly as it emits candidate CCs, and **D4
dissolves**: existing capabilities are read from their contracts, new capabilities *are* candidate
contracts. Nothing is relocated, translated, or duplicated. This is the strongest possible end-state: the
Construction Compiler, Protocol Compiler, and Promotion all operate on one artifact shape.

**Contracts own semantics — there is exactly one authority.** D4's real sin was being a *second* authority
for something contracts already own; two authorities is the defect, independent of where the second one
sits. The candidate-capability-contract model collapses the two authorities back into one.

## The Compilation Unit: canonical + candidate, and the compiler cannot tell which is which

Admission runs in a **Compilation Unit** — a virtual federation workspace that mounts read-only copies of
every involved repository and overlays the candidates, so the Protocol Compiler answers "can I consume what
the Construction Compiler emitted?" **with zero mutation of any canonical repo** (`SINGLE_COMPILATION_CONTEXT`).
The Protocol Compiler does not know which contracts are canonical and which are candidate; it just compiles
the unit. After a PASS, **Promotion is administrative, not analytical** — it *applies an admitted Compilation
Unit to the canonical federation* (copies the candidate contracts into their owning repos, changing
*ownership*, not correctness) and never recompiles. The single authority for correctness stays the Protocol
Compiler's admission. (C-toolchain analogy: release ships the validated executable; it does not re-invoke
the compiler.) This also answers the testing objection directly: if S8 already emits the artifacts that get
promoted, the end-to-end test validates the *end-state*, and Promotion changes nothing but ownership — a far
stronger proof than testing a transitional shape that will later be replaced.

Two supporting mechanisms were needed and generalize cleanly:
- **Candidate governance overlays.** Declaring a new CT *legal* extends a governed `allowed_capability_transforms`
  surface (`CT_SURFACE_CLOSED`) — the ISA-spec "declare the new opcode" act. That surface delta is a
  *candidate governance artifact* overlaid inside the unit, never a canonical edit; only Promotion writes
  the surface. Editing the canonical surface to make admission pass is the same class of error as a
  false-pass — it mutates canonical truth before the artifact earns admission.
- **Mount-by-package, layout-agnostic.** Repos are heterogeneous (doubly-nested domain packages vs the
  singly-nested, namespace-package governance repo). The unit mounts the *importable package* under one
  synthetic root and shadows editable installs via `PYTHONPATH` — so a candidate compiles in the domain's
  real import context regardless of repository layout.

## Propagate, never invent — and TYPED_PORT as the forcing function

A compiler **propagates** types along dataflow; it does not **invent** them. `block → hash:string`,
`is_equal:boolean` are irreducible semantic decisions that must be *declared* on the capability's own
contract; the compiler flows them, but it may not conjure them. The construction graph enforces this
honestly: every required port that cannot trace a type back to a declared contract interface raises
`TYPED_PORT`, and any violation is **fatal** to admission. That fatality is a feature — scaffolding cannot
hide. It is precisely what proved D4 was doing three admission-critical jobs (removing its external-input
block raised five `TYPED_PORT`; removing its CS entries, one), and it is what guarantees that after
grounding, *every* typed port in an admitted artifact traces to a contract, not to a side-file.

A subtlety the forcing function exposed: a CS operation declares `[result_status, value]` — a **control**
field plus a **data** field. Type seeding must distinguish them and seed the produced field from the *data*
output (output minus control fields), which is exactly the simplification D4 had silently baked in by
declaring a single-output `{value: object}`. Grounding makes that rule explicit in the compiler instead of
implicit in scaffolding.

## Generate, never patch — the correction belongs at the authoring source

The op-vocabulary bug (a composition invoked `SET`/`GET` on a store whose governed vocabulary is
`WRITE`/`READ`) tempted a fix at three successive layers, each wrong: the projection JSON, the D4 side-file,
then the S6b design markdown. All three are *authoring outputs*; patching any of them usurps the authoring
authority and is overwritten by the next regeneration. The correction belongs at the **authoring source**,
and better still, the illegal op should be *unauthorable*: an **S6b oracle gate** reads the referenced CS
contract's `core.policy.operations` and rejects any step operation not in it — catching the ungrounded op at
design time (Gate-1) rather than at admission. The Protocol Compiler already catches it at admission; the
gate closes the **authoring-grounding gap** so the design converges before it ever reaches the back-end.
This is the thesis in miniature: construction converges only when design is grounded in the governed
vocabulary of the contracts it references.
