#!/bin/bash

# Install system dependencies
sudo apt update && xargs -a apt-requirements.txt sudo apt install -y

# Install Python dependencies
pip install -r requirements.txt
