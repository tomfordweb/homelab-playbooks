#!/usr/bin/env python3

'''
Returns the inventory for the pve cluster 
formatted with variables using only hostname patterns.

Allows the use of DCHP by allowing control machine to administer commands
without knowing the IP beforehand
'''

import os
import sys
import argparse
import paramiko

try:
    import json
except ImportError:
    import simplejson as json

class ProxmoxVmResponse():
    '''
    A representation of a nodes container/vm
    '''
    def __init__(self, stdout_row):
        returnString = stdout_row.rstrip()
        split = returnString.split()

        self.id = split[0]
        self.hostname = split[1]
        self.ip = None

    def setIpAddress(self, paramiko_response):
        '''
        This response comes to us as a `byte` data type
        format it as a string
        '''
        self.ip = paramiko_response.get('stdout').read().decode('utf-8').rstrip()


    def toJson(self):
        return {
            "id": self.id,
            "hostname": self.hostname,
            "ip": self.ip
        }

class ProxmoxNodeInventory():
    '''
    A collection for the node responses
    '''
    def __init__(self, items):
        self.container = items

    def getContainersByHostnameStartsWith(self, search):
        items =  [x for x in self.container if x.hostname.startswith(search)]
        return ProxmoxNodeInventory(items)
    
    def length(self):
        return len(self.container)

    @staticmethod
    def createFromContainerResponse(paramiko_response):
        allContainersOutput = paramiko_response.get('stdout').readlines()
        all_containers = list(map(ProxmoxVmResponse, allContainersOutput))
        
        return ProxmoxNodeInventory(all_containers)

    def toJson(self):
        return [node.toJson() for node in self.container]


    
class PveVmHostVars():
    def __init__(self):
        self.container = {}
    
    def addItem(self, key, vars: dict):
        item = {
            key : vars
        }
        self.container.update(item)

    @staticmethod
    def create(inventory: ProxmoxNodeInventory):
        hostvars = PveVmHostVars()

        swarm_manager_containers = inventory.getContainersByHostnameStartsWith('swarm-manager')
        swarm_node_containers = inventory.getContainersByHostnameStartsWith('swarm-node')

        if(swarm_manager_containers.length() > 0 and swarm_node_containers.length() > 0):
            for host in swarm_node_containers.container:
                # Node hostnames must be this format node-01-03
                # Where 01 is the swarm manager id "swam-manager-01"
                # And 03 is the unique node id in relation to the manager
                node_swarm_manager_id = host.hostname.split('-')[2]
                swarm_manager = [x for x in swarm_manager_containers.container if x.hostname.endswith(node_swarm_manager_id)][0]
                hostvars.addItem(host.ip, { "manager": swarm_manager.ip})

        return hostvars
         
    def toJson(self):
        return self.container


class DynamicProxmoxInventory(object):
    '''
    Args: 
    --list      Returns a list of all inventory items
    --host      Returns a specific hostname
    '''
    def __init__(self):
        self.inventory = {}
        self.read_cli_args()

        if self.args.list:
            self.inventory = self.example_inventory()
        elif self.args.host:
            # Not implemented, since we return _meta info `--list`.
            self.inventory = self.empty_inventory()
        else:
            self.inventory = self.empty_inventory()

        print(json.dumps(self.inventory, indent=2))


    def paramiko_connection(self, server, username, password):
        ''' 
        Returns a paramiko ssh client
        '''
        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(server, username=username, password=password)
        return ssh

    def exec_ssh_command(self, paramikoClient, command):
        ''' 
        Returns a paramiko ssh response from the paramiko client
        TODO: error handling
        '''
        stdin, stdout, stderr = paramikoClient.exec_command(command)

        return {
            "stdin": stdin,
            "stdout": stdout,
            "stderr": stderr
        }

    def example_inventory(self):
        ssh = self.paramiko_connection('homelab', 'root', os.getenv('PVE_ROOT_PASSWORD'))

        # Retreive a list of all active containers running on the server.
        allContainersCommand  = self.exec_ssh_command(ssh, "pct list | grep 'running' | awk '{print $1, $3}'")

        inventory = ProxmoxNodeInventory.createFromContainerResponse(allContainersCommand)

        # This is a list of every VM with its IP address
        for host in inventory.container:
            command = f"pct exec {host.id} -- hostname -I | awk '{{print $1}}'"
            hostIpCommand = self.exec_ssh_command(ssh, command)
            host.setIpAddress(hostIpCommand)

        swarm_manager_containers = inventory.getContainersByHostnameStartsWith('swarm-manager')
        swarm_node_containers = inventory.getContainersByHostnameStartsWith('swarm-node')

        hostVars = PveVmHostVars.create(inventory)

        return {
            'swarmmanagers': {
                'hosts': [host.ip for host in swarm_manager_containers.container],
                'vars': {
                }
            },
            'swarmnodes': {
                'hosts': [host.ip for host in swarm_node_containers.container],
                'vars': {
                }
            },
            '_meta': {
                'hostvars': hostVars.toJson()

            }
        }

    def empty_inventory(self):
        return {'_meta': {'hostvars': {}}}

    def read_cli_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--list', action = 'store_true')
        parser.add_argument('--host', action = 'store')
        self.args = parser.parse_args()

# Get the inventory.
DynamicProxmoxInventory()
