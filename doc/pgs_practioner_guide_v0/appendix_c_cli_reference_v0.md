# Appendix C — OmniBachi CLI Reference

`omnibachi` is the command-line interface for the PGS runtime engine. It provides two subcommands: `run` executes a workflow or intent against a compiled snapshot, and `examine` inspects an execution trace.

* * *

## Global Usage

```
omnibachi <subcommand> [options]
```

The CLI reads from `protocol_snapshot/` and writes traces to `traces/`. It does not modify snapshot artifacts.

* * *

## `omnibachi run`

Executes a workflow or intent against the compiled protocol snapshot.

### Synopsis

```
omnibachi run \
  (--wf <FQDN> | --intent <FQDN>) \
  --payload <path> \
  [--rb <FQDN>] \
  [--mode <runtime|authoring>] \
  [--debug] \
  [--data-root <path>] \
  [--workspace <path>]
```

### Entry Point (mutually exclusive, one required)

| Flag | Argument | Description |
|------|----------|-------------|
| `--wf` | `<FQDN>` | Execute by workflow FQDN directly (e.g., `blockchain::WF_REGISTER_ACTOR_UNVERIFIED_V0`). Bypasses intent admission gate. |
| `--intent` | `<FQDN>` | Execute via intent FQDN (e.g., `blockchain::IN_ACTOR_REGISTERED_V0`). Admission check runs first; workflow is resolved from the intent declaration. |

`--wf` and `--intent` are mutually exclusive. Exactly one must be provided.

### Required Flags

| Flag | Argument | Description |
|------|----------|-------------|
| `--payload` | `<path>` | Path to a JSON file containing the execution payload. The payload must satisfy the schema declared by the workflow's intent. |

### Optional Flags

| Flag | Argument | Default | Description |
|------|----------|---------|-------------|
| `--rb` | `<FQDN>` | Resolved from snapshot | Runtime binding FQDN override. Overrides the default binding for the workflow. Used when testing an alternative implementation without recompiling. |
| `--mode` | `runtime` \| `authoring` | `authoring` | Execution mode. `authoring` runs governance checks and produces full trace output. `runtime` is a leaner path for production execution. |
| `--debug` | _(flag)_ | off | Enable DEBUG-level logging. Outputs internal resolution steps, JSONPath evaluations, and capability dispatch events to stderr. |
| `--data-root` | `<path>` | `PGS_DATA_ROOT` env var | Absolute path to the directory where CS\_ side effects write runtime state (e.g., `registry/actors.json`, `events/*.jsonl`). Must be absolute. |
| `--workspace` | `<path>` | `PGS_WORKSPACE` env var | Path to the `pgs_workspace` root. The runtime reads `protocol_snapshot/` from `{workspace}/protocol_snapshot/` and writes traces to `{workspace}/traces/`. |

### Environment Variables

| Variable | Equivalent Flag | Description |
|----------|----------------|-------------|
| `PGS_DATA_ROOT` | `--data-root` | Default data root when `--data-root` is not passed. |
| `PGS_WORKSPACE` | `--workspace` | Default workspace root when `--workspace` is not passed. |

Flags take precedence over environment variables when both are set.

### Execution Behavior

1. The runtime loads `protocol_snapshot/` from `{workspace}/protocol_snapshot/`.
2. If `--intent` is used, the intent admission gate runs first. The payload must satisfy the intent's declared input schema. A failed admission gate exits without writing a trace.
3. The workflow DAG is traversed: each CC\_ node resolves its inputs via JSONPath, dispatches CT\_ transforms and CS\_ side effects through RB\_ bindings, and routes to the next node based on the outcome.
4. A trace is written to `{workspace}/traces/<TRACE_ID>/`:
   - `<TRACE_ID>.jsonl` — append-only structured event log
   - `<TRACE_ID>.md` — human-readable summary
   - `<TRACE_ID>.png` — execution path visualization

### Exit Behavior

| Condition | Exit Code |
|-----------|-----------|
| Workflow completed (any terminal outcome) | `0` |
| Intent admission failed | `1` |
| Missing or unresolvable artifact | `1` |
| Unresolved RB\_ binding | `1` |
| Invalid payload JSON | `1` |

### Examples

```bash
# Execute by workflow FQDN
omnibachi run \
  --wf blockchain::WF_REGISTER_ACTOR_UNVERIFIED_V0 \
  --payload ./scripts/payloads/register_actor.json \
  --data-root ./data \
  --workspace .

# Execute via intent (admission gate enforced)
omnibachi run \
  --intent blockchain::IN_ACTOR_REGISTERED_V0 \
  --payload ./scripts/payloads/register_actor.json \
  --data-root ./data \
  --workspace .

# Run with debug logging and explicit mode
omnibachi run \
  --wf blockchain::WF_REGISTER_ACTOR_UNVERIFIED_V0 \
  --payload ./scripts/payloads/register_actor.json \
  --mode authoring \
  --debug \
  --data-root ./data \
  --workspace .

# Use environment variables instead of flags
export PGS_DATA_ROOT=./data
export PGS_WORKSPACE=.
omnibachi run \
  --wf blockchain::WF_REGISTER_ACTOR_UNVERIFIED_V0 \
  --payload ./scripts/payloads/register_actor.json
```

* * *

## `omnibachi examine`

Inspects an execution trace produced by `omnibachi run`.

### Synopsis

```
omnibachi examine <trace_file>
```

### Positional Arguments

| Argument | Description |
|----------|-------------|
| `trace_file` | Path to a `.jsonl` trace file. Typically `traces/<TRACE_ID>/<TRACE_ID>.jsonl`. |

### Behavior

The examiner reads the structured event log and prints a human-readable summary of the execution:
- Workflow and intent resolved
- Each CC\_ node: inputs, outcome, outputs
- Each CT\_ and CS\_ step within each node
- Routing decisions at each node
- Terminal state and exit outcome
- Any failures, violations, or unexpected outcomes flagged with diagnostic hints

The examiner does not modify the trace file. It is read-only.

### Output Format

The examiner prints to stdout. Output includes:
- A header with trace ID, workflow FQDN, and execution timestamp
- A node-by-node walk of the execution path
- A terminal summary (final outcome, nodes visited, capabilities invoked)

### Example

```bash
# Examine a specific trace
omnibachi examine ./traces/abc123/abc123.jsonl

# Examine after a run (capturing the trace ID from run output)
omnibachi examine ./traces/$(ls -t traces/ | head -1)/$(ls -t traces/ | head -1).jsonl
```

* * *

## Operational Notes

**Snapshot is read-only.** The CLI reads from `protocol_snapshot/` but never writes to it. Any change to behavior requires recompiling the protocol source.

**Data root must be absolute.** Relative paths for `--data-root` are not supported. Use `$(pwd)/data` if the script is in the workspace root.

**Trace IDs are deterministic.** The same payload run twice under identical snapshot state produces the same trace structure. This is the basis of the idempotency guarantee: check for `ALREADY_EXISTS` outcomes in repeated runs.

**No interactive mode.** The CLI is non-interactive. All inputs are provided at invocation time.
