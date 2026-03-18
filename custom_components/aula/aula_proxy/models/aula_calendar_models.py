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
    """A teacher/lecturer participating in a lesson.

    participant_role: Role in the lesson. Known values:
        - "primaryTeacher": The assigned teacher for this lesson
        - "substituteTeacher": A substitute teacher
    teacher_id: Unique teacher ID in Aula
    teacher_initials: Short initials (e.g. "JD")
    teacher_name: Full display name
    """
    participant_role: str
    teacher_id: int
    teacher_initials: str
    teacher_name: str

@dataclass
class AulaCalendarEventLesson:
    """Lesson metadata attached to a calendar event.

    lesson_id: Unique lesson identifier
    lesson_status: Status of the lesson. Known values (no other states known):
        - "normal": Regular lesson with the assigned teacher
        - "substitute": Teacher is a substitute
    participants: List of teachers/lecturers for this lesson
    """
    lesson_id: str
    lesson_status: str
    participants: List[AulaCalendarEventLessonParticipant]

@dataclass
class AulaCalendarEventResource:
    """A resource assigned to an event.

    id: Resource ID in Aula
    name: Name of the room, area, or other location
    """
    id: int
    name: str

@dataclass
class AulaCalendarEvent:
    """A calendar event from the Aula API.

    all_day: Whether this is an all-day event
    belongs_to_profiles: Institution profile IDs this event applies to
    belongs_to_resources: Resources associated with the event. Always observed as empty array — purpose unknown.
    created_datetime: When the event was created
    end_datetime: Event end time
    has_attachments: Whether the event has file attachments
    id: Unique event ID
    requires_new_answer: Whether a new response is needed (for bookable meetings)
    repeating: Always observed as None — purpose unknown.
    response_required: Whether a response is required from the guardian
    response_status: Guardian's response to an event invitation. Observed on type="event", but should be used if set on any type. Known values:
        - "accepted": Invitation accepted
        - "waiting": Awaiting response
        - "declined": Invitation declined (assumed, not yet confirmed)
        - None: Not set / not applicable
    start_datetime: Event start time
    title: Event title/subject name
    type: Event type. Known values:
        - "lesson": Normal scheduled lesson (has lesson data with teachers)
        - "event": Special events (theme days, trips, bike day etc.) — no lesson data
        - "presence_holiday": Registered holiday/vacation
        - See AulaCalendarEventType for all known values
    """
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