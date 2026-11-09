# Architecture

## Components

- `application/`: reserved for operator-facing application code; no web
  service or deployment target is defined yet.
- `sgif_inventory.py`: offline validation of a JSON asset register.
- `application/event_ingest.py`: offline normalization of exported Wazuh,
   Suricata EVE, and Zeek `conn.log` JSON into a common event record.
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

The event normalizer reads local files only. It is not a network sensor, alert
correlator, incident verdict engine, or isolation controller. Real event logs
remain operator-controlled and must not be committed to this public repo.

## Future decisions

Before adding an API or remote deployment, define the user roles, data
sensitivity, authentication, update lifecycle, supported operating systems,
target boundaries, recovery process, and security review approach. Initial
sensor integration should be passive and lab-only. Any future isolation
workflow must require explicit human approval and a documented safety review;
automatic control of BESS, SCADA, or other OT is out of scope.
