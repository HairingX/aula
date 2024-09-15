from typing import Any, List, NotRequired, TypedDict

class AulaProfileContextStatusData(TypedDict):
    code: NotRequired[int|None]
    message: NotRequired[str|None]

class AulaProfileContextAddressData(TypedDict):
    id: NotRequired[int|None]
    postalCode: NotRequired[int|None]
    postalDistrict: NotRequired[str|None]
    street: NotRequired[str|None]

class AulaProfileContextProfilePictureData(TypedDict):
    bucket: NotRequired[str|None]
    id: NotRequired[int|None]
    isImageScalingPending: NotRequired[bool|None]
    key: NotRequired[str|None]
    url: NotRequired[str|None]

class AulaProfileContextAdministrativeAuthorityData(TypedDict):
    id: NotRequired[int|None]
    institutionCodes: NotRequired[List[str]|None]
    name: NotRequired[str|None]

class AulaProfileContextInstitutionData(TypedDict):
    administrativeAuthority: NotRequired[AulaProfileContextAdministrativeAuthorityData|None]
    institutionCode: NotRequired[str|None]
    institutionName: NotRequired[str|None]
    municipalityCode: NotRequired[str|None]
    municipalityName: NotRequired[str|None]
    type: NotRequired[str|None]

class AulaProfileContextRelationData(TypedDict):
    firstName: NotRequired[str|None]
    fullName: NotRequired[str|None]
    gender: NotRequired[str|None]
    id: NotRequired[int|None]
    institution: NotRequired[AulaProfileContextInstitutionData|None]
    lastName: NotRequired[str|None]
    mailBoxId: NotRequired[int|None]
    mainGroupName: NotRequired[str|None]
    metadata: NotRequired[str|None]
    profileId: NotRequired[int|None]
    profilePicture: NotRequired[AulaProfileContextProfilePictureData|None]
    role: NotRequired[str|None]
    shortName: NotRequired[str|None]
    uniPersonId: NotRequired[int|None]

class AulaProfileContextInstitutionProfileData(TypedDict):
    address: NotRequired[AulaProfileContextAddressData|None]
    birthday: NotRequired[str|None]
    communicationBlock: NotRequired[bool|None]
    delegatedCalendarProfiles: NotRequired[List[Any]|None]
    email: NotRequired[str|None]
    encryptionKey: NotRequired[str|None]
    firstName: NotRequired[str|None]
    fullName: NotRequired[str|None]
    gender: NotRequired[str|None]
    id: NotRequired[int|None]
    institution: NotRequired[AulaProfileContextInstitutionData|None]
    lastName: NotRequired[str|None]
    mailBoxId: NotRequired[int|None]
    mainGroupName: NotRequired[str|None]
    metadata: NotRequired[str|None]
    phone: NotRequired[str|None]
    profileId: NotRequired[int|None]
    profilePicture: NotRequired[AulaProfileContextProfilePictureData|None]
    relations: NotRequired[List[AulaProfileContextRelationData]|None]
    role: NotRequired[str|None]
    shortName: NotRequired[str|None]
    uniPersonId: NotRequired[int|None]

class AulaProfileContextChildData(TypedDict):
    hasCustodyOrExtendedAccess: NotRequired[bool|None]
    id: NotRequired[int|None]
    institutionCode: NotRequired[str|None]
    name: NotRequired[str|None]
    profileId: NotRequired[int|None]
    profilePicture: NotRequired[AulaProfileContextProfilePictureData|None]
    shortName: NotRequired[str|None]
    userId: NotRequired[str|None]

class AulaProfileContextGroupData(TypedDict):
    dashboardEnabled: NotRequired[bool|None]
    description: NotRequired[str|None]
    endTime: NotRequired[str|None]
    groupType: NotRequired[str|None]
    id: NotRequired[int|None]
    membershipId: NotRequired[int|None]
    membershipType: NotRequired[str|None]
    name: NotRequired[str|None]
    role: NotRequired[str|None]
    uniGroupId: NotRequired[str|None]

class AulaProfileContextPermissionData(TypedDict):
    groupScopes: NotRequired[List[int]|None]
    institutionScope: NotRequired[bool|None]
    permissionId: NotRequired[int|None]
    stepUp: NotRequired[bool|None]

