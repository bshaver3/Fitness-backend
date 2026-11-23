import json
import os
import unittest
from unittest.mock import patch

os.environ["LOCAL_MOCK"] = "true"

from fastapi.testclient import TestClient
from pydantic import ValidationError

import main

GYM_EXPERIENCE_VALUES = [
    "beginner",
    "novice",
    "intermediate",
    "advanced",
    "expert",
]


class InMemoryProfileTable:
    def __init__(self):
        self.item = None

    def put_item(self, Item):
        self.item = Item


class ProfileContractTests(unittest.TestCase):
    def test_profile_accepts_supported_gym_experience_values(self):
        for value in GYM_EXPERIENCE_VALUES:
            with self.subTest(gym_experience=value):
                profile = main.Profile(gym_experience=value)
                self.assertEqual(profile.gym_experience, value)

    def test_profile_rejects_unsupported_gym_experience_value(self):
        with self.assertRaises(ValidationError):
            main.Profile(gym_experience="professional")

    def test_profile_openapi_documents_gym_experience_enum(self):
        schema = main.app.openapi()["components"]["schemas"]["Profile"]
        property_schema = schema["properties"]["gym_experience"]
        values = next(
            option["enum"] for option in property_schema["anyOf"] if "enum" in option
        )
        self.assertEqual(values, GYM_EXPERIENCE_VALUES)

    def test_profile_endpoint_saves_expert_experience(self):
        profile_table = InMemoryProfileTable()
        client = TestClient(main.app)
        with patch.object(main, "profile_table", profile_table):
            response = client.post(
                "/profile",
                json={"gym_experience": "expert", "user_id": "untrusted"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["gym_experience"], "expert")
        self.assertEqual(response.json()["user_id"], "local-dev-user")
        self.assertEqual(profile_table.item["gym_experience"], "expert")

    def test_committed_openapi_matches_fastapi_schema(self):
        with open("openapi.json", encoding="utf-8") as schema_file:
            committed_schema = json.load(schema_file)
        self.assertEqual(
            main.app.openapi()["components"]["schemas"]["Profile"],
            committed_schema["components"]["schemas"]["Profile"],
        )


if __name__ == "__main__":
    unittest.main()
