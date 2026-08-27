"""Sphinx configuration for {{ cookiecutter.project_name }}."""

from __future__ import annotations

import importlib.metadata

# -- Project information -----------------------------------------------------
project = "{{ cookiecutter.project_name }}"
copyright = "2024, {{ cookiecutter.author_name }}"
author = "{{ cookiecutter.author_name }}"

try:
    version = importlib.metadata.version("{{ cookiecutter.project_slug }}")
except importlib.metadata.PackageNotFoundError:
    version = "{{ cookiecutter.version }}"

release = version

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for autodoc -----------------------------------------------------
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autosummary_generate = True

# -- Options for intersphinx -------------------------------------------------
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "fastapi": ("https://fastapi.tiangolo.com/", None),
    "sqlalchemy": ("https://docs.sqlalchemy.org/en/20/", None),
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
}

# -- Options for HTML output -------------------------------------------------
html_theme = "furo"
html_title = "{{ cookiecutter.project_name }}"
html_static_path = ["_static"]

# -- Options for i18n --------------------------------------------------------
locale_dirs = ["locale/"]
gettext_compact = False
gettext_uuid = True
gettext_location = True
language = "en"
exclude_patterns += ["locale/"]

# -- Napoleon settings -------------------------------------------------------
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
