# Getting Started

This guide walks through adding ktisma to an existing LaTeX project and building your first
document.

## Prerequisites

- **Python 3.11+** (3.12+ recommended). ktisma has no external dependencies beyond the standard
  library.
- **A TeX distribution** (TeX Live, MacTeX, MiKTeX) with the engine you use (`pdflatex`,
  `lualatex`, or `xelatex`).
- **latexmk** on your `PATH`. Most TeX distributions include it.

You can verify all prerequisites at once with [`ktisma doctor`](../cli-reference.md#doctor) after
installation.

## Adding ktisma to Your Project

### As a Git Submodule (Recommended)

```bash
git submodule add https://github.com/esther-poniatowski/ktisma.git vendor/ktisma
```

This creates a `vendor/ktisma/` directory tracked by your repository. Collaborators get it
automatically with `git submodule update --init`.

### As a Symlink

If you have a single local checkout of ktisma and want to share it across projects:

```bash
ln -s /path/to/ktisma vendor/ktisma
```

## Creating Your Configuration

Create a `.ktisma.toml` file at the root of your project:

```toml
schema_version = 1
```

That is a complete, valid configuration. The built-in defaults give you:

- **Engine**: `pdflatex` (auto-detected from source when possible)
- **Routing**: `*-tex/` directories map to sibling `*-pdfs/` directories
- **Build directory**: `.ktisma_build/` inside the source directory
- **Cleanup**: build artifacts removed after successful PDF output
- **SyncTeX**: enabled (for PDF-to-source navigation in editors)

See the [configuration reference](../configuration.md) for the full schema.

## Building a Document

Build a `.tex` file from your project root:

```bash
python3 vendor/ktisma/bin/ktisma build slides-tex/week1.tex
```

On success, ktisma prints the path to the produced PDF:

```text
slides-pdfs/week1.pdf
```

When your source lives under a workspace with `.ktisma.toml` files, ktisma can infer the
workspace root automatically. Use `--workspace-root` when you want to pin it explicitly.

## Inspecting Decisions Before Building

You can preview what ktisma would do without compiling:

```bash
# Which engine would be selected?
python3 vendor/ktisma/bin/ktisma inspect engine slides-tex/week1.tex

# Where would the PDF be placed?
python3 vendor/ktisma/bin/ktisma inspect route slides-tex/week1.tex
```

These commands are useful for verifying your configuration before committing to a build. See the
[CLI reference](../cli-reference.md) for all available commands and options.

## Setting Up Your Editor

### VS Code with LaTeX Workshop

Add the following to your `.vscode/settings.json` or `.code-workspace` file:

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

Set `autoClean` to `"never"` because ktisma manages cleanup through its own
[policies](../build-lifecycle.md#cleanup-policies). Add `--workspace-root
%WORKSPACE_FOLDER%` only if you want the editor recipe to pin the workspace root explicitly.

See [Editor Integration](../editor-integration.md) for other editors (Vim, Emacs) and advanced
configuration.

## Updating .gitignore

Add these patterns to your `.gitignore`:

```gitignore
# ktisma build artifacts
.ktisma_build/

# Compiled PDFs in output directories (regeneratable)
**/*-pdfs/
```

The first pattern excludes intermediate build files. The second excludes the output directories
that ktisma creates — these are regeneratable from source and typically should not be tracked.

## Verifying Your Setup

Run the prerequisite checker to confirm everything is in place:

```bash
python3 vendor/ktisma/bin/ktisma doctor
```

Expected output:

```text
  [ok] latexmk: latexmk 4.x
  [ok] pdflatex: pdfTeX 3.x
```

## Next Steps

- [Project Layout](project-layout.md) — understand the `-tex`/`-pdfs` directory conventions and
  entrypoint collapse
- [Migrating from latexmk](migration.md) — if you are replacing an existing `.latexmkrc` and
  helper scripts
- [Configuration Recipes](recipes.md) — concrete `.ktisma.toml` examples for common scenarios
- [Configuration Reference](../configuration.md) — full schema documentation
