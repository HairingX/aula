import calendar
from http import HTTPStatus
from requests import Response, Session
from requests.exceptions import ConnectionError as RequestsConnectionError, Timeout as RequestsTimeout
from typing import Any, Dict, Iterable, List
from datetime import datetime, timedelta, date
import json
import logging
import re
import pytz
from .aula_errors import ParseError, AulaCredentialError
from .models.constants import AulaWidgetId
from .models.module import *
from .responses.get_daily_overview_response import AulaGetDailyOverviewResponse
from .responses.get_events_by_profile_ids_and_resource_ids import AulaGetEventsByProfileIdsAndResourceIdsResponse
from .responses.get_messages_for_thread_response import AulaGetMessagesForThreadResponse
from .responses.get_message_threads_response import AulaGetMessageThreadsResponse
from .responses.get_notifications_response import AulaGetNotificationsResponse
from .responses.get_profile_context_response import AulaGetProfileContextResponse
from .responses.get_profile_master_data_response import AulaGetProfileMasterDataResponse
from .responses.get_profiles_by_login_response import AulaGetProfilesByLoginResponse
from .responses.get_weekly_plans_response import AulaGetWeeklyPlansResponse
from .responses.get_easyiq_weekplan_response import AulaGetEasyiqWeekplanResponse
from .responses.get_weekly_newsletter_response import AulaGetWeeklyNewsletterResponse
from .responses.get_birthday_events_for_institutions import AulaGetBirthdayEventsForInstitutionsResponse
from .const import (
    API,
    API_VERSION,
    EASYIQ_API,
    MEEBOOK_API,
    MIN_UDDANNELSE_API,
    SYSTEMATIC_API,
)

_LOGGER = logging.getLogger(__name__)

REQUEST_MAX_ATTEMPTS = 3
"""Maximum number of attempts for requests, when certain errors occurs, such as timeout."""
REQUEST_TIMEOUT = 30
"""Default timeout in seconds for all HTTP requests."""
TOKEN_EXPIRATION_TIME = timedelta(minutes=40)

_ACCESS_TOKEN_PATTERN = re.compile(r'access_token=[^&\s]*')

def _redact_url(url: Any) -> str:
    """Strip access_token from a URL for safe logging."""
    return _ACCESS_TOKEN_PATTERN.sub('access_token=REDACTED', str(url))

class _TimeoutSession(Session):
    """A requests.Session that applies a default timeout to all requests."""
    def request(self, method: str, url: str, *args: Any, **kwargs: Any) -> Response:  # type: ignore[override]
        kwargs.setdefault("timeout", REQUEST_TIMEOUT)
        return super().request(method, url, *args, **kwargs)


class _TokenSession(_TimeoutSession):
    """A session that appends access_token to Aula API URLs and handles CSRF optionally."""

    _access_token: str = ""

    def set_access_token(self, token: str) -> None:
        self._access_token = token

    def request(self, method: str, url: str, *args: Any, **kwargs: Any) -> Response:  # type: ignore[override]
        if self._access_token and API in url:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}access_token={self._access_token}"
        return super().request(method, url, *args, **kwargs)


