from typing import NotRequired, TypedDict, List

from .common_data import AulaStatusData

class AulaDailyOverviewInstitutionProfileData(TypedDict):
    id: NotRequired[str|None]
    institutionCode: NotRequired[str|None]
    institutionName: NotRequired[str|None]
    metadata: NotRequired[str|None]

class AulaDailyOverviewLocationData(TypedDict):
    description: NotRequired[str|None]
    endDate: NotRequired[str|None]
    endTime: NotRequired[str|None]
    id: NotRequired[str|None]
    name: NotRequired[str|None]
    startDate: NotRequired[str|None]
    startTime: NotRequired[str|None]
    symbol: NotRequired[str|None]

class AulaDailyOverviewData(TypedDict):
    activityType: NotRequired[str|None]
    checkInTime: NotRequired[str|None]
    checkOutTime: NotRequired[str|None]
    comment: NotRequired[str|None]
    entryTime: NotRequired[str|None]
    exitTime: NotRequired[str|None]
    exitWith: NotRequired[str|None]
    id: NotRequired[str|None]
    institutionProfile: NotRequired[AulaDailyOverviewInstitutionProfileData|None]
    isDefaultEntryTime: NotRequired[bool|None]
    isDefaultExitTime: NotRequired[bool|None]
    isPlannedTimesOutsideOpeningHours: NotRequired[bool|None]
    location: NotRequired[AulaDailyOverviewLocationData|None]
    sleepIntervals: NotRequired[List[str]|None]
    spareTimeActivity: NotRequired[str|None]
    status: NotRequired[str|None]


class AulaGetDailyOverviewResponse(TypedDict):
    data: List[AulaDailyOverviewData]
    status: AulaStatusData
    version: str
