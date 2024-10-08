#!/bin/bash

# check lunasynth python package is installed
if ! python3 -c "import lunasynth"; then
    echo "lunasynth python package is not installed"
    exit 1
fi

# checkout main branch
git checkout main

# checkout gh-pages branch
git checkout gh-pages

# merge main into gh-pages
git merge main --commit --no-edit

# Create coverage report
pytest

# Generate sphinx documentation
make -C docs html

# copy coverage report to docs/htmlcov
mv htmlcov docs/coverage-report

# create flake8 report
flake8 --format=html --htmldir=docs/flake8-report src tests

# generate cli docs
python3 src/generate_markdown_cli.py src/lunasynth/cli/*

# commit and push changes
git add docs/
git add htmlcov/
git add docs/build/
git add .coverage
git commit -m "Update coverage report"

# push changes
git push

# checkout master branch
git checkout main

