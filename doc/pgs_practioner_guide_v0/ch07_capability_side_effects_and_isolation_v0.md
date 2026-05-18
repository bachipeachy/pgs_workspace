# Chapter 7 — Capability Side Effects and Isolation

Chapter 6 proved that pure computation is governed — atoms and molecules execute as deterministic, side-effect-free transforms. But a system that cannot write to storage, register state, or record events cannot do useful work. The CT\_ layer computes. Something else must mutate.

This chapter opens the CS\_ layer and answers: **How does a protocol-governed system perform world mutation — persistence, registration, event recording — without compromising the determinism and auditability guarantees that the CT\_ layer provides?**

The answer is isolation through declaration. Every side effect in PGS is declared in a capability contract, routed through a registered runtime binding, and executed by a swappable runtime implementation. The chapter examines the three persistent runtime types — mutable JSON stores, append-only event logs, and symbolic registries — showing how each enforces its own structural invariants (last-write-wins, immutability, tombstone-based deletion). It introduces runtime bindings (RB\_) as the indirection layer that maps abstract capability codes to concrete storage backends, making the same workflow portable across environments without changing a single governance artifact. By the end, the reader will understand why the CT/CS constitutional boundary is not a design preference but a structural prerequisite — it is what makes mutation visible, bounded, and replay-aware.

* * *

## 7.1 — The Engineering Objective

Chapter 6 established that pure computation is governed. Atoms and molecules execute as side-effect-free transforms — given identical inputs, they produce identical outputs, always. The CT executor resolves symbols, invokes functions, and collects results. It does not write to a database. It does not append to a log. It does not register state. Pure computation computes. It does not mutate.

But systems must mutate the world. A wallet must be persisted. An actor must be registered. An event must be recorded. If the system cannot write, it cannot do useful work. The question is not whether mutation happens — it is whether mutation is governed or wild.

**The Task:** Show how PGS performs world mutation — writing to storage, appending event logs, registering state — without violating the determinism guarantees established in Chapter 6 for CT\_.

**The Constraint:** No side effects inside CT\_. All mutation must be declared in a capability contract (CC\_). All mutation must be routed through a registered runtime binding (RB\_). The execution engine remains domain-agnostic — it dispatches operations without knowing what a wallet is, what an actor is, or why an event matters.

In the application-centric approach, service methods write to databases, call APIs, and append logs mid-computation — all invisible to the caller. A "validation helper" that appears pure may write an audit record as a side effect. A "lookup function" may update a cache on every call. The mutation surface is invisible and unbounded. When a production incident occurs, the first question is always: "What else did this function touch?" The answer requires reading every line of implementation — and every line of every function it calls.

In PGS, mutation is declared. A CS\_ capability performs a single, bounded side effect through a governed operation on a declared storage target. The mutation surface is not discovered by reading code — it is visible by reading governance artifacts. The distance between "what does this system write?" and the answer is one artifact.

* * *

## 7.2 — The CT/CS Constitutional Boundary

Before examining CS\_ artifacts, the reader must understand the boundary they cross.

**Invariant I-S1 — Transform Purity:** CT\_ artifacts may not perform I/O or state mutation. This was established in Chapter 6 and enforced by the CT executor. A CT\_PURE atom that attempts file access is rejected at validation.

**Invariant I-S2 — Declared Mutation:** All CS\_ execution must be explicitly declared in a capability contract (CC\_). A side effect that does not appear in a CC\_ pipeline does not execute. There is no mechanism for the engine to perform undeclared mutation.

**Invariant I-S3 — Binding Isolation:** CS\_ capabilities execute only through registered runtime bindings (RB\_). No direct infrastructure calls are permitted. The engine does not instantiate database connections, open files, or call APIs. It dispatches to a runtime host that the RB\_ artifact declared.

These three invariants create a constitutional boundary:

```
CC_ Pipeline:  [CT_ ... CT_] → [CS_ ... CS_] → EXIT
                 │                │
                 │                └─ Mutation: declared, bound, traced
                 └─ Pure: no I/O, no state, deterministic
```

The boundary is architectural, not conventional. Crossing from CT\_ to CS\_ requires CC\_ orchestration. No artifact may mix the two. A CT\_ atom cannot invoke a CS\_ operation. A CS\_ step cannot be embedded inside a molecule. The CC\_ pipeline is the only artifact that orchestrates both — and it declares them as distinct, ordered steps.

* * *

## 7.3 — The CS Capability Model

**Definition:** A CS\_ capability performs a bounded side effect through a declared operation on a governed storage target.

**Key Properties:**

