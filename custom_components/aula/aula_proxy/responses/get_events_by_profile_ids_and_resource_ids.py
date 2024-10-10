import datetime
from typing import List, TypedDict
from typing import List
from datetime import datetime
from typing_extensions import NotRequired

from .common_data import AulaStatusData

class AulaAnswerData(TypedDict):
    concerningProfileId: int
    id: int
    instProfileId: int
    selectedTimeSlotIndex: int

class AulaTimeSlotIndexData(TypedDict):
    endTime: datetime
    startTime: datetime

class AulaTimeSlotDetailData(TypedDict):
    answers: List[AulaAnswerData]
    endDate: datetime
    id: int
    startDate: datetime
    timeSlotIndexes: List[AulaTimeSlotIndexData]

class AulaTimeSlotData(TypedDict):
    # childRequired: bool # this field seems to be obsolete, the website does not use it, it analyzes the timeSlots array instead
    timeSlots: List[AulaTimeSlotDetailData]

class AulaLessonParticipantData(TypedDict):
    participantRole: str
    teacherId: int
    teacherInitials: str
    teacherName: str

class AulaLessonData(TypedDict):
    lessonId: str
    lessonStatus: str
    participants: List[AulaLessonParticipantData]

class AulaPrimaryResourceData(TypedDict):
    id: int
    name: str

class AulaEventData(TypedDict):
    allDay: bool
    belongsToProfiles: List[int]
    createdDateTime: datetime
    endDateTime: datetime
    hasAttachments: bool
    id: int
    lesson: NotRequired[AulaLessonData | None]
    primaryResource: NotRequired[AulaPrimaryResourceData | None]
    repeating: NotRequired[str | None]
    requiresNewAnswer: bool
    responseDeadline: NotRequired[datetime | None]
    responseRequired: bool
    responseStatus: NotRequired[str | None]
    startDateTime: datetime
    timeSlot: NotRequired[AulaTimeSlotData | None]
    title: str
    type: str

class AulaGetEventsByProfileIdsAndResourceIdsResponse(TypedDict):
    data: List[AulaEventData]
    status: AulaStatusData
    version: int