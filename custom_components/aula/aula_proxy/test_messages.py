import json
import unittest
from pathlib import Path

from custom_components.aula.aula_proxy.models.aula_profile_parser import AulaProfileParser

class TestMessages(unittest.TestCase):
    # def setUp(self):

    def test_getProfilesByLogin(self):
        fixture_path = Path(__file__).parent / "test_messages" / "profiles.getProfilesByLogin.json"
        with open(fixture_path, encoding="utf-8") as txt:
            msg = json.load(txt)
            profiles = AulaProfileParser.parse_profiles(msg["data"]["profiles"])
            for profile in profiles:
                self.assertIsNotNone(profile.profile_id)
                self.assertIsNotNone(profile.name)

                self.assertIsNotNone(profile.institution_profiles)
                self.assertGreater(len(profile.institution_profiles), 0)

                for institution in profile.institution_profiles:
                    self.assertIsNotNone(institution.id)
                    self.assertIsNotNone(institution.institution_code)
                    self.assertIsNotNone(institution.institution_name)

                self.assertIsNotNone(profile.children)
                self.assertGreater(len(profile.children), 0)
                for child in profile.children:
                    self.assertIsNotNone(child.id)
                    self.assertIsNotNone(child.institution_code)
                    self.assertIsNotNone(child.name)
                    self.assertIsNotNone(child.profile_id)
                    self.assertIsNotNone(child.short_name)
                    self.assertIsNotNone(child.user_id)
                    if child.profile_picture is not None:
                        self.assertIsNotNone(child.profile_picture.id)

if __name__ == '__main__':
    unittest.main()
