import unittest

from custom_components.aula.aula_proxy.models.aula_notification_models import (
    AulaMessageNotification,
)
from custom_components.aula.aula_proxy.models.aula_notification_parser import (
    AulaNotificationParser,
)


class TestNotifications(unittest.TestCase):
    def _message_notification(self, institution_code: object, **extra: object) -> dict:
        data = {
            "expires": "2026-05-23T23:59:59+00:00",
            "institutionCode": institution_code,
            "institutionProfileId": 123456,
            "notificationArea": "Messages",
            "notificationEventType": "NewMessagePrivateInbox",
            "notificationId": "NewMessagePrivateInbox:123456:Badge",
            "notificationType": "Badge",
            "triggered": "2026-05-22T13:09:47+00:00",
            "messageText": "Hello",
            "senderName": "Teacher",
            "threadId": 987654,
        }
        data.update(extra)
        return data

    def test_message_notification_with_non_numeric_institution_code(self):
        """Regression test for issue #10.

        Aula institution codes can be non-numeric (e.g. 'GXXXXX'). Parsing a
        message notification must not raise ValueError on such codes; previously
        institutionCode was forced through int() and crashed the whole fetch.
        """
        data = self._message_notification("GXXXXX")

        result = AulaNotificationParser.parse_notification(data)

        self.assertIsInstance(result, AulaMessageNotification)
        assert isinstance(result, AulaMessageNotification)
        self.assertEqual(result.institution_code, "GXXXXX")

    def test_message_notification_with_numeric_institution_code(self):
        """A numeric institution code is preserved verbatim as a string."""
        data = self._message_notification("123456")

        result = AulaNotificationParser.parse_notification(data)

        self.assertIsInstance(result, AulaMessageNotification)
        assert isinstance(result, AulaMessageNotification)
        self.assertEqual(result.institution_code, "123456")

    def test_batch_with_one_non_numeric_code_parses_all(self):
        """A single non-numeric institution code must not take down the batch."""
        data = [
            self._message_notification("GXXXXX"),
            self._message_notification("123456"),
        ]

        results = AulaNotificationParser.parse_notifications(data)

        self.assertEqual(len(results), 2)

    def test_folder_id_parsed_when_present(self):
        """Best-guess mapping for issue #10: a numeric folderId is captured."""
        data = self._message_notification("123456", folderId=42)

        result = AulaNotificationParser.parse_notification(data)

        assert isinstance(result, AulaMessageNotification)
        self.assertEqual(result.folder_id, 42)

    def test_folder_id_is_none_when_absent(self):
        """No folderId in the payload yields None, not a crash or sentinel int."""
        data = self._message_notification("123456")

        result = AulaNotificationParser.parse_notification(data)

        assert isinstance(result, AulaMessageNotification)
        self.assertIsNone(result.folder_id)

    def test_folder_id_non_numeric_does_not_crash(self):
        """An unexpected non-numeric folderId is tolerated (None), never raises."""
        data = self._message_notification("123456", folderId="not-a-number")

        result = AulaNotificationParser.parse_notification(data)

        assert isinstance(result, AulaMessageNotification)
        self.assertIsNone(result.folder_id)


if __name__ == "__main__":
    unittest.main()