1. **Explicit operation.** Every CS\_ step declares its operation by name: REGISTER, WRITE, APPEND, READ, RESOLVE. The operation is dispatched by exact name match — `op.lower()` must correspond to a method on the runtime host class. There are no wildcard operations, no dynamic dispatch, no "execute whatever the payload says."
2. **Explicit input binding.** Every field the CS\_ operation receives is resolved from the CC\_ pipeline state. Inputs come from the workflow payload (`$.inputs.field`), from prior step outputs (`$.results.STEP_CODE.field`), or from literal values declared in the binding. There are no implicit parameters.
3. **Explicit result\_status.** Every CS\_ operation returns a `result_status` — SUCCESS, NOT\_FOUND, ALREADY\_EXISTS, VIOLATION, or BACKEND\_ERROR. There are no void operations. There are no silent failures. The CC\_ pipeline routes on result\_status to decide whether to continue or exit.

The system provides six CS\_ runtime types. Each serves a distinct storage or interaction pattern.

### CS\_REGISTRY\_V0 — Stable Indirection

A registry maps symbolic keys to storage locations. It provides stable indirection — a name that does not change even when the underlying storage address does.

**Operations:**

| Operation | Input | Output | Semantics |
|:----------|:------|:-------|:----------|
| REGISTER | key, target\_cs, target\_ref | address, result\_status | Create mapping. Fails if key exists |
| RESOLVE | key\_or\_address | target\_cs, target\_ref, result\_status | Lookup by key or address |
| EXISTS | key\_or\_address | exists (bool), result\_status | Check existence |
| DEREGISTER | key\_or\_address | result\_status | Tombstone deletion |

**Storage mechanics:** Append-only JSONL file. Each registration appends a record with a deterministic UUID-based address. Deletion appends a tombstone record (`tombstone: true`). Resolution reads the last non-tombstoned record per key. The append-only format means every registration is an immutable historical fact — even deletions are recorded, not erased.

### Example 7.1 — CS\_REGISTRY\_V0 in a CC\_ Pipeline

From the capability contract CC\_PERSIST\_VERIFIED\_ACTOR\_V0:

*(The full artifact is provided in Appendix B, Example 7.1.)*

**Analysis:**

- **The mutation surface is fully visible.** The binding declares exactly what this step does: REGISTER with a key, a target\_cs, and a target\_ref. An auditor reads three lines and knows the complete side effect. No code inspection required.
- **Result routing is explicit.** SUCCESS continues the pipeline. ALREADY\_EXISTS, VIOLATION, and BACKEND\_ERROR exit. The CC\_ pipeline does not guess what to do on failure — the governance artifact declares it.
- **Output binding is direct.** CS\_ results are returned directly — `$.result_status` and `$.address` — not wrapped in a `.value` envelope. This differs from CT\_ result wrapping (Chapter 6) and matters for output binding paths, as Section 7.5 will show.

### CS\_MUTABLE\_JSON\_V0 — Key-Addressable State

A mutable JSON store provides read-write access to key-addressable records. It is the simplest persistence model: one JSON file, last-write-wins semantics.

**Operations:**

| Operation | Input | Output | Semantics |
|:----------|:------|:-------|:----------|
| WRITE | key, value | result\_status | Create or overwrite record |
| READ | key | value, result\_status | Retrieve record |
| DELETE | key | result\_status | Remove record |
| EXISTS | key | exists (bool), result\_status | Check existence |
| LIST\_KEYS | (none) | keys (array), result\_status | Enumerate all keys |

**Storage mechanics:** Single JSON file. The entire file is loaded on each operation and saved atomically — write to a temporary file, fsync, then atomic rename. This prevents corruption from partial writes. The trade-off is explicit: simplicity over concurrency. For high-throughput concurrent access, a different CS\_ runtime type would be authored.

### Example 7.2 — CS\_MUTABLE\_JSON\_V0 in a CC\_ Pipeline

From the capability contract CC\_RESERVE\_NONCE\_V0, the CS step that persists an updated wallet record:

*(The full artifact is provided in Appendix B, Example 7.2.)*

**Analysis:**

- **CT computes, CS persists.** The prior CT step (`CT_PURE_INCREMENT_WALLET_NONCE_V0`) computed the updated wallet record and the new nonce — purely, deterministically. This CS step writes the result to storage. The separation is absolute: computation produces no side effects; persistence performs no computation.
- **The value being written is fully resolved.** The `value` input references the prior CT step's output. The expression resolver traverses the pipeline state to produce the concrete record. The CS runtime receives a complete value — it does not compute, transform, or interpret it.
- **Output forwarding.** The CS step's outputs include `nonce` — but this value comes from the prior CT step (`$.results.CT_PURE_INCREMENT_WALLET_NONCE_V0.nonce`), not from the CS operation itself. This is output forwarding: the last step in a CC\_ pipeline determines the CC\_ result, so earlier step outputs must be forwarded through the final step's output bindings if they are needed downstream.

### CS\_APPENDONLY\_JSONL\_V0 — Immutable Event Streams

