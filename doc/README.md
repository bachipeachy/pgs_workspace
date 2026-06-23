# PGS Documentation Index

This directory contains all documentation for Protocol-Governed Systems (PGS).


## Start Here

If you are new to PGS, begin at the root of this repository:

- [**README.md**](../README.md) — plain-language introduction: what PGS is, what problem it solves, how it differs from conventional systems
- [**GETTING_STARTED.md**](../GETTING_STARTED.md) — setup, quickstart, and full operational reference


## Technical Paper

**techpaper_protocol-governed_systems_v2.pdf**
The primary academic paper on PGS. Covers the formal model, dual-space architecture,
execution semantics, security inversion, linear scalability analysis, and the Governance
Dividend. Includes the PGS reference implementation.
Also available as: techpapers/techpaper_protocol-governed_systems_v2.docx


## Conceptual Model

**pgs_conceptual_model_v0.pdf**
Defines the conceptual model for Protocol-Governed Systems, validated through the PGS
reference implementation. Covers the protocol snapshot, four-layer admissibility model,
constitutional invariants, and evidence model.
Also available as: parkinglot/pgs_conceptual_model_v0.md


## Field Manual

**pgs_field_manual_v1.md**
Authoritative architectural reference for working with PGS. Covers doctrine, invariants,
the nine execution concerns, federation boundary model, compiler pipeline, and
operational rules. Intended as a context-free cognitive digest -- read this to restore
full architectural context in any session.


## Practitioner's Guide

**pgs_practioner_guide_all_chapters.pdf**
An 18-chapter guide covering PGS from first principles through advanced topics. Chapters
progress from why software breaks at scale, through protocol authoring, execution
semantics, capability design, security, federation, scalability, and AI-augmented
development. Includes four appendices (glossary, snapshot reference, CLI reference,
artifact schema reference) and SVG figures.

  ch00  Introduction and Orientation

  ch01  Why Software Breaks at Scale

  ch02  From Applications to Protocols

  ch03  Constitutional Authoring

  ch04  The Builder as Constitutional Compiler

  ch05  Semantic-Agnostic Execution

  ch06  Capability Transforms and Composition

  ch07  Capability Side Effects and Isolation

  ch08  Failure as a First-Class Architectural
  Construct
  ch09  Deterministic Traces as First-Class Artifacts

  ch10  Inverted Security Architecture

  ch11  Declarative Package Federation

  ch12  Linear Scalability through Compositional Isolation

  ch13  Constructing a Protocol-Governed Domain

  ch14  Use Case -- AI Agent Governance Domain

  ch15  Structural Economics of Governance

  ch16  Engineering under Constitutional Constraint

  ch17  AI-Augmented Development under Protocol Governance

  ch18  Adopting Protocol Governance Incrementally

  Appendix A -- Glossary of PGS Terms

  Appendix B -- Protocol Snapshot Reference

  Appendix C -- CLI Reference

  Appendix D -- Artifact Schema Reference


## Onboarding

**onboarding_build_first_workflow.md**
Step-by-step guide for building the first workflow in PGS. Explains why PGS exists and
walks through authoring protocol artifacts, compiling a snapshot, and running an
execution end-to-end. Starting point for new contributors.


## Worked Example

**pgs_worked_example.md**
Teaches PGS by building something real: a Collatz Conjecture domain. Covers authoring
all artifact types (WF, CC, CT, CS, EV, IN, AC), compiling, and executing with trace
examination. Intended as a hands-on companion to the field manual.


## CLI Cheatsheet

**pgs_cli_cheatsheet.txt**
Quick reference for all pgs_runtime CLI commands and compiler build sequences. Covers
compile phases (Phase A per-structure, Phase B aggregation), snapshot sync, workflow
execution, and trace examination. Keep this open during active development.


## Challenge Projects

**challenge_projects/**
Experimental project proposals exploring PGS as a governance substrate for intelligent
systems. Each document describes an ambitious prototyping challenge for developers
interested in extending PGS beyond workflow governance.

  1. 1_protocol_governed_blockchain_chain_runtime.md -- Build & close the blockchain/chain CR from its dossier (2/5 difficulty)

  2. 2_pgs_governed_autonomous_agent_runtime.md       -- Structural governance for autonomous AI agents (3/5 difficulty)

  3. 3_pgs_governed_transformer_runtime.md            -- Protocol-governed Transformer inference topology (5/5 difficulty)


## Assets

**assets/**
Visual assets used across documentation.

  1. splash_screen_http_thin_client.png        -- HTTP thin client demo splash screen

  2. WF_DEMO_COLLATZ_CONJECTURE_V0.projection.png  -- Collatz workflow execution graph

  3. collatz_conjecture_happy_flow_execution.png   -- Collatz happy-path trace visualization
