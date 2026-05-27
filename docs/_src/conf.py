"""
Sphinx configuration for Ktisma API documentation.

Sphinx scope is restricted to the API tree under this directory. The prose
documentation (docs/index.md, docs/guide/, docs/internals/, docs/adr/) is
hand-written Markdown and not part of the Sphinx build.

Build via ``make api`` (Markdown into ``docs/api/``, committed) or
``make html`` (HTML preview into ``docs/_build/html/``, gitignored).
"""

import os
import sys

# Add source directory to path for autodoc.
# This file lives at docs/_src/conf.py; the package is at ../../src.
sys.path.insert(0, os.path.abspath("../../src"))

# -- Project information -----------------------------------------------------

project = "Ktisma"
copyright = "2025, Esther Poniatowski"
author = "Esther Poniatowski"
release = "0.0.0"

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "myst_parser",
    "sphinx_markdown_builder",
]

exclude_patterns = ["Thumbs.db", ".DS_Store"]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# -- MyST settings -----------------------------------------------------------

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "fieldlist",
    "tasklist",
]

# -- Options for HTML output -------------------------------------------------

html_theme = "sphinx_rtd_theme"

# -- Napoleon settings -------------------------------------------------------

napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_custom_sections = [("Class Attributes", "params_style")]

# -- Autodoc settings --------------------------------------------------------

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}
autodoc_typehints = "description"
autodoc_typehints_description_target = "documented"
autodoc_member_order = "bysource"

# -- Intersphinx -------------------------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

# -- Markdown builder configuration ------------------------------------------

# Emit explicit `<a id="...">` anchors at section and signature boundaries so
# the cross-references autodoc generates (e.g. `#module-ktisma.app.build`,
# `#ktisma.app.build.BuildResult`) actually resolve on GitHub.
markdown_anchor_sections = True
markdown_anchor_signatures = True

# -- Markdown builder customization ------------------------------------------
#
# sphinx_markdown_builder renders every admonition (note, warning, seealso, ...)
# through _push_box, which emits "#### TITLE" at H4 with an upper-cased title.
# Napoleon translates the NumPy `See Also` section into a `seealso` admonition,
# so it lands as H4 SEE ALSO. Render it instead as a Markdown blockquote
# admonition with title "See also", preserving the semantic distinction while
# keeping heading levels uncluttered.


def setup(app):
    from sphinx_markdown_builder.contexts import SubContext, SubContextParams
    from sphinx_markdown_builder.translator import (
        MarkdownTranslator,
        pushing_context,
    )

    class BlockquoteContext(SubContext):
        """Prefixes every line of the rendered body with '> ' on flush."""

        def make(self) -> str:
            content = super().make()
            lines = content.strip("\n").split("\n")
            quoted = "\n".join(f"> {line}" if line else ">" for line in lines)
            return f"> **See also**\n>\n{quoted}"

    @pushing_context
    def visit_seealso(self, _node):
        self._push_context(BlockquoteContext(SubContextParams(2, 2)))

    MarkdownTranslator.visit_seealso = visit_seealso

    # sphinx_markdown_builder ships no `visit_abbreviation` handler. The
    # builder then emits "unknown node type" warnings and drops the node's
    # text. Render the abbreviation's child text verbatim (the parent
    # paragraph visitor handles surrounding spacing).

    def visit_abbreviation(self, _node):
        pass

    def depart_abbreviation(self, _node):
        pass

    MarkdownTranslator.visit_abbreviation = visit_abbreviation
    MarkdownTranslator.depart_abbreviation = depart_abbreviation
