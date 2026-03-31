# Ktisma

[![Maintenance](https://img.shields.io/maintenance/yes/2026)]()
[![Last Commit](https://img.shields.io/github/last-commit/esther-poniatowski/ktisma)](https://github.com/esther-poniatowski/ktisma/commits/main)
[![Python](https://img.shields.io/badge/python-%E2%89%A53.9-blue)](https://www.python.org/)
[![License: GPL](https://img.shields.io/badge/License-GPL-yellow.svg)](https://opensource.org/licenses/GPL-3.0)

Builds LaTeX documents consistently and portably across shared workspaces.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

## Overview

Ktisma replaces duplicated `.latexmkrc` files, helper scripts, and
editor-specific shell glue with a single CLI and a layered build system.

### Motivation

LaTeX projects in shared workspaces (teaching, research groups) accumulate
per-editor build recipes, inconsistent output paths, and ad-hoc cleanup scripts.
Build failures are difficult to reproduce across machines because each
contributor relies on different configuration fragments.

### Advantages

- **One front door** — build, inspect, clean, and verify prerequisites through a
  single CLI instead of scattered scripts.
- **Automatic engine detection** — ktisma infers `pdflatex`, `lualatex`, or
  `xelatex` from source file preambles and magic comments.
- **Deterministic configuration** — typed TOML configuration with explicit
  precedence and merge rules replaces `.git`-driven guesswork.
- **Safe output handling** — a successful PDF is never lost because routing did
  not match; per-job build directories and lockfiles avoid collisions.
- **Thin editor adapters** — VS Code, Vim, and Emacs call the canonical CLI
  instead of bypassing it.

---

## Features

- [x] **Build**: Compile LaTeX documents with automatic engine detection and
  routing.
- [x] **Inspect**: Preview engine selection and output routing without compiling.
- [x] **Clean**: Remove build artifacts for a source file or directory.
- [x] **Doctor**: Verify prerequisites (latexmk, engines) in one command.
- [x] **Batch**: Build all entrypoint `.tex` files in a directory tree.
- [x] **Variants**: Build configured variants (e.g., review markup) alongside
  the default output.
- [x] **Layered configuration**: Workspace, project, and per-file `.ktisma.toml`
  overlays with deterministic merge semantics.
- [x] **Editor integration**: VS Code / LaTeX Workshop recipes, latexmkrc
  migration.

---

## Quick Start

Add ktisma to a project as a git submodule:

```sh
git submodule add https://github.com/esther-poniatowski/ktisma.git vendor/ktisma
```

Build a document:

```sh
python3 vendor/ktisma/bin/ktisma build slides-tex/week1.tex
```

---

## Documentation

| Guide | Content |
| ----- | ------- |
| [Installation](docs/guide/installation.md) | Prerequisites, submodule/symlink setup |
| [Project Layout](docs/guide/project-layout.md) | `-tex`/`-pdfs` directory conventions, entrypoint collapse |
| [Migration](docs/guide/migration.md) | Replacing an existing latexmk setup |
| [Recipes](docs/guide/recipes.md) | Concrete `.ktisma.toml` examples |
| [CLI Reference](docs/cli-reference.md) | Commands, flags, output modes, exit codes |
| [Configuration](docs/configuration.md) | `.ktisma.toml` schema, precedence, merge rules |
| [Architecture](docs/architecture.md) | Layers, protocols, data flow |
| [Build Lifecycle](docs/build-lifecycle.md) | Pipeline, watch mode, cleanup, locks, variants |
| [Engine Detection](docs/engine-detection.md) | Detection steps, markers, ambiguity handling |
| [Routing](docs/routing.md) | Resolution chain, suffix conventions, route rules |
| [Editor Integration](docs/editor-integration.md) | VS Code, LaTeX Workshop, latexmkrc migration |
| [Design Principles](docs/design-principles.md) | Coding standards and implementation patterns |

---

## Contributing

Open a pull request or issue against the plan documents first when changing the
public contract. For implementation work, follow
[docs/design-principles.md](docs/design-principles.md).

---

## License

This project is licensed under the terms of the
[GNU General Public License v3.0](LICENSE).
