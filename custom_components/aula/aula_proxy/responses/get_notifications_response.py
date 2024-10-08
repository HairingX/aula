from typing import NotRequired, TypedDict, List

class AulaNotificationData(TypedDict):
    notificationId: str
    institutionProfileId: int
    notificationEventType: str
    notificationArea: str
    notificationType: str
    institutionCode: str
    expires: str
    triggered: str
    title: NotRequired[str|None]
    eventId: NotRequired[int|None]
    startTime: NotRequired[str|None]
    endTime: NotRequired[str|None]
    relatedChildInstitutionProfileId: NotRequired[int|None]
    isAllDayEvent: NotRequired[bool|None]
    messageText: NotRequired[str|None]
    senderName: NotRequired[str|None]
    relatedInstitution: NotRequired[str|None]
    folderId: NotRequired[int|None]
    threadId: NotRequired[int|None]
    albumId: NotRequired[int|None]
    albumName: NotRequired[str|None]
    mediaIds: NotRequired[List[int]|None]
    relatedChildName: NotRequired[str|None]
    mediaId: NotRequired[int|None]
    postTitle: NotRequired[str|None]
    postId: NotRequired[int|None]
    groupName: NotRequired[str|None]
    groupId: NotRequired[int|None]

class AulaNotificationStatusData(TypedDict):
    code: int
    message: NotRequired[str|None]

class AulaGetNotificationsResponse(TypedDict):
    status: AulaNotificationStatusData
    data: List[AulaNotificationData]
    version: int
    module: str
    method: str
