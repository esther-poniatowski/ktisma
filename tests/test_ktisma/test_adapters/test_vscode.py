"""Tests for the VS Code / LaTeX Workshop adapter."""

from __future__ import annotations

import json

from ktisma.adapters.vscode import (
    generate_latex_workshop_config,
    format_latex_workshop_snippet,
)


# ---------------------------------------------------------------------------
# generate_latex_workshop_config
# ---------------------------------------------------------------------------


class TestGenerateLatexWorkshopConfig:
    """Test structure and expected keys of the generated config dict."""

    def test_returns_dict(self):
        config = generate_latex_workshop_config()
        assert isinstance(config, dict)

    def test_contains_tools_key(self):
        config = generate_latex_workshop_config()
        assert "latex-workshop.latex.tools" in config

    def test_contains_recipes_key(self):
        config = generate_latex_workshop_config()
        assert "latex-workshop.latex.recipes" in config

    def test_contains_autoclean_key(self):
        config = generate_latex_workshop_config()
        assert "latex-workshop.latex.autoClean.run" in config

    def test_autoclean_is_never(self):
        config = generate_latex_workshop_config()
        assert config["latex-workshop.latex.autoClean.run"] == "never"

    def test_tool_entry_structure(self):
        config = generate_latex_workshop_config()
        tools = config["latex-workshop.latex.tools"]
        assert isinstance(tools, list)
        assert len(tools) == 1
        tool = tools[0]
        assert tool["name"] == "ktisma"
        assert tool["command"] == "python3"
        assert isinstance(tool["args"], list)

    def test_tool_args_contain_build(self):
        config = generate_latex_workshop_config()
        tool = config["latex-workshop.latex.tools"][0]
        assert "build" in tool["args"]

    def test_tool_args_do_not_force_workspace_root(self):
        config = generate_latex_workshop_config()
        tool = config["latex-workshop.latex.tools"][0]
        assert "--workspace-root" not in tool["args"]

    def test_tool_args_contain_doc_placeholder(self):
        config = generate_latex_workshop_config()
        tool = config["latex-workshop.latex.tools"][0]
        assert "%DOC_EXT%" in tool["args"]

    def test_recipe_references_ktisma_tool(self):
        config = generate_latex_workshop_config()
        recipes = config["latex-workshop.latex.recipes"]
        assert isinstance(recipes, list)
        assert len(recipes) == 1
        recipe = recipes[0]
        assert recipe["name"] == "ktisma"
        assert "ktisma" in recipe["tools"]

    def test_custom_ktisma_path(self):
        custom_path = "/usr/local/bin/ktisma"
        config = generate_latex_workshop_config(ktisma_path=custom_path)
        tool = config["latex-workshop.latex.tools"][0]
        assert custom_path in tool["args"]

    def test_default_ktisma_path_in_args(self):
        config = generate_latex_workshop_config()
        tool = config["latex-workshop.latex.tools"][0]
        default_path = "%WORKSPACE_FOLDER%/vendor/ktisma/bin/ktisma"
        assert default_path in tool["args"]


# ---------------------------------------------------------------------------
# format_latex_workshop_snippet
# ---------------------------------------------------------------------------


class TestFormatLatexWorkshopSnippet:
    """Test the JSONC snippet formatter."""

    def test_returns_string(self):
        snippet = format_latex_workshop_snippet()
        assert isinstance(snippet, str)

    def test_is_valid_json(self):
        snippet = format_latex_workshop_snippet()
        parsed = json.loads(snippet)
        assert isinstance(parsed, dict)

    def test_snippet_matches_config(self):
        snippet = format_latex_workshop_snippet()
        parsed = json.loads(snippet)
        config = generate_latex_workshop_config()
        assert parsed == config

    def test_custom_path_propagated(self):
        custom_path = "/opt/ktisma"
        snippet = format_latex_workshop_snippet(ktisma_path=custom_path)
        parsed = json.loads(snippet)
        tool = parsed["latex-workshop.latex.tools"][0]
        assert custom_path in tool["args"]
