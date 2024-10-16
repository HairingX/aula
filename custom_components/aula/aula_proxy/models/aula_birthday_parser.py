from typing import List

from ..responses.get_birthday_events_for_institutions import *
from ..utils.list_utils import list_without_none
from .aula_birthday_models import *
from .aula_parser import AulaParser

class AulaBirthdayParser(AulaParser):

    @staticmethod
    def parse_birthday_event(data: AulaBirthdayEventData | None) -> AulaBirthdayEvent | None:
        if not data: return None
        result = AulaBirthdayEvent(
            institution_profile_id = AulaBirthdayParser._parse_int(data.get("institutionProfileId")),
            birthday_date = AulaBirthdayParser._parse_date(data.get("birthday")),
            institution_code = AulaBirthdayParser._parse_str(data.get("institutionCode")),
            full_name = AulaBirthdayParser._parse_str(data.get("name")),
            main_group_name = AulaBirthdayParser._parse_str(data.get("mainGroupName")),
        )

        return result

    @staticmethod
    def parse_birthday_events(data: List[AulaBirthdayEventData] | None) -> List[AulaBirthdayEvent]:
        if data is None: return []
        return list_without_none(map(AulaBirthdayParser.parse_birthday_event, data))


    @staticmethod
    def parse_birthday_event_response(data: AulaGetBirthdayEventsForInstitutionsResponse | None) -> List[AulaBirthdayEvent]:
        if data is None: return []
        return AulaBirthdayParser.parse_birthday_events(data["data"])
