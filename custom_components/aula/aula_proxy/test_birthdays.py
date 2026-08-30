import unittest

from custom_components.aula.aula_proxy.models.aula_birthday_parser import (
    AulaBirthdayParser,
)


class TestBirthdays(unittest.TestCase):
    def _event(self, **extra: object) -> dict:
        data = {
            "institutionProfileId": 111,
            "birthday": "2026-09-01T00:00:00+00:00",
            "institutionCode": "A12345",
            "name": "Some Child",
            "mainGroupName": "1A",
            "relatedChildrenIds": [222, 333],
        }
        data.update(extra)
        return data

    def test_related_children_ids_parsed(self):
        """relatedChildrenIds is captured so calendars can be scoped per child."""
        event = AulaBirthdayParser.parse_birthday_event(self._event())

        assert event is not None
        self.assertEqual(event.related_children_ids, [222, 333])
        self.assertEqual(event.main_group_name, "1A")

    def test_missing_related_children_ids_is_empty_list(self):
        """A missing field yields [] (never raises), enabling the safe fallback."""
        data = self._event()
        del data["relatedChildrenIds"]

        event = AulaBirthdayParser.parse_birthday_event(data)

        assert event is not None
        self.assertEqual(event.related_children_ids, [])


if __name__ == "__main__":
    unittest.main()
