# Design Principles

Implementation guide for ktisma.

This document governs coding style, module boundaries, testing discipline, and implementation
patterns. It does not define the public product contract.

Authority order:

1. `ROADMAP.md` defines the architecture, CLI surface, and behavioral contract.
2. This file explains how to implement that contract cleanly.
3. `README.md` is a user-facing summary.

If this document ever disagrees with `ROADMAP.md`, the roadmap wins and this file must be updated.

## 1. Architectural Layering

Ktisma uses four layers.

| Layer | Responsibility | May Depend On |
| --- | --- | --- |
| Domain | Pure policy, typed models, merge rules, engine detection, routing decisions, build planning | stdlib, type helpers |
| Application | Use-cases and orchestration | Domain, infrastructure via protocol interfaces |
| Infrastructure | Filesystem, config loading, lockfiles, subprocess, prerequisite probing | Domain types, application-defined protocols (implements them) |
| Adapters | CLI, editor integration, diagnostic rendering, composition root | Application |

### 1.1 Rules

- Domain code must be pure. No file reads, file writes, subprocesses, environment access, or
  logging side effects.
- Application code sequences work, applies recovery behavior, and maps use-cases to domain and
  infrastructure calls.
- Infrastructure performs effects but does not own policy. It should not silently decide routing,
  cleanup, or precedence behavior on its own.
- Adapters are thin. They parse external input, call application use-cases, and format output.

### 1.2 Dependency Direction

- Adapters -> Application -> Domain
- Application -> Infrastructure via protocol interfaces defined in the application layer.
  Application modules must not import concrete infrastructure modules directly.
- Infrastructure implements application-defined protocols and may depend on domain types.
- Never Domain -> Infrastructure
- Never Domain -> Adapters

### 1.3 Boundary Smells

Treat these as design failures:

- a domain function that reads a file path
- a routing resolver that moves or copies a PDF
- a config model that loads TOML from disk by itself
- a CLI command that reimplements orchestration logic
- an application module that imports a concrete infrastructure module instead of using a protocol

## 2. Package Structure

The package should be organized by layer, not by arbitrary file count.

```text
ktisma/
    __init__.py
    __main__.py
    adapters/
        __init__.py
        bootstrap.py      # composition root: wires infra into app
        cli.py
        log.py
        vscode.py
        init.py
        latexmkrc/         # generates transitional .latexmkrc shims
    app/
        __init__.py
        protocols.py       # infrastructure protocol interfaces
        build.py
        inspect.py
        clean.py
        doctor.py
        batch.py
        variants.py
    domain/
        __init__.py
        context.py
        config.py
        diagnostics.py
        engine.py
        routing.py
        build_dir.py
        exit_codes.py
    infra/
        __init__.py
        workspace.py
        config_loader.py
        source_reader.py
        locks.py
        materialize.py
        latexmk.py
        prerequisites.py
bin/
    ktisma
tests/
    fixtures/
docs/
```

Use relative imports within the package and absolute imports in tests.

## 3. Data Objects and Contracts

### 3.1 Typed Boundaries

Do not pass raw dictionaries or loosely structured tuples across module boundaries when a named
type is warranted.

Use typed objects such as:

- `SourceContext`
- `ToolkitInfo`
- `BuildRequest`
- `ResolvedConfig`
- `SourceInputs`
- `EngineDecision`
- `RouteDecision`
- `BuildDirPlan`
- `VariantSpec`
- `BuildResult`
- `Diagnostic`

### 3.2 Dataclasses

Use `@dataclass(frozen=True)` for decision objects and other inter-layer data where practical.

Examples:

- `EngineDecision`
- `RouteDecision`
- `BuildDirPlan`
- `VariantSpec`
- `Diagnostic`

Mutable containers inside frozen dataclasses must use `field(default_factory=...)`.

### 3.3 Enumerations

Use `Enum` for closed sets such as cleanup policy, diagnostic level, and exit-code categories.
Do not spread magic strings through the codebase.

## 4. Data Flow and I/O Isolation

### 4.1 Inward Flow

```text
Adapter input -> Application request objects -> Domain decisions
                               |
                               -> Infrastructure effects
```

### 4.2 Outward Flow

```text
Domain/Application/Infrastructure diagnostics -> Adapter formatter -> stderr / JSON / editor
```

