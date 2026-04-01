import json
import os
import unittest
from datetime import date, time

from custom_components.aula.aula_proxy.models.aula_easyiq_weekplan_parser import AulaEasyiqWeekplanParser


class TestEasyiqWeekplan(unittest.TestCase):
    def _load_fixture(self, filename: str):
        filepath = os.path.join(os.path.dirname(__file__), "test_messages", filename)
        with open(filepath, "r") as f:
            return json.load(f)

    def test_parse_events_as_weekly_plan(self):
        data = self._load_fixture("easyiq_weekplan_response.json")
        plan = AulaEasyiqWeekplanParser.parse_events_as_weekly_plan(
            data, "Emilie", "user123", date(2026, 3, 16)
        )

        self.assertEqual(plan.name, "Emilie")
        self.assertEqual(plan.from_date, date(2026, 3, 16))
        self.assertEqual(plan.to_date, date(2026, 3, 22))
        self.assertEqual(len(plan.daily_plans), 2)

        # Monday has 2 events
        monday = plan.daily_plans[0]
        self.assertEqual(monday.date, date(2026, 3, 16))
        self.assertEqual(len(monday.events), 2)

        # First event: itemType "5" uses title
        event1 = monday.events[0]
        self.assertEqual(event1.title, "Matematik")
        self.assertEqual(event1.owner_name, "Lars Jensen")
        self.assertEqual(event1.description, "Vi arbejder med brøker og decimaltal")
        self.assertEqual(event1.start.time(), time(8, 0))
        self.assertEqual(event1.end.time(), time(10, 0))
        self.assertEqual(event1.item_type, "5")

        # Second event: itemType "3" uses ownername as title
        event2 = monday.events[1]
        self.assertEqual(event2.title, "Mette Hansen")
        self.assertEqual(event2.owner_name, "Mette Hansen")
        self.assertEqual(event2.start.time(), time(10, 15))
        self.assertEqual(event2.end.time(), time(12, 0))

        # Tuesday has 1 event
        tuesday = plan.daily_plans[1]
        self.assertEqual(tuesday.date, date(2026, 3, 17))
        self.assertEqual(len(tuesday.events), 1)

    def test_parse_empty_response(self):
        data = {"Events": []}
        plan = AulaEasyiqWeekplanParser.parse_events_as_weekly_plan(
            data, "Test", "user1", date(2026, 3, 16)
        )
        self.assertEqual(len(plan.daily_plans), 0)

    def test_parse_none_response(self):
        plan = AulaEasyiqWeekplanParser.parse_events_as_weekly_plan(
            None, "Test", "user1", date(2026, 3, 16)
        )
        self.assertEqual(len(plan.daily_plans), 0)

    def test_parse_invalid_datetime_skipped(self):
        data = {"Events": [
            {"start": "invalid", "end": "also-invalid", "itemType": "5",
             "title": "Test", "ownername": "Test", "description": "Test"}
        ]}
        plan = AulaEasyiqWeekplanParser.parse_events_as_weekly_plan(
            data, "Test", "user1", date(2026, 3, 16)
        )
        self.assertEqual(len(plan.daily_plans), 0)

    def test_unique_ids(self):
        data = self._load_fixture("easyiq_weekplan_response.json")
        plan = AulaEasyiqWeekplanParser.parse_events_as_weekly_plan(
            data, "Emilie", "user123", date(2026, 3, 16)
        )
        all_ids = [event.id for dp in plan.daily_plans for event in dp.events]
        self.assertEqual(len(all_ids), len(set(all_ids)), "Event IDs must be unique")


if __name__ == "__main__":
    unittest.main()
