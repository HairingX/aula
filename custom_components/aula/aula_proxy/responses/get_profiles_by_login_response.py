from typing import NotRequired, TypedDict, List

from .common_data import AulaProfilePictureData, AulaStatusData

class AulaInstitutionProfileData(TypedDict):
    id: NotRequired[int|None]
    institutionCode: NotRequired[str|None]
    institutionName: NotRequired[str|None]
    metadata: NotRequired[str|None]

class AulaChildData(TypedDict):
    id: NotRequired[int|None]
    institutionCode: NotRequired[str|None]
    institutionProfile: NotRequired[AulaInstitutionProfileData|None]
    name: NotRequired[str|None]
    profileId: NotRequired[int|None]
    profilePicture: NotRequired[AulaProfilePictureData|None]
    shortName: NotRequired[str|None]
    userId: NotRequired[str|None]

class AulaProfileData(TypedDict):
    children: NotRequired[List[AulaChildData]|None]
    displayName: NotRequired[str|None]
    institutionProfiles: NotRequired[List[AulaInstitutionProfileData]|None]
    isLatestDataPolicyAccepted: NotRequired[bool|None]
    profileId: NotRequired[int|None]

class AulaGetProfilesByLoginResponseData(TypedDict):
    profiles: NotRequired[List[AulaProfileData]|None]

class AulaGetProfilesByLoginResponse(TypedDict):
    data: AulaGetProfilesByLoginResponseData
    status: AulaStatusData
    version: int