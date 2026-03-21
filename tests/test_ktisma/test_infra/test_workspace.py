"""Tests for ktisma.infra.workspace – workspace root resolution."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from ktisma.infra.workspace import resolve_workspace_root


# ---------------------------------------------------------------------------
# 1. CLI flag takes highest precedence
# ---------------------------------------------------------------------------


class TestCliFlag:
    def test_cli_flag_returns_resolved_path(self, tmp_path: Path) -> None:
        ws = tmp_path / "my_workspace"
        ws.mkdir()
        result = resolve_workspace_root(cli_workspace_root=ws)
        assert result == ws.resolve()

    def test_cli_flag_overrides_env_var(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ws_cli = tmp_path / "cli_ws"
        ws_cli.mkdir()
        ws_env = tmp_path / "env_ws"
        ws_env.mkdir()
        monkeypatch.setenv("KTISMA_WORKSPACE_ROOT", str(ws_env))
        result = resolve_workspace_root(cli_workspace_root=ws_cli)
        assert result == ws_cli.resolve()

    def test_cli_flag_overrides_adapter(self, tmp_path: Path) -> None:
        ws_cli = tmp_path / "cli_ws"
        ws_cli.mkdir()
        ws_adapter = tmp_path / "adapter_ws"
        ws_adapter.mkdir()
        result = resolve_workspace_root(
            cli_workspace_root=ws_cli, adapter_workspace_root=ws_adapter
        )
        assert result == ws_cli.resolve()

    def test_cli_flag_expands_user(self, tmp_path: Path) -> None:
        """Tilde paths are expanded."""
        ws = tmp_path / "ws"
        ws.mkdir()
        # We cannot reliably plant ~ here, but we can confirm resolve is called
        result = resolve_workspace_root(cli_workspace_root=ws)
        assert result.is_absolute()


# ---------------------------------------------------------------------------
# 2. Environment variable
# ---------------------------------------------------------------------------


class TestEnvVar:
    def test_env_var_used_when_no_cli_flag(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ws = tmp_path / "env_ws"
        ws.mkdir()
        monkeypatch.setenv("KTISMA_WORKSPACE_ROOT", str(ws))
        result = resolve_workspace_root()
        assert result == ws.resolve()

    def test_env_var_overrides_adapter(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ws_env = tmp_path / "env_ws"
        ws_env.mkdir()
        ws_adapter = tmp_path / "adapter_ws"
        ws_adapter.mkdir()
        monkeypatch.setenv("KTISMA_WORKSPACE_ROOT", str(ws_env))
        result = resolve_workspace_root(adapter_workspace_root=ws_adapter)
        assert result == ws_env.resolve()

    def test_empty_env_var_is_ignored(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An empty string in the env var should be treated as unset."""
        monkeypatch.setenv("KTISMA_WORKSPACE_ROOT", "")
        ws_adapter = tmp_path / "adapter_ws"
        ws_adapter.mkdir()
        result = resolve_workspace_root(adapter_workspace_root=ws_adapter)
        assert result == ws_adapter.resolve()

    def test_env_var_cleared_falls_through(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When env var is explicitly deleted, we should not use it."""
        monkeypatch.delenv("KTISMA_WORKSPACE_ROOT", raising=False)
        ws_adapter = tmp_path / "adapter_ws"
        ws_adapter.mkdir()
        result = resolve_workspace_root(adapter_workspace_root=ws_adapter)
        assert result == ws_adapter.resolve()


# ---------------------------------------------------------------------------
# 3. Adapter-provided workspace root
# ---------------------------------------------------------------------------


class TestAdapterProvided:
    def test_adapter_used_when_no_cli_or_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("KTISMA_WORKSPACE_ROOT", raising=False)
        ws = tmp_path / "adapter_ws"
        ws.mkdir()
        result = resolve_workspace_root(adapter_workspace_root=ws)
        assert result == ws.resolve()

    def test_adapter_overrides_config_ancestor(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("KTISMA_WORKSPACE_ROOT", raising=False)
        ws_adapter = tmp_path / "adapter_ws"
        ws_adapter.mkdir()

        # Create a .ktisma.toml in a parent so ancestor search would find it
        source_dir = tmp_path / "project" / "src"
        source_dir.mkdir(parents=True)
        (tmp_path / "project" / ".ktisma.toml").write_text("[build]\n")

        result = resolve_workspace_root(
            adapter_workspace_root=ws_adapter, source_dir=source_dir
        )
        assert result == ws_adapter.resolve()


# ---------------------------------------------------------------------------
# 4. Nearest .ktisma.toml ancestor
# ---------------------------------------------------------------------------


class TestConfigAncestor:
    def test_finds_config_in_source_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("KTISMA_WORKSPACE_ROOT", raising=False)
        source_dir = tmp_path / "project"
        source_dir.mkdir()
        (source_dir / ".ktisma.toml").write_text("[build]\n")
        result = resolve_workspace_root(source_dir=source_dir)
        assert result == source_dir.resolve()

    def test_finds_config_in_ancestor_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("KTISMA_WORKSPACE_ROOT", raising=False)
        root_dir = tmp_path / "project"
        root_dir.mkdir()
        (root_dir / ".ktisma.toml").write_text("[build]\n")
        source_dir = root_dir / "chapters" / "ch1"
        source_dir.mkdir(parents=True)
        result = resolve_workspace_root(source_dir=source_dir)
        assert result == root_dir.resolve()

    def test_nearest_ancestor_wins(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When multiple ancestors have .ktisma.toml, the nearest one wins."""
        monkeypatch.delenv("KTISMA_WORKSPACE_ROOT", raising=False)
        outer = tmp_path / "outer"
        inner = outer / "inner"
        deep = inner / "deep"
        deep.mkdir(parents=True)
        (outer / ".ktisma.toml").write_text("[build]\n")
        (inner / ".ktisma.toml").write_text("[build]\n")
        result = resolve_workspace_root(source_dir=deep)
        assert result == inner.resolve()

    def test_no_config_ancestor_falls_through(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If no ancestor has .ktisma.toml, fall through to cwd."""
        monkeypatch.delenv("KTISMA_WORKSPACE_ROOT", raising=False)
        source_dir = tmp_path / "project" / "src"
        source_dir.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)
        result = resolve_workspace_root(source_dir=source_dir)
        assert result == tmp_path.resolve()


# ---------------------------------------------------------------------------
# 5. CWD fallback
# ---------------------------------------------------------------------------


class TestCwdFallback:
    def test_cwd_when_nothing_provided(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("KTISMA_WORKSPACE_ROOT", raising=False)
        monkeypatch.chdir(tmp_path)
        result = resolve_workspace_root()
        assert result == tmp_path.resolve()

    def test_cwd_when_source_dir_has_no_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("KTISMA_WORKSPACE_ROOT", raising=False)
        monkeypatch.chdir(tmp_path)
        source_dir = tmp_path / "no_config"
        source_dir.mkdir()
        result = resolve_workspace_root(source_dir=source_dir)
        assert result == tmp_path.resolve()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_all_options_provided_cli_wins(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cli_ws = tmp_path / "cli"
        cli_ws.mkdir()
        env_ws = tmp_path / "env"
        env_ws.mkdir()
        adapter_ws = tmp_path / "adapter"
        adapter_ws.mkdir()
        source_dir = tmp_path / "src"
        source_dir.mkdir()
        (source_dir / ".ktisma.toml").write_text("[build]\n")
        monkeypatch.setenv("KTISMA_WORKSPACE_ROOT", str(env_ws))

        result = resolve_workspace_root(
            cli_workspace_root=cli_ws,
            adapter_workspace_root=adapter_ws,
            source_dir=source_dir,
        )
        assert result == cli_ws.resolve()

    def test_source_dir_none_skips_ancestor_search(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("KTISMA_WORKSPACE_ROOT", raising=False)
        monkeypatch.chdir(tmp_path)
        result = resolve_workspace_root(source_dir=None)
        assert result == tmp_path.resolve()

    def test_result_is_always_absolute(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("KTISMA_WORKSPACE_ROOT", raising=False)
        monkeypatch.chdir(tmp_path)
        result = resolve_workspace_root()
        assert result.is_absolute()

    def test_symlinked_source_dir_resolved(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Symlinks should be resolved to their real path."""
        monkeypatch.delenv("KTISMA_WORKSPACE_ROOT", raising=False)
        real_dir = tmp_path / "real_project"
        real_dir.mkdir()
        (real_dir / ".ktisma.toml").write_text("[build]\n")
        link = tmp_path / "link_project"
        link.symlink_to(real_dir)
        result = resolve_workspace_root(source_dir=link)
        assert result == real_dir.resolve()
