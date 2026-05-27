<a id="application"></a>

# Application

Application services: build, clean, doctor, inspect, batch, variants,
configuration, and the service protocols.

<a id="module-ktisma.app.build"></a>

<a id="build"></a>

## Build

<a id="ktisma.app.build.BuildResult"></a>

### *class* ktisma.app.build.BuildResult(exit_code: 'ExitCode', engine: 'Optional[EngineDecision]' = None, route: 'Optional[RouteDecision]' = None, build_plan: 'Optional[BuildDirPlan]' = None, backend_result: 'Optional[BackendResult]' = None, produced_paths: 'list[Path]' = <factory>, diagnostics: 'list[Diagnostic]' = <factory>)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

<a id="ktisma.app.build.BuildResult.exit_code"></a>

#### exit_code *: [ExitCode](domain.md#ktisma.domain.exit_codes.ExitCode)*

<a id="ktisma.app.build.BuildResult.engine"></a>

#### engine *: [EngineDecision](domain.md#ktisma.domain.engine.EngineDecision) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*

<a id="ktisma.app.build.BuildResult.route"></a>

#### route *: [RouteDecision](domain.md#ktisma.domain.routing.RouteDecision) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*

<a id="ktisma.app.build.BuildResult.build_plan"></a>

#### build_plan *: [BuildDirPlan](domain.md#ktisma.domain.build_dir.BuildDirPlan) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*

<a id="ktisma.app.build.BuildResult.backend_result"></a>

#### backend_result *: [BackendResult](#ktisma.app.protocols.BackendResult) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*

<a id="ktisma.app.build.BuildResult.produced_paths"></a>

#### produced_paths *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)]*

<a id="ktisma.app.build.BuildResult.diagnostics"></a>

#### diagnostics *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Diagnostic](domain.md#ktisma.domain.diagnostics.Diagnostic)]*

<a id="ktisma.app.build.execute_build"></a>

### ktisma.app.build.execute_build(ctx, request, services, route_resolvers=None, engine_rules=None)

Execute the build use-case.

<a id="module-ktisma.app.clean"></a>

<a id="clean"></a>

## Clean

<a id="ktisma.app.clean.CleanResult"></a>

### *class* ktisma.app.clean.CleanResult(exit_code: 'ExitCode', removed_dirs: 'list[Path]' = <factory>, diagnostics: 'list[Diagnostic]' = <factory>)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

<a id="ktisma.app.clean.CleanResult.exit_code"></a>

#### exit_code *: [ExitCode](domain.md#ktisma.domain.exit_codes.ExitCode)*

<a id="ktisma.app.clean.CleanResult.removed_dirs"></a>

#### removed_dirs *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)]*

<a id="ktisma.app.clean.CleanResult.diagnostics"></a>

#### diagnostics *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Diagnostic](domain.md#ktisma.domain.diagnostics.Diagnostic)]*

<a id="ktisma.app.clean.execute_clean"></a>

### ktisma.app.clean.execute_clean(target, workspace_root, config_loader, workspace_ops)

Clean build directories for a source file or a specific build directory.

If target is a .tex file, removes its build directory.
If target is a directory, removes it directly (if it looks like a ktisma build dir).

<a id="module-ktisma.app.doctor"></a>

<a id="doctor"></a>

## Doctor

<a id="ktisma.app.doctor.DoctorResult"></a>

### *class* ktisma.app.doctor.DoctorResult(exit_code: 'ExitCode', checks: 'list[PrerequisiteCheck]' = <factory>, diagnostics: 'list[Diagnostic]' = <factory>)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

<a id="ktisma.app.doctor.DoctorResult.exit_code"></a>

#### exit_code *: [ExitCode](domain.md#ktisma.domain.exit_codes.ExitCode)*

<a id="ktisma.app.doctor.DoctorResult.checks"></a>

#### checks *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[PrerequisiteCheck](#ktisma.app.protocols.PrerequisiteCheck)]*

<a id="ktisma.app.doctor.DoctorResult.diagnostics"></a>

#### diagnostics *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Diagnostic](domain.md#ktisma.domain.diagnostics.Diagnostic)]*

<a id="ktisma.app.doctor.execute_doctor"></a>

### ktisma.app.doctor.execute_doctor(workspace_root, config_loader, probe)

Run prerequisite checks per roadmap doctor specification.

