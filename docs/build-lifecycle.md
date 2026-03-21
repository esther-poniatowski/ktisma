# Build Lifecycle

This document covers the full build pipeline, watch mode, cleanup policies, lock semantics, and
variant handling.

## Build Pipeline

A `ktisma build` invocation follows these steps in order:

1. **Resolve workspace and source context**: Determine workspace root, source file, and source
   directory.
2. **Load and merge configuration**: Collect config layers (built-in defaults, workspace config,
   overlay configs, magic comments, CLI flags) and merge them with deterministic precedence.
3. **Read source inputs**: Extract preamble text and magic comments from the source file.
4. **Detect engine**: Select the LaTeX engine based on magic comments, preamble markers, and
   config defaults.
5. **Resolve route**: Determine the output PDF destination from overrides, route rules, suffix
   conventions, or fallback.
6. **Resolve variant**: If a variant was requested, validate and resolve it.
7. **Plan build directory**: Compute the build directory path, expected PDF path, and lock file
   path.
8. **Check prerequisites**: Verify `latexmk` and the selected engine are available.
9. **Acquire lock**: Obtain an exclusive build lock for the build directory.
10. **Compile**: Invoke `latexmk` in the planned build directory.
11. **Materialize output**: Copy the compiled PDF to its final destination (atomic write).
12. **Apply cleanup policy**: Remove the build directory based on the configured policy.
13. **Release lock**: Release the build lock.
14. **Return result**: Return a `BuildResult` with exit code, decisions, produced paths, and
    diagnostics.

If `--dry-run` is specified, the pipeline stops after step 7 and returns the plan without
performing any side effects.

## Build Directories

### Default Layout

Build directories are created inside the source file's directory:

```text
source-dir/
├── main.tex
└── .ktisma_build/
    ├── main/               # Build directory for main.tex
    │   ├── main.pdf        # Intermediate PDF
    │   ├── main.aux
    │   ├── main.log
    │   └── .ktisma.lock    # Build lock file
    └── main-corrected/     # Variant build directory
        ├── main.pdf
        └── .ktisma.lock
```

The build directory name is `<stem>/` for regular builds and `<stem>-<variant>/` for variant
builds. The directory name configured via `[build].out_dir_name` (default: `.ktisma_build`).

### Expected Artifact Path

The expected PDF is always `<build-dir>/<source-stem>.pdf`, matching `latexmk`'s output naming.

## Lock Semantics

Locks prevent concurrent builds of the same source file from corrupting intermediate artifacts.

### Lock File

- Path: `<build-dir>/.ktisma.lock`
- Creation: exclusive (`O_CREAT | O_EXCL`) to prevent races
- Contents: JSON with `hostname`, `pid`, `source`, `mode`, `created` (ISO timestamp)

### Acquisition

- If the lock file does not exist, create it atomically and write lock metadata.
- If the lock file exists, attempt recovery (see below).
- If recovery fails, raise `LockContention` (exit code 4).

### Stale Lock Recovery

A lock is considered stale only when **both** conditions are met:

1. The lock was created on the **same hostname** as the current process.
2. The owning **PID no longer exists**.

If the lock is from a different host, or the PID is still alive, the lock is considered live and
ktisma exits with a lock-contention error. Ktisma never guesses that a live lock is stale.

### Special Cases

- **Empty lock file** (crash between creation and write): treated as stale, removed, and
  acquisition retried.
- **Invalid JSON**: treated as contention (cannot determine owner).
- **Watch mode**: the lock is held for the entire session lifetime.

### Release

Lock release removes the lock file. Release is always attempted in a `finally` block to ensure
cleanup even on exceptions.

## Cleanup Policies

The cleanup policy determines whether the build directory is removed after compilation.

| Policy | Behavior |
| --- | --- |
| `never` | Never remove the build directory. |
| `on_success` | Remove after successful compilation. |
| `on_output_success` | Remove after successful compilation **and** successful materialization. |
| `always` | Remove regardless of outcome. |

### Defaults

| Mode | Default Policy |
| --- | --- |
| One-shot build | `on_output_success` |
| Watch mode | `never` |

### Safety Rules

- Cleanup **never** removes the build directory after a compile failure, regardless of the
  configured policy. Failed builds are preserved for inspection.
- Cleanup failure after a successful build emits a warning but does not change the exit code.
- Signal-driven teardown (SIGINT, SIGTERM) skips cleanup entirely.

## Watch Mode

Watch mode wraps `latexmk -pvc` in an application-level session.

### Session Lifecycle

1. **Startup**: Resolve config, engine, route, build directory, and variant once. These decisions
   are fixed for the session.
2. **Lock**: Acquire the build lock and hold it for the entire session.
3. **Launch**: Start `latexmk -pvc` as a subprocess against the planned build directory.
4. **Poll loop**: Monitor the subprocess for rebuild completions by tracking PDF modification
   times. After each successful rebuild, materialize the updated PDF to the fixed destination.
5. **Teardown**: On SIGINT or SIGTERM, terminate the subprocess, release the lock, and exit
   cleanly.

### Key Properties

- **Fixed decisions**: Config, route, and engine are resolved once. Changes require restarting
  the session.
- **Continuous lock**: The lock is held for the full session, preventing concurrent one-shot
  builds of the same source.
- **Safe materialization**: Partial materializations from interrupted rebuild cycles never
  overwrite a previously successful output.
- **No cleanup on signal**: The build directory is preserved on teardown for inspection.

### Incompatibilities

- `batch --watch` is explicitly rejected in v1.
- A one-shot build against the same source during a watch session fails with lock contention.
- Config hot-reload is not supported.

## Variants

Variants are named build profiles that inject TeX preamble content before compilation.

### Definition

Variants are defined in `.ktisma.toml`:

```toml
[variants]
blank = ""
corrected = "\\ForceSolutions"
```

Each key is a variant name; each value is a TeX preamble payload.

### Name Validation

Variant names must match `^[a-zA-Z][a-zA-Z0-9_-]*$`. Names that fail validation are rejected
with a diagnostic.

### Injection Mechanism

Variant payloads are passed to `latexmk` via `-usepretex` and `-pretex=<payload>` arguments.
The payload is passed as subprocess arguments, never through shell interpolation.

### Isolation

Each variant:

- Uses its own build directory: `<source-dir>/.ktisma_build/<stem>-<variant>/`
- Produces its own output: `<basename>_<variant>.pdf`
- Shares the same route resolution as the base document (only the filename differs)

### Building Variants

Build a single variant:

```bash
ktisma build exercises.tex --variant corrected
```

Build all configured variants:

```bash
ktisma variants exercises.tex --workspace-root .
```

An explicit payload can be provided without a config entry:

```bash
ktisma build exercises.tex --variant custom --variant-payload "\\ForceSolutions"
```

## Materialization

After successful compilation, the PDF is copied from the build directory to its final
destination.

### Atomic Writes

The materializer writes to a temporary file (`.tmp` suffix) first, then atomically renames it
to the final path. This prevents partial writes from corrupting the output if the process is
interrupted.

### Safety Guarantees

- Parent directories are created automatically.
- If the source PDF does not exist after compilation, the build is reported as failed.
- Materialization failure after a successful compile emits an error diagnostic but never
  destroys the build directory (the intermediate PDF is preserved).

## Prerequisite Checking

Before invoking `latexmk`, the build pipeline performs a fast prerequisite check:

1. Verify `latexmk` is on `PATH`.
2. Verify the selected engine is on `PATH`.

If either is missing, the build fails with exit code 3 (prerequisite failure) and a diagnostic
explaining what is missing.

For a comprehensive check, use `ktisma doctor`.
