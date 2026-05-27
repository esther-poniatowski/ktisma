<a id="domain"></a>

# Domain

Pure domain model: build context, configuration, engine selection, routing,
and error vocabulary. No I/O.

<a id="module-ktisma.domain.build_dir"></a>

<a id="build-directories"></a>

## Build directories

<a id="ktisma.domain.build_dir.BuildDirPlan"></a>

### *class* ktisma.domain.build_dir.BuildDirPlan(build_dir: 'Path', expected_pdf: 'Path', lock_file: 'Path', metadata_file: 'Path', source_stem: 'str', variant: 'Optional[VariantSpec]' = None)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

<a id="ktisma.domain.build_dir.BuildDirPlan.build_dir"></a>

#### build_dir *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

<a id="ktisma.domain.build_dir.BuildDirPlan.expected_pdf"></a>

#### expected_pdf *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

<a id="ktisma.domain.build_dir.BuildDirPlan.lock_file"></a>

#### lock_file *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

<a id="ktisma.domain.build_dir.BuildDirPlan.metadata_file"></a>

#### metadata_file *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

<a id="ktisma.domain.build_dir.BuildDirPlan.source_stem"></a>

#### source_stem *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

<a id="ktisma.domain.build_dir.BuildDirPlan.variant"></a>

#### variant *: [VariantSpec](#ktisma.domain.context.VariantSpec) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*

<a id="ktisma.domain.build_dir.BuildDirPlan.to_dict"></a>

#### to_dict()

<a id="ktisma.domain.build_dir.plan_build_dir"></a>

### ktisma.domain.build_dir.plan_build_dir(ctx, config, variant=None)

Plan the build directory and expected artifact paths.

Default pattern per roadmap:
- <source-dir>/.ktisma_build/<stem>/
- <source-dir>/.ktisma_build/<stem>-<variant>/ for variants

<a id="module-ktisma.domain.config"></a>

<a id="configuration"></a>

## Configuration

<a id="ktisma.domain.config.CleanupPolicy"></a>

### *class* ktisma.domain.config.CleanupPolicy(\*values)

