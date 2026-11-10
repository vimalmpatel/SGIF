# SGIF Implementation Guide

This guide installs the current SGIF management lab on a dedicated Ubuntu
small server. It does not install live OT monitoring sensors or enable network
isolation.

## What is installed

| Service | Purpose | Ubuntu host binding |
| --- | --- | --- |
| React dashboard + unprivileged Nginx | Operator UI | `127.0.0.1:5173` |
| FastAPI | Asset/event API and role checks | `127.0.0.1:8000` |
| PostgreSQL | Assets, imported events, audit rows | `127.0.0.1:5432` |
| Keycloak | OIDC login and SGIF roles | `127.0.0.1:8080` |

Wazuh, Suricata, and Zeek are not installed. They are supported only as
operator-exported JSONL inputs. The app does not capture packets, make an
incident verdict, or send commands to grid equipment.

## Target prerequisites

- Ubuntu Server 22.04 or newer, x86_64/AMD64 or ARM64.
- Dedicated support/lab host; never add an inverter, relay, PLC, BESS
  controller, turbine controller, or SCADA host to the Ansible target group.
- SSH account with sudo/become permission and a verified recovery path.
- Ansible Core 2.15+ on the controller and the collections in
  `ansible/requirements.yml`.
- Outbound HTTPS access for apt, GitHub, Docker Hub, and Quay image pulls.
- CPU, memory, and storage sized for expected user/event load. SGIF has not
  benchmarked minimum box requirements yet.

The Ubuntu installer does not open firewall ports. Compose services bind to
loopback. Remote access uses SSH forwarding; do not expose the HTTP ports on a
premise or OT network.

## 1. Prepare the controller

Clone the repository at a reviewed release or commit. Install the pinned
Ansible collections:

```sh
ansible-galaxy collection install -r ansible/requirements.yml
```

Create an untracked `ansible/inventories/local.yml` containing only your
authorized Ubuntu lab host:

```yaml
all:
  children:
    sgif_lab_servers:
      hosts:
        sgif-ubuntu-lab:
          ansible_host: <Ubuntu management address>
          ansible_user: <SSH account with sudo>
```

Keep real hostnames, management addresses, SSH private keys, and site
inventories out of this public repository.

## 2. Create encrypted secrets

Create an Ansible Vault file:

```sh
ansible-vault create ansible/inventories/sgif-lab.vault.yml
```

Add four distinct random alphanumeric passwords of at least 32 characters:

```yaml
sgif_stack_enable: true
sgif_stack_postgres_password: "<random secret 1>"
sgif_stack_app_db_password: "<random secret 2>"
sgif_stack_keycloak_db_password: "<random secret 3>"
sgif_stack_keycloak_admin_password: "<random secret 4>"
```

The installer validates these values and writes them to `/opt/sgif/.env`
with mode `0600`. Never place real passwords in an inventory, Git, a shell
command, or this guide.

## 3. Review and install

Syntax-check locally; this does not contact a host:

```sh
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook \
  -i ansible/inventories/example.yml \
  ansible/playbooks/install_lab.yml --syntax-check
```

Confirm the inventory contains only the dedicated Ubuntu host and recovery
access is ready. Set `sgif_stack_version` to a reviewed commit or release in
the encrypted vars file, then run:

```sh
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook \
  -i ansible/inventories/local.yml \
  ansible/playbooks/install_lab.yml \
  -e @ansible/inventories/sgif-lab.vault.yml \
  --ask-vault-pass
```

The playbook refuses to proceed unless `sgif_stack_enable` is true, the target
is in `sgif_lab_servers`, and gathered facts identify Ubuntu 22.04+ on a
supported architecture. It installs Docker/Compose, checks out the requested
revision, writes `.env`, builds the images, and starts the lab stack.

## 4. Sign in

Forward all dashboard dependencies from your workstation:

```sh
ssh -L 5173:127.0.0.1:5173 \
  -L 8000:127.0.0.1:8000 \
  -L 8080:127.0.0.1:8080 \
  <SSH account>@<Ubuntu management address>
```

Open `http://localhost:5173`. The imported `sgif-lab` Keycloak realm defines
the `sgif-web` PKCE client, `sgif-api` audience, and reader/operator/admin
roles. It does not create users. Open `http://localhost:8080/admin`, sign in
using the bootstrap admin from Vault, create an account, and assign only the
needed role:

- `sgif_reader`: view assets and events.
- `sgif_operator`: reader access, create assets, and import events.
- `sgif_admin`: operator access and reserved admin role.

The API validates RS256 signature, issuer, `sgif-api` audience, expiry,
subject, and role claims.

## 5. Import event data

Use synthetic files during initial verification. An operator selects Wazuh,
Suricata EVE, or Zeek JSONL in the dashboard and uploads an exported file. The
API accepts at most 1 MB / 1,000 records, validates timestamps, addresses,
ports, and source fields, stores normalized records, skips content duplicates,
and writes an audit record.

Real event logs may expose addresses, hosts, or communication patterns. Keep
them on an approved, access-controlled system and never commit them to this
public repository.

## 6. Verify and operate

On the Ubuntu host:

```sh
cd /opt/sgif
docker compose ps
docker compose logs --tail=100 database identity api web
curl --fail http://127.0.0.1:8000/healthz
```

Health confirms database connectivity only, not sensor state or security
posture. Plan disk retention, patching, and tested database backup/restore
before retaining site data.

Stop without deleting the database volume:

```sh
docker compose down
```

`docker compose down -v` permanently deletes lab data; use it only to reset a
disposable environment. PostgreSQL initialization scripts run only when the
data volume is first created.

## Troubleshooting

- **Installer rejects host:** verify Ubuntu 22.04+, architecture,
  `sgif_lab_servers`, sudo access, and `sgif_stack_enable: true`.
- **Secret assertion fails:** use four distinct alphanumeric passwords of at
  least 32 characters in the encrypted Vault file.
- **Image pull/build fails:** verify DNS, outbound HTTPS, disk space, and
  access to Docker Hub, Quay, GitHub, and Ubuntu repositories.
- **Login loop / invalid token:** check all three SSH forwards, local clock,
  realm import, `OIDC_ISSUER`, `OIDC_AUDIENCE`, and the realm's API audience
  mapper.
- **API returns 403:** assign the appropriate realm role and sign in again to
  receive a token with the updated role claim.
- **Database does not initialize:** inspect database logs. Initialization
  runs only for an empty volume; never delete a non-disposable database to
  force reinitialization.

## Production gaps

This is a lab deployment, not a production distribution. Production use still
requires TLS/ingress, Keycloak production configuration, secret rotation,
migrations, backup/restore drills, resource/load testing, monitoring, image
digest updates, and a site-specific security/safety review. Future response
must be human-approved, tested, and reversible. Automatic OT control remains
out of scope.
