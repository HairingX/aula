import base64
import binascii
import calendar
import threading
from http import HTTPStatus
from requests import Response, Session
from requests.exceptions import ConnectionError as RequestsConnectionError, Timeout as RequestsTimeout
from typing import Any, Callable, Dict, Iterable, List
from datetime import datetime, timedelta, date
import json
import logging
import re
import pytz
from .aula_errors import ParseError, AulaCredentialError, AulaApiError
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
"""Maximum cache duration for widget tokens when JWT exp claim is unavailable."""
TOKEN_EXPIRY_BUFFER = timedelta(seconds=60)
"""Refresh widget tokens this many seconds before their actual JWT exp claim.
Set to 60s to absorb clock skew between client and server (HA on devices
without NTP can drift by tens of seconds)."""

_ACCESS_TOKEN_PATTERN = re.compile(r'access_token=[^&\s]*')

def _redact_url(url: Any) -> str:
    """Strip access_token from a URL for safe logging."""
    return _ACCESS_TOKEN_PATTERN.sub('access_token=REDACTED', str(url))


def _describe_token(token: 'AulaToken | None') -> str:
    """Produce a diagnostic description of a widget token for log messages.

    Includes the token's age (since fetched), its JWT exp (if decodable),
    and its remaining/elapsed TTL — so a single log line tells the operator
    everything needed to spot stale-cache vs expired-at-issuance bugs.
    """
    if token is None:
        return "token=None"
    now = datetime.now(pytz.utc)
    age = (now - token.timestamp).total_seconds()
    if token.expires_at is None:
        return f"token age={age:.0f}s, JWT exp=undecoded"
    ttl = (token.expires_at - now).total_seconds()
    state = "EXPIRED" if ttl <= 0 else "valid"
    return f"token age={age:.0f}s, JWT exp={token.expires_at.isoformat()}, TTL={ttl:.0f}s ({state})"


