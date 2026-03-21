# Roadmap

Authoritative architecture and rollout contract for ktisma.

This file is the source of truth for:

- the public CLI surface
- layering and dependency boundaries
- configuration semantics
- routing, watch mode, and variant behavior
- implementation sequencing

`README.md` is a user-facing summary. `docs/design-principles.md` governs implementation style and
coding standards, but it must not redefine any public contract described here.

This roadmap is derived from the existing LaTeX build infrastructure in:

- `/Users/eresther/Documents/work/techne/`
- `/Users/eresther/Documents/work/research/RS-ctx-dep-net/`
- `/Users/eresther/Documents/teaching/thoth/`

It replaces the earlier split design based on VS Code shell snippets, `latexmkrc` hooks, and many
tiny helper scripts.

## Objectives

- Provide one canonical entry point for build, inspect, clean, and prerequisite checks.
- Keep build rules independent from VS Code, shell glue, and `latexmkrc`.
- Model a real infrastructure boundary instead of smearing file I/O and subprocess work into the
  domain layer.
- Make workspace and configuration resolution explicit and predictable.
- Preserve the final PDF safely by default, even when routing conventions do not match.
- Support layered configuration with deterministic precedence, merge, and path-resolution rules.
- Guard against concurrent builds of the same source file.
- Define watch mode and variant behavior explicitly rather than leaving them as backend accidents.
- Interleave testing with each implementation phase.
- Prove the core contract in one real workspace before broad rollout.

## Non-Goals for v1

- No implicit workspace-root discovery from `.git`, `.latexmkrc`, or similar incidental files.
- No hot reload of `.ktisma.toml` during watch mode.
- No batch watch mode.
- No include-following beyond the main-file preamble in the initial engine detector.
- No lossy rewriting of arbitrary JSONC workspace files.

## Target Architecture

### Layering

| Layer | Responsibility | Typical Modules |
| --- | --- | --- |
| Domain | Pure decisions, typed models, merge rules, engine detection, routing decisions, build planning | `domain/context.py`, `domain/config.py`, `domain/diagnostics.py`, `domain/engine.py`, `domain/routing.py`, `domain/build_dir.py`, `domain/exit_codes.py`, `domain/errors.py` |
| Application | Use-cases and orchestration | `app/protocols.py`, `app/configuration.py`, `app/build.py`, `app/inspect.py`, `app/clean.py`, `app/doctor.py`, `app/batch.py`, `app/variants.py` |
| Infrastructure | Filesystem, TOML loading, source reading, lockfiles, PDF materialization, subprocess execution, prerequisite probing | `infra/workspace.py`, `infra/config_loader.py`, `infra/source_reader.py`, `infra/locks.py`, `infra/materialize.py`, `infra/latexmk.py`, `infra/prerequisites.py` |
| Adapters | CLI, editor integration, diagnostic formatting, composition root, optional compatibility shims | `adapters/cli.py`, `adapters/bootstrap.py`, `adapters/log.py`, `adapters/vscode.py`, `adapters/init.py`, `adapters/latexmkrc/` |

### Dependency Rules

- Adapters depend on application.
- Application depends on domain. Application depends on infrastructure through protocol
  interfaces defined in the application layer, not through concrete imports.
- Infrastructure implements application-defined protocols and may depend on domain types. Domain
  never depends on infrastructure or adapters.
- Domain modules are pure: no filesystem reads, no subprocess calls, no logging side effects.
- Application modules sequence work and choose recovery behavior. They receive infrastructure
  capabilities as injected protocol implementations, never by importing concrete infrastructure
  modules directly.
- Infrastructure modules perform effects but do not own business policy.

### Protocol Boundaries

Application defines protocol interfaces for replaceable infrastructure capabilities:

