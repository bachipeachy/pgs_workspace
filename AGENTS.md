# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

**Full architectural reference:** `doc/pgs_field_manual_v2.md` — read that for doctrine, invariants, and cognitive restoration. This file covers operational guidance for the workspace only.

---

## Purpose

This is the **execution workspace** — the runtime working directory and the single entry point for experiencing Protocol-Governed Systems (PGS). It contains:
- `protocol_snapshot/` — compiled canonical artifacts (read-only input to runtime)
- `tokenized_snapshot/` — tokenized runtime projections (machine-oriented topology)
- `evidence_snapshot/` — compiler evidence projections (causality graph + views)
- `vocabulary_snapshot/` — aggregate semantic vocabulary (address space)
- `trust_snapshot/` — attestation and trust boundary projections
- `seeds/` — committed seed data (source of truth; copied to `data/` by bootstrap)
- `data/` — runtime data files (gitignored; generated at runtime)
- `scripts/` — operational scripts
- `traces/` — execution trace output (gitignored; written by runtime)

The workspace is NOT a source code repo. It is the **operational environment** where the runtime executes against a compiled snapshot.

---

## Commands

**Bootstrap (first time setup):**
```bash
cd scripts && ./bootstrap_pgs.sh            # default: --env local (editable installs from ~/pgs/)
cd scripts && ./bootstrap_pgs.sh --env remote  # published packages from PyPI
source .venv/bin/activate
pgs_runtime --help
```
`bootstrap_pgs.sh` installs eight sibling repos as editable installs into `.venv/`: the seven runtime repos (`pgs_runtime`, `pgs_governance`, `pgs_compiler`, `pgs_transport`, `pgs_capabilities`, `pgs_blockchain`, `pgs_ai_governance`) plus `pgs_change_mgmt` (the change-management engine — a Python package alongside its markdown templates/dossiers/docs). All repos must be siblings of this workspace directory. Use `--env remote` when installing from published PyPI packages instead of local source (`pgs_change_mgmt` is not on PyPI, so it installs from local source even under `--env remote`).

**Run the demo workflow end-to-end:**
```bash
source .venv/bin/activate
cd scripts && ./demo_sample_workflow.sh
```
Runs `blockchain::WF_REGISTER_ACTOR_UNVERIFIED_V0` twice, examines a trace, and prints data state — demonstrating idempotency and append-only event semantics.

**Run a workflow manually:**
```bash
pgs_runtime run \
  --wf blockchain::WF_REGISTER_ACTOR_UNVERIFIED_V0 \
  --payload <path-to-payload.json> \
  --data-root /absolute/path/to/pgs_workspace/data \
  --workspace .
```
`--data-root` MUST be an absolute path. Never use `./data` — the runtime does not infer relative paths.

**Examine a trace:**
```bash
pgs_runtime examine ./traces/<TRACE_ID>/<TRACE_ID>.jsonl
```

**Protocol inspection (`pi`) — query the compiled snapshot set (read-only):**
```bash
export PGS_WORKSPACE=/abs/path/to/pgs_workspace   # required — pi never guesses from cwd

pi artifact refs <fqdn>              # who references this artifact (consumers)
pi topology impact <fqdn> --json     # transitive consumer closure (change-mgmt evidence)
pi behavior_logic show <wf-fqdn>     # execution tree from *.graph.json
pi artifact source <fqdn>            # authoring Markdown from PPS snapshot
pi vocab search <term>               # FQDN search across all domains
pi validate --strict                 # CI gate: exit 1 unless VALID + zero violations
pi                                   # interactive shell (use <domain> to scope bare codes)
```
`pi` lives in `pgs_compiler` (the inspection library `pgs_compiler.inspection` is its core). It is strictly read-only and query-only: *pi answers questions; the compiler performs changes; the runtime performs execution.* Full taxonomy: `doc/pgs_cli_cheatsheet.txt`; doctrine: field manual §5.5.

**List available workflows (from snapshot):**
```bash
ls protocol_snapshot/artifacts/workflows/
```

**HTTP server (both domains):**
```bash
scripts/start_http_server.sh
```

---

## Compiler Build Commands

The compiler runs outside the workspace (in `pgs_compiler`), then syncs output to `protocol_snapshot/`.

