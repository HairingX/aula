from typing import List
import logging

from ..responses.get_notifications_response import AulaGetNotificationsResponse, AulaNotificationData
from ..utils.list_utils import list_without_none

from .aula_notication_models import *
from .aula_parser import AulaParser

_LOGGER = logging.getLogger(__name__)

class AulaNotificationParser(AulaParser):
    @staticmethod
    def parse_calendar_event(data: AulaNotificationData | None) -> AulaCalendarEventNotification | None:
        if not data: return None
        result = AulaCalendarEventNotification(
            expires=AulaNotificationParser._parse_datetime(data.get("expires"), fix_timezone=True),
            notification_area=AulaNotificationParser._parse_str(data.get("notificationArea")),
            notification_event_type=AulaNotificationParser._parse_str(data.get("notificationEventType")),
            notification_id=AulaNotificationParser._parse_str(data.get("notificationId")),
            notification_type=AulaNotificationParser._parse_str(data.get("notificationType")),
            triggered=AulaNotificationParser._parse_datetime(data.get("triggered"), fix_timezone=True),
            institution_code=AulaNotificationParser._parse_str(data.get("institutionCode")),
            institution_profile_id=AulaNotificationParser._parse_int(data.get("institutionProfileId")),
            end_datetime=AulaNotificationParser._parse_datetime(data.get("endTime"), fix_timezone=True),
            event_id=AulaNotificationParser._parse_int(data.get("eventId")),
            is_all_day_event=AulaNotificationParser._parse_bool(data.get("isAllDayEvent")),
            start_datetime=AulaNotificationParser._parse_datetime(data.get("startTime"), fix_timezone=True),
            title=AulaNotificationParser._parse_str(data.get("title")),
        )
        return result

    @staticmethod
    def parse_message(data: AulaNotificationData | None) -> AulaMessageNotification | None:
        if not data: return None
        result = AulaMessageNotification(
            expires=AulaNotificationParser._parse_datetime(data.get("expires"), fix_timezone=True),
            notification_area=AulaNotificationParser._parse_str(data.get("notificationArea")),
            notification_event_type=AulaNotificationParser._parse_str(data.get("notificationEventType")),
            notification_id=AulaNotificationParser._parse_str(data.get("notificationId")),
            notification_type=AulaNotificationParser._parse_str(data.get("notificationType")),
            triggered=AulaNotificationParser._parse_datetime(data.get("triggered"), fix_timezone=True),
            folder_id=AulaNotificationParser._parse_int(data.get("institutionCode")),
            institution_code=AulaNotificationParser._parse_str(data.get("institutionCode")),
            institution_profile_id=AulaNotificationParser._parse_int(data.get("institutionProfileId")),
            message_text=AulaNotificationParser._parse_str(data.get("messageText")),
            related_institution=AulaNotificationParser._parse_str(data.get("relatedInstitution")),
            sender_name=AulaNotificationParser._parse_str(data.get("senderName")),
            thread_id=AulaNotificationParser._parse_int(data.get("threadId")),
        )
        return result

    @staticmethod
    def parse_post(data: AulaNotificationData | None) -> AulaPostNotification | None:
        if not data: return None
        result = AulaPostNotification(
            expires=AulaNotificationParser._parse_datetime(data.get("expires"), fix_timezone=True),
            notification_area=AulaNotificationParser._parse_str(data.get("notificationArea")),
            notification_event_type=AulaNotificationParser._parse_str(data.get("notificationEventType")),
            notification_id=AulaNotificationParser._parse_str(data.get("notificationId")),
            notification_type=AulaNotificationParser._parse_str(data.get("notificationType")),
            triggered=AulaNotificationParser._parse_datetime(data.get("triggered"), fix_timezone=True),
            institution_code=AulaNotificationParser._parse_str(data.get("institutionCode")),
            institution_profile_id=AulaNotificationParser._parse_int(data.get("institutionProfileId")),
            title=AulaNotificationParser._parse_str(data.get("postTitle")),
        )
        return result

    @staticmethod
    def parse_presence(data: AulaNotificationData | None) -> AulaPresenceNotification | None:
        if not data: return None
        result = AulaPresenceNotification(
            expires=AulaNotificationParser._parse_datetime(data.get("expires"), fix_timezone=True),
            notification_area=AulaNotificationParser._parse_str(data.get("notificationArea")),
            notification_event_type=AulaNotificationParser._parse_str(data.get("notificationEventType")),
            notification_id=AulaNotificationParser._parse_str(data.get("notificationId")),
            notification_type=AulaNotificationParser._parse_str(data.get("notificationType")),
            triggered=AulaNotificationParser._parse_datetime(data.get("triggered"), fix_timezone=True),
            institution_code=AulaNotificationParser._parse_str(data.get("institutionCode")),
            institution_profile_id=AulaNotificationParser._parse_int(data.get("institutionProfileId")),
            end_datetime=AulaNotificationParser._parse_datetime(data.get("endDate"), fix_timezone=True),
            is_presence_times_required=AulaNotificationParser._parse_bool(data.get("isPresenceTimesRequired")),
            message_text=AulaNotificationParser._parse_str(data.get("noteToGuardians")),
            related_child_institution_profile_id=AulaNotificationParser._parse_int(data.get("relatedChildInstitutionProfileId")),
            related_child_name=AulaNotificationParser._parse_str(data.get("relatedChildName")),
            response_deadline=AulaNotificationParser._parse_datetime(data.get("responseDeadline"), fix_timezone=True),
            start_datetime=AulaNotificationParser._parse_datetime(data.get("startDate"), fix_timezone=True),
            vacation_registration_response_id=AulaNotificationParser._parse_int(data.get("vacationRegistrationResponseId")),
            vacation_request_name=AulaNotificationParser._parse_str(data.get("vacationRequestName")),
        )

        ''' Data example:
        {
            "endDate": "2025-04-16T23:59:00+00:00",
            "eventId": 123456789,
            "expires": "2025-03-10T23:59:59+00:00",
            "institutionCode": null,
            "institutionProfileId": 123456,
            "isPresenceTimesRequired": true,
            "noteToGuardians": "Kære forældre.\n\nSå er det muligt at til/framelde jeres barn/børn til pasning de 3 dage op til påskeferien.\n\nObs på at være så præcis som mulig i jeres tilbagemelding, så vi undgår ressourcespild ift. personaletimer. TAK.\n\nVh Alberta",
            "notificationArea": "Presence",
            "notificationEventType": "VacationResponseRequired",
            "notificationId": "VacationResponseRequired:11223344:Alert",
            "notificationType": "Alert",
            "relatedChildInstitutionProfileId": 123456,
            "relatedChildName": "Mulle Bin Bandana",
            "responseDeadline": "2025-03-10T23:59:59+00:00",
            "startDate": "2025-04-14T00:00:00+00:00",
            "triggered": "2025-01-03T10:22:30+00:00",
            "vacationRegistrationResponseId": 11223344,
            "vacationRequestName": "Dagene op til påske 2025"
        }
        '''
        return result

    @staticmethod
    def parse_album(data: AulaNotificationData | None) -> AulaAlbumNotification | None:
        if not data: return None
        result = AulaAlbumNotification(
            expires=AulaNotificationParser._parse_datetime(data.get("expires"), fix_timezone=True),
            notification_area=AulaNotificationParser._parse_str(data.get("notificationArea")),
            notification_event_type=AulaNotificationParser._parse_str(data.get("notificationEventType")),
            notification_id=AulaNotificationParser._parse_str(data.get("notificationId")),
            notification_type=AulaNotificationParser._parse_str(data.get("notificationType")),
            triggered=AulaNotificationParser._parse_datetime(data.get("triggered"), fix_timezone=True),
            album_id=AulaNotificationParser._parse_int(data.get("albumId")),
            institution_code=AulaNotificationParser._parse_str(data.get("institutionCode")),
            institution_profile_id=AulaNotificationParser._parse_int(data.get("institutionProfileId")),
            media_id=AulaNotificationParser._parse_int(data.get("mediaId")),
            related_institution=AulaNotificationParser._parse_str(data.get("relatedInstitution")),
        )
        return result

    @staticmethod
    def parse_gallery(data: AulaNotificationData | None) -> AulaGalleryNotification | None:
        if not data: return None
        result = AulaGalleryNotification(
            expires=AulaNotificationParser._parse_datetime(data.get("expires"), fix_timezone=True),
            notification_area=AulaNotificationParser._parse_str(data.get("notificationArea")),
            notification_event_type=AulaNotificationParser._parse_str(data.get("notificationEventType")),
            notification_id=AulaNotificationParser._parse_str(data.get("notificationId")),
            notification_type=AulaNotificationParser._parse_str(data.get("notificationType")),
            triggered=AulaNotificationParser._parse_datetime(data.get("triggered"), fix_timezone=True),
            album_id=AulaNotificationParser._parse_int(data.get("albumId")),
            institution_code=AulaNotificationParser._parse_str(data.get("institutionCode")),
            institution_profile_id=AulaNotificationParser._parse_int(data.get("institutionProfileId")),
            media_ids=AulaNotificationParser._parse_int_list(data.get("mediaIds")),
            related_institution=AulaNotificationParser._parse_str(data.get("relatedInstitution")),
        )
        return result

    @staticmethod
    def parse_notification(data: AulaNotificationData | None) -> AULA_NOTIFICATION_TYPES | None:
        if not data: return None

        notification_area = data.get("notificationArea")
        match notification_area:
            case NotificationArea.CALENDAR:
                return AulaNotificationParser.parse_calendar_event(data)
            case NotificationArea.MESSAGES:
                return AulaNotificationParser.parse_message(data)
            case NotificationArea.ALBUM:
                return AulaNotificationParser.parse_album(data)
            case NotificationArea.GALLERY:
                return AulaNotificationParser.parse_gallery(data)
            case NotificationArea.POSTS:
                return AulaNotificationParser.parse_post(data)
            case NotificationArea.PRESENCE:
                return AulaNotificationParser.parse_presence(data)
            case _:
                _LOGGER.warning(f"Notification '{notification_area}' is unknown, report to developer: {data}")
                return None

    @staticmethod
    def parse_notifications(data: List[AulaNotificationData] | None) -> List[AULA_NOTIFICATION_TYPES]:
        if data is None: return []
        return list_without_none(map(AulaNotificationParser.parse_notification, data))

    @staticmethod
    def parse_notification_response(data: AulaGetNotificationsResponse | None) -> List[AULA_NOTIFICATION_TYPES]:
        if data is None: return []
        return AulaNotificationParser.parse_notifications(data["data"])