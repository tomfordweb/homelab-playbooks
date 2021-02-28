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

class ExampleInventory(object):

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
        allContainersOutput = list(map(vm_response_factory, allContainersOutput))
        # allContainersOutput = allContainersOutput.splitlines()

        hostIps = []
        for host in allContainersOutput:
            command = f"pct exec {host['id']} -- hostname -I | awk '{{print $1}}'"
            hostIpCommand = exec_ssh_command(ssh, command)
            host['ip'] = hostIpCommand['stdout'].read().decode('utf-8').rstrip()


        print(list(allContainersOutput))
        # return {
        #     'group': {
        #         'hosts': ['192.168.28.71', '192.168.28.72'],
        #         'vars': {
        #             'ansible_ssh_user': 'vagrant',
        #             'ansible_ssh_private_key_file':
        #                 '~/.vagrant.d/insecure_private_key',
        #             'example_variable': 'value'
        #         }
        #     },
        #     '_meta': {
        #         'hostvars': {
        #             '192.168.28.71': {
        #                 'host_specific_var': 'foo'
        #             },
        #             '192.168.28.72': {
        #                 'host_specific_var': 'bar'
        #             }
        #         }
        #     }
        # }

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
ExampleInventory()
