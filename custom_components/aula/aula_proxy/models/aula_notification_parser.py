from typing import List
import logging

from ..responses.get_notifications_response import AulaGetNotificationsResponse, AulaNotificationData
from ..utils.list_utils import list_without_none

from .aula_notication_models import AULA_NOTIFICATION_TYPES, AulaAlbumNotification, AulaCalendarEventNotification, AulaGalleryNotification, AulaMessageNotification, NotificationArea
from .aula_parser import AulaParser

_LOGGER = logging.getLogger(__name__)

class AulaNotificationParser(AulaParser):
    @staticmethod
    def parse_calendar_event(data: AulaNotificationData | None) -> AulaCalendarEventNotification | None:
        if not data: return None
        result = AulaCalendarEventNotification(
            expires=AulaNotificationParser._parse_datetime(data.get("expires")),
            notification_area=AulaNotificationParser._parse_str(data.get("notificationArea")),
            notification_event_type=AulaNotificationParser._parse_str(data.get("notificationEventType")),
            notification_id=AulaNotificationParser._parse_str(data.get("notificationId")),
            notification_type=AulaNotificationParser._parse_str(data.get("notificationType")),
            triggered=AulaNotificationParser._parse_datetime(data.get("triggered")),
            institution_code=AulaNotificationParser._parse_str(data.get("institutionCode")),
            institution_profile_id=AulaNotificationParser._parse_int(data.get("institutionProfileId")),
            end_datetime=AulaNotificationParser._parse_datetime(data.get("endTime")),
            event_id=AulaNotificationParser._parse_int(data.get("eventId")),
            is_all_day_event=AulaNotificationParser._parse_bool(data.get("isAllDayEvent")),
            start_datetime=AulaNotificationParser._parse_datetime(data.get("startTime")),
            title=AulaNotificationParser._parse_str(data.get("title")),
        )
        return result

    @staticmethod
    def parse_message(data: AulaNotificationData | None) -> AulaMessageNotification | None:
        if not data: return None
        result = AulaMessageNotification(
            expires=AulaNotificationParser._parse_datetime(data.get("expires")),
            notification_area=AulaNotificationParser._parse_str(data.get("notificationArea")),
            notification_event_type=AulaNotificationParser._parse_str(data.get("notificationEventType")),
            notification_id=AulaNotificationParser._parse_str(data.get("notificationId")),
            notification_type=AulaNotificationParser._parse_str(data.get("notificationType")),
            triggered=AulaNotificationParser._parse_datetime(data.get("triggered")),
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
    def parse_album(data: AulaNotificationData | None) -> AulaAlbumNotification | None:
        if not data: return None
        result = AulaAlbumNotification(
            expires=AulaNotificationParser._parse_datetime(data.get("expires")),
            notification_area=AulaNotificationParser._parse_str(data.get("notificationArea")),
            notification_event_type=AulaNotificationParser._parse_str(data.get("notificationEventType")),
            notification_id=AulaNotificationParser._parse_str(data.get("notificationId")),
            notification_type=AulaNotificationParser._parse_str(data.get("notificationType")),
            triggered=AulaNotificationParser._parse_datetime(data.get("triggered")),
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
            expires=AulaNotificationParser._parse_datetime(data.get("expires")),
            notification_area=AulaNotificationParser._parse_str(data.get("notificationArea")),
            notification_event_type=AulaNotificationParser._parse_str(data.get("notificationEventType")),
            notification_id=AulaNotificationParser._parse_str(data.get("notificationId")),
            notification_type=AulaNotificationParser._parse_str(data.get("notificationType")),
            triggered=AulaNotificationParser._parse_datetime(data.get("triggered")),
            album_id=AulaNotificationParser._parse_int(data.get("albumId")),
            institution_code=AulaNotificationParser._parse_str(data.get("institutionCode")),
            institution_profile_id=AulaNotificationParser._parse_int(data.get("institutionProfileId")),
            media_ids=AulaNotificationParser._parse_int_list(data.get("mediaIds")),
            related_institution=AulaNotificationParser._parse_str(data.get("relatedInstitution")),
        )
        return result

    @staticmethod
    def parse_notification(data: AulaNotificationData | None) -> AULA_NOTIFICATION_TYPES | None:#AulaAlbumNotificationEvent | AulaCalendarEventNotification | AulaGalleryNotificationEvent | AulaMessageNotificationEvent | AulaGenericEvent | None:
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