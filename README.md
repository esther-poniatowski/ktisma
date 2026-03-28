# Ktisma

[![Maintenance](https://img.shields.io/maintenance/yes/2026)]()
[![Last Commit](https://img.shields.io/github/last-commit/esther-poniatowski/ktisma)](https://github.com/esther-poniatowski/ktisma/commits/main)
[![License: GPL](https://img.shields.io/badge/License-GPL-yellow.svg)](https://opensource.org/licenses/GPL-3.0)

Builds LaTeX documents consistently and portably across shared workspaces.

## Overview

Ktisma replaces duplicated `.latexmkrc` files, helper scripts, and shell glue specific to each editor with
one stable CLI and a layered build system:

- One front door for build, inspect, clean, and prerequisite checks.
- Automatic engine detection from source file preambles and magic comments.
- Explicit workspace and configuration resolution instead of `.git`-driven guesswork.
- Safe output handling: a successful PDF is never lost because routing did not match.
- Per-job build directories and lockfiles to avoid collisions across watch mode, variants, and
  concurrent builds.
- Typed TOML configuration with deterministic precedence and merge rules.
- Thin editor adapters that wrap the canonical CLI instead of bypassing it.

## Commands

```text
ktisma build <source.tex>          Compile a LaTeX document
ktisma inspect engine <source.tex> Show which engine would be selected
ktisma inspect route <source.tex>  Show where the PDF would be routed
ktisma clean <source.tex|dir>      Remove build artifacts
ktisma doctor                      Verify prerequisites
ktisma batch <source-dir>          Build batch-entrypoint .tex files in a directory tree
ktisma variants <source.tex>       Build configured variants, optionally with the default output
```

All commands accept `--workspace-root` to set the workspace explicitly. `build` and `inspect`
support `--json` for machine-readable output.

## Installation

### As a Git Submodule

```bash
git submodule add https://github.com/esther-poniatowski/ktisma.git vendor/ktisma
```

### As a Symlink

```bash
ln -s /path/to/ktisma vendor/ktisma
```

## Usage

Build a document from a vendored checkout:

```bash
python3 vendor/ktisma/bin/ktisma build project-tex/main.tex
```

Installed or development use:

```bash
python3 -m ktisma build project-tex/main.tex
```

Inspect engine selection without compiling:

```bash
python3 vendor/ktisma/bin/ktisma inspect engine project-tex/main.tex
```

Inspect routing without compiling:

```bash
python3 vendor/ktisma/bin/ktisma inspect route project-tex/main.tex
```

Verify prerequisites:

```bash
python3 vendor/ktisma/bin/ktisma doctor
```

## Configuration

Ktisma uses a single typed configuration format: `.ktisma.toml`.

Precedence, highest first:

1. CLI flags
2. Per-file magic comments
3. Project-local `.ktisma.toml` overlays between the source directory and the workspace root
4. Workspace `.ktisma.toml`
5. Built-in defaults

Deterministic merge semantics:

- Tables merge by key.
- Scalars and arrays replace the lower-precedence value.
- Route rules merge by pattern key; if the same pattern is declared more than once, the nearer
  layer wins.
- Relative paths from config resolve against the directory of the config file that declared them.
- Relative paths from magic comments resolve against the source file directory.
- Relative paths from CLI flags resolve against the current working directory.
- When ktisma infers the workspace root from `.ktisma.toml`, it uses the outermost matching
  ancestor so workspace config and subdirectory overlays can both participate.

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
default_filename_suffix = ""
variant_filename_suffix = "_{variant}"

[routes]
"lectures-tex/**" = "lectures-pdfs/"
"drafts/*.tex" = "output/"

[variants.review]
payload = "\\def\\ShowReviewMarkup{}"
filename_suffix = "_review"
```

## Architecture

Ktisma uses a four-layer architecture with strict dependency boundaries:

| Layer | Responsibility |
| --- | --- |
| Domain | Pure decisions, data models, merge rules, engine detection, routing, build planning |
| Application | Use-case orchestration: build, inspect, clean, doctor, batch, variants |
| Infrastructure | Filesystem, TOML loading, lockfiles, subprocess execution, prerequisite probing |
| Adapters | CLI parsing, editor integration, diagnostic formatting, composition root |

Dependency direction is one-way: adapters -> application -> domain. Application depends on
infrastructure through protocol interfaces, not concrete imports. Infrastructure implements
protocols defined in the application layer. The composition root in `adapters/bootstrap.py` wires
concrete implementations at startup.

See [docs/architecture.md](docs/architecture.md) for the full technical reference.

## VS Code Integration

The preferred integration path is to call the ktisma CLI directly from LaTeX Workshop:

```jsonc
"latex-workshop.latex.tools": [
  {
    "name": "ktisma",
    "command": "python3",
    "args": [
      "%WORKSPACE_FOLDER%/vendor/ktisma/bin/ktisma",
      "build",
      "%DOC_EXT%"
    ]
  }
],
"latex-workshop.latex.recipes": [
  {
    "name": "ktisma",
    "tools": ["ktisma"]
  }
],
"latex-workshop.latex.autoClean.run": "never"
```

The placeholder `%DOC_EXT%` expands to the resolved root file including its `.tex` extension.
Add `--workspace-root %WORKSPACE_FOLDER%` to pin the workspace explicitly instead of relying on
ktisma's config discovery. The recipe should call ktisma directly rather than wrapping `latexmk`
in `bash -c`.

## Directory Conventions

| Pattern | Purpose |
| --- | --- |
| `*-tex/` | Source directories containing `.tex` files |
| `*-pdfs/` | Default sibling output directories for compiled PDFs |
| `.ktisma_build/<job>/` | Per-job build directory for intermediate artifacts |

Default routing preserves relative paths and basenames:

- `slides-tex/week1.tex` -> `slides-pdfs/week1.pdf`
- `slides-tex/decks/main.tex` -> `slides-pdfs/decks/main.pdf`

Repositories that want `main.tex` to collapse to the parent directory name can opt in through
configuration.

## Support

Issues: [GitHub Issues](https://github.com/esther-poniatowski/ktisma/issues)

## Documentation

| Document | Scope |
| --- | --- |
| [Architecture](docs/architecture.md) | Layers, protocols, data flow, module inventory |
| [Configuration](docs/configuration.md) | `.ktisma.toml` reference, precedence, merge rules, path resolution |
| [CLI Reference](docs/cli-reference.md) | Commands, flags, output modes, exit codes |
| [Engine Detection](docs/engine-detection.md) | Detection steps, marker classes, ambiguity handling |
| [Routing](docs/routing.md) | Resolution chain, suffix conventions, route rules, fallback |
| [Build Lifecycle](docs/build-lifecycle.md) | Build pipeline, watch mode, cleanup, locks, variants |
| [Editor Integration](docs/editor-integration.md) | VS Code, LaTeX Workshop, latexmkrc migration |
| [Design Principles](docs/design-principles.md) | Coding standards and implementation patterns |

## Contributing

Open a pull request or issue against the plan documents first when changing the public contract.
For implementation work, follow [docs/design-principles.md](docs/design-principles.md).

## License

This project is licensed under the terms of the [GNU General Public License v3.0](LICENSE).
