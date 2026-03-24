# Getting Started

Adding ktisma to an existing LaTeX project and building a first document.

## Prerequisites

- **Python 3.11+** (3.12+ recommended). ktisma has no external dependencies beyond the standard
  library.
- **A TeX distribution** (TeX Live, MacTeX, MiKTeX) with the engine in use (`pdflatex`,
  `lualatex`, or `xelatex`).
- **latexmk** on the `PATH`. Most TeX distributions include it.

Verify all prerequisites at once with [`ktisma doctor`](../cli-reference.md#doctor) after
installation.

## Adding ktisma to the Project

### As a Git Submodule (Recommended)

```bash
git submodule add https://github.com/esther-poniatowski/ktisma.git vendor/ktisma
```

The submodule command creates a `vendor/ktisma/` directory tracked by the repository. Collaborators
get it automatically with `git submodule update --init`.

### As a Symlink

For a single local checkout of ktisma shared across projects:

```bash
ln -s /path/to/ktisma vendor/ktisma
```

## Creating the Configuration

Create a `.ktisma.toml` file at the root of the project:

```toml
schema_version = 1
```

That single line is a complete, valid configuration. The built-in defaults provide:

- **Engine**: `pdflatex` (auto-detected from source when possible)
- **Routing**: `*-tex/` directories map to sibling `*-pdfs/` directories
- **Build directory**: `.ktisma_build/` inside the source directory
- **Cleanup**: build artifacts removed after successful PDF output
- **SyncTeX**: enabled (for PDF-to-source navigation in editors)

See the [configuration reference](../configuration.md) for the full schema.

## Building a Document

Build a `.tex` file from the project root:

```bash
python3 vendor/ktisma/bin/ktisma build slides-tex/week1.tex
```

On success, ktisma prints the path to the produced PDF:

```text
slides-pdfs/week1.pdf
```

When the source lives under a workspace with `.ktisma.toml` files, ktisma can infer the
workspace root automatically. Pass `--workspace-root` when pinning the workspace root explicitly.

## Inspecting Decisions Before Building

Preview what ktisma would do without compiling:

```bash
# Which engine would be selected?
python3 vendor/ktisma/bin/ktisma inspect engine slides-tex/week1.tex

# Where would the PDF be placed?
python3 vendor/ktisma/bin/ktisma inspect route slides-tex/week1.tex
```

The inspect commands help verify the configuration before committing to a build. See the
[CLI reference](../cli-reference.md) for all available commands and options.

## Editor Setup

### VS Code with LaTeX Workshop

Add the following to the workspace `.vscode/settings.json` or `.code-workspace` file:

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
%WORKSPACE_FOLDER%` only when pinning the workspace root explicitly in the editor recipe.

See [Editor Integration](../editor-integration.md) for other editors (Vim, Emacs) and advanced
configuration.

## Updating .gitignore

Add these patterns to the project `.gitignore`:

```gitignore
# ktisma build artifacts
.ktisma_build/

# Compiled PDFs in output directories (regeneratable)
**/*-pdfs/
```

The first pattern excludes intermediate build files. The second pattern excludes the output
directories that ktisma creates -- regeneratable from source and typically not tracked.

## Verifying the Setup

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

- [Project Layout](project-layout.md) -- understand the `-tex`/`-pdfs` directory conventions and
  entrypoint collapse
- [Migrating from latexmk](migration.md) -- replacing an existing `.latexmkrc` and helper scripts
- [Configuration Recipes](recipes.md) -- concrete `.ktisma.toml` examples for common scenarios
- [Configuration Reference](../configuration.md) -- full schema documentation
