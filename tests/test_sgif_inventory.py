import unittest

from sgif_inventory import validate_inventory


class ValidateInventoryTests(unittest.TestCase):
    def test_accepts_valid_inventory(self):
        data = {
            "assets": [
                {
                    "asset_id": "EX-001",
                    "name": "Example inverter",
                    "asset_type": "inverter",
                    "zone": "generation",
                    "criticality": "high",
                    "owner": "site-operations",
                }
            ]
        }

        self.assertEqual(validate_inventory(data), [])

    def test_rejects_duplicate_asset_ids(self):
        asset = {
            "asset_id": "EX-001",
            "name": "Example inverter",
            "asset_type": "inverter",
            "zone": "generation",
            "criticality": "high",
            "owner": "site-operations",
        }

        errors = validate_inventory({"assets": [asset, asset]})

        self.assertIn("assets[1].asset_id duplicates 'EX-001'", errors)

    def test_rejects_invalid_top_level_and_criticality(self):
        self.assertEqual(validate_inventory([]), ["top level must be a JSON object"])
        data = {
            "assets": [
                {
                    "asset_id": "EX-001",
                    "name": "Example inverter",
                    "asset_type": "inverter",
                    "zone": "generation",
                    "criticality": "urgent",
                    "owner": "site-operations",
                }
            ]
        }

        self.assertTrue(any("criticality must be one of" in error for error in validate_inventory(data)))


if __name__ == "__main__":
    unittest.main()