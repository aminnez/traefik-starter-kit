#!/usr/bin/env bash
set -e
export PATH="$(pwd)/.venv/bin:$PATH"

echo "Running pytest suite..."
pytest tests/ -v

echo "Running Ansible syntax check..."
./tests/test_playbook_syntax.sh

echo "All validation checks passed successfully!"
