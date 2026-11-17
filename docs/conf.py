#  Copyright (c) 2024. Jet Propulsion Laboratory. All rights reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# Configuration file for the Sphinx documentation builder.
#
# The source directory is the repository root, so markdown files and notebooks
# anywhere in the repo are picked up and their relative links work as on GitHub.
# Build from the repository root with:
#   sphinx-build -c docs . docs/_build/html
# or from this folder with `make html`.
#
# Paths in include_patterns, exclude_patterns and autoapi_* are relative to the
# repository root. Paths in html_* options are relative to this folder.

import shutil
import tomllib
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent

# -- Project information -----------------------------------------------------

project = "LuNaSynth"
author = "Daniel Pastor"
copyright = "2024, Jet Propulsion Laboratory"
release = tomllib.loads((repo_root / "pyproject.toml").read_text())["project"]["version"]
version = release

# -- General configuration ---------------------------------------------------

extensions = [
    "myst_nb",  # markdown and notebooks, loads myst_parser
    "sphinx.ext.napoleon",  # NumPy and Google style docstrings
    "sphinx.ext.viewcode",  # must be loaded before autoapi so it uses autoapi's parsed source
    "autoapi.extension",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinxcontrib.mermaid",  # ```mermaid blocks, as rendered by GitHub
]

# Only these files become pages. Any new markdown file in these places is added automatically.
include_patterns = [
    "*.md",
    "docs/**",
    "src/**.md",
    "src/tutorials/*.ipynb",
    "tests/*.md",
    "test/*.md",
    "test/dataset_analysis.ipynb",
]
# Excluded folders are not walked, which keeps .venv and other large folders out of the build.
exclude_patterns = [
    ".*",
    "**/.*",
    "docs/_build",
    "tmp",
    "render_jobs",
    "assets",
    "example_data",
    "config",
    "scripts",
    "**/__pycache__",
]

# -- MyST and notebooks ------------------------------------------------------

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "dollarmath",
    "amsmath",
    "html_image",
    "attrs_inline",
]
myst_heading_anchors = 4
myst_fence_as_directive = ["mermaid"]

# Notebooks need Blender and the full assets to run, so they are rendered with their saved outputs.
nb_execution_mode = "off"

# -- API reference -----------------------------------------------------------

# AutoAPI parses the source without importing it. Importing lunasynth loads bpy and
# some modules have side effects at import time.
autoapi_dirs = ["src/lunasynth"]
autoapi_root = "docs/api"
autoapi_ignore = ["*/examples*", "*/blender_addons*"]
autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
]
autoapi_python_class_content = "both"
autoapi_member_order = "groupwise"

napoleon_google_docstring = True
napoleon_numpy_docstring = True
# "Attributes" sections as a field list; AutoAPI already documents dataclass fields
napoleon_use_ivar = True

# -- HTML output -------------------------------------------------------------

html_theme = "pydata_sphinx_theme"
html_title = f"LuNaSynth {release}"
html_logo = "lunasynth_logo_transparent_background.png"
html_favicon = "lunasynth_logo_transparent_background.png"
# the tutorial notebooks are large; don't copy their sources into the site
html_copy_source = False
html_show_sourcelink = False

html_theme_options = {
    "github_url": "https://github.com/nasa-jpl/lunasynth",
    "use_edit_page_button": True,
    "show_toc_level": 2,
    "navigation_with_keys": False,
}
html_context = {
    "github_user": "nasa-jpl",
    "github_repo": "lunasynth",
    "github_version": "main",
    "doc_path": "",
}


def copy_static_html_pages(app, exception):
    """Copy standalone HTML pages in docs/ to the same relative path in the site.

    Link to them from markdown with a raw ``<a href="page.html">`` so the link works
    both on GitHub and in the built site.
    """
    if exception is not None or app.builder.format != "html":
        return
    docs_dir = repo_root / "docs"
    out_dir = Path(app.outdir).resolve()
    for page in docs_dir.rglob("*.html"):
        relative = page.relative_to(docs_dir)
        if relative.parts[0] in ("_build", "api"):
            continue
        target = out_dir / "docs" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(page, target)


def setup(app):
    app.connect("build-finished", copy_static_html_pages)
