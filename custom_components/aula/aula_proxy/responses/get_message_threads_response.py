from typing import TypedDict, List

from .common_data import AulaStatusData

class AulaMessageTextData(TypedDict):
    html: str

class AulaThreadRecipientData(TypedDict):
    answerDirectlyName: str
    fullName: str
    metadata: str

class AulaThreadChildData(TypedDict):
    displayName: str
    profileId: int
    shortName: str

class AulaThreadLatestMessageData(TypedDict):
    id: str
    sendDateTime: str
    text: AulaMessageTextData

class AulaThreadData(TypedDict):
    creator: AulaThreadRecipientData
    extraRecipientsCount: int
    id: int
    institutionCode: str
    isArchived: bool
    isThreadOrSubscriptionDeleted: bool
    latestMessage: AulaThreadLatestMessageData
    marked: bool
    muted: bool
    read: bool
    recipients: List[AulaThreadRecipientData]
    regardingChildren: List[AulaThreadChildData]
    sensitive: bool
    startedTime: str
    subject: str

class AulaThreadsData(TypedDict):
    moreMessagesExist: bool
    page: int
    threads: List[AulaThreadData]

class AulaGetMessageThreadsResponse(TypedDict):
    data: AulaThreadsData
    status: AulaStatusData
    version: int
