# Architecture

## Components

- `application/`: reserved for operator-facing application code; no web
  service or deployment target is defined yet.
- `sgif_inventory.py`: offline validation of a JSON asset register.
- `ansible/`: opt-in configuration examples for Debian/Ubuntu support servers.
- `security/`: security boundaries, threat model, policy, and review checklist.
- `.github/workflows/`: test, static-analysis, and manual preflight automation.

## Trust boundaries

1. The repository and CI contain public code and synthetic example data.
2. Operators maintain real site inventories and Ansible inventories outside
   the public repository.
3. Ansible, when intentionally enabled by an operator, crosses into a
   support-server administration boundary. It must not cross into OT.

CI does not receive site credentials or contact hosts. The current deploy
workflow only performs a playbook syntax check.

## Future decisions

Before adding an application or remote deployment, define the user roles,
data sensitivity, authentication, update lifecycle, supported operating
systems, target boundaries, recovery process, and security review approach.