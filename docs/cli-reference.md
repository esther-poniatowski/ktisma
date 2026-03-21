# CLI Reference

Ktisma provides two equivalent entry points:

```bash
python3 -m ktisma <command> [options]
python3 /path/to/ktisma/bin/ktisma <command> [options]
```

## Global Options

| Flag | Description |
| --- | --- |
| `--verbose`, `-v` | Enable debug-level logging to stderr |

## Commands

### `build`

Compile a LaTeX document.

```bash
ktisma build <source.tex> [options]
```

| Option | Description |
| --- | --- |
| `source` | Path to the `.tex` source file (required) |
| `--workspace-root PATH` | Set workspace root directory |
| `--engine ENGINE` | Override engine selection (`pdflatex`, `lualatex`, `xelatex`, `latex`) |
| `--output-dir PATH` | Override output directory for the compiled PDF |
| `--watch` | Enable continuous watch mode (wraps `latexmk -pvc`) |
| `--dry-run` | Show the build plan without compiling |
| `--variant NAME` | Build a specific named variant |
| `--variant-payload PAYLOAD` | Explicit TeX preamble payload for a variant |
| `--cleanup POLICY` | Override cleanup policy (`never`, `on_success`, `on_output_success`, `always`) |
| `--json` | Emit machine-readable JSON to stdout |

Examples:

```bash
# Basic build
ktisma build slides-tex/main.tex --workspace-root .

# Build with engine override
ktisma build paper.tex --engine lualatex

# Watch mode
ktisma build slides-tex/main.tex --watch --workspace-root .

# Dry run to inspect the plan
ktisma build slides-tex/main.tex --dry-run --json

# Build a specific variant
ktisma build exercises.tex --variant corrected
```

### `inspect engine`

Show which LaTeX engine would be selected for a source file without compiling.

```bash
ktisma inspect engine <source.tex> [options]
```

| Option | Description |
| --- | --- |
| `source` | Path to the `.tex` source file (required) |
| `--workspace-root PATH` | Set workspace root directory |
| `--engine ENGINE` | Override engine selection (shows what the override would be) |
| `--json` | Emit JSON output |

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
| `--workspace-root PATH` | Set workspace root directory |
| `--output-dir PATH` | Override output directory |
| `--json` | Emit JSON output |

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
| `--workspace-root PATH` | Set workspace root directory |

When given a `.tex` file, ktisma removes the corresponding build directory and any variant build
directories. When given a directory, ktisma verifies it is a ktisma build directory (by checking
for `.ktisma.lock` or a `.ktisma*` parent) before removing it.

```bash
# Clean build artifacts for a source file
ktisma clean slides-tex/main.tex --workspace-root .

# Clean a specific build directory
ktisma clean slides-tex/.ktisma_build/main/
```

### `doctor`

Verify that prerequisites are available.

```bash
ktisma doctor [options]
```

| Option | Description |
| --- | --- |
| `--workspace-root PATH` | Set workspace root directory |
| `--json` | Emit JSON output |

Checks performed:

1. `latexmk` is on `PATH`
2. Configured default engines are available
3. Python meets the minimum version (3.9+)
4. TOML parsing support is available (`tomllib` or `tomli`)
5. Workspace root resolution works (if `--workspace-root` is provided)
6. Any present `.ktisma.toml` validates successfully

Human-readable output displays a status table with `[ok]` or `[MISSING]` for each check.

### `batch`

Build all `.tex` files in a directory.

```bash
ktisma batch <source-dir> [options]
```

| Option | Description |
| --- | --- |
| `source_dir` | Directory containing `.tex` files (required) |
| `--workspace-root PATH` | Set workspace root directory |
| `--engine ENGINE` | Override engine for all builds |
| `--watch` | **Rejected** in v1 (batch watch mode is not supported) |
| `--json` | Emit JSON output |

Each `.tex` file is built sequentially using the same `build` pipeline. If any file fails, the
batch continues and returns `COMPILATION_FAILURE` as the aggregate exit code.

### `variants`

Build all configured variants of a single source file.

```bash
ktisma variants <source.tex> [options]
```

| Option | Description |
| --- | --- |
| `source` | Path to the `.tex` source file (required) |
| `--workspace-root PATH` | Set workspace root directory |
| `--engine ENGINE` | Override engine for all variants |
| `--json` | Emit JSON output |

Reads variant definitions from the `[variants]` section of the resolved configuration and builds
each one. Each variant uses its own build directory and produces output named
`<basename>_<variant>.pdf`.

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

**JSON mode** (`--json`): structured JSON is written to stdout. Diagnostics are not printed to
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
