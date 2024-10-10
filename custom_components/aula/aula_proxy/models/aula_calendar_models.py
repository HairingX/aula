from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional

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

@dataclass
class AulaCalendarEventTimeSlot:
    # child_required: bool
    # """This property is not used in Aula website 2024, they use the CalendarEvent.belongs_to_profiles and check if the kids institutionid is in that"""
    time_slots: List[AulaCalendarEventTimeSlotEntry]

@dataclass
class AulaCalendarEventLessonParticipant:
    participant_role: str
    teacher_id: int
    teacher_initials: str
    teacher_name: str

@dataclass
class AulaCalendarEventLesson:
    lesson_id: str
    lesson_status: str
    participants: List[AulaCalendarEventLessonParticipant]

@dataclass
class AulaCalendarEventResource:
    id: int
    name: str

@dataclass
class AulaCalendarEvent:
    all_day: bool
    belongs_to_profiles: List[int]
    belongs_to_resources: List[Any]
    created_datetime: datetime
    end_datetime: datetime
    has_attachments: bool
    id: int
    requires_new_answer: bool
    response_required: bool
    start_datetime: datetime
    title: str
    type: str
    lesson: Optional[AulaCalendarEventLesson|None] = None
    primary_resource: Optional[AulaCalendarEventResource|None] = None
    repeating: Optional[bool|None] = None
    response_deadline: Optional[datetime|None] = None
    response_status: Optional[str|None] = None
    time_slot: Optional[AulaCalendarEventTimeSlot|None] = None