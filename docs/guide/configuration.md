# Configuration Reference

Ktisma uses a single configuration format: TOML files named `ktisma.toml`.

## Configuration Files and Their Places

Ktisma stacks one configuration file per folder. Every configuration file is named `ktisma.toml`,
without a leading dot. A file named `.ktisma.toml` is not read: the former name is retired without
a fallback.

Two kinds of file are distinguished by their place:

- **The workspace-root file** holds the configuration of the whole workspace. It sits either in
  `config/tools/ktisma.toml` below the root or in `ktisma.toml` at the root. When both files exist,
  Ktisma stops with an error that names both files.
- **An overlay** holds the configuration of its own folder and of the folders below it. An overlay
  is always the file `ktisma.toml` in that folder.

The place `config/tools/` applies to the workspace-root file only. The reason lies in the definition
of the root file: it is the file read at the root folder, and the folder `config/tools/` groups the
configuration files of every tool of a repository at that level. An overlay, by contrast, is
defined by the folder that it configures, so it can sit nowhere else than in that folder.
Therefore, a file `config/tools/ktisma.toml` below the root is an overlay of the folder `config/tools/` itself, which
applies only to sources inside that folder.

The `.ktisma/` state directory at the root holds the TeX snapshots of `ktisma tex install`. It is
not a configuration file, and it keeps its name.

## File Format

TOML is the only supported format. Ktisma parses configuration with `tomllib` from the Python
3.12+ standard library. No INI, YAML, shell fragments, or custom parsers are supported.

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
| `schema_version` | integer | `1` | Config schema version. Version 2 enables managed TeX dependencies. |

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
| `artifact_dirs` | array of strings | `[]` | Workspace-relative glob patterns naming the directories that hold one artifact each; the nearest matching ancestor of a source supplies `{artifact}` in output paths. |

### `[placeholders]`

