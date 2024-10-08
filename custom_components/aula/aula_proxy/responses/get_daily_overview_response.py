from typing import NotRequired, TypedDict, List

from .common_data import AulaProfilePictureData

class AulaDailyOverviewInstitutionProfileData(TypedDict):
    id: NotRequired[str|None]
    institutionCode: NotRequired[str|None]
    institutionName: NotRequired[str|None]
    institutionRole: NotRequired[str|None]
    mainGroup: NotRequired[str|None]
    metadata: NotRequired[str|None]
    name: NotRequired[str|None]
    profileId: NotRequired[str|None]
    profilePicture: NotRequired[AulaProfilePictureData|None]
    role: NotRequired[str|None]
    shortName: NotRequired[str|None]

class AulaDailyOverviewMainGroupData(TypedDict):
    allowMembersToBeShown: NotRequired[bool|None]
    id: NotRequired[str|None]
    institutionCode: NotRequired[str|None]
    institutionName: NotRequired[str|None]
    isDeactivated: NotRequired[bool|None]
    mainGroup: NotRequired[bool|None]
    name: NotRequired[str|None]
    shortName: NotRequired[str|None]
    uniGroupType: NotRequired[str|None]

class AulaDailyOverviewLocationData(TypedDict):
    description: NotRequired[str|None]
    endDate: NotRequired[str|None]
    endTime: NotRequired[str|None]
    id: NotRequired[str|None]
    isDateIntervalsEnabled: NotRequired[bool|None]
    isDeactivated: NotRequired[bool|None]
    isTimeIntervalsEnabled: NotRequired[bool|None]
    isWeekdaysEnabled: NotRequired[bool|None]
    name: NotRequired[str|None]
    startDate: NotRequired[str|None]
    startTime: NotRequired[str|None]
    symbol: NotRequired[str|None]
    weekDayMask: NotRequired[int|None]

class AulaDailyOverviewData(TypedDict):
    activityType: NotRequired[str|None]
    checkInTime: NotRequired[str|None]
    checkOutTime: NotRequired[str|None]
    comment: NotRequired[str|None]
    editablePresenceStates: NotRequired[List[str]|None]
    entryTime: NotRequired[str|None]
    exitTime: NotRequired[str|None]
    exitWith: NotRequired[str|None]
    id: NotRequired[str|None]
    institutionProfile: NotRequired[AulaDailyOverviewInstitutionProfileData|None]
    isDefaultEntryTime: NotRequired[bool|None]
    isDefaultExitTime: NotRequired[bool|None]
    isPlannedTimesOutsideOpeningHours: NotRequired[bool|None]
    location: NotRequired[AulaDailyOverviewLocationData|None]
    mainGroup: NotRequired[AulaDailyOverviewMainGroupData|None]
    selfDeciderEndTime: NotRequired[str|None]
    selfDeciderStartTime: NotRequired[str|None]
    sleepIntervals: NotRequired[List[str]|None]
    spareTimeActivity: NotRequired[str|None]
    status: NotRequired[str|None]

class AulaDailyOverviewStatusData(TypedDict):
    code: str
    message: NotRequired[str|None]

class AulaGetDailyOverviewResponse(TypedDict):
    data: List[AulaDailyOverviewData]
    method: str
    module: str
    status: AulaDailyOverviewStatusData
    version: str