Verifies:
- latexmk is on PATH
- configured default engines are available
- Python meets minimum version requirement
- TOML parsing is available
- workspace root resolution works
- any present .ktisma.toml validates successfully

<a id="module-ktisma.app.inspect"></a>

<a id="inspect"></a>

## Inspect

<a id="ktisma.app.inspect.inspect_engine"></a>

### ktisma.app.inspect.inspect_engine(ctx, request, config_loader, source_reader, engine_rules=None)

Inspect engine selection without compiling.

Reuses the same config and decision path as build, stopping before compilation.

<a id="ktisma.app.inspect.inspect_route"></a>

### ktisma.app.inspect.inspect_route(ctx, request, config_loader, source_reader, route_resolvers=None)

Inspect routing without compiling.

Reuses the same config and decision path as build, stopping before compilation.

<a id="module-ktisma.app.batch"></a>

<a id="batch"></a>

## Batch

<a id="ktisma.app.batch.BatchResult"></a>

### *class* ktisma.app.batch.BatchResult(exit_code: 'ExitCode', results: 'list[tuple[Path, BuildResult]]' = <factory>, diagnostics: 'list[Diagnostic]' = <factory>)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

<a id="ktisma.app.batch.BatchResult.exit_code"></a>

#### exit_code *: [ExitCode](domain.md#ktisma.domain.exit_codes.ExitCode)*

<a id="ktisma.app.batch.BatchResult.results"></a>

#### results *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path), [BuildResult](#ktisma.app.build.BuildResult)]]*

<a id="ktisma.app.batch.BatchResult.diagnostics"></a>

#### diagnostics *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Diagnostic](domain.md#ktisma.domain.diagnostics.Diagnostic)]*

<a id="ktisma.app.batch.execute_batch"></a>

### ktisma.app.batch.execute_batch(source_dir, workspace_root, request, services, route_resolvers=None, engine_rules=None)

Build all .tex files in a directory.

Composes the same build use-case for each source file.
batch –watch is unsupported in v1 and rejected explicitly.

<a id="module-ktisma.app.variants"></a>

<a id="variants"></a>

## Variants

<a id="ktisma.app.variants.VariantsResult"></a>

### *class* ktisma.app.variants.VariantsResult(exit_code: 'ExitCode', results: 'list[tuple[VariantSpec, BuildResult]]' = <factory>, diagnostics: 'list[Diagnostic]' = <factory>)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

<a id="ktisma.app.variants.VariantsResult.exit_code"></a>

#### exit_code *: [ExitCode](domain.md#ktisma.domain.exit_codes.ExitCode)*

<a id="ktisma.app.variants.VariantsResult.results"></a>

#### results *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[VariantSpec](domain.md#ktisma.domain.context.VariantSpec), [BuildResult](#ktisma.app.build.BuildResult)]]*

<a id="ktisma.app.variants.VariantsResult.diagnostics"></a>

#### diagnostics *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Diagnostic](domain.md#ktisma.domain.diagnostics.Diagnostic)]*

<a id="ktisma.app.variants.validate_variant_name"></a>

### ktisma.app.variants.validate_variant_name(name)

Check if a variant name is valid for use in filenames.

<a id="ktisma.app.variants.execute_variants"></a>

### ktisma.app.variants.execute_variants(ctx, request, services, route_resolvers=None, engine_rules=None)

Build all configured variants for a source file.

Each variant uses its own build directory and produces a uniquely named output.

<a id="module-ktisma.app.configuration"></a>

<a id="configuration"></a>

## Configuration

<a id="ktisma.app.configuration.load_resolved_config"></a>

### ktisma.app.configuration.load_resolved_config(workspace_root, source_dir, config_loader, extra_layers=None)

Load, merge, and validate config layers for a source context.

<a id="module-ktisma.app.protocols"></a>

<a id="service-protocols"></a>

## Service protocols

<a id="ktisma.app.protocols.ConfigLoader"></a>

### *class* ktisma.app.protocols.ConfigLoader(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

<a id="ktisma.app.protocols.ConfigLoader.load_layers"></a>

#### load_layers(workspace_root, source_dir)

Load config layers from workspace root to source directory.

Returns layers ordered from lowest to highest precedence
(workspace config first, nearest overlays last).

<a id="ktisma.app.protocols.SourceReader"></a>

