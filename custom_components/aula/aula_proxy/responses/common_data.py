from typing import NotRequired, TypedDict


class AulaStatusData(TypedDict):
    code: int
    message: str

class AulaProfilePictureData(TypedDict):
    bucket: NotRequired[str|None]
    id: NotRequired[str|None]
    isImageScalingPending: NotRequired[bool|None]
    key: NotRequired[str|None]
    url: NotRequired[str|None]