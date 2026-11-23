import os
import unittest
from unittest.mock import patch

os.environ["LOCAL_MOCK"] = "true"

from fastapi.testclient import TestClient

import main


class InMemoryFoodEntryTable:
    def __init__(self, items=None, error=None):
        self.items = items or []
        self.error = error

    def scan(self, FilterExpression=None, ExpressionAttributeValues=None):
        if self.error:
            raise self.error
        user_id = (ExpressionAttributeValues or {}).get(":uid")
        items = [item for item in self.items if item.get("user_id") == user_id]
        return {"Items": items}


class InMemoryProfileTable:
    def __init__(self, item=None):
        self.item = item

    def get_item(self, Key):
        return {"Item": self.item} if self.item else {}


class DailyFoodEntriesContractTests(unittest.TestCase):
    def test_empty_authenticated_day_returns_valid_summary(self):
        food_table = InMemoryFoodEntryTable()
        profile_table = InMemoryProfileTable({"daily_calorie_target": 1800})
        client = TestClient(main.app)

        with (
            patch.object(main, "food_entries_table", food_table),
            patch.object(main, "profile_table", profile_table),
        ):
            response = client.get(
                "/food-entries/daily",
                params={"date": "2026-11-23"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "date": "2026-11-23",
                "entries": [],
                "total_calories": 0,
                "target_calories": 1800,
                "remaining_calories": 1800,
                "over_target_calories": None,
                "status": "remaining",
            },
        )

    def test_empty_day_excludes_other_users_entries(self):
        food_table = InMemoryFoodEntryTable(
            [
                {
                    "id": "foreign-entry",
                    "user_id": "other-user",
                    "name": "Other user's food",
                    "calories": 500,
                    "date": "2026-11-23",
                }
            ]
        )
        profile_table = InMemoryProfileTable({"daily_calorie_target": None})
        client = TestClient(main.app)

        with (
            patch.object(main, "food_entries_table", food_table),
            patch.object(main, "profile_table", profile_table),
        ):
            response = client.get(
                "/food-entries/daily",
                params={"date": "2026-11-23"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["entries"], [])
        self.assertEqual(response.json()["total_calories"], 0)

    def test_unexpected_food_table_error_remains_http_500(self):
        food_table = InMemoryFoodEntryTable(error=RuntimeError("DynamoDB unavailable"))
        profile_table = InMemoryProfileTable({"daily_calorie_target": 1800})
        client = TestClient(main.app, raise_server_exceptions=False)

        with (
            patch.object(main, "food_entries_table", food_table),
            patch.object(main, "profile_table", profile_table),
        ):
            response = client.get(
                "/food-entries/daily",
                params={"date": "2026-11-23"},
            )

        self.assertEqual(response.status_code, 500)

    def test_committed_openapi_matches_fastapi_app(self):
        import json

        with open("openapi.json", encoding="utf-8") as schema_file:
            committed_schema = json.load(schema_file)
        self.assertEqual(committed_schema, main.app.openapi())


if __name__ == "__main__":
    unittest.main()