- `ConfigLoader`: load and return raw config layers from disk.
- `SourceReader`: read source file content and extract magic comments.
- `LockManager`: acquire, release, and recover build locks.
- `BackendRunner`: invoke the compilation backend and return structured results.
- `Materializer`: copy or move build artifacts to final destinations.
- `PrerequisiteProbe`: check whether required external tools are available.
- `WorkspaceOps`: create directories, check paths, list entries, remove trees, and glob files.

Infrastructure provides concrete implementations. Adapters wire concrete implementations into
application use-cases via a composition root.

### Composition Root

The composition root lives in `adapters/bootstrap.py`. It constructs concrete infrastructure
implementations and injects them into application use-cases. No other module performs this wiring.
`__main__.py` delegates to the composition root immediately after argument parsing.

### Adapter Notes

`adapters/latexmkrc/` generates minimal `.latexmkrc` shims for workspaces transitioning from
standalone latexmk configurations to ktisma. It does not read or parse existing `.latexmkrc` files.
This adapter is optional and does not affect the core build path.

### Stable Public Interfaces

Ktisma exposes exactly two supported front doors:

- `python3 -m ktisma ...`
- `python3 /path/to/ktisma/bin/ktisma ...`

The internal module layout is not public API.

Initial public commands:

- `build <source.tex>`
- `inspect engine <source.tex>`
- `inspect route <source.tex>`
- `clean <source.tex|build-dir>`
- `doctor`

Later public commands:

- `batch <source-dir>`
- `variants <source.tex>`

Deferred adapter command:

- `init <workspace-root>` only after workspace-edit behavior is proven safe

### Core Data Model

- `SourceContext`: source file, source directory, workspace root. Spatial context only.
- `ToolkitInfo`: toolkit root and installation mode. Passed separately from source context.
- `BuildRequest`: operation intent such as `watch`, `dry_run`, explicit overrides, and optional
  variant selection.
- `ResolvedConfig`: built-in defaults plus merged config layers and provenance metadata.
- `SourceInputs`: preamble text plus extracted magic comments.
- `EngineDecision`: selected engine, evidence, ambiguity status, diagnostics.
- `RouteDecision`: selected destination, naming policy, matched source, fallback status,
  diagnostics.
- `BuildDirPlan`: deterministic build directory and expected artifact paths.
- `VariantSpec`: validated variant name plus TeX preamble injection payload.
- `BuildResult`: outcome, produced paths, diagnostics, and backend result data.
- `Diagnostic`: structured warning, info, or error record that adapters format for humans or tools.

Behavioral mode lives in `BuildRequest`, not in `SourceContext`.

## Configuration Model

### Single Configuration Format

Use TOML in `.ktisma.toml`.

- Python 3.11+: `tomllib`
- Python 3.9-3.10: `tomli`

TOML is the only supported user configuration format. No INI, YAML, shell fragments, or custom
parsers.

Example:

```toml
schema_version = 1

[build]
out_dir_name = ".ktisma_build"
cleanup = "on_output_success"
synctex = true

[engines]
default = "pdflatex"
modern_default = "lualatex"
strict_detection = false

[routing]
source_suffix = "-tex"
output_suffix = "-pdfs"
preserve_relative = true
collapse_entrypoint_names = false
entrypoint_names = ["main", "index"]

[routes]
"lectures-tex/**" = "lectures-pdfs/"
"drafts/*.tex" = "output/"
"thesis/main.tex" = "~/Documents/thesis-builds/"

[variants]
blank = ""
corrected = "\\ForceSolutions"
```

### Configuration Precedence

Highest priority first:

1. CLI flags
2. Per-file magic comments
3. Project-local `.ktisma.toml` overlays between the source directory and the workspace root
4. Workspace `.ktisma.toml`
5. Built-in defaults

Concern-specific precedence:

| Concern | Precedence |
| --- | --- |
| Engine selection | `--engine` > `% !TeX program = ...` > config override > detector > `[engines].default` |
| Routing | `--output-dir` > `% !ktisma output = ...` > `[routes]` > `[routing]` suffix convention > safe fallback |
| Cleanup | CLI > nearest config > workspace config > built-in default |
| Variants | CLI explicit variant > config-defined variant map |

