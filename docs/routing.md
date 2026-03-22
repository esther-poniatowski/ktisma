# Routing

Routing determines where the compiled PDF is placed after a successful build. Ktisma uses a
multi-step resolution chain that guarantees every build produces a routed output — the final step
always succeeds.

## Resolution Chain

Routing precedence, highest first:

1. **CLI exact output override** (`--output`)
2. **CLI output directory override** (`--output-dir`)
3. **Magic-comment output override** (`% !ktisma output = ...`)
4. **Custom route resolvers**
5. **Explicit config route rules** (`[routes]`)
6. **Suffix convention** (`-tex/` to `-pdfs/`)
7. **Safe fallback** (beside the source file)

The first step that produces a match is used. Step 7 always resolves, ensuring routing mismatch
never strands a PDF.

## CLI Overrides

Use `--output` when you need to choose the exact PDF path:

```bash
ktisma build paper.tex --output ~/Desktop/review-copy.pdf
```

Use `--output-dir` when you want to preserve ktisma's filename logic but override the directory:

```bash
ktisma build paper.tex --output-dir ~/Desktop/
```

`--output` takes absolute precedence. `--output-dir` is consulted only when `--output` is not
set. Both paths resolve relative to the current working directory.

## Magic Comment Override

```latex
% !ktisma output = ../output/
```

The path resolves relative to the source file's directory. A trailing `/` indicates the path is a
directory and the source basename is preserved.

## Explicit Route Rules

Route rules are defined in the `[routes]` section of `.ktisma.toml`:

```toml
[routes]
"lectures-tex/**" = "lectures-pdfs/"
"drafts/*.tex" = "output/"
"thesis/main.tex" = "~/Documents/thesis-builds/"
```

Patterns use glob syntax and match against the source file's path relative to the workspace root.

### Specificity Scoring

When multiple route rules match the same source file within a single config layer, ktisma uses
specificity scoring to choose:

1. **Exact file matches** beat glob matches.
2. **More literal path segments** beat fewer.
3. **Fewer wildcard segments** beat more.
4. If remaining candidates resolve to the **same destination**, the ambiguity is harmless and
   ktisma proceeds silently.
5. Otherwise, ktisma emits a **warning diagnostic** and uses the first matching rule in
   declaration order.

### Route Target Resolution

- Targets ending in `/` are treated as directories: the source basename (with `.pdf` extension)
  is placed inside.
- Targets with a file extension are treated as explicit file paths.
- `~` is expanded before resolution.
- Relative targets resolve against the declaring config file's directory.

## Suffix Convention

The default naming convention maps `*-tex/` source directories to sibling `*-pdfs/` output
directories:

| Source | Output |
| --- | --- |
| `slides-tex/week1.tex` | `slides-pdfs/week1.pdf` |
| `slides-tex/deck/main.tex` | `slides-pdfs/deck/main.pdf` |

This convention applies when:

- The source directory name ends with the configured `source_suffix` (default: `-tex`)
- No explicit route rule or override matched

The suffix convention preserves relative paths beneath the source root and preserves the source
basename. Missing `*-pdfs/` siblings are created automatically when the output is materialized.

If multiple nested directories match the configured `source_suffix`, ktisma uses the nearest
match and emits a warning diagnostic describing the ignored outer matches.

### Configuring the Convention

```toml
[routing]
source_suffix = "-tex"        # Suffix identifying source directories
output_suffix = "-pdfs"       # Suffix for output directories
preserve_relative = true       # Preserve relative path structure
default_filename_suffix = ""   # Applied to non-variant outputs
variant_filename_suffix = "_{variant}"
```

### Entrypoint Collapse

By default, the source basename is always preserved. Repositories that prefer collapsing
entrypoint filenames into the parent directory name can opt in:

```toml
[routing]
collapse_entrypoint_names = true
entrypoint_names = ["main", "index"]
```

With this configuration:

| Source | Output |
| --- | --- |
| `slides-tex/deck/main.tex` | `slides-pdfs/deck.pdf` |
| `slides-tex/deck/appendix.tex` | `slides-pdfs/deck/appendix.pdf` |

Collapse only applies to files whose stem matches one of the `entrypoint_names`. Other files
preserve the full relative path.

## Safe Fallback

If no explicit rule or convention applies:

- The PDF is materialized **next to the source file** (same directory, `.pdf` extension).
- A diagnostic is emitted explaining that fallback routing was used.
- If the source lies outside the workspace root, ktisma emits an additional warning explaining
  that workspace-relative routes and suffix conventions were skipped.
- The build remains successful — fallback does not change the exit code.

This ensures the only successful PDF is never lost due to a routing configuration gap.

## Variant Output Naming

Variant builds can customize both the filename and the destination. By default, ktisma appends the
configured `variant_filename_suffix` template:

| Base | Variant | Output |
| --- | --- | --- |
| `exercises.tex` | `review` | `exercises_review.pdf` |
| `exercises.tex` | `handout` | `exercises_handout.pdf` |

You can override that per variant:

```toml
[routing]
default_filename_suffix = "_draft"
variant_filename_suffix = "_{variant}"

[variants.review]
payload = "\\def\\ShowReviewMarkup{}"
filename_suffix = ""
output = "../review-pdfs/"
```

- `default_filename_suffix` changes the non-variant filename.
- `variant_filename_suffix` changes the default variant filename pattern.
- `variants.<name>.filename_suffix` overrides the pattern for one variant.
- `variants.<name>.output` overrides the routed output directory or file for one variant.

## Inspecting Routes

Use `inspect route` to see where a file would be routed without building:

```bash
ktisma inspect route slides-tex/week1.tex
```

Add `--json` for machine-readable output:

```json
{
  "source": "slides-tex/week1.tex",
  "destination": "slides-pdfs/week1.pdf",
  "matched_rule": "lectures-tex/**",
  "fallback": false,
  "diagnostics": []
}
```

## Custom Route Resolvers

The routing function accepts an optional `extra_resolvers` parameter: a list of callables
matching the `RouteResolver` signature. Custom resolvers are checked after magic-comment
overrides but before the built-in config route rules, allowing pluggable resolution strategies
without modifying the core routing module.
