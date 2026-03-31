# Installation

## Prerequisites

- **Python 3.9+** (3.12+ recommended). Ktisma has no external dependencies
  beyond the standard library.
- **A TeX distribution** (TeX Live, MacTeX, MiKTeX) with the engine in use
  (`pdflatex`, `lualatex`, or `xelatex`).
- **latexmk** on the `PATH`. Most TeX distributions include it.

Verify all prerequisites at once with
[`ktisma doctor`](../cli-reference.md#doctor) after installation.

## As a Git Submodule (Recommended)

```sh
git submodule add https://github.com/esther-poniatowski/ktisma.git vendor/ktisma
```

The submodule command creates a `vendor/ktisma/` directory tracked by the
repository. Collaborators obtain it automatically with
`git submodule update --init`.

## As a Symlink

For a single local checkout shared across projects:

```sh
ln -s /path/to/ktisma vendor/ktisma
```

## Initial Configuration

Create a `.ktisma.toml` file at the project root:

```toml
schema_version = 1
```

A single line constitutes a complete, valid configuration. The built-in defaults
provide:

- **Engine**: `pdflatex` (auto-detected from source when possible)
- **Routing**: `*-tex/` directories map to sibling `*-pdfs/` directories
- **Build directory**: `.ktisma_build/` inside the source directory
- **Cleanup**: build artifacts removed after successful PDF output
- **SyncTeX**: enabled (for PDF-to-source navigation in editors)

See the [Configuration Reference](../configuration.md) for the full schema.

## Updating `.gitignore`

Add these patterns to the project `.gitignore`:

```gitignore
# ktisma build artifacts
.ktisma_build/

# Compiled PDFs in output directories (regeneratable)
**/*-pdfs/
```

The first pattern excludes intermediate build files. The second excludes the
output directories that ktisma creates — regeneratable from source and typically
not tracked.

## Verifying the Setup

Run the prerequisite checker to confirm the installation:

```sh
python3 vendor/ktisma/bin/ktisma doctor
```

Expected output:

```text
  [ok] latexmk: latexmk 4.x
  [ok] pdflatex: pdfTeX 3.x
```

## Next Steps

- [Project Layout](project-layout.md) — `-tex`/`-pdfs` directory conventions
  and entrypoint collapse.
- [Migration](migration.md) — Replacing an existing `.latexmkrc` and helper
  scripts.
- [Recipes](recipes.md) — Concrete `.ktisma.toml` examples for common scenarios.
- [Configuration Reference](../configuration.md) — Full schema documentation.