### Merge Semantics

Merge behavior is part of the public contract:

- Nested tables merge by key.
- Scalars replace lower-precedence values.
- Arrays replace lower-precedence values; they do not concatenate.
- `[routes]` merges by exact pattern key.
- `[variants]` merges by exact variant name.
- If the same route pattern or variant name appears in multiple layers, the higher-precedence layer
  wins entirely for that key.

### Path Resolution Semantics

Path anchoring must be deterministic:

- CLI paths resolve relative to the current working directory.
- Paths from `% !ktisma output = ...` resolve relative to the source file directory.
- Paths from `.ktisma.toml` resolve relative to the directory of the config file that declared them.
- `~` is expanded before normalization.
- Resolved paths are normalized to absolute `Path` objects at the application boundary.

### Schema Versioning

The top-level key `schema_version` declares which config schema the file targets. When absent,
schema version 1 is assumed. Ktisma validates keys against the declared schema version: a key
introduced in schema version 2 is not an error when `schema_version = 2`, but is an error when
`schema_version = 1` or absent.

This allows config files to opt into new features without breaking older ktisma installations, and
allows ktisma to reject genuinely unknown keys without false positives during schema evolution.

### Validation

Validation happens when config is loaded, not when values are first accessed.

- Unsupported keys for the declared schema version are errors, not silently ignored.
- Type mismatches are errors.
- Invalid enum values are errors.
- Route targets that normalize outside the intended filesystem root are allowed only when explicit;
  ktisma does not silently rewrite them.

### Workspace Root Resolution

The workspace root must not be inferred from `.git` or other unrelated files.

Resolution order:

1. `--workspace-root`
2. `KTISMA_WORKSPACE_ROOT`
3. Adapter-provided workspace root
4. Nearest ancestor containing `.ktisma.toml`
5. Current working directory

## Engine Detection Policy

### Engine Input Boundary

Infrastructure reads the source file and extracts magic comments and preamble text.
Domain detection consumes typed `SourceInputs` and `ResolvedConfig`.

### Detection Steps

1. Honor `% !TeX program = ...` if present.
2. Scan the main-file preamble up to `\begin{document}`.
3. Classify definitive and ambiguous engine markers.
4. If no marker is found, use config default.

Include-following is deferred from v1. Documents whose engine-specific setup lives in included
files must pin their engine via magic comment or config.

### Marker Classes

Definitive XeLaTeX markers:

- `\RequireXeTeX`
- `ifxetex`
- XeTeX primitives

Definitive LuaLaTeX markers:

- `\RequireLuaTeX`
- `luacode`
- `directlua`
- `ifluatex`

Ambiguous "modern engine required" markers:

- `fontspec`
- `polyglossia`
- `unicode-math`

### Ambiguity Policy

If only ambiguous markers are found:

- select `[engines].modern_default` (default: `lualatex`)
- emit a diagnostic explaining the ambiguity
- fail instead when `strict_detection = true`

## Routing Policy

### Routing Input Boundary

Infrastructure extracts magic comments and loads config route rules.
Domain routing resolves a destination from typed inputs; it does not read files or move PDFs.

### Resolution Chain

Routing precedence is:

1. CLI output override
2. Magic-comment output override
3. Explicit config route rules
4. Suffix convention
5. Safe fallback beside the source file

The final step always resolves a route. Routing mismatch is not allowed to strand the only
successful PDF in a later-cleaned build directory.

### Route Rule Specificity

If multiple config route rules match in the same precedence layer:

1. Prefer exact file matches over glob matches.
2. Otherwise prefer the rule with more literal path segments.
3. Otherwise prefer the rule with fewer wildcard segments.
4. If the remaining candidates resolve to the same destination, the ambiguity is harmless and
   ktisma proceeds silently.
5. Otherwise emit a diagnostic warning and use the first matching rule in declaration order.
   This keeps a working config from breaking when a second rule is added, while still surfacing
   the ambiguity for the user to resolve.

