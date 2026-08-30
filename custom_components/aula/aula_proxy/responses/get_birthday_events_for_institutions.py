from typing import List, NotRequired, TypedDict
from datetime import datetime

from .common_data import AulaStatusData

class AulaBirthdayEventData(TypedDict):
    institutionProfileId: int
    birthday: datetime
    institutionCode: str
    name: str
    mainGroupName: NotRequired[str|None]
    relatedChildrenIds: NotRequired[List[int]|None]  # instProfileIds of your related children

class AulaGetBirthdayEventsForInstitutionsResponse(TypedDict):
    data: List[AulaBirthdayEventData]
    status: AulaStatusData
    version: int