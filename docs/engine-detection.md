# Engine Detection

Ktisma automatically selects the correct LaTeX engine for each source file by inspecting magic
comments, preamble markers, and configuration defaults.

## Detection Steps

Engine detection follows a strict precedence chain. The first step that produces a definitive
result wins:

1. **Magic comment**: Honor `% !TeX program = <engine>` if present in the source file.
2. **Definitive preamble markers**: Scan the main-file preamble (up to `\begin{document}`) for
   engine-specific commands.
3. **Ambiguous preamble markers**: If only ambiguous "modern engine required" markers are found,
   select `[engines].modern_default` (default: `lualatex`) and emit a diagnostic. If
   `strict_detection = true`, fail with an error instead.
4. **Config default**: If no markers are found, use `[engines].default` (default: `pdflatex`).

### CLI Override

The `--engine` flag bypasses all detection and uses the specified engine directly. This takes
the highest precedence of all.

## Input Boundary

Infrastructure reads the source file and extracts:

- **Magic comments**: `% !TeX program = ...` directives
- **Preamble text**: everything before `\begin{document}`

These are packaged into a `SourceInputs` object. The domain detection function consumes this
typed input and the resolved configuration — it never reads files directly.

## Marker Classes

### Definitive XeLaTeX Markers

These markers conclusively identify a document that requires XeLaTeX:

| Pattern | Description |
| --- | --- |
| `\RequireXeTeX` | Explicit XeTeX requirement |
| `ifxetex` | XeTeX conditional |
| XeTeX primitives | Engine-specific primitives |

### Definitive LuaLaTeX Markers

These markers conclusively identify a document that requires LuaLaTeX:

| Pattern | Description |
| --- | --- |
| `\RequireLuaTeX` | Explicit LuaTeX requirement |
| `luacode` | Lua code environment |
| `\directlua` | Direct Lua execution |
| `ifluatex` | LuaTeX conditional |
| `\luaexec` | Lua execution command |

### Ambiguous Modern-Engine Markers

These markers indicate a modern Unicode engine is needed but do not distinguish between XeLaTeX
and LuaLaTeX:

| Pattern | Description |
| --- | --- |
| `fontspec` | Unicode font selection package |
| `polyglossia` | Multilingual support (Unicode engines) |
| `unicode-math` | Unicode math package |

## Ambiguity Handling

When only ambiguous markers are found:

- **Default behavior** (`strict_detection = false`): Select `[engines].modern_default` (defaults
  to `lualatex`) and emit a warning diagnostic explaining the ambiguity and the evidence found.
- **Strict mode** (`strict_detection = true`): Fail with an error diagnostic. The user must pin
  the engine via a magic comment or explicit config.

## Engine Normalization

Engine names are normalized to canonical forms:

| Input | Normalized |
| --- | --- |
| `luatex` | `lualatex` |
| `pdftex` | `pdflatex` |
| `xetex` | `xelatex` |
| `pdflatex`, `lualatex`, `xelatex`, `latex` | unchanged |

## Custom Engine Rules

The detection function accepts an optional `custom_rules` parameter: a list of `EngineRule`
objects, each containing an engine name and a list of `(regex_pattern, description)` marker
tuples. Custom rules are checked after magic comments but before the built-in marker scan,
allowing users to supplement detection without modifying the core module.

## Limitations

- **Include-following**: v1 does not follow `\input` or `\include` directives. Documents whose
  engine-specific setup lives in included files must pin their engine via magic comment or config.
- **Preamble boundary**: Detection only scans text before `\begin{document}`. Markers appearing
  after this boundary are not considered.

## Configuration

Relevant configuration keys:

```toml
[engines]
default = "pdflatex"        # Fallback when no markers are detected
modern_default = "lualatex"  # Used for ambiguous modern-engine markers
strict_detection = false     # Fail on ambiguity instead of falling back
```

## Example Scenarios

**Document with `\RequireLuaTeX`**: Detected as `lualatex` (definitive marker, step 2).

**Document using `fontspec` only**: Detected as `lualatex` with an ambiguity warning (step 3,
using `modern_default`). With `strict_detection = true`, this would fail.

**Document with `% !TeX program = xelatex` and `fontspec`**: Detected as `xelatex` (magic
comment wins at step 1, preamble markers are not checked).

**Plain document with no markers**: Detected as `pdflatex` (config default, step 4).
