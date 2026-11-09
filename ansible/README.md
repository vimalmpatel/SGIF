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

Roles are disabled by default. To preview one role, first set its
`sgif_enable_*` variable in a protected local vars file, then use Ansible
check mode and review the diff. Check mode cannot guarantee that every module
is non-mutating or predict the full result. SSH and firewall roles can lock
you out; require confirmed key-based access, console recovery, and a tested
rollback before enabling them.

The application and database roles intentionally fail with an explanation if
enabled: no application or database stack has been selected yet.