Bases: [`Enum`](https://docs.python.org/3/library/enum.html#enum.Enum)

<a id="ktisma.domain.config.CleanupPolicy.NEVER"></a>

#### NEVER *= 'never'*

<a id="ktisma.domain.config.CleanupPolicy.ON_SUCCESS"></a>

#### ON_SUCCESS *= 'on_success'*

<a id="ktisma.domain.config.CleanupPolicy.ON_OUTPUT_SUCCESS"></a>

#### ON_OUTPUT_SUCCESS *= 'on_output_success'*

<a id="ktisma.domain.config.CleanupPolicy.ALWAYS"></a>

#### ALWAYS *= 'always'*

<a id="ktisma.domain.config.ConfigLayer"></a>

### *class* ktisma.domain.config.ConfigLayer(data: 'dict[str, Any]', source: 'Optional[Path]', label: 'str', base_dir: 'Optional[Path]' = None)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

<a id="ktisma.domain.config.ConfigLayer.data"></a>

#### data *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]*

<a id="ktisma.domain.config.ConfigLayer.source"></a>

#### source *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [None](https://docs.python.org/3/library/constants.html#None)*

<a id="ktisma.domain.config.ConfigLayer.label"></a>

#### label *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

<a id="ktisma.domain.config.ConfigLayer.base_dir"></a>

#### base_dir *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*

<a id="ktisma.domain.config.BuildConfig"></a>

### *class* ktisma.domain.config.BuildConfig(out_dir_name: 'str', cleanup: 'CleanupPolicy', synctex: 'bool')

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

<a id="ktisma.domain.config.BuildConfig.out_dir_name"></a>

#### out_dir_name *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

<a id="ktisma.domain.config.BuildConfig.cleanup"></a>

#### cleanup *: [CleanupPolicy](#ktisma.domain.config.CleanupPolicy)*

<a id="ktisma.domain.config.BuildConfig.synctex"></a>

#### synctex *: [bool](https://docs.python.org/3/library/functions.html#bool)*

<a id="ktisma.domain.config.EngineConfig"></a>

### *class* ktisma.domain.config.EngineConfig(default: 'str', modern_default: 'str', strict_detection: 'bool')

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

<a id="ktisma.domain.config.EngineConfig.default"></a>

#### default *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

<a id="ktisma.domain.config.EngineConfig.modern_default"></a>

#### modern_default *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

<a id="ktisma.domain.config.EngineConfig.strict_detection"></a>

#### strict_detection *: [bool](https://docs.python.org/3/library/functions.html#bool)*

<a id="ktisma.domain.config.RoutingConfig"></a>

### *class* ktisma.domain.config.RoutingConfig(source_suffix: 'str', output_suffix: 'str', preserve_relative: 'bool', collapse_entrypoint_names: 'bool', entrypoint_names: 'list[str]', default_filename_suffix: 'str', variant_filename_suffix: 'str')

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

<a id="ktisma.domain.config.RoutingConfig.source_suffix"></a>

#### source_suffix *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

<a id="ktisma.domain.config.RoutingConfig.output_suffix"></a>

#### output_suffix *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

<a id="ktisma.domain.config.RoutingConfig.preserve_relative"></a>

#### preserve_relative *: [bool](https://docs.python.org/3/library/functions.html#bool)*

<a id="ktisma.domain.config.RoutingConfig.collapse_entrypoint_names"></a>

#### collapse_entrypoint_names *: [bool](https://docs.python.org/3/library/functions.html#bool)*

<a id="ktisma.domain.config.RoutingConfig.entrypoint_names"></a>

#### entrypoint_names *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]*

<a id="ktisma.domain.config.RoutingConfig.default_filename_suffix"></a>

#### default_filename_suffix *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

<a id="ktisma.domain.config.RoutingConfig.variant_filename_suffix"></a>

#### variant_filename_suffix *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

<a id="ktisma.domain.config.VariantConfig"></a>

### *class* ktisma.domain.config.VariantConfig(payload: 'str' = '', engine: 'Optional[str]' = None, output: 'Optional[str]' = None, filename_suffix: 'Optional[str]' = None)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

<a id="ktisma.domain.config.VariantConfig.payload"></a>

#### payload *: [str](https://docs.python.org/3/library/stdtypes.html#str)* *= ''*

<a id="ktisma.domain.config.VariantConfig.engine"></a>

#### engine *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*

<a id="ktisma.domain.config.VariantConfig.output"></a>

#### output *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*

<a id="ktisma.domain.config.VariantConfig.filename_suffix"></a>

#### filename_suffix *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*

<a id="ktisma.domain.config.ResolvedConfig"></a>

### *class* ktisma.domain.config.ResolvedConfig(schema_version: 'int', build: 'BuildConfig', engines: 'EngineConfig', routing: 'RoutingConfig', routes: 'dict[str, str]' = <factory>, variants: 'dict[str, VariantConfig]' = <factory>, provenance: 'list[str]' = <factory>)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

<a id="ktisma.domain.config.ResolvedConfig.schema_version"></a>

#### schema_version *: [int](https://docs.python.org/3/library/functions.html#int)*

<a id="ktisma.domain.config.ResolvedConfig.build"></a>

#### build *: [BuildConfig](#ktisma.domain.config.BuildConfig)*

<a id="ktisma.domain.config.ResolvedConfig.engines"></a>

#### engines *: [EngineConfig](#ktisma.domain.config.EngineConfig)*

<a id="ktisma.domain.config.ResolvedConfig.routing"></a>

#### routing *: [RoutingConfig](#ktisma.domain.config.RoutingConfig)*

<a id="ktisma.domain.config.ResolvedConfig.routes"></a>

#### routes *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str)]*

<a id="ktisma.domain.config.ResolvedConfig.variants"></a>

#### variants *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [VariantConfig](#ktisma.domain.config.VariantConfig)]*

<a id="ktisma.domain.config.ResolvedConfig.provenance"></a>

#### provenance *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]*

<a id="ktisma.domain.config.validate_config"></a>

### ktisma.domain.config.validate_config(data, schema_version=1)

<a id="ktisma.domain.config.merge_config_layers"></a>

### ktisma.domain.config.merge_config_layers(layers)

Merge config layers from lowest to highest precedence.

Returns the merged dict and a list of provenance labels.
Layers should be ordered from lowest to highest precedence.

<a id="ktisma.domain.config.resolve_config"></a>

### ktisma.domain.config.resolve_config(merged, provenance)

Construct a ResolvedConfig from a merged config dict.

Expects *merged* to have been produced by a pipeline that starts with
`BUILTIN_DEFAULTS`, so every key is guaranteed present.

<a id="ktisma.domain.config.default_config"></a>

### ktisma.domain.config.default_config()

Return a ResolvedConfig with all built-in defaults.

<a id="module-ktisma.domain.context"></a>

<a id="build-context"></a>

## Build context

<a id="ktisma.domain.context.SourceContext"></a>

### *class* ktisma.domain.context.SourceContext(source_file: 'Path', source_dir: 'Path', workspace_root: 'Path')

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

<a id="ktisma.domain.context.SourceContext.source_file"></a>

#### source_file *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

<a id="ktisma.domain.context.SourceContext.source_dir"></a>

#### source_dir *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

<a id="ktisma.domain.context.SourceContext.workspace_root"></a>

#### workspace_root *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

<a id="ktisma.domain.context.ToolkitInfo"></a>

### *class* ktisma.domain.context.ToolkitInfo(toolkit_root: 'Path', installation_mode: 'str')

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

<a id="ktisma.domain.context.ToolkitInfo.toolkit_root"></a>

#### toolkit_root *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

<a id="ktisma.domain.context.ToolkitInfo.installation_mode"></a>

#### installation_mode *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

<a id="ktisma.domain.context.BuildRequest"></a>

### *class* ktisma.domain.context.BuildRequest(watch: 'bool' = False, dry_run: 'bool' = False, engine_override: 'Optional[str]' = None, output_path_override: 'Optional[Path]' = None, output_dir_override: 'Optional[Path]' = None, variant: 'Optional[str]' = None, variant_spec: "Optional['VariantSpec']" = None, variant_payload: 'Optional[str]' = None, include_default: 'bool' = False, json_output: 'bool' = False, cleanup_override: 'Optional[str]' = None)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

<a id="ktisma.domain.context.BuildRequest.watch"></a>

#### watch *: [bool](https://docs.python.org/3/library/functions.html#bool)* *= False*

<a id="ktisma.domain.context.BuildRequest.dry_run"></a>

#### dry_run *: [bool](https://docs.python.org/3/library/functions.html#bool)* *= False*

<a id="ktisma.domain.context.BuildRequest.engine_override"></a>

#### engine_override *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*

<a id="ktisma.domain.context.BuildRequest.output_path_override"></a>

#### output_path_override *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*

<a id="ktisma.domain.context.BuildRequest.output_dir_override"></a>

#### output_dir_override *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*

<a id="ktisma.domain.context.BuildRequest.variant"></a>

#### variant *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*

<a id="ktisma.domain.context.BuildRequest.variant_spec"></a>

#### variant_spec *: [VariantSpec](#ktisma.domain.context.VariantSpec) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*

<a id="ktisma.domain.context.BuildRequest.variant_payload"></a>

#### variant_payload *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*

<a id="ktisma.domain.context.BuildRequest.include_default"></a>

#### include_default *: [bool](https://docs.python.org/3/library/functions.html#bool)* *= False*

<a id="ktisma.domain.context.BuildRequest.json_output"></a>

#### json_output *: [bool](https://docs.python.org/3/library/functions.html#bool)* *= False*

<a id="ktisma.domain.context.BuildRequest.cleanup_override"></a>

#### cleanup_override *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*

<a id="ktisma.domain.context.SourceInputs"></a>

### *class* ktisma.domain.context.SourceInputs(preamble: 'str', magic_comments: 'dict[str, str]' = <factory>)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

<a id="ktisma.domain.context.SourceInputs.preamble"></a>

#### preamble *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

<a id="ktisma.domain.context.SourceInputs.magic_comments"></a>

#### magic_comments *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str)]*

<a id="ktisma.domain.context.VariantSpec"></a>

### *class* ktisma.domain.context.VariantSpec(name: 'str', payload: 'str', engine_override: 'Optional[str]' = None, output_override: 'Optional[str]' = None, filename_suffix: 'Optional[str]' = None)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

<a id="ktisma.domain.context.VariantSpec.name"></a>

#### name *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

<a id="ktisma.domain.context.VariantSpec.payload"></a>

#### payload *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

<a id="ktisma.domain.context.VariantSpec.engine_override"></a>

#### engine_override *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*

<a id="ktisma.domain.context.VariantSpec.output_override"></a>

#### output_override *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*

<a id="ktisma.domain.context.VariantSpec.filename_suffix"></a>

#### filename_suffix *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*

<a id="ktisma.domain.context.VariantSpec.VALID_NAME_PATTERN"></a>

#### VALID_NAME_PATTERN *: [ClassVar](https://docs.python.org/3/library/typing.html#typing.ClassVar)[[str](https://docs.python.org/3/library/stdtypes.html#str)]* *= '^[a-zA-Z][a-zA-Z0-9_-]\*$'*

<a id="ktisma.domain.context.is_valid_variant_name"></a>

### ktisma.domain.context.is_valid_variant_name(name)

Return whether a variant name is safe for filenames and CLI use.

<a id="module-ktisma.domain.diagnostics"></a>

<a id="diagnostics"></a>

## Diagnostics

<a id="ktisma.domain.diagnostics.DiagnosticLevel"></a>

### *class* ktisma.domain.diagnostics.DiagnosticLevel(\*values)

Bases: [`Enum`](https://docs.python.org/3/library/enum.html#enum.Enum)

<a id="ktisma.domain.diagnostics.DiagnosticLevel.INFO"></a>

#### INFO *= 'info'*

<a id="ktisma.domain.diagnostics.DiagnosticLevel.WARNING"></a>

#### WARNING *= 'warning'*

<a id="ktisma.domain.diagnostics.DiagnosticLevel.ERROR"></a>

#### ERROR *= 'error'*

<a id="ktisma.domain.diagnostics.Diagnostic"></a>

### *class* ktisma.domain.diagnostics.Diagnostic(level: 'DiagnosticLevel', component: 'str', code: 'str', message: 'str', evidence: 'Optional[list[str]]' = None)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

<a id="ktisma.domain.diagnostics.Diagnostic.level"></a>

#### level *: [DiagnosticLevel](#ktisma.domain.diagnostics.DiagnosticLevel)*

<a id="ktisma.domain.diagnostics.Diagnostic.component"></a>

#### component *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

<a id="ktisma.domain.diagnostics.Diagnostic.code"></a>

#### code *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

<a id="ktisma.domain.diagnostics.Diagnostic.message"></a>

#### message *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

<a id="ktisma.domain.diagnostics.Diagnostic.evidence"></a>

#### evidence *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)] | [None](https://docs.python.org/3/library/constants.html#None)* *= None*

<a id="ktisma.domain.diagnostics.Diagnostic.to_dict"></a>

#### to_dict()

<a id="module-ktisma.domain.engine"></a>

<a id="engine-selection"></a>

## Engine selection

<a id="ktisma.domain.engine.EngineDecision"></a>

### *class* ktisma.domain.engine.EngineDecision(engine: 'str', evidence: 'list[str]' = <factory>, ambiguous: 'bool' = False, diagnostics: 'list[Diagnostic]' = <factory>)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

<a id="ktisma.domain.engine.EngineDecision.engine"></a>

#### engine *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

<a id="ktisma.domain.engine.EngineDecision.evidence"></a>

#### evidence *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[str](https://docs.python.org/3/library/stdtypes.html#str)]*

<a id="ktisma.domain.engine.EngineDecision.ambiguous"></a>

#### ambiguous *: [bool](https://docs.python.org/3/library/functions.html#bool)* *= False*

<a id="ktisma.domain.engine.EngineDecision.diagnostics"></a>

#### diagnostics *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Diagnostic](#ktisma.domain.diagnostics.Diagnostic)]*

<a id="ktisma.domain.engine.EngineDecision.to_dict"></a>

#### to_dict()

<a id="ktisma.domain.engine.EngineRule"></a>

### *class* ktisma.domain.engine.EngineRule(engine: 'str', markers: 'list[tuple[str, str]]')

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

<a id="ktisma.domain.engine.EngineRule.engine"></a>

#### engine *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

<a id="ktisma.domain.engine.EngineRule.markers"></a>

#### markers *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str)]]*

<a id="ktisma.domain.engine.detect_engine"></a>

### ktisma.domain.engine.detect_engine(source_inputs, config, custom_rules=None)

Detect the appropriate LaTeX engine from source inputs and config.

Detection steps per roadmap:
1. Honor magic comment if present.
2. Scan preamble for definitive markers.
3. Handle ambiguous markers.
4. Fall back to config default.

<a id="module-ktisma.domain.errors"></a>

<a id="errors"></a>

## Errors

<a id="ktisma.domain.errors.KtismaError"></a>

### *exception* ktisma.domain.errors.KtismaError(exit_code, message, diagnostics=None)

Bases: [`Exception`](https://docs.python.org/3/library/exceptions.html#Exception)

Base exception for ktisma failures that map to a public exit code.

<a id="ktisma.domain.errors.ConfigError"></a>

### *exception* ktisma.domain.errors.ConfigError(message, diagnostics=None)

Bases: [`KtismaError`](#ktisma.domain.errors.KtismaError)

<a id="ktisma.domain.errors.ConfigLoadError"></a>

### *exception* ktisma.domain.errors.ConfigLoadError(path, message)

Bases: [`ConfigError`](#ktisma.domain.errors.ConfigError)

<a id="ktisma.domain.errors.PrerequisiteError"></a>

### *exception* ktisma.domain.errors.PrerequisiteError(message, diagnostics=None)

Bases: [`KtismaError`](#ktisma.domain.errors.KtismaError)

<a id="ktisma.domain.errors.LockContention"></a>

### *exception* ktisma.domain.errors.LockContention(message, diagnostics=None)

Bases: [`KtismaError`](#ktisma.domain.errors.KtismaError)

<a id="module-ktisma.domain.exit_codes"></a>

<a id="exit-codes"></a>

## Exit codes

<a id="ktisma.domain.exit_codes.ExitCode"></a>

### *class* ktisma.domain.exit_codes.ExitCode(\*values)

Bases: [`IntEnum`](https://docs.python.org/3/library/enum.html#enum.IntEnum)

<a id="ktisma.domain.exit_codes.ExitCode.SUCCESS"></a>

#### SUCCESS *= 0*

<a id="ktisma.domain.exit_codes.ExitCode.COMPILATION_FAILURE"></a>

#### COMPILATION_FAILURE *= 1*

<a id="ktisma.domain.exit_codes.ExitCode.CONFIG_ERROR"></a>

#### CONFIG_ERROR *= 2*

<a id="ktisma.domain.exit_codes.ExitCode.PREREQUISITE_FAILURE"></a>

#### PREREQUISITE_FAILURE *= 3*

<a id="ktisma.domain.exit_codes.ExitCode.LOCK_CONTENTION"></a>

#### LOCK_CONTENTION *= 4*

<a id="ktisma.domain.exit_codes.ExitCode.INTERNAL_ERROR"></a>

#### INTERNAL_ERROR *= 5*

<a id="module-ktisma.domain.routing"></a>

<a id="routing"></a>

## Routing

<a id="ktisma.domain.routing.RouteDecision"></a>

### *class* ktisma.domain.routing.RouteDecision(destination: 'Path', matched_rule: 'Optional[str]' = None, fallback: 'bool' = False, diagnostics: 'list[Diagnostic]' = <factory>)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

<a id="ktisma.domain.routing.RouteDecision.destination"></a>

#### destination *: [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path)*

<a id="ktisma.domain.routing.RouteDecision.matched_rule"></a>

#### matched_rule *: [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None)* *= None*

<a id="ktisma.domain.routing.RouteDecision.fallback"></a>

#### fallback *: [bool](https://docs.python.org/3/library/functions.html#bool)* *= False*

<a id="ktisma.domain.routing.RouteDecision.diagnostics"></a>

#### diagnostics *: [list](https://docs.python.org/3/library/stdtypes.html#list)[[Diagnostic](#ktisma.domain.diagnostics.Diagnostic)]*

<a id="ktisma.domain.routing.RouteDecision.to_dict"></a>

#### to_dict(source)

<a id="ktisma.domain.routing.resolve_route"></a>

### ktisma.domain.routing.resolve_route(ctx, source_inputs, config, output_path_override=None, output_dir_override=None, extra_resolvers=None)

Resolve the output destination for a compiled PDF.

Precedence per roadmap:
1. CLI output-file override
2. CLI output-directory override
3. Magic-comment output override
4. Custom route resolvers
5. Explicit config route rules
6. Suffix convention
7. Safe fallback beside the source file
