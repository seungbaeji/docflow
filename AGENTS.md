# AGENTS.md

## Goal

Build a document-processing service that is easy for junior developers, locally testable, and safe to extend.

Main complexity:

- document interpretation
- multi-source combination
- accounting/business rules

## Architecture

Use this dependency shape:

```text
inbound -> workflow -> usecases
usecases -> core
usecases -> outbound
```

Rules:

- `core` must not call `outbound`
- `outbound` must not call `core`
- `inbound` is entrypoint only
- `workflow` is its own layer, not part of `inbound`

## Workflow

`workflow` is a stateful orchestration object, not a framework synonym.

Responsibilities:

- choose and advance flow steps
- connect multiple usecases
- manage small state and context
- manage HITL pending / approve / reject / resume
- keep only control fields and artifact refs in state

Rules:

- large data must live in repository/store, not workflow state
- current implementation may use LangGraph, but workflow concept is not LangGraph-specific
- entrypoints are stateless; workflow owns execution context

## Layers

### inbound

- FastAPI, Streamlit, CLI entrypoints
- call workflow or usecases only
- no business logic

### usecases

- orchestrate core + outbound
- no business rules
- no parsing logic
- no direct file/automation details

### core

- source_kind, parse, category, combine, analyze, edit, rules
- structured data only
- no files, UI automation, or outbound imports
- `edit` produces structured edit intents only

### outbound

- external systems and representation
- ECM, SAP, mail, OCR, LLM, storage, queue, DB, file automation
- fetch/persist data, convert external responses, apply edit intents, run automation
- no business rules or classification

### ports

- boundary interfaces used by usecases/workflow
- examples: repository, llm, rdbms, vector_store, queue

### types

- dataclasses only
- explicit real data shapes
- acyclic imports only

## Data Rules

- flow: `source -> parse -> unit -> category -> combine -> analyze -> rules -> edit`
- core uses structured types only
- outbound handles bytes/files/external SDKs
- workbook, worksheet, dataframe, OCR text blobs, mail attachments, UI objects must not escape outbound

## Testing

- `tests/unit/core`
- `tests/unit/usecases`
- `tests/unit/workflow`
- `tests/integration/outbound`

Rules:

- tests must run locally
- no real external systems
- use fixtures, fake objects, monkeypatch, tmp files

## Design Rules

- use type hints everywhere
- prefer small functions over unnecessary classes
- keep modules small
- use explicit names
- shared custom errors may live in `errors.py`

## Constraint

Optimize for document complexity, not provider abstraction.

If external agent exposure is needed later, prefer adding MCP as a separate public interface rather than exposing workflow through ad hoc public tools.
