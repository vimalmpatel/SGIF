# Security Checklist

## Before using Ansible

- [ ] Confirm the target is a Debian/Ubuntu support server, not OT equipment.
- [ ] Review the host-specific inventory and confirm it is not committed.
- [ ] Confirm SSH key access and out-of-band recovery before SSH changes.
- [ ] Confirm required application ports before enabling the firewall role.
- [ ] Back up affected configuration and test recovery.
- [ ] Review role variables, check-mode output, and rendered configuration.
- [ ] Apply changes in a maintenance window with an operator available.
- [ ] Verify SSH access, application health, and audit service after changes.

## Before publishing

- [ ] Use fictional examples only.
- [ ] Remove credentials, tokens, private keys, and real site identifiers.
- [ ] Check diffs for topology, IP addresses, hostnames, and personal data.
- [ ] Run unit tests, Ansible syntax checks, and security workflows.
- [ ] Ensure documentation matches the controls actually implemented.