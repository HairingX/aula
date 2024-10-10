from datetime import date
from typing import List, NotRequired, TypedDict

class AulaWeeklyNewsletterData(TypedDict):
    indhold: str

class AulaWeeklyNewsletterInstitutionData(TypedDict):
    institution: str
    ugebreve: NotRequired[List[AulaWeeklyNewsletterData]|None]

class AulaWeeklyNewsletterPersonData(TypedDict):
    navn: str
    institutioner: NotRequired[List[AulaWeeklyNewsletterInstitutionData]|None]

class AulaGetWeeklyNewsletterResponse(TypedDict):
    from_date: date
    to_date: date
    personer: List[AulaWeeklyNewsletterPersonData]
