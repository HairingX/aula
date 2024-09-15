import datetime
from typing import Any, List, NotRequired, TypedDict

from .aula_profile_models import AulaProfilePicture

class AulaThreadRecipient(TypedDict):
    answer_directly_name: str
    full_name: str
    metadata: str

class AulaMessageText(TypedDict):
    html: str

class AulaMessage(TypedDict):
    id: str
    message_type: str
    send_datetime: datetime.datetime
    text: NotRequired[AulaMessageText|None]
    deleted_at: NotRequired[datetime.datetime|None]
    has_attachments: NotRequired[bool|None]
    pending_media: NotRequired[bool|None]
    leaver_names: NotRequired[str|None]
    inviter_name: NotRequired[str|None]
    sender: NotRequired[AulaThreadRecipient|None]
    new_recipients: NotRequired[List[AulaThreadRecipient]|None]
    original_recipients: NotRequired[List[AulaThreadRecipient]|None]
    recipients: NotRequired[List[AulaThreadRecipient]|None]
    attachments: NotRequired[List[Any]|None]
    can_reply_to_message: NotRequired[bool|None]

class AulaMessagePreview(TypedDict):
    id: str
    send_datetime: datetime.datetime
    text: NotRequired[AulaMessageText|None]

class AulaThreadRegardingChild(TypedDict):
    display_name: str
    profile_id: int
    profile_picture: NotRequired[AulaProfilePicture|None]
    short_name: str

class AulaMessageThread(TypedDict):
    creator: NotRequired[AulaThreadRecipient|None]
    extra_recipients_count: int
    id: int
    institution_code: str
    is_archived: bool
    is_thread_or_subscription_deleted: bool
    last_read_message_id: str
    latest_message: NotRequired[AulaMessagePreview|None]
    marked: bool
    muted: bool
    read: bool
    recipients: List[AulaThreadRecipient]
    regarding_children: List[AulaThreadRegardingChild]
    sensitive: bool
    started_time: datetime.datetime
    subject: str
    subscription_id: NotRequired[int|None]
    subscription_type: NotRequired[str|None]

    leave_time: NotRequired[datetime.datetime|None]
    number_of_bundle_items: NotRequired[int|None]