def _decode_jwt_exp(jwt_token: str) -> datetime | None:
    """Decode the exp claim from a JWT without verifying its signature.

    Returns the expiry as a UTC datetime, or None if the token is malformed
    or has no exp claim.
    """
    try:
        parts = jwt_token.split('.')
        if len(parts) != 3:
            return None
        payload = parts[1]
        # JWT base64url encoding has no padding — add it back
        payload += '=' * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        claims = json.loads(decoded)
        if not isinstance(claims, dict):
            return None
        exp = claims.get('exp')
        if not isinstance(exp, (int, float)):
            return None
        # Sanity check: exp MUST be seconds-since-epoch per RFC 7519, but
        # broken issuers sometimes use milliseconds. Reject anything beyond
        # year 3000 (32503680000s) to avoid silently caching forever.
        if exp <= 0 or exp > 32503680000:
            return None
        return datetime.fromtimestamp(exp, tz=pytz.utc)
    except (ValueError, TypeError, AttributeError, binascii.Error, json.JSONDecodeError, UnicodeDecodeError, OverflowError, OSError) as e:
        # Log at DEBUG so a future malformed-JWT incident is traceable without
        # spamming INFO/WARNING on every call. Intentionally narrow: KeyboardInterrupt,
        # SystemExit, MemoryError etc. must propagate.
        _LOGGER.debug("Could not decode JWT exp claim (%s): %s", type(e).__name__, e)
        return None

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
    _token_refresh_callback: Callable[[], bool] | None = None

    def __init__(self, access_token: str, username_for_meebook: str = ""):
        self._username = username_for_meebook
        self._session = _TokenSession()
        self._session.set_access_token(access_token)
        self._tokens = dict()
        # Serialize widget token refreshes so two coordinator threads can't
        # both make HTTP roundtrips for the same widget simultaneously.
        self._token_refresh_lock = threading.Lock()

    def set_token_refresh_callback(self, callback: Callable[[], bool]) -> None:
        """Set a callback that force-refreshes the OAuth access_token.

        The callback handles the OAuth bearer token (used in ?access_token=...
        query parameters), NOT the widget JWT cookie cache (which is handled
        by reset_session()). The two failure modes are independent:

        - Main-session 401 from Aula API → callback refreshes access_token
        - Already-expired widget JWT from getAulaToken → reset_session()
          drops cookies + warms fresh server session

        The callback is invoked from _retry_on_401 when any Aula API call
        (including the widget token endpoint itself) returns 401.

        Returns:
            True if the access_token was refreshed successfully, False on
            transient failure. AulaCredentialError must propagate (not be
            converted to False) so genuine credential failures still trigger
            HA reauth.
        """
        self._token_refresh_callback = callback

    def update_token(self, new_token: str) -> None:
        """Update the access token used for API calls."""
        self._session.set_access_token(new_token)

    def reset_session(self) -> None:
        """Discard the HTTP session and start fresh.

        Aula's gateway caches widget JWTs server-side keyed by the HTTP
        session cookies (Csrfp-Token, PHPSESSID, etc.) — NOT by the
        access_token. When that server session ages out, the cached widget
        JWT goes stale and Aula keeps handing us the same already-expired
        JWT no matter how many times we re-call aulaToken.getAulaToken
        with the same cookies — even with a refreshed access_token.

        Rebuilding requests.Session drops the cookie jar and forces Aula
        to mint a brand-new server session (and therefore a fresh widget
        JWT) on the next request. This is the ONLY known client-side
        workaround for Aula's stale-JWT bug.

        All cached widget tokens are also cleared because they were minted
        against the now-discarded server session.
        """
        current_token = getattr(self._session, "_access_token", "")
        try:
            self._session.close()
        except Exception:  # noqa: BLE001 — closing failures must not block reset
            pass
        self._session = _TokenSession()
        if current_token:
            self._session.set_access_token(current_token)
        # Mark logged-in as False so any next login() call re-warms the session
        self._is_logged_in = False
        # Drop all cached widget tokens — they were minted against the old session
        self._tokens.clear()
        _LOGGER.info("HTTP session reset (cookies dropped, widget cache cleared)")

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
            try:
                login_response = self._session.get(self._apiurl + "?method=profiles.getProfilesByLogin", verify=True)
                if login_response.status_code == HTTPStatus.OK:
                    login_responsedata = login_response.json()
                    self._is_logged_in = login_responsedata["status"]["message"] == "OK"
            except (json.JSONDecodeError, KeyError, RequestsTimeout, RequestsConnectionError) as e:
                _LOGGER.debug("Quick login check failed, will proceed with full login: %s", e)

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
            if response.status_code == HTTPStatus.FORBIDDEN:
                raise AulaCredentialError(f"Access denied for {api_method_context}")
            if response.status_code != HTTPStatus.OK:
                _LOGGER.warning(f"Failed to fetch {api_method_context}: HTTP {response.status_code}, some data may be missing")
            else:
                try:
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
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    _LOGGER.warning(f"Failed to parse {api_method_context} response: {e}")

        if len(profiles) > 0:
            # PROFILE MASTER DATA (set master group on children)
            api_method_masterdata = "profiles.getProfileMasterData"
            inst_profile_ids = list(set(str(institution_profile.id) for profile in profiles for institution_profile in profile.institution_profiles))
            response = self._session.get(f"{self._apiurl}?method={api_method_masterdata}&instProfileIds[]={"&instProfileIds[]=".join(inst_profile_ids)}&fromAdministration=false",verify=True)
            if response.status_code != HTTPStatus.OK:
                _LOGGER.warning(f"Failed to fetch {api_method_masterdata}: HTTP {response.status_code}, master group data may be missing")
            else:
                try:
                    responsedata_masterdata: AulaGetProfileMasterDataResponse = response.json()
                    #set master group on children profiles
                    relations = AulaProfileParser.parse_profile_master_data_response(responsedata_masterdata)
                    children = dict((child.id, child) for child in self.flatten_children(profiles))

                    for relation in relations:
                        child = children.get(relation.child_id)
                        if child: child.main_group = relation.main_group
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    _LOGGER.warning(f"Failed to parse {api_method_masterdata} response: {e}")
                except Exception as e:
                    _LOGGER.info(f"method={api_method_masterdata} response: {response.text}")
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
        response = self._retry_on_401(response, lambda: self._session.get(requesturl, headers=headers, verify=True))
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
        response = self._retry_on_401(response, lambda: self._session.post(requesturl, json=post_data, headers=headers, verify=True))
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
        response = self._retry_on_401(response, lambda: self._session.get(requesturl, headers=headers, verify=True))
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
        response = self._retry_on_401(response, lambda: self._session.get(requesturl, headers=headers, verify=True))
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
            AulaApiError: If the status code of the response is not OK.
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
        response = self._retry_on_401(response, lambda: self._session.get(requesturl, headers=headers, verify=True))
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
        response = self._retry_on_401(response, lambda: self._session.get(requesturl, headers=headers, verify=True))
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
                _LOGGER.warning(
                    "Meebook rejected widget %s token, force-refreshing. Rejected %s. Response body: %s",
                    widgetid, _describe_token(token), response.text[:200],
                )
                token = self._refresh_token(widgetid, force=True)
                _LOGGER.info("After force-refresh: %s", _describe_token(token))
                headers = self._get_meebook_header(token)
                has_force_refreshed = True
                try:
                    response = self._session.get(requesturl.format(weekno=weekno), headers=headers, verify=True)
                except (RequestsTimeout, RequestsConnectionError) as e:
                    _LOGGER.warning("Meebook retry after token refresh failed with network error: %s", e)
                    response = None
            if response == None or response.status_code != HTTPStatus.OK:
                if response is not None:
                    _LOGGER.error(f"Failed to retrieve weekly plans from children: {child_userids_as_str_list} from {from_datetime} to {to_datetime}. Error: {response.status_code}/{response.reason} - {response.text}. Request: {_redact_url(response.request.url)}.")
                    if not first_run:
                        from_datetime += timedelta(weeks=1)
                        continue
                    # Widget token failure — don't trigger main session reauth
                    if response.status_code == HTTPStatus.UNAUTHORIZED:
                        raise AulaApiError(
                            f"Meebook widget {widgetid} returned HTTP 401 even after force-refresh "
                            f"({_describe_token(token)}). Response: {response.text[:200]}. "
                            f"This usually means Aula's aulaToken endpoint is issuing tokens that Meebook rejects."
                        )
                    self._raise_error(response)
                return []
            responsedata = response.json()
            # Meebook may return a dict (e.g. error/expired token payload) instead of the expected list
            if not isinstance(responsedata, list):
                _LOGGER.warning(f"Unexpected Meebook response type ({type(responsedata).__name__}) for week {weekno}, skipping: {responsedata}")
                from_datetime += timedelta(weeks=1)
                first_run = False
                continue
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
        response = self._session.get(f"{self._apiurl}?method=profiles.getProfileContext&portalrole=guardian", verify=True)
        if response.status_code != HTTPStatus.OK:
            raise AulaApiError(f"Failed to fetch guardian user ID: HTTP {response.status_code}")
        responsedata = response.json()
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
                        _LOGGER.warning(
                            "EasyIQ rejected widget %s token, force-refreshing. Rejected %s. Response body: %s",
                            widgetid, _describe_token(token), response.text[:200],
                        )
                        token = self._refresh_token(widgetid, force=True)
                        _LOGGER.info("After force-refresh: %s", _describe_token(token))
                        has_force_refreshed = True
                        headers = self._get_easyiq_header(token, inst_code, csrf_token)
                        try:
                            response = self._session.post(EASYIQ_API + "/weekplaninfo", json=post_data, headers=headers, verify=True)
                        except (RequestsTimeout, RequestsConnectionError) as e:
                            _LOGGER.warning("EasyIQ retry after token refresh failed with network error: %s", e)
                            response = None
                    if response == None or response.status_code != HTTPStatus.OK:
                        if response is not None:
                            _LOGGER.error(f"Failed to retrieve EasyIQ weekplan for child {child.first_name}. Error: {response.status_code}/{response.reason} - {response.text}.")
                            if first_run:
                                # Widget token failure — don't trigger main session reauth
                                if response.status_code == HTTPStatus.UNAUTHORIZED:
                                    raise AulaApiError(
                                        f"EasyIQ widget {widgetid} returned HTTP 401 even after force-refresh "
                                        f"({_describe_token(token)}). Response: {response.text[:200]}. "
                                        f"This usually means Aula's aulaToken endpoint is issuing tokens that EasyIQ rejects."
                                    )
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
                _LOGGER.warning(
                    "MinUddannelse rejected widget %s token, force-refreshing. Rejected %s. Response body: %s",
                    widgetid, _describe_token(token), response.text[:200],
                )
                token = self._refresh_token(widgetid, force=True)
                _LOGGER.info("After force-refresh: %s", _describe_token(token))
                headers = self._get_myeducation_header(token)
                has_force_refreshed = True
                try:
                    response = self._session.get(requesturl.format(weekno=weekno), headers=headers, verify=True)
                except (RequestsTimeout, RequestsConnectionError) as e:
                    _LOGGER.warning("MinUddannelse retry after token refresh failed with network error: %s", e)
                    response = None
            if response == None or response.status_code != HTTPStatus.OK:
                if response is not None:
                    _LOGGER.error(f"Failed to retrieve newsletters from children: {child_userids_as_str_list} from {from_datetime} to {to_datetime}. Error: {response.status_code}/{response.reason} - {response.text}.")
                    if first_run:
                        # Widget token failure — don't trigger main session reauth
                        if response.status_code == HTTPStatus.UNAUTHORIZED:
                            raise AulaApiError(
                                f"MinUddannelse widget {widgetid} returned HTTP 401 even after force-refresh "
                                f"({_describe_token(token)}). Response: {response.text[:200]}. "
                                f"This usually means Aula's aulaToken endpoint is issuing tokens that MinUddannelse rejects."
                            )
                        self._raise_error(response)
                from_datetime += timedelta(weeks=1)
                first_run = False
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
        # Serialize: prevents two coordinator threads from both making the
        # HTTP roundtrip for the same widget simultaneously.
        with self._token_refresh_lock:
            return self._refresh_token_locked(widgetid, force)

    def _refresh_token_locked(self, widgetid:AulaWidgetId, force: bool = False) -> AulaToken | None:
        """Fetch a fresh widget JWT, with proactive recovery from Aula's stale-cache bug.

        Behavior contract by mode and outcome:

        | Outcome                              | force=True             | force=False            |
        | -----------------------------------  | ---------------------- | ---------------------- |
        | HTTP non-200 from token endpoint     | evict + raise AulaApiError | log + return old token |
        | HTTP 200 + non-string `data`         | evict + raise AulaApiError | log + return old token |
        | HTTP 200 + valid JWT                 | cache + return         | cache + return         |
        | HTTP 200 + already-expired JWT       | trigger reset+retry recovery (see below) | same |
        | Network error / JSONDecodeError      | evict + raise AulaApiError | log + return old token |

        The "force returns nothing usable" rule exists to prevent silent retries
        with stale tokens that would loop the caller into reporting "HTTP 401
        after token refresh" when no actual refresh happened.

        Stale-at-issuance recovery (proactive, runs in BOTH force modes):
        Aula caches widget JWTs server-side keyed by HTTP session cookies.
        When the JWT we receive is already expired, we drop the cookie jar via
        reset_session(), warm a fresh server session via getProfilesByLogin,
        and retry getAulaToken once. If that retry succeeds we cache+return it;
        if it STILL returns expired, force=True raises AulaApiError and
        force=False evicts the cache and returns None.
        """
        token = self._tokens.get(widgetid)
        current_time = datetime.now(pytz.utc)
        # Double-checked locking guard: if another thread acquired the lock
        # before us and refreshed within the last 5 minutes, reuse its result
        # rather than making a redundant HTTP roundtrip.
        # 5 minutes is the dedup window — actual cache TTL is enforced by
        # _get_token using the JWT's own exp claim (or TOKEN_EXPIRATION_TIME
        # as fallback), NOT by this 5-minute value.
        if not force and token is not None and current_time - token.timestamp < timedelta(minutes=5):
            jwt_still_valid = token.expires_at is None or current_time < token.expires_at - TOKEN_EXPIRY_BUFFER
            if jwt_still_valid:
                _LOGGER.debug("Ignoring token refresh request to avoid refreshing too often for widget id: " + widgetid)
                return token

        url = f"{self._apiurl}?method=aulaToken.getAulaToken&widgetId={widgetid}"
        try:
            response: Response | None = None
            # Retry loop absorbs transient 5xx and network errors from Aula's token endpoint
            for attempt in range(1, REQUEST_MAX_ATTEMPTS + 1):
                try:
                    response = self._session.get(url, verify=True)
                except (RequestsTimeout, RequestsConnectionError) as e:
                    self._handle_request_exception(e, attempt, "aulaToken.getAulaToken")
                    continue
                if not self._should_retry_request(response, attempt):
                    break
            # If main Aula session returned 401 (access token expired mid-widget-refresh),
            # the callback refreshes it and we retry once. Without this, a main-session
            # hiccup during widget refresh would bubble up as a misleading widget error.
            response = self._retry_on_401(response, lambda: self._session.get(url, verify=True))
            if response is None or response.status_code != HTTPStatus.OK:
                if force:
                    self._tokens.pop(widgetid, None)
                    detail = (
                        f"HTTP {response.status_code} {response.reason}. Body: {response.text[:200]}"
                        if response is not None else "no response after retries"
                    )
                    raise AulaApiError(
                        f"Force-refresh failed for widget {widgetid}: aulaToken.getAulaToken returned {detail}"
                    )
                if response is not None:
                    _LOGGER.warning("Failed to refresh token for widget %s: HTTP %s %s. Body: %s",
                                    widgetid, response.status_code, response.reason, response.text[:200])
                return token
            responsedata = response.json()
            data = responsedata["data"]
            if not isinstance(data, str):
                if force:
                    self._tokens.pop(widgetid, None)
                    raise AulaApiError(
                        f"Force-refresh failed for widget {widgetid}: aulaToken.getAulaToken returned "
                        f"non-string data (type={type(data).__name__}, value={str(data)[:200]}). "
                        f"This is an Aula server-side bug."
                    )
                _LOGGER.warning("Widget token response for %s contained non-string data (%s), skipping: %s", widgetid, type(data).__name__, data)
                return token
            token = AulaToken(
                bearer_token = "Bearer " + data,
                timestamp = datetime.now(pytz.utc),
                expires_at = _decode_jwt_exp(data),
            )
            self._tokens[widgetid] = token
            now = datetime.now(pytz.utc)
            if token.expires_at is not None and token.expires_at <= now:
                # Aula's server-side bug: returned a JWT whose exp claim is
                # already in the past. Empirically, this happens because Aula
                # caches widget JWTs server-side keyed by HTTP session cookies
                # (Csrfp-Token, PHPSESSID, etc.) — NOT by access_token. When
                # the server-side session ages out, Aula keeps returning the
                # SAME stale cached JWT no matter how many times we re-call
                # getAulaToken with the same cookies (and even after
                # access_token rotation, since cookies are unchanged).
                #
                # The only client-side recovery is to drop the cookie jar
                # and force Aula to mint a fresh server-side session by
                # calling profiles.getProfilesByLogin first.
                cookie_summary = sorted(self._session.cookies.keys())
                _LOGGER.warning(
                    "Aula returned ALREADY-EXPIRED widget JWT for %s (exp: %s, now: %s, age: %ss, force=%s). "
                    "Proactively resetting HTTP session and retrying — does NOT wait for downstream "
                    "widget endpoint to reject this token first. Cookies before reset: %s. Full response: %s",
                    widgetid, token.expires_at.isoformat(), now.isoformat(),
                    (now - token.expires_at).total_seconds(), force,
                    cookie_summary, str(responsedata)[:500],
                )
                # Proactive recovery — runs in BOTH force=True and force=False paths.
                # Detecting expired-at-issuance ANY time we receive a JWT means we never
                # cache or hand out a known-bad token to a downstream widget call.
                try:
                    # Step 1: drop cookie jar and clear all widget caches
                    self.reset_session()
                    # Step 2: warm the new session by calling
                    # profiles.getProfilesByLogin — this is what causes
                    # Aula's gateway to allocate a fresh server session
                    # bound to the new cookies.
                    try:
                        warm = self._session.get(
                            f"{self._apiurl}?method=profiles.getProfilesByLogin",
                            verify=True,
                        )
                        _LOGGER.debug(
                            "Session warmup after reset: HTTP %s, new cookies: %s",
                            warm.status_code, sorted(self._session.cookies.keys()),
                        )
                    except (RequestsTimeout, RequestsConnectionError) as warm_err:
                        _LOGGER.warning(
                            "Session warmup after reset failed for widget %s: %s. "
                            "Trying widget token fetch anyway.",
                            widgetid, warm_err,
                        )
                    # Step 3: retry getAulaToken with fresh cookie jar
                    retry_response = self._session.get(url, verify=True)
                    if retry_response.status_code == HTTPStatus.OK:
                        retry_data = retry_response.json().get("data")
                        if isinstance(retry_data, str):
                            retry_token = AulaToken(
                                bearer_token = "Bearer " + retry_data,
                                timestamp = datetime.now(pytz.utc),
                                expires_at = _decode_jwt_exp(retry_data),
                            )
                            retry_now = datetime.now(pytz.utc)
                            retry_valid = (retry_token.expires_at is None
                                           or retry_token.expires_at > retry_now)
                            if retry_valid:
                                _LOGGER.info(
                                    "Widget %s token recovered after session reset (TTL: %ss)",
                                    widgetid,
                                    (retry_token.expires_at - retry_now).total_seconds() if retry_token.expires_at else "undecoded",
                                )
                                self._tokens[widgetid] = retry_token
                                return retry_token
                            _LOGGER.error(
                                "Widget %s STILL ALREADY-EXPIRED after session reset "
                                "(new exp: %s, now: %s, age: %ss). This is a confirmed "
                                "Aula server-side bug with no client-side workaround.",
                                widgetid,
                                retry_token.expires_at.isoformat() if retry_token.expires_at else "undecoded",
                                retry_now.isoformat(),
                                (retry_now - retry_token.expires_at).total_seconds() if retry_token.expires_at else "n/a",
                            )
                        else:
                            _LOGGER.error(
                                "Widget %s retry after session reset returned non-string "
                                "data (type=%s, value=%s)",
                                widgetid, type(retry_data).__name__, str(retry_data)[:200],
                            )
                    else:
                        _LOGGER.error(
                            "Widget %s retry after session reset returned HTTP %s %s. Body: %s",
                            widgetid, retry_response.status_code, retry_response.reason,
                            retry_response.text[:200],
                        )
                except (RequestsTimeout, RequestsConnectionError) as retry_err:
                    _LOGGER.warning(
                        "Widget %s retry after session reset failed with network error: %s",
                        widgetid, retry_err,
                    )
                # We tried our best; flag loudly that this is server-side.
                # In force=True mode, raise so caller knows refresh failed.
                # In force=False mode, evict the bad token and return None
                # so the caller can decide what to do (typically: skip widget call).
                _LOGGER.error(
                    "Aula issued an ALREADY-EXPIRED widget JWT for %s (exp: %s, now: %s, age: %ss). "
                    "This is an Aula server-side bug — the widget endpoint will reject this token. "
                    "If this persists, please report to the integration maintainers.",
                    widgetid, token.expires_at.isoformat(), now.isoformat(),
                    (now - token.expires_at).total_seconds(),
                )
                # Evict the bad token from cache so we don't keep handing it out
                self._tokens.pop(widgetid, None)
                if force:
                    raise AulaApiError(
                        f"Widget {widgetid}: Aula returned an already-expired JWT even after "
                        f"session reset (exp: {token.expires_at.isoformat()}, age: "
                        f"{(now - token.expires_at).total_seconds():.0f}s). Aula server-side bug."
                    )
                return None
            elif token.expires_at is not None:
                _LOGGER.debug(
                    "Widget %s token refreshed, JWT exp: %s (TTL: %ss)",
                    widgetid, token.expires_at.isoformat(),
                    (token.expires_at - now).total_seconds(),
                )
            return token
        except (RequestsTimeout, RequestsConnectionError, ConnectionError, json.JSONDecodeError, KeyError) as e:
            # ConnectionError is raised by _retry_on_401 on transient main-session refresh failure.
            # AulaCredentialError is intentionally NOT caught — must propagate to trigger reauth
            # when main-session credentials are genuinely invalid.
            if force:
                self._tokens.pop(widgetid, None)
                raise AulaApiError(
                    f"Force-refresh failed for widget {widgetid}: aulaToken.getAulaToken raised "
                    f"{type(e).__name__}: {e}"
                ) from e
            _LOGGER.warning("Failed to refresh widget token for %s: %s: %s", widgetid, type(e).__name__, e)
            return token

    def _get_token(self, widgetid:AulaWidgetId) -> AulaToken | None:
        """Return a cached widget token if still valid, else refresh.

        Uses the JWT's actual exp claim (with a small safety buffer) when
        available — this prevents serving tokens that the server considers
        expired even if our wall-clock cache window has not elapsed.
        Falls back to TOKEN_EXPIRATION_TIME when the JWT cannot be decoded.
        """
        _LOGGER.debug(f"Requesting new token for widget {widgetid}")
        # Use dict.get() instead of `in` + [] to avoid a KeyError race when
        # another thread runs reset_session() between the check and the access.
        # _refresh_token_locked already uses the same pattern.
        token = self._tokens.get(widgetid)
        if token is not None:
            current_time = datetime.now(pytz.utc)
            if token.expires_at is not None:
                # Trust the JWT's own exp claim — refresh slightly before it
                if current_time < token.expires_at - TOKEN_EXPIRY_BUFFER:
                    _LOGGER.debug("Reusing existing token for widget %s (exp: %s)", widgetid, token.expires_at.isoformat())
                    return token
            elif current_time - token.timestamp < TOKEN_EXPIRATION_TIME:
                # JWT exp not parseable — fall back to fixed cache window
                _LOGGER.debug("Reusing existing token for widget " + widgetid)
                return token
        return self._refresh_token(widgetid)

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

    def _retry_on_401(self, response: Response | None, request_fn: Callable[[], Response]) -> Response | None:
        """If response is 401, force-refresh the access token and retry once.

        This prevents transient 401s (e.g. token propagation delays on
        the server side) from triggering a full MitID re-authentication.

        AulaCredentialError from the callback (permanent credential failure)
        is allowed to propagate — the coordinator will convert it to reauth.
        """
        if response is None or response.status_code != HTTPStatus.UNAUTHORIZED:
            return response
        if self._token_refresh_callback is None:
            return response
        # Callback may raise AulaCredentialError for permanent failures — let it propagate
        if not self._token_refresh_callback():
            # Transient refresh failure — don't let the original 401 trigger reauth
            _LOGGER.warning("Access token refresh failed (transient), returning error without reauth")
            raise ConnectionError("Access token refresh failed — could not retry after 401")
        _LOGGER.debug("Got 401, retrying after access token refresh")
        try:
            retried = request_fn()
        except (RequestsTimeout, RequestsConnectionError):
            _LOGGER.debug("Retry after token refresh failed with network error")
            raise ConnectionError("Request failed after token refresh (network error)")
        if retried.status_code == HTTPStatus.UNAUTHORIZED:
            # Token was JUST refreshed successfully but API still returns 401 —
            # this is almost certainly a transient server-side issue, not dead credentials.
            _LOGGER.warning("API returned 401 even after successful token refresh — treating as transient")
            raise ConnectionError("API returned 401 after successful token refresh")
        return retried

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
        raise AulaApiError(message)
