#!/usr/bin/env python3

'''
Example custom dynamic inventory script for Ansible, in Python.
'''

import os
import sys
import argparse
import paramiko

try:
    import json
except ImportError:
    import simplejson as json

def exec_ssh_command(paramikoClient, command):
    stdin, stdout, stderr = paramikoClient.exec_command(command)

    return {
        "stdin": stdin,
        "stdout": stdout,
        "stderr": stderr
    }

def vm_response_factory(line):
    returnString = line.rstrip()
    split = returnString.split()
    return {
        "id": split[0],
        "hostname": split[1],
        "ip": None
    }

class ProxmoxVmInventory(object):

    def __init__(self):
        self.inventory = {}
        self.read_cli_args()

        # Called with `--list`.
        if self.args.list:
            self.inventory = self.example_inventory()
        # Called with `--host [hostname]`.
        elif self.args.host:
            # Not implemented, since we return _meta info `--list`.
            self.inventory = self.empty_inventory()
        # If no groups or vars are present, return an empty inventory.
        else:
            self.inventory = self.empty_inventory()

        print(json.dumps(self.inventory))

    # Example inventory for testing.
    def example_inventory(self):
        server = 'homelab'
        username='root'
        password=os.getenv('PVE_ROOT_PASSWORD')

        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(server, username=username, password=password)
        # Get a list of active vms
        allContainersCommand  = exec_ssh_command(ssh, "pct list | grep 'running' | awk '{print $1, $3}'")
        allContainersOutput = allContainersCommand['stdout'].readlines()
        all_containers = list(map(vm_response_factory, allContainersOutput))

        # This is a list of every VM with its IP address
        for host in all_containers:
            command = f"pct exec {host['id']} -- hostname -I | awk '{{print $1}}'"
            hostIpCommand = exec_ssh_command(ssh, command)
            host['ip'] = hostIpCommand['stdout'].read().decode('utf-8').rstrip()

        # extract swarm managers
        swarm_manager_containers = [x for x in all_containers if x['hostname'].startswith('swarm-manager')]
        swarm_node_containers = [x for x in all_containers if x['hostname'].startswith('swarm-node')]

        hostvars = {}
        # For every swarm node, determine which manager it belongs to and set a custom
        # host variable for that node. This will let us create a join token and join the appropriate
        # swarm in the playbook
        for host in swarm_node_containers:
            node_swarm_manager_id = host['hostname'].split('-')[2]
            swarm_manager = [x for x in swarm_manager_containers if x['hostname'].endswith(node_swarm_manager_id)][0]
            hostvars[host['ip']] = {
                    "manager": swarm_manager['ip']
                }


        return {
            'swarmmanagers': {
                'hosts': [host['ip'] for host in swarm_manager_containers],
                'vars': {
                }
            },
            'swarmnodes': {
                'hosts': [host['ip'] for host in swarm_node_containers],
                'vars': {
                }
            },
            '_meta': {
                'hostvars': hostvars

            }
        }

    # Empty inventory for testing.
    def empty_inventory(self):
        return {'_meta': {'hostvars': {}}}

    # Read the command line args passed to the script.
    def read_cli_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--list', action = 'store_true')
        parser.add_argument('--host', action = 'store')
        self.args = parser.parse_args()

# Get the inventory.
ProxmoxVmInventory()
