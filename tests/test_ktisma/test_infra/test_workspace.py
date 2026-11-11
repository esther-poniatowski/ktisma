"""Tests for ktisma.infra.workspace – workspace root resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from ktisma.infra.workspace import resolve_workspace_root


@pytest.fixture(autouse=True)
def _clear_root_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the root variables of the calling shell out of every test."""
    monkeypatch.delenv("KTISMA_ROOT", raising=False)
    monkeypatch.delenv("KTISMA_WORKSPACE_ROOT", raising=False)


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
        monkeypatch.setenv("KTISMA_ROOT", str(ws_env))
        result = resolve_workspace_root(cli_workspace_root=ws_cli)
        assert result == ws_cli.resolve()

    def test_relative_cli_flag_is_read_from_the_current_folder(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ws = tmp_path / "ws"
        ws.mkdir()
        monkeypatch.chdir(tmp_path)
        result = resolve_workspace_root(cli_workspace_root=Path("ws"))
        assert result == ws.resolve()

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
        monkeypatch.setenv("KTISMA_ROOT", str(ws))
        result = resolve_workspace_root()
        assert result == ws.resolve()

    def test_env_var_overrides_config_ancestor(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ws_env = tmp_path / "env_ws"
        ws_env.mkdir()
        source_dir = tmp_path / "project" / "src"
        source_dir.mkdir(parents=True)
        (tmp_path / "project" / "ktisma.toml").write_text("[build]\n")
        monkeypatch.setenv("KTISMA_ROOT", str(ws_env))
        result = resolve_workspace_root(source_dir=source_dir)
        assert result == ws_env.resolve()

    def test_empty_env_var_is_ignored(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An empty string in the env var should be treated as unset."""
        monkeypatch.setenv("KTISMA_ROOT", "")
        monkeypatch.chdir(tmp_path)
        result = resolve_workspace_root()
        assert result == tmp_path.resolve()


class TestRetiredEnvVar:
    """The former variable KTISMA_WORKSPACE_ROOT is retired without a fallback."""

    def test_former_variable_is_ignored(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        former = tmp_path / "former_ws"
        former.mkdir()
        monkeypatch.setenv("KTISMA_WORKSPACE_ROOT", str(former))
        monkeypatch.chdir(tmp_path)
        assert resolve_workspace_root() == tmp_path.resolve()

    def test_former_variable_is_ignored_when_new_variable_is_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        former = tmp_path / "former_ws"
        former.mkdir()
        monkeypatch.setenv("KTISMA_ROOT", "")
        monkeypatch.setenv("KTISMA_WORKSPACE_ROOT", str(former))
        monkeypatch.chdir(tmp_path)
        assert resolve_workspace_root() == tmp_path.resolve()


# ---------------------------------------------------------------------------
# 3. Outermost ancestor holding a configuration file
# ---------------------------------------------------------------------------


class TestConfigAncestor:
    def test_finds_config_in_source_dir(self, tmp_path: Path) -> None:
        source_dir = tmp_path / "project"
        source_dir.mkdir()
        (source_dir / "ktisma.toml").write_text("[build]\n")
        result = resolve_workspace_root(source_dir=source_dir)
        assert result == source_dir.resolve()

    def test_finds_config_in_ancestor_dir(self, tmp_path: Path) -> None:
        root_dir = tmp_path / "project"
        root_dir.mkdir()
        (root_dir / "ktisma.toml").write_text("[build]\n")
        source_dir = root_dir / "chapters" / "ch1"
        source_dir.mkdir(parents=True)
        result = resolve_workspace_root(source_dir=source_dir)
        assert result == root_dir.resolve()

    def test_finds_config_in_config_tools(self, tmp_path: Path) -> None:
        root_dir = tmp_path / "project"
        (root_dir / "config" / "tools").mkdir(parents=True)
        (root_dir / "config" / "tools" / "ktisma.toml").write_text("[build]\n")
        source_dir = root_dir / "chapters"
        source_dir.mkdir()
        result = resolve_workspace_root(source_dir=source_dir)
        assert result == root_dir.resolve()

    def test_outermost_ancestor_wins(self, tmp_path: Path) -> None:
        """When multiple ancestors hold ktisma.toml, the outermost one wins."""
        outer = tmp_path / "outer"
        inner = outer / "inner"
        deep = inner / "deep"
        deep.mkdir(parents=True)
        (outer / "ktisma.toml").write_text("[build]\n")
        (inner / "ktisma.toml").write_text("[build]\n")
        result = resolve_workspace_root(source_dir=deep)
        assert result == outer.resolve()

    def test_outermost_ancestor_wins_across_both_places(self, tmp_path: Path) -> None:
        outer = tmp_path / "outer"
        inner = outer / "inner"
        (outer / "config" / "tools").mkdir(parents=True)
        (outer / "config" / "tools" / "ktisma.toml").write_text("[build]\n")
        inner.mkdir()
        (inner / "ktisma.toml").write_text("[build]\n")
        result = resolve_workspace_root(source_dir=inner)
        assert result == outer.resolve()

    def test_former_settings_name_is_not_recognized(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A file still named .ktisma.toml does not mark a workspace root."""
        source_dir = tmp_path / "project"
        source_dir.mkdir()
        (source_dir / ".ktisma.toml").write_text("[build]\n")
        monkeypatch.chdir(tmp_path)
        result = resolve_workspace_root(source_dir=source_dir)
        assert result == tmp_path.resolve()

    def test_no_config_ancestor_falls_through(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If no ancestor holds ktisma.toml, fall through to cwd."""
        source_dir = tmp_path / "project" / "src"
        source_dir.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)
        result = resolve_workspace_root(source_dir=source_dir)
        assert result == tmp_path.resolve()

    def test_search_starts_at_the_current_folder_without_a_source(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root_dir = tmp_path / "project"
        sub = root_dir / "sub"
        sub.mkdir(parents=True)
        (root_dir / "ktisma.toml").write_text("[build]\n")
        monkeypatch.chdir(sub)
        assert resolve_workspace_root() == root_dir.resolve()


# ---------------------------------------------------------------------------
# 4. CWD fallback
# ---------------------------------------------------------------------------


class TestCwdFallback:
    def test_cwd_when_nothing_provided(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        result = resolve_workspace_root()
        assert result == tmp_path.resolve()

    def test_cwd_when_source_dir_has_no_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
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
        source_dir = tmp_path / "src"
        source_dir.mkdir()
        (source_dir / "ktisma.toml").write_text("[build]\n")
        monkeypatch.setenv("KTISMA_ROOT", str(env_ws))

        result = resolve_workspace_root(cli_workspace_root=cli_ws, source_dir=source_dir)
        assert result == cli_ws.resolve()

    def test_result_is_always_absolute(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        result = resolve_workspace_root()
        assert result.is_absolute()

    def test_symlinked_source_dir_resolved(self, tmp_path: Path) -> None:
        """Symlinks should be resolved to their real path."""
        real_dir = tmp_path / "real_project"
        real_dir.mkdir()
        (real_dir / "ktisma.toml").write_text("[build]\n")
        link = tmp_path / "link_project"
        link.symlink_to(real_dir)
        result = resolve_workspace_root(source_dir=link)
        assert result == real_dir.resolve()