```bash
# Phase Type A — per-structure compilation (run in order)
python -m pgs_compiler.cli compile --structure STRUCTURE_BUILD_PLATFORM_CONFIG_V0
python -m pgs_compiler.cli compile --structure STRUCTURE_BUILD_BLOCKCHAIN_CONFIG_V0
python -m pgs_compiler.cli compile --structure STRUCTURE_BUILD_AI_GOVERNANCE_CONFIG_V0

# Cross-structure aggregation happens in `build` (artifact_index/ emission) —
# the former Phase B vocabulary-aggregate compile step is retired; per-domain
# vocabulary is materialized in Phase A (S7).

# Full build: sync artifacts + conformance tests + mark snapshot valid
python -m pgs_compiler.cli build --workspace /abs/path/to/pgs_workspace

# Inspect compiled evidence (query without recompiling)
python -m pgs_compiler.cli inspect --structure STRUCTURE_BUILD_BLOCKCHAIN_CONFIG_V0 --artifact blockchain::WF_REGISTER_ACTOR_UNVERIFIED_V0
python -m pgs_compiler.cli inspect --structure STRUCTURE_BUILD_BLOCKCHAIN_CONFIG_V0 --upstream blockchain::CC_GENERATE_ACTOR_ID_V0
python -m pgs_compiler.cli inspect --structure STRUCTURE_BUILD_BLOCKCHAIN_CONFIG_V0 --family CONSTRUCTION
```

---

## Architecture

### Repo Ecosystem (layered)

```
pgs_governance      →  constitutional governance, federated boundaries, invariant enforcement
pgs_compiler        →  compiler pipeline, admissibility construction, conformance generation
pgs_transport       →  ingress/egress adapters (HTTP, CLI transport surfaces)
pgs_runtime         →  execution engine (pgs_runtime CLI)
pgs_capabilities    →  governed capability substrate (CT, CS implementations)
pgs_blockchain      →  blockchain domain (workflows, CCs, data model)
pgs_ai_governance   →  AI governance domain
pgs_change_mgmt     →  governed change management — SDLC pipeline from CR to Authoring Mandate
pgs_workspace       →  THIS REPO: snapshot + scripts + entry point
```

Dependency direction: `pgs_workspace` → domains → capabilities → runtime ← compiler ← governance
`pgs_change_mgmt` → `pgs_compiler` (validation) + `pgs_workspace` (PPS snapshot, read-only)

### The Nine Execution Concerns

All protocol artifacts belong to one of nine named execution concerns:

| Prefix | Name | Role | Group |
|--------|------|------|-------|
| `TI_` | Transport Ingress | Normalizes external input → canonical internal form | Boundary |
| `AC_` | Actor Context | Binds execution authority context | Authority |
| `IN_` | Intent | Declarative admission gate; validates payload before graph traversal | Authority |
| `WF_` | Workflow | Declarative execution topology graph; compile-time governed traversal | Authority |
| `CC_` | Capability Contract | Named DAG node; declares inputs, outputs, routing outcomes | Capability |
| `CT_` | Capability Transform | Pure computation; deterministic; zero side effects | Capability |
| `CS_` | Capability Side Effect | Controlled external state interaction; enumerated, bounded | Capability |
| `EV_` | Event | Control plane + observability; governance signaling | Observation |
| `TE_` | Transport Egress | Boundary projection only; formats internal results for external systems | Boundary |

**Orthogonal resolution:**

| Prefix | Name | Role |
|--------|------|------|
| `RB_` | Runtime Binding | Maps CT_ and CS_ declarations to concrete implementations; provides execution mapping, not authority |

### Execution Flow

```
External input
  → TI_ (boundary normalization)
  → IN_ (admission check — ACK or NACK)
  → WF_ (governed DAG traversal)
       → CC_1 → CT_/CS_ → outcome (SUCCESS | VIOLATION | ALREADY_EXISTS | ...)
       → CC_2 (inputs resolved via JSONPath: $.results.<CC_CODE>.<field>)
       → ...
  → TE_ (boundary projection)
  → Trace written to traces/<TRACE_ID>/
```

- Runtime is generic — it has no domain logic
- All behavior comes from the compiled snapshot
- Each CC declares a named outcome that routes the DAG; no runtime branching logic

### FQDN Format

