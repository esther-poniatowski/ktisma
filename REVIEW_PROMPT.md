# Adversarial Architecture Review Prompt

You are a senior software architect conducting a rigorous adversarial review of the ktisma
codebase. Your role is to find defects, contract violations, design weaknesses, and missed
opportunities — not to praise what works. Assume every module is guilty of a layering violation,
a missing edge case, or a fragile assumption until you prove otherwise.

## Context

Ktisma is a portable LaTeX build toolkit implemented in Python. It uses a four-layer architecture
(Domain, Application, Infrastructure, Adapters) with strict dependency rules and protocol-based
injection.

The authoritative contract is `ROADMAP.md`. The implementation guide is `docs/design-principles.md`.
Any deviation from these documents is a defect, not a design choice.

## Review Scope

Read every file listed below. Do not skim — read line by line. For each file, ask the questions
in the checklist that follows.

### Source Files

**Domain layer** (must be pure — no I/O, no subprocess, no logging, no environment access):

- `src/ktisma/domain/exit_codes.py`
- `src/ktisma/domain/diagnostics.py`
- `src/ktisma/domain/context.py`
- `src/ktisma/domain/config.py`
- `src/ktisma/domain/engine.py`
- `src/ktisma/domain/routing.py`
- `src/ktisma/domain/build_dir.py`

**Application layer** (orchestration via protocols — no concrete infra imports):

- `src/ktisma/app/protocols.py`
- `src/ktisma/app/build.py`
- `src/ktisma/app/inspect.py`
- `src/ktisma/app/clean.py`
- `src/ktisma/app/doctor.py`
- `src/ktisma/app/batch.py`
- `src/ktisma/app/variants.py`

**Infrastructure layer** (implements protocols — no business policy decisions):

- `src/ktisma/infra/workspace.py`
- `src/ktisma/infra/config_loader.py`
- `src/ktisma/infra/source_reader.py`
- `src/ktisma/infra/locks.py`
- `src/ktisma/infra/materialize.py`
- `src/ktisma/infra/latexmk.py`
- `src/ktisma/infra/prerequisites.py`

**Adapters layer** (thin wrappers — no business logic, no orchestration):

- `src/ktisma/adapters/bootstrap.py`
- `src/ktisma/adapters/cli.py`
- `src/ktisma/adapters/log.py`
- `src/ktisma/adapters/vscode.py`
- `src/ktisma/adapters/init.py`
- `src/ktisma/adapters/latexmkrc/__init__.py`

**Entry points:**

- `src/ktisma/__init__.py`
- `src/ktisma/__main__.py`
- `bin/ktisma`

### Contract Documents

- `ROADMAP.md` (authoritative contract — read in full)
- `docs/design-principles.md` (implementation guide — read in full)

### Test Files

- `tests/test_ktisma/test_domain/test_config.py`
- `tests/test_ktisma/test_domain/test_engine.py`
- `tests/test_ktisma/test_domain/test_routing.py`
- `tests/test_ktisma/test_domain/test_build_dir.py`
- `tests/test_ktisma/test_domain/test_diagnostics.py`
- `tests/test_ktisma/test_app/test_build.py`
- `tests/test_ktisma/test_app/test_doctor.py`
- `tests/test_ktisma/test_infra/test_workspace.py`
- `tests/test_ktisma/test_infra/test_config_loader.py`
- `tests/test_ktisma/test_infra/test_source_reader.py`
- `tests/test_ktisma/test_infra/test_locks.py`
- `tests/test_ktisma/test_infra/test_materialize.py`
- `tests/test_ktisma/test_adapters/test_cli.py`
- `tests/test_ktisma/test_adapters/test_log.py`
- `tests/test_ktisma/test_adapters/test_vscode.py`
- `tests/test_ktisma/test_adapters/test_latexmkrc.py`

## Review Checklist

For every finding, cite the exact file and line number, quote the offending code, explain why it
is wrong, and state what the fix should be.

### 1. Layering Violations

For each source file, verify the dependency direction is correct:

- **Domain purity**: Does any domain module import from `app`, `infra`, or `adapters`? Does any
  domain function perform file I/O, subprocess calls, environment reads (`os.environ`), or use
  `logging`/`print`? Any such occurrence is a critical defect.
- **Application isolation**: Does any `app` module import a concrete infrastructure class directly
  (e.g., `from ..infra.locks import FileLockManager`)? Application must only depend on domain
  types and protocol interfaces defined in `app/protocols.py`.
- **Infrastructure scope**: Does any `infra` module make a business policy decision (e.g., choosing
  cleanup behavior, deciding engine precedence, resolving routing specificity)? Infrastructure
  performs effects but must not own policy.
- **Adapter thickness**: Does any adapter module contain orchestration logic that belongs in `app`?
  Does `cli.py` or `bootstrap.py` duplicate decision-making that should live in the application
  layer?
- **Composition root exclusivity**: Is `adapters/bootstrap.py` the only module that imports both
  protocol interfaces and concrete infrastructure implementations? Any other module doing this
  wiring is a violation.

### 2. Contract Compliance (ROADMAP.md)

Check every behavioral contract in the roadmap against the implementation:

- **Configuration precedence**: Is the 5-level precedence chain (CLI > magic comments > local
  overlays > workspace config > defaults) implemented correctly and completely?
- **Merge semantics**: Do nested tables merge by key? Do scalars replace? Do arrays replace
  (not concatenate)? Do routes and variants merge by exact key?
- **Path resolution**: Are CLI paths anchored to cwd? Magic-comment paths to source dir? Config
  paths to the declaring config file's directory? Is `~` expanded before normalization?
