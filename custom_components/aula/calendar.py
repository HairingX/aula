"""Support for Google Calendar Search binary sensors."""

from datetime import datetime, timedelta
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.dt import now
from typing import List
import logging

from .aula_calendar_coordinator import AulaCalendarCoordinator, AulaCalendarCoordinatorData
from .aula_data import get_aula_calendar_coordinator, get_aula_data_coordinator
from .aula_data_coordinator import AulaDataCoordinator
from .aula_proxy.models.constants import AULA_CALENDAR_EVENT_TYPE
from .aula_proxy.utils.list_utils import list_without_none
from .aula_proxy.models.module import (
    AulaChildProfile,
    AulaInstitutionProfile,
    AulaProfile,
    AulaCalendarEvent,
    AulaDailyPlanTask,
    AulaWeeklyPlan,
    AulaDailyPlan,
)

from .entity import AulaCalendarEntityBase

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the calendar platform."""
    data_coordinator = get_aula_data_coordinator(hass, entry)
    calendar_coordinator = get_aula_calendar_coordinator(hass, entry)
    await calendar_coordinator.async_config_entry_first_refresh()
    entities: List[AulaEventCalendar|AulaWeekPlanCalendar] = []
    for child in data_coordinator.data['children']:
        entities.append(AulaEventCalendar(calendar_coordinator, data_coordinator, child, child["institution_profile"]))
    for profile in data_coordinator.data['profiles']:
        for institution in profile["institution_profiles"]:
            entities.append(AulaEventCalendar(calendar_coordinator, data_coordinator, profile, institution))

    for child in data_coordinator.data['children']:
        entities.append(AulaWeekPlanCalendar(calendar_coordinator, data_coordinator, child, child["institution_profile"]))

    # if data_coordinator.data
    async_add_entities(entities)

class AulaEventCalendar(AulaCalendarEntityBase, CalendarEntity): # type: ignore
    """A calendar event entity."""
    _event: CalendarEvent | None = None
    _profile: AulaChildProfile|AulaProfile
    _institution: AulaInstitutionProfile
    _data_coordinator: AulaDataCoordinator

    def __init__(self, calendar_coordinator: AulaCalendarCoordinator, data_coordinator: AulaDataCoordinator, profile: AulaChildProfile|AulaProfile, institution: AulaInstitutionProfile):
        super().__init__(calendar_coordinator, name="events")
        self._data_coordinator = data_coordinator
        self._profile = profile
        self._profile_is_child = "children" not in self._profile
        self._institution = institution
        first_name = profile["first_name"]
        institution_name = institution["institution_name"]
        self._attr_unique_id = f"{self._attr_unique_id}_{first_name}_{institution_name}"
        self._attr_translation_placeholders = { "name": first_name, "institution": institution_name }

    async def async_will_remove_from_hass(self):
        await self.coordinator.async_remove_event_key(self._institution)
        return await super().async_will_remove_from_hass()

    async def async_added_to_hass(self):
        await self.coordinator.async_add_event_key(self._institution)
        return await super().async_added_to_hass()

    def _handle_data_updated(self, data: AulaCalendarCoordinatorData) -> bool:
        if self._institution["id"] in data["updated_events_for_listener_keys"]:
            return True
        return False

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        # (event, _) = self._event_with_offset()
        result = self._get_active_or_upcoming_event()
        # _LOGGER.debug(f"event = {None if result is None else result.summary}")
        return result

    def _event_filter(self, event: AulaCalendarEvent) -> bool:
        """Return True if the event is visible."""
        if self._profile_is_child:
            # following meetings can be without kids, leave them out of the kids calendar
            if event["type"] == AULA_CALENDAR_EVENT_TYPE.SCHOOL_HOME_MEETING or event["type"] == AULA_CALENDAR_EVENT_TYPE.PARENTAL_MEETING:
                return len(self._get_required_children(event)) > 0
        return True

    async def async_get_events(self, hass: HomeAssistant, start_date: datetime, end_date: datetime) -> List[CalendarEvent]:
        """Get all events in a specific time frame."""
        # _LOGGER.debug(f"Getting events for profile: {self._profile["name"]}, interval: {start_date} - {end_date}")
        result_items = await self.coordinator.get_events_for_interval([self._institution], start_date, end_date)
        return list_without_none(self._create_calendar_event(event) for event in filter(self._event_filter, result_items))

    def _get_active_or_upcoming_event(self) -> CalendarEvent | None:
        current_time = now()
        events = self.coordinator.get_events(self._institution)
        for event in filter(self._event_filter,events):
            if event["end_datetime"] >= current_time:
                calendar_event = self._create_calendar_event(event)
                if calendar_event is not None and calendar_event.end >= current_time:
                    # _LOGGER.debug(f"Event found key:{self._institution["id"]}, dict keys: {[f"{key}|{len(evts)}" for (key, evts) in self.coordinator.data['events'].items()]})")
                    return calendar_event
        # _LOGGER.debug(f"No present/future events found for the {len(events)} events (key:{self._institution["id"]}, dict keys: {[f"{key}|{len(evts)}" for (key, evts) in self.coordinator.data['events'].items()]})")
        return None

    def _create_calendar_event(self, event: AulaCalendarEvent) -> CalendarEvent|None:
        """Return a CalendarEvent from an API event."""
        summary = event["title"]
        description = ""
        start_datetime = event["start_datetime"]
        end_datetime = event["end_datetime"]

        location:str|None = None
        if "primary_resource" in event and event["primary_resource"] is not None:
            location = event["primary_resource"]["name"]

        # meetings have timeslots parents book into. The meeting runs over many days, but we only want to display it for the duration booked, once the booking has been done.
        if event["type"] == AULA_CALENDAR_EVENT_TYPE.SCHOOL_HOME_MEETING or event["type"] == AULA_CALENDAR_EVENT_TYPE.PARENTAL_MEETING:
            required_children = self._get_required_children(event)
            id = self._institution["id"]
            unbooked_meeting = True
            timeslot = None if "time_slot" not in event else event["time_slot"]
            if timeslot is not None:
                timeslots = [] if "time_slots" not in timeslot else timeslot["time_slots"]
                for slot in timeslots:
                    for answer in slot["answers"]:
                        if answer["inst_profile_id"] == id or answer["concerning_profile_id"] == id:
                            timeslotindexes = slot["time_slot_indexes"]
                            if len(timeslotindexes) > answer["selected_time_slot_index"]:
                                timeslotindex = timeslotindexes[answer["selected_time_slot_index"]]
                                start_datetime = timeslotindex["start_datetime"]
                                end_datetime = timeslotindex["end_datetime"]
                                summary = f"{summary} {self._institution["institution_name"]}"
                                if location is None: location = self._institution["institution_name"]
                                if required_children: description += f"Medbring {", ".join(child["name"] for child in required_children)}"
                                unbooked_meeting = False
                        if not unbooked_meeting: break
                    if not unbooked_meeting: break

                if unbooked_meeting:
                    summary += " <!>"

        return CalendarEvent(
            uid=str(event["id"]),
            summary=summary,
            start=start_datetime,
            end=end_datetime,
            description=None if len(description.strip()) == 0 else description,
            location=location,
        )

    def _get_required_children(self, event: AulaCalendarEvent) -> List[AulaChildProfile]:
        result = list[AulaChildProfile]()
        if "children" in self._profile: #parent profile
            for child in self._profile["children"]:
                if child["id"] in event["belongs_to_profiles"]:
                    result.append(child)
        else: #child profile
            if self._institution["id"] in event["belongs_to_profiles"]:
                result.append(self._profile)
        return result


class AulaWeekPlanCalendar(AulaCalendarEntityBase, CalendarEntity): # type: ignore
    """A calendar event entity."""
    _event: CalendarEvent | None = None
    _profile: AulaChildProfile
    _institution: AulaInstitutionProfile
    _data_coordinator: AulaDataCoordinator

    def __init__(self, calendar_coordinator: AulaCalendarCoordinator, data_coordinator: AulaDataCoordinator, profile: AulaChildProfile, institution: AulaInstitutionProfile):
        super().__init__(calendar_coordinator, name="weekly_plan")
        self._data_coordinator = data_coordinator
        self._profile = profile
        first_name = profile["first_name"]
        institution_name = institution["institution_name"]
        self._attr_unique_id = f"{self._attr_unique_id}_{first_name}_{institution_name}"
        self._attr_translation_placeholders = { "name": first_name, "institution": institution_name }

    async def async_will_remove_from_hass(self):
        await self.coordinator.async_remove_weekly_plan_key(self._profile)
        return await super().async_will_remove_from_hass()

    async def async_added_to_hass(self):
        await self.coordinator.async_add_weekly_plan_key(self._profile)
        return await super().async_added_to_hass()

    def _handle_data_updated(self, data: AulaCalendarCoordinatorData) -> bool:
        """Handle the update and return True if data has changed for the entity."""
        if self._profile["id"] in data["updated_weekly_plans_for_listener_keys"]:
            return True
        return False

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        result = self._get_active_or_upcoming_event()
        # _LOGGER.debug(f"event = {None if result is None else result.summary}")
        return result

    def _filter_plan(self, dailyplan: AulaDailyPlan) -> bool:
        """Return True if the daily plan is visible."""
        return True

    def _filter_task(self, task: AulaDailyPlanTask) -> bool:
        """Return True if the task is visible."""
        return True

    async def async_get_events(self, hass: HomeAssistant, start_date: datetime, end_date: datetime) -> List[CalendarEvent]:
        """HA Get all events in a specific time frame."""
        # _LOGGER.debug(f"Getting events for profile: {self._profile["name"]}, interval: {start_date} - {end_date}")
        weekplans = await self.coordinator.get_weekly_plans_for_interval([self._profile], start_date, end_date)
        events = list[CalendarEvent]()
        for weekplan, dayplan, task in self._weekplans_iterable(weekplans):
            event = self._create_calendar_event(weekplan, dayplan, task)
            if event: events.append(event)
        return events

    def _get_active_or_upcoming_event(self) -> CalendarEvent | None:
        current_time = now()
        END_DELTA = timedelta(days=1)
        weekplans = self.coordinator.get_weekly_plans(self._profile)
        for weekplan, dayplan, task in self._weekplans_iterable(weekplans):
            if dayplan["date"] +  END_DELTA > current_time.date():
                calendar_event = self._create_calendar_event(weekplan, dayplan, task)
                if calendar_event.end > current_time.date():
                    # _LOGGER.debug(f"Event found key:{self._institution["id"]}, dict keys: {[f"{key}|{len(evts)}" for (key, evts) in self.coordinator.data['events'].items()]})")
                    return calendar_event
        # _LOGGER.debug(f"No present/future events found for the {len(events)} events (key:{self._institution["id"]}, dict keys: {[f"{key}|{len(evts)}" for (key, evts) in self.coordinator.data['events'].items()]})")
        return None

    def _weekplans_iterable(self, weekplans: List[AulaWeeklyPlan]):# -> Iterator[(AulaWeeklyPlan, AulaDailyPlan, AulaDailyPlanTask)]:
        for weekplan in weekplans:
            for dailyplan in weekplan["daily_plans"]:
                if not self._filter_plan(dailyplan): continue
                for task in dailyplan["tasks"]:
                    if not self._filter_task(task): continue
                    yield weekplan, dailyplan, task

    def _create_calendar_event(self, weekplan: AulaWeeklyPlan, dailyplan: AulaDailyPlan, task: AulaDailyPlanTask) -> CalendarEvent:
        """Return a CalendarEvent from a API weekplan."""
        summary = task["content"].split("\n", 1)[0]
        description = task["content"]
        start_date = dailyplan["date"]
        end_date = start_date + timedelta(days=1)

        return CalendarEvent(
            uid=str(task["id"]),
            summary=summary,
            start=start_date,
            end=end_date,
            description=None if len(description.strip()) == 0 else description,
        )