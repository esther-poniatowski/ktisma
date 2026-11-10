# CLI Reference

Ktisma exposes the `ktisma` console entry point (installed via `pip install`),
plus two alternative invocation forms:

```bash
ktisma <command> [options]
python3 -m ktisma <command> [options]
python3 /path/to/ktisma/bin/ktisma <command> [options]
```

## Global Options

| Flag | Description |
| --- | --- |
| `-v`, `--version` | Print the version of ktisma and exit |
| `--verbose` | Enable debug-level logging to stderr; it has no short form |

## Commands

### `build`

Compile a LaTeX document.

```bash
ktisma build <source.tex> [options]
```

| Option | Description |
| --- | --- |
| `source` | Path to the `.tex` source file (required) |
| `-r`, `--root PATH` | Set the workspace root folder, relative to the current folder; takes precedence over `KTISMA_ROOT` |
| `--engine ENGINE` | Override engine selection (`pdflatex`, `lualatex`, `xelatex`, `latex`) |
| `-o`, `--output PATH` | Override the exact output PDF path, relative to the current folder |
| `--output-dir PATH` | Override output directory for the compiled PDF |
| `--watch` | Enable continuous watch mode (wraps `latexmk -pvc`) |
| `--dry-run` | Show the build plan without compiling |
| `--variant NAME` | Build a specific named variant |
| `--variant-payload PAYLOAD` | Explicit TeX preamble payload for a variant |
| `--cleanup POLICY` | Override cleanup policy (`never`, `on_success`, `on_output_success`, `always`) |
| `--format FORMAT` | Output format: `text` (default) or `json` |

Examples:

```bash
# Basic build
ktisma build slides-tex/main.tex

# Build with engine override
ktisma build paper.tex --engine lualatex

# Watch mode
ktisma build slides-tex/main.tex --watch

# Dry run to inspect the plan
ktisma build slides-tex/main.tex --dry-run --format json

# Build a specific variant
ktisma build exercises.tex --variant corrected

# Build to an exact PDF path
ktisma build exercises.tex --output review-pdfs/exercises_review.pdf
```

### `inspect engine`

Show which LaTeX engine would be selected for a source file without compiling.

```bash
ktisma inspect engine <source.tex> [options]
```

| Option | Description |
| --- | --- |
| `source` | Path to the `.tex` source file (required) |
| `-r`, `--root PATH` | Set the workspace root folder, relative to the current folder; takes precedence over `KTISMA_ROOT` |
| `--engine ENGINE` | Override engine selection (shows what the override would be) |
| `--format FORMAT` | Output format: `text` (default) or `json` |

Human-readable output shows the engine name, detection evidence, and ambiguity status. JSON
output follows this shape:

```json
{
  "engine": "lualatex",
  "evidence": ["fontspec package detected in preamble"],
  "ambiguous": true,
  "diagnostics": [{"level": "warning", "code": "ambiguous-engine", "message": "..."}]
}
```

### `inspect route`

Show where the compiled PDF would be routed without compiling.

```bash
ktisma inspect route <source.tex> [options]
```

| Option | Description |
| --- | --- |
| `source` | Path to the `.tex` source file (required) |
| `-r`, `--root PATH` | Set the workspace root folder, relative to the current folder; takes precedence over `KTISMA_ROOT` |
| `-o`, `--output PATH` | Override the exact output PDF path, relative to the current folder |
| `--output-dir PATH` | Override output directory |
| `--format FORMAT` | Output format: `text` (default) or `json` |

JSON output shape:

```json
{
  "source": "lectures-tex/week1.tex",
  "destination": "lectures-pdfs/week1.pdf",
  "matched_rule": "lectures-tex/**",
  "fallback": false,
  "diagnostics": []
}
```

### `clean`

Remove build artifacts for a source file or a specific build directory.

```bash
ktisma clean <target> [options]
```

