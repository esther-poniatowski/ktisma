# Project Layout

Structuring a LaTeX project so ktisma can route compiled PDFs to the right locations automatically.

## Directory Conventions

ktisma uses a naming convention to determine where compiled PDFs should go:

- **Source directories** end with `-tex` (e.g., `lectures-tex/`, `exercises-tex/`)
- **Output directories** end with `-pdfs` (e.g., `lectures-pdfs/`, `exercises-pdfs/`)
- **Build artifacts** go in `.ktisma_build/` inside the source directory

A typical project looks like the following:

```text
my-project/
  ktisma.toml
  vendor/ktisma/
  lectures-tex/
    week1.tex
    week2.tex
  lectures-pdfs/          (created by ktisma)
    week1.pdf
    week2.pdf
  exercises-tex/
    algebra.tex
  exercises-pdfs/         (created by ktisma)
    algebra.pdf
```

ktisma creates the `-pdfs` directories automatically when routing the first output.

## The Suffix Convention

When building `lectures-tex/week1.tex`, ktisma:

1. Sees that the file sits inside a directory ending in `-tex`
2. Replaces the `-tex` suffix with `-pdfs` to find the output directory
3. Places the PDF there with the same basename: `lectures-pdfs/week1.pdf`

Relative paths inside the source directory are preserved. For example,
`lectures-tex/advanced/topic.tex` routes to `lectures-pdfs/advanced/topic.pdf`.

The suffixes are configurable:

```toml
[routing]
source_suffix = "-src"
output_suffix = "-out"
```

See [Routing: Suffix Convention](routing.md#suffix-convention) for the full resolution rules.

## Entrypoint Collapse

A common pattern organizes each document as a subdirectory with a `main.tex` entry point:

```text
presentations-tex/
  research-overview/
    main.tex
    slides/
    figures/
  project-update/
    main.tex
    slides/
```

Without any special configuration, both documents produce a file named `main.pdf` -- not useful
when sharing with colleagues. Entrypoint collapse solves the naming conflict by deriving the output
name from the parent directory instead:

```toml
[routing]
collapse_entrypoint_names = true
```

With the collapse setting enabled:

| Source | Output |
| ------ | ------ |
| `presentations-tex/research-overview/main.tex` | `presentations-pdfs/research-overview.pdf` |
| `presentations-tex/project-update/main.tex` | `presentations-pdfs/project-update.pdf` |

The collapse applies when the source filename matches one of the configured entrypoint names
(`main` and `index` by default). The entrypoint list is customizable:

```toml
[routing]
collapse_entrypoint_names = true
entrypoint_names = ["main", "index", "document"]
```

See [Routing: Entrypoint Collapse](routing.md#entrypoint-collapse) for details.

## Projects Without the Suffix Convention

The suffix convention is not required. If source files do not live in `*-tex/` directories,
ktisma still works -- it just uses different routing methods.

### Explicit Route Rules

Define explicit mappings in `ktisma.toml`:

```toml
[routes]
"drafts/*.tex" = "output/"
"thesis/main.tex" = "thesis/thesis.pdf"
```

Glob patterns match against the path relative to the workspace root, and relative targets resolve
from the workspace root too, in an overlay as in the root file. See
[Routing: Explicit Route Rules](routing.md#explicit-route-rules) for specificity scoring and
pattern syntax.

### Fallback Routing

If no route rule or suffix convention matches, ktisma places the PDF beside the source file. The
fallback ensures a successful PDF is never lost.

## Where ktisma Looks for Configuration

ktisma loads the `ktisma.toml` files from the workspace root toward the source directory, with
nearer files taking higher precedence:

```text
my-project/
  ktisma.toml               (workspace-root file -- lowest precedence)
  lectures-tex/
    ktisma.toml             (overlay -- higher precedence for files in this subtree)
    advanced/
      ktisma.toml           (overlay -- highest precedence for files in this subtree)
      topic.tex
```

The layered approach allows setting project-wide defaults at the root and overriding specific
configuration values for subdirectories (e.g., a different engine for one subtree).

### The Workspace-Root File in `config/tools/`

A repository that groups the configuration files of its tools in `config/tools/` may hold the
workspace-root file there, as `config/tools/ktisma.toml`:

```text
my-project/
  config/tools/
    ktisma.toml             (workspace-root file -- lowest precedence)
  lectures-tex/
    ktisma.toml             (overlay -- higher precedence for files in this subtree)
    week1.tex
```

The folder `my-project/` is then the workspace root, because it holds `config/tools/ktisma.toml`.
The paths written in the file stay relative to `my-project/`, so the file moves between the two
places without an edit. Only the workspace-root file has this second place. An overlay stays
`ktisma.toml` in the folder that it configures, because that folder defines the scope of the
overlay. A root that holds both `ktisma.toml` and `config/tools/ktisma.toml` is an error that
names both files (see
[Configuration Files and Their Places](configuration.md#configuration-files-and-their-places)).

See [Configuration: Precedence](configuration.md#configuration-precedence) and
[Merge Semantics](configuration.md#merge-semantics) for how layers combine.

### Workspace Configuration Below the Repository Root

A repository whose LaTeX sources all sit in one folder, such as `artifacts/`, may hold its workspace
configuration in that folder, as `artifacts/ktisma.toml`. The root of the repository then keeps only
the files that its readers navigate. Ktisma takes the outermost ancestor holding a `ktisma.toml` as
its workspace root (see [Workspace Root Resolution](configuration.md#workspace-root-resolution)), so
`artifacts/` becomes the workspace root of every source below it. Four consequences follow:

- `artifacts/ktisma.toml` is the workspace-root file, so it may declare `[[tex.dependencies]]`.
- Workspace-relative paths are relative to `artifacts/`. A pattern of `[routing].artifact_dirs` that
  named `artifacts/*` from the repository root becomes `*`, and selects the same folders.
- The state directory `.ktisma/` of `ktisma tex install` is created in `artifacts/`. An ignore rule
  written without a leading slash, `.ktisma/`, covers it.
- A command or an editor adapter that passes the repository root as `--root`, or sets it in
  `KTISMA_ROOT`, must pass `artifacts/` instead. Otherwise, the file becomes an overlay, and Ktisma rejects its TeX
  dependencies with the diagnostic `tex-dependencies-not-root`.

A repository may sit inside a larger workspace with its own `ktisma.toml`, such as a vault that
includes the repository as a submodule. The file of that workspace is then the outermost, so it stays
the workspace root, and `artifacts/ktisma.toml` becomes an overlay whose TeX dependencies Ktisma
rejects. A build of such a source that needs those dependencies passes the `artifacts/` folder of the
repository as `--root`.

## The vendor/ Directory

ktisma itself lives in `vendor/ktisma/` as a git submodule (or symlink). The vendor directory
should **not** be in `.gitignore` -- it is part of the repository.

To update ktisma to the latest version:

```bash
cd vendor/ktisma && git pull origin main && cd ../..
git add vendor/ktisma
git commit -m "Update ktisma submodule"
```
