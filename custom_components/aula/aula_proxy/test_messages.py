import json
import unittest

from .models.aula_profile_parser import AulaProfileParser

class TestMessages(unittest.TestCase):
    # def setUp(self):

    def test_getProfilesByLogin(self):
        with open("custom_components/aula/aula_proxy/test_messages/profiles.getProfilesByLogin.json", encoding="utf-8", ) as txt:
            msg = json.load(txt)
            profiles = AulaProfileParser.parse_profiles(msg["data"]["profiles"])
            for profile in profiles:
                self.assertIsNotNone(profile["profile_id"])
                self.assertIsNotNone(profile["display_name"])

                #optional
                # self.assertIsNotNone(profile["age_18_and_older"])
                # self.assertIsNotNone(profile["contact_info_editable"])
                # self.assertIsNotNone(profile.get("is_latest_data_policy_accepted"))
                # self.assertIsNotNone(profile["over_consent_age"])
                # self.assertIsNotNone(profile.get("portal_role"))
                # self.assertIsNotNone(profile.get("support_role"))

                self.assertIsNotNone(profile["institution_profiles"])
                self.assertGreater(len(profile["institution_profiles"]), 0)

                for institution in profile["institution_profiles"]:
                    self.assertIsNotNone(institution["first_name"])
                    self.assertIsNotNone(institution["full_name"])
                    self.assertNotEqual("None", institution["full_name"])
                    self.assertIsNotNone(institution["gender"])
                    self.assertIsNotNone(institution["id"])
                    self.assertIsNotNone(institution["institution_code"])
                    self.assertIsNotNone(institution["institution_name"])
                    self.assertIsNotNone(institution["is_primary"])
                    self.assertIsNotNone(institution["last_name"])
                    self.assertIsNotNone(institution["short_name"])
                    if "profile_picture" in institution and institution["profile_picture"] is not None:
                        profile_picture = institution["profile_picture"]
                        self.assertIsNotNone(profile_picture["id"])
                        self.assertIsNotNone(profile_picture.get("bucket"))
                        self.assertIsNotNone(profile_picture.get("key"))
                        self.assertIsNotNone(profile_picture.get("is_image_scaling_pending"))
                        self.assertIsNotNone(profile_picture.get("url"))

                self.assertIsNotNone(profile["children"])
                self.assertGreater(len(profile["children"]), 0)
                for child in profile["children"]:
                    self.assertIsNotNone(child["id"])
                    self.assertIsNotNone(child["institution_code"])
                    self.assertIsNotNone(child["name"])
                    self.assertIsNotNone(child["profile_id"])
                    self.assertIsNotNone(child["short_name"])
                    self.assertIsNotNone(child["user_id"])
                    if "profile_picture" in child and child["profile_picture"] is not None:
                        profile_picture = child["profile_picture"]
                        self.assertIsNotNone(profile_picture["id"])
                        self.assertIsNotNone(profile_picture.get("bucket"))
                        self.assertIsNotNone(profile_picture.get("key"))
                        self.assertIsNotNone(profile_picture.get("is_image_scaling_pending"))
                        self.assertIsNotNone(profile_picture.get("url"))

            print([json.dumps(profile, ensure_ascii=False) for profile in profiles])

if __name__ == '__main__':
    unittest.main()
