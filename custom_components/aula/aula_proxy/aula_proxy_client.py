import calendar
from bs4 import BeautifulSoup
from http import HTTPStatus
from requests import Session
from typing import Any, Dict, Iterable, List
# from homeassistant.util.dt import now
from datetime import datetime, timedelta, date
import json, re
import logging
import pytz
import requests

from .responses.get_weekly_plans_response import GetWeeklyPlansResponse
from .responses.get_daily_overview_response import AulaGetDailyOverviewResponse
from .responses.get_profile_context_response import AulaGetProfileContextResponse
from .aula_errors import ParseError, AulaCredentialError
from .models.aula_weekly_plan_parser import AulaWeeklyPlanParser
from .models.aula_profile_parser import AulaProfileParser
from .models.constants import AULA_WIDGET_ID
from .models.module import *
from .const import (
    API,
    API_VERSION,
    MIN_UDDANNELSE_API,
    MEEBOOK_API,
    SYSTEMATIC_API,
    EASYIQ_API,
)

_LOGGER = logging.getLogger(__name__)

class AulaProxyClient:
    api_version:int = int(API_VERSION)

    _login_result: AulaLoginData | None = None
    _tokens = dict[AULA_WIDGET_ID, AulaToken]()
    _is_logged_in: bool = False
    _apiurl:str = ""
    _username:str = ""
    _password:str = ""
    _session:Session

    def __init__(self, username:str, password:str):
        self._username = username
        self._password = password
        self._session = requests.Session()

    def custom_api_call(self, uri:str, post_data:str|None) -> Dict[str,str]:
        csrf_token = self._session.cookies.get_dict()["Csrfp-Token"]
        headers = {"csrfp-token": csrf_token, "content-type": "application/json"}
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
            res = response.json()
        except:
            res = {"raw_response": response.text}
        return res

    def login(self) -> AulaLoginData:
        """
        Logs into the Aula system and retrieves user profiles.
        This method performs the following steps:
        1. Attempts to log in using the session and API URL.
        2. If the initial login attempt fails, it navigates through the login forms for non-employees and unilogin.
        3. Fills out the necessary forms with username, password, and other required data.
        4. Handles redirects and retries up to 10 times to complete the login process.
        5. Finds the appropriate API URL in case of a version change.
        6. Retrieves and parses user profiles from the Aula API.
        7. Associates the user ID with each profile.
        Returns:
            AulaLoginData: Contains a list of user profiles, widgets, version etc.
        Raises:
            ParseError: If the login form is not found or multiple actions are found in the HTML response.
            AulaCredentialError: If access to the Aula API is denied or an unknown error occurs.
            ConnectionRefusedError: If the API URL is unreachable or an unknown error occurs.
        """
        _LOGGER.debug("Logging in")
        self._is_logged_in = False
        if self._session and self._apiurl:
            login_response = self._session.get(self._apiurl + "?method=profiles.getProfilesByLogin", verify=True).json()
            self._is_logged_in = login_response["status"]["message"] == "OK"

        _LOGGER.debug(f"Logged in already? {self._is_logged_in}")

        if self._is_logged_in and self._login_result is not None:
            return self._login_result

        #select login for non-employees (options: Non-employees / Employees)
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/112.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "da,en-US;q=0.7,en;q=0.3",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }
        params = {
            "type": "unilogin",
        }
        non_employee_login_response = self._session.get(
            "https://login.aula.dk/auth/login.php",
            params=params,
            headers=headers,
            verify=True,
        )
        # _LOGGER.debug(f"Result from {non_employee_login_response.url}: {non_employee_login_response.text}")

        #select unilogin (options: unilogin / MitID / Local login)
        html = BeautifulSoup(non_employee_login_response.text, features="lxml")
        if html.form is None:
            _LOGGER.debug(f"method=login response: {non_employee_login_response}")
            _LOGGER.error("Login form not found in the HTML response.")
            raise ParseError("Login form not found in the HTML response.")
        url = html.form["action"]
        if isinstance(url, list):
            _LOGGER.debug(f"method=login response: {non_employee_login_response}")
            _LOGGER.error("Login form found multiple actions in the HTML response.")
            _LOGGER.error(html)
            raise ParseError("Login form found multiple actions in the HTML response.")
        headers = {
            "Host": "broker.unilogin.dk",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/112.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "da,en-US;q=0.7,en;q=0.3",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "null",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
        }
        data = {
            "selectedIdp": "uni_idp",
        }
        uni_login_response = self._session.post(
            url,
            headers=headers,
            data=data,
            verify=True,
        )
        # _LOGGER.debug(f"Result from {uni_login_response.url}: {uni_login_response.text}")

        user_data = {
            "username": self._username,
            "password": self._password,
            "selected-aktoer": "KONTAKT",
        }
        redirects = 0
        success = False
        url = ""
        # navigate through forms and fill out username, password and other data. This is required as first page is only username, second is password etc.
        while success == False and redirects < 10:
            html = BeautifulSoup(uni_login_response.text, features="lxml")
            form = html.form
            if form is None:
                url = None
                _LOGGER.debug(f"method={url} response: {uni_login_response}")
                _LOGGER.error("Login form not found in the HTML response.")
                alert = html.find(class_="alert-text")
                if alert is not None:
                    raise ConnectionAbortedError(alert.get_text())
                else:
                    raise ParseError("Login details form not found in the HTML response.")

            errormsg = form.find(class_="form-error-message")
            if errormsg:
                errortext = errormsg.get_text()
                _LOGGER.error(errortext)
                if re.search(r'(?=.*(?:brugernavn|user))(?=.*(?:fundet|ugyldig|found|invalid)).+', errortext, re.IGNORECASE):
                    raise AulaCredentialError("Username is invalid")
                if re.search(r'(?=.*(?:kode|password))(?=.*(?:forkert|ugyldig|wrong|invalid)).+', errortext, re.IGNORECASE):
                    raise AulaCredentialError("Password is invalid")

            url = form["action"]

            if isinstance(url, str):
                post_data:Dict[str,str] = {}
                for input in html.find_all("input"):
                    if input.has_attr("name") and input.has_attr("value"):
                        post_data[input["name"]] = input["value"]
                        for key in user_data:
                            if input.has_attr("name") and input["name"] == key:
                                # _LOGGER.debug(f"Login progress - setting {key} = {user_data[key]}")
                                post_data[key] = user_data[key]

                uni_login_response = self._session.post(url, data=post_data, verify=True)
                # _LOGGER.debug(f"login process: request sent={uni_login_response.request}")
                if uni_login_response.url == "https://www.aula.dk:443/portal/":
                    _LOGGER.debug(f"Login success - redirected to portal. redirects: {redirects}")
                    success = True
            redirects += 1



        # Find the API url in case of a version change
        api_version = int(API_VERSION)
        original_profiles = profiles = [] if self._login_result is None else self._login_result["profiles"]
        while profiles == original_profiles:
            self._apiurl = API + str(self.api_version)
            _LOGGER.debug(f"Trying API at {self._apiurl}")
            api_response = self._session.get(f"{self._apiurl}?method=profiles.getProfilesByLogin", verify=True)
            # _LOGGER.debug(f"Result from {api_response.url}: {api_response.text}")
            if api_response.status_code == HTTPStatus.OK:
                _LOGGER.debug(f"API success: v{api_version}")
                try:
                    profiles = AulaProfileParser.parse_profiles(api_response.json()["data"]["profiles"])
                except Exception as e:
                    _LOGGER.debug(f"method=profiles.getProfilesByLogin response: {api_response}")
                    _LOGGER.error(f"Error parsing profiles: {e}")
                    raise
                # _LOGGER.debug("self._profiles "+str(self._profiles))
                break
            elif api_response.status_code == HTTPStatus.GONE:
                msg = f"API was expected at {self._apiurl} but responded with HTTP 410. The integration will automatically try a newer version and everything may work fine."
                _LOGGER.debug(msg)
                api_version += 1
                if int(API_VERSION) - api_version > 10:
                    raise ConnectionRefusedError(msg)
            elif api_response.status_code == HTTPStatus.FORBIDDEN:
                msg = "Access to Aula API was denied. Please check that you have entered the correct credentials. (Your password automatically expires on regular intervals!)"
                _LOGGER.error(msg)
                raise AulaCredentialError(msg)
            else:
                _LOGGER.debug(f"method=profiles.getProfilesByLogin response: {api_response}")
                msg = f"Unknown error occured. Received status code {api_response.status_code}."
                _LOGGER.error(msg)
                raise ConnectionRefusedError(msg)

        self.api_version = api_version
        widgets: List[AulaWidget] = []
        if len(profiles) > 0:
            response: AulaGetProfileContextResponse = self._session.get(f"{self._apiurl}?method=profiles.getProfileContext&portalrole=guardian",verify=True,).json()
            data = response["data"]
            #set user id on logged in profile
            userid = data["userId"]
            for profile in profiles:
                profile["user_id"] = userid

            #set user id on children profiles
            children = dict((child["id"], child) for child in self.flatten_children(profiles))
            institutions = None if "institutions" not in data else data["institutions"]
            if institutions:
                for institutiondata in institutions:
                    if "children" in institutiondata and institutiondata["children"] is not None:
                        for childdata in institutiondata["children"]:
                            child = children.get(childdata["id"])
                            if child: child["user_id"] = childdata["userId"]

            #read widgets (used to identify supported features)
            detected_widgets = response["data"]["pageConfiguration"]["widgetConfigurations"]
            try:
                widgets = AulaProfileParser.parse_widgets([widgetconf["widget"] for widgetconf in detected_widgets])
            except Exception as e:
                _LOGGER.debug(f"method=profiles.getProfileContext response: {response}")
                _LOGGER.error(f"Error parsing widgets: {e}")

        result: AulaLoginData = {
            "profiles": profiles,
            "widgets": widgets,
            "api_version": self.api_version
        }
        self._login_result = result
        # _LOGGER.debug(f"login: {result}")
        _LOGGER.debug(f"Login found {len(profiles)} profiles")
        _LOGGER.debug(f"Widgets found: {str.join(", ", [widget["widget_id"] for widget in widgets])}")
        return result

    def get_message_threads(self) -> List[AulaMessageThread]:
        _LOGGER.debug(f"Fetching message threads")
        response = self._session.get(f"{self._apiurl}?method=messaging.getThreads&sortOn=date&orderDirection=desc&page=0",verify=True).json()
        try:
            threads = AulaMessageThreadParser.parse_message_threads(response["data"]["threads"])
        except Exception as e:
            _LOGGER.debug(f"method=messaging.getThreads response: {response}")
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
        if thread["sensitive"]: raise PermissionError("Use Aula to read this message.")
        msgresponse = self._session.get(f"{self._apiurl}?method=messaging.getMessagesForThread&threadId={thread["id"]}&page=0",verify=True).json()
        status_code = msgresponse["status"]["code"]
        if status_code == HTTPStatus.FORBIDDEN: raise PermissionError(msgresponse["status"]["message"])
        if status_code != HTTPStatus.OK: raise ImportError(msgresponse["status"]["message"])
        try:
            messages = AulaMessageThreadParser.parse_messages(msgresponse["data"]["messages"])
        except Exception as e:
            _LOGGER.debug(f"method=messaging.getMessagesForThread response: {msgresponse}")
            _LOGGER.error(f"Error parsing messages: {e}")
            raise
        # _LOGGER.debug(f"get_messages: {messages}")
        return messages

    def get_daily_overviews(self, profiles: List[AulaProfile]) -> List[AulaDailyOverview]:
        _LOGGER.debug(f"Fetching daily overviews for {len(profiles)} profiles")
        if len(profiles) == 0: return []
        children = self.flatten_children(profiles)
        child_ids_as_str_list = list(set(str(child["id"]) for child in children))
        response: AulaGetDailyOverviewResponse = self._session.get(f"{self._apiurl}?method=presence.getDailyOverview&childIds[]={str.join("&childIds[]=", child_ids_as_str_list)}",verify=True).json()
        try:
            daily_overviews = AulaProfileParser.parse_daily_overviews(response["data"])
            if len(daily_overviews) < len(children):
                overview_ids = set[int](overview["id"] for overview in daily_overviews)
                for child in children:
                    if child["id"] not in overview_ids:
                        _LOGGER.warning(f"Unable to retrieve presence data from Aula from child with id {child['id']}. Some data will be missing from sensor entities.")
        except Exception as e:
            _LOGGER.debug(f"method=presence.getDailyOverview response: {response}")
            _LOGGER.error(f"Error parsing daily overviews: {e}")
            raise
        # _LOGGER.debug(f"get_daily_overviews: {daily_overviews}")
        _LOGGER.debug(f"Fetched daily overviews: {len(daily_overviews)}")
        return daily_overviews

    def get_calendar_events(self, profiles: List[AulaInstitutionProfile], start_date: datetime, end_date: datetime) -> List[AulaCalendarEvent]:
        _LOGGER.debug(f"Fetching calendar events for {len(profiles)} profiles")
        if len(profiles) == 0: return []
        inst_profile_ids = list(set(profile["id"] for profile in profiles))

        csrf_token = self._session.cookies.get_dict()["Csrfp-Token"]
        headers = {"csrfp-token": csrf_token, "content-type": "application/json"}

        start = start_date.strftime("%Y-%m-%d 00:00:00.0000%:z")
        end = end_date.strftime("%Y-%m-%d 00:00:00.0000%:z")

        # start = now().strftime("%Y-%m-%d 00:00:00.0000%:z")
        # end = (now() + timedelta(days=14)).strftime("%Y-%m-%d 00:00:00.0000%:z")

        # post_data = (f'{{"instProfileIds":[{str.join(",", child_ids_as_str_list)}],"resourceIds":[],"start":"{start}","end":"{end}"}}')
        post_data:Dict[str, Any] = dict()
        post_data["instProfileIds"] = inst_profile_ids
        post_data["resourceIds"] =  []
        post_data["start"] = start
        post_data["end"] = end

        # _LOGGER.debug("Calendar post-data: "+str(post_data))
        response = self._session.post(f"{self._apiurl}?method=calendar.getEventsByProfileIdsAndResourceIds", json=post_data, headers=headers, verify=True).json()
        # _LOGGER.debug(f"method=presence.getDailyOverview response: {response}")
        try:
            events = AulaCalendarParser.parse_calendar_events(response["data"])
        except Exception as e:
            _LOGGER.debug(f"method=presence.getDailyOverview response: {response}")
            _LOGGER.error(f"Error parsing daily overviews: {e}")
            raise
        # _LOGGER.debug(f"get_calendar_events: {result}")
        _LOGGER.debug(f"Fetched calendar events: {len(events)}")
        return events

    #TODO: Return List of known types
    def get_weekly_newsletters(self, profiles: List[AulaProfile], timestamp: datetime) -> Dict[str, str]:
        """Returns a dictionary of firstname, html - planned to be rewritten, but cant test for now due to missing data"""
        _LOGGER.debug(f"Fetching weekly newsletters for {len(profiles)} profiles")
        if len(profiles) == 0: return dict[str,str]()
        userid = self._get_user_id(profiles)
        children = self.flatten_children(profiles)
        child_ids_as_str_list = set(str(child["id"]) for child in children)
        childUserIds = ",".join(child_ids_as_str_list)
        widgets = [] if self._login_result is None else self._login_result["widgets"]
        weekletters = dict[str, str]()
        if self._has_widget(widgets, AULA_WIDGET_ID.MY_EDUCATION_WEEKLETTER) and not self._has_widget(widgets, AULA_WIDGET_ID.MY_EDUCATION_ASSIGNMENTS):
            token = self._get_token(AULA_WIDGET_ID.MY_EDUCATION_WEEKLETTER)
            week_no_str = self._get_aula_week_formatted(timestamp)
            get_payload = (f"/ugebrev?assuranceLevel=2&childFilter={childUserIds}&currentWeekNumber={week_no_str}&isMobileApp=false&placement=narrow&sessionUUID={userid}&userProfile=guardian")
            response = requests.get(
                MIN_UDDANNELSE_API + get_payload,
                headers={"Authorization": token["bearer_token"], "accept": "application/json"},
                verify=True,
            )
            data=response.json()
            # _LOGGER.debug("newsletter status_code "+str(response.status_code))
            # _LOGGER.debug("newsletter response "+str(response.text))
            try:
                for person in data["personer"]:
                    ugeplan = person["institutioner"][0]["ugebreve"][0]["indhold"]
                    weekletters[person["first_name"]] = ugeplan
            except:
                _LOGGER.debug("Cannot fetch newsletter, so setting as empty")
                _LOGGER.debug("newsletter response "+str(response.text))

        _LOGGER.debug(f"Fetched weekly newsletters: {len(weekletters)}")
        return weekletters

    #TODO: Return List of known types
    def get_task_list(self, profiles: List[AulaProfile], timestamp: datetime) -> Dict[str, str]:
        """Returns a dictionary of firstname, html - planned to be rewritten, but cant test for now due to missing data"""
        _LOGGER.debug(f"Fetching task list for {len(profiles)} profiles")
        if len(profiles) == 0: return dict[str,str]()
        userid = self._get_user_id(profiles)
        children = self.flatten_children(profiles)
        child_ids_as_str_list = set(str(child["id"]) for child in children)
        childUserIds = ",".join(child_ids_as_str_list)
        result = dict[str, str]()
        widgets = [] if self._login_result is None else self._login_result["widgets"]
        if self._has_widget(widgets, AULA_WIDGET_ID.MY_EDUCATION_ASSIGNMENTS):
            _LOGGER.debug("In the MU assignments flow")
            token = self._get_token(AULA_WIDGET_ID.MY_EDUCATION_ASSIGNMENTS)
            week_no_str = self._get_aula_week_formatted(timestamp)
            get_payload = f"/opgaveliste?assuranceLevel=2&childFilter={childUserIds}&currentWeekNumber={week_no_str}&isMobileApp=false&placement=narrow&sessionUUID={userid}&userProfile=guardian"
            response = requests.get(
                MIN_UDDANNELSE_API + get_payload,
                headers={"Authorization": token["bearer_token"], "accept": "application/json"},
                verify=True,
            )
            data = response.json()
            _LOGGER.debug(f"MU assignments status_code {response.status_code}")
            _LOGGER.debug(f"MU assignments response {response.text}")

            for child in self.flatten_children(profiles):
                first_name = child["first_name"]
                _ugep = ""
                for assignment in data.json()["opgaver"]:
                    _LOGGER.debug(f"i kuvertnavn split {assignment["kuvertnavn"].split()[0]}")
                    _LOGGER.debug(f"first_name {first_name}")
                    if assignment["kuvertnavn"].split()[0] == first_name:
                        _ugep += f"<h2>{assignment["title"]}</h2>"
                        _ugep += f"<h3>{assignment["kuvertnavn"]}</h3>"
                        _ugep += f"Ugedag: {assignment["ugedag"]}<br>"
                        _ugep += f"Type: {assignment["opgaveType"]}<br>"
                        for h in assignment["hold"]:
                            _ugep += f"Hold: {h["navn"]}<br>"
                        try:
                            _ugep += f"Forløb: {assignment["forloeb"]["navn"]}"
                        except:
                            _LOGGER.debug(f"Did not find forloeb key: {assignment}")
                result[first_name] = _ugep
                _LOGGER.debug(f"MU assignments result: {_ugep}")
        _LOGGER.debug(f"Fetched task list: {len(result)}")
        return result

    #TODO: Return List of known types
    def get_easyiq_weekplan(self, profiles: List[AulaProfile], timestamp: datetime) -> Dict[str, str]:
        """Returns a dictionary of firstname, html - planned to be rewritten, but cant test for now due to missing data"""
        _LOGGER.debug(f"Fetching easyiq weekplan for {len(profiles)} profiles")
        if len(profiles) == 0: return dict[str,str]()
        userid = self._get_user_id(profiles)
        children = self.flatten_children(profiles)
        institution_profile_codes = list(set(child["institution_code"] for child in children))

        widgets = [] if self._login_result is None else self._login_result["widgets"]
        result = dict[str, str]()
        if self._has_widget(widgets, AULA_WIDGET_ID.EASYIQ_WEEKPLAN):
            _LOGGER.debug("In the EasyIQ flow")
            token = self._get_token(AULA_WIDGET_ID.EASYIQ_WEEKPLAN)
            csrf_token = self._session.cookies.get_dict()["Csrfp-Token"]

            easyiq_headers = {
                "x-aula-institutionfilter": institution_profile_codes[0],
                "x-aula-userprofile": "guardian",
                "Authorization": token["bearer_token"],
                "accept": "application/json",
                "csrfp-token": csrf_token,
                "origin": "https://www.aula.dk",
                "referer": "https://www.aula.dk/",
                "authority": "api.easyiqcloud.dk",
            }

            week_no_str = self._get_aula_week_formatted(timestamp)
            for child in children:
                userid = child["user_id"]
                first_name = child["first_name"]

                _LOGGER.debug("EasyIQ headers " + str(easyiq_headers))
                post_data: Dict[str, Any] = {
                    "sessionId": userid,
                    "currentWeekNr": week_no_str,
                    "userProfile": "guardian",
                    "institutionFilter": institution_profile_codes,
                    "childFilter": [userid],
                }
                _LOGGER.debug(f"EasyIQ post data {post_data}")
                weekplans = requests.post(
                    EASYIQ_API + "/weekplaninfo",
                    json=post_data,
                    headers=easyiq_headers,
                    verify=True,
                )
                # _LOGGER.debug(
                #    "EasyIQ Opgaver status_code " + str(weekplans.status_code)
                # )
                _LOGGER.debug(f"EasyIQ Opgaver response {weekplans.json()}")
                _ugep = f"<h2>Uge {timestamp.isocalendar().week}</h2>"
                    # + weekplans.json()["Weekplan"]["ActivityName"]
                    # + weekplans.json()["Weekplan"]["WeekNo"]
                # from datetime import datetime

                for i in weekplans.json()["Events"]:
                    if self._matches_datetime_format(i["start"], "%Y/%m/%d %H:%M"):
                        _LOGGER.debug("No Event")
                        start_datetime = datetime.strptime(i["start"], "%Y/%m/%d %H:%M")
                        _LOGGER.debug(start_datetime)
                        end_datetime = datetime.strptime(i["end"], "%Y/%m/%d %H:%M")
                        if start_datetime.date() == end_datetime.date():
                            formatted_day = self._get_weekday(start_datetime.strftime("%d %m %Y"))
                            formatted_start = start_datetime.strftime(" %H:%M")
                            formatted_end = end_datetime.strftime("- %H:%M")
                            dresult = f"{formatted_day} {formatted_start} {formatted_end}"
                        else:
                            formatted_start = self._get_weekday(start_datetime.strftime("%d %m %Y"))
                            formatted_end = self._get_weekday(end_datetime.strftime("%d %m %Y"))
                            dresult = f"{formatted_start} {formatted_end}"
                        _ugep += f"<br><b>{dresult}</b><br>"
                        if i["itemType"] == "5":
                            _ugep += f"<br><b>{i["title"]}</b><br>"
                        else:
                            _ugep += f"<br><b>{i["ownername"]}</b><br>"
                        _ugep +=f"{i["description"]}<br>"
                    else:
                        _LOGGER.debug("None")
                    result[first_name] = _ugep
                _LOGGER.debug("EasyIQ result: " + str(_ugep))
        _LOGGER.debug(f"Fetched easyiq weekplan: {len(result)}")
        return result

    #TODO: Return List of known types
    def get_reminders(self, profiles: List[AulaProfile], timestamp: datetime) -> Dict[str, str]:
        """Returns a dictionary of firstname, html - planned to be rewritten, but cant test for now due to missing data"""
        _LOGGER.debug(f"Fetching reminders for {len(profiles)} profiles")
        if len(profiles) == 0: return dict[str,str]()
        children = self.flatten_children(profiles)
        child_ids_as_str_list = list(set(str(child["id"]) for child in children))
        institution_profile_codes = list(set(child["institution_code"] for child in children))

        widgets = [] if self._login_result is None else self._login_result["widgets"]
        result = dict[str, str]()
        if self._has_widget(widgets, AULA_WIDGET_ID.REMINDERS):
            _LOGGER.debug("In the Huskelisten flow...")
            token = self._get_token(AULA_WIDGET_ID.REMINDERS)
            huskelisten_headers = {
                "Accept": "application/json, text/plain, */*",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "en-US,en;q=0.9,da;q=0.8",
                "Aula-Authorization": token["bearer_token"],
                "Origin": "https://www.aula.dk",
                "Referer": "https://www.aula.dk/",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "cross-site",
                "User-Agent": "Mozilla/5.0 (X11; CrOS x86_64 15183.51.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
                "zone": "Europe/Copenhagen",
            }

            children = "&children=".join(child_ids_as_str_list)
            institutions = "&institutions=".join(institution_profile_codes)
            delta = datetime.now() + timedelta(days=180)
            From = datetime.now().strftime("%Y-%m-%d")
            dueNoLaterThan = delta.strftime("%Y-%m-%d")
            get_payload = f"/reminders/v1?children={children}&from={From}&dueNoLaterThan={dueNoLaterThan}&widgetVersion=1.10&userProfile=guardian&sessionId={self._username}&institutions={institutions}"
            _LOGGER.debug(f"Huskelisten get_payload: {SYSTEMATIC_API}{get_payload}")

            reminder_persons: List[Dict[str,Any]] = []
            #
            mock_huskelisten:int|str = 0
            #
            if mock_huskelisten == 1: # type: ignore
                _LOGGER.warning("Using mock data for Huskelisten.")
                mock_huskelisten = '[{"userName":"Emilie efternavn","userId":164625,"courseReminders":[],"assignmentReminders":[],"teamReminders":[{"id":76169,"institutionName":"Holme Skole","institutionId":183,"dueDate":"2022-11-29T23:00:00Z","teamId":65240,"teamName":"2A","reminderText":"Onsdagslektie: Matematikfessor.dk: Sænk skibet med plus.","createdBy":"Peter ","lastEditBy":"Peter ","subjectName":"Matematik"},{"id":76598,"institutionName":"Holme Skole","institutionId":183,"dueDate":"2022-12-06T23:00:00Z","teamId":65240,"teamName":"2A","reminderText":"Julekalender på Skoledu.dk: I skal forsøge at løse dagens kalenderopgave. opgaven kan også godt løses dagen efter.","createdBy":"Peter ","lastEditBy":"Peter Riis","subjectName":"Matematik"},{"id":76599,"institutionName":"Holme Skole","institutionId":183,"dueDate":"2022-12-13T23:00:00Z","teamId":65240,"teamName":"2A","reminderText":"Julekalender på Skoledu.dk: I skal forsøge at løse dagens kalenderopgave. opgaven kan også godt løses dagen efter.","createdBy":"Peter ","lastEditBy":"Peter ","subjectName":"Matematik"},{"id":76600,"institutionName":"Holme Skole","institutionId":183,"dueDate":"2022-12-20T23:00:00Z","teamId":65240,"teamName":"2A","reminderText":"Julekalender på Skoledu.dk: I skal forsøge at løse dagens kalenderopgave. opgaven kan også godt løses dagen efter.","createdBy":"Peter Riis","lastEditBy":"Peter Riis","subjectName":"Matematik"}]},{"userName":"Karla","userId":77882,"courseReminders":[],"assignmentReminders":[{"id":0,"institutionName":"Holme Skole","institutionId":183,"dueDate":"2022-12-08T11:00:00Z","courseId":297469,"teamNames":["5A","5B"],"teamIds":[65271,65258],"courseSubjects":[],"assignmentId":5027904,"assignmentText":"Skriv en novelle"}],"teamReminders":[{"id":76367,"institutionName":"Holme Skole","institutionId":183,"dueDate":"2022-11-30T23:00:00Z","teamId":65258,"teamName":"5A","reminderText":"Læse resten af kap.1 fra Ternet Ninja ( kopiark) Læs det hele højt eller vælg et afsnit. ","createdBy":"Christina ","lastEditBy":"Christina ","subjectName":"Dansk"}]},{"userName":"Vega  ","userId":206597,"courseReminders":[],"assignmentReminders":[],"teamReminders":[]}]'
                reminder_persons = json.loads(mock_huskelisten, strict=False)
            else:
                response = requests.get(
                    SYSTEMATIC_API + get_payload,
                    headers=huskelisten_headers,
                    verify=True,
                )
                try:
                    reminder_persons = json.loads(response.text, strict=False)
                except:
                    _LOGGER.error(
                        "Could not parse the response from Huskelisten as json."
                    )
                # _LOGGER.debug("Huskelisten raw response: "+str(response.text))

            for person in reminder_persons:
                name = person["userName"].split()[0]
                _LOGGER.debug("Huskelisten for " + name)
                huskel = ""
                reminders = person["teamReminders"]
                if len(reminders) > 0:
                    for reminder in reminders:
                        mytime = datetime.strptime(reminder["dueDate"], "%Y-%m-%dT%H:%M:%SZ")
                        ftime = mytime.strftime("%A %d. %B")
                        huskel += f"<h3>{ftime}</h3>"
                        huskel += f"<b>{reminder["subjectName"]}</b><br>"
                        huskel += f"af {reminder["createdBy"]}<br><br>"
                        content = re.sub(r"([0-9]+)(\.)", r"\1\.", reminder["reminderText"])
                        huskel += f"{content}<br><br>"
                else:
                    huskel += f"{name} har ingen påmindelser."
                result[name] = huskel
        _LOGGER.debug(f"Fetched reminders: {len(result)}")
        return result

    WEEKLY_PLANS_MAX_TIME = timedelta(days=14)
    #TODO: Return List of known types
    def get_weekly_plans(self, profiles: List[AulaChildProfile], from_datetime: datetime, to_datetime: datetime) -> List[AulaWeeklyPlan]:
        """Returns a dictionary of firstname, html - planned to be rewritten, but cant test for now due to missing data"""
        _LOGGER.debug(f"Fetching weekplan for {len(profiles)} profiles")
        if len(profiles) == 0: return []
        children = profiles
        child_userids_as_str_list = list(set(str(child["user_id"]) for child in children))
        institution_profile_codes = list(set(child["institution_code"] for child in children))
        widgets = [] if self._login_result is None else self._login_result["widgets"]
        result = list[AulaWeeklyPlan]()
        if self._has_widget(widgets, AULA_WIDGET_ID.WEEKPLAN_PARENTS):
            # Try Meebook:
            _LOGGER.debug("In the Meebook flow...")
            token = self._get_token(AULA_WIDGET_ID.WEEKPLAN_PARENTS)
            # _LOGGER.debug("Token "+token)
            headers: Dict[str, str] = {
                "authority": "app.meebook.com",
                "accept": "application/json",
                "authorization": token["bearer_token"],
                "dnt": "1",
                "origin": "https://www.aula.dk",
                "referer": "https://www.aula.dk/",
                "sessionuuid": self._username,
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
                "x-version": "1.0",
            }

            from_datetime = from_datetime - timedelta(days=from_datetime.weekday()) #ensure it is a monday
            from_date = from_datetime.date()
            weeklyplans = list[AulaWeeklyPlan]()
            while from_datetime < to_datetime:
                from_date = from_datetime.date()
                week_no_str = self._get_aula_week_formatted(from_date)
                get_payload = f"/relatedweekplan/all?currentWeekNumber={week_no_str}&userProfile=guardian&childFilter[]={str.join("&childFilter[]=",child_userids_as_str_list)}&institutionFilter[]={str.join("&institutionFilter[]=",institution_profile_codes)}"
                responses:List[GetWeeklyPlansResponse]|Any = requests.get(MEEBOOK_API + get_payload, headers=headers, verify=True).json()

                # meebook_persons = json.loads(response.text, strict=False)
                # _LOGGER.debug("Meebook weekplan raw response from week "+week+": "+str(response.text))
                if not isinstance(responses, List):
                    _LOGGER.error(f"Failed to retrieve weekly plan for children: {", ".join(f"{child["first_name"]}({child["user_id"]})" for child in children)}. Error: {responses}")
                else:
                    for response in responses:
                        response["from_date"] = from_date
                        response["to_date"] = response["from_date"] + timedelta(days=6)
                    weeklyplans.extend(AulaWeeklyPlanParser.parse_weekly_plans(responses))
                from_datetime += timedelta(weeks=1)

            return weeklyplans

            # for plan in weeklyplans:
            #     _LOGGER.debug(f"Meebook weekplan for {plan["name"]}")
            #     ugep = ""
            #     weekplan = plan["weekPlan"]
            #     for day in weekplan:
            #         ugep += f"<h3>{day["date"]}</h3>"
            #         if len(day["tasks"]) > 0:
            #             for task in day["tasks"]:
            #                 if not task["pill"] == "Ingen fag tilknyttet":
            #                     ugep += f"<b>{task["pill"]}</b><br>"
            #                 ugep += f"{task["author"]}<br><br>"
            #                 content = re.sub(r"([0-9]+)(\.)", r"\1\.", task["content"])
            #                 ugep += f"{content}<br><br>"
            #         else:
            #             ugep += "-"
            #     # try:
            #     #     name = person["first_name"]
            #     # except:
            #     #     name = person["name"]
            #     result = ugep
        _LOGGER.debug(f"Fetched weekplan: {len(result)}")
        return result

    def _get_token(self, widgetid:AULA_WIDGET_ID) -> AulaToken:
        _LOGGER.debug(f"Requesting new token for widget {widgetid}")
        if widgetid in self._tokens:
            token = self._tokens[widgetid]
            current_time = datetime.now(pytz.utc)
            if current_time - token["timestamp"] < timedelta(minutes=1):
                _LOGGER.debug("Reusing existing token for widget " + widgetid)
                return token
        response = self._session.get(f"{self._apiurl}?method=aulaToken.getAulaToken&widgetId={widgetid}", verify=True).json()
        responsedata = response["data"]
        token:AulaToken = {
            # "token": str(responsedata),
            "bearer_token": "Bearer " + str(responsedata),
            "timestamp": datetime.now(pytz.utc)
        }
        self._tokens[widgetid] = token
        return token

    #TODO: Return List of known types
    def _get_user_id(self, profiles: List[AulaProfile]) -> str:
        """Ensures that each profile in the provided list has a user_id by fetching it from the API."""
        currentid: str|None = None
        for profile in profiles:
            if "user_id" not in profile or profile["user_id"] is None:
                currentid = None
                break
            else:
                currentid = profile["user_id"]

        if currentid is not None:
            return currentid

        response = self._session.get(f"{self._apiurl}?method=profiles.getProfileContext&portalrole=guardian",verify=True,).json()
        newid = response["data"]["userId"]

        for profile in profiles:
            profile["user_id"] = newid

        return newid

    @staticmethod
    def flatten_children(profiles: Iterable[AulaProfile]) -> List[AulaChildProfile]:
        result: List[AulaChildProfile] = []
        for profile in profiles:
            for child in profile["children"]:
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
    def _has_widget(widgets: List[AulaWidget], widget_match: AULA_WIDGET_ID) -> bool:
        return any(widget["widget_id"] == widget_match for widget in widgets)


    @staticmethod
    def _get_aula_week_formatted(timestamp: datetime|date) -> str:
        return timestamp.strftime("%Y-W%W")