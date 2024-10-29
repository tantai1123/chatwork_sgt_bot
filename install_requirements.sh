#!/bin/sh

# Install common dependencies
pip install --no-cache-dir -r requirements/requirements.txt

# Install action-specific dependencies
for req_file in requirements/requirements_*.txt; do
    pip install --no-cache-dir -r "$req_file"
done
