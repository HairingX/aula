from typing import NotRequired, TypedDict, List

from .common_data import AulaStatusData
from .get_message_threads_response import AulaThreadRecipientData, AulaMessageTextData

class AulaMessageData(TypedDict):
    canReplyToMessage: bool
    hasAttachments: bool
    id: str
    messageType: str
    sendDateTime: str
    sender: NotRequired[AulaThreadRecipientData|None]
    text: NotRequired[AulaMessageTextData|None]

class AulaMessagesForThreadData(TypedDict):
    extraRecipientsCount: NotRequired[int|None]
    hasSecureDocuments: bool
    id: int
    institutionCode: str
    isArchived: bool
    lastReadMessageId: str
    marked: bool
    messages: List[AulaMessageData]
    moreMessagesExist: bool
    muted: bool
    page: int
    recipients: List[AulaThreadRecipientData]
    sensitive: bool
    subject: str
    threadCreator: AulaThreadRecipientData
    threadStartedDateTime: str
    totalMessageCount: int

class AulaGetMessagesForThreadResponse(TypedDict):
    data: AulaMessagesForThreadData
    status: AulaStatusData
    version: int