```
<domain>::<ARTIFACT_CODE>_V<version>

Examples:
  blockchain::WF_REGISTER_ACTOR_UNVERIFIED_V0
  blockchain::CC_GENERATE_ACTOR_ID_V0
  capability_transforms::CT_PURE_GENERATE_ID_V0
  ai_governance::WF_GOVERN_AGENT_ACTION_V0

Governance artifacts use fb.* namespace:
  fb.constitution::CONSTITUTION_FEDERATION_BOUNDARY_V0
  fb.topology::CONSTITUTION_EXECUTION_TOPOLOGY_V0
```

**Filesystem separator:** `::` in code becomes `__` (double-underscore) in filenames:
```
blockchain__WF_REGISTER_ACTOR_UNVERIFIED_V0.json
```

### Snapshot Structure

```
protocol_snapshot/
  artifacts/
    workflows/                  # WF_ JSON
    capability_contracts/       # CC_ JSON
    capability_transforms/      # CT_ JSON
    capability_side_effects/    # CS_ JSON
    runtime_bindings/           # RB_ JSON
    intents/                    # IN_ JSON
    events/                     # EV_ JSON
    actors/                     # AC_ JSON
    layers/ invariants/ assertions/  # governance (compiled from all FB_* boundaries)
  artifact_index/
    index.json                  # FQDN → domain/structure/kind/paths/addresses (query metadata; consumed by pi)
    stores.json                 # entity-store ownership join (storage STRUCTURE × RB × evidence edges)
  behavior_logic/
    <WF_NAME>/
      <WF_NAME>.graph.json      # machine-readable DAG (behavior logic source of truth)
      <WF_NAME>.projection.png  # visual graph
```
Both `artifact_index/` projections enter the workspace only via `pgs_compiler.cli build` — never hand-placed.

### Trace Structure

Traces are organized by domain and subdomain (matching FB boundaries):

```
traces/
├── blockchain/
│   ├── identity/           # WF_REGISTER_ACTOR_UNVERIFIED_V0, WF_VERIFY_ACTOR_V0
│   ├── transaction/        # WF_SUBMIT_TRANSACTION_V0
│   ├── wallet/             # WF_CREATE_WALLET_V0
│   └── collatz_conjecture/ # WF_DEMO_COLLATZ_CONJECTURE_V0
└── ai_governance/
    ├── ai_licensing/       # WF_PROVISION_AI_LICENSING_V0, WF_DENY_PROVISION_V0, WF_AUTO_RECLAIM_V0
    └── agent_governance/   # WF_GOVERN_AGENT_ACTION_V0
```

Each execution writes to `traces/<domain>/<subdomain>/<TRACE_ID>/`:
- `<TRACE_ID>.jsonl` — append-only structured event log (input to `pgs_runtime examine`)
- `<TRACE_ID>.md` — human-readable summary
- `<TRACE_ID>.png` — execution path visualization

Trace IDs are deterministic — same inputs produce the same trace ID.
Domain/subdomain routing is declared via the `subdomain` field in each WF artifact.

### Data Structure

`data/` holds mutable runtime state organized by domain and subdomain (matching FB boundaries):

```
data/
├── blockchain/
│   ├── identity/
│   │   ├── registry/actors.json          # deduplicated actor registry
│   │   └── events/identity_events.jsonl  # actor lifecycle events
│   ├── transaction/
│   │   └── events/transaction_events.jsonl
│   ├── wallet/
│   │   ├── state/wallets.json
│   │   └── events/wallet_events.jsonl
│   └── collatz_conjecture/
│       └── collatz_results.json
└── ai_governance/
    ├── ai_licensing/
    │   ├── license_facts.json    # read-only seed data (from seeds/)
    │   ├── license_registry.json
    │   └── audit_log.jsonl
    └── agent_governance/
        ├── governance_actions.json
        └── governance_audit.jsonl
```

Paths are declared in RB artifacts (via `{{module_data_root}}/domain/subdomain/...`) and STRUCTURE artifacts (via `entity_stores`). Storage topology is a governance concern — never hardcode paths in runtime code.

---

## Core Doctrine

**Workspace is an execution environment, not a development environment.**