### *class* ktisma.app.protocols.SourceReader(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

<a id="ktisma.app.protocols.SourceReader.read_source"></a>

#### read_source(source_file)

Read a source file and extract preamble text and magic comments.

<a id="ktisma.app.protocols.LockManager"></a>

### *class* ktisma.app.protocols.LockManager(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

<a id="ktisma.app.protocols.LockManager.acquire"></a>

#### acquire(lock_file, source_path, mode)

Acquire an exclusive build lock.

Raises LockContention if the lock cannot be acquired.

<a id="ktisma.app.protocols.LockManager.release"></a>

#### release(lock_file)

Release a previously acquired build lock.

<a id="ktisma.app.protocols.BackendResult"></a>

### *class* ktisma.app.protocols.BackendResult(success: 'bool', exit_code: 'int', stdout: 'str' = '', stderr: 'str' = '', pdf_path: 'Optional[Path]' = None, diagnostics: 'list[Diagnostic]' = <factory>)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

<a id="ktisma.app.protocols.BackendResult.success"></a>

#### success *: [bool](https://docs.python.org/3/library/functions.html#bool)*

<a id="ktisma.app.protocols.BackendResult.exit_code"></a>

#### exit_code *: [int](https://docs.python.org/3/library/functions.html#int)*

<a id="ktisma.app.protocols.BackendResult.stdout"></a>

#### stdout *: [str](https://docs.python.org/3/library/stdtypes.html#str)* *= ''*

<a id="ktisma.app.protocols.BackendResult.stderr"></a>

#### stderr *: [str](https://docs.python.org/3/library/stdtypes.html#str)* *= ''*

<a id="ktisma.app.protocols.BackendResult.pdf_path"></a>

#### pdf_path *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*

<a id="ktisma.app.protocols.BackendResult.diagnostics"></a>

#### diagnostics *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Diagnostic](domain.md#ktisma.domain.diagnostics.Diagnostic)]*

<a id="ktisma.app.protocols.WatchUpdate"></a>

### *class* ktisma.app.protocols.WatchUpdate(result: 'BackendResult', finished: 'bool' = False)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

<a id="ktisma.app.protocols.WatchUpdate.result"></a>

#### result *: [BackendResult](#ktisma.app.protocols.BackendResult)*

<a id="ktisma.app.protocols.WatchUpdate.finished"></a>

#### finished *: [bool](https://docs.python.org/3/library/functions.html#bool)* *= False*

<a id="ktisma.app.protocols.WatchSession"></a>

### *class* ktisma.app.protocols.WatchSession(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

<a id="ktisma.app.protocols.WatchSession.poll"></a>

#### poll(timeout_seconds=0.5)

Wait briefly for a rebuild update or final process completion.

<a id="ktisma.app.protocols.WatchSession.terminate"></a>

#### terminate()

Terminate the active watch process and return its final status.

<a id="ktisma.app.protocols.BackendRunner"></a>

### *class* ktisma.app.protocols.BackendRunner(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

<a id="ktisma.app.protocols.BackendRunner.compile"></a>

#### compile(source_file, build_dir, engine, synctex, extra_args=None)

Run the compilation backend and return structured results.

<a id="ktisma.app.protocols.BackendRunner.start_watch"></a>

#### start_watch(source_file, build_dir, engine, synctex, extra_args=None)

Launch the backend in continuous watch mode.

<a id="ktisma.app.protocols.Materializer"></a>

### *class* ktisma.app.protocols.Materializer(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

<a id="ktisma.app.protocols.Materializer.materialize"></a>

#### materialize(source, destination)

Copy or move a build artifact to its final destination.

Creates parent directories as needed.

<a id="ktisma.app.protocols.WorkspaceOps"></a>

### *class* ktisma.app.protocols.WorkspaceOps(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

<a id="ktisma.app.protocols.WorkspaceOps.ensure_directory"></a>

#### ensure_directory(path)

Create a directory and any missing parents.

<a id="ktisma.app.protocols.WorkspaceOps.path_exists"></a>

#### path_exists(path)

Return whether a path exists.

<a id="ktisma.app.protocols.WorkspaceOps.is_directory"></a>

#### is_directory(path)

Return whether a path is a directory.

<a id="ktisma.app.protocols.WorkspaceOps.list_directory"></a>

#### list_directory(path)

