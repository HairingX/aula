from typing import List

from ..responses.get_messages_for_thread_response import *
from ..responses.get_message_threads_response import *
from ..utils.list_utils import list_without_none

from .aula_message_thread_models import AulaMessage, AulaMessagePreview, AulaMessageText, AulaMessageThread, AulaThreadRecipient, AulaThreadRegardingChild
from .aula_parser import AulaParser

class AulaMessageThreadParser(AulaParser):

    @staticmethod
    def parse_message_contact(data: AulaThreadRecipientData | None) -> AulaThreadRecipient :
        if not data: raise ValueError()
        result = AulaThreadRecipient(
            answer_directly_name = AulaMessageThreadParser._parse_str(data.get("answerDirectlyName")),
            full_name = AulaMessageThreadParser._parse_str(data.get("fullName")),
            metadata = AulaMessageThreadParser._parse_str(data.get("metadata")),
        )
        return result

    @staticmethod
    def parse_message_contacts(data: List[AulaThreadRecipientData] | None) -> List[AulaThreadRecipient]:
        if data is None: return []
        return list_without_none(map(AulaMessageThreadParser.parse_message_contact, data))

    @staticmethod
    def parse_message_thread_regarding_child(data: AulaThreadChildData | None) -> AulaThreadRegardingChild:
        if not data: raise ValueError()
        result = AulaThreadRegardingChild(
            display_name = AulaMessageThreadParser._parse_str(data.get("displayName")),
            profile_id = AulaMessageThreadParser._parse_int(data.get("profileId")),
            short_name = AulaMessageThreadParser._parse_str(data.get("shortName")),
        )
        return result

    @staticmethod
    def parse_message_thread_regarding_children(data: List[AulaThreadChildData] | None) -> List[AulaThreadRegardingChild]:
        if data is None: return []
        return list_without_none(map(AulaMessageThreadParser.parse_message_thread_regarding_child, data))

    @staticmethod
    def parse_message_text(data: AulaMessageTextData | None) -> AulaMessageText | None:
        if not data: return None
        result = AulaMessageText(
            html = AulaMessageThreadParser._parse_str(data.get("html")),
        )
        return result

    @staticmethod
    def parse_message(data: AulaMessageData | None) -> AulaMessage | None:
        if not data: raise ValueError()
        result = AulaMessage(
            can_reply_to_message = AulaMessageThreadParser._parse_nullable_bool(data.get("canReplyToMessage")),
            has_attachments = AulaMessageThreadParser._parse_nullable_bool(data.get("hasAttachments")),
            id = AulaMessageThreadParser._parse_str(data.get("id")),
            message_type = AulaMessageThreadParser._parse_str(data.get("messageType")),
            send_datetime = AulaMessageThreadParser._parse_datetime(data.get("sendDateTime"), fix_timezone=False),
            sender = AulaMessageThreadParser.parse_message_contact(data.get("sender")),
            text = AulaMessageThreadParser.parse_message_text(data.get("text")),
        )
        return result

    @staticmethod
    def parse_message_preview(data: AulaThreadLatestMessageData | None) -> AulaMessagePreview | None:
        if not data: raise ValueError()
        result = AulaMessagePreview(
            id = AulaMessageThreadParser._parse_str(data.get("id")),
            send_datetime = AulaMessageThreadParser._parse_datetime(data.get("sendDateTime"), fix_timezone=False),
            text = AulaMessageThreadParser.parse_message_text(data.get("text")),
        )
        return result

    @staticmethod
    def parse_messages(data: List[AulaMessageData] | None) -> List[AulaMessage]:
        if data is None: return []
        return list_without_none(map(AulaMessageThreadParser.parse_message, data))

    @staticmethod
    def parse_messages_response(data: AulaGetMessagesForThreadResponse | None) -> List[AulaMessage]:
        if data is None: return []
        return AulaMessageThreadParser.parse_messages(data["data"]["messages"])

    @staticmethod
    def parse_message_thread(data: AulaThreadData | None) -> AulaMessageThread | None:
        if not data: return None
        result = AulaMessageThread(
            creator = AulaMessageThreadParser.parse_message_contact(data.get("creator")),
            extra_recipients_count = AulaMessageThreadParser._parse_int(data.get("extraRecipientsCount", 0)),
            id = AulaMessageThreadParser._parse_int(data.get("id", 0)),
            institution_code = AulaMessageThreadParser._parse_str(data.get("institutionCode")),
            is_archived = data.get("isArchived") == True,
            is_thread_or_subscription_deleted = data.get("isThreadOrSubscriptionDeleted") == True,
            latest_message = AulaMessageThreadParser.parse_message_preview(data.get("latestMessage")),
            marked = data.get("marked") == True,
            muted = data.get("muted") == True,
            read = data.get("read") == True,
            recipients = AulaMessageThreadParser.parse_message_contacts(data.get("recipients")),
            regarding_children = AulaMessageThreadParser.parse_message_thread_regarding_children(data.get("regardingChildren")),
            sensitive = data.get("sensitive") == True,
            started_datetime = AulaMessageThreadParser._parse_datetime(data.get("startedTime"), fix_timezone=False),
            subject = AulaMessageThreadParser._parse_str(data.get("subject")),
        )
        return result

    @staticmethod
    def parse_message_threads(data: List[AulaThreadData] | None) -> List[AulaMessageThread]:
        if data is None: return []
        return list_without_none(map(AulaMessageThreadParser.parse_message_thread, data))

    @staticmethod
    def parse_message_threads_response(data: AulaGetMessageThreadsResponse | None) -> List[AulaMessageThread]:
        if data is None: return []
        return AulaMessageThreadParser.parse_message_threads(data["data"]["threads"])