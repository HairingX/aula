from typing import NotRequired, TypedDict, List

from .common_data import AulaStatusData

class AulaNotificationData(TypedDict):
    expires: str
    institutionCode: str
    institutionProfileId: int
    notificationArea: str
    notificationEventType: str
    notificationId: str
    notificationType: str
    triggered: str
    albumId: NotRequired[int|None]
    endTime: NotRequired[str|None]
    eventId: NotRequired[int|None]
    folderId: NotRequired[int|None]  # best guess for issue #10; verify against real payload
    isAllDayEvent: NotRequired[bool|None]
    mediaId: NotRequired[int|None]
    mediaIds: NotRequired[List[int]|None]
    messageText: NotRequired[str|None]
    postId: NotRequired[int|None]
    postTitle: NotRequired[str|None]
    relatedChildName: NotRequired[str|None]
    relatedInstitution: NotRequired[str|None]
    senderName: NotRequired[str|None]
    startTime: NotRequired[str|None]
    threadId: NotRequired[int|None]
    title: NotRequired[str|None]

class AulaGetNotificationsResponse(TypedDict):
    data: List[AulaNotificationData]
    status: AulaStatusData
    version: int
