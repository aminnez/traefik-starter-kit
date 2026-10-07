#!/usr/bin/env python3

import argparse
import json
import os
import sys

class SSHInventory(object):
    def __init__(self):
        self.inventory = {}
        self.read_cli_args()
        
        if self.args.list:
            self.inventory = self.get_inventory()
        elif self.args.host:
            self.inventory = self.empty_inventory()
        else:
            self.inventory = self.get_inventory()
        
        print(json.dumps(self.inventory))
    
    def get_inventory(self):
        inventory = {
            '_meta': {
                'hostvars': {}
            }
        }
        
        ssh_config = os.path.expanduser('~/.ssh/config')
        if not os.path.isfile(ssh_config):
            return inventory
        
        current_host = None
        host_vars = {}
        
        with open(ssh_config, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                    
                if line.lower().startswith('host '):
                    if current_host and host_vars:
                        inventory['_meta']['hostvars'][current_host] = host_vars
                        if 'groups' in host_vars:
                            for group in host_vars['groups'].split(','):
                                if group not in inventory:
                                    inventory[group] = {'hosts': []}
                                if current_host not in inventory[group]['hosts']:
                                    inventory[group]['hosts'].append(current_host)
                    
                    # Split host aliases (can have multiple per Host line, or wildcard)
                    hosts = line.split()[1:]
                    # Skip wildcards like Host *
                    target_host = None
                    for h in hosts:
                        if '*' not in h and '?' not in h:
                            target_host = h
                            break
                    
                    current_host = target_host
                    host_vars = {}
                    
                    if current_host:
                        if 'all' not in inventory:
                            inventory['all'] = {'hosts': []}
                        if current_host not in inventory['all']['hosts']:
                            inventory['all']['hosts'].append(current_host)
                
                elif ' ' in line and current_host:
                    key, value = line.split(maxsplit=1)
                    key = key.lower()
                    
                    if key == 'hostname':
                        host_vars['ansible_host'] = value
                    elif key == 'port':
                        try:
                            host_vars['ansible_port'] = int(value)
                        except ValueError:
                            pass
                    elif key == 'user':
                        host_vars['ansible_user'] = value
                    elif key == 'identityfile':
                        host_vars['ansible_ssh_private_key_file'] = value.replace('~', os.path.expanduser('~'))
                    elif key == 'proxycommand':
                        host_vars['ansible_ssh_common_args'] = f'-o ProxyCommand="{value}"'
        
        # Add the last host
        if current_host and host_vars:
            inventory['_meta']['hostvars'][current_host] = host_vars
            if 'groups' in host_vars:
                for group in host_vars['groups'].split(','):
                    if group not in inventory:
                        inventory[group] = {'hosts': []}
                    if current_host not in inventory[group]['hosts']:
                        inventory[group]['hosts'].append(current_host)
        
        return inventory
    
    def empty_inventory(self):
        return {'_meta': {'hostvars': {}}}
    
    def read_cli_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--list', action='store_true')
        parser.add_argument('--host', action='store')
        self.args = parser.parse_args()

if __name__ == '__main__':
    SSHInventory()
