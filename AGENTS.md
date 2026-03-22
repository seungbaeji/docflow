# AGENTS.md

## Goal

Build a document-processing service that is:
- easy for junior developers
- locally testable
- safe to extend

The system processes data from ECM, Mail, SAP, and external APIs.

The main complexity is:
- document interpretation
- multi-source combination
- business rules (accounting)

---

## Core Architecture

Use this structure:

inbound → usecases

Usecases may call:
- core
- outbound

Usecases orchestrate both core and outbound.
Core must NOT call outbound.
Outbound must NOT call core.

---

## Layers

### inbound/
Entry points only:
- FastAPI
- Streamlit
- LangGraph
- CLI

Rules:
- must call usecases only
- no business logic here

---

### usecases/
Orchestration layer.

Responsibilities:
- fetch data from outbound
- call core logic
- combine results
- persist or send results

Rules:
- no business logic
- no parsing logic
- no direct DB/ECM logic

---

### core/

Main processing logic.

#### source_kind/
Determine source type (excel, pdf, image, mail, sap)

#### parse/
Read source and produce units

#### category/
Determine business meaning of units or bundles

#### combine/
Combine multiple units into business bundles

#### analyze/
Perform analysis (aggregation, matching, etc.)

#### edit/
Apply modifications to structured data

#### rules/
Business rules (accounting, invoice, settlement, validation)

Rules:
- core must not call outbound
- core operates on structured data only

---

### outbound/

External systems and representation.

Includes:
- ECM
- files
- mail
- SAP
- OCR
- LLM
- database

Responsibilities:
- fetch/persist data
- convert structured data to bytes/files
- convert external responses to typed structures
- load sources from ECM, mail, SAP/API, files, or other external systems
- convert files, bytes, and external responses into typed source or external structures

Rules:
- no business logic
- no classification
- no rules
- must not import core

---

### types/

Typed structures.

Includes:
- source types
- parsed structures
- units
- bundles
- db records when persistence is introduced
- results

Rules:
- use dataclasses
- reflect real data shapes
- allow multiple explicit types
- allow nested structures
- avoid unnecessary abstraction
- imports between types modules are allowed only when they remain acyclic

---

## Dependency Rules

Allowed:
- inbound → usecases
- usecases → core
- usecases → outbound
- core → core
- outbound → outbound

Forbidden:
- core → outbound
- core → usecases
- outbound → core
- inbound → core

---

## Import Rules

- inbound → usecases, types
- usecases → core, outbound, types
- core → core, types
- outbound → outbound, types
- types → (no imports from other layers)
- types → types is allowed only when it does not create circular references
- shared errors may live in root `errors.py`
- same-layer imports are allowed only when they remain acyclic
- circular imports are not allowed in any layer

---

## Data Flow

source → parse → unit → category → combine → analyze → rules

---

## Binary Handling

- core uses structured types only
- outbound handles bytes and file conversion
- bytes are external transfer format only

---

## Database Rules

- database logic stays in outbound/db
- SQLAlchemy must not be imported outside outbound
- only map persistence-relevant types
- do not map processing units or bundles

---

## CLI

- must call usecases only
- no logic inside CLI

---

## LangGraph

- orchestration only
- nodes call usecases
- no business logic in graph

---

## Design Rules

- use type hints everywhere
- prefer functions over classes
- keep modules small
- avoid generic names (logic, manager, util)
- use explicit names
- keep shared custom errors in root `errors.py` until growth justifies subpackages

## Error Rules

- shared custom errors may live in root `errors.py`
- core raises business errors
- raise integration errors from `outbound`
- usecases may propagate existing errors and may raise orchestration-specific errors only when the failure is about usecase flow itself
- do not define custom errors inside `inbound`
- `inbound` must translate custom errors into HTTP/UI/CLI/agent-friendly outputs
- if errors grow significantly, split root `errors.py` into subpackages later

---

## Testing

### Unit
- core logic
- rules
- source kind
- parse
- category
- combine
- usecases

### Integration
- outbound modules

Rules:
- must run locally
- no real external systems
- use fixtures or monkeypatch

---

## Development Flow

1. define types
2. parse source
3. categorize units
4. combine if needed
5. apply rules
6. orchestrate in usecase
7. test

---

## Important Constraint

Focus on document complexity, not provider abstraction.
