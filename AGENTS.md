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
- must not depend on file formats or automation tools

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
Produce structured edit intents (no file or UI logic)

#### rules/
Business rules (accounting, invoice, settlement, validation)

Rules:
- core must not call outbound
- core operates on structured data only
- core must not depend on Excel, files, or UI automation
- core must not know how edits are applied

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
- document automation (Excel, RPA, COM)

Responsibilities:
- fetch/persist data
- convert structured data to bytes/files
- convert external responses to typed structures
- load sources from ECM, mail, SAP/API, files, or other external systems
- convert files, bytes, and external responses into typed structures
- apply edit intents to documents
- execute application-level automation when required (Excel, RPA, COM)
- manage external application sessions and execution lifecycle

Rules:
- no business logic
- no classification
- no rules
- must not import core
- must encapsulate all file libraries and automation tools

---

## Types

### types/

Typed structures.

Includes:
- source types
- parsed structures
- units
- bundles
- edit intents
- db records (when needed)
- results

Rules:
- use dataclasses
- reflect real data shapes
- allow multiple explicit types
- allow nested structures
- avoid unnecessary abstraction
- imports between types modules must remain acyclic

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
- types → types only if acyclic
- shared errors may live in root `errors.py`
- circular imports are not allowed

---

## Data Flow

source → parse → unit → category → combine → analyze → rules → edit

---

## Document Editing / Automation

- core must produce structured edit intents only
- outbound must apply edit intents to documents
- file libraries (e.g. openpyxl) must stay in outbound
- automation tools (Excel COM, RPA) must stay in outbound
- workbook, worksheet, or UI automation objects must not escape outbound
- usecases must not depend on file or automation implementation details

Execution rules:
- prefer file-level processing (e.g. openpyxl) by default
- use application-level automation (Excel, RPA) only when required
- outbound is responsible for choosing execution strategy

Automation responsibilities (outbound):
- manage application sessions (start, reuse, terminate)
- handle file locks and concurrent access
- handle timeouts and retries
- handle popups or blocking states
- ensure document save correctness
- optionally verify results after write (read-back validation)
- trigger recalculation when needed

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
- keep shared custom errors in root `errors.py`

---

## Error Rules

- shared custom errors may live in root `errors.py`
- core raises business errors
- outbound raises integration errors (file, automation, external systems)
- usecases may propagate errors or raise orchestration-specific errors
- inbound translates errors into user-friendly outputs
- do not define custom errors inside inbound

---

## Testing

### Unit
- core logic
- rules
- source kind
- parse
- category
- combine
- edit
- usecases

### Integration
- outbound modules
- file handlers
- document automation (RPA, Excel)

Rules:
- must run locally
- no real external systems
- use fixtures or monkeypatch
- automation tests may be optional if environment-dependent

---

## Development Flow

1. define types
2. parse source
3. categorize units
4. combine if needed
5. analyze combined bundles
6. apply rules
7. produce edit intents
8. orchestrate in usecase
9. apply edits via outbound
10. test

---

## Important Constraint

Focus on document complexity, not provider abstraction.
