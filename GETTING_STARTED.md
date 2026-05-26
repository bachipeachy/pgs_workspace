# Getting Started — pgs_workspace

> New here? Start with [README.md](README.md) for a plain-language introduction to what PGS is and why it exists. This guide covers setup and operation.

---

**The runnable entry point for Protocol-Governed Systems.**
Imagine software where the "rules" are written first, and the code just follows them,
making behavior predictable, safe, and auditable by design.

---

## What is this?

This repository lets you run a working system where:

- You execute workflows without writing execution code
- Behavior is declared in protocol artifacts and compiled ahead of time
- The runtime simply follows a precomputed execution graph

You are not starting a framework.

You are executing a compiled protocol.

---

## Quick questions you might have

### What am I looking at?

A system where application behavior is not embedded in code, but defined in protocol artifacts and compiled into an execution graph.

---

### What happens if I run this?

You will execute a real workflow end-to-end:

- A payload enters the system
- A precompiled DAG (directed graph) is traversed
- Side effects update state
- A trace records exactly what happened

You will not write or modify execution logic.

---

### Why is this different?

Traditional systems:

- Behavior lives in code
- Control flow is implicit
- Runtime decides what to do

PGS:

- Behavior is compiled ahead of time
- Control flow is explicit in a DAG
- Runtime does not make decisions

---

### What is the point?

To make behavior:

- deterministic  
- inspectable  
- governed by protocol instead of code  

---

## The paradigm

Traditional systems embed behavior in code.

PGS compiles behavior into the execution substrate. The runtime does not decide what to do. It only traverses a precomputed graph.

**Three properties this system demonstrates:**

1. Compile-time resolution  
2. Deterministic routing  
3. Append-only history  

> Extensibility by declaration, not refactor.

---

## What you are about to do

In a few commands, you will:

1. Set up the workspace  
2. Execute a compiled workflow  
3. Observe system behavior without writing code  
4. Inspect traces and resulting state  

---

## Prerequisites

All repositories must exist side-by-side:

~/  
├── pgs_workspace/  
├── pgs_runtime/  
├── pgs_governance/  
├── pgs_compiler/  
├── pgs_transport/  
├── pgs_capabilities/  
├── pgs_blockchain/  
├── pgs_ai_governance/  

---

## Quickstart

```bash
git clone https://github.com/bachipeachy/pgs_workspace
cd pgs_workspace
./scripts/bootstrap_pgs.sh
source .venv/bin/activate
./scripts/demo_sample_workflow.sh
```

---

## What the demo proves

- Same workflow executed twice without changing code
- State enforces constraints
- Event history remains append-only

→ State is constrained. History is not.

---

## Examine what ran

```bash
pgs_runtime examine traces/<TRACE_ID>/<TRACE_ID>.jsonl
```

---

## Run any workflow

```bash
pgs_runtime run \
  --wf <domain::WORKFLOW> \
  --payload <payload.json> \
  --data-root $(pwd)/data \
  --workspace $(pwd)
```

---

## Artifact reference

| Prefix | Meaning |
|--------|--------|
| WF_ | Workflow |
| CC_ | Capability Contract |
| CT_ | Transform |
| CS_ | Side Effect |
| IN_ | Intent |
| RB_ | Runtime Binding |
| AS_ | Assertion |

---

## Why this matters (Developer Benefits)

PGS fundamentally changes how software is built and governed, offering significant advantages for developers:

-   **Correct-by-Construction Execution**: Invalid behavior cannot be expressed or executed.
-   **Reduced Boilerplate**: Focus on business logic, not orchestration or routing.
-   **Enhanced Security**: Eliminates entire classes of vulnerabilities (e.g., RCE, injection) by design.
-   **Simplified Auditing**: Every execution produces an immutable, verifiable trace.
-   **Linear Scalability of Governance**: Complexity scales additively, not multiplicatively.
-   **Accelerated AI-Generated Code Integration**: Provides a robust framework for governing autonomous and AI-generated software.

---

## Further Reading

For a deeper dive into the theoretical foundations, architectural model, and empirical validation of Protocol-Governed Systems, please refer to the accompanying technical paper:

*   [**Technical Paper**](doc/techpaper_protocol-governed_systems_v1.pdf) — formal model, dual-space architecture, security inversion, scalability analysis
*   [**Conceptual Model**](doc/pgs_conceptual_model_v0.pdf) — protocol snapshot, four-layer admissibility model, constitutional invariants, evidence model
*   [**Practitioner's Guide**](doc/pgs_practioner_guide_all_chapters.pdf) — all chapters in a single document

---

## License

Apache-2.0

---

## Contributing

We welcome contributions to the Protocol-Governed Systems project. Open an issue or pull request on GitHub.
