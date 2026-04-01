import json
import os
import unittest
from datetime import date, timedelta

from custom_components.aula.aula_proxy.models.aula_newsletter_parser import AulaNewsletterParser


class TestNewsletter(unittest.TestCase):
    def _load_fixture(self, filename: str):
        filepath = os.path.join(os.path.dirname(__file__), "test_messages", filename)
        with open(filepath, "r") as f:
            return json.load(f)

    def test_parse_valid_newsletter_response(self):
        raw = self._load_fixture("newsletter_response.json")
        data = raw["module_response"]
        from_date = date(2026, 3, 16)
        results = AulaNewsletterParser.parse_response(data, from_date)

        self.assertEqual(len(results), 1)
        weekly = results[0]
        self.assertEqual(weekly.child_name, "Test Child")
        self.assertEqual(weekly.from_date, date(2026, 3, 16))
        self.assertEqual(weekly.to_date, date(2026, 3, 22))
        self.assertEqual(len(weekly.newsletters), 1)

        newsletter = weekly.newsletters[0]
        self.assertEqual(newsletter.institution_name, "Solskolen")
        self.assertIn("<h1>Week Newsletter</h1>", newsletter.content_html)

    def test_parse_empty_ugebreve(self):
        data = {
            "from_date": "2026-03-16",
            "to_date": "2026-03-22",
            "personer": [
                {
                    "navn": "Empty Child",
                    "institutioner": [
                        {
                            "institution": "Solskolen",
                            "ugebreve": []
                        }
                    ]
                }
            ]
        }
        results = AulaNewsletterParser.parse_response(data, date(2026, 3, 16))
        self.assertEqual(len(results), 0)

    def test_parse_missing_institutioner(self):
        data = {
            "from_date": "2026-03-16",
            "to_date": "2026-03-22",
            "personer": [
                {
                    "navn": "No Inst Child"
                }
            ]
        }
        results = AulaNewsletterParser.parse_response(data, date(2026, 3, 16))
        self.assertEqual(len(results), 0)

    def test_parse_multiple_children(self):
        data = {
            "from_date": "2026-03-16",
            "to_date": "2026-03-22",
            "personer": [
                {
                    "navn": "Child One",
                    "institutioner": [
                        {
                            "institution": "Solskolen",
                            "ugebreve": [
                                {"indhold": "<p>Newsletter for child one</p>"}
                            ]
                        }
                    ]
                },
                {
                    "navn": "Child Two",
                    "institutioner": [
                        {
                            "institution": "Maaneskolen",
                            "ugebreve": [
                                {"indhold": "<p>Newsletter for child two</p>"}
                            ]
                        }
                    ]
                }
            ]
        }
        results = AulaNewsletterParser.parse_response(data, date(2026, 3, 16))

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].child_name, "Child One")
        self.assertEqual(results[0].newsletters[0].institution_name, "Solskolen")
        self.assertEqual(results[1].child_name, "Child Two")
        self.assertEqual(results[1].newsletters[0].institution_name, "Maaneskolen")

    def test_html_content_preserved(self):
        html = '<div class="newsletter"><h2>Title</h2><p>Content with <em>emphasis</em> &amp; special chars</p><img src="photo.jpg"/></div>'
        data = {
            "from_date": "2026-03-16",
            "to_date": "2026-03-22",
            "personer": [
                {
                    "navn": "HTML Child",
                    "institutioner": [
                        {
                            "institution": "TestSkolen",
                            "ugebreve": [
                                {"indhold": html}
                            ]
                        }
                    ]
                }
            ]
        }
        results = AulaNewsletterParser.parse_response(data, date(2026, 3, 16))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].newsletters[0].content_html, html)

    def test_parse_none_response(self):
        results = AulaNewsletterParser.parse_response(None, date(2026, 3, 16))
        self.assertEqual(len(results), 0)

    def test_parse_empty_personer(self):
        data = {
            "from_date": "2026-03-16",
            "to_date": "2026-03-22",
            "personer": []
        }
        results = AulaNewsletterParser.parse_response(data, date(2026, 3, 16))
        self.assertEqual(len(results), 0)

    def test_to_date_is_six_days_after_from_date(self):
        from_date = date(2026, 3, 16)
        data = {
            "from_date": "2026-03-16",
            "to_date": "2026-03-22",
            "personer": [
                {
                    "navn": "Date Child",
                    "institutioner": [
                        {
                            "institution": "Skolen",
                            "ugebreve": [
                                {"indhold": "<p>Content</p>"}
                            ]
                        }
                    ]
                }
            ]
        }
        results = AulaNewsletterParser.parse_response(data, from_date)
        self.assertEqual(results[0].to_date, from_date + timedelta(days=6))


if __name__ == "__main__":
    unittest.main()