class AulaProxyClient:
    api_version:int = int(API_VERSION)

    _login_result: AulaLoginData | None = None
    _tokens: dict[AulaWidgetId, AulaToken]
    _is_logged_in: bool = False
    _apiurl:str = ""
    _username:str = ""
    _session:_TokenSession

    def __init__(self, access_token: str, username_for_meebook: str = ""):
        self._username = username_for_meebook
        self._session = _TokenSession()
        self._session.set_access_token(access_token)
        self._tokens = dict()

    def update_token(self, new_token: str) -> None:
        """Update the access token used for API calls."""
        self._session.set_access_token(new_token)

    def close(self) -> None:
        """Close the HTTP session."""
        self._session.close()


    def _get_csrf_token(self) -> str | None:
        """Get CSRF token from session cookies, or None if not available (token-based auth)."""
        return self._session.cookies.get_dict().get("Csrfp-Token")

    def custom_api_call(self, uri:str, post_data:str|None) -> Dict[str,str]:
        headers: Dict[str, str] = {"content-type": "application/json"}
        csrf_token = self._get_csrf_token()
        if csrf_token:
            headers["csrfp-token"] = csrf_token
        url = self._apiurl + uri
        _LOGGER.debug(f"custom_api_call: Making API call to {url}")
        if post_data == None:
            response = self._session.get(url, headers=headers, verify=True)
        else:
            try:
                # Check if post_data is valid JSON
                json.loads(post_data)
            except json.JSONDecodeError as e:
                _LOGGER.error(f"Invalid json supplied as post_data: {e}")
                error_msg = {"result": "Fail - invalid json supplied as post_data"}
                return error_msg
            _LOGGER.debug("custom_api_call: post_data:" + post_data)
            response = self._session.post(
                url,
                headers=headers,
                json=json.loads(post_data),
                verify=True,
            )
        _LOGGER.debug(response.text)
        try:
            responsedata = response.json()
        except (json.JSONDecodeError, ValueError):
            responsedata = {"raw_response": response.text}
        return responsedata


    def login(self) -> AulaLoginData:
        """
        Verifies token-based authentication and retrieves user profiles.

        Uses the access_token (appended automatically by _TokenSession) to call the
        Aula API. Discovers the correct API version and fetches profiles, widgets,
        and user context.

        Returns:
            AulaLoginData: Contains a list of user profiles, widgets, version etc.
        Raises:
            AulaCredentialError: If access to the Aula API is denied.
            ConnectionRefusedError: If the API URL is unreachable or an unknown error occurs.
        """
        _LOGGER.debug("Logging in with token-based auth")
        self._is_logged_in = False
        if self._session and self._apiurl:
            login_responsedata = self._session.get(self._apiurl + "?method=profiles.getProfilesByLogin", verify=True).json()
            self._is_logged_in = login_responsedata["status"]["message"] == "OK"

        _LOGGER.debug(f"Logged in already? {self._is_logged_in}")

        if self._is_logged_in and self._login_result is not None:
            return self._login_result

        # Find the API url in case of a version change
        original_profiles = profiles = [] if self._login_result is None else self._login_result.profiles
        while profiles == original_profiles:
            self._apiurl = self._get_aula_api()
            _LOGGER.debug(f"Trying API at {self._apiurl}")
            api_response = self._session.get(f"{self._apiurl}?method=profiles.getProfilesByLogin", verify=True)
            # _LOGGER.debug(f"Result from {api_response.url}: {api_response.text}")
            if api_response.status_code == HTTPStatus.OK:
                api_responsedata:AulaGetProfilesByLoginResponse = api_response.json()
                _LOGGER.debug(f"API success: v{self.api_version}")
                try:
                    profiles = AulaProfileParser.parse_profiles_response(api_responsedata)
                except Exception as e:
                    _LOGGER.info(f"method=profiles.getProfilesByLogin response: {api_response}")
                    _LOGGER.error(f"Error parsing profiles: {e}")
                    raise
                # _LOGGER.debug("self._profiles "+str(self._profiles))
                break
            elif api_response.status_code == HTTPStatus.GONE:
                msg = f"API was expected at {self._apiurl} but responded with HTTP 410. The integration will automatically try a newer version and everything may work fine."
                _LOGGER.debug(msg)
                self.api_version += 1
                if self.api_version - int(API_VERSION) > 10:
                    raise ConnectionRefusedError(msg)
            elif api_response.status_code == HTTPStatus.FORBIDDEN:
                msg = "Access to Aula API was denied. Please check that you have entered the correct credentials. (Your password automatically expires on regular intervals!)"
                _LOGGER.error(msg)
                raise AulaCredentialError(msg)
            else:
                _LOGGER.info(f"method=profiles.getProfilesByLogin response: {api_response}")
                msg = f"Unknown error occured. Received status code {api_response.status_code}."
                _LOGGER.error(msg)
                raise ConnectionRefusedError(msg)

        widgets: List[AulaWidget] = []
        if len(profiles) > 0:
            # PROFILE CONTEXT (widgets & set user ids on profiles and children)
            api_method_context = "profiles.getProfileContext"
            response =  self._session.get(f"{self._apiurl}?method={api_method_context}&portalrole=guardian",verify=True)
            responsedata_context: AulaGetProfileContextResponse = response.json()
            data = responsedata_context["data"]
            #set user id on logged in profile
            userid = data["userId"]
            for profile in profiles:
                profile.user_id = userid

            #set user id on children profiles
            children = dict((child.id, child) for child in self.flatten_children(profiles))
            institutions = None if "institutions" not in data else data["institutions"]
            if institutions:
                for institutiondata in institutions:
                    if "children" in institutiondata and institutiondata["children"] is not None:
                        for childdata in institutiondata["children"]:
                            child = children.get(childdata["id"])
                            if child: child.user_id = childdata["userId"]

            #read widgets (used to identify supported features)
            detected_widgetsdata = responsedata_context["data"]["pageConfiguration"]["widgetConfigurations"]
            try:
                widgets = AulaProfileParser.parse_widgets([widgetconfdata["widget"] for widgetconfdata in detected_widgetsdata])
            except Exception as e:
                _LOGGER.info(f"method={api_method_context} response: {responsedata_context}")
                _LOGGER.error(f"Error parsing widgets: {e}")

        if len(profiles) > 0:
            # PROFILE MASTER DATA (set master group on children)
            api_method_masterdata = "profiles.getProfileMasterData"
            inst_profile_ids = list(set(str(institution_profile.id) for profile in profiles for institution_profile in profile.institution_profiles))
            response = self._session.get(f"{self._apiurl}?method={api_method_masterdata}&instProfileIds[]={"&instProfileIds[]=".join(inst_profile_ids)}&fromAdministration=false",verify=True)
            responsedata_masterdata: AulaGetProfileMasterDataResponse = response.json()
            #set master group on children profiles
            relations = AulaProfileParser.parse_profile_master_data_response(responsedata_masterdata)
            children = dict((child.id, child) for child in self.flatten_children(profiles))

            try:
                for relation in relations:
                    child = children.get(relation.child_id)
                    if child: child.main_group = relation.main_group
            except Exception as e:
                _LOGGER.info(f"method={api_method_masterdata} response: {responsedata_masterdata}")
                _LOGGER.error(f"Error assigning main groups: {e}")

        result = AulaLoginData(
            profiles = profiles,
            widgets = widgets,
            api_version = self.api_version
        )
        self._login_result = result
        # _LOGGER.debug(f"login: {result}")
        _LOGGER.debug(f"Login found {len(profiles)} profiles")
        _LOGGER.debug(f"Widgets found: {str.join(", ", [widget.widget_id for widget in widgets])}")
        return result


    def get_birthday_events(self, profiles: List[AulaChildProfile], start_datetime: datetime, end_datetime: datetime) -> List[AulaBirthdayEvent]:
        _LOGGER.debug(f"Fetching birthday events for {len(profiles)} profiles from {start_datetime} to {end_datetime}")
        if len(profiles) == 0: return []
        inst_profile_codes = list(set(profile.institution_code for profile in profiles))
        start = start_datetime.strftime("%Y-%m-%dT00:00:00.0000%:z").replace("+", "%2B")
        end = end_datetime.strftime("%Y-%m-%dT23:59:59.9990%:z").replace("+", "%2B")

        api_method = "calendar.getBirthdayEventsForInstitutions"
        headers: Dict[str, str]|None = None
        requesturl: str = f"{self._apiurl}?method={api_method}&start={start}&end={end}&instCodes[]={str.join("&instCodes[]=", inst_profile_codes)}"

        # _LOGGER.debug("Calendar post-data: "+str(post_data))
        response: Response|None = None
        for attempt in range(1, REQUEST_MAX_ATTEMPTS+1):
            try:
                response = self._session.get(requesturl, headers=headers, verify=True)
            except (RequestsTimeout, RequestsConnectionError) as e:
                self._handle_request_exception(e, attempt, api_method)
                continue
            if not self._should_retry_request(response, attempt):
                break
        if response == None or response.status_code != HTTPStatus.OK:
            if response is not None:
                _LOGGER.error(f"Failed to retrieve birthday events for profile codes: {inst_profile_codes}. Error: {response.status_code}/{response.reason} - {response.text}. Request url: {_redact_url(response.request.url)}, Request headers: {response.request.headers}, Request body: {response.request.body}.")
                self._raise_error(response)
            return []
        responsedata: AulaGetBirthdayEventsForInstitutionsResponse = response.json()
        try:
            events = AulaBirthdayParser.parse_birthday_event_response(responsedata)
        except Exception as e:
            _LOGGER.info(f"method={api_method} response: {responsedata}")
            _LOGGER.error(f"Error parsing birthday events: {e}")
            raise
        # _LOGGER.debug(f"get_calendar_events: {result}")
        _LOGGER.debug(f"Fetched birthday events: {len(events)}")
        return events


    def get_calendar_events(self, profiles: List[AulaInstitutionProfile], start_datetime: datetime, end_datetime: datetime) -> List[AulaCalendarEvent]:
        _LOGGER.debug(f"Fetching calendar events for {len(profiles)} profiles from {start_datetime} to {end_datetime}")
        if len(profiles) == 0: return []
        inst_profile_ids = list(set(profile.id for profile in profiles))
        start = start_datetime.strftime("%Y-%m-%d 00:00:00.0000%:z")
        end = end_datetime.strftime("%Y-%m-%d 00:00:00.0000%:z")

        headers: Dict[str, str] = {"content-type": "application/json"}
        csrf_token = self._get_csrf_token()
        if csrf_token:
            headers["csrfp-token"] = csrf_token

        post_data:Dict[str, Any]|None = dict()
        post_data["instProfileIds"] = inst_profile_ids
        post_data["resourceIds"] =  []
        post_data["start"] = start
        post_data["end"] = end

        api_method = "calendar.getEventsByProfileIdsAndResourceIds"
        requesturl: str = f"{self._apiurl}?method={api_method}"

        # _LOGGER.debug("Calendar post-data: "+str(post_data))
        response: Response|None = None
        for attempt in range(1, REQUEST_MAX_ATTEMPTS+1):
            try:
                response = self._session.post(requesturl, json=post_data, headers=headers, verify=True)
            except (RequestsTimeout, RequestsConnectionError) as e:
                self._handle_request_exception(e, attempt, api_method)
                continue
            if not self._should_retry_request(response, attempt):
                break
        if response == None or response.status_code != HTTPStatus.OK:
            if response is not None:
                _LOGGER.error(f"Failed to retrieve calendar events for profileids: {inst_profile_ids}. Error: {response.status_code}/{response.reason} - {response.text}. Request: {_redact_url(response.request.url)}.")
                self._raise_error(response)
            return []
        responsedata: AulaGetEventsByProfileIdsAndResourceIdsResponse = response.json()
        try:
            events = AulaCalendarParser.parse_calendar_event_response(responsedata)
        except Exception as e:
            _LOGGER.info(f"method={api_method} response: {responsedata}")
            _LOGGER.error(f"Error parsing calendar events: {e}")
            raise
        # _LOGGER.debug(f"get_calendar_events: {result}")
        _LOGGER.debug(f"Fetched calendar events: {len(events)}")
        return events


    def get_daily_overviews(self, profiles: List[AulaProfile]) -> List[AulaDailyOverview]:
        _LOGGER.debug(f"Fetching daily overviews for {len(profiles)} profiles")
        if len(profiles) == 0: return []
        children = self.flatten_children(profiles)
        child_ids_as_str_list = list(set(str(child.id) for child in children))

        api_method = "presence.getDailyOverview"
        headers:Dict[str, str]|None = None
        requesturl: str = f"{self._apiurl}?method={api_method}&childIds[]={str.join("&childIds[]=", child_ids_as_str_list)}"

        response: Response|None = None
        for attempt in range(1, REQUEST_MAX_ATTEMPTS+1):
            try:
                response = self._session.get(requesturl, headers=headers, verify=True)
            except (RequestsTimeout, RequestsConnectionError) as e:
                self._handle_request_exception(e, attempt, api_method)
                continue
            if not self._should_retry_request(response, attempt):
                break
        if response == None or response.status_code != HTTPStatus.OK:
            if response is not None:
                _LOGGER.error(f"Failed to retrieve daily overview for childids: {child_ids_as_str_list}. Error: {response.status_code}/{response.reason} - {response.text}. Request: {_redact_url(response.request.url)}.")
                self._raise_error(response)
            return []
        responsedata: AulaGetDailyOverviewResponse = response.json()

        try:
            daily_overviews = AulaProfileParser.parse_daily_overview_response(responsedata)
            if len(daily_overviews) < len(children):
                overview_ids = set[int](overview.id for overview in daily_overviews)
                for child in children:
                    if child.id not in overview_ids:
                        _LOGGER.warning(f"Unable to retrieve presence data from Aula from child with id {child.id}. Some data will be missing from sensor entities.")
        except Exception as e:
            _LOGGER.info(f"method={api_method} response: {responsedata}")
            _LOGGER.error(f"Error parsing daily overviews: {e}")
            raise
        # _LOGGER.debug(f"get_daily_overviews: {daily_overviews}")
        _LOGGER.debug(f"Fetched daily overviews: {len(daily_overviews)}")
        return daily_overviews


    def get_message_threads(self) -> List[AulaMessageThread]:
        _LOGGER.debug(f"Fetching message threads")
        api_method = "messaging.getThreads"
        headers:Dict[str, str]|None = None
        requesturl: str = f"{self._apiurl}?method={api_method}&sortOn=date&orderDirection=desc&page=0"

        response: Response|None = None
        for attempt in range(1, REQUEST_MAX_ATTEMPTS+1):
            try:
                response = self._session.get(requesturl, headers=headers, verify=True)
            except (RequestsTimeout, RequestsConnectionError) as e:
                self._handle_request_exception(e, attempt, api_method)
                continue
            if not self._should_retry_request(response, attempt):
                break
        if response == None or response.status_code != HTTPStatus.OK:
            if response is not None:
                _LOGGER.error(f"Failed to retrieve message threads. Error: {response.status_code}/{response.reason} - {response.text}. Request: {_redact_url(response.request.url)}.")
                self._raise_error(response)
            return []
        responsedata: AulaGetMessageThreadsResponse = response.json()

        try:
            threads = AulaMessageThreadParser.parse_message_threads_response(responsedata)
        except Exception as e:
            _LOGGER.info(f"method={api_method} response: {responsedata}")
            _LOGGER.error(f"Error parsing message threads: {e}")
            raise
        # _LOGGER.debug(f"get_message_threads: {threads}")
        _LOGGER.debug(f"Fetched message threads: {len(threads)}")
        return threads


    def get_messages(self, thread: AulaMessageThread) -> List[AulaMessage]:
        """
        Retrieve messages from a specified thread.

        Raises
            PermissionError: If the thread is marked as sensitive or if access is forbidden.
            ImportError: If the status code of the response is not OK.
        """
        _LOGGER.debug(f"Fetching messages")
        if not thread: return []
        if thread.sensitive: raise PermissionError("Use Aula to read this message.")
        api_method = "messaging.getMessagesForThread"
        headers:Dict[str, str]|None = None
        requesturl: str = f"{self._apiurl}?method={api_method}&threadId={thread.id}&page=0"

        response: Response|None = None
        for attempt in range(1, REQUEST_MAX_ATTEMPTS+1):
            try:
                response = self._session.get(requesturl, headers=headers, verify=True)
            except (RequestsTimeout, RequestsConnectionError) as e:
                self._handle_request_exception(e, attempt, api_method)
                continue
            if not self._should_retry_request(response, attempt):
                break
        if response == None or response.status_code != HTTPStatus.OK:
            if response is not None:
                _LOGGER.error(f"Failed to retrieve messages from thread: {thread.subject} (id {thread.id}). Error: {response.status_code}/{response.reason} - {response.text}. Request: {_redact_url(response.request.url)}.")
                self._raise_error(response)
            return []
        responsedata: AulaGetMessagesForThreadResponse = response.json()
        try:
            messages = AulaMessageThreadParser.parse_messages_response(responsedata)
        except Exception as e:
            _LOGGER.info(f"method={api_method} response: {responsedata}")
            _LOGGER.error(f"Error parsing messages: {e}")
            raise
        # _LOGGER.debug(f"get_messages: {messages}")
        _LOGGER.debug(f"Fetched messages: {len(messages)}")
        return messages


    def get_notifications(self, profiles: List[AulaChildProfile]) -> List[AULA_NOTIFICATION_TYPES]:
        """Returns a list of notifications"""
        _LOGGER.debug(f"Fetching notifications for {len(profiles)} profiles")
        if len(profiles) == 0: return []
        children = profiles
        child_userids_as_str_list = list(set(str(child.id) for child in children))
        institution_profile_codes = list(set(child.institution_code for child in children))

        api_method = "notifications.getNotificationsForActiveProfile"
        headers: Dict[str, str] = self._get_aula_header()
        requesturl: str = f"{self._get_aula_api()}?method={api_method}&activeChildrenIds[]={str.join("&activeChildrenIds[]=",child_userids_as_str_list)}&activeInstitutionCodes[]={str.join("&activeInstitutionCodes[]=",institution_profile_codes)}"

        response: Response|None = None
        for attempt in range(1, REQUEST_MAX_ATTEMPTS+1):
            try:
                response = self._session.get(requesturl, headers=headers, verify=True)
            except (RequestsTimeout, RequestsConnectionError) as e:
                self._handle_request_exception(e, attempt, api_method)
                continue
            if not self._should_retry_request(response, attempt):
                break
        if response == None or response.status_code != HTTPStatus.OK:
            if response is not None:
                _LOGGER.error(f"Failed to retrieve notifications from children: {child_userids_as_str_list}. Error: {response.status_code}/{response.reason} - {response.text}. Request: {_redact_url(response.request.url)}.")
                self._raise_error(response)
            return []
        responsedata: AulaGetNotificationsResponse = response.json()
        try:
            notifications = AulaNotificationParser.parse_notification_response(responsedata)
        except Exception as e:
            _LOGGER.info(f"method={api_method} response: {responsedata}")
            _LOGGER.error(f"Error parsing notifications: {e}")
            raise
        # _LOGGER.debug(f"get_notifications: {notifications}")
        _LOGGER.debug(f"Fetched notifications: {len(notifications)}")
        return notifications


    def get_weekly_plans(self, profiles: List[AulaChildProfile], from_datetime: datetime, to_datetime: datetime) -> List[AulaWeeklyPlan]:
        """Fetches weekly plans from Meebook (widget 0004)."""
        _LOGGER.debug(f"Fetching weekplan for {len(profiles)} profiles from {from_datetime} to {to_datetime}")
        if len(profiles) == 0: return []
        if not self.has_widget(AulaWidgetId.WEEKPLAN_PARENTS): return []
        children = profiles
        child_userids_as_str_list = list(set(str(child.user_id) for child in children))
        institution_profile_codes = list(set(child.institution_code for child in children))

        widgetid = AulaWidgetId.WEEKPLAN_PARENTS
        token = self._get_token(widgetid)
        headers: Dict[str, str] = self._get_meebook_header(token)
        requesturl: str = f"{MEEBOOK_API}/relatedweekplan/all?currentWeekNumber={{weekno}}&userProfile=guardian&childFilter[]={str.join("&childFilter[]=",child_userids_as_str_list)}&institutionFilter[]={str.join("&institutionFilter[]=",institution_profile_codes)}"

        response: Response|None = None
        weeklyplans = list[AulaWeeklyPlan]()
        from_datetime = from_datetime - timedelta(days=from_datetime.weekday()) #ensure it is a monday
        from_date = from_datetime.date()
        first_run = True
        has_force_refreshed = False  # only one force-refresh per call to avoid spamming the token endpoint
        while from_datetime < to_datetime:
            from_date = from_datetime.date()
            weekno = self._get_aula_week_formatted(from_date)
            for attempt in range(1, REQUEST_MAX_ATTEMPTS+1):
                try:
                    response = self._session.get(requesturl.format(weekno=weekno), headers=headers, verify=True)
                except (RequestsTimeout, RequestsConnectionError) as e:
                    self._handle_request_exception(e, attempt, "relatedweekplan")
                    continue
                if not self._should_retry_request(response, attempt):
                    break
            # On 401, force-refresh token once and retry this request
            if response is not None and response.status_code == HTTPStatus.UNAUTHORIZED and not has_force_refreshed:
                token = self._refresh_token(widgetid, force=True)
                headers = self._get_meebook_header(token)
                has_force_refreshed = True
                try:
                    response = self._session.get(requesturl.format(weekno=weekno), headers=headers, verify=True)
                except (RequestsTimeout, RequestsConnectionError):
                    response = None
            if response == None or response.status_code != HTTPStatus.OK:
                if response is not None:
                    _LOGGER.error(f"Failed to retrieve weekly plans from children: {child_userids_as_str_list} from {from_datetime} to {to_datetime}. Error: {response.status_code}/{response.reason} - {response.text}. Request: {_redact_url(response.request.url)}.")
                    if not first_run: continue
                    self._raise_error(response)
                return []
            responsedata: List[AulaGetWeeklyPlansResponse] = response.json()
            # assign dates to the weekly plans - we need them later
            for respdata in responsedata:
                respdata["from_date"] = from_date
                respdata["to_date"] = respdata["from_date"] + timedelta(days=6)
            weeklyplans.extend(AulaWeeklyPlanParser.parse_weekly_plans(responsedata))
            from_datetime += timedelta(weeks=1)
            first_run = False
        _LOGGER.debug(f"Fetched meebook weekplan: {len(weeklyplans)}")
        return weeklyplans

    def _get_guardian_user_id(self) -> str:
        """Get the guardian userId, from login data or by fetching from the API."""
        if self._login_result and self._login_result.profiles:
            for profile in self._login_result.profiles:
                if profile.user_id:
                    return profile.user_id
        responsedata = self._session.get(f"{self._apiurl}?method=profiles.getProfileContext&portalrole=guardian", verify=True).json()
        return responsedata["data"]["userId"]

    def get_easyiq_weekly_plans(self, profiles: List[AulaChildProfile], from_datetime: datetime, to_datetime: datetime) -> List[AulaEasyiqWeeklyPlan]:
        """Fetches weekly plans from EasyIQ (widget 0001)."""
        _LOGGER.debug(f"Fetching EasyIQ weekplan for {len(profiles)} profiles from {from_datetime} to {to_datetime}")
        if len(profiles) == 0: return []
        if not self.has_widget(AulaWidgetId.EASYIQ_WEEKPLAN): return []
        guardian_user_id = self._get_guardian_user_id()
        institution_profile_codes = list(set(child.institution_code for child in profiles))

        widgetid = AulaWidgetId.EASYIQ_WEEKPLAN
        token = self._get_token(widgetid)
        csrf_token = self._get_csrf_token()

        weeklyplans = list[AulaEasyiqWeeklyPlan]()
        from_datetime = from_datetime - timedelta(days=from_datetime.weekday())
        first_run = True
        has_force_refreshed = False  # only one force-refresh per call to avoid spamming the token endpoint
        while from_datetime < to_datetime:
            from_date = from_datetime.date()
            weekno = self._get_aula_week_formatted(from_date)
            for child in profiles:
                for inst_code in institution_profile_codes:
                    headers = self._get_easyiq_header(token, inst_code, csrf_token)
                    post_data: Dict[str, Any] = {
                        "sessionId": guardian_user_id,
                        "currentWeekNr": weekno,
                        "userProfile": "guardian",
                        "institutionFilter": [inst_code],
                        "childFilter": [child.user_id],
                    }
                    response: Response|None = None
                    for attempt in range(1, REQUEST_MAX_ATTEMPTS+1):
                        try:
                            response = self._session.post(EASYIQ_API + "/weekplaninfo", json=post_data, headers=headers, verify=True)
                        except (RequestsTimeout, RequestsConnectionError) as e:
                            self._handle_request_exception(e, attempt, "weekplaninfo")
                            continue
                        if not self._should_retry_request(response, attempt):
                            break
                    # On 401, force-refresh token once and retry this request
                    if response is not None and response.status_code == HTTPStatus.UNAUTHORIZED and not has_force_refreshed:
                        token = self._refresh_token(widgetid, force=True)
                        has_force_refreshed = True
                        headers = self._get_easyiq_header(token, inst_code, csrf_token)
                        try:
                            response = self._session.post(EASYIQ_API + "/weekplaninfo", json=post_data, headers=headers, verify=True)
                        except (RequestsTimeout, RequestsConnectionError):
                            response = None
                    if response == None or response.status_code != HTTPStatus.OK:
                        if response is not None:
                            _LOGGER.error(f"Failed to retrieve EasyIQ weekplan for child {child.first_name}. Error: {response.status_code}/{response.reason} - {response.text}.")
                            if first_run:
                                self._raise_error(response)
                            continue
                        continue
                    responsedata: AulaGetEasyiqWeekplanResponse = response.json()
                    plan = AulaEasyiqWeekplanParser.parse_events_as_weekly_plan(responsedata, child.first_name, str(child.user_id), from_date)
                    if plan.daily_plans:
                        weeklyplans.append(plan)
            from_datetime += timedelta(weeks=1)
            first_run = False
        _LOGGER.debug(f"Fetched easyiq weekplan: {len(weeklyplans)}")
        return weeklyplans

    def get_newsletters(self, profiles: List[AulaChildProfile], from_datetime: datetime, to_datetime: datetime) -> List[AulaWeeklyNewsletter]:
        """Fetches weekly newsletters from MinUddannelse (widget 0029)."""
        _LOGGER.debug(f"Fetching newsletters for {len(profiles)} profiles from {from_datetime} to {to_datetime}")
        if len(profiles) == 0: return []
        if not self.has_widget(AulaWidgetId.MY_EDUCATION_WEEKLETTER): return []
        guardian_user_id = self._get_guardian_user_id()
        child_userids_as_str_list = list(set(str(child.user_id) for child in profiles))

        widgetid = AulaWidgetId.MY_EDUCATION_WEEKLETTER
        token = self._get_token(widgetid)
        headers: Dict[str, str] = self._get_myeducation_header(token)
        requesturl: str = f"{MIN_UDDANNELSE_API}/ugebrev?assuranceLevel=2&childFilter={",".join(child_userids_as_str_list)}&currentWeekNumber={{weekno}}&isMobileApp=false&placement=narrow&sessionUUID={guardian_user_id}&userProfile=guardian"

        newsletters = list[AulaWeeklyNewsletter]()
        from_datetime = from_datetime - timedelta(days=from_datetime.weekday())
        first_run = True
        has_force_refreshed = False  # only one force-refresh per call to avoid spamming the token endpoint
        while from_datetime < to_datetime:
            from_date = from_datetime.date()
            weekno = self._get_aula_week_formatted(from_date)
            response: Response|None = None
            for attempt in range(1, REQUEST_MAX_ATTEMPTS+1):
                try:
                    response = self._session.get(requesturl.format(weekno=weekno), headers=headers, verify=True)
                except (RequestsTimeout, RequestsConnectionError) as e:
                    self._handle_request_exception(e, attempt, "ugebrev")
                    continue
                if not self._should_retry_request(response, attempt):
                    break
            # On 401, force-refresh token once and retry this request
            if response is not None and response.status_code == HTTPStatus.UNAUTHORIZED and not has_force_refreshed:
                token = self._refresh_token(widgetid, force=True)
                headers = self._get_myeducation_header(token)
                has_force_refreshed = True
                try:
                    response = self._session.get(requesturl.format(weekno=weekno), headers=headers, verify=True)
                except (RequestsTimeout, RequestsConnectionError):
                    response = None
            if response == None or response.status_code != HTTPStatus.OK:
                if response is not None:
                    _LOGGER.error(f"Failed to retrieve newsletters from children: {child_userids_as_str_list} from {from_datetime} to {to_datetime}. Error: {response.status_code}/{response.reason} - {response.text}.")
                    if first_run:
                        self._raise_error(response)
                    continue
                continue
            responsedata: AulaGetWeeklyNewsletterResponse = response.json()
            newsletters.extend(AulaNewsletterParser.parse_response(responsedata, from_date))
            from_datetime += timedelta(weeks=1)
            first_run = False
        _LOGGER.debug(f"Fetched newsletters: {len(newsletters)}")
        return newsletters


    # #TODO: Not yet implemented
    # def get_reminders(self, profiles: List[AulaProfile], timestamp: datetime) -> Dict[str, str]:
    #     """Returns a dictionary of firstname, html - planned to be rewritten, but cant test for now due to missing data"""
    #     _LOGGER.debug(f"Fetching reminders for {len(profiles)} profiles")
    #     if len(profiles) == 0: return dict[str,str]()
    #     children = self.flatten_children(profiles)
    #     child_ids_as_str_list = list(set(str(child.id) for child in children))
    #     institution_profile_codes = list(set(child.institution_code for child in children))

    #     result = dict[str, str]()
    #     if self.has_widget(AulaWidgetId.REMINDERS):
    #         _LOGGER.debug("In the Huskelisten flow...")
    #         token = self._get_token(AulaWidgetId.REMINDERS)
    #         huskelisten_headers = self._get_aula_header(token)

    #         children = "&children=".join(child_ids_as_str_list)
    #         institutions = "&institutions=".join(institution_profile_codes)
    #         delta = datetime.now() + timedelta(days=180)
    #         From = datetime.now().strftime("%Y-%m-%d")
    #         dueNoLaterThan = delta.strftime("%Y-%m-%d")
    #         get_payload = f"/reminders/v1?children={children}&from={From}&dueNoLaterThan={dueNoLaterThan}&widgetVersion=1.10&userProfile=guardian&sessionId={self._username}&institutions={institutions}"
    #         _LOGGER.debug(f"Huskelisten get_payload: {SYSTEMATIC_API}{get_payload}")

    #         reminder_personsdata: List[Dict[str,Any]] = []
    #         #
    #         mock_huskelisten:int|str = 0
    #         #
    #         if mock_huskelisten == 1: # type: ignore
    #             _LOGGER.warning("Using mock data for Huskelisten.")
    #             mock_huskelisten = '[{"userName":"Emilie efternavn","userId":164625,"courseReminders":[],"assignmentReminders":[],"teamReminders":[{"id":76169,"institutionName":"Holme Skole","institutionId":183,"dueDate":"2022-11-29T23:00:00Z","teamId":65240,"teamName":"2A","reminderText":"Onsdagslektie: Matematikfessor.dk: Sænk skibet med plus.","createdBy":"Peter ","lastEditBy":"Peter ","subjectName":"Matematik"},{"id":76598,"institutionName":"Holme Skole","institutionId":183,"dueDate":"2022-12-06T23:00:00Z","teamId":65240,"teamName":"2A","reminderText":"Julekalender på Skoledu.dk: I skal forsøge at løse dagens kalenderopgave. opgaven kan også godt løses dagen efter.","createdBy":"Peter ","lastEditBy":"Peter Riis","subjectName":"Matematik"},{"id":76599,"institutionName":"Holme Skole","institutionId":183,"dueDate":"2022-12-13T23:00:00Z","teamId":65240,"teamName":"2A","reminderText":"Julekalender på Skoledu.dk: I skal forsøge at løse dagens kalenderopgave. opgaven kan også godt løses dagen efter.","createdBy":"Peter ","lastEditBy":"Peter ","subjectName":"Matematik"},{"id":76600,"institutionName":"Holme Skole","institutionId":183,"dueDate":"2022-12-20T23:00:00Z","teamId":65240,"teamName":"2A","reminderText":"Julekalender på Skoledu.dk: I skal forsøge at løse dagens kalenderopgave. opgaven kan også godt løses dagen efter.","createdBy":"Peter Riis","lastEditBy":"Peter Riis","subjectName":"Matematik"}]},{"userName":"Karla","userId":77882,"courseReminders":[],"assignmentReminders":[{"id":0,"institutionName":"Holme Skole","institutionId":183,"dueDate":"2022-12-08T11:00:00Z","courseId":297469,"teamNames":["5A","5B"],"teamIds":[65271,65258],"courseSubjects":[],"assignmentId":5027904,"assignmentText":"Skriv en novelle"}],"teamReminders":[{"id":76367,"institutionName":"Holme Skole","institutionId":183,"dueDate":"2022-11-30T23:00:00Z","teamId":65258,"teamName":"5A","reminderText":"Læse resten af kap.1 fra Ternet Ninja ( kopiark) Læs det hele højt eller vælg et afsnit. ","createdBy":"Christina ","lastEditBy":"Christina ","subjectName":"Dansk"}]},{"userName":"Vega  ","userId":206597,"courseReminders":[],"assignmentReminders":[],"teamReminders":[]}]'
    #             reminder_personsdata = json.loads(mock_huskelisten, strict=False)
    #         else:
    #             response = requests.get(
    #                 SYSTEMATIC_API + get_payload,
    #                 headers=huskelisten_headers,
    #                 verify=True,
    #             )
    #             try:
    #                 reminder_personsdata = json.loads(response.text, strict=False)
    #             except:
    #                 _LOGGER.error(
    #                     "Could not parse the response from Huskelisten as json."
    #                 )
    #             # _LOGGER.debug("Huskelisten raw response: "+str(response.text))

    #         for persondata in reminder_personsdata:
    #             name = persondata["userName"].split()[0]
    #             _LOGGER.debug("Huskelisten for " + name)
    #             huskel = ""
    #             remindersdata = persondata["teamReminders"]
    #             if len(remindersdata) > 0:
    #                 for reminderdata in remindersdata:
    #                     mytime = datetime.strptime(reminderdata["dueDate"], "%Y-%m-%dT%H:%M:%SZ")
    #                     ftime = mytime.strftime("%A %d. %B")
    #                     huskel += f"<h3>{ftime}</h3>"
    #                     huskel += f"<b>{reminderdata["subjectName"]}</b><br>"
    #                     huskel += f"af {reminderdata["createdBy"]}<br><br>"
    #                     content = re.sub(r"([0-9]+)(\.)", r"\1\.", reminderdata["reminderText"])
    #                     huskel += f"{content}<br><br>"
    #             else:
    #                 huskel += f"{name} har ingen påmindelser."
    #             result[name] = huskel
    #     _LOGGER.debug(f"Fetched reminders: {len(result)}")
    #     return result

    def _refresh_token(self, widgetid:AulaWidgetId, force: bool = False) -> AulaToken | None:
        token = self._tokens.get(widgetid)
        current_time = datetime.now(pytz.utc)
        if not force and token is not None and current_time - token.timestamp < timedelta(minutes=5):
            _LOGGER.debug("Ignoring token refresh request to avoid refreshing too often for widget id: " + widgetid)
            return token

        try:
            response = self._session.get(f"{self._apiurl}?method=aulaToken.getAulaToken&widgetId={widgetid}", verify=True)
            if response.status_code != HTTPStatus.OK:
                _LOGGER.warning("Failed to refresh token for widget %s: HTTP %s", widgetid, response.status_code)
                return token
            responsedata = response.json()
            data = responsedata["data"]
            token = AulaToken(
                bearer_token = "Bearer " + str(data),
                timestamp = datetime.now(pytz.utc)
            )
            self._tokens[widgetid] = token
            return token
        except (RequestsTimeout, RequestsConnectionError, json.JSONDecodeError, KeyError) as e:
            _LOGGER.warning("Failed to refresh widget token for %s: %s", widgetid, e)
            return token

    def _get_token(self, widgetid:AulaWidgetId) -> AulaToken | None:
        _LOGGER.debug(f"Requesting new token for widget {widgetid}")
        if widgetid in self._tokens:
            token = self._tokens[widgetid]
            current_time = datetime.now(pytz.utc)
            if current_time - token.timestamp < TOKEN_EXPIRATION_TIME:
                _LOGGER.debug("Reusing existing token for widget " + widgetid)
                return token
        return self._refresh_token(widgetid)

    def _get_user_id(self, profiles: List[AulaProfile]) -> str:
        """Ensures that each profile in the provided list has a user_id by fetching it from the API."""
        currentid: str|None = None
        for profile in profiles:
            if profile.user_id:
                currentid = profile.user_id
            else:
                currentid = None
                break

        if currentid is not None:
            return currentid

        responsedata = self._session.get(f"{self._apiurl}?method=profiles.getProfileContext&portalrole=guardian",verify=True,).json()
        newid = responsedata["data"]["userId"]

        for profile in profiles:
            profile.user_id = newid

        return newid

    def has_widget(self, widget_match: AulaWidgetId) -> bool:
        widgets = [] if self._login_result is None else self._login_result.widgets
        return any(widget.widget_id == widget_match for widget in widgets)

    def _get_aula_api(self) -> str:
        return API + str(self.api_version)

    def _get_user_agent(self) -> str:
        # Using Firefox browser as of 2024-10 for requests, as Python somtimes are blocked from accessing websites
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0"

    def _get_myeducation_header(self, token: AulaToken|None = None) -> Dict[str,str]:
        result: Dict[str, str] = {
            "user-agent": self._get_user_agent(),
            "accept": "application/json"
        }

        if token:
            result["authorization"] = token.bearer_token

        return result

    def _get_meebook_header(self, token: AulaToken|None = None) -> Dict[str,str]:
        result: Dict[str, str] = {
            "user-agent": self._get_user_agent(),
            "authority": "app.meebook.com",
            "accept": "application/json",
            "dnt": "1",
            "origin": "https://www.aula.dk",
            "referer": "https://www.aula.dk/",
            "sessionuuid": self._username,
            "x-version": "1.0",
        }

        if token:
            result["authorization"] = token.bearer_token

        return result

    def _get_easyiq_header(self, token: AulaToken|None, institution_profile_code: str, csrf_token: str | None) -> Dict[str,str]:
        result: Dict[str, str] = {
            "user-agent": self._get_user_agent(),
            "x-aula-institutionfilter": institution_profile_code,
            "x-aula-userprofile": "guardian",
            "accept": "application/json",
            "origin": "https://www.aula.dk",
            "referer": "https://www.aula.dk/",
            "authority": "api.easyiqcloud.dk",
            }
        if csrf_token:
            result["csrfp-token"] = csrf_token

        if token:
            result["authorization"] = token.bearer_token

        return result

    def _get_aula_header(self, token: AulaToken|None = None) -> Dict[str,str]:
        result: Dict[str, str] = {
                "user-agent": self._get_user_agent(),
                "Accept": "application/json, text/plain, */*",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "en-US,en;q=0.9,da;q=0.8",
                "Origin": "https://www.aula.dk",
                "Referer": "https://www.aula.dk/",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "cross-site",
                "zone": "Europe/Copenhagen",
            }

        if token:
            result["authorization"] = token.bearer_token

        return result

    @staticmethod
    def flatten_children(profiles: Iterable[AulaProfile]) -> List[AulaChildProfile]:
        result: List[AulaChildProfile] = []
        for profile in profiles:
            for child in profile.children:
                result.append(child)
        return result

    @staticmethod
    def _get_weekday(date:str) -> str:
        day, month, year = (int(i) for i in date.split(" "))
        dayNumber = calendar.weekday(year, month, day)
        days = [
            "Mandag",
            "Tirsdag",
            "Onsdag",
            "Torsdag",
            "Fredag",
            "Lørdag",
            "Søndag",
        ]
        return days[dayNumber]

    @staticmethod
    def _matches_datetime_format(date_string:str, format:str):
        try:
            datetime.strptime(date_string, format)
            return True
        except ValueError:
            _LOGGER.debug(f"Could not parse timestamp: {date_string}")
            return False

    @staticmethod
    def _get_aula_week_formatted(timestamp: datetime|date) -> str:
        return timestamp.strftime("%Y-W%V")

    @staticmethod
    def _is_last_attempt(attempt: int) -> bool:
        """Check if the current retry attempt is the last one"""
        return attempt >= REQUEST_MAX_ATTEMPTS

    @staticmethod
    def _handle_request_exception(e: Exception, attempt: int, api_method: str) -> None:
        """Handle timeout/connection errors in retry loops. Re-raises on last attempt."""
        if AulaProxyClient._is_last_attempt(attempt):
            raise
        _LOGGER.debug(f"Request for {api_method} failed ({type(e).__name__}), will retry (attempt {attempt}/{REQUEST_MAX_ATTEMPTS})")

    @staticmethod
    def _should_retry_request(response: Response, attempt: int) -> bool:
        if response.status_code == HTTPStatus.OK:
            return False
        # Only retry on server errors (5xx) — retrying 401 with the same token is pointless,
        # widget methods handle 401 with force-refresh-and-retry instead.
        status = HTTPStatus(response.status_code)
        if status.is_server_error:
            if not AulaProxyClient._is_last_attempt(attempt):
                _LOGGER.debug(f"Request failed due to server error, will retry (attempt {attempt}/{REQUEST_MAX_ATTEMPTS}): {response}")
                return True
        return False

    @staticmethod
    def _raise_error(response: Response | None) -> None:
        if response is None: return
        if response.ok: return
        # Safe message extraction — Aula API uses {"status": {"message": ...}}
        # but widget APIs may return plain text or different JSON structures
        message: str = f"{response.status_code} {response.reason or ''}"
        try:
            responsedata: dict[str, Any] = response.json()
            status: dict[str, Any] | None = responsedata.get("status")
            if isinstance(status, dict):
                msg: Any = status.get("message")
                if msg is not None:
                    message = str(msg)
        except (json.JSONDecodeError, ValueError, AttributeError):
            pass
        if response.status_code == HTTPStatus.UNAUTHORIZED:
            raise AulaCredentialError(message)
        if response.status_code == HTTPStatus.PAYMENT_REQUIRED: raise PermissionError(message)
        if response.status_code == HTTPStatus.FORBIDDEN: raise PermissionError(message)
        raise ImportError(message)
