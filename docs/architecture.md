# Architecture

Technical reference for ktisma's internal structure, layering, protocols, and data flow.

## Layers

Ktisma is organized into four layers, each with a distinct responsibility and strict dependency
rules.

```text
┌─────────────────────────────────────────────────────┐
│  Adapters                                           │
│  CLI, editor integration, composition root          │
├─────────────────────────────────────────────────────┤
│  Application                                        │
│  Use-case orchestration, protocol definitions       │
├──────────────────────┬──────────────────────────────┤
│  Domain              │  Infrastructure              │
│  Pure policy,        │  Filesystem, subprocess,     │
│  typed models        │  protocol implementations    │
└──────────────────────┴──────────────────────────────┘
```

### Domain (`domain/`)

Pure policy layer. Every function is deterministic and side-effect-free: no filesystem reads,
no subprocess calls, no logging, no environment access.

| Module | Responsibility |
| --- | --- |
| `context.py` | Core data types: `SourceContext`, `ToolkitInfo`, `BuildRequest`, `SourceInputs`, `VariantSpec` |
| `config.py` | Configuration models (`ResolvedConfig`, `ConfigLayer`, `BuildConfig`, `EngineConfig`, `RoutingConfig`), schema validation, merge logic |
| `diagnostics.py` | `Diagnostic` record and `DiagnosticLevel` enum |
| `engine.py` | Engine detection from preamble markers and magic comments (`EngineDecision`) |
| `routing.py` | Output path resolution from config routes, suffix conventions, and fallback (`RouteDecision`) |
| `build_dir.py` | Build directory layout planning (`BuildDirPlan`) |
| `exit_codes.py` | `ExitCode` enum (0-5) |
| `errors.py` | Exception hierarchy: `KtismaError`, `ConfigError`, `ConfigLoadError`, `PrerequisiteError`, `LockContention` |

### Application (`app/`)

Orchestration layer. Sequences domain decisions and infrastructure effects through protocol
interfaces. Application modules never import concrete infrastructure modules directly.

| Module | Responsibility |
| --- | --- |
| `protocols.py` | Protocol interfaces for all infrastructure capabilities, plus `BackendResult`, `WatchUpdate`, `PrerequisiteCheck` |
| `configuration.py` | Config layer loading, merging, and validation orchestration |
| `build.py` | Full build use-case: config -> detection -> routing -> compilation -> materialization -> cleanup |
| `inspect.py` | Read-only engine and route inspection (reuses config/detection path, stops before compilation) |
| `clean.py` | Build artifact removal for source files or build directories |
| `doctor.py` | Prerequisite verification: latexmk, engines, Python version, TOML support, config validation |
| `batch.py` | Build all `.tex` files in a directory (sequential, shared infrastructure) |
| `variants.py` | Build all configured variants of a single source file |

### Infrastructure (`infra/`)

Effectful layer. Implements application-defined protocols. Performs filesystem I/O, subprocess
execution, and system probing but does not own business policy.

| Module | Class | Protocol |
| --- | --- | --- |
| `workspace.py` | `FileWorkspaceOps` | `WorkspaceOps` |
| `config_loader.py` | `TomlConfigLoader` | `ConfigLoader` |
| `source_reader.py` | `FileSourceReader` | `SourceReader` |
| `locks.py` | `FileLockManager` | `LockManager` |
| `materialize.py` | `FileMaterializer` | `Materializer` |
| `latexmk.py` | `LatexmkRunner` | `BackendRunner` |
| `latexmk.py` | `LatexmkWatchSession` | `WatchSession` |
| `prerequisites.py` | `SystemPrerequisiteProbe` | `PrerequisiteProbe` |

`workspace.py` also provides the standalone function `resolve_workspace_root()` for workspace root
resolution.

### Adapters (`adapters/`)

Thin wrappers that parse external input, dispatch to application use-cases, and format output.

| Module | Responsibility |
| --- | --- |
| `cli.py` | Argument parsing, command dispatch, human and JSON output formatting |
| `bootstrap.py` | Composition root: creates infrastructure instances and wires them into application use-cases |
| `log.py` | Logging setup and diagnostic formatting (color-aware) |
| `vscode.py` | LaTeX Workshop configuration generation |
| `init.py` | Deferred `init` command placeholder |
| `latexmkrc/` | Transitional `.latexmkrc` shim generation |

## Dependency Rules

```text
Adapters  ──→  Application  ──→  Domain
                    │
                    │ (via protocols)
                    ▼
              Infrastructure  ──→  Domain
```

- Domain never imports from application, infrastructure, or adapters.
- Application imports domain types and defines protocol interfaces. It never imports concrete
  infrastructure classes.
- Infrastructure implements application-defined protocols and may import domain types.
- Adapters import from application (and transitively from domain). Only the composition root
  (`bootstrap.py`) imports concrete infrastructure classes.

## Protocol Boundaries

Application defines seven protocol interfaces that infrastructure must satisfy:

