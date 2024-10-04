from typing import Any, Dict, List

from ..utils.list_utils import list_without_none
from .aula_message_thread_models import AulaMessage, AulaMessagePreview, AulaMessageText, AulaMessageThread, AulaThreadRecipient, AulaThreadRegardingChild
from .aula_parser import AulaParser
from .aula_profile_parser import AulaProfileParser

class AulaMessageThreadParser(AulaParser):

    @staticmethod
    def parse_message_thread_recipient(data: Dict[str, Any] | None) -> AulaThreadRecipient :
        if not data: raise ValueError()
        result = AulaThreadRecipient(
            answer_directly_name = AulaMessageThreadParser._parse_str(data.get("answerDirectlyName")),
            full_name = AulaMessageThreadParser._parse_str(data.get("fullName")),
            metadata = AulaMessageThreadParser._parse_str(data.get("metadata")),
        )
        return result

    @staticmethod
    def parse_message_thread_recipients(data: List[Dict[str, Any]] | None) -> List[AulaThreadRecipient]:
        if data is None: return []
        return list_without_none(map(AulaMessageThreadParser.parse_message_thread_recipient, data))

    @staticmethod
    def parse_message_thread_regarding_child(data: Dict[str, Any] | None) -> AulaThreadRegardingChild:
        if not data: raise ValueError()
        result = AulaThreadRegardingChild(
            display_name = AulaMessageThreadParser._parse_str(data.get("displayName")),
            profile_id = AulaMessageThreadParser._parse_int(data.get("profileId")),
            profile_picture = AulaProfileParser.parse_picture(data.get("profilePicture")),
            short_name = AulaMessageThreadParser._parse_str(data.get("shortName")),
        )
        return result

    @staticmethod
    def parse_message_thread_regarding_children(data: List[Dict[str, Any]] | None) -> List[AulaThreadRegardingChild]:
        if data is None: return []
        return list_without_none(map(AulaMessageThreadParser.parse_message_thread_regarding_child, data))

    @staticmethod
    def parse_message_text(data: Dict[str, Any] | None) -> AulaMessageText | None:
        if not data: return None
        result = AulaMessageText(
            html = AulaMessageThreadParser._parse_str(data.get("html")),
        )
        return result

    @staticmethod
    def parse_message(data: Dict[str, Any] | None) -> AulaMessage | None:
        if not data: raise ValueError()
        result = AulaMessage(
            attachments = data.get("attachments", []),
            can_reply_to_message = AulaMessageThreadParser._parse_nullable_bool(data.get("canReplyToMessage")),
            deleted_at = AulaMessageThreadParser._parse_nullable_datetime(data.get("deletedAt")),
            has_attachments = AulaMessageThreadParser._parse_nullable_bool(data.get("hasAttachments")),
            id = AulaMessageThreadParser._parse_str(data.get("id")),
            inviter_name = AulaMessageThreadParser._parse_nullable_str(data.get("inviterName")),
            leaver_names = AulaMessageThreadParser._parse_nullable_str(data.get("leaverNames")),
            message_type = AulaMessageThreadParser._parse_str(data.get("messageType")),
            new_recipients = list_without_none(map(AulaMessageThreadParser.parse_message_thread_recipient, data.get("newRecipients", []))),
            original_recipients = list_without_none(map(AulaMessageThreadParser.parse_message_thread_recipient, data.get("originalRecipients", []))),
            pending_media = AulaMessageThreadParser._parse_nullable_bool(data.get("pendingMedia")),
            send_datetime = AulaMessageThreadParser._parse_datetime(data.get("sendDateTime")),
            sender = AulaMessageThreadParser.parse_message_thread_recipient(data.get("sender")),
            text = AulaMessageThreadParser.parse_message_text(data.get("text")),
        )
        return result

    @staticmethod
    def parse_message_preview(data: Dict[str, Any] | None) -> AulaMessagePreview | None:
        if not data: raise ValueError()
        result = AulaMessagePreview(
            id = AulaMessageThreadParser._parse_str(data.get("id")),
            send_datetime = AulaMessageThreadParser._parse_datetime(data.get("sendDateTime")),
            text = AulaMessageThreadParser.parse_message_text(data.get("text")),
        )
        return result

    @staticmethod
    def parse_messages(data: List[Dict[str, Any]] | None) -> List[AulaMessage]:
        if data is None: return []
        return list_without_none(map(AulaMessageThreadParser.parse_message, data))

    @staticmethod
    def parse_message_thread(data: Dict[str, Any] | None) -> AulaMessageThread | None:
        if not data: return None
        result = AulaMessageThread(
            creator = AulaMessageThreadParser.parse_message_thread_recipient(data.get("creator")),
            extra_recipients_count = AulaMessageThreadParser._parse_int(data.get("extraRecipientsCount", 0)),
            id = AulaMessageThreadParser._parse_int(data.get("id", 0)),
            institution_code = AulaMessageThreadParser._parse_str(data.get("institutionCode")),
            is_archived = data.get("isArchived") == True,
            is_thread_or_subscription_deleted = data.get("isThreadOrSubscriptionDeleted") == True,
            last_read_message_id = AulaMessageThreadParser._parse_str(data.get("lastReadMessageId")),
            latest_message = AulaMessageThreadParser.parse_message_preview(data.get("latestMessage")),
            marked = data.get("marked") == True,
            muted = data.get("muted") == True,
            read = data.get("read") == True,
            recipients = AulaMessageThreadParser.parse_message_thread_recipients(data.get("recipients")),
            regarding_children = AulaMessageThreadParser.parse_message_thread_regarding_children(data.get("regardingChildren")),
            sensitive = data.get("sensitive") == True,
            started_time = AulaMessageThreadParser._parse_datetime(data.get("startedTime")),
            subject = AulaMessageThreadParser._parse_str(data.get("subject")),
            subscription_id = AulaMessageThreadParser._parse_nullable_int(data.get("subscriptionId", 0)),
            subscription_type = AulaMessageThreadParser._parse_str(data.get("subscriptionType")),
            leave_time = AulaMessageThreadParser._parse_nullable_datetime(data.get("leaveTime")),
            number_of_bundle_items = AulaMessageThreadParser._parse_nullable_int(data.get("numberOfBundleItems")),
        )
        return result

    @staticmethod
    def parse_message_threads(data: List[Dict[str, Any]] | None) -> List[AulaMessageThread]:
        if data is None: return []
        return list_without_none(map(AulaMessageThreadParser.parse_message_thread, data))