### 4.3 Pure Domain Inputs

Pure domain functions consume already-extracted data.

Preferred:

```python
def detect_engine(source_inputs: SourceInputs, config: ResolvedConfig) -> EngineDecision:
    ...
```

Avoid:

```python
def detect_engine(source_path: Path, config_path: Path) -> EngineDecision:
    ...
```

The second form hides I/O behind what should be a policy function.

## 5. Configuration Management

### 5.1 Contract Source

The public config contract lives in `ROADMAP.md`. This file only constrains how to implement it.

### 5.2 Parsing vs. Policy

- Infrastructure parses TOML from disk.
- Domain owns typed config models, validation rules, defaults, and pure merge behavior.
- Application coordinates layer collection and surfaces validation failures.

### 5.3 Merge Rules

Implementation must preserve the roadmap semantics exactly:

- nested tables merge by key
- scalars replace
- arrays replace
- routes merge by exact pattern key
- variants merge by exact name

Do not introduce special cases in code that are not documented in the roadmap.

### 5.4 Path Anchoring

Preserve provenance for any config or magic-comment path until it has been anchored correctly.

- config-relative paths anchor to the declaring config file
- magic-comment paths anchor to the source file directory
- CLI paths anchor to the current working directory

Do not flatten everything into strings too early.

## 6. Workflow Orchestration

### 6.1 Application Responsibilities

The build use-case should sequence the following steps and nothing more:

1. Resolve workspace and source context.
2. Load and merge configuration layers.
3. Read source inputs.
4. Resolve engine.
5. Resolve route.
6. Plan build directory.
7. Acquire lock.
8. Run backend compilation.
9. Materialize final output.
10. Apply cleanup policy.
11. Return a structured result with diagnostics.

### 6.2 Reuse

- `inspect` reuses the same config and decision path but stops before compilation.
- `clean` reuses build-directory resolution and cleanup primitives.
- `doctor` reuses infrastructure probes and returns structured diagnostics.
- `batch` and `variants` compose the same build use-case rather than forking it.

### 6.3 Recovery Rules

- If engine detection fails, stop early with a clear error.
- If explicit routing cannot produce a destination, fall back beside the source file when the
  roadmap says to do so.
- If cleanup fails after a successful build, emit a warning but preserve success.
- A successful PDF must never be lost due to cleanup or routing mistakes.

## 7. Watch Mode

Watch mode is a long-lived application session, not an adapter trick.

Implementation requirements:

- resolve config, route, engine, and variant once at startup
- hold the build lock for the full session
- keep the final destination fixed for the session
- materialize the updated PDF after each successful rebuild
- require restart for config or route changes

Do not add hidden hot reload or per-cycle policy changes without updating the roadmap first.

Signal handling:

- Register handlers for SIGINT and SIGTERM that terminate the backend subprocess, release the
  build lock, and exit cleanly.
- Do not apply cleanup policy on signal-driven teardown. Preserve the build directory for
  inspection.
- Do not overwrite a previously successful output with a partial materialization from an
  interrupted rebuild cycle.

## 8. Variants

Treat variants as validated structured input.

- Parse user input into `VariantSpec`.
- Validate variant names before any filesystem or subprocess work.
- Pass variant payloads as subprocess arguments, never through shell interpolation.
- Keep variant naming, routing, and artifact isolation consistent with the roadmap.

Do not let teaching-specific variant names become architecture.

## 9. Diagnostics, Errors, and Logging

### 9.1 Diagnostics as Data

User-facing diagnostics are structured records, not ad hoc formatted strings deep in the stack.

Each diagnostic should carry:

- level
- component
- code
- human-readable message
- optional provenance or evidence metadata

### 9.2 Formatting Boundary

Adapters own rendering:

- human-readable stderr
- machine-readable JSON
- editor-facing formatting

Domain and application code should create diagnostics, not print them.

### 9.3 Exceptions

Use ktisma-specific exceptions for unrecoverable failures.

- configuration errors
- prerequisite failures
- compilation failures
- lock contention
- internal errors

Exceptions may carry context, but the CLI should map them to documented exit codes instead of
inventing per-call behavior.

### 9.4 Logging

The Python `logging` module is optional developer instrumentation, not the primary user-diagnostic
channel.

- Configure logging in adapters only.
- Never rely on logging side effects for core behavior.
- Never use `print()` for diagnostics in domain, application, or infrastructure code.

