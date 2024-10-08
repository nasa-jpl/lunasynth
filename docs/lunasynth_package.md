
# Lunasynth package

## Overview

Here there are described some of the decisions made during the development of the package. 

- package structure: src: it provides isolation. Other options: flat
- build system: poetry, it has a good dependency solver. Other options: flit, hatch, setuptools
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


Sphinx: 

Once to start the documentation:
```bash
(lunasynth) [lunasynth]$ sphinx-quickstart docs
```

To generate the `.rst` files from the docstrings:
```bash
(lunasynth) [lunasynth]$ sphinx-apidoc -o docs/source src
```

To build the html files:
```bash
(lunasynth) [lunasynth]$ make -C docs html
```



## Issue Tracking

Use github issues to create any issue with Lunasynth