from typing import Any, Dict, List

from ..utils.list_utils import list_without_none
from .aula_calendar_models import AulaCalendarEvent, AulaCalendarEventLesson, AulaCalendarEventLessonParticipant, AulaCalendarEventResource, AulaCalendarEventTimeSlot, AulaCalendarEventTimeSlotEntry, AulaCalendarEventTimeSlotEntryAnswer, AulaCalendarEventTimeSlotEntryIndex
from .aula_parser import AulaParser
from .aula_profile_parser import AulaProfileParser

class AulaCalendarParser(AulaParser):

    @staticmethod
    def parse_calendar_event(data: Dict[str, Any] | None) -> AulaCalendarEvent | None:
        if not data: return None
        result: AulaCalendarEvent = {
            "added_to_institution_calendar": AulaCalendarParser._parse_bool(data.get("addedToInstitutionCalendar")),
            "additional_resources": AulaCalendarParser.parse_calendar_event_resources(data.get("additionalResources", [])),
            "all_day": AulaCalendarParser._parse_bool(data.get("allDay")),
            "belongs_to_profiles": list(map(AulaCalendarParser._parse_int, data.get("belongsToProfiles", []))),
            "belongs_to_resources": data.get("belongsToResources", []),
            "created_datetime": AulaCalendarParser._parse_datetime(data.get("createdDateTime")),
            "directly_related": AulaCalendarParser._parse_bool(data.get("directlyRelated")),
            "end_datetime": AulaCalendarParser._parse_datetime(data.get("endDateTime")),
            "has_attachments": AulaCalendarParser._parse_bool(data.get("hasAttachments")),
            "id": AulaCalendarParser._parse_int(data.get("id")),
            "invited_groups": AulaProfileParser.parse_groups(data.get("invitedGroups", [])),
            "private": AulaCalendarParser._parse_bool(data.get("private")),
            "requires_new_answer": AulaCalendarParser._parse_bool(data.get("requiresNewAnswer")),
            "response_required": AulaCalendarParser._parse_bool(data.get("responseRequired")),
            "start_datetime": AulaCalendarParser._parse_datetime(data.get("startDateTime")),
            "title": AulaCalendarParser._parse_str(data.get("title")),
            "type": AulaCalendarParser._parse_str(data.get("type")),
            "additional_resource_text": AulaCalendarParser._parse_nullable_str(data.get("additionalResourceText")),
            "creator_inst_profile_id": AulaCalendarParser._parse_nullable_int(data.get("creatorInstProfileId")),
            "creator_profile_id": AulaCalendarParser._parse_nullable_int(data.get("creatorProfileId")),
            "institution_code": AulaCalendarParser._parse_nullable_str(data.get("institutionCode")),
            "institution_name": AulaCalendarParser._parse_nullable_str(data.get("institutionName")),
            "lesson": AulaCalendarParser.parse_calendar_event_lesson(data.get("lesson")),
            "old_all_day": AulaCalendarParser._parse_nullable_bool(data.get("oldAllDay")),
            "old_end_datetime": AulaCalendarParser._parse_nullable_datetime(data.get("oldEndDateTime")),
            "old_start_datetime": AulaCalendarParser._parse_nullable_datetime(data.get("oldStartDateTime")),
            "primary_resource": AulaCalendarParser.parse_calendar_event_resource(data.get("primaryResource")),
            "primary_resource_text": AulaCalendarParser._parse_nullable_str(data.get("primaryResourceText")),
            "repeating": AulaCalendarParser._parse_nullable_bool(data.get("repeating")),
            "response_deadline": AulaCalendarParser._parse_nullable_datetime(data.get("responseDeadline")),
            "response_status": AulaCalendarParser._parse_nullable_str(data.get("responseStatus")),
            "time_slot": AulaCalendarParser.parse_calendar_event_time_slot(data.get("timeSlot")),
        }

        return result

    @staticmethod
    def parse_calendar_events(data: List[Dict[str, Any]] | None) -> List[AulaCalendarEvent]:
        if data is None: return []
        return list_without_none(map(AulaCalendarParser.parse_calendar_event, data))

    @staticmethod
    def parse_calendar_event_resource(data: Dict[str, Any] | None) -> AulaCalendarEventResource | None:
        if not data: return None
        result: AulaCalendarEventResource = {
            "id": AulaCalendarParser._parse_int(data.get("id")),
            "name": AulaCalendarParser._parse_str(data.get("name")),
        }
        return result

    @staticmethod
    def parse_calendar_event_resources(data: List[Dict[str, Any]] | None) -> List[AulaCalendarEventResource]:
        if data is None: return []
        return list_without_none(map(AulaCalendarParser.parse_calendar_event_resource, data))

    @staticmethod
    def parse_calendar_event_lesson_participant(data: Dict[str, Any] | None) -> AulaCalendarEventLessonParticipant | None:
        if not data: return None
        result: AulaCalendarEventLessonParticipant = {
            "participant_role": AulaCalendarParser._parse_str(data.get("participantRole")),
            "teacher_id": AulaCalendarParser._parse_int(data.get("teacherId")),
            "teacher_initials": AulaCalendarParser._parse_str(data.get("teacherInitials")),
            "teacher_name": AulaCalendarParser._parse_str(data.get("teacherName")),
        }
        return result

    @staticmethod
    def parse_calendar_event_lesson_participants(data: List[Dict[str, Any]] | None) -> List[AulaCalendarEventLessonParticipant]:
        if data is None: return []
        return list_without_none(map(AulaCalendarParser.parse_calendar_event_lesson_participant, data))

    @staticmethod
    def parse_calendar_event_lesson(data: Dict[str, Any] | None) -> AulaCalendarEventLesson | None:
        if not data: return None
        result: AulaCalendarEventLesson = {
            "has_relevant_note": AulaCalendarParser._parse_bool(data.get("hasRelevantNote")),
            "lesson_id": AulaCalendarParser._parse_str(data.get("lessonId")),
            "lesson_status": AulaCalendarParser._parse_str(data.get("lessonStatus")),
            "participants": AulaCalendarParser.parse_calendar_event_lesson_participants(data.get("participants")),
        }
        return result

    @staticmethod
    def parse_calendar_event_time_slot(data: Dict[str, Any] | None) -> AulaCalendarEventTimeSlot | None:
        if not data: return None
        result: AulaCalendarEventTimeSlot = {
            "child_required": AulaCalendarParser._parse_bool(data.get("childRequired")),
            "time_slots": AulaCalendarParser.parse_calendar_event_time_slot_entries(data.get("timeSlots", [])),
        }
        return result
    @staticmethod
    def parse_calendar_event_time_slot_entry_index(data: Dict[str, Any] | None) -> AulaCalendarEventTimeSlotEntryIndex | None:
        if not data: return None
        result: AulaCalendarEventTimeSlotEntryIndex = {
            "start_time": AulaCalendarParser._parse_datetime(data.get("startTime")),
            "end_time": AulaCalendarParser._parse_datetime(data.get("endTime")),
        }
        return result

    @staticmethod
    def parse_calendar_event_time_slot_entry_indexes(data: List[Dict[str, Any]] | None) -> List[AulaCalendarEventTimeSlotEntryIndex]:
        if data is None: return []
        return list_without_none(map(AulaCalendarParser.parse_calendar_event_time_slot_entry_index, data))

    @staticmethod
    def parse_calendar_event_time_slot_entry_answer(data: Dict[str, Any] | None) -> AulaCalendarEventTimeSlotEntryAnswer | None:
        if not data: return None
        result: AulaCalendarEventTimeSlotEntryAnswer = {
            "concerning_profile_id": AulaCalendarParser._parse_int(data.get("concerningProfileId")),
            "id": AulaCalendarParser._parse_int(data.get("id")),
            "inst_profile_id": AulaCalendarParser._parse_int(data.get("instProfileId")),
            "selected_time_slot_index": AulaCalendarParser._parse_int(data.get("selectedTimeSlotIndex")),
        }
        return result

    @staticmethod
    def parse_calendar_event_time_slot_entry_answers(data: List[Dict[str, Any]] | None) -> List[AulaCalendarEventTimeSlotEntryAnswer]:
        if data is None: return []
        return list_without_none(map(AulaCalendarParser.parse_calendar_event_time_slot_entry_answer, data))

    @staticmethod
    def parse_calendar_event_time_slot_entry(data: Dict[str, Any] | None) -> AulaCalendarEventTimeSlotEntry | None:
        if not data: return None
        result: AulaCalendarEventTimeSlotEntry = {
            "answers": AulaCalendarParser.parse_calendar_event_time_slot_entry_answers(data.get("answers", [])),
            "belongs_to_resource": data.get("belongsToResource"),
            "end_date": AulaCalendarParser._parse_datetime(data.get("endDate")),
            "id": AulaCalendarParser._parse_int(data.get("id")),
            "start_date": AulaCalendarParser._parse_datetime(data.get("startDate")),
            "time_slot_indexes": AulaCalendarParser.parse_calendar_event_time_slot_entry_indexes(data.get("timeSlotIndexes", [])),
        }
        return result

    @staticmethod
    def parse_calendar_event_time_slot_entries(data: List[Dict[str, Any]] | None) -> List[AulaCalendarEventTimeSlotEntry]:
        if data is None: return []
        return list_without_none(map(AulaCalendarParser.parse_calendar_event_time_slot_entry, data))