An append-only JSONL store records immutable events. Records can be added but never modified or deleted.

**Operations:**

| Operation | Input | Output | Semantics |
|:----------|:------|:-------|:----------|
| APPEND | record, stream\_id (optional), actor\_id (optional) | record\_id, sequence\_number, result\_status | Append record with auto-generated ID |
| READ\_ALL | stream\_id (optional filter) | entries (array), result\_status | Retrieve all records |

**Storage mechanics:** Each appended entry is enriched with a `record_id` (timestamp + sequence), a `sequence_number`, and a `timestamp`. The file is opened in append mode — prior records cannot be modified. This provides a structural audit trail: every event is an immutable fact.

### Example 7.3 — CS\_APPENDONLY\_JSONL\_V0 in a CC\_ Pipeline

From the capability contract CC\_APPEND\_ACTOR\_EVENT\_V0:

*(The full artifact is provided in Appendix B, Example 7.3.)*

**Analysis:**

- **Nested dict resolution.** The `record` input is a nested dictionary with fields resolved from the pipeline state. The expression resolver recursively resolves `$.inputs.event_type`, `$.inputs.actor_id`, and `$.inputs.data` — producing a complete record before the CS runtime receives it. The runtime appends; it does not assemble.
- **Append-only guarantees are structural.** The AppendOnlyJsonlRuntime opens the file in append mode. There is no `UPDATE` operation. There is no `DELETE` operation. Prior records are immutable by construction — the runtime class does not provide methods to modify them.
- **Event streams are filterable.** The optional `stream_id` on both APPEND and READ\_ALL enables logical partitioning within a single JSONL file. Events for different actors or different workflows coexist in the same file but can be filtered independently.

### CS\_SEND\_EMAIL\_V0 — External Notification

Delivers an email notification to a declared recipient. This CS\_ type represents the pattern for external communication side effects: the operation is bounded, the recipient and content are declared as inputs, and the runtime handles delivery through a configured transport (SMTP, API, or stub for testing).

**Operations:**

| Operation | Input | Output | Semantics |
|:----------|:------|:-------|:----------|
| SEND | to, subject, body | message\_id, result\_status | Deliver email via configured transport |

**Design note:** `CS_SEND_EMAIL_V0` is the canonical example of how external I/O fits the CS\_ model. The workflow does not know how email is delivered. The runtime binding maps the CS\_ code to the actual transport. Swapping from SMTP to an API requires only an RB\_ binding change — no workflow or CC\_ modification.

### CS\_WORKFLOW\_GATEWAY\_V0 — Cross-Workflow Invocation

Invokes another workflow as a governed side effect, enabling workflow composition without coupling. One workflow can trigger another while keeping the governance boundary explicit — the invoked workflow executes as an independent governed operation with its own trace.

**Operations:**

| Operation | Input | Output | Semantics |
|:----------|:------|:-------|:----------|
| INVOKE | workflow\_code, payload | trace\_id, result\_status | Trigger governed sub-workflow |

**Design note:** `CS_WORKFLOW_GATEWAY_V0` is the cross-workflow coordination primitive. It is how PGS composes workflows without creating hidden couplings. The invoking workflow declares the target workflow code; the gateway resolves and dispatches it. The sub-workflow's execution is fully traced and governed independently.

### CS\_NAME\_REGISTRY\_V0 — Name Service

Provides a domain-scoped name registry that maps logical names to structured records. Used by name service infrastructure to support stable FQDN resolution within the runtime.

**Operations:**

| Operation | Input | Output | Semantics |
|:----------|:------|:-------|:----------|
| REGISTER | name, record | result\_status | Register a named record |
| RESOLVE | name | record, result\_status | Look up a registered name |
| EXISTS | name | exists (bool), result\_status | Check registration status |

**Design note:** `CS_NAME_REGISTRY_V0` is structurally similar to `CS_REGISTRY_V0` but operates at the naming layer — it maps logical FQDN names to their structural records rather than symbolic keys to storage addresses. This separation keeps domain-level registry operations distinct from infrastructure-level name resolution.

* * *

## 7.4 — Runtime Bindings (RB\_)

**Definition:** An RB\_ artifact binds abstract capability codes — both CS\_ (Capability Side Effects) and CT\_ (Capability Transforms) — to their concrete runtime host classes and configurations. It is the symmetric indirection layer between what a CC\_ pipeline declares and how the system fulfills it. Chapter 6 noted that CT\_ atoms are resolved via RB\_ at startup; Section 5.3 explained the mechanism. This section focuses on how RB\_ artifacts are authored and what they declare for the CS\_ layer, which is typically where environment-specific configuration (storage paths, transport configs) lives.

### Example 7.4 — RB\_CAPABILITY\_BINDINGS\_V0

From the blockchain module's runtime binding artifact:

