# Minimal makefile for Sphinx documentation

SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build
LOCALEDIR     = locale
LANGS         = en fa_IR

.PHONY: help clean html livehtml gettext translate

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

clean:
	rm -rf $(BUILDDIR)

html:
	@for lang in $(LANGS); do \
		echo "Building $$lang..."; \
		$(SPHINXBUILD) -b html -D language=$$lang "$(SOURCEDIR)" "$(BUILDDIR)/$$lang" $(SPHINXOPTS) $(O); \
	done

livehtml:
	sphinx-autobuild "$(SOURCEDIR)" "$(BUILDDIR)/html" $(SPHINXOPTS) $(O)

gettext:
	$(SPHINXBUILD) -b gettext "$(SOURCEDIR)" "$(BUILDDIR)/gettext" $(SPHINXOPTS) $(O)

translate: gettext
	@for lang in $(filter-out en,$(LANGS)); do \
		echo "Updating $$lang translations..."; \
		sphinx-intl update -p "$(BUILDDIR)/gettext" -l $$lang; \
	done

# Catch-all target: route all unknown targets to Sphinx
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
