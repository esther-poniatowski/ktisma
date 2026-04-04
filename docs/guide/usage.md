# Usage

Ktisma builds LaTeX documents through a single CLI that handles engine
detection, output routing, build directories, and cleanup. All commands accept
`--workspace-root` to pin the workspace explicitly; without the flag, ktisma
infers the workspace root from the nearest `.ktisma.toml`.

Ktisma requires Python 3.12 or later.

Full command reference: [CLI Reference](../cli-reference.md).
Configuration options: [Configuration](../configuration.md).

## Building a Document

Compile a LaTeX source file:

```sh
ktisma build slides-tex/week1.tex
```

On success, ktisma prints the path to the produced PDF:

```text
slides-pdfs/week1.pdf
```

## Inspecting Decisions Before Building

Preview what ktisma would do without compiling:

```sh
# Which engine would be selected?
ktisma inspect engine slides-tex/week1.tex

# Where would the PDF be placed?
ktisma inspect route slides-tex/week1.tex
```

Both inspect subcommands accept `--json` for machine-readable output.

## Cleaning Build Artifacts

Remove intermediate build files for a source file or an entire directory:

```sh
ktisma clean slides-tex/week1.tex
ktisma clean slides-tex/
```

## Building Multiple Documents

The `batch` command builds all entrypoint `.tex` files in a directory tree:

```sh
ktisma batch lectures-tex/
```

Entrypoint files are identified by name (`main.tex`, `index.tex` by default).
The `routing.entrypoint_names` option controls which filenames qualify.

## Building Variants

Compile configured variants (e.g., review markup) alongside the default output:

```sh
ktisma variants slides-tex/week1.tex
```

Variant definitions live in the `[variants]` table of `.ktisma.toml` and inject
LaTeX preamble content via `latexmk -usepretex`. See
[Build Lifecycle](../build-lifecycle.md) for the full reference.

## Verifying Prerequisites

Confirm that all required tools (latexmk, engines) are installed:

```sh
ktisma doctor
```

Expected output:

```text
  [ok] latexmk: latexmk 4.x
  [ok] pdflatex: pdfTeX 3.x
```

## Initializing a Workspace

Generate a wrapper script (`scripts/ktisma`) and a VS Code LaTeX Workshop
configuration snippet:

```sh
ktisma init
```

The wrapper script sets `KTISMA_WORKSPACE_ROOT` automatically and delegates to
the vendored ktisma entry point. If `scripts/ktisma` already exists, the
command skips creation and prints the VS Code configuration only.

Pass `--workspace-root` to target a specific directory:

```sh
ktisma init --workspace-root /path/to/workspace
```

## Setting Up VS Code Integration

The `init` command prints a ready-to-use LaTeX Workshop configuration. For
manual setup, add the following to `.code-workspace` or
`.vscode/settings.json`:

```jsonc
"latex-workshop.latex.tools": [
  {
    "name": "ktisma",
    "command": "python3",
    "args": [
      "%WORKSPACE_FOLDER%/scripts/ktisma",
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

`autoClean` must be `"never"` because ktisma manages cleanup through its own
policies. See [Editor Integration](../editor-integration.md) for other editors
and advanced configuration.

## Next Steps

- [Project Layout](project-layout.md) — `-tex`/`-pdfs` directory conventions.
- [Migration](migration.md) — Replacing an existing latexmk setup.
- [Recipes](recipes.md) — Concrete `.ktisma.toml` examples.
- [Configuration Reference](../configuration.md) — Full schema documentation.
