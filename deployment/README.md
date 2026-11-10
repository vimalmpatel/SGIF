# SGIF Lab Deployment

This profile runs the SGIF management application on a dedicated Ubuntu
22.04+ support box using Docker Compose:

- PostgreSQL stores assets, normalized events, and application audit records.
- Keycloak provides local lab sign-in and reader/operator/admin roles.
- FastAPI validates Keycloak access tokens and applies role-based access.
- React provides the browser dashboard and imports exported JSONL files.

It does **not** install Wazuh, Suricata, or Zeek; capture live network traffic;
make incident verdicts; or enforce network isolation. It is not a production
deployment and must not be exposed directly to an OT network or the Internet.

## Local disposable stack

Copy `.env.example` to `.env` and replace every placeholder with a different,
long random alphanumeric value. Keep `.env` private; it is ignored by Git. Then
run from the repository root:

```sh
docker compose up --build
```

Open `http://localhost:5173`. Keycloak is at `http://localhost:8080`; API
health is `http://localhost:8000/healthz`. For a disposable lab, create a
Keycloak user in the `sgif-lab` realm and assign one realm role:
`sgif_reader`, `sgif_operator`, or `sgif_admin`.

All published ports bind to localhost. To reach the UI on a remote Ubuntu box,
use an SSH tunnel, for example:

```sh
ssh -L 5173:127.0.0.1:5173 \
	-L 8000:127.0.0.1:8000 \
	-L 8080:127.0.0.1:8080 \
	operator@ubuntu-lab
```

These three forwards are required for the browser to reach the dashboard, API,
and Keycloak. Do not change Compose bindings to `0.0.0.0` without
designing TLS, ingress controls, and an approved network boundary.

Stop without deleting data using `docker compose down`. The lab database
persists in a Docker volume. `docker compose down -v` permanently deletes that
volume and is only suitable for a disposable lab.

## Ubuntu installation

For a dedicated Ubuntu 22.04+ host, use the opt-in Ansible installer and
Ansible Vault instructions in [the Ansible guide](../ansible/README.md). The
installer installs Docker Engine, checks out a reviewed SGIF revision, writes
distinct service credentials with restrictive file permissions, and starts
the Compose profile. It does not configure site firewalls or OT equipment.

## Before production

Production use requires, at minimum, TLS and an approved ingress design,
Keycloak production mode and lifecycle, secret rotation, PostgreSQL backup and
restore tests, schema migrations, resource sizing, monitoring, patching, and a
site-specific security and safety review. Current schema creation is intended
for a fresh lab database only.