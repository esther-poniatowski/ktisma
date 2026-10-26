# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- `ktisma check-log`: checks recursively discovered LaTeX logs against a zero baseline and reports
  selected measurement channels.
- Placeholders in output paths: the output path of a `% !ktisma output` magic comment and the
  targets of `[routes]` expand `{stem}`, `{artifact}` and every key of the new `[placeholders]`
  table. `{artifact}` names the nearest ancestor directory matching `[routing].artifact_dirs`.
  An unresolved placeholder stops the build before compilation with an `unresolved-placeholder`
  error.
- Editor guide: viewing the build-directory PDF in LaTeX Workshop when the routed output is renamed.