### Default Naming Policy

Built-in convention:

- `*-tex/` maps to sibling `*-pdfs/`
- preserve relative path beneath the source root
- preserve the source basename

Examples:

- `presentations-tex/file.tex` -> `presentations-pdfs/file.pdf`
- `presentations-tex/deck/main.tex` -> `presentations-pdfs/deck/main.pdf`

### Optional Entrypoint Collapse

Repositories that prefer:

- `presentations-tex/deck/main.tex` -> `presentations-pdfs/deck.pdf`

may opt in with:

- `collapse_entrypoint_names = true`
- `entrypoint_names = ["main", "index"]`

### Fallback Behavior

If no explicit rule or convention applies:

- materialize the PDF next to the source file
- emit a diagnostic explaining that fallback routing was used
- keep the build successful unless the fallback materialization itself fails

## Build and Artifact Policy

### Responsibility Split

| Concern | Owner | Nature |
| --- | --- | --- |
| Build directory planning | Domain | Pure |
| Lock acquisition and release | Infrastructure | Effectful |
| `latexmk` invocation | Infrastructure, orchestrated by application | Effectful |
| PDF materialization | Infrastructure, chosen by application | Effectful |
| Cleanup policy decision | Domain | Pure |
| Cleanup execution | Infrastructure, triggered by application | Effectful |

### Build Directories

Default pattern:

- `<source-dir>/.ktisma_build/<stem>/`
- `<source-dir>/.ktisma_build/<stem>-<variant>/` for variants

The build directory naming does not expose the backend implementation.

### Lock Semantics

Locking is required for builds of the same source file and build directory.

- Lock file path: `<build-dir>/.ktisma.lock`
- Acquisition uses exclusive creation.
- Lock contents include hostname, PID, source path, mode, and creation timestamp.
- The watch session holds the lock for its full lifetime.
- Automatic stale-lock recovery is allowed only when the lock was created on the same host and the
  owning PID no longer exists.
- Timeout is advisory for diagnostics; it must not override a live PID.
- If the lock cannot be safely recovered, ktisma exits with a dedicated lock-contention code.

### Cleanup Policies

Supported policies:

- `never`: never remove the build directory.
- `on_success`: remove the build directory after successful compilation.
- `on_output_success`: remove the build directory after successful compilation and successful
  materialization of the final output to its destination.
- `always`: remove the build directory regardless of outcome.

Defaults:

- one-shot build: `on_output_success`
- watch mode: `never`

Cleanup must never remove the build directory after compile failure or failed post-processing that
could still be needed for inspection.

## Watch Mode Policy

Watch mode is an application-level session wrapped around `latexmk -pvc`.

### Session Contract

- Resolve context, config, engine, route, build directory, and variant once at startup.
- Acquire and hold the build lock for the entire session.
- Launch `latexmk -pvc` against the planned build directory.
- Treat the resolved destination as fixed for the session.
- After each successful rebuild, materialize the updated PDF from the fixed build artifact path to
  the fixed final destination.

### Session Teardown

- On SIGINT or SIGTERM, ktisma must terminate the `latexmk -pvc` subprocess, release the build
  lock, and exit cleanly. Partial materializations from an interrupted rebuild cycle must not
  overwrite a previously successful output.
- On abnormal termination (SIGKILL, power loss), the lock file remains on disk. The stale-lock
  recovery rules in the lock semantics section apply on the next invocation.
- Cleanup policy does not apply on signal-driven teardown. The build directory is preserved so the
  user can inspect intermediate artifacts.

### Interactions

- Cleanup defaults to `never`.
- Config changes require restarting the watch session.
- Route and variant changes require restarting the watch session.
- `batch --watch` is unsupported in v1 and must be rejected explicitly.
- A second one-shot build against the same source during watch mode must fail with lock contention.

## Variant Policy

### User-Facing Contract

