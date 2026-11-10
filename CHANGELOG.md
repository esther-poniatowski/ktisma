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

- The option `--workspace-root` is renamed `--root`, on every command that takes it: `build`,
  `inspect engine`, `inspect route`, `clean`, `doctor`, `batch`, `variants`, `init`, `tex install`,
  `tex check`, `tex inspect` and `tex resolve`.
- The environment variable `KTISMA_WORKSPACE_ROOT` is renamed `KTISMA_ROOT`. When both are set,
  `KTISMA_ROOT` takes precedence.
- The flag `--json` is replaced by `--format {text,json}`, with `text` as the default, on every
  command that took `--json`: `build`, `inspect engine`, `inspect route`, `doctor`, `batch`,
  `variants`, `tex install`, `tex check`, `tex inspect` and `tex resolve`. The output of
  `--format json` is identical to the former output of `--json`.
- The wrapper script written by `ktisma init` sets `KTISMA_ROOT`. A wrapper written by an earlier
  release still sets `KTISMA_WORKSPACE_ROOT`, and `ktisma init` does not overwrite it; replace the
  variable in that script by hand.

### Deprecated

- `--workspace-root`, `--json` and `KTISMA_WORKSPACE_ROOT` remain accepted for one release, and are
  hidden from the help. Ktisma prints a warning to stderr that names the replacement for each
  deprecated option used, and for `KTISMA_WORKSPACE_ROOT` whenever it is set while `KTISMA_ROOT` is
  unset or empty. The standard output is unchanged. `KTISMA_WORKSPACE_ROOT` is read only when
  `KTISMA_ROOT` is unset or empty.
