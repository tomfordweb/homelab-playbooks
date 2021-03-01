#!/usr/bin/env python3

'''
A dynamic inventory script that will open an SSH session to the
pve node and get a list of all running containers.

It will the returned a detailed inventory setting up any group variables needed.
'''

import os
import sys
import argparse
import paramiko

try:
    import json
except ImportError:
    import simplejson as json

def paramiko_connection(server, username, password):
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(server, username=username, password=password)
    return ssh;

def exec_ssh_command(paramikoClient, command):
    stdin, stdout, stderr = paramikoClient.exec_command(command)

    return {
        "stdin": stdin,
        "stdout": stdout,
        "stderr": stderr
    }


class ProxmoxVmResponse():
    def __init__(self, stdout_row):
        returnString = stdout_row.rstrip()
        split = returnString.split()

        self.id = split[0]
        self.hostname = split[1]
        self.ip = None

    def setIpAddress(self, paramiko_response):
        self.ip = paramiko_response.get('stdout').read().decode('utf-8').rstrip()


    def toJson(self):
        return {
            "id": self.id,
            "hostname": self.hostname,
            "ip": self.ip
        }

class ProxmoxNodeInventory():
    def __init__(self, items):
        self.container = items


    def getContainersByHostnameStartsWith(self, search):
        return [x for x in self.container if x.hostname.startswith(search)]


    @staticmethod
    def createFromContainerResponse(paramiko_response):
        allContainersOutput = paramiko_response.get('stdout').readlines()
        all_containers = list(map(ProxmoxVmResponse, allContainersOutput))
        
        return ProxmoxNodeInventory(all_containers)

    def toJson(self):
        return [node.toJson() for node in self.container]


# TODO: Use objects, clean this logic up
def generate_swarm_node_meta(swarm_manager_containers, swarm_node_containers):

    hostvars = {}
    # For every swarm node, determine which manager it belongs to and set a custom
    # host variable for that node. This will let us create a join token and join the appropriate
    # swarm in the playbook
    for host in swarm_node_containers:
        node_swarm_manager_id = host.hostname.split('-')[2]
        swarm_manager = [x for x in swarm_manager_containers if x.hostname.endswith(node_swarm_manager_id)][0]
        hostvars[host.ip] = {
            "manager": swarm_manager.ip
        }

    return hostvars



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
        ssh = paramiko_connection('homelab', 'root', os.getenv('PVE_ROOT_PASSWORD'))

        # Retreive a list of all active containers running on the server.
        allContainersCommand  = exec_ssh_command(ssh, "pct list | grep 'running' | awk '{print $1, $3}'")

        all_containers = ProxmoxNodeInventory.createFromContainerResponse(allContainersCommand)

        # This is a list of every VM with its IP address
        for host in all_containers.container:
            command = f"pct exec {host.id} -- hostname -I | awk '{{print $1}}'"
            hostIpCommand = exec_ssh_command(ssh, command)
            host.setIpAddress(hostIpCommand)

        swarm_manager_containers = all_containers.getContainersByHostnameStartsWith('swarm-manager')
        swarm_node_containers = all_containers.getContainersByHostnameStartsWith('swarm-node')

        
        hostvars = generate_swarm_node_meta(swarm_manager_containers, swarm_node_containers)

        return {
            'swarmmanagers': {
                'hosts': [host.ip for host in swarm_manager_containers],
                'vars': {
                }
            },
            'swarmnodes': {
                'hosts': [host.ip for host in swarm_node_containers],
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
