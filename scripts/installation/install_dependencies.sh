#!/bin/bash 

# check we are in Debian, or MacOS, reject otherwise
if [[ "$OSTYPE" != "linux-gnu"* ]] && [[ "$OSTYPE" != "darwin"* ]]; then
    echo "This script is only for Debian or MacOS"
    exit 1
fi

#  install python3-pip, git, git-lfs
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    sudo apt install git git-lfs python3-pip qgis imagemagick
elif [[ "$OSTYPE" == "darwin"* ]]; then
    brew install git git-lfs python3-pip qgis imagemagick 
fi

# finally install uv, it also manages the python version required by the project
if ! command -v uv &> /dev/null; then
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
        source "$HOME/.local/bin/env"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install uv
    fi
fi

# python dependencies will be installed by uv
uv sync # call uv sync everytime the lock file changes