*(The full artifact is provided in Appendix B, Example 7.4.)*

**Key Properties:**

1. **Abstract-to-concrete mapping.** Each CS\_ code maps to a host class and a storage policy. `CS_ACTOR_EVENTS_V0` maps to `AppendOnlyJsonlRuntime` with a specific file path. The CC\_ pipeline declares "append to CS\_ACTOR\_EVENTS\_V0." The RB\_ artifact declares "CS\_ACTOR\_EVENTS\_V0 is an AppendOnlyJsonlRuntime at this path." The pipeline does not know the path. The runtime does not know the pipeline.
2. **Parameter substitution.** The `parameters` array declares template variables. `{{module_data_root}}` is resolved at load time from the path registry — the constitutional single source of truth for all filesystem paths (Chapter 3). The RB\_ artifact does not hardcode absolute paths. It declares parameterized paths that the runtime loader resolves.
3. **Domain-scoped binding.** Each module provides its own RB\_ artifact. The blockchain module binds its CS\_ codes to its storage locations. A different module binds its own CS\_ codes to its own storage. There is no cross-domain leakage — a CS\_ code bound in one module cannot be resolved from another module's binding.
4. **Closed runtime class registry.** The runtime loader maps host names to a fixed set of runtime classes: `MutableJsonRuntime`, `RegistryRuntime`, `AppendOnlyJsonlRuntime`, `SendEmailRuntime`, `WorkflowGatewayRuntime`, `NameRegistryRuntime`. CT\_ codes bind to `PureTransformRuntime` or equivalent transform-dispatch classes. A host name that does not appear in this registry is rejected. There is no plugin system, no dynamic class loading, no reflection-based discovery.

### Binding Resolution Flow

The runtime loader processes the RB\_ artifact at workflow bootstrap:

```
RB_ artifact loaded
  → Parameter substitution ({{module_data_root}} → concrete path)
  → For each CS_ code:
      → Look up host class in closed registry
      → Instantiate runtime with policy (storage path)
      → Register in CapabilityRegistry
  → CapabilityRouter wraps registry for pipeline dispatch
```

When a CC\_ pipeline encounters a CS\_ step, the capability router resolves the CS\_ code through the registry, retrieves the runtime instance, and dispatches the declared operation. The engine never interprets what the operation means. It dispatches `op="REGISTER"` to a runtime that has a `register()` method. The method name must match exactly — `op.lower()` is called as `getattr(runtime_engine, op.lower())`. There is no fuzzy matching, no alias resolution, no fallback.

* * *

## 7.5 — The CC\_ Pipeline: CT/CS Integration

The capability contract pipeline orchestrates both CT\_ and CS\_ steps in a declared sequence. The CC\_ pipeline order is authoritative at authoring time, but execution order is enforced by the compiled DAG generated by the builder (Chapter 4), not by runtime interpretation of JSON array order. The pipeline array declares intent; the compiled artifact governs execution. The critical integration detail is how results flow between steps — and how CT\_ and CS\_ results differ.

### Example 7.5 — Mixed CT+CS Pipeline

From CC\_REGISTER\_ACTOR\_KYC\_V0 — a pipeline that computes an identifier (CT\_) then registers it (CS\_):

*(The full artifact is provided in Appendix B, Example 7.5.)*

### The CT/CS Result Wrapping Distinction

This pipeline reveals a critical structural difference in how the CC\_ pipeline handles CT\_ and CS\_ results:

**CT\_ steps:** The pipeline wraps CT\_ return values as `{"value": <ct_output>, "result_status": "SUCCESS"}`. CT\_ returns pure values — including structured data that may internally represent success or failure conditions. The pipeline maps those values to protocol-level `result_status` using the binding's `on_ct_result` declaration. Output bindings must use `$.capability_result.value.field` to reach the actual computation output.

**CS\_ steps:** The runtime returns results directly — `{"result_status": "SUCCESS", "address": "ADDR_xyz"}`. There is no `.value` wrapper. Output bindings use `$.capability_result.field` to reach the result fields.

| Aspect | CT\_ Steps | CS\_ Steps |
|:-------|:-----------|:-----------|
| Result wrapping | `{"value": <output>, "result_status": ...}` | Direct: `{"result_status": ..., field: ...}` |
| Output binding path | `$.capability_result.value.field` | `$.capability_result.field` |
| result\_status source | From `on_ct_result` declaration | From runtime's execute() return |
| Executor | CT-IR executor (symbol resolve + atom dispatch) | Capability router (op dispatch to runtime) |

This distinction is not arbitrary. CT\_ is pure computation — it produces values, not protocol status codes. The pipeline is responsible for interpreting those values into protocol-level result statuses via `on_ct_result`. CS\_ is a governed operation — it natively returns result statuses because its contract with the system includes them. The wrapping reflects the architectural difference between computation and interaction.

