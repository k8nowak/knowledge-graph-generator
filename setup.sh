#!/bin/bash

# Create directory structure
mkdir -p src
mkdir -p data
mkdir -p output

# Move the main script if it's not already there
if [ -f "KG_creator_networkx.py" ] && [ ! -f "src/KG_creator_networkx.py" ]; then
    mv KG_creator_networkx.py src/
fi

# Move CSV files if they exist
if [ -f "concepts.csv" ]; then
    mv concepts.csv data/
fi

if [ -f "connections.csv" ]; then
    mv connections.csv data/
fi

# Create __init__.py to make src a proper package
touch src/__init__.py 