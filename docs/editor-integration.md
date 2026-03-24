# Editor Integration

Ktisma is designed to be called directly from editor build recipes. The canonical CLI is the
source of truth -- editor adapters wrap it rather than reimplementing build logic.

## VS Code with LaTeX Workshop

### Recommended Configuration

Add the following to the workspace `.vscode/settings.json`:

```jsonc
{
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
}
```

Key points:

- The recipe calls ktisma directly rather than wrapping `latexmk` in `bash -c`.
- `autoClean` is set to `"never"` because ktisma manages cleanup through its own policies.
- Use the placeholder that expands to the resolved root document including its `.tex` extension.
  In LaTeX Workshop that is typically `%DOC_EXT%`.
- Add `--workspace-root %WORKSPACE_FOLDER%` only when pinning the workspace root explicitly in
  the editor recipe, instead of relying on ktisma's config discovery.

### Generating the Configuration

Ktisma can generate the LaTeX Workshop configuration snippet programmatically:

```python
from ktisma.adapters.vscode import format_latex_workshop_snippet

print(format_latex_workshop_snippet())
```

Or with a custom ktisma path:

```python
print(format_latex_workshop_snippet("/absolute/path/to/ktisma/bin/ktisma"))
```

### Adapter-Provided Workspace Root

When ktisma is invoked from an editor, the adapter can pass the editor's workspace root via the
`--workspace-root` flag or through the adapter API when explicit pinning is needed. The flag takes
precedence over environment variables and `.ktisma.toml` discovery (see
[Configuration: Workspace Root Resolution](configuration.md#workspace-root-resolution)).

## Other Editors

Any editor that supports running external build commands can use ktisma. The integration pattern
is the same:

1. Configure the editor to run `python3 /path/to/ktisma/bin/ktisma build <source.tex>
   [--workspace-root <root>]`.
2. Disable the editor's own cleanup if ktisma manages it.
3. Optionally use `--json` for machine-readable output that the editor can parse.

### Vim/Neovim

Example `:make` integration:

```vim
set makeprg=python3\ vendor/ktisma/bin/ktisma\ build\ %\ --workspace-root\ .
```

### Emacs

Example `compile-command` integration:

```elisp
(setq compile-command "python3 vendor/ktisma/bin/ktisma build ")
```

## Transitional `.latexmkrc` Generation

For workspaces migrating from standalone `latexmk` configurations, ktisma can generate minimal
`.latexmkrc` shims:

```python
from ktisma.adapters.latexmkrc import write_latexmkrc

write_latexmkrc(workspace_root=Path("."), stem="main")
```

The generated file configures `latexmk` to use the same build directory layout as ktisma and
includes a comment indicating it should be removed after migration is complete.

The adapter is optional and does not affect the core build path.

## Installation for Editor Use

### Git Submodule (Recommended)

```bash
git submodule add https://github.com/esther-poniatowski/ktisma.git vendor/ktisma
```

Then reference `vendor/ktisma/bin/ktisma` in the editor configuration.

### Symlink

```bash
ln -s /path/to/ktisma vendor/ktisma
```

### Direct Path

If ktisma is installed globally or in a known location, reference it directly:

```jsonc
"command": "python3",
"args": ["/path/to/ktisma/bin/ktisma", "build", "%DOC_EXT%"]
```

## Diagnostics in Editors

Ktisma writes diagnostics to stderr in human-readable format by default. With `--json`, it
writes structured output to stdout that editors can parse for integration with problem matchers
or diagnostic panels.

The JSON output includes diagnostic records with `level`, `code`, and `message` fields that map
naturally to editor diagnostic severities.
