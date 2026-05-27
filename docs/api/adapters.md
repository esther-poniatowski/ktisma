<a id="adapters"></a>

# Adapters

External-facing adapters: CLI, bootstrap wiring, init scaffolding, logging,
VS Code integration, and transitional `.latexmkrc` shim generation.

<a id="module-ktisma.adapters.cli"></a>

<a id="cli"></a>

## CLI

<a id="ktisma.adapters.cli.main"></a>

### ktisma.adapters.cli.main(argv=None)

Main CLI entry point.

<a id="module-ktisma.adapters.bootstrap"></a>

<a id="bootstrap"></a>

## Bootstrap

<a id="ktisma.adapters.bootstrap.Services"></a>

### *class* ktisma.adapters.bootstrap.Services(config_loader, source_reader, lock_manager, backend_runner, materializer, probe, workspace_ops)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Wired infrastructure implementations.

All wiring of concrete infrastructure into application use-cases
happens here in the composition root.

<a id="ktisma.adapters.bootstrap.Services.config_loader"></a>

#### config_loader *: [TomlConfigLoader](infra.md#ktisma.infra.config_loader.TomlConfigLoader)*

<a id="ktisma.adapters.bootstrap.Services.source_reader"></a>

#### source_reader *: [FileSourceReader](infra.md#ktisma.infra.source_reader.FileSourceReader)*

<a id="ktisma.adapters.bootstrap.Services.lock_manager"></a>

#### lock_manager *: [FileLockManager](infra.md#ktisma.infra.locks.FileLockManager)*

<a id="ktisma.adapters.bootstrap.Services.backend_runner"></a>

#### backend_runner *: [LatexmkRunner](infra.md#ktisma.infra.latexmk.LatexmkRunner)*

<a id="ktisma.adapters.bootstrap.Services.materializer"></a>

#### materializer *: [FileMaterializer](infra.md#ktisma.infra.materialize.FileMaterializer)*

<a id="ktisma.adapters.bootstrap.Services.probe"></a>

#### probe *: [SystemPrerequisiteProbe](infra.md#ktisma.infra.prerequisites.SystemPrerequisiteProbe)*

<a id="ktisma.adapters.bootstrap.Services.workspace_ops"></a>

#### workspace_ops *: [FileWorkspaceOps](infra.md#ktisma.infra.workspace.FileWorkspaceOps)*

<a id="ktisma.adapters.bootstrap.create_services"></a>

### ktisma.adapters.bootstrap.create_services()

Construct concrete infrastructure implementations.

<a id="ktisma.adapters.bootstrap.build"></a>

### ktisma.adapters.bootstrap.build(source_file, request, workspace_root=None, adapter_workspace_root=None, post_processor=None, route_resolvers=None, engine_rules=None)

Composition root entry for the build use-case.

<a id="ktisma.adapters.bootstrap.inspect_engine_cmd"></a>

### ktisma.adapters.bootstrap.inspect_engine_cmd(source_file, request, workspace_root=None, adapter_workspace_root=None, engine_rules=None)

Composition root entry for inspect engine.

<a id="ktisma.adapters.bootstrap.inspect_route_cmd"></a>

### ktisma.adapters.bootstrap.inspect_route_cmd(source_file, request, workspace_root=None, adapter_workspace_root=None, route_resolvers=None)

Composition root entry for inspect route.

<a id="ktisma.adapters.bootstrap.clean"></a>

### ktisma.adapters.bootstrap.clean(target, workspace_root=None)

Composition root entry for the clean use-case.

<a id="ktisma.adapters.bootstrap.doctor"></a>

### ktisma.adapters.bootstrap.doctor(workspace_root=None)

Composition root entry for the doctor use-case.

<a id="ktisma.adapters.bootstrap.batch"></a>

### ktisma.adapters.bootstrap.batch(source_dir, request, workspace_root=None, post_processor=None, route_resolvers=None, engine_rules=None)

Composition root entry for the batch use-case.

<a id="ktisma.adapters.bootstrap.variants"></a>

### ktisma.adapters.bootstrap.variants(source_file, request, workspace_root=None, adapter_workspace_root=None, post_processor=None, route_resolvers=None, engine_rules=None)

Composition root entry for the variants use-case.

<a id="module-ktisma.adapters.init"></a>

<a id="init-scaffolding"></a>

## Init scaffolding

<a id="ktisma.adapters.init.execute_init"></a>

### ktisma.adapters.init.execute_init(workspace_root)

Initialize ktisma integration files in the workspace.

Creates a wrapper script at `scripts/ktisma` and prints the VS Code
LaTeX Workshop configuration snippet to stdout.

<a id="module-ktisma.adapters.log"></a>

<a id="logging"></a>

## Logging

<a id="ktisma.adapters.log.setup_logging"></a>

### ktisma.adapters.log.setup_logging(verbose=False)

Configure logging for the CLI adapter.

Per design principles: logging is optional developer instrumentation,
configured only in adapters.

<a id="ktisma.adapters.log.format_diagnostics"></a>

### ktisma.adapters.log.format_diagnostics(diagnostics, use_color=True)

Format diagnostics for human-readable stderr output.

<a id="module-ktisma.adapters.vscode"></a>

<a id="vs-code-integration"></a>

## VS Code integration

<a id="ktisma.adapters.vscode.generate_latex_workshop_config"></a>

### ktisma.adapters.vscode.generate_latex_workshop_config(ktisma_path='%WORKSPACE_FOLDER%/vendor/ktisma/bin/ktisma', \*, use_wrapper_script=False, extra_settings=None)

Generate LaTeX Workshop configuration for VS Code.

Returns a dict suitable for merging into .vscode/settings.json.

* **Parameters:**
  * **ktisma_path** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – Path (or VS Code variable expression) to the ktisma executable.
  * **use_wrapper_script** ([*bool*](https://docs.python.org/3/library/functions.html#bool)) – If `True`, the tool entry calls *ktisma_path* directly as the
    command (wrapper-script pattern used by `ktisma init`).
    If `False` (default), it invokes `python3` with *ktisma_path*
    as the first argument.
  * **extra_settings** ([*dict*](https://docs.python.org/3/library/stdtypes.html#dict) *[*[*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* [*object*](https://docs.python.org/3/library/functions.html#object) *]*  *|* *None*) – Additional VS Code settings to include in the returned dict
    (e.g. `{"latex-workshop.view.pdf.viewer": "tab"}`).

<a id="ktisma.adapters.vscode.format_latex_workshop_snippet"></a>

### ktisma.adapters.vscode.format_latex_workshop_snippet(ktisma_path='%WORKSPACE_FOLDER%/vendor/ktisma/bin/ktisma', \*, use_wrapper_script=False, extra_settings=None)

Format the LaTeX Workshop configuration as a JSONC snippet.

<a id="module-ktisma.adapters.latexmkrc"></a>

<a id="latexmkrc-shim"></a>

## latexmkrc shim

Generate minimal .latexmkrc shims for workspaces transitioning to ktisma.

Per roadmap: this adapter is optional, does not affect the core build path,
and does not read or parse existing .latexmkrc files.

<a id="ktisma.adapters.latexmkrc.generate_latexmkrc"></a>

### ktisma.adapters.latexmkrc.generate_latexmkrc(workspace_root, stem='main')

Generate a transitional .latexmkrc shim content.

<a id="ktisma.adapters.latexmkrc.write_latexmkrc"></a>

### ktisma.adapters.latexmkrc.write_latexmkrc(workspace_root, stem='main')

Write a transitional .latexmkrc to the workspace root.

Returns the path of the written file.
