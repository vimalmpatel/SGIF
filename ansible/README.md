# Ansible Guide

These examples are designed for Debian/Ubuntu **support servers only**. Do not
put OT equipment in the `support_servers` group. The committed inventory is
empty and is used only for syntax checks.

Create an untracked inventory at `ansible/inventories/local.yml` and add only
authorized support-server hosts. Keep credentials in Ansible Vault or an
approved secret manager; never put them in inventory or source control.

Check syntax without making a connection:

```sh
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventories/example.yml ansible/playbooks/site.yml --syntax-check
```

## Install the SGIF lab stack on Ubuntu

`playbooks/install_lab.yml` provisions a dedicated Ubuntu 22.04+ small server
with Docker Engine and the local SGIF Compose profile (API, web dashboard,
PostgreSQL, and Keycloak). It is not for OT devices or a production control
network. Service ports bind to localhost on the Ubuntu box; use an approved
management path or SSH tunnel rather than exposing them to the site network.

Use Ansible Core 2.15 or newer on the controller, then install the pinned
collections required by this repository:

```sh
ansible-galaxy collection install -r ansible/requirements.yml
```

Create an untracked `ansible/inventories/local.yml` with a dedicated lab host
in `sgif_lab_servers`. Create an encrypted vars file with `ansible-vault
create ansible/inventories/sgif-lab.vault.yml` containing:

```yaml
sgif_stack_enable: true
sgif_stack_postgres_password: "<32+ character alphanumeric secret>"
sgif_stack_app_db_password: "<different 32+ character alphanumeric secret>"
sgif_stack_keycloak_db_password: "<different 32+ character alphanumeric secret>"
sgif_stack_keycloak_admin_password: "<different 32+ character alphanumeric secret>"
```

Run the install only after confirming the host is a dedicated Ubuntu lab box
and backups/recovery access are available:

```sh
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook \
	-i ansible/inventories/local.yml \
	ansible/playbooks/install_lab.yml \
	-e @ansible/inventories/sgif-lab.vault.yml \
	--ask-vault-pass
```

The role refuses to run unless `sgif_stack_enable` is true, the target is
Ubuntu 22.04 or newer, and all four passwords are long, distinct, alphanumeric
values. Pin `sgif_stack_version` to a reviewed commit or release for repeatable
deployments. The dashboard binds to `127.0.0.1:5173` on the Ubuntu box. Access
it using an SSH tunnel. Forward all three ports needed by the browser; the
installer does not open firewall ports:

```sh
ssh -L 5173:127.0.0.1:5173 \
	-L 8000:127.0.0.1:8000 \
	-L 8080:127.0.0.1:8080 \
	operator@ubuntu-lab
```

The example inventory remains empty and no real host or secrets belong in
this repository.

For a disposable local lab instead of an Ubuntu host, copy `.env.example` to
`.env`, replace every placeholder with a distinct random alphanumeric secret,
then run `docker compose up --build`. See [the deployment guide](../deployment/README.md).

Hardening roles are disabled by default. To preview one role, first set its
role-prefixed `*_enable` variable in a protected local vars file, then use Ansible
check mode and review the diff. Check mode cannot guarantee that every module
is non-mutating or predict the full result. SSH and firewall roles can lock
you out; require confirmed key-based access, console recovery, and a tested
rollback before enabling them.

The application and database hardening roles remain placeholders and fail
with an explanation if enabled. The lab installer deploys the application
stack with Compose but does not install Wazuh/Suricata/Zeek, capture network
traffic, or configure network isolation.