### Cross-Step Data Flow

In the example above, the CS\_ step's `key` input binds to `$.results.CT_PURE_GENERATE_ID_V0.kyc_key` — the resolved output of the prior CT\_ step. The pipeline accumulates step outputs in a `results` dictionary keyed by capability code. Each step can reference any prior step's resolved outputs.

**Output forwarding rule:** Only the last step's resolved outputs become the CC\_ result. If the CC\_ needs to expose values from earlier steps, the last step's output bindings must forward them. In Example 7.2 (CC\_RESERVE\_NONCE\_V0), the final CS\_ step forwards `nonce` from the prior CT\_ step: `"nonce": "$.results.CT_PURE_INCREMENT_WALLET_NONCE_V0.nonce"`. Without this forwarding, the nonce would be lost — it was computed by the first step but the CC\_ result contains only the last step's outputs.

* * *

## 7.6 — Validation and Failure Surface

The CS\_ layer has its own failure surface — distinct from governance validation (Chapter 3), compilation (Chapter 4), runtime dispatch (Chapter 5), and transform execution (Chapter 6).

### CS Validation Checks

| Step | Check | Failure Condition |
|:-----|:------|:------------------|
| 1 | Binding resolution | CS\_ code not found in RB\_ registry |
| 2 | Path resolution | Storage path template `{{param}}` unresolvable |
| 3 | Operation dispatch | Operation name does not match any runtime method |
| 4 | Input resolution | Required input expression resolves to None |
| 5 | Runtime I/O | Storage file corrupt, inaccessible, or locked |
| 6 | Result status | CS returns classified error (NOT\_FOUND, VIOLATION, BACKEND\_ERROR) |

### Broken Example: Missing Runtime Binding

A CC\_ pipeline references `CS_AUDIT_LOG_V0`, but no RB\_ artifact binds this code:

```
CC PIPELINE FAILURE
  Contract:    CC_LOG_ACTIVITY_V0
  Step:        CS_AUDIT_LOG_V0
  Check:       Binding resolution
  Detail:      Capability code "CS_AUDIT_LOG_V0" not found in registry.
               No runtime binding declares this CS_ code.
  Resolution:  Add CS_AUDIT_LOG_V0 to the module's RB_ artifact
               with a host class and storage policy.
```

The pipeline does not silently skip the step. It does not fall back to a default logger. It fails immediately with a classified diagnostic. The failure names the contract, the step, the check, and the resolution.

### Broken Example: Storage Path Failure

An RB\_ artifact binds CS\_WALLET\_STATE\_V0 to a path that does not exist:

```
CS EXECUTION FAILURE
  Capability:  CS_WALLET_STATE_V0
  Operation:   WRITE
  Check:       Runtime I/O
  Detail:      Storage backend error at "/nonexistent/path/wallet_state.json"
  Status:      BACKEND_ERROR
  Resolution:  Verify the module_data_root parameter resolves to an
               existing directory. Check path_registry configuration.
```

The runtime catches the I/O error and returns `result_status: "BACKEND_ERROR"`. The CC\_ pipeline routes on this status — if the binding declares `"BACKEND_ERROR": "exit"`, the pipeline terminates with a classified failure. The error does not propagate as an unhandled exception. It is a governed result.

**This section proves:** CS\_ failures are structural and classified. Every failure has a named check, a diagnostic message, and a declared routing action. The distance between a misconfigured binding and a classified failure is zero.

* * *

## 7.7 — Structural Insight (Doctrine Moment)

The reader has seen three CS\_ runtime types with declared operations, RB\_ artifacts that bind abstract capabilities to concrete storage, and CC\_ pipelines that orchestrate CT\_ and CS\_ steps with explicit result routing. At no point did the execution engine interpret what was being stored, why it was being registered, or what the event meant. It dispatched operations. It collected results. It routed on status codes.

This is Chapter 2's **Property 3 — Structural Enforcement** made operational at the mutation layer. Side effects are not discovered in code. They are declared in governance artifacts. The CC\_ pipeline declares which CS\_ steps execute. The RB\_ artifact declares which runtime hosts serve them. The runtime class declares which operations it supports. Each layer constrains the next. No layer can expand its authority beyond what the layer above declares.

**Invariant I-S4 — Explicit Mutation Policy:** Side effects must declare behavior under repeated execution. Replay safety is not universal idempotency; it is declared behavior under repeated execution — each CS\_ type has distinct replay characteristics. Append-only stores (CS\_APPENDONLY\_JSONL\_V0) are naturally idempotent-aware — each append creates a new record with a unique ID, so replaying an append produces a new entry rather than corrupting an existing one. Mutable stores (CS\_MUTABLE\_JSON\_V0) use last-write-wins — replaying a WRITE overwrites with the same value. Registries (CS\_REGISTRY\_V0) return ALREADY\_EXISTS on duplicate registration — the CC\_ pipeline routes on this status, making replay handling explicit in the governance artifact. The point is not that all CS\_ operations are idempotent — they are not. The point is that every CS\_ type's replay behavior is known, declared, and routable.

