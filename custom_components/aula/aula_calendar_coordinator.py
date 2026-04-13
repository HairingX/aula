from dataclasses import dataclass
from datetime import timedelta
import datetime
from typing import Dict, List, TypeVar
from homeassistant.util.dt import now
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import asyncio
import logging

from .aula_proxy.models.module import (
    AulaInstitutionProfile,
    AulaBirthdayEvent,
    AulaCalendarEvent,
    AulaChildProfile,
    AulaEasyiqWeeklyPlan,
    AulaWeeklyNewsletter,
    AulaWeeklyPlan,
)
from .aula_client import AulaClient
from .aula_proxy.aula_errors import AulaCredentialError

_LOGGER = logging.getLogger(__name__)

# Coordinator polling interval (how often HA calls _async_update_data)
COORDINATOR_POLL_INTERVAL = timedelta(minutes=10)

# Per-data-type refresh intervals (how often we actually fetch fresh data from Aula)
BIRTHDAYS_UPDATE_INTERVAL = timedelta(days=1)
EVENTS_UPDATE_INTERVAL = timedelta(hours=2)
WEEKLY_PLANS_UPDATE_INTERVAL = timedelta(hours=2)
EASYIQ_WEEKPLAN_UPDATE_INTERVAL = timedelta(hours=2)
NEWSLETTER_UPDATE_INTERVAL = timedelta(hours=2)

# How far ahead to sync calendar data
SYNC_EVENT_MAX_TIME = timedelta(weeks=2)

# Number of consecutive fetch failures before raising UpdateFailed
MAX_CONSECUTIVE_FAILURES = 3

@dataclass
class AulaCalendarCoordinatorData:
    updated_birthdays_for_listener_keys: List[int]
    updated_events_for_listener_keys: List[int]
    updated_weekly_plans_for_listener_keys: List[int]
    updated_easyiq_weekplans_for_listener_keys: List[int]
    updated_newsletters_for_listener_keys: List[int]

T = TypeVar("T", AulaInstitutionProfile, AulaChildProfile)
class AulaCalendarCoordinatorMeta[T]:
    keys: List[T]
    last_updated: datetime.datetime|None = None
    def __init__(self):
        self.keys = []

