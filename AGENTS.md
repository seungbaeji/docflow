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
inbound -> usecases
usecases -> workflow
usecases -> core
usecases -> outbound
```

Rules:

- `core` must not call `outbound`
- `outbound` must not call `core`
- `inbound` is entrypoint only
- `workflow` is its own layer, not part of `inbound`
- `tools` is its own layer for agent/tool-calling actions, not part of `workflow`
- `types` must not import any non-types layer
- `workflow` must not import `bootstrap`

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
- call usecases only
- no business logic

### usecases

- orchestrate core + outbound
- may invoke workflow when stateful orchestration is needed
- no business rules
- no parsing logic
- no direct file/automation details

### tools

- internal agent/tool-calling action surface
- consume explicit prepared context from workflow
- do not own workflow state transitions
- do not decide current document or session state

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

### bootstrap

- provide the default DI container
- build settings, repositories, gateways, workflow runtime, and usecases in one place
- entrypoints and usecase facades should use bootstrap wiring rather than instantiating adapters inline
- workflow must consume explicit dependencies, not the container itself

### types

- `types/value`: `frozen dataclass` value object only
- `types/boundary`: `pydantic` boundary DTO and external payload shape
- explicit real data shapes
- acyclic imports only

Rules:

- `core` uses `types/value` only
- `types/value` must not import `types/boundary`
- `dataclass` is for data models only and must live under `types`
- do not use `dataclass` in `usecases`, `workflow`, `outbound`, `bootstrap`, or `inbound`
- treat all external input as untrusted
- validate or normalize external input at inbound/outbound boundaries before converting to value objects

## Data Rules

- flow: `source -> parse -> unit -> category -> combine -> analyze -> rules -> edit`
- core uses structured types only
- outbound handles bytes/files/external SDKs
- workbook, worksheet, dataframe, OCR text blobs, mail attachments, UI objects must not escape outbound

## Workflow Direction Rules

- `workflow/process/*` handles process graph/state/node orchestration only
- `workflow/chat/*` handles chat prep workflow and agent wiring only
- `workflow/agent/*` handles tool-calling loop only
- `workflow/document/*` contains document workflow helpers only

`workflow/document/*` must stay one-directional:

```text
workflow/document/{source,parse,chat,mail} -> workflow/document/support
```

Rules:

- `support.py` is the lowest helper module in `workflow/document`
- `source`, `parse`, `chat`, `mail` may depend on `support`
- `source`, `parse`, `chat`, `mail` must not depend on each other
- `chat` must not re-run parse logic; prep workflow must guarantee prepared artifacts first
- tools must consume prepared explicit context only
- tools must not select current document, upload, or session state

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