**Invariant I-S5 — No Ambient Authority:** The system cannot mutate anything not declared in a CS\_ capability and bound through RB\_. There is no `db.write()` call hidden in a helper. There is no `logger.append()` embedded in a transform. There is no `cache.update()` triggered by a read. Every mutation flows through a single chain:

```
CC_ declares CS_ step → RB_ binds CS_ to runtime → Runtime executes operation
```

Break any link in this chain and mutation cannot occur. The engine has no backdoor, no escape hatch, no "just this once" override. Mutation authority is constitutional.

**Structural impossibility:** The execution engine cannot write to storage, call an external service, or mutate state unless a CC\_ pipeline declares a CS\_ step, the CS\_ code is bound in an RB\_ artifact, and the RB\_ maps to a registered runtime class with a matching operation method. There is no mechanism to bypass this chain.

> **[DIAGRAM 4] — The Mutation Authority Chain**
>
> ```
>         CT_ Layer
>      (Pure Computation)
>             |
>      ===== Constitutional Boundary =====
>             |
>             v
>         CC_ Pipeline
>      (Declared Orchestration)
>             |
>             v
>         RB_ Binding
>      (Abstract -> Concrete)
>             |
>             v
>        CS_ Runtime
>      (Bounded Mutation)
> ```
>
> Every mutation traverses this chain from top to bottom. Break any link and mutation cannot occur. The chain is not a convention — it is the only path the architecture provides.

CT\_ purity + CS\_ declaration = total mutation visibility.

This is the enforcement half of the paradigm. Chapter 6 proved that computation is pure. This chapter proves that mutation is declared. Together, they complete the execution layer: everything the system does is either governed computation (CT\_) or governed interaction (CS\_), including both reads and writes. There is no third category.

* * *

## 7.8 — Solved Problems

### Problem 7.1 — Hidden Database Writes

**Scenario:** A validation helper writes an audit record to the database as a side effect of computing a validation result.

**Application-Centric Approach:** The function `validate_actor(record)` checks field validity AND writes to an audit table. Callers assume it is pure — it is not. Moving the function to a batch processing context writes thousands of unexpected audit records. Moving it to a test context requires a database connection that the test environment does not have. The function's actual dependency surface is invisible.

**PGS Approach:**
1. Validation is a CT\_ atom — pure, deterministic, no I/O. It takes a record, returns a validation result.
2. Audit logging is a separate CS\_ step in the CC\_ pipeline — declared, bound, independently traceable.
3. The CC\_ pipeline declares the order: validate first (CT\_), then log (CS\_). The ordering is visible in the artifact.
4. The validation atom is reusable in any context — batch processing, testing, different modules — because it has no hidden dependencies.

**Eliminated pathology:** Implicit mutation. Side effects cannot hide inside pure computation because the architecture does not permit CT\_ to perform I/O. The CT/CS boundary is constitutional.

### Problem 7.2 — Implicit Transaction Scopes

**Scenario:** A service method opens a database transaction, calls three helper functions that each perform writes, and commits the transaction implicitly when the method returns. One helper fails mid-transaction. The transaction scope is invisible to the caller.

**Application-Centric Approach:** The service method's `@transactional` annotation wraps an implicit scope around all database operations within the call. If helper B fails after helper A has written, the framework silently rolls back A's write. If the framework does not support distributed transactions, A's write persists while B's fails — producing an inconsistent state that no one declared or anticipated. The transaction boundary is a framework convention, not a structural guarantee.

**PGS Approach:**
1. No implicit transaction scope. Each CS\_ step in the CC\_ pipeline is a declared, independent mutation.
2. Ordering is explicit — step 1, then step 2, then step 3. The pipeline artifact shows the sequence.
3. Each step's `on_result` declaration specifies what happens on failure. If step 2 returns BACKEND\_ERROR and the binding declares `"BACKEND_ERROR": "exit"`, the pipeline terminates. Step 3 does not execute.
4. Compensating logic, if needed, is itself a declared workflow — not hidden rollback magic.

**Eliminated pathology:** Hidden commit/rollback semantics. Every mutation is a declared step with explicit failure routing. The system does not silently roll back or silently commit. What happens on failure is written in the governance artifact.

### Problem 7.3 — Side-Effect Drift

**Scenario:** A developer adds a new logging call to a helper function. Production behavior changes silently — the new log writes to a shared event stream that downstream consumers depend on. The change was a one-line addition to a helper. The impact was a schema change to a production event stream.