User-defined values substituted for `{name}` in the output path of a magic comment and in route
targets. A name is an identifier and may not shadow a built-in placeholder (`stem`, `artifact`,
`variant`). Layers merge by key. See [Placeholders in Output Paths](routing.md#placeholders-in-output-paths).

```toml
[placeholders]
author = "Doe"
```

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

### `[[tex.dependencies]]`

Schema version 2 lets the workspace root declare a reproducible TeX dependency closure. Each
dependency declares an exact Git commit, a registered builder and public package entry points.
Ktisma resolves every declared entry point from the installed tree.

```toml
schema_version = 2

[[tex.dependencies]]
name = "scholia"
repository = "https://github.com/esther-poniatowski/scholia.git"
commit = "0123456789abcdef0123456789abcdef01234567"
builder = "l3build"
provides = ["scholia.sty"]
```

| Key | Constraint |
| --- | --- |
| `name` | Unique lowercase identifier |
| `repository` | Nonempty Git repository location |
| `commit` | Full 40-character Git commit hash |
| `builder` | Identifier registered by the installed Ktisma adapters |
| `provides` | One or more unique package entry points resolved through the managed TeX tree |

Ktisma registers the `l3build` adapter. This adapter invokes the package's ordinary
`l3build install --texmfhome <package-tree>` target. Package-specific target names and source-tree
paths do not enter the dependency record.

A dependency can expose TeX files and companion resources as package entry points. Each exposed
entry point has a qualified identifier of the form `<dependency-name>:<entrypoint>`. `ktisma tex
resolve` accepts only identifiers declared by the record. Then, the command verifies that the named
dependency owns the resolved file.

Only the workspace-root `ktisma.toml` may declare this table. Directory overlays and command-line
configuration layers cannot replace or extend the closure. Run `ktisma tex install` after changing
the record. Normal builds verify the selected snapshot without network access and pass its absolute
path to TeX as `TEXMFHOME`. The `.ktisma/` state directory is machine-local and should be ignored
by version control.

A new snapshot does not invalidate an existing build. latexmk records the absolute path of each TeX
input. The previous snapshot remains on disk, so these paths still resolve. Therefore, `ktisma
build` still reports the old output as current. After `ktisma tex install` selects a new snapshot,
run `ktisma clean` on each source before building it again.

## Configuration Precedence

Highest priority first:

1. **CLI flags** (`--engine`, `--output`, `--output-dir`, `--cleanup`)
2. **Per-file magic comments** (`% !TeX program = ...`, `% !ktisma output = ...`)
3. **Overlays `ktisma.toml`** in the folders between the source directory and the workspace root
4. **Workspace-root `ktisma.toml`**, in `config/tools/` or at the root
5. **Built-in defaults**

### Concern-Specific Precedence

| Concern | Precedence (highest first) |
| --- | --- |
| Engine | `--engine` > variant `engine` > `% !TeX program` / marker detection > `[engines].default` |
| Routing | `--output` > `--output-dir` > variant `output` > `% !ktisma output` > custom route resolvers > `[routes]` > `[routing]` suffix convention > fallback beside source |
| Cleanup | CLI > nearest config > workspace config > built-in default |
| Variants | CLI explicit variant > config-defined variant map |
| TeX dependencies | Workspace-root declaration only; overlays are rejected |

## Merge Semantics

When multiple config layers are present, they merge with these rules:

- **Nested tables** (e.g., `[build]`, `[engines]`) merge by key. A key in a higher-precedence
  layer overrides the same key from a lower layer, but other keys in the table are preserved.
- **Scalars** replace lower-precedence values entirely.
- **Arrays** replace lower-precedence values entirely (no concatenation).
- **`[routes]`** merges by exact pattern key. If the same glob pattern appears in multiple
  layers, the higher-precedence layer wins for that pattern.
- **`[variants]`** merges by exact variant name, same as routes.
- **`schema_version`** in the workspace-root config governs the resolved workspace. A nested
  config declares the syntax of its own layer but cannot downgrade capabilities enabled at
  the root.

### Example

Workspace-root `ktisma.toml`:

```toml
[engines]
default = "pdflatex"
modern_default = "lualatex"

[routes]
"lectures-tex/**" = "lectures-pdfs/"
"drafts/*.tex" = "output/"
```

Subdirectory `ktisma.toml`:

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

The anchor of a relative path is fixed by the place where the path is written:

| Source | Anchor |
| --- | --- |
| Command-line paths (the source, `--root`, `--output`, `--output-dir`) | Current working directory |
| Magic comments (`% !ktisma output = ...`) | Source file directory |
| Route targets in `[routes]`, in the root file or in an overlay | Workspace root |
| Route patterns in `[routes]` and `[routing].artifact_dirs` | Workspace root |
| Variant `output` values | Source file directory |

A path written in a configuration file is read from the workspace root, whichever file declares
it. The root file can therefore move between the root and `config/tools/` without an edit. An
overlay follows the same rule for two reasons. First, the patterns of `[routes]` already match the source
path relative to the root, so a target relative to the root reads in the same frame as its pattern.
Second, one reading for every configuration file spares the reader a check of the folder that
holds the file.

The variant `output` is the one exception. It is a template applied to every source that the layer
covers, and no placeholder names the folder of the source. A relative `output` therefore resolves
against the source file directory, so that one declaration places each output beside its own
source, as `../pdfs/` does.

Processing steps:

1. `~` is expanded to the user's home directory.
2. Relative paths are resolved against their anchor.
3. All paths are normalized to absolute `Path` objects at the application boundary.

## Workspace Root Resolution

The workspace root determines where ktisma searches for its configuration files and anchors
workspace-relative paths. Resolution stops at the first answer:

1. `--root` (`-r`) command-line option, relative to the current folder
2. `KTISMA_ROOT` environment variable
3. Outermost ancestor folder that holds `ktisma.toml` or `config/tools/ktisma.toml`
4. Current working directory

Step 3 takes the *outermost* ancestor, not the nearest one. Ktisma stacks one `ktisma.toml` per
folder: the file at the workspace root holds the configuration of the whole workspace, and each
file below it overlays the configuration of its own folder (see
[Configuration Precedence](#configuration-precedence)). Therefore, a nested `ktisma.toml` never
starts a workspace of its own when the root is resolved from the source path. The workspace root
is never inferred from `.git` or other unrelated files.

The search of step 3 starts at the folder of the source when the command names one (`build`,
`inspect`, `clean`, `variants`, and the source folder of `batch`), and at the current folder
otherwise (`doctor`, `init`, `tex`). A build of a source given by its full path thus finds the
workspace of that source from any current folder, as pytest determines its root from the paths
given on its command line.

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
- Version 2 adds `[[tex.dependencies]]`.
- Keys introduced in a later schema version are errors under an earlier version.
- Explicit versioning allows config files to opt into new features without breaking older ktisma installations.

## Validation

Validation happens when config is loaded, not when values are accessed:

- Unknown keys for the declared schema version are errors.
- Type mismatches are errors.
- Invalid enum values (e.g., `cleanup = "maybe"`) are errors.
- Route targets that normalize outside the intended filesystem root are allowed when explicit;
  ktisma does not silently rewrite them.
