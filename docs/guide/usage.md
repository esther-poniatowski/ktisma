# Usage

Ktisma builds LaTeX documents through a single CLI that handles engine
detection, output routing, build directories, and cleanup. All commands accept
`--workspace-root` to pin the workspace explicitly; without it, ktisma infers
the workspace root from the nearest `.ktisma.toml`.

For the full command reference, refer to [CLI Reference](../cli-reference.md).
For configuration options, refer to [Configuration](../configuration.md).

## Building a Document

Compile a LaTeX source file:

```sh
python3 vendor/ktisma/bin/ktisma build slides-tex/week1.tex
```

On success, ktisma prints the path to the produced PDF:

```text
slides-pdfs/week1.pdf
```

## Inspecting Decisions Before Building

Preview what ktisma would do without compiling:

```sh
# Which engine would be selected?
python3 vendor/ktisma/bin/ktisma inspect engine slides-tex/week1.tex

# Where would the PDF be placed?
python3 vendor/ktisma/bin/ktisma inspect route slides-tex/week1.tex
```

The inspect commands help verify the configuration before committing to a
build. Both support `--json` for machine-readable output.

## Cleaning Build Artifacts

Remove intermediate build files for a source file or an entire directory:

```sh
python3 vendor/ktisma/bin/ktisma clean slides-tex/week1.tex
python3 vendor/ktisma/bin/ktisma clean slides-tex/
```

## Building Multiple Documents

The `batch` command builds all entrypoint `.tex` files in a directory tree:

```sh
python3 vendor/ktisma/bin/ktisma batch lectures-tex/
```

Entrypoint files are identified by name (`main.tex`, `index.tex` by default)
and can be configured via the `routing.entrypoint_names` option.

## Building Variants

Compile configured variants (e.g., review markup) alongside the default output:

```sh
python3 vendor/ktisma/bin/ktisma variants slides-tex/week1.tex
```

Variants inject LaTeX preamble content through the `[variants]` table in
`.ktisma.toml`. See [Build Lifecycle](../build-lifecycle.md) for the full
reference.

## Verifying Prerequisites

Confirm that all required tools (latexmk, engines) are installed:

```sh
python3 vendor/ktisma/bin/ktisma doctor
```

Expected output:

```text
  [ok] latexmk: latexmk 4.x
  [ok] pdflatex: pdfTeX 3.x
```

## Setting Up VS Code Integration

The preferred integration path calls the ktisma CLI directly from LaTeX
Workshop:

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
policies. See [Editor Integration](../editor-integration.md) for other editors
and advanced configuration.

## Next Steps

- [Project Layout](project-layout.md) — `-tex`/`-pdfs` directory conventions.
- [Migration](migration.md) — Replacing an existing latexmk setup.
- [Recipes](recipes.md) — Concrete `.ktisma.toml` examples.
- [Configuration Reference](../configuration.md) — Full schema documentation.
