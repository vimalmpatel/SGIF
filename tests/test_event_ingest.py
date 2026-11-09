import io
import json
import unittest

from application.event_ingest import convert_jsonl, iter_normalized_events, normalize_event


class NormalizeEventTests(unittest.TestCase):
    def test_normalizes_suricata_alert(self):
        record = {
            "timestamp": "2026-11-09T12:30:00-05:00",
            "event_type": "alert",
            "src_ip": "192.0.2.10",
            "src_port": 45678,
            "dest_ip": "198.51.100.20",
            "dest_port": 443,
            "proto": "TCP",
            "alert": {"signature": "Synthetic test alert", "severity": 2},
        }

        event = normalize_event(record, "suricata")

        self.assertEqual(event["observed_at"], "2026-11-09T17:30:00Z")
        self.assertEqual(event["severity"], "medium")
        self.assertEqual(event["summary"], "Synthetic test alert")
        self.assertEqual(event["protocol"], "tcp")

    def test_normalizes_zeek_connection(self):
        event = normalize_event(
            {
                "ts": 1794245400.0,
                "id.orig_h": "192.0.2.11",
                "id.orig_p": 53000,
                "id.resp_h": "198.51.100.21",
                "id.resp_p": 53,
                "proto": "udp",
            },
            "zeek",
        )

        self.assertEqual(event["source"], "zeek")
        self.assertEqual(event["event_type"], "connection")
        self.assertEqual(event["severity"], "info")
        self.assertEqual(event["dest_port"], 53)

    def test_normalizes_wazuh_alert(self):
        event = normalize_event(
            {
                "timestamp": "2026-11-09T12:30:00Z",
                "rule": {"level": 13, "description": "Synthetic lab finding"},
                "agent": {"name": "lab-endpoint"},
                "data": {"srcip": "192.0.2.12", "dstport": "443", "protocol": "TCP"},
            },
            "wazuh",
        )

        self.assertEqual(event["source"], "wazuh")
        self.assertEqual(event["severity"], "high")
        self.assertEqual(event["sensor"], "lab-endpoint")
        self.assertEqual(event["dest_port"], 443)
        self.assertEqual(event["protocol"], "tcp")

    def test_rejects_invalid_addresses_and_timestamps(self):
        with self.assertRaisesRegex(ValueError, "src_ip"):
            normalize_event(
                {"timestamp": "2026-11-09T12:00:00Z", "event_type": "flow", "src_ip": "not-an-ip"},
                "suricata",
            )
        with self.assertRaisesRegex(ValueError, "Zeek ts"):
            normalize_event({"ts": True}, "zeek")
        with self.assertRaisesRegex(ValueError, "Zeek ts"):
            normalize_event({"ts": 10**10000}, "zeek")
        with self.assertRaisesRegex(ValueError, "Wazuh rule.level"):
            normalize_event(
                {"timestamp": "2026-11-09T12:00:00Z", "rule": {"level": 16, "description": "bad"}},
                "wazuh",
            )
        with self.assertRaisesRegex(ValueError, "source must be"):
            normalize_event({}, [])

    def test_reports_jsonl_line_number(self):
        valid_record = json.dumps({"timestamp": "2026-11-09T12:00:00Z", "event_type": "flow"})
        with self.assertRaisesRegex(ValueError, "line 2"):
            list(iter_normalized_events([valid_record + "\n", "not-json\n"], "suricata"))

    def test_converts_jsonl_to_normalized_jsonl(self):
        input_stream = io.StringIO(
            json.dumps({"timestamp": "2026-11-09T12:00:00Z", "event_type": "flow"}) + "\n"
        )
        output_stream = io.StringIO()

        count = convert_jsonl(input_stream, output_stream, "suricata")

        self.assertEqual(count, 1)
        self.assertEqual(json.loads(output_stream.getvalue())["source"], "suricata")


if __name__ == "__main__":
    unittest.main()
