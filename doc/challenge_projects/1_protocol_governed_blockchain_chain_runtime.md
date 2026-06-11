# Challenge Project: Protocol-Governed Blockchain Chain Runtime

**Difficulty:** &#11088;&#11088; (2/5 — Guided Implementation)

**Category:** Governed SDLC / Blockchain Execution Substrate

**Prerequisites:** Completed PGS onboarding (`doc/onboarding_build_first_workflow.md`). Comfort with the author → compile → sync → test loop. Familiarity with the nine execution concerns, snapshot sovereignty, and the FQDN artifact model. No blockchain expertise required — the chain design is already done for you.

---

## The Premise

Unlike the other two challenge projects, this one is **not open-ended**. The design is finished. A complete governed change dossier already exists for a new blockchain subdomain — `blockchain::chain` — that takes the platform from *proposing* blocks to *committing* them onto a canonical, hash-linked chain.

Every stage of the governed SDLC has been authored except the last one: **the protocol artifacts themselves do not exist yet.** Your job is to take the dossier — a real Change Request that advanced through Design Intent, an Authoring Mandate, and a pre-authoring Manifest — and *build it*. Author the artifacts, compile them into the snapshot, prove them with end-to-end tests, and close the CR.

This is the PGS authoring loop in miniature, on a real, non-trivial feature, with a known-good answer key (the dossier) and an objective definition of done (the tests pass and the CR closes).

---

## What This Is

A bounded implementation of a fully-specified CR. You will:

- **Author 21 new protocol artifacts** (Markdown source with `## Machine` YAML blocks) across three subdomains
- **Extend one workflow** and **update one event's metadata**
- **Compile and sync** the snapshot, watching `chain` appear as a new governed subdomain
- **Extend the existing E2E harness** (`scripts/test_blockchain_e2e.py`) to exercise chain
- **Close the CR** by populating the Stage 8 Authoring Manifest and flipping it to APPROVED

## What This Is NOT

