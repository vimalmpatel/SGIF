# Scope and Threat Model

## Purpose

SGIF aims to help small renewable-energy site operators organize defensive
cybersecurity work for solar, wind, and related grid-connected systems. The
current repository includes offline inventory validation and opt-in Ansible
examples for Debian/Ubuntu support servers only.

## In scope for this starter

- Validating a manually maintained JSON asset inventory.
- Helping operators identify missing or inconsistent inventory fields.
- Demonstrating opt-in host-hardening controls for support servers.
- Using fictional data in public examples and tests.

## Out of scope

- Discovering assets by probing networks or communicating with equipment.
- Exploiting, bypassing, or stress-testing site devices or services.
- Sending commands to inverters, turbines, protection relays, controllers, or
  other operational technology.
- Managing or changing production OT configurations or providing autonomous
  response actions.
- Storing secrets or real site-specific operational data in this public repo.

## Assumptions and risks

- Users may mistakenly publish sensitive topology, equipment, or ownership
  details. Public examples must remain synthetic, and real inventories should
  stay in access-controlled storage.
- Inventory completeness depends on the operator; a valid file does not prove
  that it describes the real site accurately or securely.
- SSH, firewall, and host-hardening changes can interrupt support services or
  lock out administrators. Roles are disabled by default and require local
  review, recovery access, and a tested rollback before use.
- A tool that communicates with operational systems can create safety and
  availability risks. Such capabilities require a separate threat review,
  explicit authorization model, and qualified operator oversight before being
  considered.

## Before expanding scope

The technical reference document must be available in a readable form and
reviewed with the intended operator workflow, deployment assumptions, and
applicable safety and regulatory requirements. Future changes should document
their trust boundaries, data handling, failure behavior, and safe test method.