| Option | Description |
| --- | --- |
| `target` | Path to a `.tex` source file or a build directory (required) |
| `-r`, `--root PATH` | Set the workspace root folder, relative to the current folder; takes precedence over `KTISMA_ROOT` |

When given a `.tex` file, ktisma resolves the workspace root as `build` does, reads the same
configuration, and removes the corresponding build directory and any variant build directories.
When given a directory, ktisma verifies it is a ktisma build directory (by checking for
`.ktisma.lock` or a `.ktisma*` parent other than the state directory `.ktisma/`) before removing
it. `clean` removes only build directories, which the next build recreates, so it asks for no
confirmation.

```bash
# Clean build artifacts for a source file
ktisma clean slides-tex/main.tex

# Clean a specific build directory
ktisma clean slides-tex/.ktisma_build/main/
```

### `check-log`

Check retained LaTeX logs against a zero baseline after a build.

```bash
ktisma check-log [--build-dir NAME] [--channel TAGS] <source-dir> [stem]
```

| Argument or option | Description |
| --- | --- |
| `source-dir` | Directory holding the sources and build directory |
| `stem` | Optional document stem; without it, every retained log is checked |
| `--build-dir NAME` | Build directory relative to `source-dir` (default: `.ktisma_build`) |
| `--channel TAGS` | Comma-separated measurement channels to print; repeatable |

The command searches recursively below the build directory. Each selected log must report
`Output written`. Its zero baseline covers fatal errors, LaTeX font warnings, TeX error lines in
both supported forms, and overfull or underfull horizontal or vertical boxes. Requested channel
lines are reported without affecting the exit status.

A log need not be valid UTF-8: pdfTeX wraps log lines after a fixed number of bytes, which can
split a multi-byte character, and it prints the glyphs of 8-bit font encodings as raw bytes. Each
invalid byte sequence is read as the replacement character `�`. Every pattern of the baseline is
ASCII, so the counts are those of the raw bytes, and a reported line shows `�` where its bytes were
invalid.

```bash
ktisma check-log --channel banner,fit,layout posters/tex poster
```

The command exits with code `1` when a log violates the baseline or when the build directory or
selected logs are absent. A missing source directory is a usage error and exits with code `2`.

### `doctor`

Verify that prerequisites are available.

```bash
ktisma doctor [options]
```

| Option | Description |
| --- | --- |
| `-r`, `--root PATH` | Set the workspace root folder, relative to the current folder; takes precedence over `KTISMA_ROOT` |
| `--format FORMAT` | Output format: `text` (default) or `json` |

Checks performed:

1. `latexmk` is on `PATH`
2. Configured default engines are available
3. Python meets the minimum version (3.12+)
4. The workspace root resolves (from `--root`, `KTISMA_ROOT`, or the search from the current folder)
5. The settings files of that workspace root validate successfully

Human-readable output displays a status table with `[ok]` or `[MISSING]` for each check.

### `batch`

Build batch-entrypoint `.tex` files in a directory tree.

```bash
ktisma batch <source-dir> [options]
```

| Option | Description |
| --- | --- |
| `source_dir` | Directory containing `.tex` entrypoints or nested entrypoint directories (required) |
| `-r`, `--root PATH` | Set the workspace root folder, relative to the current folder; takes precedence over `KTISMA_ROOT` |
| `--engine ENGINE` | Override engine for all builds |
| `--watch` | **Rejected** in v1 (batch watch mode is not supported) |
| `--format FORMAT` | Output format: `text` (default) or `json` |

Ktisma searches recursively, collecting `.tex` files directly inside `source_dir` plus nested
entrypoints (`main.tex`, `index.tex`, or files containing a document preamble). Fragment files
without a preamble are skipped. If any build fails, the batch continues and returns
`COMPILATION_FAILURE` as the aggregate exit code.

### `variants`

Build all configured variants of a single source file.

```bash
ktisma variants <source.tex> [options]
```

