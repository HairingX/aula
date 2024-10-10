from typing import List

from ..responses.get_events_by_profile_ids_and_resource_ids import *
from ..utils.list_utils import list_without_none
from .aula_calendar_models import AulaCalendarEvent, AulaCalendarEventLesson, AulaCalendarEventLessonParticipant, AulaCalendarEventResource, AulaCalendarEventTimeSlot, AulaCalendarEventTimeSlotEntry, AulaCalendarEventTimeSlotEntryAnswer, AulaCalendarEventTimeSlotEntryIndex
from .aula_parser import AulaParser

class AulaCalendarParser(AulaParser):

    @staticmethod
    def parse_calendar_event(data: AulaEventData | None) -> AulaCalendarEvent | None:
        if not data: return None
        result = AulaCalendarEvent(
            all_day = AulaCalendarParser._parse_bool(data.get("allDay")),
            belongs_to_profiles = list(map(AulaCalendarParser._parse_int, data.get("belongsToProfiles", []))),
            belongs_to_resources = data.get("belongsToResources", []),
            created_datetime = AulaCalendarParser._parse_datetime(data.get("createdDateTime")),
            end_datetime = AulaCalendarParser._parse_datetime(data.get("endDateTime")),
            has_attachments = AulaCalendarParser._parse_bool(data.get("hasAttachments")),
            id = AulaCalendarParser._parse_int(data.get("id")),
            requires_new_answer = AulaCalendarParser._parse_bool(data.get("requiresNewAnswer")),
            response_required = AulaCalendarParser._parse_bool(data.get("responseRequired")),
            start_datetime = AulaCalendarParser._parse_datetime(data.get("startDateTime")),
            title = AulaCalendarParser._parse_str(data.get("title")),
            type = AulaCalendarParser._parse_str(data.get("type")),
            lesson = AulaCalendarParser.parse_calendar_event_lesson(data.get("lesson")),
            primary_resource = AulaCalendarParser.parse_calendar_event_resource(data.get("primaryResource")),
            repeating = AulaCalendarParser._parse_nullable_bool(data.get("repeating")),
            response_deadline = AulaCalendarParser._parse_nullable_datetime(data.get("responseDeadline")),
            response_status = AulaCalendarParser._parse_nullable_str(data.get("responseStatus")),
            time_slot = AulaCalendarParser.parse_calendar_event_time_slot(data.get("timeSlot")),
        )

        return result

    @staticmethod
    def parse_calendar_events(data: List[AulaEventData] | None) -> List[AulaCalendarEvent]:
        if data is None: return []
        return list_without_none(map(AulaCalendarParser.parse_calendar_event, data))

    @staticmethod
    def parse_calendar_event_resource(data: AulaPrimaryResourceData  | None) -> AulaCalendarEventResource | None:
        if not data: return None
        result = AulaCalendarEventResource(
            id = AulaCalendarParser._parse_int(data.get("id")),
            name = AulaCalendarParser._parse_str(data.get("name")),
        )
        return result

    @staticmethod
    def parse_calendar_event_resources(data: List[AulaPrimaryResourceData ] | None) -> List[AulaCalendarEventResource]:
        if data is None: return []
        return list_without_none(map(AulaCalendarParser.parse_calendar_event_resource, data))

    @staticmethod
    def parse_calendar_event_lesson_participant(data: AulaLessonParticipantData | None) -> AulaCalendarEventLessonParticipant | None:
        if not data: return None
        result = AulaCalendarEventLessonParticipant(
            participant_role = AulaCalendarParser._parse_str(data.get("participantRole")),
            teacher_id = AulaCalendarParser._parse_int(data.get("teacherId")),
            teacher_initials = AulaCalendarParser._parse_str(data.get("teacherInitials")),
            teacher_name = AulaCalendarParser._parse_str(data.get("teacherName")),
        )
        return result

    @staticmethod
    def parse_calendar_event_lesson_participants(data: List[AulaLessonParticipantData] | None) -> List[AulaCalendarEventLessonParticipant]:
        if data is None: return []
        return list_without_none(map(AulaCalendarParser.parse_calendar_event_lesson_participant, data))

    @staticmethod
    def parse_calendar_event_lesson(data: AulaLessonData | None) -> AulaCalendarEventLesson | None:
        if not data: return None
        result = AulaCalendarEventLesson(
            lesson_id = AulaCalendarParser._parse_str(data.get("lessonId")),
            lesson_status = AulaCalendarParser._parse_str(data.get("lessonStatus")),
            participants = AulaCalendarParser.parse_calendar_event_lesson_participants(data.get("participants")),
        )
        return result

    @staticmethod
    def parse_calendar_event_time_slot(data: AulaTimeSlotData  | None) -> AulaCalendarEventTimeSlot | None:
        if not data: return None
        result = AulaCalendarEventTimeSlot(
            # child_required = AulaCalendarParser._parse_bool(data.get("childRequired")),
            time_slots = AulaCalendarParser.parse_calendar_event_time_slot_entries(data.get("timeSlots", [])),
        )
        return result
    @staticmethod
    def parse_calendar_event_time_slot_entry_index(data: AulaTimeSlotIndexData | None) -> AulaCalendarEventTimeSlotEntryIndex | None:
        if not data: return None
        result = AulaCalendarEventTimeSlotEntryIndex(
            start_datetime = AulaCalendarParser._parse_datetime(data.get("startTime")),
            end_datetime = AulaCalendarParser._parse_datetime(data.get("endTime")),
        )
        return result

    @staticmethod
    def parse_calendar_event_time_slot_entry_indexes(data: List[AulaTimeSlotIndexData] | None) -> List[AulaCalendarEventTimeSlotEntryIndex]:
        if data is None: return []
        return list_without_none(map(AulaCalendarParser.parse_calendar_event_time_slot_entry_index, data))

    @staticmethod
    def parse_calendar_event_time_slot_entry_answer(data: AulaAnswerData | None) -> AulaCalendarEventTimeSlotEntryAnswer | None:
        if not data: return None
        result = AulaCalendarEventTimeSlotEntryAnswer(
            concerning_profile_id = AulaCalendarParser._parse_int(data.get("concerningProfileId")),
            id = AulaCalendarParser._parse_int(data.get("id")),
            inst_profile_id = AulaCalendarParser._parse_int(data.get("instProfileId")),
            selected_time_slot_index = AulaCalendarParser._parse_int(data.get("selectedTimeSlotIndex")),
        )
        return result

    @staticmethod
    def parse_calendar_event_time_slot_entry_answers(data: List[AulaAnswerData] | None) -> List[AulaCalendarEventTimeSlotEntryAnswer]:
        if data is None: return []
        return list_without_none(map(AulaCalendarParser.parse_calendar_event_time_slot_entry_answer, data))

    @staticmethod
    def parse_calendar_event_time_slot_entry(data: AulaTimeSlotDetailData | None) -> AulaCalendarEventTimeSlotEntry | None:
        if not data: return None
        result = AulaCalendarEventTimeSlotEntry(
            answers = AulaCalendarParser.parse_calendar_event_time_slot_entry_answers(data.get("answers", [])),
            end_date = AulaCalendarParser._parse_datetime(data.get("endDate")),
            id = AulaCalendarParser._parse_int(data.get("id")),
            start_date = AulaCalendarParser._parse_datetime(data.get("startDate")),
            time_slot_indexes = AulaCalendarParser.parse_calendar_event_time_slot_entry_indexes(data.get("timeSlotIndexes", [])),
        )
        return result

    @staticmethod
    def parse_calendar_event_time_slot_entries(data: List[AulaTimeSlotDetailData] | None) -> List[AulaCalendarEventTimeSlotEntry]:
        if data is None: return []
        return list_without_none(map(AulaCalendarParser.parse_calendar_event_time_slot_entry, data))



    @staticmethod
    def parse_calendar_event_response(data: AulaGetEventsByProfileIdsAndResourceIdsResponse | None) -> List[AulaCalendarEvent]:
        if data is None: return []
        return AulaCalendarParser.parse_calendar_events(data["data"])
