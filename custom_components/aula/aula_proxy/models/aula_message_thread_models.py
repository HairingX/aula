from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import List, Optional


class AulaMessageType(StrEnum):
    RECIPIENTS_ADDED= "RecipientsAdded"
    RECIPIENTS_REMOVED = "RecipientsRemoved"
    MESSAGE = "Message"

@dataclass
class AulaThreadRecipient:
    answer_directly_name: str
    full_name: str
    metadata: str

@dataclass
class AulaMessageText:
    html: str

@dataclass
class AulaMessage:
    id: str
    message_type: str
    send_datetime: datetime
    can_reply_to_message: Optional[bool|None] = None
    has_attachments: Optional[bool|None] = None
    recipients: Optional[List[AulaThreadRecipient]|None] = None
    sender: Optional[AulaThreadRecipient|None] = None
    text: Optional[AulaMessageText|None] = None

@dataclass
class AulaMessagePreview:
    id: str
    send_datetime: datetime
    text: Optional[AulaMessageText|None] = None

@dataclass
class AulaThreadRegardingChild:
    display_name: str
    profile_id: int
    short_name: str

@dataclass
class AulaMessageThread:
    extra_recipients_count: int
    id: int
    institution_code: str
    is_archived: bool
    is_thread_or_subscription_deleted: bool
    marked: bool
    muted: bool
    read: bool
    recipients: List[AulaThreadRecipient]
    regarding_children: List[AulaThreadRegardingChild]
    sensitive: bool
    started_datetime: datetime
    subject: str
    creator: Optional[AulaThreadRecipient|None] = None
    latest_message: Optional[AulaMessagePreview|None] = None