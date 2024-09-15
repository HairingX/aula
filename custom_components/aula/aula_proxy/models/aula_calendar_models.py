import datetime
from typing import Any, List, NotRequired, TypedDict

from .aula_profile_models import AulaGroup

class AulaCalendarEventTimeSlotEntryIndex(TypedDict):
    start_time: datetime.datetime
    end_time: datetime.datetime

class AulaCalendarEventTimeSlotEntryAnswer(TypedDict):
    concerning_profile_id: int
    id: int
    inst_profile_id: int
    selected_time_slot_index: int

class AulaCalendarEventTimeSlotEntry(TypedDict):
    answers: List[AulaCalendarEventTimeSlotEntryAnswer]
    belongs_to_resource: NotRequired[Any]
    end_date: datetime.datetime
    id: int
    start_date: datetime.datetime
    time_slot_indexes: List[AulaCalendarEventTimeSlotEntryIndex]

class AulaCalendarEventTimeSlot(TypedDict):
    child_required: bool
    time_slots: List[AulaCalendarEventTimeSlotEntry]

class AulaCalendarEventLessonParticipant(TypedDict):
    participant_role: str
    teacher_id: int
    teacher_initials: str
    teacher_name: str

class AulaCalendarEventLesson(TypedDict):
    has_relevant_note: bool
    lesson_id: str
    lesson_status: str
    participants: List[AulaCalendarEventLessonParticipant]

class AulaCalendarEventResource(TypedDict):
    id: int
    name: str

class AulaCalendarEvent(TypedDict):
    added_to_institution_calendar: bool
    additional_resources: List[AulaCalendarEventResource]
    additional_resource_text: NotRequired[str|None]
    all_day: bool
    belongs_to_profiles: List[int]
    belongs_to_resources: List[Any]
    created_datetime: datetime.datetime
    creator_inst_profile_id: NotRequired[int|None]
    creator_profile_id: NotRequired[int|None]
    directly_related: bool
    end_datetime: datetime.datetime
    has_attachments: bool
    id: int
    institution_code: NotRequired[str|None]
    institution_name: NotRequired[str|None]
    invited_groups: List[AulaGroup]
    lesson: NotRequired[AulaCalendarEventLesson|None]
    old_all_day: NotRequired[bool|None]
    old_end_datetime: NotRequired[datetime.datetime|None]
    old_start_datetime: NotRequired[datetime.datetime|None]
    primary_resource: NotRequired[AulaCalendarEventResource|None]
    primary_resource_text: NotRequired[str|None]
    private: bool
    repeating: NotRequired[bool|None]
    requires_new_answer: bool
    response_deadline: NotRequired[datetime.datetime|None]
    response_required: bool
    response_status: NotRequired[str|None]
    start_datetime: datetime.datetime
    time_slot: NotRequired[AulaCalendarEventTimeSlot|None]
    title: str
    type: str