**Application-Centric Approach:** The helper function is "just code." Adding a logging call requires no approval, no schema change, no version update. The change passes code review because it looks harmless. The downstream consumer breaks two weeks later when it encounters event records with a new field it does not expect. Root cause analysis takes days because no one connected the helper change to the event stream impact.

**PGS Approach:**
1. A new CS\_ step requires a governance artifact — it must be declared in a CC\_ pipeline.
2. The CC\_ pipeline change requires builder validation — the new CS\_ code must be bound in an RB\_ artifact.
3. The RB\_ binding must reference a registered runtime class with a matching operation.
4. The entire chain is versioned. The CC\_ is versioned. The RB\_ is versioned. The change is traceable from governance through compilation through execution.

**Eliminated pathology:** Silent mutation expansion. No side effect can enter the system without a governance artifact, a runtime binding, and a pipeline declaration. The cost of adding a side effect is the cost of declaring it — which is exactly the cost it should have.

* * *

## 7.9 — Generated Output: The Mixed CT+CS Execution Trace

The CC\_ pipeline produces a step-by-step trace that records both pure computation and side-effect execution. This trace is the structural proof of what the system computed and what it mutated.

### Trace: CC\_REGISTER\_ACTOR\_KYC\_V0

```
CC_PIPELINE_START
  contract: CC_REGISTER_ACTOR_KYC_V0
  inputs: {actor_record: {first_name: "Ada", last_name: "Lovelace",
           email_registration: "ada@example.com"},
           actor_id: "AC_7f3a2b"}

  STEP 1: CT_PURE_GENERATE_ID_V0
    type: CT (pure computation)
    op: GENERATE_ID
    inputs: {prefix: "KYC",
             data: {first_name: "Ada", last_name: "Lovelace",
                    email: "ada@example.com"}}
    result: {value: "KYC_8a4c1d9e", result_status: "SUCCESS"}
    resolved_outputs: {kyc_key: "KYC_8a4c1d9e"}
    routing: SUCCESS → continue

  STEP 2: CS_ACTOR_ALIAS_INDEX_V0
    type: CS (side effect)
    op: REGISTER
    inputs: {key: "KYC_8a4c1d9e",
             target_cs: "CS_ACTOR_STATE_V0",
             target_ref: "AC_7f3a2b"}
    result: {result_status: "SUCCESS", address: "ADDR_f91b3c"}
    resolved_outputs: {address: "ADDR_f91b3c"}
    routing: SUCCESS → continue

CC_PIPELINE_END
  final_outputs: {address: "ADDR_f91b3c"}
  result_status: SUCCESS
  steps_executed: 2
  ct_steps: 1
  cs_steps: 1
```

### What the Trace Proves

- **Every side effect is visible.** Step 2 records the CS\_ operation (REGISTER), the inputs (key, target\_cs, target\_ref), and the result (address, result\_status). There is no hidden write. The trace is a complete record of what the system mutated.
- **CT and CS results follow distinct conventions.** Step 1's result is wrapped: `{value: "KYC_8a4c1d9e", result_status: "SUCCESS"}`. Step 2's result is direct: `{result_status: "SUCCESS", address: "ADDR_f91b3c"}`. The trace makes the wrapping convention visible — an auditor can distinguish pure computation from side effects by inspecting the result structure.
- **Cross-step data flow is traceable.** Step 2's `key` input (`"KYC_8a4c1d9e"`) is the resolved output of Step 1. The trace records both the symbolic binding and the resolved value. An auditor can trace every value from its source to its consumption.
- **Ordering is structural.** Step 1 executes before Step 2 because the pipeline array declares that order. The trace records the execution in pipeline order. There is no concurrent execution, no implicit interleaving, no race condition.
- **The engine did not interpret meaning.** It did not know what KYC means, what an actor alias is, or why the registry matters. It dispatched GENERATE\_ID to a CT atom. It dispatched REGISTER to a CS runtime. It collected results and routed on status codes.

**Structural impossibility:** The CC\_ pipeline cannot execute a CS\_ step that is not declared in the pipeline array, not bound in the RB\_ artifact, or not registered as a runtime class. The trace cannot contain a side effect that the governance artifacts did not declare. If the trace records two steps, the pipeline declared two steps. There is no mechanism for the engine to deviate from the declared pipeline.

You authored governance artifacts for capability contracts and runtime bindings. The pipeline dispatched CT\_ and CS\_ steps in declared order. The trace recorded every computation and every mutation. At no point did the engine decide what to compute or what to mutate — and that is the point.

* * *

## 7.10 — Boundary and Forward Pointer

This chapter proved that world mutation is governed structurally — through CS\_ capabilities with declared operations, RB\_ artifacts that bind capabilities to concrete runtimes, and CC\_ pipelines that orchestrate CT\_ and CS\_ steps with explicit result routing. It proved that the CT/CS boundary is constitutional: pure computation on one side, governed mutation on the other, with no mechanism to cross the boundary except through the CC\_ pipeline.

