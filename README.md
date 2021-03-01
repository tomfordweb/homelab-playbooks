Ansible playbooks to administer my proxmox ve cluster.

# Playbooks

### `docker-compose run ansible -i inventory/all -i inventory/pvenodes.py main.yml`

Runs all playbooks.

### `docker-compose run ansible -i inventory/pvenodes.py docker.yml`

Installs, and configures a docker swarm for hosts following the naming convention.

```
swarm-manager-[swarm-manager-id]
swarm-node-<swarm-node-id>-<swarm-manager-id>

# example...
swarm-manager-01
swarm-node-01-01
swarm-node-01-02
swarm-manager-02
swarm-node-02-01
swarm-node-02-02
```

# Other Tips

### Debugging

## `docker-compsose run --entrypoint ansible ansible all -i inventory/pvenodes.py -m ping`

Ensure that all pve nodes are reachable.

### Prettier

Run npm install locally, you probably need to add the vscode prettier package too if you want to get that running.

### Creating vaulted passwords

You can link your local vault password to the container using a volume. It would be advised to set this as read-only and it is added to verison control

To create a new vault password.

```bash
docker-compose run --entrypoint ansible-vault ansible encrypt_string --vault-password-file .vault_password 'secret' --name 'the_secret'
```

Your terminal will spit out some yaml that you can now include in any variable you need.


# Thanks

- https://github.com/lae/ansible-role-proxmox
