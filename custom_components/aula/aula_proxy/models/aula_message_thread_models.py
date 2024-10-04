from dataclasses import dataclass
import datetime
from typing import Any, List, Optional

from .aula_profile_models import AulaProfilePicture

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
    send_datetime: datetime.datetime
    attachments: Optional[List[Any]|None] = None
    can_reply_to_message: Optional[bool|None] = None
    deleted_at: Optional[datetime.datetime|None] = None
    has_attachments: Optional[bool|None] = None
    inviter_name: Optional[str|None] = None
    leaver_names: Optional[str|None] = None
    new_recipients: Optional[List[AulaThreadRecipient]|None] = None
    original_recipients: Optional[List[AulaThreadRecipient]|None] = None
    pending_media: Optional[bool|None] = None
    recipients: Optional[List[AulaThreadRecipient]|None] = None
    sender: Optional[AulaThreadRecipient|None] = None
    text: Optional[AulaMessageText|None] = None

@dataclass
class AulaMessagePreview:
    id: str
    send_datetime: datetime.datetime
    text: Optional[AulaMessageText|None] = None

@dataclass
class AulaThreadRegardingChild:
    display_name: str
    profile_id: int
    short_name: str
    profile_picture: Optional[AulaProfilePicture|None] = None

@dataclass
class AulaMessageThread:
    extra_recipients_count: int
    id: int
    institution_code: str
    is_archived: bool
    is_thread_or_subscription_deleted: bool
    last_read_message_id: str
    marked: bool
    muted: bool
    read: bool
    recipients: List[AulaThreadRecipient]
    regarding_children: List[AulaThreadRegardingChild]
    sensitive: bool
    started_time: datetime.datetime
    subject: str
    creator: Optional[AulaThreadRecipient|None] = None
    latest_message: Optional[AulaMessagePreview|None] = None
    leave_time: Optional[datetime.datetime|None] = None
    number_of_bundle_items: Optional[int|None] = None
    subscription_id: Optional[int|None] = None
    subscription_type: Optional[str|None] = None