Together with Chapter 6, this completes the execution layer:

- **Chapter 6:** Pure computation — atoms, molecules, CT-IR, deterministic execution
- **Chapter 7:** Controlled mutation — CS\_ runtimes, RB\_ bindings, declared side effects

Everything the system does is either a governed computation or a governed side effect. There is no third category.

**What this chapter did not cover:**

- Domain-specific CS\_ runtimes beyond the three persistent types (e.g., external services, workflow gateways)
- External side effects (email, webhooks) and the disable mechanism for test environments
- Distributed consistency models and cross-node mutation coordination
- Cross-domain federation and how separate modules' RB\_ bindings interact (Chapter 11)
- The full failure taxonomy across all layers (Chapter 8)
- Trace field suppression for sensitive data (e.g., `suppress_trace_fields` in CC\_ artifacts)

**What comes next:** Chapter 8 — Failure Taxonomy and Structural Diagnostics. Chapters 3 through 7 each introduced layer-specific failures: governance validation, compilation, runtime dispatch, transform execution, and side-effect execution. Chapter 8 classifies all failure modes into a unified taxonomy. The reader will see that PGS failure is structural — every failure has a layer, a check, a classification, and a deterministic diagnostic. There are no unclassified errors.

* * *

## 7.11 — Review Questions

1. **True or False: A CS\_ runtime may perform computation on the values it receives before writing them to storage.**

    *False. CS\_ runtimes perform bounded storage operations — WRITE, REGISTER, APPEND — on the values they receive. Computation belongs in CT\_ steps. The CS\_ runtime stores the value it is given without transforming it. If computation is needed before persistence, it must be a prior CT\_ step in the CC\_ pipeline.*

2. **What structural guarantee does runtime binding (RB\_) provide?**

    *RB\_ provides a governed indirection between abstract CS\_ codes and concrete runtime implementations. It guarantees that: (a) every CS\_ code maps to exactly one runtime host class and storage policy, (b) storage paths are parameterized and resolved from the path registry, (c) the set of host classes is closed — no dynamic class loading or plugin discovery, and (d) bindings are domain-scoped, preventing cross-module storage leakage.*

3. **Explain the difference between CT\_ and CS\_ result wrapping in the CC\_ pipeline, and why it matters.**

    *CT\_ results are wrapped as `{"value": <output>, "result_status": "SUCCESS"}` by the pipeline. CS\_ results are returned directly as `{"result_status": "SUCCESS", "field": "value"}`. This means CT\_ output bindings must use `$.capability_result.value.field` while CS\_ output bindings use `$.capability_result.field`. The distinction exists because CT\_ is pure computation — it does not know about result statuses — so the pipeline wraps its output to integrate it into the protocol flow. CS\_ operations natively return result statuses as part of their contract.*

4. **Why is append-only logging structurally safer than mutable state for audit trails?**

    *CS\_APPENDONLY\_JSONL\_V0 opens the file in append mode. There is no UPDATE operation. There is no DELETE operation. Prior records cannot be modified because the runtime class does not provide methods to modify them. Every event is an immutable fact. Append-only safety is not a convention enforced by discipline — it is a structural property of the runtime API surface. Mutable state (CS\_MUTABLE\_JSON\_V0) uses last-write-wins, which is appropriate for current state but not for historical records.*

5. **What chain must be satisfied before the system can perform a mutation?**

    *Three links: (1) A CC\_ pipeline must declare a CS\_ step in its pipeline array with a binding that specifies the operation and inputs. (2) An RB\_ artifact must bind the CS\_ code to a registered runtime host class with a storage policy. (3) The runtime host class must have a method matching the declared operation name (op.lower()). If any link is missing, the mutation cannot occur. There is no bypass mechanism.*

6. **Why must the last step in a CC\_ pipeline forward outputs from earlier steps?**

    *Only the last step's resolved outputs become the CC\_ result. If a CC\_ needs to expose a value computed by an earlier CT\_ step, the last step must include that value in its output bindings — either by re-resolving it from `$.results.PRIOR_STEP.field` or by passing it through its own computation. This rule is structural: the pipeline accumulates results but only surfaces the final step's outputs to the calling workflow.*

7. **If a new CS\_ operation (e.g., logging to an external analytics service) is needed, what governance artifacts must change?**

    *At minimum: (a) a new CS\_ runtime class must be authored and registered in the closed runtime class registry, (b) the module's RB\_ artifact must add a binding for the new CS\_ code with the appropriate host class and policy, and (c) the CC\_ pipeline must declare the new CS\_ step with operation, inputs, outputs, and result routing. The change is traceable across three versioned artifacts. It cannot be done silently.*
