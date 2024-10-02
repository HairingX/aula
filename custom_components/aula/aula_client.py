import logging
from typing import Dict, List, Tuple, TypedDict
import datetime

from .const import API_VERSION
from .aula_proxy.module import (
        AulaCalendarEvent,
        AulaDailyOverview,
        AulaInstitutionProfile,
        AulaLoginData,
        AulaMessageThread,
        AulaProfile,
        AulaProxyClient,
        AulaWeeklyPlan,
        AulaChildProfile,
    )

_LOGGER = logging.getLogger(__name__)

class AulaData(TypedDict):
    reminders:int

class AulaClient:
    aula_version: int = int(API_VERSION)
    _proxy: AulaProxyClient

    huskeliste:Dict[str,str] = {}
    presence:Dict[str,bool] = {}
    ugep_attr:Dict[str,str] = {}
    ugepnext_attr:Dict[str,str] = {}
    widgets:Dict[str,str] = {}
    tokens:Dict[str, Tuple[str, datetime.datetime]] = {}

    def __init__(self, username:str, password:str):
        self._proxy = AulaProxyClient(username, password)

    def connection_check(self) -> Exception | None:
        """
        Attempts to log in using the proxy, returns an exception if it fails. None if successfully connected
        Raises:
            ParseError: If the login form is not found or multiple actions are found in the HTML response.
            AulaCredentialError: If access to the Aula API is denied or an unknown error occurs.
            ConnectionRefusedError: If the API URL is unreachable or an unknown error occurs.
        """
        self._proxy.login()
        self.aula_version = self._proxy.api_version

    def login(self) -> AulaLoginData:
        return self._proxy.login()

    def get_message_threads(self, profiles: List[AulaProfile]) -> List[AulaMessageThread]:
        return self._proxy.get_message_threads()

    def get_daily_overviews(self, profiles: List[AulaProfile]) -> List[AulaDailyOverview]:
        return self._proxy.get_daily_overviews(profiles)

    def get_calendar_events(self, profiles: List[AulaInstitutionProfile], start_datetime: datetime.datetime, end_datetime: datetime.datetime) -> List[AulaCalendarEvent]:
        return self._proxy.get_calendar_events(profiles, start_datetime, end_datetime)

    def get_weekly_plans(self, profiles: List[AulaChildProfile], start_datetime: datetime.datetime, end_datetime: datetime.datetime) -> List[AulaWeeklyPlan]:
        return self._proxy.get_weekly_plans(profiles, start_datetime, end_datetime)

    # def get_widgets_data(self, profiles: List[AulaProfile]) -> List[Any]:
    #     widgets = self.get_widgets()

    #     if len(widgets) == 0:
    #         self.get_widgets()
    #     if (
    #         not self._has_widget(widgets, AULA_WIDGETS.EASYIQ_WEEKPLAN)
    #         and not self._has_widget(widgets, AULA_WIDGETS.WEEKPLAN_PARENTS)
    #         and not self._has_widget(widgets, AULA_WIDGETS.MY_EDUCATION_WEEKLETTER)
    #         and not self._has_widget(widgets, AULA_WIDGETS.MY_EDUCATION_ASSIGNMENTS)
    #         and not self._has_widget(widgets, AULA_WIDGETS.REMINDERS)
    #     ):
    #         _LOGGER.error(
    #             "You have enabled weekplans, but we cannot find any supported widgets (0001,0004,0029,0030,0062) in Aula."
    #         )
    #     if self._has_widget(widgets, AULA_WIDGETS.MY_EDUCATION_WEEKLETTER) and self._has_widget(widgets, AULA_WIDGETS.WEEKPLAN_PARENTS):
    #         _LOGGER.warning("Multiple sources for weekplans is untested and might cause problems.")

    #     now = datetime.datetime.now() + datetime.timedelta(weeks=1)
    #     thisweek = datetime.datetime.now().strftime("%Y-W%W")
    #     nextweek = now.strftime("%Y-W%W")
    #     self._weekplan(thisweek, "this")
    #     self._weekplan(nextweek, "next")
    #     # _LOGGER.debug("End result of weekplan object: "+str(self.ug ep_attr))
    #     # End of Weekplans
    #     return True

    # async def update_data(self):
    #     profiles = self._proxy.login()

    #     self._childnames: Dict[str, str] = {}
    #     self._institutions: Dict[str, str] = {}
    #     self._childuserids: List[str] = []
    #     self._childids: List[str] = []
    #     self._children: List[Dict[str, str]] = []
    #     self._institutionProfiles: List[str] = []
    #     self._childrenFirstNamesAndUserIDs: Dict[str, str] = {}

    #     thisweek = datetime.datetime.now()
    #     nextweek = (thisweek + datetime.timedelta(weeks=1))

    #     widgets = self._proxy.get_widgets()
    #     self._proxy.get_calendar_events(profiles)
    #     self._proxy.get_daily_overviews(profiles)
    #     self._proxy.get_message_threads()
    #     self._proxy.get_easyiq_weekplan(profiles, widgets, thisweek)
    #     self._proxy.get_easyiq_weekplan(profiles, widgets, nextweek)
    #     self._proxy.get_reminders(profiles, widgets, thisweek)
    #     self._proxy.get_reminders(profiles, widgets, nextweek)
    #     self._proxy.get_task_list(profiles, widgets, thisweek)
    #     self._proxy.get_task_list(profiles, widgets, nextweek)
    #     self._proxy.get_weekly_newsletters(profiles, widgets, thisweek)
    #     self._proxy.get_weekly_newsletters(profiles, widgets, nextweek)

    #     # _LOGGER.debug("End result of weekplan object: "+str(self.ugep_attr))
    #     # End of Weekplans
    #     return True

    # def get_data(self, child_id: int) -> AulaData:
    #     return {
    #         'reminders': child_id
    #     }

