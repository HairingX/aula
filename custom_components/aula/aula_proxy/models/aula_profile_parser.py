from typing import List
from datetime import datetime, timedelta

from ..responses.common_data import AulaProfilePictureData
from ..responses.get_daily_overview_response import *
from ..responses.get_profiles_by_login_response import *
from ..responses.get_profile_context_response import *
from ..responses.get_profile_master_data_response import *
from ..utils.list_utils import list_without_none

from .aula_parser import AulaParser
from .aula_profile_models import *

class AulaProfileParser(AulaParser):
    @staticmethod
    def parse_profile(data: AulaProfileData | None) -> AulaProfile | None:
        if not data: return None
        result = AulaProfile(
            children = AulaProfileParser.parse_children(data.get("children")),
            first_name = AulaProfileParser._parse_str(data.get("displayName")).split()[0],
            institution_profiles = AulaProfileParser.parse_institutions(data.get("institutionProfiles")),
            is_latest_data_policy_accepted = AulaProfileParser._parse_nullable_bool(data.get("isLatestDataPolicyAccepted")),
            name = AulaProfileParser._parse_str(data.get("displayName")),
            profile_id = AulaProfileParser._parse_int(data.get("profileId", 0)),
            user_id= "",
        )
        return result

    @staticmethod
    def parse_profiles(data: List[AulaProfileData] | None) -> List[AulaProfile]:
        if data is None: return []
        return list_without_none(map(AulaProfileParser.parse_profile, data))

    @staticmethod
    def parse_picture(data: AulaProfilePictureData | None) -> AulaProfilePicture | None:
        if not data: return None
        result = AulaProfilePicture(
            bucket = AulaProfileParser._parse_nullable_str(data.get("bucket")),
            id = AulaProfileParser._parse_int(data.get("id")),
            is_image_scaling_pending = AulaProfileParser._parse_nullable_bool(data.get("isImageScalingPending")),
            key = AulaProfileParser._parse_nullable_str(data.get("key")),
            url = AulaProfileParser._parse_nullable_str(data.get("url")),
        )
        return result

    @staticmethod
    def parse_child(data: AulaChildData | None) -> AulaChildProfile | None:
        if not data: return None
        result = AulaChildProfile(
            first_name = AulaProfileParser._parse_str(data.get("name")).split()[0],
            id = AulaProfileParser._parse_int(data.get("id")),
            institution_code = AulaProfileParser._parse_str(data.get("institutionCode")),
            institution_profile = AulaProfileParser.parse_institution(data.get("institutionProfile")),
            main_group= AulaInstitutionGroup(id=0, name="", short_name=""), # this is assigned later, as it is not present in the data object
            name = AulaProfileParser._parse_str(data.get("name")),
            profile_id = AulaProfileParser._parse_int(data.get("profileId")),
            profile_picture = AulaProfileParser.parse_picture(data.get("profilePicture")),
            short_name = AulaProfileParser._parse_str(data.get("shortName")),
            user_id = AulaProfileParser._parse_str(data.get("userId")),
        )
        return result

    @staticmethod
    def parse_children(data: List[AulaChildData] | None) -> List[AulaChildProfile]:
        if not data: return []
        return list_without_none(map(AulaProfileParser.parse_child, data))

    @staticmethod
    def parse_institution(data: AulaInstitutionProfileData|AulaDailyOverviewInstitutionProfileData| None) -> AulaInstitutionProfile:
        if not data: raise ValueError()
        result = AulaInstitutionProfile(
            id = AulaProfileParser._parse_int(data.get("id", 0)),
            institution_code = AulaProfileParser._parse_str(data.get("institutionCode")),
            institution_name = AulaProfileParser._parse_str(data.get("institutionName")),
            metadata = AulaProfileParser._parse_nullable_str(data.get("metadata")),
        )
        return result

    @staticmethod
    def parse_institutions(data: List[AulaInstitutionProfileData] | List[AulaDailyOverviewInstitutionProfileData] | None) -> List[AulaInstitutionProfile]:
        if data is None: return []
        return list_without_none(map(AulaProfileParser.parse_institution, data))

    @staticmethod
    def parse_widget(data: AulaProfileContextWidgetData) -> AulaWidget | None:
        if not data: return None
        result = AulaWidget(
            description = AulaProfileParser._parse_nullable_str(data.get("description")),
            icon = AulaProfileParser._parse_nullable_str(data.get("icon")),
            id = AulaProfileParser._parse_int(data.get("id", 0)),
            name = AulaProfileParser._parse_str(data.get("name")),
            widget_id = AulaProfileParser._parse_str(data.get("widgetId")),
            widget_supplier = AulaProfileParser._parse_nullable_str(data.get("widgetSupplier")),
            widget_version = AulaProfileParser._parse_nullable_str(data.get("widgetVersion")),
        )
        return result

    @staticmethod
    def parse_widgets(data: List[AulaProfileContextWidgetData] | None) -> List[AulaWidget]:
        if data is None: return []
        return list_without_none(map(AulaProfileParser.parse_widget, data))

    @staticmethod
    def parse_location(data: AulaDailyOverviewLocationData | None) -> AulaLocation | None:
        if not data: return None

        start_datetime: datetime|None = None
        start_date = AulaProfileParser._parse_nullable_date(data.get("startDate"))
        start_time = AulaProfileParser._parse_nullable_time(data.get("startTime"), fix_timezone=False)
        if start_date is not None:
            start_datetime = datetime(year=start_date.year, month=start_date.month, day=start_date.day)
            if start_time is not None:
                start_datetime += timedelta(hours=start_time.hour, minutes=start_time.minute, seconds=start_time.second, microseconds=start_time.microsecond)

        end_datetime: datetime|None = None
        end_date = AulaProfileParser._parse_nullable_date(data.get("endDate"))
        end_time = AulaProfileParser._parse_nullable_time(data.get("endTime"), fix_timezone=False)
        if end_date is not None:
            end_datetime = datetime(year=end_date.year, month=end_date.month, day=end_date.day)
            if end_time is not None:
                end_datetime += timedelta(hours=end_time.hour, minutes=end_time.minute, seconds=end_time.second, microseconds=end_time.microsecond)

        result = AulaLocation(
            description = AulaProfileParser._parse_str(data.get("description")),
            end_datetime = end_datetime,
            icon = AulaProfileParser._parse_nullable_icon_str(data.get("symbol")),
            id = AulaProfileParser._parse_int(data.get("id", 0)),
            name = AulaProfileParser._parse_str(data.get("name")),
            start_datetime = start_datetime,
        )
        return result

    @staticmethod
    def parse_daily_overview(data: AulaDailyOverviewData | None) -> AulaDailyOverview | None:
        if not data: return None
        result = AulaDailyOverview(
            check_in_time = AulaProfileParser._parse_nullable_time(data.get("checkInTime"), fix_timezone=False),
            check_in_time_expected = AulaProfileParser._parse_nullable_time(data.get("entryTime"), fix_timezone=False),
            check_out_time = AulaProfileParser._parse_nullable_time(data.get("checkOutTime"), fix_timezone=False),
            check_out_time_expected = AulaProfileParser._parse_nullable_time(data.get("exitTime"), fix_timezone=False),
            comment = AulaProfileParser._parse_nullable_str(data.get("comment")),
            exit_with = AulaProfileParser._parse_nullable_str(data.get("exitWith")),
            id = AulaProfileParser._parse_int(data.get("id", 0)),
            institution_profile = AulaProfileParser.parse_institution(data.get("institutionProfile")),
            is_default_check_in_time_expected = AulaProfileParser._parse_nullable_bool(data.get("isDefaultEntryTime")),
            is_default_check_out_time_expected = AulaProfileParser._parse_nullable_bool(data.get("isDefaultExitTime")),
            is_planned_times_outside_opening_hours = AulaProfileParser._parse_nullable_bool(data.get("isPlannedTimesOutsideOpeningHours")),
            location = AulaProfileParser.parse_location(data.get("location")),
            spare_time_activity = AulaProfileParser._parse_nullable_str(data.get("spareTimeActivity")),
            status = AulaProfileParser._parse_int(data.get("status", 0)),
        )
        return result

    @staticmethod
    def parse_institution_group(data: AulaProfileMasterDataInstitutionGroupData | None) -> AulaInstitutionGroup | None:
        if not data: return None
        result = AulaInstitutionGroup(
            id = AulaProfileParser._parse_int(data.get("id")),
            name = AulaProfileParser._parse_str(data.get("name")),
            short_name = AulaProfileParser._parse_str(data.get("shortName")),
        )
        return result

    @staticmethod
    def parse_profile_relation(data: AulaProfileMasterDataRelationData | None) -> AulaProfileRelation | None:
        if not data: return None
        inst_group = AulaProfileParser.parse_institution_group(data.get("mainGroup"))
        result = AulaProfileRelation(
            child_id = AulaProfileParser._parse_int(data.get("id")),
            main_group = inst_group if inst_group else AulaInstitutionGroup(id=0, name="", short_name=""),
        )
        return result

    @staticmethod
    def parse_daily_overviews(data: List[AulaDailyOverviewData] | None) -> List[AulaDailyOverview]:
        if data is None: return []
        return list_without_none(map(AulaProfileParser.parse_daily_overview, data))

    @staticmethod
    def parse_daily_overview_response(data: AulaGetDailyOverviewResponse | None) -> List[AulaDailyOverview]:
        if data is None: return []
        return AulaProfileParser.parse_daily_overviews(data["data"])

    @staticmethod
    def parse_profiles_response(data: AulaGetProfilesByLoginResponse | None) -> List[AulaProfile]:
        if not data: return []
        d = data.get("data")
        if not d: return []
        return AulaProfileParser.parse_profiles(d.get("profiles"))

    @staticmethod
    def parse_profile_master_data_response(data: AulaGetProfileMasterDataResponse | None) -> List[AulaProfileRelation]:
        if not data: return []
        d = data.get("data")
        if not d: return []
        institution_profiles = d.get("institutionProfiles")
        if not institution_profiles: return []
        result = list[AulaProfileRelation]()
        for institution_profile in institution_profiles:
            relations = institution_profile.get("relations")
            if not relations: continue
            for relation in relations:
                relation = AulaProfileParser.parse_profile_relation(relation)
                if relation: result.append(relation)
        return result