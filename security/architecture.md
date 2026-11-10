# Architecture

## Components

- `application/api.py`: Keycloak JWT-protected FastAPI API for assets and
   imported events, with role-gated writes and an audit record for mutations.
- `application/web/`: React dashboard using Keycloak Authorization Code + PKCE.
- `docker-compose.yml`: localhost-only lab stack for the web app, API,
   PostgreSQL, and Keycloak.
- `ansible/roles/sgif_stack/`: opt-in Ubuntu 22.04+ Docker/Compose installer.
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

CI does not receive site credentials or contact hosts. The GitHub deployment
workflow only performs syntax checks. The Ansible installer is for an
operator-authorized Ubuntu lab/support server and requires Ansible Vault
secrets.

The event normalizer reads imported files only. It is not a network sensor,
alert correlator, incident verdict engine, or isolation controller. Real event
logs remain operator-controlled and must not be committed to this public repo.
The local lab stack binds to localhost; it uses Keycloak in development HTTP
mode and must not be exposed as-is to a site network or the Internet.

## Future decisions

The API defines reader/operator/admin roles and audit rows for asset/event
mutations. Initial sensor integration should remain passive and lab-only. Any
future isolation workflow must require explicit human approval and a
documented safety review; automatic control of BESS, SCADA, or other OT is out
of scope. Production deployment still needs TLS, schema migrations, secret
rotation, backups, monitoring, and an operator-approved network exposure plan.
