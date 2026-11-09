"""Normalize exported Wazuh, Suricata, and Zeek JSON records offline."""

import argparse
import ipaddress
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, TextIO


SURICATA_SEVERITIES = {1: "high", 2: "medium", 3: "low"}


def _wazuh_severity(level: Any) -> str:
    if isinstance(level, bool) or not isinstance(level, int) or not 0 <= level <= 15:
        raise ValueError("Wazuh rule.level must be an integer from 0 to 15")
    if level <= 3:
        return "info"
    if level <= 7:
        return "low"
    if level <= 11:
        return "medium"
    if level <= 14:
        return "high"
    return "critical"


def _normalize_timestamp(value: Any, source: str) -> str:
    if source in {"suricata", "wazuh"}:
        if not isinstance(value, str):
            raise ValueError(f"{source.capitalize()} timestamp must be a string")
        normalized_value = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            timestamp = datetime.fromisoformat(normalized_value)
        except ValueError as error:
            raise ValueError(f"{source.capitalize()} timestamp must be ISO 8601") from error
        if timestamp.tzinfo is None:
            raise ValueError(f"{source.capitalize()} timestamp must include a timezone")
    elif source == "zeek":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Zeek ts must be a Unix timestamp number")
        try:
            timestamp_is_finite = math.isfinite(value)
        except OverflowError as error:
            raise ValueError("Zeek ts is outside the supported range") from error
        if not timestamp_is_finite:
            raise ValueError("Zeek ts must be finite")
        try:
            timestamp = datetime.fromtimestamp(value, tz=timezone.utc)
        except (OverflowError, OSError, ValueError) as error:
            raise ValueError("Zeek ts is outside the supported range") from error

    return timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _optional_ip(record: dict[str, Any], field: str) -> str | None:
    value = record.get(field)
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an IP address string")
    try:
        return str(ipaddress.ip_address(value))
    except ValueError as error:
        raise ValueError(f"{field} is not a valid IP address") from error


def _optional_port(record: dict[str, Any], field: str) -> int | None:
    value = record.get(field)
    if value is None or value == "":
        return None
    if isinstance(value, str) and value.isdecimal():
        value = int(value)
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 65535:
        raise ValueError(f"{field} must be an integer from 0 to 65535")
    return value


def normalize_event(record: Any, source: str) -> dict[str, Any]:
    """Normalize one exported Wazuh, Suricata EVE, or Zeek conn.log object."""
    if not isinstance(source, str) or source not in ("wazuh", "suricata", "zeek"):
        raise ValueError("source must be 'wazuh', 'suricata', or 'zeek'")
    if not isinstance(record, dict):
        raise ValueError("record must be a JSON object")

    if source == "suricata":
        event_type = record.get("event_type")
        if not isinstance(event_type, str) or not event_type.strip():
            raise ValueError("Suricata event_type must be a non-empty string")
        observed_at = _normalize_timestamp(record.get("timestamp"), source)
        alert = record.get("alert", {})
        if not isinstance(alert, dict):
            raise ValueError("Suricata alert must be a JSON object")
        signature = alert.get("signature")
        summary = signature.strip() if isinstance(signature, str) and signature.strip() else event_type
        severity_value = alert.get("severity")
        severity = (
            SURICATA_SEVERITIES.get(severity_value, "info")
            if isinstance(severity_value, int) and not isinstance(severity_value, bool)
            else "info"
        )
        source_ip = _optional_ip(record, "src_ip")
        destination_ip = _optional_ip(record, "dest_ip")
        source_port = _optional_port(record, "src_port")
        destination_port = _optional_port(record, "dest_port")
        protocol = record.get("proto")
        sensor = None
    elif source == "zeek":
        observed_at = _normalize_timestamp(record.get("ts"), source)
        event_type = "connection"
        summary = "Zeek connection observed"
        severity = "info"
        source_ip = _optional_ip(record, "id.orig_h")
        destination_ip = _optional_ip(record, "id.resp_h")
        source_port = _optional_port(record, "id.orig_p")
        destination_port = _optional_port(record, "id.resp_p")
        protocol = record.get("proto")
        sensor = None
    else:
        observed_at = _normalize_timestamp(record.get("timestamp"), source)
        rule = record.get("rule")
        if not isinstance(rule, dict):
            raise ValueError("Wazuh rule must be a JSON object")
        summary = rule.get("description")
        if not isinstance(summary, str) or not summary.strip():
            raise ValueError("Wazuh rule.description must be a non-empty string")
        severity = _wazuh_severity(rule.get("level"))
        agent = record.get("agent", {})
        if not isinstance(agent, dict):
            raise ValueError("Wazuh agent must be a JSON object")
        sensor = agent.get("name")
        if sensor is not None and not isinstance(sensor, str):
            raise ValueError("Wazuh agent.name must be a string")
        data = record.get("data", {})
        if not isinstance(data, dict):
            raise ValueError("Wazuh data must be a JSON object")
        event_type = "alert"
        source_ip = _optional_ip({"src_ip": data.get("srcip")}, "src_ip")
        destination_ip = _optional_ip({"dest_ip": data.get("dstip")}, "dest_ip")
        source_port = _optional_port({"src_port": data.get("srcport")}, "src_port")
        destination_port = _optional_port({"dest_port": data.get("dstport")}, "dest_port")
        protocol = data.get("protocol")

    if protocol is not None and not isinstance(protocol, str):
        raise ValueError("proto must be a string")

    return {
        "schema_version": 1,
        "source": source,
        "observed_at": observed_at,
        "event_type": event_type,
        "severity": severity,
        "summary": summary,
        "sensor": sensor,
        "src_ip": source_ip,
        "src_port": source_port,
        "dest_ip": destination_ip,
        "dest_port": destination_port,
        "protocol": protocol.lower() if protocol else None,
    }


def iter_normalized_events(lines: Iterable[str], source: str) -> Iterator[dict[str, Any]]:
    """Yield normalized events from newline-delimited JSON, with line context."""
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            yield normalize_event(record, source)
        except (json.JSONDecodeError, ValueError) as error:
            raise ValueError(f"line {line_number}: {error}") from error


def convert_jsonl(input_stream: TextIO, output_stream: TextIO, source: str) -> int:
    """Write normalized JSONL records and return the number converted."""
    count = 0
    for event in iter_normalized_events(input_stream, source):
        output_stream.write(json.dumps(event, separators=(",", ":")) + "\n")
        count += 1
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Normalize exported network events offline")
    parser.add_argument("source", choices=("wazuh", "suricata", "zeek"), help="input format")
    parser.add_argument("input", type=Path, help="newline-delimited JSON input file")
    args = parser.parse_args(argv)

    try:
        with args.input.open(encoding="utf-8") as input_stream:
            count = convert_jsonl(input_stream, sys.stdout, args.source)
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"Normalized {count} event(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
