from dataclasses import dataclass
from datetime import timedelta
import datetime
from typing import Dict, List, TypeVar
from homeassistant.util.dt import now
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import async_timeout
import logging

from .aula_proxy.models.module import (
    AulaInstitutionProfile,
    AulaCalendarEvent,
    AulaChildProfile,
    AulaWeeklyPlan,
)
from .aula_client import AulaClient
from .aula_proxy.aula_errors import AulaCredentialError

_LOGGER = logging.getLogger(__name__)

@dataclass
class AulaCalendarCoordinatorData:
    updated_events_for_listener_keys: List[int]
    updated_weekly_plans_for_listener_keys: List[int]

T = TypeVar("T", AulaInstitutionProfile, AulaChildProfile)
class AulaCalendarCoordinatorMeta[T]:
    keys: List[T]
    last_updated: datetime.datetime|None = None
    def __init__(self):
        self.keys = []

DATA_UPDATE_INTERVAL = timedelta(hours=6)
SYNC_EVENT_TIME = timedelta(days=14)
class AulaCalendarCoordinator(DataUpdateCoordinator[AulaCalendarCoordinatorData]):
    """My custom coordinator."""
    _weeklyplanmap: dict[int, List[AulaWeeklyPlan]]
    _eventmap: dict[int, List[AulaCalendarEvent]]
    _client: AulaClient
    _event_listeners = dict[int, AulaCalendarCoordinatorMeta[AulaInstitutionProfile]]()
    _weekly_plan_listeners = dict[int, AulaCalendarCoordinatorMeta[AulaChildProfile]]()

    def __init__(self, device_id: str, hass: HomeAssistant, client: AulaClient):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="calendar",
            # Polling interval. Will only be polled if there are subscribers.
            # We poll often, but limit the data update with DATA_UPDATE_INTERVAL. We want data to refresh past midnight no matter the interval.
            update_interval=timedelta(minutes=10),
            # Set always_update to `False` if the data returned from the
            # api can be compared via `__eq__` to avoid duplicate updates
            # being dispatched to listeners
            always_update=True
        )
        self._eventmap = dict()
        self._client = client
        self.device_id = device_id
        self.aula_version = client.aula_version

        _LOGGER.debug(f"Coordinator Calendar {device_id} initialized")

    def _connection_check(self) -> Exception | None:
        return self._client.connection_check()

    async def _async_setup(self) -> None:
        """Set up the coordinator

        This is the place to set up your coordinator,
        or to load data, that only needs to be loaded once.

        This method will be called automatically during
        coordinator.async_config_entry_first_refresh.

        If the refresh fails, async_config_entry_first_refresh will
        raise ConfigEntryNotReady and setup will try again later
        """
        await self.hass.async_add_executor_job(self._connection_check)

    async def _async_update_data(self) -> AulaCalendarCoordinatorData:
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:

            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(10):
                # Grab active context variables to limit data required to be fetched from API
                # Note: using context is not required if there is no need or ability to limit
                # data retrieved from API.
                # listening_ids = set(self.async_contexts())

                # always retrieve profiles first
                data = await self.hass.async_add_executor_job(self._fetch_data, self._event_listeners, self._weekly_plan_listeners)
                if isinstance(data, Exception):
                    raise data
                return data
        except AulaCredentialError as err:
            # Raising ConfigEntryAuthFailed will cancel future updates
            # and start a config flow with SOURCE_REAUTH (async_step_reauth)
            raise ConfigEntryAuthFailed from err
        except Exception as error:
            if isinstance(error.args, str):
                raise UpdateFailed(error.args)
            else:
                raise UpdateFailed(error)

    def _fetch_data(self, eventlisteners: Dict[int, AulaCalendarCoordinatorMeta[AulaInstitutionProfile]], weekplanlisteners: Dict[int, AulaCalendarCoordinatorMeta[AulaChildProfile]]) -> AulaCalendarCoordinatorData|Exception:
        try:
            logindata = self._client.login()
            self.aula_version = logindata.api_version

            new_eventmap, new_event_keys = self._fetch_events(eventlisteners)
            self._eventmap = new_eventmap

            new_weeklyplanmap, new_weeklyplan_keys = self._fetch_weekly_plans(weekplanlisteners)
            self._weeklyplanmap = new_weeklyplanmap

            data = AulaCalendarCoordinatorData(
                updated_events_for_listener_keys = new_event_keys,
                updated_weekly_plans_for_listener_keys = new_weeklyplan_keys
            )

            for key in new_event_keys:
                meta = eventlisteners.get(key)
                if meta: meta.last_updated = now()
                else: _LOGGER.warning(f"Out of sync with event listeners. {key} could not be found, even though it received new data")


            for key in new_weeklyplan_keys:
                meta = weekplanlisteners.get(key)
                if meta: meta.last_updated = now()
                else: _LOGGER.warning(f"Out of sync with weekplan listeners. {key} could not be found, even though it received new data")

        except Exception as ex:
            _LOGGER.error(ex)
            return ex
        # _LOGGER.debug(f"Coordinator fetched data: {data}")
        return data

    #region Events

    async def get_events_for_interval(self, profiles: List[AulaInstitutionProfile], start_date: datetime.datetime, end_date: datetime.datetime) -> List[AulaCalendarEvent]:
        return await self.hass.async_add_executor_job(self._client.get_calendar_events, profiles, start_date, end_date)

    def get_events(self, profile: AulaInstitutionProfile) -> List[AulaCalendarEvent]:
        key = profile.id
        if key not in self._event_listeners:
            raise KeyError(f"Listener not found for the event key. Ensure you add the key when component is added to HASS (async_add_event_key), and remove when component is removed from HASS (async_remove_event_key)")
        return self._eventmap.get(key, [])

    async def async_add_event_key(self, profile: AulaInstitutionProfile) -> None:
        id = profile.id
        meta = self._event_listeners.setdefault(id, AulaCalendarCoordinatorMeta[AulaInstitutionProfile]())
        _LOGGER.debug(f"async_add_event_key {id}")
        meta.keys.append(profile)
        self._eventmap.setdefault(id, [])
        await self.async_refresh()

    async def async_remove_event_key(self, profile: AulaInstitutionProfile) -> None:
        id = profile.id
        meta = self._event_listeners.get(id)
        if meta is None: return
        meta.keys.remove(profile)
        _LOGGER.debug(f"async_remove_event_key {id}")
        if len(meta.keys) == 0:
            self._event_listeners.pop(id)
            self._eventmap.pop(id)

    def _fetch_events(self, listeners: Dict[int, AulaCalendarCoordinatorMeta[AulaInstitutionProfile]]):
        request_data_institutions = list[AulaInstitutionProfile]()
        new_eventmap = dict[int, List[AulaCalendarEvent]]()
        for (id, meta) in listeners.items():
            if meta.last_updated is None or meta.last_updated < now() - DATA_UPDATE_INTERVAL or meta.last_updated.date() < now().date():
                request_data_institutions.append(meta.keys[0])
            else: #not requesting, reuse cached data
                new_eventmap[id] = self._eventmap.get(id, list[AulaCalendarEvent]())
        for institution in request_data_institutions:
            #Batch fetching and then splitting events across profiles is very difficult, so we fetch per institution
            events = self._client.get_calendar_events([institution], now(), now() + SYNC_EVENT_TIME)
            _LOGGER.debug(f"Fetching events for id: {institution.id}, got {len(events)} events")
            new_eventmap[institution.id] = events
        return (new_eventmap, [inst.id for inst in request_data_institutions])

    #endregion Events

    #region Weekly Plans

    async def get_weekly_plans_for_interval(self, profiles: List[AulaChildProfile], start_datetime: datetime.datetime, end_datetime: datetime.datetime) -> List[AulaWeeklyPlan]:
        return await self.hass.async_add_executor_job(self._client.get_weekly_plans, profiles, start_datetime, end_datetime)

    def get_weekly_plans(self, profile: AulaChildProfile) -> List[AulaWeeklyPlan]:
        key = profile.id
        if key not in self._weekly_plan_listeners:
            raise KeyError(f"Listener not found for the weekly_plan key. Ensure you add the key when component is added to HASS (async_add_weekly_plan_key), and remove when component is removed from HASS (async_remove_weekly_plan_key)")
        return self._weeklyplanmap.get(key, [])

    async def async_add_weekly_plan_key(self, profile: AulaChildProfile) -> None:
        id = profile.id
        meta = self._weekly_plan_listeners.setdefault(id, AulaCalendarCoordinatorMeta[AulaChildProfile]())
        _LOGGER.debug(f"async_add_weekly_plan_key {id}")
        meta.keys.append(profile)
        self._weeklyplanmap.setdefault(id, [])
        await self.async_refresh()

    async def async_remove_weekly_plan_key(self, profile: AulaChildProfile) -> None:
        id = profile.id
        meta = self._weekly_plan_listeners.get(id)
        if meta is None: return
        meta.keys.remove(profile)
        _LOGGER.debug(f"async_remove_weekly_plan_key {id}")
        if len(meta.keys) == 0:
            self._weekly_plan_listeners.pop(id)
            self._weeklyplanmap.pop(id)

    def _fetch_weekly_plans(self, listeners: Dict[int, AulaCalendarCoordinatorMeta[AulaChildProfile]]):
        request_data_institutions = list[AulaChildProfile]()
        new_weeklyplanmap = dict[int, List[AulaWeeklyPlan]]()
        for (id, meta) in listeners.items():
            if meta.last_updated is None or meta.last_updated < now() - DATA_UPDATE_INTERVAL or meta.last_updated.date() < now().date():
                request_data_institutions.append(meta.keys[0])
            else: #not requesting, reuse cached data
                new_weeklyplanmap[id] = self._weeklyplanmap.get(id, list[AulaWeeklyPlan]())

        for institution in request_data_institutions:
            #Batch fetching and then splitting weekly_plans across profiles is very difficult, so we fetch per institution
            weekly_plans = self._client.get_weekly_plans([institution], now(), now() + SYNC_EVENT_TIME)
            _LOGGER.debug(f"Fetching weekly_plans for id: {institution.id}, got {len(weekly_plans)} weekly_plans")
            new_weeklyplanmap[institution.id] = weekly_plans

        return (new_weeklyplanmap, [inst.id for inst in request_data_institutions])

    #endregion Weekly Plans