Variants are named build profiles, not arbitrary shell snippets.

- Config source: `[variants]`
- CLI source: explicit variant name or explicit `NAME=MACRO_PAYLOAD` pair
- Internal representation: `VariantSpec(name, payload)`

Variant names must match a conservative identifier pattern and must be safe to use in filenames.

### Injection Mechanism

The backend injection mechanism is `latexmk -usepretex` / `-pretex`.

- The application layer constructs the argument vector.
- Injection is passed as subprocess arguments, never via shell interpolation.
- The variant payload is TeX preamble text, not shell code.

### Output and Isolation

- Variant outputs materialize as `<basename>_<variant>.pdf`.
- Each variant uses its own build directory.
- Route resolution is shared with the base document; output naming is the only variant-specific
  routing change in v1.

### Deferred Richer Model

If a richer variant model is needed later, add it as a higher-level schema on top of
`VariantSpec`. Do not couple the public architecture to teaching-specific `blank` / `corrected`
profiles.

## Prerequisite Checking

### `ktisma doctor`

`doctor` is an application use-case backed by infrastructure checks.

It verifies:

- `latexmk` is on `PATH`
- configured default engines are available
- Python meets the minimum version requirement
- `tomli` is importable on Python < 3.11
- workspace root resolution works
- any present `.ktisma.toml` validates successfully

The build path also performs a fast prerequisite check before invoking `latexmk`.

## Diagnostics and Exit Codes

Diagnostics are structured data produced by domain, application, and infrastructure components and
formatted only by adapters.

Initial exit codes:

- `0`: success
- `1`: compilation failure (the backend reported an error)
- `2`: configuration or contract error
- `3`: prerequisite failure
- `4`: lock contention
- `5`: internal or unexpected runtime error

Safe routing fallback does not change a successful exit status.

### Structured Output

`inspect` commands support a `--json` flag that emits machine-readable JSON to stdout. The JSON
schema is part of the public contract.

`inspect engine` JSON shape:

```json
{
  "engine": "lualatex",
  "evidence": ["fontspec package detected in preamble"],
  "ambiguous": true,
  "diagnostics": [{"level": "warning", "code": "ambiguous-engine", "message": "..."}]
}
```

`inspect route` JSON shape:

```json
{
  "source": "lectures-tex/week1.tex",
  "destination": "lectures-pdfs/week1.pdf",
  "matched_rule": "lectures-tex/**",
  "fallback": false,
  "diagnostics": []
}
```

Human-readable output is the default. Adapters must not mix human formatting into JSON output.

## Deferred Extension Seams

The following extension points are not part of v1 but are anticipated. The architecture must not
preclude them.

- **Post-processing hooks**: user-defined steps that run after successful materialization (e.g.,
  watermarking, `pdftk` merging). These will compose after the materializer, before cleanup.
- **Custom engine detection rules**: user-supplied marker-to-engine mappings that supplement the
  built-in marker classes.
- **Custom route resolvers**: pluggable resolution strategies that slot into the routing chain
  before the suffix convention step.
- **Alternative backends**: compilation backends other than `latexmk` (e.g., `tectonic`),
  introduced via the `BackendRunner` protocol without changing application logic.

Each seam corresponds to an existing protocol boundary or decision point. No plugin registry or
dynamic loading is required: protocol implementations can be swapped at the composition root.

## Implementation Phases

### Phase 0: Contract Alignment

- [ ] Keep `ROADMAP.md` authoritative.
- [ ] Reduce `README.md` to a user-facing summary.
- [ ] Ensure `docs/design-principles.md` matches this contract without redefining it.
- [ ] Freeze the initial public CLI commands.
- [ ] Freeze `.ktisma.toml` schema, merge rules, and path-resolution semantics.
- [ ] Freeze routing, lock, watch, variant, and diagnostic behavior.

Deliverable: one coherent contract with no competing architecture documents.

### Phase 1: Domain Layer and Protocol Definitions

