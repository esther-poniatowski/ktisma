<a id="infrastructure"></a>

# Infrastructure

Infrastructure adapters: config loading, latexmk invocation, file locks,
materialization, prerequisite probing, source reading, and workspace ops.

<a id="module-ktisma.infra.config_loader"></a>

<a id="config-loader"></a>

## Config loader

<a id="ktisma.infra.config_loader.TomlConfigLoader"></a>

### *class* ktisma.infra.config_loader.TomlConfigLoader

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Concrete ConfigLoader: loads .ktisma.toml files from disk.

<a id="ktisma.infra.config_loader.TomlConfigLoader.load_layers"></a>

#### load_layers(workspace_root, source_dir)

Load config layers from workspace root toward the source directory.

Returns layers ordered from lowest to highest precedence:
1. Workspace .ktisma.toml (lowest)
2. Intermediate overlay .ktisma.toml files
3. Source-dir .ktisma.toml (highest file-based precedence)

<a id="ktisma.infra.config_loader.normalize_route_paths"></a>

### ktisma.infra.config_loader.normalize_route_paths(data)

Expand `~` and resolve symlinks on route target paths.

This function lives in the infrastructure layer because it performs
filesystem I/O (`expanduser`, `resolve`).  The application layer
calls it on the merged config dict after the domain merge completes.

<a id="module-ktisma.infra.latexmk"></a>

<a id="latexmk-runner"></a>

## Latexmk runner

<a id="ktisma.infra.latexmk.LatexmkRunner"></a>

### *class* ktisma.infra.latexmk.LatexmkRunner

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Concrete BackendRunner: invokes latexmk for compilation.

<a id="ktisma.infra.latexmk.LatexmkRunner.compile"></a>

#### compile(source_file, build_dir, engine, synctex, extra_args=None)

Run latexmk for a one-shot compilation.

<a id="ktisma.infra.latexmk.LatexmkRunner.start_watch"></a>

#### start_watch(source_file, build_dir, engine, synctex, extra_args=None)

Launch latexmk in continuous watch mode (latexmk -pvc).

<a id="ktisma.infra.latexmk.LatexmkWatchSession"></a>

### *class* ktisma.infra.latexmk.LatexmkWatchSession(source_file, build_dir, args)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Polling watch session over a live latexmk -pvc subprocess.

<a id="ktisma.infra.latexmk.LatexmkWatchSession.poll"></a>

#### poll(timeout_seconds=0.5)

<a id="ktisma.infra.latexmk.LatexmkWatchSession.terminate"></a>

#### terminate()

<a id="module-ktisma.infra.locks"></a>

<a id="file-locks"></a>

## File locks

<a id="ktisma.infra.locks.FileLockManager"></a>

### *class* ktisma.infra.locks.FileLockManager

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Concrete LockManager: file-based exclusive build locks.

Lock semantics per roadmap:
- Lock file path: <build-dir>/.ktisma.lock
- Acquisition uses exclusive creation.
- Lock contents: hostname, PID, source path, mode, creation timestamp.
- Stale recovery: same host + PID no longer exists.
- If unrecoverable, raise LockContention with dedicated exit code.

<a id="ktisma.infra.locks.FileLockManager.acquire"></a>

#### acquire(lock_file, source_path, mode)

Acquire an exclusive build lock.

<a id="ktisma.infra.locks.FileLockManager.release"></a>

#### release(lock_file)

Release a previously acquired build lock.

<a id="module-ktisma.infra.materialize"></a>

<a id="materialization"></a>

## Materialization

<a id="ktisma.infra.materialize.FileMaterializer"></a>

### *class* ktisma.infra.materialize.FileMaterializer

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Concrete Materializer: copies build artifacts to final destinations.

Per roadmap: creates parent directories as needed.
Uses copy2 to preserve metadata. A successful PDF must never be lost.

<a id="ktisma.infra.materialize.FileMaterializer.materialize"></a>

#### materialize(source, destination)

Copy a build artifact to its final destination.

<a id="module-ktisma.infra.prerequisites"></a>

<a id="prerequisites"></a>

## Prerequisites

<a id="ktisma.infra.prerequisites.SystemPrerequisiteProbe"></a>

### *class* ktisma.infra.prerequisites.SystemPrerequisiteProbe

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Concrete PrerequisiteProbe: checks system prerequisites.

<a id="ktisma.infra.prerequisites.SystemPrerequisiteProbe.check_latexmk"></a>

#### check_latexmk()

Check if latexmk is available on PATH.

<a id="ktisma.infra.prerequisites.SystemPrerequisiteProbe.check_engine"></a>

#### check_engine(engine)

Check if a specific LaTeX engine is available.

<a id="ktisma.infra.prerequisites.SystemPrerequisiteProbe.check_python_version"></a>

#### check_python_version()

Check if the Python version meets minimum requirements.

<a id="ktisma.infra.prerequisites.SystemPrerequisiteProbe.check_toml_support"></a>

#### check_toml_support()

Check if TOML parsing is available.

<a id="module-ktisma.infra.source_reader"></a>

<a id="source-reader"></a>

## Source reader

<a id="ktisma.infra.source_reader.FileSourceReader"></a>

### *class* ktisma.infra.source_reader.FileSourceReader

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Concrete SourceReader: reads .tex files from disk and extracts magic comments.

<a id="ktisma.infra.source_reader.FileSourceReader.read_source"></a>

#### read_source(source_file)

Read a source file and extract preamble text and magic comments.

Per roadmap, infrastructure extracts the preamble (up to begin{document})
so domain code receives only the preamble text.

<a id="module-ktisma.infra.workspace"></a>

<a id="workspace"></a>

## Workspace

<a id="ktisma.infra.workspace.resolve_workspace_root"></a>

### ktisma.infra.workspace.resolve_workspace_root(cli_workspace_root=None, adapter_workspace_root=None, source_dir=None)

Resolve the workspace root per roadmap precedence.

Resolution order:
1. –workspace-root (CLI flag)
2. KTISMA_WORKSPACE_ROOT environment variable
3. Adapter-provided workspace root
4. Nearest ancestor of source_dir containing .ktisma.toml
5. Current working directory

<a id="ktisma.infra.workspace.FileWorkspaceOps"></a>

### *class* ktisma.infra.workspace.FileWorkspaceOps

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Filesystem implementation for build-dir creation and cleanup helpers.

<a id="ktisma.infra.workspace.FileWorkspaceOps.ensure_directory"></a>

#### ensure_directory(path)

<a id="ktisma.infra.workspace.FileWorkspaceOps.path_exists"></a>

#### path_exists(path)

<a id="ktisma.infra.workspace.FileWorkspaceOps.is_directory"></a>

#### is_directory(path)

<a id="ktisma.infra.workspace.FileWorkspaceOps.list_directory"></a>

#### list_directory(path)

<a id="ktisma.infra.workspace.FileWorkspaceOps.read_text"></a>

#### read_text(path)

<a id="ktisma.infra.workspace.FileWorkspaceOps.write_text"></a>

#### write_text(path, content)

<a id="ktisma.infra.workspace.FileWorkspaceOps.remove_tree"></a>

#### remove_tree(path)

<a id="ktisma.infra.workspace.FileWorkspaceOps.glob_files"></a>

#### glob_files(path, pattern)