class AulaCalendarCoordinator(DataUpdateCoordinator[AulaCalendarCoordinatorData]):
    """My custom coordinator."""
    _birthdaymap: dict[int, List[AulaBirthdayEvent]]
    _weeklyplanmap: dict[int, List[AulaWeeklyPlan]]
    _easyiqweekplanmap: dict[int, List[AulaEasyiqWeeklyPlan]]
    _newslettermap: dict[int, List[AulaWeeklyNewsletter]]
    _eventmap: dict[int, List[AulaCalendarEvent]]
    _client: AulaClient
    _birthday_listeners: dict[int, AulaCalendarCoordinatorMeta[AulaChildProfile]]
    _event_listeners: dict[int, AulaCalendarCoordinatorMeta[AulaInstitutionProfile]]
    _weekly_plan_listeners: dict[int, AulaCalendarCoordinatorMeta[AulaChildProfile]]
    _easyiq_weekplan_listeners: dict[int, AulaCalendarCoordinatorMeta[AulaChildProfile]]
    _newsletter_listeners: dict[int, AulaCalendarCoordinatorMeta[AulaChildProfile]]

    def __init__(self, device_id: str, hass: HomeAssistant, client: AulaClient, config_entry: ConfigEntry):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="calendar",
            config_entry=config_entry,
            # Polling interval. Will only be polled if there are subscribers.
            # We poll often, but limit the data update with DATA_UPDATE_INTERVAL. We want data to refresh past midnight no matter the interval.
            update_interval=COORDINATOR_POLL_INTERVAL,
            # Set always_update to `False` if the data returned from the
            # api can be compared via `__eq__` to avoid duplicate updates
            # being dispatched to listeners
            always_update=True,
        )
        self._birthdaymap = dict()
        self._eventmap = dict()
        self._weeklyplanmap = dict()
        self._easyiqweekplanmap = dict()
        self._newslettermap = dict()
        self._birthday_listeners = dict()
        self._event_listeners = dict()
        self._weekly_plan_listeners = dict()
        self._easyiq_weekplan_listeners = dict()
        self._newsletter_listeners = dict()
        self._consecutive_failures = 0
        self._client = client
        self.device_id = device_id
        self.aula_version = client.aula_version

        _LOGGER.debug(f"Coordinator Calendar {device_id} initialized")

    def _connection_check(self) -> None:
        self._client.connection_check()

    async def _async_setup(self) -> None:
        """Set up the coordinator

        This is the place to set up your coordinator,
        or to load data, that only needs to be loaded once.

        This method will be called automatically during
        coordinator.async_config_entry_first_refresh.

        If the refresh fails, async_config_entry_first_refresh will
        raise ConfigEntryNotReady and setup will try again later
        """
        try:
            await self.hass.async_add_executor_job(self._connection_check)
        except AulaCredentialError as err:
            raise ConfigEntryAuthFailed from err

    async def _async_update_data(self) -> AulaCalendarCoordinatorData:
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:

            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with asyncio.timeout(120):
                # Grab active context variables to limit data required to be fetched from API
                # Note: using context is not required if there is no need or ability to limit
                # data retrieved from API.
                # listening_ids = set(self.async_contexts())

                # always retrieve profiles first
                data = await self.hass.async_add_executor_job(self._fetch_data, self._birthday_listeners, self._event_listeners, self._weekly_plan_listeners, self._easyiq_weekplan_listeners, self._newsletter_listeners)
                if isinstance(data, Exception):
                    raise data
                return data
        except AulaCredentialError as err:
            # Raising ConfigEntryAuthFailed will cancel future updates
            # and start a config flow with SOURCE_REAUTH (async_step_reauth)
            raise ConfigEntryAuthFailed from err
        except Exception as error:
            if error.args and isinstance(error.args[0], str):
                raise UpdateFailed(error.args[0]) from error
            else:
                raise UpdateFailed from error

    def _fetch_data(self, birthdaylisteners: Dict[int, AulaCalendarCoordinatorMeta[AulaChildProfile]], eventlisteners: Dict[int, AulaCalendarCoordinatorMeta[AulaInstitutionProfile]], weekplanlisteners: Dict[int, AulaCalendarCoordinatorMeta[AulaChildProfile]], easyiqweekplanlisteners: Dict[int, AulaCalendarCoordinatorMeta[AulaChildProfile]], newsletterlisteners: Dict[int, AulaCalendarCoordinatorMeta[AulaChildProfile]]) -> AulaCalendarCoordinatorData|Exception:
        # Login is required for all fetches — if this fails, nothing works
        try:
            logindata = self._client.login()
            self.aula_version = logindata.api_version
        except AulaCredentialError:
            raise
        except Exception as ex:
            _LOGGER.error(f"Login failed: {ex}")
            return ex

        # Fetch each data type independently — a failure in one does not affect the others
        had_failure = False

        new_birtyday_keys = list[int]()
        try:
            new_birthdaymap, new_birtyday_keys = self._fetch_birthdays(birthdaylisteners)
            self._birthdaymap = new_birthdaymap
        except AulaCredentialError:
            raise
        except Exception as ex:
            had_failure = True
            _LOGGER.warning(f"Failed to fetch birthdays, using cached data: {ex}")

        new_event_keys = list[int]()
        try:
            new_eventmap, new_event_keys = self._fetch_events(eventlisteners)
            self._eventmap = new_eventmap
        except AulaCredentialError:
            raise
        except Exception as ex:
            had_failure = True
            _LOGGER.warning(f"Failed to fetch events, using cached data: {ex}")

        new_weeklyplan_keys = list[int]()
        try:
            new_weeklyplanmap, new_weeklyplan_keys = self._fetch_weekly_plans(weekplanlisteners)
            self._weeklyplanmap = new_weeklyplanmap
        except AulaCredentialError:
            raise
        except Exception as ex:
            had_failure = True
            _LOGGER.warning(f"Failed to fetch weekly plans, using cached data: {ex}")

        new_easyiq_keys = list[int]()
        try:
            new_easyiqweekplanmap, new_easyiq_keys = self._fetch_easyiq_weekly_plans(easyiqweekplanlisteners)
            self._easyiqweekplanmap = new_easyiqweekplanmap
        except AulaCredentialError:
            raise
        except Exception as ex:
            had_failure = True
            _LOGGER.warning(f"Failed to fetch EasyIQ weekplans, using cached data: {ex}")

        new_newsletter_keys = list[int]()
        try:
            new_newslettermap, new_newsletter_keys = self._fetch_newsletters(newsletterlisteners)
            self._newslettermap = new_newslettermap
        except AulaCredentialError:
            raise
        except Exception as ex:
            had_failure = True
            _LOGGER.warning(f"Failed to fetch newsletters, using cached data: {ex}")

        # Track consecutive failures — only raise after MAX_CONSECUTIVE_FAILURES
        if had_failure:
            self._consecutive_failures += 1
            if self._consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                self._consecutive_failures = 0
                return Exception(f"Aula API failed {MAX_CONSECUTIVE_FAILURES} consecutive times")
            _LOGGER.debug(f"Fetch had partial failures ({self._consecutive_failures}/{MAX_CONSECUTIVE_FAILURES} before unavailable)")
        else:
            self._consecutive_failures = 0

        # Update last_updated for successful fetches
        for key in new_birtyday_keys:
            meta = birthdaylisteners.get(key)
            if meta: meta.last_updated = now()

        for key in new_event_keys:
            meta = eventlisteners.get(key)
            if meta: meta.last_updated = now()

        for key in new_weeklyplan_keys:
            meta = weekplanlisteners.get(key)
            if meta: meta.last_updated = now()

        for key in new_easyiq_keys:
            meta = easyiqweekplanlisteners.get(key)
            if meta: meta.last_updated = now()

        for key in new_newsletter_keys:
            meta = newsletterlisteners.get(key)
            if meta: meta.last_updated = now()

        return AulaCalendarCoordinatorData(
            updated_birthdays_for_listener_keys=new_birtyday_keys,
            updated_events_for_listener_keys=new_event_keys,
            updated_weekly_plans_for_listener_keys=new_weeklyplan_keys,
            updated_easyiq_weekplans_for_listener_keys=new_easyiq_keys,
            updated_newsletters_for_listener_keys=new_newsletter_keys,
        )


    #region Birthdays

    async def get_birthdays_for_interval(self, profiles: List[AulaChildProfile], start_datetime: datetime.datetime, end_datetime: datetime.datetime) -> List[AulaBirthdayEvent]:
        return await self.hass.async_add_executor_job(self._client.get_birthday_events, profiles, start_datetime, end_datetime)

    def get_birthdays(self, profile: AulaChildProfile) -> List[AulaBirthdayEvent]:
        key = profile.id
        if key not in self._birthday_listeners:
            raise KeyError(f"Listener not found for the birthday key. Ensure you add the key when component is added to HASS (async_add_birthday_key), and remove when component is removed from HASS (async_remove_birthday_key)")
        return self._birthdaymap.get(key, [])

    async def async_add_birthday_key(self, profile: AulaChildProfile) -> None:
        id = profile.id
        meta = self._birthday_listeners.setdefault(id, AulaCalendarCoordinatorMeta[AulaChildProfile]())
        _LOGGER.debug(f"async_add_birthday_key {id}")
        meta.keys.append(profile)
        self._birthdaymap.setdefault(id, [])
        await self.async_refresh()

    async def async_remove_birthday_key(self, profile: AulaChildProfile) -> None:
        id = profile.id
        meta = self._birthday_listeners.get(id)
        if meta is None: return
        meta.keys.remove(profile)
        _LOGGER.debug(f"async_remove_birthday_key {id}")
        if len(meta.keys) == 0:
            self._birthday_listeners.pop(id)
            self._birthdaymap.pop(id)

    def _fetch_birthdays(self, listeners: Dict[int, AulaCalendarCoordinatorMeta[AulaChildProfile]]):
        request_data_profiles = list[AulaChildProfile]()
        new_birthdaymap = dict[int, List[AulaBirthdayEvent]]()
        for (id, meta) in listeners.items():
            if meta.last_updated is None or meta.last_updated < now() - BIRTHDAYS_UPDATE_INTERVAL or meta.last_updated.date() < now().date():
                request_data_profiles.append(meta.keys[0])
            else: #not requesting, reuse cached data
                new_birthdaymap[id] = self._birthdaymap.get(id, list[AulaBirthdayEvent]())

        for profile in request_data_profiles:
            #Batch fetching and then splitting birthdays across profiles is very difficult, so we fetch per institution
            birthdays = self._client.get_birthday_events([profile], now(), now() + SYNC_EVENT_MAX_TIME)
            _LOGGER.debug(f"Fetching birthdays for id: {profile.id}, got {len(birthdays)} birthdays")
            new_birthdaymap[profile.id] = birthdays

        return (new_birthdaymap, [inst.id for inst in request_data_profiles])

    #endregion Birthdays

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
            if meta.last_updated is None or meta.last_updated < now() - EVENTS_UPDATE_INTERVAL or meta.last_updated.date() < now().date():
                request_data_institutions.append(meta.keys[0])
            else: #not requesting, reuse cached data
                new_eventmap[id] = self._eventmap.get(id, list[AulaCalendarEvent]())
        for institution in request_data_institutions:
            #Batch fetching and then splitting events across profiles is very difficult, so we fetch per institution
            events = self._client.get_calendar_events([institution], now(), now() + SYNC_EVENT_MAX_TIME)
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
            if meta.last_updated is None or meta.last_updated < now() - WEEKLY_PLANS_UPDATE_INTERVAL or meta.last_updated.date() < now().date():
                request_data_institutions.append(meta.keys[0])
            else: #not requesting, reuse cached data
                new_weeklyplanmap[id] = self._weeklyplanmap.get(id, list[AulaWeeklyPlan]())

        for institution in request_data_institutions:
            #Batch fetching and then splitting weekly_plans across profiles is very difficult, so we fetch per institution
            weekly_plans = self._client.get_weekly_plans([institution], now(), now() + SYNC_EVENT_MAX_TIME)
            _LOGGER.debug(f"Fetching weekly_plans for id: {institution.id}, got {len(weekly_plans)} weekly_plans")
            new_weeklyplanmap[institution.id] = weekly_plans

        return (new_weeklyplanmap, [inst.id for inst in request_data_institutions])

    #endregion Weekly Plans

    #region EasyIQ Weekly Plans

    async def get_easyiq_weekly_plans_for_interval(self, profiles: List[AulaChildProfile], start_datetime: datetime.datetime, end_datetime: datetime.datetime) -> List[AulaEasyiqWeeklyPlan]:
        return await self.hass.async_add_executor_job(self._client.get_easyiq_weekly_plans, profiles, start_datetime, end_datetime)

    def get_easyiq_weekly_plans(self, profile: AulaChildProfile) -> List[AulaEasyiqWeeklyPlan]:
        key = profile.id
        if key not in self._easyiq_weekplan_listeners:
            raise KeyError(f"Listener not found for the easyiq_weekplan key. Ensure you add the key when component is added to HASS (async_add_easyiq_weekplan_key), and remove when component is removed from HASS (async_remove_easyiq_weekplan_key)")
        return self._easyiqweekplanmap.get(key, [])

    async def async_add_easyiq_weekplan_key(self, profile: AulaChildProfile) -> None:
        id = profile.id
        meta = self._easyiq_weekplan_listeners.setdefault(id, AulaCalendarCoordinatorMeta[AulaChildProfile]())
        _LOGGER.debug(f"async_add_easyiq_weekplan_key {id}")
        meta.keys.append(profile)
        self._easyiqweekplanmap.setdefault(id, [])
        await self.async_refresh()

    async def async_remove_easyiq_weekplan_key(self, profile: AulaChildProfile) -> None:
        id = profile.id
        meta = self._easyiq_weekplan_listeners.get(id)
        if meta is None: return
        meta.keys.remove(profile)
        _LOGGER.debug(f"async_remove_easyiq_weekplan_key {id}")
        if len(meta.keys) == 0:
            self._easyiq_weekplan_listeners.pop(id)
            self._easyiqweekplanmap.pop(id)

    def _fetch_easyiq_weekly_plans(self, listeners: Dict[int, AulaCalendarCoordinatorMeta[AulaChildProfile]]):
        request_data_profiles = list[AulaChildProfile]()
        new_easyiqmap = dict[int, List[AulaEasyiqWeeklyPlan]]()
        for (id, meta) in listeners.items():
            if meta.last_updated is None or meta.last_updated < now() - EASYIQ_WEEKPLAN_UPDATE_INTERVAL or meta.last_updated.date() < now().date():
                request_data_profiles.append(meta.keys[0])
            else:
                new_easyiqmap[id] = self._easyiqweekplanmap.get(id, list[AulaEasyiqWeeklyPlan]())

        for profile in request_data_profiles:
            plans = self._client.get_easyiq_weekly_plans([profile], now(), now() + SYNC_EVENT_MAX_TIME)
            _LOGGER.debug(f"Fetching easyiq weekplans for id: {profile.id}, got {len(plans)} plans")
            new_easyiqmap[profile.id] = plans

        return (new_easyiqmap, [p.id for p in request_data_profiles])

    #endregion EasyIQ Weekly Plans

    #region Newsletters (MinUddannelse)

    async def get_newsletters_for_interval(self, profiles: List[AulaChildProfile], start_datetime: datetime.datetime, end_datetime: datetime.datetime) -> List[AulaWeeklyNewsletter]:
        return await self.hass.async_add_executor_job(self._client.get_newsletters, profiles, start_datetime, end_datetime)

    def get_newsletters(self, profile: AulaChildProfile) -> List[AulaWeeklyNewsletter]:
        key = profile.id
        if key not in self._newsletter_listeners:
            raise KeyError(f"Listener not found for the newsletter key. Ensure you add the key when component is added to HASS (async_add_newsletter_key), and remove when component is removed from HASS (async_remove_newsletter_key)")
        return self._newslettermap.get(key, [])

    async def async_add_newsletter_key(self, profile: AulaChildProfile) -> None:
        id = profile.id
        meta = self._newsletter_listeners.setdefault(id, AulaCalendarCoordinatorMeta[AulaChildProfile]())
        _LOGGER.debug(f"async_add_newsletter_key {id}")
        meta.keys.append(profile)
        self._newslettermap.setdefault(id, [])
        await self.async_refresh()

    async def async_remove_newsletter_key(self, profile: AulaChildProfile) -> None:
        id = profile.id
        meta = self._newsletter_listeners.get(id)
        if meta is None: return
        meta.keys.remove(profile)
        _LOGGER.debug(f"async_remove_newsletter_key {id}")
        if len(meta.keys) == 0:
            self._newsletter_listeners.pop(id)
            self._newslettermap.pop(id)

    def _fetch_newsletters(self, listeners: Dict[int, AulaCalendarCoordinatorMeta[AulaChildProfile]]):
        request_data_profiles = list[AulaChildProfile]()
        new_newslettermap = dict[int, List[AulaWeeklyNewsletter]]()
        for (id, meta) in listeners.items():
            if meta.last_updated is None or meta.last_updated < now() - NEWSLETTER_UPDATE_INTERVAL or meta.last_updated.date() < now().date():
                request_data_profiles.append(meta.keys[0])
            else:
                new_newslettermap[id] = self._newslettermap.get(id, list[AulaWeeklyNewsletter]())

        for profile in request_data_profiles:
            newsletters = self._client.get_newsletters([profile], now(), now() + SYNC_EVENT_MAX_TIME)
            _LOGGER.debug(f"Fetching newsletters for id: {profile.id}, got {len(newsletters)} newsletters")
            new_newslettermap[profile.id] = newsletters

        return (new_newslettermap, [p.id for p in request_data_profiles])

    #endregion Newsletters