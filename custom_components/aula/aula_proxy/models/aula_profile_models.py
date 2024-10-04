from dataclasses import dataclass
from datetime import datetime, time
from typing import List, Optional
@dataclass
class AulaProfileAddress:
    id: int
    postal_code: Optional[int|None] = None
    postal_district: Optional[str|None] = None
    street: Optional[str|None] = None

@dataclass
class AulaProfilePicture:
    id: int
    bucket: Optional[str|None] = None
    is_image_scaling_pending: Optional[bool|None] = None
    key: Optional[str|None] = None
    url: Optional[str|None] = None

@dataclass
class AulaInstitutionProfile:
    first_name: str
    full_name: str
    gender: str
    id: int
    institution_code: str
    institution_name: str
    is_primary: bool
    last_name: str
    short_name: str
    access_level: Optional[str|None] = None
    address: Optional[AulaProfileAddress|None] = None
    alias: Optional[bool|None] = None
    aula_email: Optional[str|None] = None
    birthday: Optional[str|None] = None
    communication_blocked: Optional[bool|None] = None
    contact_type: Optional[str|None] = None
    current_user_can_delete_profile_picture: Optional[bool|None] = None
    current_user_can_edit_contact_information: Optional[bool|None] = None
    current_user_can_edit_profile_description: Optional[bool|None] = None
    current_user_can_edit_profile_picture: Optional[bool|None] = None
    current_user_can_see_profile_description: Optional[bool|None] = None
    current_user_can_view_contact_information: Optional[bool|None] = None
    deactivated: Optional[bool|None] = None
    email: Optional[str|None] = None
    groups: Optional[str|None] = None
    has_blocked_communication_channels: Optional[bool|None] = None
    has_custody: Optional[bool|None] = None
    home_phone_number: Optional[str|None] = None
    institution_profile_descriptions: Optional[str|None] = None
    institution_role: Optional[str|None] = None
    institution_type: Optional[str|None] = None
    is_internal_profile_picture: Optional[bool|None] = None
    last_activity: Optional[str|None] = None
    main_group: Optional[str|None] = None
    metadata: Optional[str|None] = None
    mobile_phone_number: Optional[str|None] = None
    municipality_code: Optional[str|None] = None
    municipality_name: Optional[str|None] = None
    new_institution_profile: Optional[bool|None] = None
    profile_picture_url: Optional[str|None] = None
    profile_picture: Optional[AulaProfilePicture|None] = None
    profile_status: Optional[str|None] = None
    relation: Optional[str|None] = None
    role: Optional[str|None] = None
    should_show_decline_consent_two_warning: Optional[bool|None] = None
    user_has_given_consent_to_show_contact_information: Optional[bool|None] = None
    work_phone_number: Optional[str|None] = None

@dataclass
class AulaChildProfile:
    first_name: str
    id: int
    institution_code: str
    institution_profile: AulaInstitutionProfile
    name: str
    profile_id: int
    short_name: str
    user_id: str
    has_custody_or_extended_access: Optional[bool|None] = None
    profile_picture: Optional[AulaProfilePicture|None] = None

@dataclass
class AulaProfile:
    children: List[AulaChildProfile]
    first_name: str
    institution_profiles: List[AulaInstitutionProfile]
    name: str
    profile_id: int
    user_id: str
    age_18_and_older: Optional[bool|None] = None
    contact_info_editable: Optional[bool|None] = None
    is_latest_data_policy_accepted: Optional[bool|None] = None
    over_consent_age: Optional[bool|None] = None
    portal_role: Optional[str|None] = None
    support_role: Optional[bool|None] = None

@dataclass
class AulaToken:
    bearer_token: str
    timestamp: datetime

@dataclass
class AulaWidget:
    id: int
    name: str
    widget_id: str
    can_access_on_mobile: Optional[bool|None] = None
    can_be_placed_inside_module: Optional[bool|None] = None
    can_be_placed_on_full_page: Optional[bool|None] = None
    can_be_placed_on_group: Optional[bool|None] = None
    description: Optional[str|None] = None
    icon_employee: Optional[str|None] = None
    icon_hover: Optional[str|None] = None
    is_pilot: Optional[bool|None] = None
    is_secure: Optional[bool|None] = None
    supports_test_mode: Optional[bool|None] = None
    type: Optional[str|None] = None
    url: Optional[str|None] = None
    widget_supplier: Optional[str|None] = None
    widget_version: Optional[str|None] = None

@dataclass
class AulaLocation:
    description: str
    id: int
    name: str
    end_datetime: Optional[datetime|None] = None
    icon: Optional[str|None] = None
    is_date_intervals_enabled: Optional[bool|None] = None
    is_deactivated: Optional[bool|None] = None
    is_time_intervals_enabled: Optional[bool|None] = None
    is_weekdays_enabled: Optional[bool|None] = None
    start_datetime: Optional[datetime|None] = None
    week_day_mask: Optional[str|None] = None

@dataclass
class AulaGroup:
    id: int
    institution_code: str
    institution_name: str
    name: str
    short_name: str
    uni_group_type: str
    allow_members_to_be_shown: Optional[bool|None] = None
    is_deactivated: Optional[bool|None] = None
    main_group: Optional[bool|None] = None

@dataclass
class AulaDailyOverview:
    id: int
    institution_profile: AulaInstitutionProfile
    status: int
    check_in_time_expected: Optional[time|None] = None
    check_in_time: Optional[time|None] = None
    check_out_time_expected: Optional[time|None] = None
    check_out_time: Optional[time|None] = None
    comment: Optional[str|None] = None
    exit_with: Optional[str|None] = None
    is_default_check_in_time_expected: Optional[bool|None] = None
    is_default_check_out_time_expected: Optional[bool|None] = None
    is_planned_times_outside_opening_hours: Optional[bool|None] = None
    location: Optional[AulaLocation|None] = None
    main_group: Optional[AulaGroup|None] = None
    self_decider_end_time: Optional[time|None] = None
    self_decider_start_time: Optional[time|None] = None
    spare_time_activity: Optional[str|None] = None
    # activity_type: int
    # '''Unsure of the data type in this, need more info to support it wholefully. Always appear to be 0'''
    # editable_presence_states: Optional[List[Any]|None]
    # '''Unsure of the data type in this, need more info to support it wholefully. Always appear empty'''
    # sleep_intervals: Optional[List[Any]|None]
    # '''Unsure of the data type in this, need more info to support it wholefully. Always appear empty'''

@dataclass
class AulaLoginData:
    api_version: int
    profiles: List[AulaProfile]
    widgets: List[AulaWidget]