| Option | Description |
| --- | --- |
| `source` | Path to the `.tex` source file (required) |
| `-r`, `--root PATH` | Set the workspace root folder, relative to the current folder; takes precedence over `KTISMA_ROOT` |
| `--engine ENGINE` | Override engine for all variants |
| `--include-default` | Build the non-variant output in addition to configured variants |
| `--format FORMAT` | Output format: `text` (default) or `json` |

Ktisma reads variant definitions from the `[variants]` section of the resolved configuration and
builds each one in a separate build directory. Output naming defaults to
`[routing].variant_filename_suffix` (default: `_{variant}`) and can be overridden per variant.
`--include-default` adds the non-variant build to the same run -- suited for dual-output
workflows such as `draft` + `review` or `student` + `annotated`.

### `init`

Generate a wrapper script and print VS Code LaTeX Workshop configuration.

```bash
ktisma init [options]
```

| Option | Description |
| --- | --- |
| `-r`, `--root PATH` | Set the workspace root folder, relative to the current folder; takes precedence over `KTISMA_ROOT` |
| `--force` | Overwrite an existing wrapper script |

The command creates `scripts/ktisma` in the workspace root -- a shell wrapper
that sets `KTISMA_ROOT` and delegates to the vendored ktisma entry
point -- and prints the VS Code configuration snippet to stdout. The wrapper may hold edits of the
researcher, so an existing wrapper is overwritten only with `--force`. Without `--force`, the
command stops with exit code `2` and an error that names the wrapper, and writes nothing. The
command writes no settings file.

### `tex`

Manage the dependency closure declared by `[[tex.dependencies]]` in the workspace-root
`ktisma.toml`.

```bash
ktisma tex install [--root PATH] [--format FORMAT]
ktisma tex check [--root PATH] [--format FORMAT]
ktisma tex inspect [--root PATH] [--format FORMAT]
ktisma tex resolve DEPENDENCY:ENTRYPOINT [--root PATH] [--format FORMAT]
```

| Command | Result |
| --- | --- |
| `tex install` | Fetches each exact commit, runs its registered builder, verifies the assembled tree, and selects the immutable snapshot |
| `tex check` | Verifies the selected snapshot, its receipt, every file digest, and every declared TeX entry point |
| `tex inspect` | Returns the same validated state with its record digest, snapshot path, receipt, and resolved entry points |
| `tex resolve` | Verifies the selected snapshot and prints the absolute path of one qualified entry point |

Only `tex install` changes dependency state by fetching sources and running package builders. By
contrast, every other command, and normal document builds, only check the current snapshot.
Accordingly, a build must stop before LaTeX when the snapshot is absent or stale, or when a file
digest or resolved path fails its check.

Plain output from `tex resolve` is the selected path alone. Therefore, another installed command can
consume the path directly. For machine-readable output, `--format json` adds the logical identifier
and record digest.

## Exit Codes

| Code | Meaning |
| --- | --- |
| `0` | Success |
| `1` | Compilation failure (the backend reported an error) |
| `2` | Configuration or contract error |
| `3` | Prerequisite failure |
| `4` | Lock contention |
| `5` | Internal or unexpected runtime error |

Safe routing fallback does not change a successful exit status.

## Output Modes

**Human mode** (default): diagnostics are printed to stderr with color when connected to a
terminal. Success messages and file paths go to stdout.

**JSON mode** (`--format json`): structured JSON is written to stdout. Diagnostics are not printed to
stderr separately — they are included in the JSON output. Human formatting is never mixed into
JSON output.

## Diagnostics

All commands may emit structured diagnostics at three levels:

- **info**: informational notes (e.g., fallback routing was used)
- **warning**: non-fatal issues (e.g., ambiguous engine detection)
- **error**: failures that prevent the operation from completing

In human mode, diagnostics are formatted as:

```text
warning: [ambiguous-engine] Ambiguous modern-engine markers found; using lualatex
  - fontspec package detected in preamble
```
