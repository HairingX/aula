import datetime
from typing import List, NotRequired, TypedDict

class AulaProfileAddress(TypedDict):
    id: int

    postal_code: NotRequired[int|None]
    postal_district: NotRequired[str|None]
    street: NotRequired[str|None]

class AulaProfilePicture(TypedDict):
    id: int
    bucket: NotRequired[str|None]
    is_image_scaling_pending: NotRequired[bool|None]
    key: NotRequired[str|None]
    url: NotRequired[str|None]

class AulaInstitutionProfile(TypedDict):
    first_name: str
    full_name: str
    gender: str
    id: int
    institution_code: str
    institution_name: str
    is_primary: bool
    last_name: str
    short_name: str

    access_level: NotRequired[str|None]
    address: NotRequired[AulaProfileAddress|None]
    alias: NotRequired[bool|None]
    aula_email: NotRequired[str|None]
    birthday: NotRequired[str|None]
    communication_blocked: NotRequired[bool|None]
    contact_type: NotRequired[str|None]
    current_user_can_delete_profile_picture: NotRequired[bool|None]
    current_user_can_edit_contact_information: NotRequired[bool|None]
    current_user_can_edit_profile_description: NotRequired[bool|None]
    current_user_can_edit_profile_picture: NotRequired[bool|None]
    current_user_can_see_profile_description: NotRequired[bool|None]
    current_user_can_view_contact_information: NotRequired[bool|None]
    deactivated: NotRequired[bool|None]
    email: NotRequired[str|None]
    groups: NotRequired[str|None]
    has_blocked_communication_channels: NotRequired[bool|None]
    has_custody: NotRequired[bool|None]
    home_phone_number: NotRequired[str|None]
    institution_profile_descriptions: NotRequired[str|None]
    institution_role: NotRequired[str|None]
    institution_type: NotRequired[str|None]
    is_internal_profile_picture: NotRequired[bool|None]
    last_activity: NotRequired[str|None]
    main_group: NotRequired[str|None]
    metadata: NotRequired[str|None]
    mobile_phone_number: NotRequired[str|None]
    municipality_code: NotRequired[str|None]
    municipality_name: NotRequired[str|None]
    new_institution_profile: NotRequired[bool|None]
    profile_picture_url: NotRequired[str|None]
    profile_picture: NotRequired[AulaProfilePicture|None]
    profile_status: NotRequired[str|None]
    relation: NotRequired[str|None]
    role: NotRequired[str|None]
    should_show_decline_consent_two_warning: NotRequired[bool|None]
    user_has_given_consent_to_show_contact_information: NotRequired[bool|None]
    work_phone_number: NotRequired[str|None]

class AulaChildProfile(TypedDict):
    id: int
    institution_code: str
    institution_profile: AulaInstitutionProfile
    name: str
    profile_id: int
    short_name: str
    user_id: str

    has_custody_or_extended_access: NotRequired[bool|None]
    profile_picture: NotRequired[AulaProfilePicture|None]

class AulaProfile(TypedDict):
    profile_id: int
    display_name: str
    children: List[AulaChildProfile]
    institution_profiles: List[AulaInstitutionProfile]

    user_id: NotRequired[str|None]
    age_18_and_older: NotRequired[bool|None]
    contact_info_editable: NotRequired[bool|None]
    is_latest_data_policy_accepted: NotRequired[bool|None]
    over_consent_age: NotRequired[bool|None]
    portal_role: NotRequired[str|None]
    support_role: NotRequired[bool|None]

class AulaToken(TypedDict):
    # token: str
    bearer_token: str
    timestamp: datetime.datetime

class AulaWidget(TypedDict):
    id: int
    name: str
    widget_id: str
    can_access_on_mobile: NotRequired[bool|None]
    can_be_placed_inside_module: NotRequired[bool|None]
    can_be_placed_on_full_page: NotRequired[bool|None]
    can_be_placed_on_group: NotRequired[bool|None]
    description: NotRequired[str|None]
    icon_employee: NotRequired[str|None]
    icon_hover: NotRequired[str|None]
    is_pilot: NotRequired[bool|None]
    is_secure: NotRequired[bool|None]
    supports_test_mode: NotRequired[bool|None]
    type: NotRequired[str|None]
    url: NotRequired[str|None]
    widget_supplier: NotRequired[str|None]
    widget_version: NotRequired[str|None]

class AulaLocation(TypedDict):
    id: int
    name: str
    description: str

    end_date: NotRequired[datetime.date|None]
    end_time: NotRequired[datetime.time|None]
    icon: NotRequired[str|None]
    is_date_intervals_enabled: NotRequired[bool|None]
    is_deactivated: NotRequired[bool|None]
    is_time_intervals_enabled: NotRequired[bool|None]
    is_weekdays_enabled: NotRequired[bool|None]
    start_date: NotRequired[datetime.date|None]
    start_time: NotRequired[datetime.time|None]
    week_day_mask: NotRequired[str|None]

class AulaGroup(TypedDict):
    id: int
    name: str
    short_name: str
    institution_code: str
    institution_name: str
    uni_group_type: str
    main_group: NotRequired[bool|None]
    is_deactivated: NotRequired[bool|None]
    allow_members_to_be_shown: NotRequired[bool|None]

class AulaDailyOverview(TypedDict):
    id: int
    institution_profile: AulaInstitutionProfile
    status: int
    # activity_type: int
    # '''Unsure of the data type in this, need more info to support it wholefully. Always appear to be 0'''

    check_in_time: NotRequired[datetime.time|None]
    check_out_time: NotRequired[datetime.time|None]
    comment: NotRequired[str|None]
    check_in_time_expected: NotRequired[datetime.time|None]
    check_out_time_expected: NotRequired[datetime.time|None]
    exit_with: NotRequired[str|None]
    is_default_check_in_time_expected: NotRequired[bool|None]
    is_default_check_out_time_expected: NotRequired[bool|None]
    is_planned_times_outside_opening_hours: NotRequired[bool|None]
    location: NotRequired[AulaLocation|None]
    main_group: NotRequired[AulaGroup|None]
    self_decider_end_time: NotRequired[datetime.time|None]
    self_decider_start_time: NotRequired[datetime.time|None]
    spare_time_activity: NotRequired[str|None]
    # editable_presence_states: NotRequired[List[Any]|None]
    # '''Unsure of the data type in this, need more info to support it wholefully. Always appear empty'''
    # sleep_intervals: NotRequired[List[Any]|None]
    # '''Unsure of the data type in this, need more info to support it wholefully. Always appear empty'''

class AulaLoginData(TypedDict):
    profiles: List[AulaProfile]
    widgets: List[AulaWidget]
    api_version: int