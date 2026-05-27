# Makefile for Ktisma documentation
#
# Sphinx is restricted to the API documentation tree. Prose documentation
# (index.md, guide/, internals/, adr/) is hand-written Markdown and not
# part of the Sphinx build.
#
# Source root: _src/       (API entry points: index.md + automodule stubs)
# Output:      api/        (generated Markdown, committed to git)
# Cache:       _build/     (gitignored)

SPHINXBUILD := sphinx-build
SOURCEDIR   := _src
APIDIR      := api
BUILDDIR    := _build

.PHONY: help api html clean

help:
	@echo "Targets:"
	@echo "  api    Generate Markdown API docs into $(APIDIR)/"
	@echo "  html   Generate HTML preview into $(BUILDDIR)/html/"
	@echo "  clean  Remove generated API docs and build cache"

api:
	$(SPHINXBUILD) -b markdown -d $(BUILDDIR)/doctrees $(SOURCEDIR) $(APIDIR)

html:
	$(SPHINXBUILD) -b html -d $(BUILDDIR)/doctrees $(SOURCEDIR) $(BUILDDIR)/html

clean:
	rm -rf $(APIDIR)/*.md $(BUILDDIR)