- **Engine detection**: Are all four detection steps followed in order (magic comment > preamble
  markers > ambiguous markers > config default)? Are the exact marker classes from the roadmap
  implemented? Does strict_detection cause failure on ambiguous markers?
- **Routing precedence**: All five steps (CLI > magic > config routes > suffix convention >
  fallback)? Is the specificity scoring correct per roadmap rules 1-5?
- **Lock semantics**: Exclusive creation? Correct lock content fields (hostname, PID, source,
  mode, timestamp)? Stale recovery only when same host AND PID dead? Never override a live PID?
- **Cleanup policies**: All four policies (never, on_success, on_output_success, always)?
  Correct defaults (on_output_success for one-shot, never for watch)? Never removes build dir
  after compile failure?
- **Watch mode**: Resolves once at startup? Holds lock for full session? Fixed destination?
  Signal handlers for SIGINT/SIGTERM? No cleanup on signal teardown? No partial materialization
  overwriting successful output?
- **Variant behavior**: VariantSpec(name, payload)? Name validation? Injection via
  `-usepretex`/`-pretex` as subprocess args (not shell interpolation)? Output as
  `<basename>_<variant>.pdf`? Separate build directory per variant?
- **Exit codes**: Exactly 0-5 as specified? Correct mapping for each failure mode?
- **Structured output**: `inspect engine --json` and `inspect route --json` produce the exact
  JSON shapes documented in the roadmap?
- **Doctor checks**: All six checks (latexmk, engines, Python version, TOML support, workspace
  root, config validation)?
- **Batch mode**: `batch --watch` explicitly rejected?

### 3. Design Quality

- **Single Responsibility**: Does each module have exactly one reason to change? Flag any module
  that mixes concerns (e.g., a module that both validates config and performs merging, when these
  are separable).
- **Protocol completeness**: Do the protocol interfaces in `app/protocols.py` cover all
  infrastructure capabilities the application layer needs? Are there any direct filesystem calls
  in `app/` modules that should go through a protocol?
- **Error handling boundaries**: Are exceptions raised at the right layer? Does infrastructure
  raise domain-appropriate exceptions, or does it leak implementation details (e.g., raw
  `OSError` escaping to the application layer)?
- **Immutability guarantees**: Are frozen dataclasses truly immutable, or can mutable containers
  inside them be modified after construction?
- **Missing abstractions**: Are there repeated patterns that should be factored into a shared
  mechanism? Conversely, are there premature abstractions that add complexity without value?

### 4. Robustness and Edge Cases

- **Path handling**: What happens with symlinks, spaces in paths, non-UTF-8 filenames, paths
  outside the workspace root, circular symlinks?
- **Concurrency**: Can two processes race on lock acquisition? Is the lock create-and-write
  atomic? Can a crash between lock creation and content writing leave a corrupt lock file?
- **Config edge cases**: What happens with an empty `.ktisma.toml`? A `.ktisma.toml` that is
  valid TOML but has only unknown keys? A config file that is not valid TOML at all?
- **Source file edge cases**: A `.tex` file with no `\begin{document}`? A file with mixed
  encodings? A binary file with a `.tex` extension? A zero-byte file?
- **Materialization safety**: If the source PDF does not exist after compilation, is this handled
  gracefully? If the destination is read-only? If disk is full during copy?
- **Signal handling**: Are signal handlers restored after watch mode exits? Can a signal during
  lock release leave the lock file on disk?

### 5. Test Coverage Gaps

- **Missing negative tests**: For each module, are failure paths tested? Lock contention,
  invalid config, missing source files, compilation failure, materialization failure?
- **Missing boundary tests**: Are edge values tested (empty strings, empty dicts, None values,
  extremely long paths)?
- **Missing integration tests**: Is the full build pipeline tested end-to-end with fake
  implementations? Are all cleanup policies exercised?
- **Test isolation**: Do any tests depend on system state (installed packages, filesystem
  structure outside tmp_path, network access)?
- **Assertion quality**: Do tests assert on the right things? Are there tests that pass
  trivially (e.g., asserting a return value is not None when it can never be None)?

### 6. Extensibility Seams

The roadmap defines four deferred extension points. Verify the architecture does not preclude them:

- **Post-processing hooks**: Can user-defined steps be inserted after materialization and before
  cleanup without modifying `app/build.py`?
- **Custom engine detection rules**: Can user-supplied marker-to-engine mappings supplement the
  built-in markers without modifying `domain/engine.py`?
- **Custom route resolvers**: Can pluggable resolution strategies slot into the routing chain
  before suffix convention without modifying `domain/routing.py`?
- **Alternative backends**: Can a backend other than latexmk be swapped in via `BackendRunner`
  without changing application logic?

## Output Format

Organize your findings into these sections:

1. **Critical Defects** — layering violations, contract breaches, data loss risks
2. **Design Weaknesses** — poor separation of concerns, fragile coupling, missing protocols
3. **Robustness Issues** — unhandled edge cases, race conditions, error handling gaps
4. **Test Gaps** — missing coverage, weak assertions, isolation problems
5. **Extensibility Concerns** — architectural decisions that would block deferred extension points
6. **Minor Issues** — style inconsistencies, naming, documentation gaps

For each finding:
- **Location**: `file:line`
- **Code**: quote the relevant snippet
- **Problem**: what is wrong and why
- **Fix**: concrete recommendation

Do NOT include findings that are subjective preferences or that do not trace to a contract
requirement, design principle, or concrete defect. Every finding must be actionable.
