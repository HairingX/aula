from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional

from .aula_profile_models import AulaGroup

@dataclass
class AulaCalendarEventTimeSlotEntryIndex:
    end_datetime: datetime
    start_datetime: datetime

@dataclass
class AulaCalendarEventTimeSlotEntryAnswer:
    concerning_profile_id: int
    id: int
    inst_profile_id: int
    selected_time_slot_index: int

@dataclass
class AulaCalendarEventTimeSlotEntry:
    answers: List[AulaCalendarEventTimeSlotEntryAnswer]
    end_date: datetime
    id: int
    start_date: datetime
    time_slot_indexes: List[AulaCalendarEventTimeSlotEntryIndex]
    belongs_to_resource: Optional[Any] = None

@dataclass
class AulaCalendarEventTimeSlot:
    child_required: bool
    """This property is not used in Aula website 2024, they use the CalendarEvent.belongs_to_profiles and check if the kids institutionid is in that"""
    time_slots: List[AulaCalendarEventTimeSlotEntry]

@dataclass
class AulaCalendarEventLessonParticipant:
    participant_role: str
    teacher_id: int
    teacher_initials: str
    teacher_name: str

@dataclass
class AulaCalendarEventLesson:
    has_relevant_note: bool
    lesson_id: str
    lesson_status: str
    participants: List[AulaCalendarEventLessonParticipant]

@dataclass
class AulaCalendarEventResource:
    id: int
    name: str

@dataclass
class AulaCalendarEvent:
    added_to_institution_calendar: bool
    additional_resources: List[AulaCalendarEventResource]
    all_day: bool
    belongs_to_profiles: List[int]
    belongs_to_resources: List[Any]
    created_datetime: datetime
    directly_related: bool
    end_datetime: datetime
    has_attachments: bool
    id: int
    private: bool
    invited_groups: List[AulaGroup]
    requires_new_answer: bool
    response_required: bool
    start_datetime: datetime
    title: str
    type: str
    additional_resource_text: Optional[str|None] = None
    creator_inst_profile_id: Optional[int|None] = None
    creator_profile_id: Optional[int|None] = None
    institution_code: Optional[str|None] = None
    institution_name: Optional[str|None] = None
    lesson: Optional[AulaCalendarEventLesson|None] = None
    old_all_day: Optional[bool|None] = None
    old_end_datetime: Optional[datetime|None] = None
    old_start_datetime: Optional[datetime|None] = None
    primary_resource_text: Optional[str|None] = None
    primary_resource: Optional[AulaCalendarEventResource|None] = None
    repeating: Optional[bool|None] = None
    response_deadline: Optional[datetime|None] = None
    response_status: Optional[str|None] = None
    time_slot: Optional[AulaCalendarEventTimeSlot|None] = None