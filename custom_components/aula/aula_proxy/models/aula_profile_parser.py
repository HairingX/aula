from typing import Any, Dict, List
from datetime import datetime, timedelta

from ..responses.common_data import AulaProfilePictureData
from ..responses.get_daily_overview_response import *
from ..responses.get_profile_context_response import *
from ..utils.list_utils import list_without_none

from .aula_parser import AulaParser
from .aula_profile_models import AulaDailyOverview, AulaGroup, AulaLocation, AulaWidget, AulaChildProfile, AulaInstitutionProfile, AulaProfile, AulaProfileAddress, AulaProfilePicture

class AulaProfileParser(AulaParser):
    @staticmethod
    def parse_profile(data: Dict[str, Any] | None) -> AulaProfile | None:
        if not data: return None

        result = AulaProfile(
            age_18_and_older = AulaProfileParser._parse_nullable_bool(data.get("age18AndOlder")),
            children = AulaProfileParser.parse_children(data.get("children")),
            contact_info_editable = AulaProfileParser._parse_nullable_bool(data.get("contactInfoEditable")),
            first_name = AulaProfileParser._parse_str(data.get("displayName")).split()[0],
            institution_profiles = AulaProfileParser.parse_institutions(data.get("institutionProfiles")),
            is_latest_data_policy_accepted = AulaProfileParser._parse_nullable_bool(data.get("isLatestDataPolicyAccepted")),
            name = AulaProfileParser._parse_str(data.get("displayName")),
            over_consent_age = AulaProfileParser._parse_nullable_bool(data.get("overConsentAge")),
            portal_role = AulaProfileParser._parse_nullable_str(data.get("portalRole")),
            profile_id = AulaProfileParser._parse_int(data.get("profileId", 0)),
            support_role = AulaProfileParser._parse_nullable_bool(data.get("supportRole")),
            user_id= "",
        )

        return result

    @staticmethod
    def parse_profiles(data: List[Dict[str, Any]] | None) -> List[AulaProfile]:
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
    def parse_child(data: Dict[str, Any] | None) -> AulaChildProfile | None:
        if not data: return None
        result = AulaChildProfile(
            first_name = AulaProfileParser._parse_str(data.get("name")).split()[0],
            has_custody_or_extended_access = AulaProfileParser._parse_nullable_bool(data.get("hasCustodyOrExtendedAccess")),
            id = AulaProfileParser._parse_int(data.get("id")),
            institution_code = AulaProfileParser._parse_str(data.get("institutionCode")),
            institution_profile = AulaProfileParser.parse_institution(data.get("institutionProfile")),
            name = AulaProfileParser._parse_str(data.get("name")),
            profile_id = AulaProfileParser._parse_int(data.get("profileId")),
            profile_picture = AulaProfileParser.parse_picture(data.get("profilePicture")),
            short_name = AulaProfileParser._parse_str(data.get("shortName")),
            user_id = AulaProfileParser._parse_str(data.get("userId")),
        )

        return result

    @staticmethod
    def parse_children(data: List[Dict[str, Any]] | None) -> List[AulaChildProfile]:
        if not data: return []
        return list_without_none(map(AulaProfileParser.parse_child, data))

    @staticmethod
    def parse_institution(data: AulaDailyOverviewInstitutionProfileData | None) -> AulaInstitutionProfile:
        if not data: raise ValueError()
        result = AulaInstitutionProfile(
            access_level = AulaProfileParser._parse_nullable_str(data.get("accessLevel")),
            address = AulaProfileParser.parse_address(data.get("address")),
            alias = AulaProfileParser._parse_nullable_bool(data.get("alias")),
            aula_email = AulaProfileParser._parse_nullable_str(data.get("aulaEmail")),
            birthday = AulaProfileParser._parse_nullable_str(data.get("birthday")),
            communication_blocked = AulaProfileParser._parse_nullable_bool(data.get("communicationBlocked")),
            contact_type = AulaProfileParser._parse_nullable_str(data.get("contactType")),
            current_user_can_delete_profile_picture = AulaProfileParser._parse_nullable_bool(data.get("currentUserCanDeleteProfilePicture")),
            current_user_can_edit_contact_information = AulaProfileParser._parse_nullable_bool(data.get("currentUserCanEditContactInformation")),
            current_user_can_edit_profile_description = AulaProfileParser._parse_nullable_bool(data.get("currentUserCanEditProfileDescription")),
            current_user_can_edit_profile_picture = AulaProfileParser._parse_nullable_bool(data.get("currentUserCanEditProfilePicture")),
            current_user_can_see_profile_description = AulaProfileParser._parse_nullable_bool(data.get("currentUserCanSeeProfileDescription")),
            current_user_can_view_contact_information = AulaProfileParser._parse_nullable_bool(data.get("currentUserCanViewContactInformation")),
            deactivated = AulaProfileParser._parse_nullable_bool(data.get("deactivated")),
            email = AulaProfileParser._parse_nullable_str(data.get("email")),
            first_name = AulaProfileParser._parse_str(data.get("firstName")),
            full_name = AulaProfileParser._parse_str(data.get("fullName")),
            gender = AulaProfileParser._parse_str(data.get("gender")),
            groups = AulaProfileParser._parse_nullable_str(data.get("groups")),
            has_blocked_communication_channels = AulaProfileParser._parse_nullable_bool(data.get("hasBlockedCommunicationChannels")),
            has_custody = AulaProfileParser._parse_nullable_bool(data.get("hasCustody")),
            home_phone_number = AulaProfileParser._parse_nullable_str(data.get("homePhoneNumber")),
            id = AulaProfileParser._parse_int(data.get("id", 0)),
            institution_code = AulaProfileParser._parse_str(data.get("institutionCode")),
            institution_name = AulaProfileParser._parse_str(data.get("institutionName")),
            institution_profile_descriptions = AulaProfileParser._parse_nullable_str(data.get("institutionProfileDescriptions")),
            institution_role = AulaProfileParser._parse_nullable_str(data.get("institutionRole")),
            institution_type = AulaProfileParser._parse_nullable_str(data.get("institutionType")),
            is_internal_profile_picture = AulaProfileParser._parse_nullable_bool(data.get("isInternalProfilePicture")),
            is_primary = data.get("isPrimary") == True,
            last_activity = AulaProfileParser._parse_nullable_str(data.get("lastActivity")),
            last_name = AulaProfileParser._parse_str(data.get("lastName")),
            main_group = AulaProfileParser._parse_nullable_str(data.get("mainGroup")),
            metadata = AulaProfileParser._parse_nullable_str(data.get("metadata")),
            mobile_phone_number = AulaProfileParser._parse_nullable_str(data.get("mobilePhoneNumber")),
            municipality_code = AulaProfileParser._parse_nullable_str(data.get("municipalityCode")),
            municipality_name = AulaProfileParser._parse_nullable_str(data.get("municipalityName")),
            new_institution_profile = AulaProfileParser._parse_nullable_bool(data.get("newInstitutionProfile")),
            profile_picture = AulaProfileParser.parse_picture(data.get("profilePicture")),
            profile_picture_url = AulaProfileParser._parse_nullable_str(data.get("profilePictureUrl")),
            profile_status = AulaProfileParser._parse_nullable_str(data.get("profileStatus")),
            relation = AulaProfileParser._parse_nullable_str(data.get("relation")),
            role = AulaProfileParser._parse_nullable_str(data.get("role")),
            short_name = AulaProfileParser._parse_str(data.get("shortName")),
            should_show_decline_consent_two_warning = AulaProfileParser._parse_nullable_bool(data.get("shouldShowDeclineConsentTwoWarning")),
            user_has_given_consent_to_show_contact_information = AulaProfileParser._parse_nullable_bool(data.get("userHasGivenConsentToShowContactInformation")),
            work_phone_number = AulaProfileParser._parse_nullable_str(data.get("workPhoneNumber")),
        )

        return result

    @staticmethod
    def parse_institutions(data: List[AulaDailyOverviewInstitutionProfileData] | None) -> List[AulaInstitutionProfile]:
        if data is None: return []
        return list_without_none(map(AulaProfileParser.parse_institution, data))

    @staticmethod
    def parse_address(data: Dict[str, Any] | None) -> AulaProfileAddress | None:
        if not data: return None
        result = AulaProfileAddress(
            id = AulaProfileParser._parse_int(data.get("id", 0)),
            postal_code = AulaProfileParser._parse_int(data.get("postalCode", 0)),
            postal_district = AulaProfileParser._parse_nullable_str(data.get("postalDistrict")),
            street = AulaProfileParser._parse_nullable_str(data.get("street")),
        )
        return result

    @staticmethod
    def parse_widget(data: AulaProfileContextWidgetData) -> AulaWidget | None:
        if not data: return None
        result = AulaWidget(
            can_access_on_mobile = AulaProfileParser._parse_nullable_bool(data.get("canAccessOnMobile")),
            can_be_placed_inside_module = AulaProfileParser._parse_nullable_bool(data.get("canBePlacedInsideModule")),
            can_be_placed_on_full_page = AulaProfileParser._parse_nullable_bool(data.get("canBePlacedOnFullPage")),
            can_be_placed_on_group = AulaProfileParser._parse_nullable_bool(data.get("canBePlacedOnGroup")),
            description = AulaProfileParser._parse_nullable_str(data.get("description")),
            icon_employee = AulaProfileParser._parse_nullable_str(data.get("iconEmployee")),
            icon_hover = AulaProfileParser._parse_nullable_str(data.get("iconHover")),
            id = AulaProfileParser._parse_int(data.get("id", 0)),
            is_pilot = AulaProfileParser._parse_nullable_bool(data.get("isPilot")),
            is_secure = AulaProfileParser._parse_nullable_bool(data.get("isSecure")),
            name = AulaProfileParser._parse_str(data.get("name")),
            supports_test_mode = AulaProfileParser._parse_nullable_bool(data.get("supportsTestMode")),
            type = AulaProfileParser._parse_nullable_str(data.get("type")),
            url = AulaProfileParser._parse_nullable_str(data.get("url")),
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
        start_time = AulaProfileParser._parse_nullable_time(data.get("startTime"))
        if start_date is not None:
            start_datetime = datetime(year=start_date.year, month=start_date.month, day=start_date.day)
            if start_time is not None:
                start_datetime += timedelta(hours=start_time.hour, minutes=start_time.minute, seconds=start_time.second, microseconds=start_time.microsecond)

        end_datetime: datetime|None = None
        end_date = AulaProfileParser._parse_nullable_date(data.get("endDate"))
        end_time = AulaProfileParser._parse_nullable_time(data.get("endTime"))
        if end_date is not None:
            end_datetime = datetime(year=end_date.year, month=end_date.month, day=end_date.day)
            if end_time is not None:
                end_datetime += timedelta(hours=end_time.hour, minutes=end_time.minute, seconds=end_time.second, microseconds=end_time.microsecond)

        result = AulaLocation(
            description = AulaProfileParser._parse_str(data.get("description")),
            end_datetime = end_datetime,
            icon = AulaProfileParser._parse_nullable_icon_str(data.get("symbol")),
            id = AulaProfileParser._parse_int(data.get("id", 0)),
            is_date_intervals_enabled = AulaProfileParser._parse_nullable_bool(data.get("isDateIntervalsEnabled")),
            is_deactivated = AulaProfileParser._parse_nullable_bool(data.get("isDeactivated")),
            is_time_intervals_enabled = AulaProfileParser._parse_nullable_bool(data.get("isTimeIntervalsEnabled")),
            is_weekdays_enabled = AulaProfileParser._parse_nullable_bool(data.get("isWeekdaysEnabled")),
            name = AulaProfileParser._parse_str(data.get("name")),
            start_datetime = start_datetime,
            week_day_mask = AulaProfileParser._parse_nullable_str(data.get("weekDayMask")),
        )
        return result

    @staticmethod
    def parse_group(data: AulaDailyOverviewMainGroupData | None) -> AulaGroup | None:
        if not data: return None
        result = AulaGroup(
            allow_members_to_be_shown = AulaProfileParser._parse_nullable_bool(data.get("allowMembersToBeShown")),
            id = AulaProfileParser._parse_int(data.get("id", 0)),
            institution_code = AulaProfileParser._parse_str(data.get("institutionCode")),
            institution_name = AulaProfileParser._parse_str(data.get("institutionName")),
            is_deactivated = AulaProfileParser._parse_nullable_bool(data.get("isDeactivated")),
            main_group = AulaProfileParser._parse_nullable_bool(data.get("mainGroup")),
            name = AulaProfileParser._parse_str(data.get("name")),
            short_name = AulaProfileParser._parse_str(data.get("shortName")),
            uni_group_type = AulaProfileParser._parse_str(data.get("uniGroupType")),
        )
        return result

    @staticmethod
    def parse_groups(data: List[AulaDailyOverviewMainGroupData] | None) -> List[AulaGroup]:
        if data is None: return []
        return list_without_none(map(AulaProfileParser.parse_group, data))

    @staticmethod
    def parse_daily_overview(data: AulaDailyOverviewData | None) -> AulaDailyOverview | None:
        if not data: return None
        result = AulaDailyOverview(
            check_in_time = AulaProfileParser._parse_nullable_time(data.get("checkInTime")),
            check_in_time_expected = AulaProfileParser._parse_nullable_time(data.get("entryTime")),
            check_out_time = AulaProfileParser._parse_nullable_time(data.get("checkOutTime")),
            check_out_time_expected = AulaProfileParser._parse_nullable_time(data.get("exitTime")),
            comment = AulaProfileParser._parse_nullable_str(data.get("comment")),
            exit_with = AulaProfileParser._parse_nullable_str(data.get("exitWith")),
            id = AulaProfileParser._parse_int(data.get("id", 0)),
            institution_profile = AulaProfileParser.parse_institution(data.get("institutionProfile")),
            is_default_check_in_time_expected = AulaProfileParser._parse_nullable_bool(data.get("isDefaultEntryTime")),
            is_default_check_out_time_expected = AulaProfileParser._parse_nullable_bool(data.get("isDefaultExitTime")),
            is_planned_times_outside_opening_hours = AulaProfileParser._parse_nullable_bool(data.get("isPlannedTimesOutsideOpeningHours")),
            location = AulaProfileParser.parse_location(data.get("location")),
            main_group = AulaProfileParser.parse_group(data.get("mainGroup")),
            self_decider_end_time = AulaProfileParser._parse_nullable_time(data.get("selfDeciderEndTime")),
            self_decider_start_time = AulaProfileParser._parse_nullable_time(data.get("selfDeciderStartTime")),
            spare_time_activity = AulaProfileParser._parse_nullable_str(data.get("spareTimeActivity")),
            status = AulaProfileParser._parse_int(data.get("status", 0)),
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