- **Not a design exercise.** The Business Model, Governance Intent, and Design Intent are written. You are not deciding *what* to build — you are building *exactly what was mandated*, and learning why fidelity to the mandate matters.
- **Not a blockchain research project.** V0 is a single canonical chain: no forks, no reorgs, no finality gadget. Those are explicitly deferred (see the Manifest's Future CR Candidates).
- **Not a snapshot hand-edit.** You never touch `protocol_snapshot/`. You author source in `pgs_blockchain`, recompile, and let the build sync.

---

## The Architecture

The chain subdomain adds two workflows and three stores, and wires commitment into the existing consensus slot loop.

```
WF_INITIALIZE_CHAIN_V0  (one-time genesis bootstrap)
  IN admission → single-genesis check → genesis actor → MINT wallet
  → initial mint → genesis validator → genesis block → genesis chain
  ref → init chain state → EXIT_SUCCESS

WF_COMMIT_BLOCK_V0  (per committed block)
  IN admission → read head (CHAIN_STATE) → read proposed block (BLOCKS)
  → verify eligibility (PROPOSED + sequential round) → mark canonical
  → append linked chain ref + record EV_BLOCK_COMMITTED_V0 → advance head

WF_PROCESS_SLOT_V0  (EXTENDED — orchestration)
  ... → CC_INVOKE_BLOCK_PROPOSAL_V0 SUCCESS
      → CC_INVOKE_BLOCK_COMMITMENT_V0  (NEW: gateway → WF_COMMIT_BLOCK_V0)
      → CC_ADVANCE_SLOT_CLOCK_V0 → ...

Stores (STRUCTURE_BLOCKCHAIN_CHAIN_STORAGE_V0)
  CHAIN         append-only journal of block references
  CHAIN_STATE   single mutable record — the canonical head authority
  CHAIN_EVENTS  append-only chain lifecycle facts
```

**Three invariants govern the whole feature:**

- **Single-head:** a candidate block commits only if its `round_id == CHAIN_STATE height + 1` and it is in `PROPOSED` status; linkage is constructed at commit.
- **Exactly-once genesis:** `CC_CHECK_CHAIN_NOT_INITIALIZED_V0` gates initialization; a second run terminates `ALREADY_EXISTS` with no side effects.
- **Store ownership:** all `BLOCKS` writes go through **block-owned** CCs. Chain CCs write only chain stores. A cross-subdomain write is a hard governance violation, no exceptions.

---

## What You're Given (the answer key)

The complete dossier lives in the change-management repo:

```
pgs_change_mgmt/change_mgmt/dossiers/blockchain/chain/
  1_change_request_blockchain_chain_v0.md   — problem & scope
  2_domain_model_…  3_analysis_loop_…  4_business_model_…  5_business_intent_…
  6_governance_intent_…   (WHERE artifacts live, ownership)
  6b_design_intent_…      (HOW — per-artifact pipelines, topology, schemas)
  7_authoring_mandate_…   (the exact build order — Waves 1-5, critical path)
  8_authoring_manifest_…  (the close-out checklist & reconciliation tables)
```

Read **Stage 6b (Design Intent)** for the per-artifact specification and **Stage 7 (Authoring Mandate)** for the dependency-ordered build sequence. Stage 8 is your definition of done.

> **Note on Stage 7 vs Stage 8 timing.** The **Authoring Mandate (Stage 7) drives the build** — it is finalized *before* any artifact is authored and is the input to implementation. The **Authoring Manifest (Stage 8) records the result** — it is created as an empty *pre-authoring baseline* (its as-built sections marked `PENDING`), then populated *during and after* implementation and finalized at **Stage 9 — CR Closure** (`DRAFT → APPROVED`). So the mandate is written ahead of the work; the manifest's substance is filled in behind it. The early baseline exists so the post-build as-designed-vs-as-built reconciliation diffs against what was actually planned, not a reconstruction from memory.

---

## The Build — follow the Authoring Mandate

**23 authoring actions:** 21 NEW + 1 EXTEND + 1 metadata UPDATE. Source artifacts are Markdown with a `## Machine` YAML block — mirror existing precedents (`CC_INVOKE_BLOCK_PROPOSAL_V0` for gateway CCs, `STRUCTURE_BLOCKCHAIN_ORCHESTRATION_STORAGE_V0` for the chain STRUCTURE).

Where the files go (all under `pgs_blockchain/pgs_blockchain/registry/`):

| Location | Artifacts |
|---|---|
| `chain/` (new subdomain dir) | 2 WF, 2 IN, 2 RB, 1 CT, 10 CC, 1 STRUCTURE |
| `block/capability_contracts/` (exists) | `CC_FORM_GENESIS_BLOCK_V0`, `CC_MARK_BLOCK_CANONICAL_V0` |
| `orchestration/capability_contracts/` (exists) | `CC_INVOKE_BLOCK_COMMITMENT_V0` |
| `orchestration/workflows/WF_PROCESS_SLOT_V0.md` | EXTEND — insert commitment node |
| `block/events/EV_BLOCK_COMMITTED_V0.md` | UPDATE metadata only (reuse the existing event) |

Build the waves in order (foundational primitives → CCs → WFs → bindings → slot extension), then run the standard compile/build pipeline:

```bash
# clean
~/pgs/pgs_compiler/scripts/clean_pycache.sh
~/pgs/pgs_compiler/scripts/clean_outputs_dir.sh
~/pgs/pgs_compiler/scripts/clean_compiled_artifacts.sh

# compile each structure, then build + project
python -m pgs_compiler.cli compile --structure STRUCTURE_BUILD_PLATFORM_CONFIG_V0
python -m pgs_compiler.cli compile --structure STRUCTURE_BUILD_BLOCKCHAIN_CONFIG_V0
python -m pgs_compiler.cli compile --structure STRUCTURE_BUILD_AI_GOVERNANCE_CONFIG_V0
python -m pgs_compiler.cli build     --workspace ~/pgs/pgs_workspace
python -m pgs_compiler.cli build-pps --workspace ~/pgs/pgs_workspace
```

The chain subdomain is **auto-discovered** — the blockchain build config scans the registry tree recursively, so no governance or structure edit is needed. Success looks like `chain` appearing in the PPS subdomain list and conformance staying green.

---

## Testing & Definition of Done

Extend `pgs_workspace/scripts/test_blockchain_e2e.py` to cover chain, and run the six scenarios from the Manifest:

| # | Scenario | Workflow | Expected |
|---|---|---|---|
| 1 | Genesis init — happy | `WF_INITIALIZE_CHAIN_V0` | `EXIT_SUCCESS` |
| 2 | Genesis re-init | `WF_INITIALIZE_CHAIN_V0` (again) | `ALREADY_EXISTS` |
| 3 | Block commit — happy | inside the slot simulation | `EXIT_SUCCESS` |
| 4 | Non-sequential round | `WF_COMMIT_BLOCK_V0` (wrong `round_id`) | `VIOLATION` |
| 5 | Unknown block | `WF_COMMIT_BLOCK_V0` (bad `block_id`) | `NOT_FOUND` |
| 6 | Determinism | re-run scenario 1 or 3 | identical `TRACE_ID` |

Genesis init must run **before** the simulation (the slot loop's commit step reads `CHAIN_STATE`). The happy-path commit is exercised *inside* the simulation once `WF_PROCESS_SLOT_V0` is extended. Add a chain diagnostics block that reads `CHAIN_STATE` head, `CHAIN` length, and `CHAIN_EVENTS`.

**The CR is closed when** (Stage 8 §10): all 21 artifacts are compiled into `protocol_snapshot/`; all six scenarios produce the expected decision; traces are verified (non-empty, correct outcome, correct denial reason); the determinism invariant holds; no artifact outside the declared scope was modified. Then populate the Manifest's PENDING sections and flip its status `DRAFT → APPROVED`.

---

## Estimated Scale

| Area | Count |
|---|---|
| New workflows (WF_) | 2 |
| New intents (IN_) | 2 |
| New runtime bindings (RB_) | 2 |
| New capability contracts (CC_) | 13 |
| New capability transform (CT_) + Python impl + TEST_DATA | 1 (×3 files) |
| New storage structure (STRUCTURE_) | 1 |
| Workflow extension / event metadata update | 2 |
| Test harness extension | 1 script |
| **Total authoring actions** | **23** |

Small by PGS standards — but every artifact is governed, every path is declared, and nothing passes the build unless it is admissible.

---

## Hard Problems (the things that catch people)

- **It's Markdown, not JSON.** Source artifacts are `.md` with a `## Machine` YAML block. Never edit `protocol_snapshot/` — author source and recompile. The snapshot is read-only by doctrine.
- **The CT is real code.** `CT_PURE_COMPARE_ROUND_IDS_V0` needs a Python implementation module *and* a `TEST_DATA` artifact, and it must pass conformance. CTs are pure and deterministic — no side effects, never call a CS.
- **Reuse, don't recreate.** `EV_BLOCK_COMMITTED_V0` already exists. The mandate is a *metadata* update, not a new event. Always check the snapshot inventory before authoring.
- **Events are facts, not triggers.** Commitment is invoked by the slot workflow via an orchestration-owned **gateway CC** — not by anything consuming `EV_BLOCK_COMMITTED_V0`. Workflow chaining uses gateway CCs; events only record.
- **Hash-at-commit.** Proposed blocks carry no hashes. Commitment computes `block_hash` (keccak256 reuse) and links `previous_block_hash` from the `CHAIN_STATE` head. Verify a producing CC's outputs before consuming its fields.
- **One store, one owner.** Chain CCs may not write `BLOCKS`; that's why the two block-owned dependency-gap CCs exist. Get this wrong and the compiler (rightly) refuses you.
- **Genesis vs. seeds.** `WF_INITIALIZE_CHAIN_V0` bootstraps actor/wallet/mint/validator through gateway sub-workflows. Decide how it coexists with pre-seeded genesis state — the idempotent `ALREADY_EXISTS` paths exist for exactly this reason.

---

## The Core Question

Can a developer take a **finished governance dossier** and reproduce a working, admissible feature — with no design latitude, only fidelity to the mandate — and have the compiler and the trace evidence confirm correctness?

If yes, then the PGS SDLC delivers its central promise: **the design is the contract, the build is mechanical, and admissibility is provable.** Two developers handed the same dossier should converge on the same governed behavior — not because they coordinated, but because the protocol left no room to diverge.

---

## Who Should Attempt This

Anyone learning PGS who wants to experience the full governed loop — author, compile, admit, trace, close — on a real feature without having to design it first. It is the natural next step after onboarding, and the on-ramp to the open-ended challenge projects. If you can close this CR, you understand how PGS turns intent into admissible execution.

---

*PGS Workspace: [github.com/bachipeachy/pgs_workspace](https://github.com/bachipeachy/pgs_workspace)*

*Field Manual: `doc/pgs_field_manual_v0.md`*

*Onboarding: `doc/onboarding_build_first_workflow.md`*

*Dossier: `pgs_change_mgmt/change_mgmt/dossiers/blockchain/chain/`*
