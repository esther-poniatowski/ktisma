"""Tests for ktisma.domain.config — validation, merge semantics, defaults, resolution."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from ktisma.domain.config import (
    BUILTIN_DEFAULTS,
    VALID_ENGINES,
    BuildConfig,
    CleanupPolicy,
    ConfigLayer,
    EngineConfig,
    ResolvedConfig,
    RoutingConfig,
    TexConfig,
    TexDependency,
    VariantConfig,
    default_config,
    merge_config_layers,
    resolve_config,
    validate_config,
)
from ktisma.domain.diagnostics import DiagnosticLevel

# ---------------------------------------------------------------------------
# CleanupPolicy
# ---------------------------------------------------------------------------


class TestCleanupPolicy:
    @pytest.mark.parametrize(
        "value, member",
        [
            ("never", CleanupPolicy.NEVER),
            ("on_success", CleanupPolicy.ON_SUCCESS),
            ("on_output_success", CleanupPolicy.ON_OUTPUT_SUCCESS),
            ("always", CleanupPolicy.ALWAYS),
        ],
    )
    def test_from_value(self, value: str, member: CleanupPolicy) -> None:
        assert CleanupPolicy(value) is member

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            CleanupPolicy("aggressive")


# ---------------------------------------------------------------------------
# Sub-config dataclass defaults
# ---------------------------------------------------------------------------


class TestSubConfigDefaults:
    """Defaults are defined once in BUILTIN_DEFAULTS and verified via default_config()."""

    def test_build_config_defaults(self) -> None:
        cfg = default_config()
        assert cfg.build.out_dir_name == ".ktisma_build"
        assert cfg.build.cleanup is CleanupPolicy.ON_OUTPUT_SUCCESS
        assert cfg.build.synctex is True

    def test_engine_config_defaults(self) -> None:
        cfg = default_config()
        assert cfg.engines.default == "pdflatex"
        assert cfg.engines.modern_default == "lualatex"
        assert cfg.engines.strict_detection is False

    def test_routing_config_defaults(self) -> None:
        cfg = default_config()
        assert cfg.routing.source_suffix == "-tex"
        assert cfg.routing.output_suffix == "-pdfs"
        assert cfg.routing.preserve_relative is True
        assert cfg.routing.collapse_entrypoint_names is False
        assert cfg.routing.entrypoint_names == ["main", "index"]


# ---------------------------------------------------------------------------
# ResolvedConfig defaults
# ---------------------------------------------------------------------------


class TestResolvedConfigDefaults:
    def test_default_config_function(self) -> None:
        cfg = default_config()
        assert cfg.schema_version == 1
        assert cfg.build.out_dir_name == ".ktisma_build"
        assert cfg.build.cleanup is CleanupPolicy.ON_OUTPUT_SUCCESS
        assert cfg.build.synctex is True
        assert cfg.engines.default == "pdflatex"
        assert cfg.engines.modern_default == "lualatex"
        assert cfg.engines.strict_detection is False
        assert cfg.routing.source_suffix == "-tex"
        assert cfg.routing.output_suffix == "-pdfs"
        assert cfg.routing.preserve_relative is True
        assert cfg.routing.collapse_entrypoint_names is False
        assert cfg.routing.entrypoint_names == ["main", "index"]
        assert cfg.routes == {}
        assert cfg.variants == {}
        assert cfg.provenance == ["built-in defaults"]
        assert cfg.tex == TexConfig()

    def test_resolved_config_requires_explicit_fields(self) -> None:
        """ResolvedConfig has no field defaults for schema_version, build, engines,
        routing — they must be supplied explicitly (single source of truth is
        BUILTIN_DEFAULTS)."""
        cfg = default_config()
        assert isinstance(cfg.build, BuildConfig)
        assert isinstance(cfg.engines, EngineConfig)
        assert isinstance(cfg.routing, RoutingConfig)
        assert cfg.routes == {}
        assert cfg.variants == {}
        assert cfg.tex.dependencies == ()

    def test_frozen(self) -> None:
        cfg = default_config()
        with pytest.raises(AttributeError):
            cfg.schema_version = 2  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ConfigLayer
# ---------------------------------------------------------------------------


class TestConfigLayer:
    def test_with_path_source(self) -> None:
        layer = ConfigLayer(
            data={"build": {"synctex": False}},
            source=Path("/some/ktisma.toml"),
            label="workspace config",
        )
        assert layer.source == Path("/some/ktisma.toml")
        assert layer.label == "workspace config"

    def test_with_none_source(self) -> None:
        layer = ConfigLayer(data={}, source=None, label="built-in defaults")
        assert layer.source is None


# ---------------------------------------------------------------------------
# Merge semantics
# ---------------------------------------------------------------------------


class TestMergeConfigLayers:
    def test_empty_layers(self) -> None:
        merged, prov = merge_config_layers([])
        assert merged == {}
        assert prov == []

    def test_single_layer(self) -> None:
        layer = ConfigLayer(
            data={"build": {"synctex": False}},
            source=None,
            label="user config",
        )
        merged, prov = merge_config_layers([layer])
        assert merged == {"build": {"synctex": False}}
        assert prov == ["user config"]

    def test_empty_data_layer_skipped(self) -> None:
        layer = ConfigLayer(data={}, source=None, label="empty")
        merged, prov = merge_config_layers([layer])
        assert merged == {}
        assert prov == []  # empty data layers are not added to provenance

    def test_nested_tables_merge(self) -> None:
        """Nested dicts (tables) should be recursively merged, not replaced."""
        base = ConfigLayer(
            data={"build": {"synctex": True, "out_dir_name": ".build"}},
            source=None,
            label="base",
        )
        override = ConfigLayer(
            data={"build": {"synctex": False}},
            source=None,
            label="override",
        )
        merged, prov = merge_config_layers([base, override])
        assert merged["build"]["synctex"] is False
        assert merged["build"]["out_dir_name"] == ".build"  # preserved from base
        assert prov == ["base", "override"]

    def test_scalars_replace(self) -> None:
        """Scalar values should be replaced, not merged."""
        base = ConfigLayer(
            data={"engines": {"default": "pdflatex"}},
            source=None,
            label="base",
        )
        override = ConfigLayer(
            data={"engines": {"default": "lualatex"}},
            source=None,
            label="override",
        )
        merged, _ = merge_config_layers([base, override])
        assert merged["engines"]["default"] == "lualatex"

    def test_arrays_replace(self) -> None:
        """Arrays should be replaced entirely, not concatenated."""
        base = ConfigLayer(
            data={"routing": {"entrypoint_names": ["main", "index"]}},
            source=None,
            label="base",
        )
        override = ConfigLayer(
            data={"routing": {"entrypoint_names": ["document"]}},
            source=None,
            label="override",
        )
        merged, _ = merge_config_layers([base, override])
        assert merged["routing"]["entrypoint_names"] == ["document"]

    def test_routes_merge_by_key(self) -> None:
        """Routes (flat dicts) should merge by exact key."""
        base = ConfigLayer(
            data={"routes": {"src/*.tex": "out/"}},
            source=None,
            label="base",
        )
        override = ConfigLayer(
            data={"routes": {"drafts/*.tex": "draft-out/"}},
            source=None,
            label="override",
        )
        merged, _ = merge_config_layers([base, override])
        assert merged["routes"] == {
            "src/*.tex": "out/",
            "drafts/*.tex": "draft-out/",
        }

    def test_routes_override_same_key(self) -> None:
        base = ConfigLayer(
            data={"routes": {"src/*.tex": "old/"}},
            source=None,
            label="base",
        )
        override = ConfigLayer(
            data={"routes": {"src/*.tex": "new/"}},
            source=None,
            label="override",
        )
        merged, _ = merge_config_layers([base, override])
        assert merged["routes"]["src/*.tex"] == "new/"

    def test_three_layer_merge(self) -> None:
        defaults = ConfigLayer(
            data=copy.deepcopy(BUILTIN_DEFAULTS),
            source=None,
            label="built-in defaults",
        )
        workspace = ConfigLayer(
            data={"engines": {"default": "xelatex"}, "routes": {"a.tex": "out/"}},
            source=Path("/ws/ktisma.toml"),
            label="workspace",
            base_dir=Path("/ws"),
        )
        cli = ConfigLayer(
            data={"build": {"synctex": False}},
            source=None,
            label="CLI",
        )
        merged, prov = merge_config_layers([defaults, workspace, cli])
        assert merged["engines"]["default"] == "xelatex"
        assert merged["engines"]["modern_default"] == "lualatex"  # from defaults
        assert merged["build"]["synctex"] is False  # from CLI
        assert merged["build"]["out_dir_name"] == ".ktisma_build"  # from defaults
        assert merged["routes"] == {"a.tex": "/ws/out/"}
        assert prov == ["built-in defaults", "workspace", "CLI"]

    def test_non_dict_overwrites_dict(self) -> None:
        """If override provides a non-dict where base has a dict, replace entirely."""
        base = ConfigLayer(
            data={"build": {"synctex": True}},
            source=None,
            label="base",
        )
        override = ConfigLayer(
            data={"build": "invalid_scalar"},
            source=None,
            label="override",
        )
        merged, _ = merge_config_layers([base, override])
        assert merged["build"] == "invalid_scalar"


# ---------------------------------------------------------------------------
# resolve_config
# ---------------------------------------------------------------------------


class TestResolveConfig:
    def test_from_builtin_defaults(self) -> None:
        cfg = resolve_config(copy.deepcopy(BUILTIN_DEFAULTS), ["built-in defaults"])
        assert cfg == default_config()

    def test_custom_values(self) -> None:
        data: dict[str, Any] = {
            "schema_version": 1,
            "build": {
                "out_dir_name": "build",
                "cleanup": "always",
                "synctex": False,
            },
            "engines": {
                "default": "xelatex",
                "modern_default": "xelatex",
                "strict_detection": True,
            },
            "routing": {
                "source_suffix": "-src",
                "output_suffix": "-out",
                "preserve_relative": False,
                "collapse_entrypoint_names": True,
                "entrypoint_names": ["document"],
                "default_filename_suffix": "",
                "variant_filename_suffix": "_{variant}",
            },
            "routes": {"ch1/*.tex": "output/ch1/"},
            "variants": {"print": "\\printmodetrue"},
        }
        cfg = resolve_config(data, ["custom"])
        assert cfg.schema_version == 1
        assert cfg.build.out_dir_name == "build"
        assert cfg.build.cleanup is CleanupPolicy.ALWAYS
        assert cfg.build.synctex is False
        assert cfg.engines.default == "xelatex"
        assert cfg.engines.modern_default == "xelatex"
        assert cfg.engines.strict_detection is True
        assert cfg.routing.source_suffix == "-src"
        assert cfg.routing.output_suffix == "-out"
        assert cfg.routing.preserve_relative is False
        assert cfg.routing.collapse_entrypoint_names is True
        assert cfg.routing.entrypoint_names == ["document"]
        assert cfg.routes == {"ch1/*.tex": "output/ch1/"}
        assert cfg.variants == {"print": VariantConfig(payload="\\printmodetrue")}
        assert cfg.provenance == ["custom"]

    def test_missing_sections_use_defaults(self) -> None:
        """When no user config is provided, BUILTIN_DEFAULTS supplies all keys."""
        merged, prov = merge_config_layers(
            [
                ConfigLayer(
                    data=copy.deepcopy(BUILTIN_DEFAULTS),
                    source=None,
                    label="built-in defaults",
                ),
            ]
        )
        cfg = resolve_config(merged, prov)
        assert cfg.build.out_dir_name == ".ktisma_build"
        assert cfg.engines.default == "pdflatex"
        assert cfg.routing.source_suffix == "-tex"

    def test_partial_section_fills_defaults(self) -> None:
        """A partial user config is merged on top of BUILTIN_DEFAULTS."""
        merged, prov = merge_config_layers(
            [
                ConfigLayer(
                    data=copy.deepcopy(BUILTIN_DEFAULTS),
                    source=None,
                    label="built-in defaults",
                ),
                ConfigLayer(data={"build": {"synctex": False}}, source=None, label="partial"),
            ]
        )
        cfg = resolve_config(merged, prov)
        assert cfg.build.synctex is False
        assert cfg.build.out_dir_name == ".ktisma_build"  # from defaults
        assert cfg.build.cleanup is CleanupPolicy.ON_OUTPUT_SUCCESS  # from defaults


# ---------------------------------------------------------------------------
# Schema validation — valid configs
# ---------------------------------------------------------------------------


class TestValidateConfigValid:
    def test_empty_config(self) -> None:
        assert validate_config({}) == []

    def test_full_valid_config(self) -> None:
        data = copy.deepcopy(BUILTIN_DEFAULTS)
        assert validate_config(data) == []

    def test_valid_with_routes_and_variants(self) -> None:
        data: dict[str, Any] = {
            "routes": {"src/*.tex": "out/"},
            "variants": {"print": "\\printmodetrue"},
        }
        assert validate_config(data) == []


# ---------------------------------------------------------------------------
# Schema validation — unknown keys
# ---------------------------------------------------------------------------


class TestValidateConfigUnknownKeys:
    def test_unknown_top_level_key(self) -> None:
        diags = validate_config({"unknown_key": True})
        assert len(diags) == 1
        assert diags[0].code == "unknown-key"
        assert "'unknown_key'" in diags[0].message

    def test_unknown_build_key(self) -> None:
        diags = validate_config({"build": {"flavor": "spicy"}})
        assert len(diags) == 1
        assert diags[0].code == "unknown-key"
        assert "'build.flavor'" in diags[0].message

    def test_unknown_engines_key(self) -> None:
        diags = validate_config({"engines": {"turbo": True}})
        assert len(diags) == 1
        assert diags[0].code == "unknown-key"
        assert "'engines.turbo'" in diags[0].message

    def test_unknown_routing_key(self) -> None:
        diags = validate_config({"routing": {"fast_mode": True}})
        assert len(diags) == 1
        assert diags[0].code == "unknown-key"
        assert "'routing.fast_mode'" in diags[0].message

    def test_multiple_unknown_keys(self) -> None:
        diags = validate_config({"x": 1, "y": 2})
        codes = [d.code for d in diags]
        assert codes.count("unknown-key") == 2


# ---------------------------------------------------------------------------
# Schema validation — type mismatches
# ---------------------------------------------------------------------------


class TestValidateConfigTypeMismatches:
    def test_build_not_a_table(self) -> None:
        diags = validate_config({"build": "string"})
        assert any(
            d.code == "type-mismatch" and "'build' must be a table" in d.message for d in diags
        )

    def test_engines_not_a_table(self) -> None:
        diags = validate_config({"engines": 42})
        assert any(
            d.code == "type-mismatch" and "'engines' must be a table" in d.message for d in diags
        )

    def test_routing_not_a_table(self) -> None:
        diags = validate_config({"routing": []})
        assert any(
            d.code == "type-mismatch" and "'routing' must be a table" in d.message for d in diags
        )

    def test_routes_not_a_table(self) -> None:
        diags = validate_config({"routes": "flat"})
        assert any(
            d.code == "type-mismatch" and "'routes' must be a table" in d.message for d in diags
        )

    def test_variants_not_a_table(self) -> None:
        diags = validate_config({"variants": [1, 2]})
        assert any(
            d.code == "type-mismatch" and "'variants' must be a table" in d.message for d in diags
        )

    def test_synctex_not_bool(self) -> None:
        diags = validate_config({"build": {"synctex": "yes"}})
        assert any(d.code == "type-mismatch" and "synctex" in d.message for d in diags)

    def test_strict_detection_not_bool(self) -> None:
        diags = validate_config({"engines": {"strict_detection": 1}})
        assert any(d.code == "type-mismatch" and "strict_detection" in d.message for d in diags)

    def test_entrypoint_names_not_array(self) -> None:
        diags = validate_config({"routing": {"entrypoint_names": "main"}})
        assert any(d.code == "type-mismatch" and "entrypoint_names" in d.message for d in diags)


# ---------------------------------------------------------------------------
# Schema validation — invalid engine values
# ---------------------------------------------------------------------------


class TestValidateConfigInvalidEngines:
    @pytest.mark.parametrize("key", ["default", "modern_default"])
    def test_invalid_engine_name(self, key: str) -> None:
        diags = validate_config({"engines": {key: "pdftex"}})
        assert len(diags) == 1
        assert diags[0].code == "invalid-engine"
        assert diags[0].level is DiagnosticLevel.ERROR

    @pytest.mark.parametrize("engine", sorted(VALID_ENGINES))
    def test_valid_engine_names(self, engine: str) -> None:
        diags = validate_config({"engines": {"default": engine}})
        engine_diags = [d for d in diags if d.code == "invalid-engine"]
        assert engine_diags == []


# ---------------------------------------------------------------------------
# Schema validation — invalid cleanup policy
# ---------------------------------------------------------------------------


class TestValidateConfigInvalidCleanup:
    def test_invalid_cleanup_value(self) -> None:
        diags = validate_config({"build": {"cleanup": "aggressive"}})
        assert len(diags) == 1
        assert diags[0].code == "invalid-cleanup-policy"
        assert "aggressive" in diags[0].message

    @pytest.mark.parametrize(
        "policy",
        ["never", "on_success", "on_output_success", "always"],
    )
    def test_valid_cleanup_values(self, policy: str) -> None:
        diags = validate_config({"build": {"cleanup": policy}})
        cleanup_diags = [d for d in diags if d.code == "invalid-cleanup-policy"]
        assert cleanup_diags == []


# ---------------------------------------------------------------------------
# Schema validation — unsupported schema version
# ---------------------------------------------------------------------------


class TestValidateConfigSchemaVersion:
    def test_version_2_ok(self) -> None:
        diags = validate_config({}, schema_version=2)
        assert diags == []

    def test_version_1_ok(self) -> None:
        diags = validate_config({}, schema_version=1)
        assert diags == []

    def test_unsupported_version_returns_early(self) -> None:
        """With unsupported schema, no further validation keys are checked."""
        diags = validate_config({"totally": "bogus"}, schema_version=99)
        assert len(diags) == 1
        assert diags[0].code == "unsupported-schema-version"


# ---------------------------------------------------------------------------
# Schema validation — all diagnostics are ERROR level
# ---------------------------------------------------------------------------


class TestValidateConfigDiagnosticLevels:
    def test_all_validation_errors_are_error_level(self) -> None:
        data: dict[str, Any] = {
            "unknown": True,
            "build": {"synctex": "yes", "cleanup": "bad"},
            "engines": {"default": "pdftex", "strict_detection": 1},
            "routing": {"entrypoint_names": "main", "bogus": True},
            "routes": "flat",
            "variants": [1],
        }
        diags = validate_config(data)
        assert len(diags) > 0
        for d in diags:
            assert d.level is DiagnosticLevel.ERROR


# ---------------------------------------------------------------------------
# BUILTIN_DEFAULTS consistency
# ---------------------------------------------------------------------------


class TestBuiltinDefaults:
    def test_builtin_defaults_validates_clean(self) -> None:
        diags = validate_config(copy.deepcopy(BUILTIN_DEFAULTS))
        assert diags == []

    def test_builtin_defaults_schema_version(self) -> None:
        assert BUILTIN_DEFAULTS["schema_version"] == 1

    def test_builtin_defaults_has_all_sections(self) -> None:
        for section in ("build", "engines", "routing", "routes", "variants"):
            assert section in BUILTIN_DEFAULTS


class TestTexDependencyConfig:
    COMMIT = "0123456789abcdef0123456789abcdef01234567"

    @classmethod
    def dependency(cls, **overrides: Any) -> dict[str, Any]:
        result: dict[str, Any] = {
            "name": "scholia",
            "repository": "https://example.test/scholia.git",
            "commit": cls.COMMIT,
            "builder": "l3build",
            "provides": ["scholia.sty"],
        }
        result.update(overrides)
        return result

    def test_version_2_accepts_dependency_record(self) -> None:
        data = {"schema_version": 2, "tex": {"dependencies": [self.dependency()]}}
        assert validate_config(data, schema_version=2) == []

    def test_version_1_rejects_tex_section(self) -> None:
        diags = validate_config({"tex": {"dependencies": []}}, schema_version=1)
        assert any(d.code == "unknown-key" for d in diags)

    @pytest.mark.parametrize(
        ("data", "code"),
        [
            ({"tex": []}, "type-mismatch"),
            ({"tex": {"dependencies": {}}}, "type-mismatch"),
            ({"tex": {"dependencies": ["scholia"]}}, "type-mismatch"),
            ({"tex": {"unknown": True}}, "unknown-key"),
            (
                {"tex": {"dependencies": [{"unknown": True}]}},
                "unknown-key",
            ),
        ],
    )
    def test_tex_structure_rejects_unknown_keys_and_wrong_types(
        self, data: dict[str, Any], code: str
    ) -> None:
        diags = validate_config(data, schema_version=2)
        assert any(d.code == code for d in diags)

    @pytest.mark.parametrize(
        ("field", "value", "code"),
        [
            ("name", "Scholia", "invalid-tex-dependency-name"),
            ("name", "two words", "invalid-tex-dependency-name"),
            ("repository", "", "invalid-tex-repository"),
            ("repository", "   ", "invalid-tex-repository"),
            ("builder", "Custom Builder", "invalid-tex-builder-name"),
        ],
    )
    def test_dependency_scalar_constraints(self, field: str, value: str, code: str) -> None:
        data = {"tex": {"dependencies": [self.dependency(**{field: value})]}}
        diags = validate_config(data, schema_version=2)
        assert any(d.code == code for d in diags)

    @pytest.mark.parametrize(
        "commit",
        ["main", "v1.0.0", "0123456", "g" * 40, "0" * 39, "0" * 41],
    )
    def test_commit_must_be_full_hexadecimal_hash(self, commit: str) -> None:
        data = {"tex": {"dependencies": [self.dependency(commit=commit)]}}
        diags = validate_config(data, schema_version=2)
        assert any(d.code == "invalid-tex-commit" for d in diags)

    def test_dependency_name_must_be_unique(self) -> None:
        data = {
            "tex": {
                "dependencies": [
                    self.dependency(),
                    self.dependency(repository="https://example.test/other.git"),
                ]
            }
        }
        diags = validate_config(data, schema_version=2)
        assert any(d.code == "duplicate-tex-dependency" for d in diags)

    @pytest.mark.parametrize("missing", ["name", "repository", "commit", "builder", "provides"])
    def test_every_dependency_field_is_required(self, missing: str) -> None:
        dependency = self.dependency()
        dependency.pop(missing)
        diags = validate_config({"tex": {"dependencies": [dependency]}}, schema_version=2)
        assert any(d.code == "missing-key" and missing in d.message for d in diags)

    @pytest.mark.parametrize(
        "provides",
        [
            [],
            [""],
            ["../scholia.sty"],
            ["/scholia.sty"],
            ["scholia.sty", "scholia.sty"],
        ],
    )
    def test_provides_must_name_unique_relative_entries(self, provides: list[str]) -> None:
        data = {"tex": {"dependencies": [self.dependency(provides=provides)]}}
        diags = validate_config(data, schema_version=2)
        assert any(d.code == "invalid-tex-provides" for d in diags)

    def test_resolution_is_immutable_and_order_independent(self) -> None:
        first = self.dependency(name="zeta", provides=["zeta-b.sty", "zeta-a.sty"])
        second = self.dependency(
            name="alpha",
            repository="https://example.test/alpha.git",
            commit="ABCDEF0123456789ABCDEF0123456789ABCDEF01",
            provides=["alpha.sty"],
        )
        merged = _merged_with_defaults(
            {"schema_version": 2, "tex": {"dependencies": [first, second]}}
        )
        cfg = resolve_config(merged, ["test"])
        assert cfg.tex.dependencies == (
            TexDependency(
                name="alpha",
                repository="https://example.test/alpha.git",
                commit="abcdef0123456789abcdef0123456789abcdef01",
                builder="l3build",
                provides=("alpha.sty",),
            ),
            TexDependency(
                name="zeta",
                repository="https://example.test/scholia.git",
                commit=self.COMMIT,
                builder="l3build",
                provides=("zeta-a.sty", "zeta-b.sty"),
            ),
        )
        with pytest.raises(AttributeError):
            cfg.tex.dependencies[0].commit = "0" * 40  # type: ignore[misc]


class TestPlaceholderConfig:
    def test_valid_placeholders_and_artifact_dirs(self) -> None:
        data = {
            "placeholders": {"author": "Doe"},
            "routing": {"artifact_dirs": ["artifacts/*"]},
        }
        assert validate_config(data) == []
        cfg = resolve_config(_merged_with_defaults(data), ["test"])
        assert cfg.placeholders == {"author": "Doe"}
        assert cfg.routing.artifact_dirs == ["artifacts/*"]

    @pytest.mark.parametrize("name", ["stem", "artifact", "variant", "1bad", "with space"])
    def test_invalid_placeholder_names(self, name: str) -> None:
        diags = validate_config({"placeholders": {name: "x"}})
        assert any(d.code == "invalid-placeholder-name" for d in diags)

    def test_placeholder_value_must_be_string(self) -> None:
        diags = validate_config({"placeholders": {"author": 3}})
        assert any(d.code == "type-mismatch" for d in diags)

    def test_artifact_dirs_must_be_array_of_strings(self) -> None:
        diags = validate_config({"routing": {"artifact_dirs": "artifacts/*"}})
        assert any(d.code == "type-mismatch" for d in diags)


def _merged_with_defaults(data: dict) -> dict:
    import copy

    from ktisma.domain.config import BUILTIN_DEFAULTS, _deep_merge

    merged = copy.deepcopy(BUILTIN_DEFAULTS)
    _deep_merge(merged, copy.deepcopy(data))
    return merged