| Principle | Statement |
|-----------|-----------|
| Protocol Sovereignty | Protocol is the sole source of behavioral truth |
| Runtime Dumbness | Runtime enforces graph structure; has zero domain knowledge |
| Compile-Time Resolution | All behavior determined and validated before execution |
| Zero Inference | Nothing assumed, guessed, or defaulted — all paths declared explicitly |
| Fail Hard | Missing artifact → hard failure; no silent skip, no fallback |
| Snapshot Sovereignty | `protocol_snapshot/` is READ-ONLY; never edit by hand |
| CT Purity | CT_ implementations have zero side effects; CT may never call CS |
| No Ambient Authority | All authority originates exclusively from (AC, IN, WF, CC) declarations |
| Trace Output Only | Traces written by runtime; never used as input to any component |
| Determinism | Identical inputs → identical traces, always |

---

## Snapshot Rules (MANDATORY)

**`protocol_snapshot/` is READ-ONLY:**
- Contents are generated by the compiler (`pgs_compiler`)
- Never edit JSON artifacts inside `protocol_snapshot/` by hand
- Never write scripts that patch or mutate snapshot contents
- To change an artifact → change the protocol source and recompile

**Artifact identity:**
- All artifact filenames and references MUST use FQDN format (`domain::ARTIFACT_CODE_Vn`)
- No short names anywhere
- Versions are immutable — a behavior change requires a new version number

---

## Script Rules

**Scripts MUST:**
- Use explicit, declared paths (no `cwd`, no relative path guessing)
- Read from `protocol_snapshot/` only
- Write traces/output to `traces/` only
- Fail hard on missing artifacts

**Scripts MUST NOT:**
- Mutate `protocol_snapshot/`
- Use `sys.path` manipulation
- Use dynamic imports
- Hardcode absolute paths (use script-relative or env-var-driven paths declared explicitly)

---

## Trace Rules

**Execution traces are OUTPUT artifacts:**
- Written to `traces/` by the runtime
- Never used as input to compiler or protocol
- Never mutated by scripts
- Immutable once written (append-only trace log)

---

## No Hardcoded Paths

- All paths MUST be declared explicitly or derived from snapshot manifest
- No guessing, no relative traversal, no `../` hacks
- `--data-root` MUST be an absolute path, never inferred

---

## Workflow Rules (MANDATORY)

**Diagnose before fix — ALWAYS:**
1. State the root cause you've identified
2. List which files need to change and why
3. Identify any architectural concerns with the proposed change
4. **Wait for approval before implementing anything**

**Multi-file changes — plan first:**
- Present the complete list of files to be changed before starting any edits
- No scattered incremental edits — plan the full pass, then execute it

**Do NOT touch `protocol_snapshot/` contents directly. Recompile instead.**

---

## Environment Rules

- Do NOT run `pip install` — all dependencies are pre-installed in `.venv/`
- Do NOT run `pip`, `pip3`, or any package setup commands
- Dependencies are managed externally; assume they are available

---

## Forbidden Patterns

- Editing `protocol_snapshot/` artifacts by hand
- Using trace output as runtime input
- `sys.path` manipulation in scripts
- Hardcoded absolute paths
- Dynamic imports in operational scripts
- Guessing artifact locations via filesystem scan
- CT calling CS (breaks CT purity invariant)
- Role-branching or transport conditions in execution topology steps
- Runtime step injection or topology synthesis from payload/environment

---

## Final Invariant

Workspace MUST be:
- Snapshot-driven (runtime reads from snapshot, not protocol source)
- Trace-producing (execution output goes to `traces/`, nothing else)
- Path-explicit (no guessing, no traversal)

**Any deviation → operational violation.**

Add as a top-level rule under ## Core Rules or ## Important Conventions\n\nNever introduce new terminology, rename concepts, or deviate from established naming conventions without explicit user approval. When in doubt, use the exact terms found in existing project files.
Add under ## Workflow / Process Rules\n\nFollow the established change management workflow. Do not skip process steps (e.g., merging directly, running workflows without required flags). Ask before taking action if the process isn't clear.
Add under ## Multi-Repo Work\n\nWhen working across multiple repos or copies (local, test, workspace), always confirm which copy is being modified and verify sync status before proceeding.
Add as a new section ## PGS Glossary / Terminology\n\nPGS Project Glossary: EV_ = Event (not Evidence). Subdomains are flat peers (no primary/extended hierarchy). Use 'evidence' not 'tooling' for evidence-related naming. Refer to existing manifests for canonical terms.