- [ ] Create domain packages and data models (`SourceContext`, `ToolkitInfo`, `BuildRequest`, etc.).
- [ ] Implement `Diagnostic` and exit-code definitions.
- [ ] Implement typed config models and pure merge logic.
- [ ] Implement pure engine detection from `SourceInputs`.
- [ ] Implement pure routing from typed inputs.
- [ ] Implement pure build-directory planning.
- [ ] Define application-layer protocol interfaces (`ConfigLoader`, `SourceReader`, `LockManager`,
  `BackendRunner`, `Materializer`, `PrerequisiteProbe`).
- [ ] Write unit tests for each pure module.

Deliverable: a fully testable policy core with no I/O, plus the protocol contracts that
infrastructure will implement.

### Phase 2: Infrastructure and Core Application

- [ ] Implement concrete infrastructure modules against the protocol interfaces.
- [ ] Implement workspace-root resolution and config loading in infrastructure.
- [ ] Implement source reading and magic-comment extraction in infrastructure.
- [ ] Implement lock acquisition and recovery rules in infrastructure.
- [ ] Implement `latexmk` invocation wrapper in infrastructure.
- [ ] Implement PDF materialization and cleanup primitives in infrastructure.
- [ ] Implement `build`, `inspect`, `clean`, and `doctor` use-cases in application, receiving
  infrastructure through protocol injection.
- [ ] Write unit tests for infrastructure helpers and integration tests for the use-cases.

Deliverable: one command path that handles a real build end to end with correct side-effect
boundaries.

### Phase 3: CLI and Editor Adapters

- [ ] Implement the composition root in `adapters/bootstrap.py`.
- [ ] Implement the canonical CLI adapter.
- [ ] Format diagnostics for stderr and machine-readable JSON output (`--json`).
- [ ] Support vendored use via `bin/ktisma`.
- [ ] Provide VS Code LaTeX Workshop helper assets that call ktisma directly.
- [ ] Keep `init` deferred until adapter edit behavior is proven safe.

Deliverable: adapters that wrap the core instead of bypassing it.

### Phase 4: Extended Modes

- [ ] Add batch mode on top of the same build use-case.
- [ ] Add variant mode on top of the same build use-case.
- [ ] Defer include-following in the engine detector to this phase, with explicit depth and file
  count limits.
- [ ] Write tests for batch isolation, variant isolation, and bounded include-following.

Deliverable: extended modes that compose the same core API.

### Phase 5: CI and Coverage Audit

- [ ] Use `pytest` for all tests.
- [ ] Cover domain precedence and merge semantics exactly.
- [ ] Cover safe fallback routing and cleanup behavior.
- [ ] Cover lock contention and stale-lock recovery.
- [ ] Cover watch-mode session behavior.
- [ ] Run the suite in CI across supported Python versions.
- [ ] Add TeX-enabled integration coverage in a reproducible Linux environment.
- [ ] Add macOS smoke coverage for path handling and adapters.

Deliverable: confidence in the contract before wide adoption.

### Phase 6: Pilot Migration and Rollout

- [ ] Migrate one workspace manually.
- [ ] Compare behavior against the incumbent scripts.
- [ ] Verify engine overrides, routing, watch mode, cleanup, and variants in real usage.
- [ ] Roll out incrementally to the remaining workspaces.
- [ ] Remove duplicated helper scripts only after parity is observed, not assumed.

Deliverable: migration based on observed parity.

## Design Principles Summary

- One front door: adapters wrap the canonical CLI.
- One contract: this roadmap is authoritative.
- Pure policy, effectful infrastructure: no hidden I/O in the domain layer.
- Safe output semantics: the only successful PDF must survive post-processing mistakes.
- Explicit precedence: config, routing, and workspace resolution must be traceable.
- Lossless defaults: preserve relative paths and basenames unless repositories opt into a more
  opinionated policy.
- Conservative concurrency: never guess that a live lock is stale.
- Thin adapters: editor integration is convenience, not the source of truth.