class AulaProfileContextInstitutionDetailsData(TypedDict):
    administrativeAuthority: NotRequired[AulaProfileContextAdministrativeAuthorityData|None]
    children: NotRequired[List[AulaProfileContextChildData]|None]
    groups: NotRequired[List[AulaProfileContextGroupData]|None]
    institutionCode: NotRequired[str|None]
    institutionProfileId: NotRequired[int|None]
    institutionRole: NotRequired[str|None]
    institutionType: NotRequired[str|None]
    mailboxId: NotRequired[int|None]
    municipalityCode: NotRequired[str|None]
    name: NotRequired[str|None]
    permissions: NotRequired[List[AulaProfileContextPermissionData]|None]
    shortName: NotRequired[str|None]

class AulaProfileContextMunicipalGroupData(TypedDict):
    dashboardEnabled: NotRequired[bool|None]
    description: NotRequired[str|None]
    endTime: NotRequired[str|None]
    groupType: NotRequired[str|None]
    id: NotRequired[int|None]
    membershipId: NotRequired[int|None]
    membershipInstitutions: NotRequired[List[str]|None]
    membershipType: NotRequired[str|None]
    name: NotRequired[str|None]
    role: NotRequired[str|None]
    uniGroupId: NotRequired[str|None]

class AulaProfileContextWidgetData(TypedDict):
    canAccessOnMobile: NotRequired[bool|None]
    canBePlacedInsideModule: NotRequired[bool|None]
    canBePlacedOnFullPage: NotRequired[bool|None]
    canBePlacedOnGroup: NotRequired[bool|None]
    description: NotRequired[str|None]
    icon: NotRequired[str|None]
    iconEmployee: NotRequired[str|None]
    iconHover: NotRequired[str|None]
    id: NotRequired[int|None]
    isPilot: NotRequired[bool|None]
    isSecure: NotRequired[bool|None]
    name: NotRequired[str|None]
    supportsTestMode: NotRequired[bool|None]
    type: NotRequired[str|None]
    url: NotRequired[str|None]
    widgetId: NotRequired[str|None]
    widgetSupplier: NotRequired[str|None]
    widgetVersion: NotRequired[str|None]

class AulaProfileContextRestrictedGroupData(TypedDict):
    id: NotRequired[int|None]
    name: NotRequired[str|None]
    shortName: NotRequired[str|None]
    institutionCode: NotRequired[str|None]
    institutionName: NotRequired[str|None]
    mainGroup: NotRequired[bool|None]
    uniGroupType: NotRequired[str|None]
    isDeactivated: NotRequired[bool|None]
    allowMembersToBeShown: NotRequired[bool|None]

class AulaProfileContextWidgetConfigurationData(TypedDict):
    widget: AulaProfileContextWidgetData

    aggregatedDisplayMode: NotRequired[str|None]
    centralDisplayMode: NotRequired[str|None]
    id: NotRequired[int|None]
    institutionDisplayMode: NotRequired[str|None]
    institutionRole: NotRequired[str|None]
    municipalityDisplayMode: NotRequired[str|None]
    order: NotRequired[int|None]
    placement: NotRequired[str|None]
    restrictedGroups: NotRequired[List[AulaProfileContextRestrictedGroupData]|None]
    scope: NotRequired[str|None]

class AulaProfileContextPageConfigurationData(TypedDict):
    widgetConfigurations: List[AulaProfileContextWidgetConfigurationData]

class AulaProfileContextData(TypedDict):
    pageConfiguration: AulaProfileContextPageConfigurationData
    userId: str

    groupHomes: NotRequired[List[Any]|None]
    homePhonenumber: NotRequired[str|None]
    id: NotRequired[int|None]
    institutionProfile: NotRequired[AulaProfileContextInstitutionProfileData|None]
    institutions: NotRequired[List[AulaProfileContextInstitutionDetailsData]|None]
    isGroupHomeAdmin: NotRequired[bool|None]
    isSteppedUp: NotRequired[bool|None]
    loginPortalRole: NotRequired[str|None]
    mobilePhonenumber: NotRequired[str|None]
    municipalAdmin: NotRequired[bool|None]
    municipalGroups: NotRequired[List[AulaProfileContextMunicipalGroupData]|None]
    portalRole: NotRequired[str|None]
    supportRole: NotRequired[bool|None]
    workPhonenumber: NotRequired[str|None]


class AulaGetProfileContextResponse(TypedDict):
    data: AulaProfileContextData
    method: str
    module: str
    status: AulaProfileContextStatusData
    version: int
