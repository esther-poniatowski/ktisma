# Roadmap

Implementation plan for ktisma, derived from the analysis of existing build infrastructure across
the following workspaces:

- `/Users/eresther/Documents/work/techne/`
- `/Users/eresther/Documents/work/research/RS-ctx-dep-net/`
- `/Users/eresther/Documents/teaching/thoth/`

---

## Phase 1: Core Scripts

Unify the divergent `latexmk-helper.sh` copies into a single, robust post-compilation handler and
extract engine detection into a standalone script.

### 1.1 Engine Detection (`scripts/detect-engine.sh`)

- [ ] Accept a `.tex` file path as input.
- [ ] Recursively follow `\input` and `\include` chains to collect all loaded files.
- [ ] Scan for engine-specific markers:
  - `fontspec`, `polyglossia`, `\RequireXeTeX` --> xelatex
  - `fontspec`, `polyglossia`, `\RequireLuaTeX`, `luacode` --> lualatex
  - Absence of the above --> pdflatex
- [ ] Resolve ambiguity (both XeTeX and LuaTeX markers) with a deterministic priority rule.
- [ ] Output the engine name to stdout (consumable by latexmkrc or other scripts).

### 1.2 Post-Compilation Handler (`scripts/post-compile.sh`)

Merge the three existing `latexmk-helper.sh` variants into one script that supports all observed
directory layouts.

- [ ] Walk up from the source file to find the nearest `*-tex` ancestor directory.
- [ ] Support flat layout: `presentations-tex/file.tex` --> `presentations-pdfs/file.pdf`.
- [ ] Support nested layout: `presentations-tex/deck/main.tex` --> `presentations-pdfs/deck.pdf`.
- [ ] Support non-`*-tex` directories (graceful fallback: leave PDF in place, still clean artifacts).
- [ ] Remove `.latexmk_build/` after successful PDF relocation.
- [ ] Emit structured status messages (success, warning, error) to stderr.

---

## Phase 2: Shared Latexmkrc

Replace the per-workspace `.latexmkrc` files with a shared configuration that integrates engine
detection and post-compilation.

### 2.1 Package-Level Latexmkrc (`latexmkrc`)

- [ ] Call `detect-engine.sh` on the source file to determine `$pdf_mode` and the compiler command.
- [ ] Set `$success_cmd` to invoke `post-compile.sh`.
- [ ] Disable SyncTeX by default (configurable).
- [ ] Resolve script paths relative to `$ENV{KTISMA}` (no hardcoded absolute paths).

### 2.2 Workspace-Level Integration

- [ ] Define the one-liner `.latexmkrc` pattern for consuming workspaces:
  `do "$ENV{KTISMA}/latexmkrc";`
- [ ] Document per-project override mechanism (e.g., force a specific engine).
- [ ] Test layered configuration: package --> workspace --> project.

---

## Phase 3: Extended Build Modes

Port the specialized build scripts from thoth into the shared toolkit.

### 3.1 Batch Compilation (`scripts/compile-batch.sh`)

- [ ] Accept a `*-tex/` directory path.
- [ ] Compile all `.tex` files in the directory using the shared latexmkrc.
- [ ] Route PDFs to the sibling `*-pdfs/` directory.
- [ ] Report per-file success/failure summary.

### 3.2 Dual-Version Compilation (`scripts/compile-dual.sh`)

- [ ] Accept a `.tex` file path and a macro name (default: `\ForceSolutions`).
- [ ] First pass: compile as-is (blank version).
- [ ] Second pass: compile with macro injection (corrected version).
- [ ] Output both `*_blank.pdf` and `*.pdf` to the output directory.
- [ ] Clean up both build directories.

---

## Phase 4: VS Code Integration

Provide importable configuration snippets so consuming workspaces do not duplicate LaTeX Workshop
settings.

### 4.1 Configuration Snippets (`vscode/`)

- [ ] `tools.jsonc`: LaTeX Workshop tool definitions with `KTISMA` env var.
- [ ] `recipes.jsonc`: Recipe definitions referencing the tools.
- [ ] `settings.jsonc`: Recommended settings (autoClean, autoBuild, PDF viewer).

### 4.2 Documentation

- [ ] Document how to reference snippets from a `.code-workspace` file.
- [ ] Provide a migration guide for each existing workspace.

---

## Phase 5: Gitignore Fragment

### 5.1 Canonical Fragment (`gitignore-fragments/latex.gitignore`)

- [ ] Consolidate the LaTeX-related `.gitignore` entries shared across all workspaces.
- [ ] Document inclusion via `cat` or symlink into consuming workspace `.gitignore`.

---

## Phase 6: Migration

Integrate ktisma into the three existing workspaces and remove the duplicated infrastructure.

### 6.1 Add Submodule

- [ ] Add ktisma as a submodule at `vendor/ktisma/` in each workspace.

### 6.2 Replace Per-Workspace Files

For each workspace (techne, RS-ctx-dep-net, thoth):

- [ ] Replace `.latexmkrc` with the one-liner sourcing ktisma.
- [ ] Remove the local `latexmk-helper.sh` (and other duplicated build scripts).
- [ ] Update VS Code workspace file to use ktisma tool/recipe definitions.
- [ ] Verify compilation of all documents (pdflatex and lualatex projects).
- [ ] Verify PDF routing and artifact cleanup.

---

## Design Principles

- **No hardcoded paths**: All script resolution via `$KTISMA` environment variable.
- **Layered overrides**: Package defaults < workspace config < project config.
- **Standalone scripts**: Each script is independently callable from CLI, latexmkrc, or VS Code.
- **Convention over configuration**: `*-tex/` to `*-pdfs/` is the default; non-conforming layouts
  degrade gracefully rather than failing.
- **Minimal dependencies**: POSIX shell + latexmk + TeX Live. No Python or other runtimes required.
