# Configuration Reference

Ktisma uses a single configuration format: TOML files named `.ktisma.toml`.

## File Format

TOML is the only supported format. Ktisma uses `tomllib` (Python 3.11+) or `tomli` (Python
3.9-3.10) for parsing. No INI, YAML, shell fragments, or custom parsers are supported.

## Full Example

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
default_filename_suffix = ""
variant_filename_suffix = "_{variant}"

[routes]
"lectures-tex/**" = "lectures-pdfs/"
"drafts/*.tex" = "output/"
"thesis/main.tex" = "~/Documents/thesis-builds/"

[variants.review]
payload = "\\def\\ShowReviewMarkup{}"
filename_suffix = "_review"
```

## Schema Reference

### Top Level

| Key | Type | Default | Description |
| --- | --- | --- | --- |
| `schema_version` | integer | `1` | Config schema version. When absent, version 1 is assumed. |

### `[build]`

| Key | Type | Default | Description |
| --- | --- | --- | --- |
| `out_dir_name` | string | `".ktisma_build"` | Name of the build directory created inside the source directory. |
| `cleanup` | string | `"on_output_success"` | Cleanup policy. One of: `never`, `on_success`, `on_output_success`, `always`. |
| `synctex` | boolean | `true` | Enable SyncTeX output for editor integration. |

### `[engines]`

| Key | Type | Default | Description |
| --- | --- | --- | --- |
| `default` | string | `"pdflatex"` | Default engine when no markers are detected. |
| `modern_default` | string | `"lualatex"` | Engine used when only ambiguous modern-engine markers are found. |
| `strict_detection` | boolean | `false` | When `true`, ambiguous markers cause an error instead of falling back to `modern_default`. |

Valid engine values: `pdflatex`, `lualatex`, `xelatex`, `latex`.

### `[routing]`

| Key | Type | Default | Description |
| --- | --- | --- | --- |
| `source_suffix` | string | `"-tex"` | Suffix identifying source directories (e.g., `lectures-tex/`). |
| `output_suffix` | string | `"-pdfs"` | Suffix for the corresponding output directories (e.g., `lectures-pdfs/`). |
| `preserve_relative` | boolean | `true` | Preserve relative path structure from source to output. |
| `collapse_entrypoint_names` | boolean | `false` | Collapse entrypoint filenames into parent directory names. |
| `entrypoint_names` | array of strings | `["main", "index"]` | Filenames eligible for entrypoint collapse. |
| `default_filename_suffix` | string | `""` | Suffix template appended to non-variant outputs before `.pdf`. Supports `{stem}` and `{variant}` placeholders. |
| `variant_filename_suffix` | string | `_{variant}` | Default suffix template appended to variant outputs before `.pdf`. Supports `{stem}` and `{variant}` placeholders. |

### `[routes]`

Explicit routing rules mapping source file patterns to output destinations.

```toml
[routes]
"lectures-tex/**" = "lectures-pdfs/"
"thesis/main.tex" = "~/Documents/thesis-builds/"
```

Patterns use glob syntax. Targets ending in `/` are treated as directories; the source basename
is preserved. Targets with a file extension are treated as explicit file paths.

### `[variants]`

Named build variants. Variants support two forms:

```toml
[variants]
review = "\\def\\ShowReviewMarkup{}"

