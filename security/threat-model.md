# Threat Model

## Purpose

SGIF aims to help small renewable-energy site operators organize defensive
cybersecurity work. The current framework consists of static inventory checks,
offline normalization of exported Wazuh/Suricata/Zeek records, and opt-in
configuration examples for ordinary support servers.

## In scope

- Validating a manually maintained JSON asset inventory.
- Normalizing local, exported Wazuh alerts, Suricata EVE, and Zeek `conn.log`
  JSON files.
- Demonstrating conservative host-hardening patterns for Debian/Ubuntu
  support servers.
- Reviewing code and synthetic test data in CI without site connectivity.

## Out of scope

- Asset discovery by probing networks or communicating with equipment.
- Live network monitoring, alert correlation, incident verdicts, or automated
  isolation actions.
- Exploiting, bypassing, or stress-testing site devices or services.
- Sending commands to inverters, turbines, protection relays, controllers, or
  other OT.
- Automated incident response or changes to production OT configurations.
- Storing secrets or real site-specific operational data in this repository.

## Threats and mitigations

- **Accidental disclosure:** real inventories, secrets, and host-specific
  files are excluded or ignored; published examples must remain fictional.
- **Sensitive event data:** exported network logs may disclose site topology;
  keep real logs outside the public repository and access-controlled.
- **Administrative lockout or outage:** roles default to disabled, target only
  the `support_servers` group, and require operator review, recovery access,
  and a staged rollout.
- **Misapplied controls:** examples are OS-specific and require local review;
  successful execution is not a compliance or safety claim.
- **Scope creep into OT:** project docs and workflows prohibit OT targets;
  future capabilities require a new threat and safety review.

## Assumptions

Operators are responsible for authorization, host classification, maintenance
windows, and recovery. The attached technical reference must be made available
in a readable form before its requirements can be incorporated.
