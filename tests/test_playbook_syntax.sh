#!/usr/bin/env bash
set -e
export PATH="$(pwd)/.venv/bin:$PATH"
ansible-playbook -i inventory/hosts.ini playbook.yml --syntax-check
ansible-playbook -i inventory/hosts.ini backup_acme.yml --syntax-check
