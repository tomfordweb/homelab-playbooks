Ansible playbooks to administer my proxmox ve cluster.

# Prettier

Run npm install locally, you probably need to add the vscode prettier package too if you want to get that running.

# Working with vaulted passwords

You can link your local vault password to the container using a volume. It would be advised to set this as read-only and it is added to verison control

To create a new vault password.

```bash
docker-compose run --entrypoint ansible-vault ansible encrypt_string --vault-password-file .vault_password 'secret' --name 'the_secret'
```

Your terminal will spit out some yaml that you can now include in any variable you need.

# Setup

### LXC Templates

If you need to update the template list, pass this argument on build

Please note: This will destroy and recreate the containers...things such as IP addresses assigned by DHCP may change.

```
docker-compose run ansible homelab.yml --extra-vars "update_templates=yes"
```

# Thanks

- https://github.com/lae/ansible-role-proxmox