| Protocol | Methods | Purpose |
| --- | --- | --- |
| `ConfigLoader` | `load_layers()` | Load raw TOML config layers from disk |
| `SourceReader` | `read_source()` | Read source file content and extract magic comments |
| `LockManager` | `acquire()`, `release()` | Exclusive build lock management |
| `BackendRunner` | `compile()`, `start_watch()` | Invoke compilation backend |
| `Materializer` | `materialize()` | Copy build artifacts to final destinations |
| `WorkspaceOps` | `ensure_directory()`, `path_exists()`, `is_directory()`, `list_directory()`, `remove_tree()`, `glob_files()` | Filesystem operations |
| `PrerequisiteProbe` | `check_latexmk()`, `check_engine()`, `check_python_version()`, `check_toml_support()` | System prerequisite checks |

Two additional protocols support extension points:

| Protocol | Methods | Purpose |
| --- | --- | --- |
| `PostProcessor` | `process()` | User-defined steps after materialization |
| `WatchSession` | `poll()`, `terminate()` | Long-lived watch mode session |

## Composition Root

`adapters/bootstrap.py` is the single module that wires concrete infrastructure into application
use-cases. It:

1. Instantiates all infrastructure implementations (`TomlConfigLoader`, `FileSourceReader`,
   `FileLockManager`, `LatexmkRunner`, `FileMaterializer`, `SystemPrerequisiteProbe`,
   `FileWorkspaceOps`).
2. Resolves workspace root and constructs `SourceContext`.
3. Calls the appropriate application function with all dependencies injected.

No other module performs this wiring.

## Core Data Flow

### Build Pipeline

```text
CLI args
  │
  ▼
BuildRequest + SourceContext
  │
  ├──→ ConfigLoader.load_layers()  ──→  merge_config_layers()  ──→  ResolvedConfig
  │
  ├──→ SourceReader.read_source()  ──→  SourceInputs
  │
  ├──→ detect_engine(SourceInputs, ResolvedConfig)  ──→  EngineDecision
  │
  ├──→ resolve_route(SourceContext, SourceInputs, ResolvedConfig)  ──→  RouteDecision
  │
  ├──→ plan_build_dir(SourceContext, ResolvedConfig, variant)  ──→  BuildDirPlan
  │
  ├──→ LockManager.acquire()
  │
  ├──→ BackendRunner.compile()  ──→  BackendResult
  │
  ├──→ Materializer.materialize()
  │
  ├──→ cleanup (conditional on policy)
  │
  └──→ BuildResult
```

### Diagnostic Flow

```text
Domain/Application/Infrastructure
  │
  │  create Diagnostic records
  │
  ▼
Adapter formatter
  │
  ├──→ stderr (human-readable, color-aware)
  └──→ stdout (JSON, when --json is passed)
```

Diagnostics are structured data throughout the stack. Only adapters render them for display.

## Entry Points

Ktisma exposes two supported entry points:

- **Module**: `python3 -m ktisma ...` (via `__main__.py`)
- **Vendored script**: `python3 /path/to/ktisma/bin/ktisma ...` (adds `src/` to `sys.path`)

Both delegate to `adapters.cli.main()`.

## Module Inventory

```text
src/ktisma/
├── __init__.py              Package root (__version__)
├── __main__.py              Module entry point
├── domain/
│   ├── context.py           SourceContext, ToolkitInfo, BuildRequest, SourceInputs, VariantSpec
│   ├── config.py            ResolvedConfig, ConfigLayer, validation, merge logic
│   ├── diagnostics.py       Diagnostic, DiagnosticLevel
│   ├── engine.py            EngineDecision, detect_engine(), marker definitions
│   ├── routing.py           RouteDecision, resolve_route(), suffix conventions
│   ├── build_dir.py         BuildDirPlan, plan_build_dir()
│   ├── exit_codes.py        ExitCode enum (0-5)
│   └── errors.py            KtismaError hierarchy
├── app/
│   ├── protocols.py         Protocol interfaces, BackendResult, WatchUpdate, PrerequisiteCheck
│   ├── configuration.py     load_resolved_config()
│   ├── build.py             execute_build(), BuildResult
│   ├── inspect.py           inspect_engine(), inspect_route()
│   ├── clean.py             execute_clean(), CleanResult
│   ├── doctor.py            execute_doctor(), DoctorResult
│   ├── batch.py             execute_batch(), BatchResult
│   └── variants.py          execute_variants(), VariantsResult
├── infra/
│   ├── workspace.py         FileWorkspaceOps, resolve_workspace_root()
│   ├── config_loader.py     TomlConfigLoader
│   ├── source_reader.py     FileSourceReader
│   ├── locks.py             FileLockManager
│   ├── materialize.py       FileMaterializer
│   ├── latexmk.py           LatexmkRunner, LatexmkWatchSession
│   └── prerequisites.py     SystemPrerequisiteProbe
├── adapters/
│   ├── cli.py               CLI argument parsing and command handlers
│   ├── bootstrap.py         Composition root
│   ├── log.py               Logging setup, diagnostic formatting
│   ├── vscode.py            LaTeX Workshop config generation
│   ├── init.py              Deferred init command
│   └── latexmkrc/           Transitional .latexmkrc generation
└── bin/
    └── ktisma               Vendored entry point script
```
