# Ktisma

[![Maintenance](https://img.shields.io/maintenance/yes/2026)]()
[![Last Commit](https://img.shields.io/github/last-commit/esther-poniatowski/ktisma)](https://github.com/esther-poniatowski/ktisma/commits/main)
[![License: GPL](https://img.shields.io/badge/License-GPL-yellow.svg)](https://opensource.org/licenses/GPL-3.0)

---

Portable LaTeX build toolkit providing automatic engine detection, convention-based PDF
routing, artifact cleanup, and VS Code integration across multiple workspaces.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Support](#support)
- [Contributing](#contributing)
- [Acknowledgments](#acknowledgments)
- [License](#license)

## Overview

### Motivation

LaTeX projects across multiple workspaces share a common compilation workflow: invoke `latexmk`,
route the compiled PDF to a designated output directory, and clean up intermediate artifacts. Each
workspace currently reimplements this workflow independently through duplicated `.latexmkrc` files,
post-compilation shell scripts, and VS Code LaTeX Workshop configurations.

This duplication introduces several problems:

- **Divergent evolution**: Copies of the same helper script evolve independently. Fixes and
  improvements in one workspace do not propagate to others (e.g., nested directory support exists in
  some workspaces but not others).
- **Hardcoded paths**: Each `.latexmkrc` embeds an absolute path to its helper script, tying the
  build configuration to a specific machine layout.
- **Engine mismatch**: A single `pdflatex` configuration is assumed globally, but some projects
  require `lualatex` or `xelatex` (e.g., for `fontspec` or `polyglossia`). Compilation fails
  silently or requires manual overrides.
- **Redundant VS Code configuration**: LaTeX Workshop tool definitions, recipes, and cleanup
  settings are copied verbatim across workspace files.

### Advantages

Ktisma centralizes the LaTeX build pipeline into a single, portable toolkit that can be imported
into any workspace as a git submodule or symlink.

It provides the following benefits:

- **Automatic engine detection**: Scans the document preamble (including `\input` chains) for
  engine-specific packages (`fontspec`, `polyglossia`, `\RequireXeTeX`) and selects the appropriate
  compiler without manual configuration.
- **Convention-based PDF routing**: Moves compiled PDFs from the build directory to a sibling output
  directory following the `*-tex/` to `*-pdfs/` naming convention, supporting both flat and nested
  source layouts.
- **Zero-residue builds**: Intermediate artifacts are confined to a temporary `.latexmk_build/`
  directory and removed after successful compilation.
- **Portable configuration**: No hardcoded absolute paths. Workspaces reference the toolkit via a
  single environment variable, and per-workspace or per-project overrides layer cleanly on top of
  shared defaults.
- **Single source of truth**: Bug fixes, new build modes (batch, dual-version), and convention
  changes propagate to all consuming workspaces through a submodule update.

---

## Features

- [ ] Automatic TeX engine detection from document preamble analysis.
- [ ] Post-compilation PDF relocation following `*-tex/` to `*-pdfs/` convention.
- [ ] Automatic cleanup of `.latexmk_build/` intermediate artifacts.
- [ ] Support for flat and nested source directory layouts.
- [ ] Layered configuration: package defaults, workspace overrides, project overrides.
- [ ] Batch compilation of all `.tex` files in a directory.
- [ ] Dual-version compilation (e.g., blank and corrected variants).
- [ ] VS Code LaTeX Workshop tool and recipe definitions (importable snippets).
- [ ] Portable `.gitignore` fragment for LaTeX build artifacts.

---

## Installation

### As a Git Submodule

Add ktisma to any workspace (recommended location: `vendor/ktisma/`):

```bash
git submodule add https://github.com/esther-poniatowski/ktisma.git vendor/ktisma
```

### As a Symlink

For local-only use, symlink from a central installation:

```bash
ln -s /path/to/ktisma vendor/ktisma
```

### Workspace Integration

In the consuming workspace's `.latexmkrc`, source the shared configuration:

```perl
do "$ENV{KTISMA}/latexmkrc";
```

The `KTISMA` environment variable is set by the VS Code tool definition (see
[Configuration](#configuration)).

---

## Usage

### Automatic Compilation (VS Code)

With the LaTeX Workshop tool and recipe configured (see [Configuration](#configuration)),
compilation triggers on save. The toolkit automatically:

1. Detects the required TeX engine.
2. Compiles the document into `.latexmk_build/`.
3. Moves the PDF to the appropriate `*-pdfs/` directory.
4. Removes all intermediate artifacts.

### Command Line

Compile a single document:

```bash
cd project-tex/ && KTISMA=/path/to/ktisma latexmk -r "$KTISMA/latexmkrc" main.tex
```

Batch compile all documents in a directory:

```bash
ktisma/scripts/compile-batch.sh path/to/sources-tex/
```

Compile dual versions (blank + corrected):

```bash
ktisma/scripts/compile-dual.sh path/to/document.tex
```

---

## Configuration

### Layered Override System

Ktisma uses latexmk's native configuration layering:

| Layer | File | Scope |
|-------|------|-------|
| Package defaults | `ktisma/latexmkrc` | Engine detection, post-compile, cleanup |
| Workspace overrides | `<workspace>/.latexmkrc` | Custom hooks, additional rules |
| Project overrides | `<project>/.latexmkrc` | Force a specific engine, disable cleanup |

### VS Code Integration

Add the following to your `.code-workspace` or `.vscode/settings.json`:

```jsonc
"latex-workshop.latex.tools": [
    {
        "name": "latexmk_custom",
        "command": "bash",
        "args": [
            "-c",
            "cd '%DIR%' && mkdir -p .latexmk_build && KTISMA='%WORKSPACE_FOLDER%/vendor/ktisma' latexmk -outdir=.latexmk_build -interaction=nonstopmode -file-line-error -r '%WORKSPACE_FOLDER%/.latexmkrc' '%DOCFILE%'"
        ],
        "env": {}
    }
],
"latex-workshop.latex.recipes": [
    {
        "name": "latexmk (ktisma)",
        "tools": ["latexmk_custom"]
    }
],
"latex-workshop.latex.autoClean.run": "never"
```

### Directory Conventions

| Pattern | Purpose |
|---------|---------|
| `*-tex/` | Source directories containing `.tex` files |
| `*-pdfs/` | Output directories for compiled PDFs (auto-created) |
| `.latexmk_build/` | Temporary build directory (auto-removed) |

---

## Support

**Issues**: [GitHub Issues](https://github.com/esther-poniatowski/ktisma/issues)

---

## Contributing

Please refer to the [contribution guidelines](CONTRIBUTING.md).

---

## Acknowledgments

### Authors & Contributors

**Author**: @esther-poniatowski

For academic use, please cite using the GitHub "Cite this repository" feature to
generate a citation in various formats.

---

## License

This project is licensed under the terms of the [GNU General Public License v3.0](LICENSE).
