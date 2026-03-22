# Migrating from latexmk

This guide walks through replacing a manual `.latexmkrc` + helper script setup with ktisma.

## What ktisma Replaces

| Before | After | Notes |
| ------ | ----- | ----- |
| `.latexmkrc` | `.ktisma.toml` | Typed TOML config instead of Perl |
| Helper shell scripts (`latexmk-helper.sh`, `compile.sh`) | ktisma routing + materialization | PDF placement handled automatically |
| `$success_cmd` post-processing | Built-in cleanup and output routing | No shell glue needed |
| `.latexmk_build/` | `.ktisma_build/` | Per-job build directories with lockfiles |
| Manual `mkdir -p` + `latexmk` in editor config | Single `ktisma build` call | Editor recipe calls ktisma directly |
| `compile-batch-to-pdfs.sh` | `ktisma batch` | Builds all `.tex` files in a directory |
| `compile-dual-versions.sh` | `ktisma variants` / `ktisma build --variant` | Variant compilation via config |

## Step-by-Step Migration

### 1. Add ktisma to Your Project

```bash
git submodule add https://github.com/esther-poniatowski/ktisma.git vendor/ktisma
```

See [Getting Started: Adding ktisma](getting-started.md#adding-ktisma-to-your-project) for
alternative installation methods.

### 2. Create .ktisma.toml

Start with a minimal config at the project root:

```toml
schema_version = 1
```

Then map your old settings. Common translations:

**Engine selection** — if your `.latexmkrc` forced a specific engine:

```perl
# Old: .latexmkrc
$pdf_mode = 4;  # lualatex
```

```toml
# New: .ktisma.toml
[engines]
default = "lualatex"
```

ktisma also auto-detects engines from source preambles (e.g., `\RequireLuaTeX`, `fontspec`),
so you may not need this at all. See [Engine Detection](../engine-detection.md).

**SyncTeX** — if your `.latexmkrc` disabled it:

```perl
# Old: .latexmkrc
$pdflatex = 'pdflatex -interaction=nonstopmode -synctex=0 %O %S';
```

```toml
# New: .ktisma.toml
[build]
synctex = false
```

ktisma enables SyncTeX by default (useful for PDF-to-source navigation in editors).

**Custom output directories** — if your helper script moved PDFs to specific locations, the
default `-tex` to `-pdfs` suffix convention likely handles it. If not, use explicit route rules:

```toml
[routes]
"lectures/*.tex" = "output/lectures/"
```

See [Configuration Reference](../configuration.md) for the full schema.

### 3. Update Your Editor

Replace the old latexmk tool and recipe in your VS Code workspace or settings file:

```jsonc
// Old
"latex-workshop.latex.tools": [
  {
    "name": "latexmk_custom",
    "command": "bash",
    "args": ["-c", "cd '%DIR%' && mkdir -p .latexmk_build && latexmk ..."]
  }
]

// New
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

Add `--workspace-root %WORKSPACE_FOLDER%` only if you want the editor recipe to pin the
workspace root explicitly.

See [Editor Integration](../editor-integration.md) for other editors.

### 4. Update .gitignore

Replace the old build directory pattern with the new one:

```diff
- .latexmk_build/
+ .ktisma_build/
```

If you do not already have it, also add:

```gitignore
**/*-pdfs/
```

### 5. Remove Old Build Infrastructure

Delete the files that ktisma replaces:

- `.latexmkrc`
- Helper scripts (e.g., `latexmk-helper.sh`, `compile-batch-to-pdfs.sh`,
  `compile-dual-versions.sh`)
- Any leftover `.latexmk_build/` directories

### 6. Verify

```bash
# Check prerequisites
python3 vendor/ktisma/bin/ktisma doctor

# Verify routing for a source file
python3 vendor/ktisma/bin/ktisma inspect route lectures-tex/week1.tex

# Build and confirm output
python3 vendor/ktisma/bin/ktisma build lectures-tex/week1.tex
```

## Transitional .latexmkrc Shim

If you need to keep `latexmk` working during a gradual transition (e.g., CI pipelines that call
`latexmk` directly), ktisma can generate a minimal `.latexmkrc` shim:

```python
from ktisma.adapters.latexmkrc import write_latexmkrc
from pathlib import Path

write_latexmkrc(workspace_root=Path("."))
```

This produces a `.latexmkrc` that uses the same build directory layout as ktisma. Remove it once
you have fully migrated to calling ktisma directly. See
[Editor Integration: Transitional .latexmkrc](../editor-integration.md#transitional-latexmkrc-generation).

## Common Migration Scenarios

### Flat Project (Single .tex File)

No special routing needed. The default config works:

```toml
schema_version = 1
```

The PDF is placed beside the source file (fallback routing).

### Multi-Document Project with -tex/-pdfs Convention

If your project already uses the `-tex`/`-pdfs` directory naming, the default suffix convention
handles routing automatically. For nested `main.tex` files, enable entrypoint collapse:

```toml
schema_version = 1

[routing]
collapse_entrypoint_names = true
```

See [Project Layout: Entrypoint Collapse](project-layout.md#entrypoint-collapse).

### Project with Dual Outputs

If you had a shell script that compiled documents twice — once normally and once with a TeX macro
injected — replace it with the [variants](../build-lifecycle.md#variants) feature:

```toml
schema_version = 1

[routing]
default_filename_suffix = ""
variant_filename_suffix = "_{variant}"

[variants.review]
payload = "\\def\\ShowReviewMarkup{}"
filename_suffix = "_review"
```

Build both outputs:

```bash
# Default build
python3 vendor/ktisma/bin/ktisma build exercises-tex/algebra.tex
# -> exercises-pdfs/algebra.pdf

# Review variant
python3 vendor/ktisma/bin/ktisma build exercises-tex/algebra.tex --variant review
# -> exercises-pdfs/algebra_review.pdf

# Default output plus all configured variants
python3 vendor/ktisma/bin/ktisma variants exercises-tex/algebra.tex --include-default
```

### Batch Compilation

If you had a script that compiled every entrypoint `.tex` file in a directory tree, use
[`ktisma batch`](../cli-reference.md#batch):

```bash
python3 vendor/ktisma/bin/ktisma batch exercises-tex/
```