[variants.handout]
payload = "\\def\\HandoutMode{}"
engine = "lualatex"
output = "../review-pdfs/"
filename_suffix = "_handout"
```

- **String form**: the value is a TeX preamble payload injected via `latexmk -usepretex`.
- **Table form**: supports:
  - `payload`: TeX preamble payload
  - `engine`: variant-specific engine override
  - `output`: variant-specific output directory or explicit output file, resolved relative to the source file directory
  - `filename_suffix`: variant-specific filename suffix template, overriding `[routing].variant_filename_suffix`

Variant names must match the pattern `^[a-zA-Z][a-zA-Z0-9_-]*$` and be safe for use in
filenames.

## Configuration Precedence

Highest priority first:

1. **CLI flags** (`--engine`, `--output`, `--output-dir`, `--cleanup`)
2. **Per-file magic comments** (`% !TeX program = ...`, `% !ktisma output = ...`)
3. **Project-local `.ktisma.toml` overlays** between the source directory and the workspace root
4. **Workspace `.ktisma.toml`** at the workspace root
5. **Built-in defaults**

### Concern-Specific Precedence

| Concern | Precedence (highest first) |
| --- | --- |
| Engine | `--engine` > variant `engine` > `% !TeX program` / marker detection > `[engines].default` |
| Routing | `--output` > `--output-dir` > variant `output` > `% !ktisma output` > custom route resolvers > `[routes]` > `[routing]` suffix convention > fallback beside source |
| Cleanup | CLI > nearest config > workspace config > built-in default |
| Variants | CLI explicit variant > config-defined variant map |

## Merge Semantics

When multiple config layers are present, they merge with these rules:

- **Nested tables** (e.g., `[build]`, `[engines]`) merge by key. A key in a higher-precedence
  layer overrides the same key from a lower layer, but other keys in the table are preserved.
- **Scalars** replace lower-precedence values entirely.
- **Arrays** replace lower-precedence values entirely (no concatenation).
- **`[routes]`** merges by exact pattern key. If the same glob pattern appears in multiple
  layers, the higher-precedence layer wins for that pattern.
- **`[variants]`** merges by exact variant name, same as routes.

### Example

Workspace `.ktisma.toml`:

```toml
[engines]
default = "pdflatex"
modern_default = "lualatex"

[routes]
"lectures-tex/**" = "lectures-pdfs/"
"drafts/*.tex" = "output/"
```

Subdirectory `.ktisma.toml`:

```toml
[engines]
default = "xelatex"

[routes]
"drafts/*.tex" = "final/"
```

Merged result:

```toml
[engines]
default = "xelatex"          # overridden by subdirectory
modern_default = "lualatex"   # preserved from workspace

[routes]
"lectures-tex/**" = "lectures-pdfs/"   # preserved from workspace
"drafts/*.tex" = "final/"              # overridden by subdirectory
```

## Path Resolution

Path anchoring is deterministic based on where the path was declared:

| Source | Anchor |
| --- | --- |
| CLI flags | Current working directory |
| Magic comments (`% !ktisma output = ...`) | Source file directory |
| `.ktisma.toml` route targets | Directory of the config file that declared the path |
| Variant `output` values | Source file directory |

Processing steps:

1. `~` is expanded to the user's home directory.
2. Relative paths are resolved against their anchor.
3. All paths are normalized to absolute `Path` objects at the application boundary.

## Workspace Root Resolution

The workspace root determines where ktisma searches for `.ktisma.toml` files and anchors
workspace-relative paths. Resolution order:

1. `--workspace-root` CLI flag
2. `KTISMA_WORKSPACE_ROOT` environment variable
3. Adapter-provided workspace root (e.g., from VS Code)
4. Outermost ancestor directory containing `.ktisma.toml`
5. Current working directory

The workspace root is never inferred from `.git` or other unrelated files.

## Magic Comments

Magic comments are `%`-prefixed directives in the source file, recognized before
`\begin{document}`:

```latex
% !TeX program = lualatex
% !ktisma output = ../output/
```

| Comment | Effect |
| --- | --- |
| `% !TeX program = <engine>` | Override engine selection |
| `% !ktisma output = <path>` | Override output destination |

Paths in magic comments resolve relative to the source file's directory.

## Schema Versioning

The top-level `schema_version` key declares which config schema the file targets:

- When absent, schema version 1 is assumed.
- Keys introduced in a later schema version are errors under an earlier version.
- This allows config files to opt into new features without breaking older ktisma installations.

## Validation

Validation happens when config is loaded, not when values are accessed:

- Unknown keys for the declared schema version are errors.
- Type mismatches are errors.
- Invalid enum values (e.g., `cleanup = "maybe"`) are errors.
- Route targets that normalize outside the intended filesystem root are allowed when explicit;
  ktisma does not silently rewrite them.
