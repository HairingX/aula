from typing import List
import datetime
import logging

from .aula_proxy.const import API_VERSION
from .aula_proxy.models.constants import AulaWidgetId
from .aula_proxy.module import (
        AulaBirthdayEvent,
        AulaCalendarEvent,
        AulaDailyOverview,
        AulaEasyiqWeeklyPlan,
        AulaInstitutionProfile,
        AulaLoginData,
        AulaMessageThread,
        AulaProfile,
        AulaProxyClient,
        AulaWeeklyPlan,
        AulaChildProfile,
        AULA_NOTIFICATION_TYPES
    )

_LOGGER = logging.getLogger(__name__)

class AulaClient:
    aula_version: int = int(API_VERSION)
    _proxy: AulaProxyClient

    def __init__(self, username:str, password:str):
        self._proxy = AulaProxyClient(username, password)

    def connection_check(self) -> None:
        """
        Attempts to log in using the proxy.
        Raises:
            ParseError: If the login form is not found or multiple actions are found in the HTML response.
            AulaCredentialError: If access to the Aula API is denied or an unknown error occurs.
            ConnectionRefusedError: If the API URL is unreachable or an unknown error occurs.
        """
        self._proxy.login()
        self.aula_version = self._proxy.api_version

    def has_widget(self, widgetid: AulaWidgetId):
        return self._proxy.has_widget(widgetid)

    def login(self) -> AulaLoginData:
        return self._proxy.login()

    def get_birthday_events(self, profiles: List[AulaChildProfile], start_datetime: datetime.datetime, end_datetime: datetime.datetime) -> List[AulaBirthdayEvent]:
        return self._proxy.get_birthday_events(profiles, start_datetime, end_datetime)

    def get_daily_overviews(self, profiles: List[AulaProfile]) -> List[AulaDailyOverview]:
        return self._proxy.get_daily_overviews(profiles)

    def get_calendar_events(self, profiles: List[AulaInstitutionProfile], start_datetime: datetime.datetime, end_datetime: datetime.datetime) -> List[AulaCalendarEvent]:
        return self._proxy.get_calendar_events(profiles, start_datetime, end_datetime)

    def get_message_threads(self) -> List[AulaMessageThread]:
        return self._proxy.get_message_threads()

    def get_notifications(self, profiles: List[AulaChildProfile]) -> List[AULA_NOTIFICATION_TYPES]:
        return self._proxy.get_notifications(profiles)

    def get_weekly_plans(self, profiles: List[AulaChildProfile], start_datetime: datetime.datetime, end_datetime: datetime.datetime) -> List[AulaWeeklyPlan]:
        return self._proxy.get_weekly_plans(profiles, start_datetime, end_datetime)

    def get_easyiq_weekly_plans(self, profiles: List[AulaChildProfile], start_datetime: datetime.datetime, end_datetime: datetime.datetime) -> List[AulaEasyiqWeeklyPlan]:
        return self._proxy.get_easyiq_weekly_plans(profiles, start_datetime, end_datetime)
