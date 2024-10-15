import datetime
from typing import List, TypedDict
from typing import List
from datetime import datetime

from .common_data import AulaStatusData

class AulaBirthdayEventData(TypedDict):
    institutionProfileId: int
    birthday: datetime
    institutionCode: str
    name: str

class AulaGetBirthdayEventsForInstitutionsResponse(TypedDict):
    data: List[AulaBirthdayEventData]
    status: AulaStatusData
    version: int