List a directory’s entries.

<a id="ktisma.app.protocols.WorkspaceOps.read_text"></a>

#### read_text(path)

Read UTF-8 text from a file.

<a id="ktisma.app.protocols.WorkspaceOps.write_text"></a>

#### write_text(path, content)

Write UTF-8 text to a file, creating parents as needed.

<a id="ktisma.app.protocols.WorkspaceOps.remove_tree"></a>

#### remove_tree(path)

Recursively remove a directory tree.

<a id="ktisma.app.protocols.WorkspaceOps.glob_files"></a>

#### glob_files(path, pattern)

Return sorted files matching a glob pattern in a directory.

<a id="ktisma.app.protocols.PrerequisiteCheck"></a>

### *class* ktisma.app.protocols.PrerequisiteCheck(name: 'str', available: 'bool', version: 'Optional[str]' = None, message: 'str' = '')

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

<a id="ktisma.app.protocols.PrerequisiteCheck.name"></a>

#### name *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

<a id="ktisma.app.protocols.PrerequisiteCheck.available"></a>

#### available *: [bool](https://docs.python.org/3/library/functions.html#bool)*

<a id="ktisma.app.protocols.PrerequisiteCheck.version"></a>

#### version *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*

<a id="ktisma.app.protocols.PrerequisiteCheck.message"></a>

#### message *: [str](https://docs.python.org/3/library/stdtypes.html#str)* *= ''*

<a id="ktisma.app.protocols.PrerequisiteProbe"></a>

### *class* ktisma.app.protocols.PrerequisiteProbe(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

<a id="ktisma.app.protocols.PrerequisiteProbe.check_latexmk"></a>

#### check_latexmk()

Check if latexmk is available on PATH.

<a id="ktisma.app.protocols.PrerequisiteProbe.check_engine"></a>

#### check_engine(engine)

Check if a specific LaTeX engine is available.

<a id="ktisma.app.protocols.PrerequisiteProbe.check_python_version"></a>

#### check_python_version()

Check if the Python version meets minimum requirements.

<a id="ktisma.app.protocols.PrerequisiteProbe.check_toml_support"></a>

#### check_toml_support()

Check if TOML parsing is available.

<a id="ktisma.app.protocols.PostProcessor"></a>

### *class* ktisma.app.protocols.PostProcessor(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

<a id="ktisma.app.protocols.PostProcessor.process"></a>

#### process(materialized_pdf, ctx, variant=None)

Run post-materialization steps before cleanup.

<a id="ktisma.app.protocols.BuildServices"></a>

### *class* ktisma.app.protocols.BuildServices(config_loader, source_reader, lock_manager, backend_runner, materializer, prerequisite_probe, workspace_ops, post_processor=None)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Bundle of protocol dependencies for build use-cases.

Constructed once at the composition root and threaded through
`execute_build`, `execute_batch`, and `execute_variants`
instead of passing each dependency as a separate argument.

<a id="ktisma.app.protocols.BuildServices.config_loader"></a>

#### config_loader *: [ConfigLoader](#ktisma.app.protocols.ConfigLoader)*

<a id="ktisma.app.protocols.BuildServices.source_reader"></a>

#### source_reader *: [SourceReader](#ktisma.app.protocols.SourceReader)*

<a id="ktisma.app.protocols.BuildServices.lock_manager"></a>

#### lock_manager *: [LockManager](#ktisma.app.protocols.LockManager)*

<a id="ktisma.app.protocols.BuildServices.backend_runner"></a>

#### backend_runner *: [BackendRunner](#ktisma.app.protocols.BackendRunner)*

<a id="ktisma.app.protocols.BuildServices.materializer"></a>

#### materializer *: [Materializer](#ktisma.app.protocols.Materializer)*

<a id="ktisma.app.protocols.BuildServices.prerequisite_probe"></a>

#### prerequisite_probe *: [PrerequisiteProbe](#ktisma.app.protocols.PrerequisiteProbe)*

<a id="ktisma.app.protocols.BuildServices.workspace_ops"></a>

#### workspace_ops *: [WorkspaceOps](#ktisma.app.protocols.WorkspaceOps)*

<a id="ktisma.app.protocols.BuildServices.post_processor"></a>

#### post_processor *: [PostProcessor](#ktisma.app.protocols.PostProcessor) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*
