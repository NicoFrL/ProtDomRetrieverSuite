#!/bin/bash

# Setup script for ProtDomRetriever

# Create project directory structure
mkdir -p /Users/Nico/ProtDomRetrieverSuite/{src,tests,docs}
cd /Users/Nico/ProtDomRetrieverSuite

# Create source directory structure
mkdir -p src/{gui,processors,utils}
mkdir -p tests/{gui,processors,utils}

# Create necessary files
touch src/gui/__init__.py
touch src/processors/__init__.py
touch src/utils/__init__.py
touch tests/__init__.py

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Install package in development mode
pip install -e .

# Set up git repository
git init
echo "venv/" > .gitignore
echo "__pycache__/" >> .gitignore
echo "*.pyc" >> .gitignore
echo "*.pyo" >> .gitignore
echo "*.pyd" >> .gitignore
echo ".Python" >> .gitignore
echo "*.log" >> .gitignore
echo "output/" >> .gitignore
echo "cache/" >> .gitignore

git add .
git commit -m "Initial commit"

echo "Project setup complete!"
