# Ktisma

[![Maintenance](https://img.shields.io/maintenance/yes/2026)]()
[![Last Commit](https://img.shields.io/github/last-commit/esther-poniatowski/ktisma)](https://github.com/esther-poniatowski/ktisma/commits/main)
[![License: GPL](https://img.shields.io/badge/License-GPL-yellow.svg)](https://opensource.org/licenses/GPL-3.0)

Portable LaTeX build toolkit for predictable, shared document builds across multiple workspaces.

This repository is still plan-first. `ROADMAP.md` is the authoritative contract for architecture,
CLI surface, configuration semantics, and rollout sequencing. `docs/design-principles.md`
documents implementation rules and coding standards, but it must not redefine the public contract.

## Overview

Ktisma replaces duplicated `.latexmkrc` files, helper scripts, and editor-specific shell glue with
one stable CLI and a layered build system:

- One front door for build, inspect, clean, and prerequisite checks.
- Explicit workspace and configuration resolution instead of `.git`-driven guesswork.
- Safe output handling: a successful PDF must never be lost because routing did not match.
- Per-job build directories and lockfiles to avoid collisions across watch mode, variants, and
  concurrent builds.
- Typed TOML configuration with deterministic precedence and merge rules.
- Thin editor adapters that wrap the canonical CLI instead of bypassing it.

## Current Contract

Initial public commands:

- `build <source.tex>`
- `inspect engine <source.tex>`
- `inspect route <source.tex>`
- `clean <source.tex|build-dir>`
- `doctor`

Planned later commands:

- `batch <source-dir>`
- `variants <source.tex>`

Deferred adapter command:

- `init <workspace-root>` after workspace-editing behavior is proven stable

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
python3 vendor/ktisma/bin/ktisma build project-tex/main.tex --workspace-root .
```

Installed or development use:

```bash
python3 -m ktisma build project-tex/main.tex --workspace-root .
```

Inspect engine selection without compiling:

```bash
python3 vendor/ktisma/bin/ktisma inspect engine project-tex/main.tex --workspace-root .
```

Inspect routing without compiling:

```bash
python3 vendor/ktisma/bin/ktisma inspect route project-tex/main.tex --workspace-root .
```

Verify prerequisites:

```bash
python3 vendor/ktisma/bin/ktisma doctor --workspace-root .
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

[variants]
blank = ""
corrected = "\\ForceSolutions"
```

## Architecture Summary

Ktisma uses four layers:

| Layer | Responsibility |
| --- | --- |
| Domain | Pure decisions, data models, merge rules, engine detection, routing decisions, build planning |
| Application | Build, inspect, clean, doctor, batch, and variant use-cases |
| Infrastructure | TOML loading, source reading, lockfiles, filesystem mutation, subprocess execution, prerequisite probing |
| Adapters | CLI, editor integration, diagnostic formatting, composition root, optional compatibility shims |

Dependency direction is one-way: adapters -> application -> domain. Application depends on
infrastructure through protocol interfaces, not concrete imports. Infrastructure implements
protocols defined in the application layer. The composition root in the adapter layer wires
concrete implementations at startup.

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
      "%DOC%",
      "--workspace-root",
      "%WORKSPACE_FOLDER%"
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

The exact root-document placeholder may vary by LaTeX Workshop version. The important part is that
the recipe calls ktisma directly rather than wrapping `latexmk` in `bash -c`.

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

## Contributing

Open a pull request or issue against the plan documents first when changing the public contract.
For implementation work, follow `docs/design-principles.md`.

## License

This project is licensed under the terms of the [GNU General Public License v3.0](LICENSE).
