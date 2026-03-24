# Configuration Recipes

Each recipe below is a self-contained `.ktisma.toml` snippet for a common use case. For the full
schema, see the [configuration reference](../configuration.md).

## Minimal Configuration (Zero-Config Defaults)

```toml
schema_version = 1
```

Defaults:

| Setting | Default |
| ------- | ------- |
| Engine | `pdflatex` (auto-detected from source when possible) |
| Routing | `*-tex/` maps to sibling `*-pdfs/` |
| Build directory | `.ktisma_build/` |
| Cleanup | Remove build artifacts after successful output |
| SyncTeX | Enabled |

## Nested Presentations with Entrypoint Collapse

**Use case**: each presentation is a subdirectory with a `main.tex` entry point, and the output PDF
should be named after the subdirectory rather than `main.pdf`.

```toml
schema_version = 1

[routing]
collapse_entrypoint_names = true
```

| Source | Output |
| ------ | ------ |
| `presentations-tex/intro-lecture/main.tex` | `presentations-pdfs/intro-lecture.pdf` |
| `presentations-tex/final-review/main.tex` | `presentations-pdfs/final-review.pdf` |

Files that are not named `main` or `index` are unaffected — they keep their original basename.

See [Routing: Entrypoint Collapse](../routing.md#entrypoint-collapse).

## Dual Compilation with Variants

**Use case**: compile a document twice from the same source, once normally and once with extra
annotations or review markup enabled.

```toml
schema_version = 1

[routing]
default_filename_suffix = ""
variant_filename_suffix = "_{variant}"

[variants.review]
payload = "\\def\\ShowReviewMarkup{}"
filename_suffix = "_review"
```

Build the default output and the configured variant:

```bash
# Default output
python3 vendor/ktisma/bin/ktisma build exercises-tex/algebra.tex
# -> exercises-pdfs/algebra.pdf

# Review variant
python3 vendor/ktisma/bin/ktisma build exercises-tex/algebra.tex --variant review
# -> exercises-pdfs/algebra_review.pdf

# Default output plus all configured variants
python3 vendor/ktisma/bin/ktisma variants exercises-tex/algebra.tex --include-default
```

Each variant builds in its own isolated directory (`.ktisma_build/review/`) to avoid
interference. See [Build Lifecycle: Variants](../build-lifecycle.md#variants).

## LuaLaTeX by Default

**Use case**: the workspace primarily uses `fontspec`, `unicode-math`, or other packages that
require a modern engine.

```toml
schema_version = 1

[engines]
default = "lualatex"
```

ktisma still auto-detects from source preambles — this setting only affects files where no
definitive engine marker is found. See [Engine Detection](../engine-detection.md).

## Explicit Route Rules

**Use case**: the project does not follow the `-tex`/`-pdfs` convention and output locations need
explicit control.

```toml
schema_version = 1

[routes]
"drafts/*.tex" = "output/drafts/"
"thesis/main.tex" = "thesis/thesis.pdf"
"papers/**/main.tex" = "compiled/"
```

Route patterns are matched against the source path relative to the workspace root. The most
specific matching rule wins. See [Routing: Explicit Route Rules](../routing.md#explicit-route-rules)
for specificity scoring.

A target ending with `/` is treated as a directory — the PDF keeps its original filename. A target
with a file extension is treated as the exact output path.

## Per-Subdirectory Engine Override

**Use case**: most documents use `pdflatex`, but one subdirectory requires `lualatex`.

Place a `.ktisma.toml` overlay in the subdirectory:

```text
my-project/
  .ktisma.toml           # [engines] default = "pdflatex"
  lectures-tex/
    week1.tex            # -> pdflatex
  special-tex/
    .ktisma.toml         # [engines] default = "lualatex"
    document.tex         # -> lualatex
```

Contents of `special-tex/.ktisma.toml`:

```toml
[engines]
default = "lualatex"
```

Overlay configs merge with the workspace-level config — only the overridden keys change. See
[Configuration: Precedence](../configuration.md#configuration-precedence) and
[Merge Semantics](../configuration.md#merge-semantics).

## Custom Source and Output Suffixes

**Use case**: the project uses `-src/` and `-out/` instead of `-tex/` and `-pdfs/`.

```toml
schema_version = 1

[routing]
source_suffix = "-src"
output_suffix = "-out"
```

See [Routing: Configuring the Convention](../routing.md#configuring-the-convention).

## Preserving Build Artifacts for Debugging

**Use case**: keep `.aux`, `.log`, and other intermediate files after a build for debugging
compilation issues.

```toml
schema_version = 1

[build]
cleanup = "never"
```

The build directory (`.ktisma_build/`) and its contents are preserved after every build. To clean
up manually:

```bash
python3 vendor/ktisma/bin/ktisma clean lectures-tex/week1.tex
```

See [Build Lifecycle: Cleanup Policies](../build-lifecycle.md#cleanup-policies) for all available
policies (`never`, `on_success`, `on_output_success`, `always`).
