# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- `ktisma tex resolve`: returns the absolute path of a declared entry point only after the selected
  snapshot and named provider pass their checks.
- `ktisma check-log`: checks recursively discovered LaTeX logs against a zero baseline and reports
  selected measurement channels. A log that is not valid UTF-8, such as a pdfTeX log splitting a
  multi-byte character at a line wrap, is read with each invalid byte sequence replaced by `�`.
- Placeholders in output paths: the output path of a `% !ktisma output` magic comment and the
  targets of `[routes]` expand `{stem}`, `{artifact}` and every key of the new `[placeholders]`
  table. `{artifact}` names the nearest ancestor directory matching `[routing].artifact_dirs`.
  An unresolved placeholder stops the build before compilation with an `unresolved-placeholder`
  error.
- Editor guide: viewing the build-directory PDF in LaTeX Workshop when the routed output is renamed.

### Changed

The command line follows the shared command-line conventions of the workspace. Every renamed name
below loses its former name in this release, without an alias, a fallback or a warning.

- **Settings file renamed.** Every settings file is now named `ktisma.toml`, without the leading
  dot: the workspace-root file and every overlay. A file named `.ktisma.toml` is no longer read and
  no longer marks a workspace root, and Ktisma then runs on its built-in defaults without a
  warning. Consumers must rename each `.ktisma.toml` file to `ktisma.toml`, for instance with
  `git mv .ktisma.toml ktisma.toml`.
- The workspace-root file may also sit in `config/tools/ktisma.toml`. A root that holds both
  `ktisma.toml` and `config/tools/ktisma.toml` is an error that names both files. Overlays below
  the root stay `ktisma.toml` in their own folder.
- The option `--workspace-root` is renamed `--root`, with the short form `-r`, on every command that
  takes it: `build`, `inspect engine`, `inspect route`, `clean`, `doctor`, `batch`, `variants`,
  `init`, `tex install`, `tex check`, `tex inspect` and `tex resolve`. `--workspace-root` is
  rejected as an unknown option, with exit code `2`.
- The environment variable `KTISMA_WORKSPACE_ROOT` is renamed `KTISMA_ROOT`. The former variable is
  ignored.
- The flag `--json` is replaced by `--format {text,json}`, with `text` as the default, on every
  command that took `--json`: `build`, `inspect engine`, `inspect route`, `doctor`, `batch`,
  `variants`, `tex install`, `tex check`, `tex inspect` and `tex resolve`. The output of
  `--format json` is identical to the former output of `--json`. `--json` is rejected as an unknown
  option, with exit code `2`.
- `-v` now prints the version, as `--version` does. `--verbose` keeps no short form.
- `--output` takes the short form `-o` on `build` and `inspect route`.
- A route target written in an overlay is now relative to the workspace root, as in the
  workspace-root file; it was relative to the folder of the overlay. A target written in the
  workspace-root file is unchanged.
- The workspace root no longer takes an adapter-provided root between `KTISMA_ROOT` and the
  search for a settings file: the Python entry points of `ktisma.adapters.bootstrap` lose their
  `adapter_workspace_root` parameter, and an adapter passes the root as `workspace_root`.
- Without `--root`, `clean` resolves the workspace root of a source as `build` does; it took the
  folder of the source, and so missed the settings of the root, such as `[build].out_dir_name`.
  `clean` refuses a folder of the state directory `.ktisma/`.
- Without `--root`, `doctor` validates the settings of the workspace root found from the current
  folder; it validated no settings file.
- `ktisma init` stops with exit code `2` and an error that names the existing wrapper script, unless
  `--force` is given; it skipped the wrapper silently. The wrapper sets `KTISMA_ROOT`. A wrapper
  written by an earlier release sets `KTISMA_WORKSPACE_ROOT`, which Ktisma now ignores: rerun
  `ktisma init --force`, or replace the variable in that script by hand.