## 10. Object Design

### 10.1 Prefer Functions for Pure Policy

Use standalone functions for pure transformations such as:

- merging config models
- detecting the engine
- resolving routes
- planning build directories

Use classes only when an object has real state or when a protocol is useful.

### 10.2 Protocols Over Deep Inheritance

Use `Protocol` interfaces for all infrastructure capabilities consumed by the application layer.
These protocols are defined in the application layer and implemented by infrastructure.

Required protocols:

- `ConfigLoader`: load raw config layers from disk.
- `SourceReader`: read source content and extract magic comments.
- `LockManager`: acquire, release, and recover build locks.
- `BackendRunner`: invoke the compilation backend and return structured results.
- `Materializer`: copy or move build artifacts to final destinations.
- `PrerequisiteProbe`: check availability of required external tools.

Avoid deep inheritance trees and god objects.

### 10.3 Composition Root

All wiring of concrete infrastructure into application use-cases happens in
`adapters/bootstrap.py`. This is the only module that imports both application protocols and
concrete infrastructure implementations. `__main__.py` delegates to the composition root
immediately after argument parsing.

### 10.4 No Hidden Singletons

Do not use:

- global registries
- mutable module-level caches for config or route state
- service locators

Pass dependencies explicitly.

## 11. Typing

### 11.1 Baseline

Target Python 3.9+.

- Use PEP 585 built-in generics such as `list[str]`.
- Use syntax compatible with Python 3.9 for unions, such as `Optional[str]`, unless the minimum
  supported version is raised.
- Add `from __future__ import annotations` where it simplifies forward references.

### 11.2 Requirements

- Annotate all function signatures.
- Annotate dataclass fields.
- Annotate module-level constants that carry semantic meaning.
- Use `TypeAlias` for repeated complex types.

## 12. Path and Subprocess Handling

### 12.1 Paths

- Use `pathlib.Path` everywhere.
- Normalize paths at the application boundary after provenance-aware anchoring.
- Keep source, workspace, toolkit, build, and destination paths distinct in typed objects.

### 12.2 Filesystem Mutation

- Prefer atomic or near-atomic operations where practical.
- Create lock files with exclusive semantics.
- Do not delete build artifacts unless the cleanup policy explicitly allows it.
- Never remove a build directory just because routing fell back.

### 12.3 Subprocesses

- Use argument vectors, not shell command strings.
- Do not use `shell=True`.
- Keep backend invocation code in infrastructure.
- Capture stdout/stderr in a form the application can attach to results or diagnostics.

## 13. Testing

### 13.1 Structure

Mirror the layered architecture in tests:

- domain unit tests
- infrastructure unit tests
- application integration tests
- adapter smoke tests

### 13.2 Domain Tests

Domain tests must be pure.

- no filesystem
- no subprocess
- no environment dependence

Test exact precedence, merge, and fallback behavior with controlled inputs.

### 13.3 Infrastructure Tests

Use `tmp_path` and focused mocking for:

- config loading
- lockfile behavior
- materialization behavior
- prerequisite probing
- backend invocation wrappers

### 13.4 Application Tests

Exercise real orchestration with fake protocol implementations or controlled fixtures.

Cover:

- successful build flow
- compile failure
- lock contention
- safe routing fallback
- cleanup behavior
- watch session setup
- variant isolation

### 13.5 Adapter Tests

Keep adapter tests thin:

- CLI parsing
- exit-code mapping
- diagnostic formatting
- generated VS Code snippets or assets

### 13.6 Framework

Use `pytest`.

Prefer parametrized tests and fixtures. Avoid `unittest.TestCase` unless interoperability forces it.

## 14. Documentation Discipline

- Do not add a second authoritative contract document.
- When behavior changes, update `ROADMAP.md` first, then this file, then `README.md`.
- Document deferred behavior explicitly instead of leaving silent gaps.
- Keep examples synchronized with the actual contract.

## 15. Anti-Patterns to Avoid

- competing architecture documents
- I/O hidden inside domain functions
- adapter code that duplicates build logic
- source-order-sensitive routing behavior when specificity rules exist
- shell interpolation for variant payloads
- silent fallback that discards provenance or diagnostics
- cleanup that can destroy the only successful PDF
- auto-removing a live lock because it "looks old"
