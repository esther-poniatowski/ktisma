# ktisma

Portable LaTeX build toolkit for predictable, shared document builds across multiple workspaces.
ktisma replaces duplicated `.latexmkrc` files, helper scripts, and editor-specific shell glue
with a single CLI and layered TOML configuration.

**New here?** Start with the [Getting Started](guide/getting-started.md) guide.
Migrating from an existing latexmk setup? See [Migrating from latexmk](guide/migration.md).

```{toctree}
:maxdepth: 2
:caption: User Guide

guide/getting-started
guide/project-layout
guide/migration
guide/recipes
```

```{toctree}
:maxdepth: 2
:caption: Design

design-principles
architecture
configuration
build-lifecycle
engine-detection
routing
```

```{toctree}
:maxdepth: 2
:caption: Reference

cli-reference
editor-integration
api/index
```

```{toctree}
:maxdepth: 1
:caption: Architecture Decisions

adr/adr-template
```
