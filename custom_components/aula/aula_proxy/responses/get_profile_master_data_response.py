from typing import List, NotRequired, TypedDict

from .common_data import AulaStatusData

class AulaProfileMasterDataInstitutionGroupData(TypedDict):
    name: NotRequired[str|None]
    id: int
    shortName: NotRequired[str|None]

class AulaProfileMasterDataRelationData(TypedDict):
    id: NotRequired[int|None]
    mainGroup: NotRequired[AulaProfileMasterDataInstitutionGroupData|None]

class AulaProfileMasterDataInstitutionProfileData(TypedDict):
    relations: NotRequired[List[AulaProfileMasterDataRelationData]|None]

class AulaGetProfileMasterData(TypedDict):
    institutionProfiles: NotRequired[List[AulaProfileMasterDataInstitutionProfileData]|None]

class AulaGetProfileMasterDataResponse(TypedDict):
    data: AulaGetProfileMasterData
    status: AulaStatusData
    version: int
