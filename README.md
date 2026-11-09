# SGIF

SGIF is an open-source starting point for improving the cybersecurity
readiness of small solar, wind, and distributed-energy sites. The Ansible
examples in this repository are for **Debian/Ubuntu support servers only**.
They are not for inverters, turbines, protection relays, controllers, or other
operational technology (OT).

The repository includes a local asset inventory validator and opt-in Ansible
roles. The validator reads a local file only. Ansible roles make changes only
when explicitly enabled and should first be reviewed and tested on a
non-production support server.

## Quick start

Requires Python 3.10 or newer. From the repository root, run:

```sh
python sgif_inventory.py examples/site-inventory.json
```

The command exits with status `0` for a valid inventory and `1` for invalid
data. Run the tests with:

```sh
python -m unittest discover -s tests -v
```

## Ansible

Requires a supported Ansible installation and an operator-managed inventory.
The committed example inventory has no hosts. It is intentionally not a
production inventory. Review [the Ansible guide](ansible/README.md) before
using any role. All role enable flags default to `false`.

Check playbook syntax without connecting to a host:

```sh
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventories/example.yml ansible/playbooks/site.yml --syntax-check
```

Do not run a mutating playbook against production without an approved change
plan, tested backup and recovery procedure, console access, and a reviewed
host-specific inventory. No playbook in this repo should target OT networks.

## Inventory format

The top-level JSON object contains an `assets` array. Every asset needs a
unique `asset_id`, `name`, `asset_type`, `zone`, `criticality`, and
`owner`. See [the example inventory](examples/site-inventory.json).

Use role names rather than personal contact details. Do not commit real site
inventories, credentials, network diagrams, or other sensitive operational
details to a public repository. Keep those files in an appropriately
controlled local system.

## Project boundaries

This repository is an early defensive framework, not a certified security
product or a substitute for qualified engineering, operational safety
procedures, or applicable standards. Security controls are examples that need
site-specific review; they are not a compliance guarantee.

The CI workflows run unit tests, inventory validation, Ansible syntax checks,
Ansible linting, and CodeQL analysis. The manually triggered deployment
workflow is a syntax preflight only: it does not connect to or configure
servers.

See [the security architecture](security/architecture.md),
[the threat model](security/threat-model.md), and
[the security checklist](security/security-checklist.md) for the current
design boundaries and planned safeguards.
