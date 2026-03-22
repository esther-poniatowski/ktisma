# Project Layout

This guide explains how to structure your LaTeX project so ktisma can route compiled PDFs to the
right locations automatically.

## Directory Conventions

ktisma uses a naming convention to determine where compiled PDFs should go:

- **Source directories** end with `-tex` (e.g., `lectures-tex/`, `exercises-tex/`)
- **Output directories** end with `-pdfs` (e.g., `lectures-pdfs/`, `exercises-pdfs/`)
- **Build artifacts** go in `.ktisma_build/` inside the source directory

A typical project looks like this:

```text
my-project/
  .ktisma.toml
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

ktisma creates the `-pdfs` directories automatically when it routes the first output.

## The Suffix Convention

When you build `lectures-tex/week1.tex`, ktisma:

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

See [Routing: Suffix Convention](../routing.md#suffix-convention) for the full resolution rules.

## Entrypoint Collapse

A common pattern is to organize each document as a subdirectory with a `main.tex` entry point:

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

Without any special configuration, both documents produce a file named `main.pdf` — not useful
when sharing with colleagues. Entrypoint collapse solves this by naming the output after the parent
directory instead:

```toml
[routing]
collapse_entrypoint_names = true
```

With this setting:

| Source | Output |
| ------ | ------ |
| `presentations-tex/research-overview/main.tex` | `presentations-pdfs/research-overview.pdf` |
| `presentations-tex/project-update/main.tex` | `presentations-pdfs/project-update.pdf` |

The collapse applies when the source filename matches one of the configured entrypoint names
(`main` and `index` by default). You can customize this list:

```toml
[routing]
collapse_entrypoint_names = true
entrypoint_names = ["main", "index", "document"]
```

See [Routing: Entrypoint Collapse](../routing.md#entrypoint-collapse) for details.

## Projects Without the Suffix Convention

The suffix convention is not required. If your source files do not live in `*-tex/` directories,
ktisma still works — it just uses different routing methods.

### Explicit Route Rules

You can define explicit mappings in `.ktisma.toml`:

```toml
[routes]
"drafts/*.tex" = "output/"
"thesis/main.tex" = "thesis/thesis.pdf"
```

Glob patterns match against the path relative to the workspace root. See
[Routing: Explicit Route Rules](../routing.md#explicit-route-rules) for specificity scoring and
pattern syntax.

### Fallback Routing

If no route rule or suffix convention matches, ktisma places the PDF beside the source file. This
is safe — a successful PDF is never lost.

## Where ktisma Looks for Configuration

ktisma loads `.ktisma.toml` files from the workspace root toward the source directory, with nearer
files taking higher precedence:

```text
my-project/
  .ktisma.toml              (workspace-level config — lowest precedence)
  lectures-tex/
    .ktisma.toml            (overlay — higher precedence for files in this subtree)
    advanced/
      .ktisma.toml          (overlay — highest precedence for files in this subtree)
      topic.tex
```

This lets you set project-wide defaults at the root and override specific settings for
subdirectories (e.g., a different engine for one subtree).

See [Configuration: Precedence](../configuration.md#configuration-precedence) and
[Merge Semantics](../configuration.md#merge-semantics) for how layers combine.

## The vendor/ Directory

ktisma itself lives in `vendor/ktisma/` as a git submodule (or symlink). This directory should
**not** be in `.gitignore` — it is part of your repository.

To update ktisma to the latest version:

```bash
cd vendor/ktisma && git pull origin main && cd ../..
git add vendor/ktisma
git commit -m "Update ktisma submodule"
```
