import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import jwt

from fastapi.testclient import TestClient

from application.api import Principal, create_app, current_principal


class ApiTests(unittest.TestCase):
    def make_client(self, roles: set[str] | None = None) -> TestClient:
        app = create_app("sqlite://")
        if roles is not None:
            app.dependency_overrides[current_principal] = lambda: Principal(subject="test-user", roles=roles)
        return TestClient(app)

    def test_health_checks_database(self):
        with self.make_client() as client:
            response = client.get("/healthz")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_api_requires_bearer_token(self):
        with self.make_client() as client:
            response = client.get("/api/v1/assets")

        self.assertEqual(response.status_code, 401)

    def test_api_validates_keycloak_signed_token(self):
        app = create_app("sqlite://")
        app.state.jwks_client.get_signing_key_from_jwt = lambda _: SimpleNamespace(key="test-public-key")
        claims = {
            "iss": app.state.oidc_issuer,
            "aud": app.state.oidc_audience,
            "sub": "lab-reader",
            "realm_access": {"roles": ["sgif_reader"]},
        }

        with patch("application.api.jwt.decode", return_value=claims) as decode:
            with TestClient(app) as client:
                valid_response = client.get("/api/v1/assets", headers={"Authorization": "Bearer test-token"})

        with patch("application.api.jwt.decode", side_effect=jwt.InvalidTokenError("bad audience")):
            with TestClient(app) as client:
                rejected_response = client.get("/api/v1/assets", headers={"Authorization": "Bearer test-token"})

        self.assertEqual(valid_response.status_code, 200)
        self.assertEqual(rejected_response.status_code, 401)
        self.assertEqual(decode.call_args.kwargs["algorithms"], ["RS256"])
        self.assertEqual(decode.call_args.kwargs["audience"], "sgif-api")
        self.assertEqual(decode.call_args.kwargs["issuer"], "http://localhost:8080/realms/sgif-lab")

    def test_reader_can_list_but_cannot_create_assets(self):
        with self.make_client({"sgif_reader"}) as client:
            list_response = client.get("/api/v1/assets")
            create_response = client.post(
                "/api/v1/assets",
                json={
                    "asset_id": "LAB-001",
                    "name": "Synthetic asset",
                    "asset_type": "sensor",
                    "zone": "lab",
                    "criticality": "low",
                    "owner": "lab-operator",
                },
            )

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(create_response.status_code, 403)

    def test_operator_creates_asset(self):
        with self.make_client({"sgif_operator"}) as client:
            response = client.post(
                "/api/v1/assets",
                json={
                    "asset_id": "LAB-001",
                    "name": "Synthetic asset",
                    "asset_type": "sensor",
                    "zone": "lab",
                    "criticality": "low",
                    "owner": "lab-operator",
                },
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {"asset_id": "LAB-001"})

    def test_operator_imports_events_idempotently(self):
        event = {
            "timestamp": "2026-11-09T12:30:00Z",
            "event_type": "alert",
            "src_ip": "192.0.2.10",
            "dest_ip": "198.51.100.20",
            "alert": {"signature": "Synthetic lab finding", "severity": 1},
        }
        payload = {"source": "suricata", "content": json.dumps(event)}

        with self.make_client({"sgif_operator"}) as client:
            first_import = client.post("/api/v1/events/import", json=payload)
            repeated_import = client.post("/api/v1/events/import", json=payload)
            event_list = client.get("/api/v1/events")

        self.assertEqual(first_import.status_code, 201)
        self.assertEqual(first_import.json(), {"accepted": 1, "duplicates": 0})
        self.assertEqual(repeated_import.json(), {"accepted": 0, "duplicates": 1})
        self.assertEqual(len(event_list.json()), 1)
        self.assertEqual(event_list.json()[0]["summary"], "Synthetic lab finding")


if __name__ == "__main__":
    unittest.main()