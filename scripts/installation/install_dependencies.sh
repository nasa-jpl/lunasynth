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

# check if python3.11 is installed, install if not
if ! command -v python3.11 &> /dev/null; then
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            # check if python3.11 is available in the package manager, install if available, use deadsnakes PPA if not
            sudo apt update
            sudo apt install software-properties-common
            sudo add-apt-repository ppa:deadsnakes/ppa 
            sudo apt install -y python3.11
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install python@3.11
    fi
fi

# install pipx
# check if it is already installed
if ! command -v pipx &> /dev/null; then
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt update
        sudo apt install pipx
        pipx ensurepath
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install pipx
        pipx ensurepath
    fi
fi

# finally install poetry
if ! command -v poetry &> /dev/null; then
    pipx install poetry
fi

# python dependencies will be installed by poetry
poetry install # call poetry install evertime the lock file changes