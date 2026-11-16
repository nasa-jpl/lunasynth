
# Lunasynth package

## Overview

Here there are described some of the decisions made during the development of the package. 

- package structure: src: it provides isolation. Other options: flat
- build system: uv (with the uv_build backend), it has a fast dependency solver and manages python versions. Other options: poetry, flit, hatch, setuptools
- testing framework: pytest, it is a good option for small projects. Other options: unittest, nose
- documentation: sphinx, good support. Other options: mkdocs, pdoc3
- coverage: pytest-cov, more convenient than coverage.py. Other options: coverage.py




## Folder Structure


The package has the following structure:
```bash
lunasynth
├── assets   
│   ├── base_meshes
│   ├── materials
│   └── rocks
├── config
│   ├── apollo_data
│   ├── extend_base_mesh_geometry
│   ├── polyhaven_textures
│   ├── rendering
│   └── sampling_jobs
├── docs
├── example_data
├── scripts
├── src
│   ├── blender_testing
│   ├── data_tools
│   ├── lunasynth
│   ├── matlab_create_rock_field
│   └── playground
├── test
└── tests
    └── resources
```

using the command:
```bash
tree -L 2 -d  -I "__pycache__"
```


# Development


## Development

### Testing

Run the tests with
```bash
(lunasynth) [lunasynth]$ pytest
```
See results in the terminal. See the coverage in `htmlcov/index.html`.


### Linting

Run the linter with
```bash
(lunasynth) [lunasynth]$ flake8 --format=html --htmldir=docs/flake-report src tests
```
See the results in `flake-report/index.html`.

Alternatively, you can run ruff with
```bash
(lunasynth) [lunasynth]$ ruff check
```
It will show you style errors like flake8, but it is much faster and it can correct some of the errors automatically with the option `--fix`.

### Formatting

Run the formatter with
```bash
(lunasynth) [lunasynth]$ ruff format
```
It will format the code according to the style defined in the `pyproject.toml` file.

## Documentation

The documentation site is built with [Sphinx](https://www.sphinx-doc.org/) and published to
https://nasa-jpl.github.io/lunasynth/ by the `docs.yml` workflow on every push to `main`.
Pull requests only build it.

- Markdown files and notebooks are parsed with [MyST-NB](https://myst-nb.readthedocs.io/).
  Notebooks are not executed; they are rendered with the outputs saved in them.
- The API reference is generated from the docstrings by
  [sphinx-autoapi](https://sphinx-autoapi.readthedocs.io/), which reads the source without importing it.
  Docstrings can use the NumPy (`Parameters` / `----------`) or Google (`Args:`) style.
- The configuration is in `docs/conf.py`. The Sphinx source directory is the repository root, so
  relative links and images work the same on GitHub and in the site.

Build the site locally with
```bash
(lunasynth) [lunasynth]$ make -C docs html
```
and open `docs/_build/html/index.html`. Use `make -C docs clean` to remove the build.

To add content:
- **Markdown page**: add a `.md` file to `docs/` and it appears under "Notes". Markdown files at the
  repository root and `README.md` files in folders under `src/` appear under "Project". Start each
  page with a `# Title`. The section pages are in `docs/sections/`.
- **Tutorial notebook**: add a `.ipynb` file to `src/tutorials/`, starting with a `# Title`
  markdown cell. Run it and save it with its outputs.
- **Static HTML page**: add a `.html` file to `docs/` and link it from a markdown page with a raw
  `<a href="page.html">` link. It is copied to the same path in the site.

## Issue Tracking

Use github issues to create any issue with Lunasynth