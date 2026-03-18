from datetime import timedelta, date
from typing import List

from ..responses.get_weekly_newsletter_response import (
    AulaGetWeeklyNewsletterResponse,
    AulaWeeklyNewsletterPersonData,
)
from ..utils.list_utils import list_without_none

from .aula_newsletter_models import AulaNewsletter, AulaWeeklyNewsletter
from .aula_parser import AulaParser


class AulaNewsletterParser(AulaParser):
    @staticmethod
    def parse_person(data: AulaWeeklyNewsletterPersonData, from_date: date) -> AulaWeeklyNewsletter | None:
        full_name = AulaNewsletterParser._parse_str(data.get("navn"))
        if not full_name:
            return None

        institutions = data.get("institutioner")
        if not institutions:
            return None

        weekno = from_date.strftime("%Y-W%V")
        newsletters: List[AulaNewsletter] = []

        for institution in institutions:
            inst_name = AulaNewsletterParser._parse_str(institution.get("institution"))
            newsletter_list = institution.get("ugebreve")
            if not newsletter_list:
                continue
            for newsletter in newsletter_list:
                indhold = newsletter.get("indhold", "")
                if not indhold:
                    continue
                newsletter_id = hash(full_name + weekno + indhold[:50])
                newsletters.append(AulaNewsletter(
                    id=newsletter_id,
                    content_html=indhold,
                    institution_name=inst_name,
                ))

        if not newsletters:
            return None

        return AulaWeeklyNewsletter(
            child_name=full_name,
            from_date=from_date,
            to_date=from_date + timedelta(days=6),
            newsletters=newsletters,
        )

    @staticmethod
    def parse_response(data: AulaGetWeeklyNewsletterResponse | None, from_date: date) -> List[AulaWeeklyNewsletter]:
        if not data:
            return []
        personer = data.get("personer")
        if not personer:
            return []
        return list_without_none([
            AulaNewsletterParser.parse_person(person, from_date)
            for person in personer
        ])
