# Application

## Offline event normalizer

`event_ingest` converts newline-delimited JSON exported from Wazuh alerts,
Suricata EVE, or Zeek's JSON `conn.log` into a small common event schema:

```sh
python -m application.event_ingest suricata examples/suricata-eve.sample.jsonl
python -m application.event_ingest zeek examples/zeek-conn.sample.jsonl
python -m application.event_ingest wazuh examples/wazuh-alert.sample.jsonl
```

The input is read from a file and normalized records are written to standard
output. Errors include the input line number. Suricata severity values 1, 2,
and 3 map to high, medium, and low. Wazuh levels 0-3 map to info, 4-7 to low,
8-11 to medium, 12-14 to high, and 15 to critical. Zeek connection records
are informational observations, not alerts. This parser does not perform
threat detection or decide that activity is malicious.

## Safety and data handling

This is an offline development slice. It does not listen for network traffic,
connect to Wazuh, Suricata, or Zeek sensors, scan a site, or perform response or
isolation actions. Only synthetic, documentation-range addresses belong in
public examples. Real logs can reveal sensitive topology and must not be
committed to this public repository.

The FastAPI API, PostgreSQL schema, Keycloak/OIDC role checks, and React
dashboard are included in the lab stack. They bind to localhost and are not a
production deployment. Review [the deployment guide](../deployment/README.md)
before starting the stack. Do not expose it beyond localhost without TLS,
production identity settings, backup/restore, migration, and security review.
