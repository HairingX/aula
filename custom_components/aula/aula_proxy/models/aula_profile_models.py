from dataclasses import dataclass
from datetime import datetime, time
from typing import List, Optional
@dataclass
class AulaProfilePicture:
    id: int
    bucket: Optional[str|None] = None
    is_image_scaling_pending: Optional[bool|None] = None
    key: Optional[str|None] = None
    url: Optional[str|None] = None

@dataclass
class AulaInstitutionProfile:
    id: int
    institution_code: str
    institution_name: str
    metadata: Optional[str|None] = None

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
    profile_picture: Optional[AulaProfilePicture|None] = None

@dataclass
class AulaProfile:
    children: List[AulaChildProfile]
    first_name: str
    institution_profiles: List[AulaInstitutionProfile]
    name: str
    profile_id: int
    user_id: str
    is_latest_data_policy_accepted: Optional[bool|None] = None

@dataclass
class AulaToken:
    bearer_token: str
    timestamp: datetime

@dataclass
class AulaWidget:
    id: int
    name: str
    widget_id: str
    description: Optional[str|None] = None
    icon: Optional[str|None] = None
    widget_supplier: Optional[str|None] = None
    widget_version: Optional[str|None] = None

@dataclass
class AulaLocation:
    description: str
    id: int
    name: str
    end_datetime: Optional[datetime|None] = None
    icon: Optional[str|None] = None
    start_datetime: Optional[datetime|None] = None

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