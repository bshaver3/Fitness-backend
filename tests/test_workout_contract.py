import json
import os
import unittest
from unittest.mock import patch

os.environ["LOCAL_MOCK"] = "true"

from fastapi.testclient import TestClient
from pydantic import ValidationError

import main

NEW_WORKOUT_TYPES = [
    "jogging",
    "weight training",
    "crossfit",
    "elliptical",
    "hiking",
]

SUPPORTED_WORKOUT_TYPES = [
    "running",
    "jogging",
    "cycling",
    "swimming",
    "weight training",
    "strength",
    "yoga",
    "hiit",
    "cardio",
    "walking",
    "crossfit",
    "elliptical",
    "hiking",
    "basketball",
    "soccer",
    "tennis",
    "volleyball",
    "dancing",
    "rowing",
    "climbing",
    "boxing",
    "pilates",
    "other",
]


class InMemoryWorkoutTable:
    def __init__(self):
        self.items = []

    def put_item(self, Item):
        self.items.append(Item)


class WorkoutContractTests(unittest.TestCase):
    def test_models_accept_existing_and_new_workout_types(self):
        for value in SUPPORTED_WORKOUT_TYPES:
            with self.subTest(workout_type=value):
                workout = main.Workout(type=value, duration=30, calories=200)
                planned = main.PlannedWorkout(
                    workout_type=value,
                    planned_date="2026-12-01",
                    planned_duration=30,
                )
                self.assertEqual(workout.type, value)
                self.assertEqual(planned.workout_type, value)

    def test_models_preserve_normalization_and_reject_unsupported_value(self):
        workout = main.Workout(type=" Running ", duration=30, calories=200)
        planned = main.PlannedWorkout(
            workout_type=" Weight Training ",
            planned_date="2026-12-01",
            planned_duration=30,
        )
        self.assertEqual(workout.type, "running")
        self.assertEqual(planned.workout_type, "weight training")

        with self.assertRaises(ValidationError):
            main.Workout(type="unsupported sport", duration=30, calories=200)
        with self.assertRaises(ValidationError):
            main.PlannedWorkout(
                workout_type="unsupported sport",
                planned_date="2026-12-01",
                planned_duration=30,
            )

    def test_logged_workout_route_accepts_all_new_types_and_rejects_invalid(self):
        workout_table = InMemoryWorkoutTable()
        client = TestClient(main.app)

        with patch.object(main, "table", workout_table):
            for value in NEW_WORKOUT_TYPES:
                with self.subTest(workout_type=value):
                    response = client.post(
                        "/workouts",
                        json={"type": value, "duration": 30, "calories": 200},
                    )
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()["type"], value)

            invalid = client.post(
                "/workouts",
                json={"type": "unsupported sport", "duration": 30, "calories": 200},
            )

        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(len(workout_table.items), len(NEW_WORKOUT_TYPES))

    def test_planned_workout_route_accepts_all_new_types_and_rejects_invalid(self):
        planned_table = InMemoryWorkoutTable()
        client = TestClient(main.app)

        with patch.object(main, "planned_workouts_table", planned_table):
            for value in NEW_WORKOUT_TYPES:
                with self.subTest(workout_type=value):
                    response = client.post(
                        "/planned-workouts",
                        json={
                            "workout_type": value,
                            "planned_date": "2026-12-01",
                            "planned_duration": 30,
                        },
                    )
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()["workout_type"], value)

            invalid = client.post(
                "/planned-workouts",
                json={
                    "workout_type": "unsupported sport",
                    "planned_date": "2026-12-01",
                    "planned_duration": 30,
                },
            )

        self.assertEqual(invalid.status_code, 422)
        self.assertEqual(len(planned_table.items), len(NEW_WORKOUT_TYPES))

    def test_openapi_documents_supported_workout_enums(self):
        schemas = main.app.openapi()["components"]["schemas"]
        workout_values = schemas["Workout"]["properties"]["type"]["enum"]
        planned_values = schemas["PlannedWorkout"]["properties"]["workout_type"]["enum"]
        self.assertEqual(workout_values, SUPPORTED_WORKOUT_TYPES)
        self.assertEqual(planned_values, SUPPORTED_WORKOUT_TYPES)

    def test_committed_openapi_matches_fastapi_app(self):
        with open("openapi.json", encoding="utf-8") as schema_file:
            committed_schema = json.load(schema_file)
        self.assertEqual(main.app.openapi(), committed_schema)


if __name__ == "__main__":
    unittest.main()
