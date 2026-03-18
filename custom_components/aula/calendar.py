from datetime import datetime, timedelta, date
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.dt import now
from typing import Any, List
import logging

from .aula_calendar_coordinator import AulaCalendarCoordinator, AulaCalendarCoordinatorData
from .aula_data import get_aula_calendar_coordinator, get_aula_data_coordinator
from .aula_data_coordinator import AulaDataCoordinator
from .aula_proxy.models.constants import (
    AulaCalendarEventType, CALENDAR_EVENT_ICON, WEEKLY_PLAN_TASK_ICON,
    get_label,
)
from .aula_proxy.utils.list_utils import list_without_none
from .aula_proxy.models.module import (
    AulaBirthdayEvent,
    AulaChildProfile,
    AulaEasyiqDailyPlan,
    AulaEasyiqEvent,
    AulaEasyiqWeeklyPlan,
    AulaInstitutionProfile,
    AulaProfile,
    AulaCalendarEvent,
    AulaDailyPlanTask,
    AulaWeeklyPlan,
    AulaDailyPlan,
)

from .entity import AulaCalendarEntityBase

_LOGGER = logging.getLogger(__name__)

def _to_datetime(value: datetime | date, tzinfo: Any) -> datetime:
    """Convert a date or datetime to a datetime with timezone."""
    if type(value) is date:
        return datetime.combine(value, datetime.min.time(), tzinfo)
    return value  # type: ignore[return-value]

def _is_event_in_range(event: CalendarEvent, start: datetime, end: datetime) -> bool:
    """Return True if the event overlaps with the given range."""
    event_start = _to_datetime(event.start, start.tzinfo)
    event_end = _to_datetime(event.end, start.tzinfo)
    return event_start < end and event_end >= start

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the calendar platform."""
    data_coordinator = get_aula_data_coordinator(hass, entry)
    calendar_coordinator = get_aula_calendar_coordinator(hass, entry)
    await calendar_coordinator.async_config_entry_first_refresh()
    entities: List[CalendarEntity] = []
    for child in data_coordinator.data.children:
        entities.append(AulaEventCalendar(calendar_coordinator, data_coordinator, child, child.institution_profile))
    for profile in data_coordinator.data.profiles:
        for institution in profile.institution_profiles:
            entities.append(AulaEventCalendar(calendar_coordinator, data_coordinator, profile, institution))

    if data_coordinator.weekly_plans_supported():
        for child in data_coordinator.data.children:
            entities.append(AulaWeeklyPlanCalendar(calendar_coordinator, data_coordinator, child, child.institution_profile))
            entities.append(AulaBirthdayCalendar(calendar_coordinator, data_coordinator, child, child.institution_profile))

    if data_coordinator.easyiq_weekplan_supported():
        for child in data_coordinator.data.children:
            entities.append(AulaEasyiqWeekplanCalendar(calendar_coordinator, data_coordinator, child, child.institution_profile))

    async_add_entities(entities)

class AulaBirthdayCalendar(AulaCalendarEntityBase, CalendarEntity): # type: ignore
    """A calendar event entity."""
    _event: CalendarEvent | None = None
    _profile: AulaChildProfile
    _institution: AulaInstitutionProfile
    _data_coordinator: AulaDataCoordinator

    def __init__(self, calendar_coordinator: AulaCalendarCoordinator, data_coordinator: AulaDataCoordinator, profile: AulaChildProfile, institution: AulaInstitutionProfile):
        super().__init__(calendar_coordinator, name="birthdays")
        self._data_coordinator = data_coordinator
        self._profile = profile
        first_name = profile.first_name
        institution_name = institution.institution_name
        self._attr_unique_id = f"{self._attr_unique_id}_{first_name}_{institution_name}"
        self._attr_translation_placeholders = { "name": first_name, "institution": institution_name }

    async def async_will_remove_from_hass(self):
        await self.coordinator.async_remove_birthday_key(self._profile)
        return await super().async_will_remove_from_hass()

    async def async_added_to_hass(self):
        await self.coordinator.async_add_birthday_key(self._profile)
        return await super().async_added_to_hass()

    def _handle_data_updated(self, data: AulaCalendarCoordinatorData) -> bool:
        """Handle the update and return True if data has changed for the entity."""
        if self._profile.id in data.updated_birthdays_for_listener_keys:
            return True
        return False

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        result = self._get_active_or_upcoming_event()
        # _LOGGER.debug(f"event = {None if result is None else result.summary}")
        return result

    async def async_get_events(self, hass: HomeAssistant, start_date: datetime, end_date: datetime) -> List[CalendarEvent]:
        """HA Get all events in a specific time frame."""
        birthdays = await self.coordinator.get_birthdays_for_interval([self._profile], start_date, end_date)
        events = list[CalendarEvent]()
        for birthday in birthdays:
            event = self._create_calendar_event(birthday)
            if event and _is_event_in_range(event, start_date, end_date):
                events.append(event)
        return events

    def _get_active_or_upcoming_event(self) -> CalendarEvent | None:
        current_time = now()
        birthdays = self.coordinator.get_birthdays(self._profile)
        for birthday in birthdays:
            if self._get_event_start(birthday) >= current_time.date():
                calendar_event = self._create_calendar_event(birthday)
                return calendar_event
        return None

    def _create_calendar_event(self, event: AulaBirthdayEvent) -> CalendarEvent:
        age = self._get_age(event)
        icon = CALENDAR_EVENT_ICON.get(AulaCalendarEventType.BIRTHDAY, "")
        summary = f"{icon} {event.full_name} ({event.main_group_name}) {get_label('birthday_turns')} {age}"
        description = ""
        start_date = self._get_event_start(event)
        end_date = start_date + timedelta(days=1)

        return CalendarEvent(
            uid=str(event.institution_profile_id),
            summary=summary,
            start=start_date,
            end=end_date,
            description=None if len(description.strip()) == 0 else description,
        )

    def _get_age(self, event: AulaBirthdayEvent) -> int:
        """Return the age of the child."""
        return now().year - event.birthday_date.year

    def _get_event_start(self, event: AulaBirthdayEvent) -> date:
        """Return the start date of the event."""
        return event.birthday_date.replace(year=now().year)

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
        self._profile_is_child = isinstance(self._profile, AulaChildProfile)
        self._institution = institution
        first_name = profile.first_name
        institution_name = institution.institution_name
        self._attr_unique_id = f"{self._attr_unique_id}_{first_name}_{institution_name}"
        self._attr_translation_placeholders = { "name": first_name, "institution": institution_name }

    async def async_will_remove_from_hass(self):
        await self.coordinator.async_remove_event_key(self._institution)
        return await super().async_will_remove_from_hass()

    async def async_added_to_hass(self):
        await self.coordinator.async_add_event_key(self._institution)
        return await super().async_added_to_hass()

    def _handle_data_updated(self, data: AulaCalendarCoordinatorData) -> bool:
        if self._institution.id in data.updated_events_for_listener_keys:
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
            if event.type == AulaCalendarEventType.SCHOOL_HOME_MEETING or event.type == AulaCalendarEventType.PARENTAL_MEETING:
                return len(self._get_required_children(event)) > 0
        return True

    async def async_get_events(self, hass: HomeAssistant, start_date: datetime, end_date: datetime) -> List[CalendarEvent]:
        """Get all events in a specific time frame."""
        # _LOGGER.debug(f"Getting events for profile: {self._profile.name}, interval: {start_date} - {end_date}")
        result_items = await self.coordinator.get_events_for_interval([self._institution], start_date, end_date)
        events = list_without_none(self._create_calendar_event(event) for event in filter(self._event_filter, result_items))
        return [e for e in events if _is_event_in_range(e, start_date, end_date)]

    def _get_active_or_upcoming_event(self) -> CalendarEvent | None:
        current_time = now()
        events = self.coordinator.get_events(self._institution)
        for event in filter(self._event_filter,events):
            if event.end_datetime >= current_time:
                calendar_event = self._create_calendar_event(event)
                if calendar_event is not None and calendar_event.end >= current_time:
                    # _LOGGER.debug(f"Event found key:{self._institution.id}, dict keys: {[f"{key}|{len(evts)}" for (key, evts) in self.coordinator.data.events.items()]})")
                    return calendar_event
        # _LOGGER.debug(f"No present/future events found for the {len(events)} events (key:{self._institution.id}, dict keys: {[f"{key}|{len(evts)}" for (key, evts) in self.coordinator.data.events.items()]})")
        return None

    def _create_calendar_event(self, event: AulaCalendarEvent) -> CalendarEvent|None:
        """Return a CalendarEvent from an API event."""
        icon = CALENDAR_EVENT_ICON.get(event.type, "")
        summary = event.title
        description = ""
        start_datetime = event.start_datetime
        end_datetime = event.end_datetime
        location:str|None = None
        if event.primary_resource is not None:
            location = event.primary_resource.name

        # meetings have timeslots parents book into. The meeting runs over many days, but we only want to display it for the duration booked, once the booking has been done.
        if event.type == AulaCalendarEventType.SCHOOL_HOME_MEETING or event.type == AulaCalendarEventType.PARENTAL_MEETING:
            required_children = self._get_required_children(event)
            id = self._institution.id
            unbooked_meeting = True
            timeslot = event.time_slot
            if timeslot is not None:
                timeslots = timeslot.time_slots
                for slot in timeslots:
                    for answer in slot.answers:
                        if answer.inst_profile_id == id or answer.concerning_profile_id == id:
                            timeslotindexes = slot.time_slot_indexes
                            if len(timeslotindexes) > answer.selected_time_slot_index:
                                timeslotindex = timeslotindexes[answer.selected_time_slot_index]
                                start_datetime = timeslotindex.start_datetime
                                end_datetime = timeslotindex.end_datetime
                                summary = f"{summary} {self._institution.institution_name}"
                                if location is None: location = self._institution.institution_name
                                if required_children: description += f"{get_label('bring_children')} {", ".join(child.name for child in required_children)}"
                                unbooked_meeting = False
                        if not unbooked_meeting: break
                    if not unbooked_meeting: break

                if unbooked_meeting:
                    summary += " <!>"

        if event.lesson is not None and event.lesson.participants:
            initials = ", ".join(
                p.teacher_initials for p in event.lesson.participants if p.teacher_initials
            )
            if initials:
                summary = f"{summary} ({initials})"
            if event.lesson.lesson_status == "substitute":
                summary = f"{summary} - {get_label('substitute')}"
            teachers = ", ".join(
                p.teacher_name for p in event.lesson.participants if p.teacher_name
            )
            if teachers:
                if description:
                    description += "\n"
                description += teachers

        if event.response_status and event.response_status != "accepted":
            label = get_label(f"response_{event.response_status}")
            if description:
                description += "\n"
            description += f"{get_label('status_prefix')}: {label}"

        summary = f"{icon} {summary}" if icon else summary

        return CalendarEvent(
            uid=str(event.id),
            summary=summary,
            start=start_datetime,
            end=end_datetime,
            description=None if len(description.strip()) == 0 else description,
            location=location,
        )

    def _get_required_children(self, event: AulaCalendarEvent) -> List[AulaChildProfile]:
        result = list[AulaChildProfile]()
        if isinstance(self._profile, AulaChildProfile):
            if self._institution.id in event.belongs_to_profiles:
                result.append(self._profile)
        else: #parent profile
            for child in self._profile.children:
                if child.id in event.belongs_to_profiles:
                    result.append(child)
        return result


class AulaWeeklyPlanCalendar(AulaCalendarEntityBase, CalendarEntity): # type: ignore
    """A calendar event entity."""
    _event: CalendarEvent | None = None
    _profile: AulaChildProfile
    _institution: AulaInstitutionProfile
    _data_coordinator: AulaDataCoordinator

    def __init__(self, calendar_coordinator: AulaCalendarCoordinator, data_coordinator: AulaDataCoordinator, profile: AulaChildProfile, institution: AulaInstitutionProfile):
        super().__init__(calendar_coordinator, name="weekly_plan")
        self._data_coordinator = data_coordinator
        self._profile = profile
        first_name = profile.first_name
        institution_name = institution.institution_name
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
        if self._profile.id in data.updated_weekly_plans_for_listener_keys:
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
        # _LOGGER.debug(f"Getting events for profile: {self._profile.name}, interval: {start_date} - {end_date}")
        weekplans = await self.coordinator.get_weekly_plans_for_interval([self._profile], start_date, end_date)
        events = list[CalendarEvent]()
        for weekplan, dayplan, task in self._weekplans_iterable(weekplans):
            event = self._create_calendar_event(weekplan, dayplan, task)
            if event and _is_event_in_range(event, start_date, end_date):
                events.append(event)
        return events

    def _get_active_or_upcoming_event(self) -> CalendarEvent | None:
        current_time = now()
        END_DELTA = timedelta(days=1)
        weekplans = self.coordinator.get_weekly_plans(self._profile)
        for weekplan, dayplan, task in self._weekplans_iterable(weekplans):
            if dayplan.date +  END_DELTA > current_time.date():
                calendar_event = self._create_calendar_event(weekplan, dayplan, task)
                if calendar_event.end > current_time.date():
                    # _LOGGER.debug(f"Event found key:{self._institution.id}, dict keys: {[f"{key}|{len(evts)}" for (key, evts) in self.coordinator.data.events.items()]})")
                    return calendar_event
        # _LOGGER.debug(f"No present/future events found for the {len(events)} events (key:{self._institution.id}, dict keys: {[f"{key}|{len(evts)}" for (key, evts) in self.coordinator.data.events.items()]})")
        return None

    def _weekplans_iterable(self, weekplans: List[AulaWeeklyPlan]):# -> Iterator[(AulaWeeklyPlan, AulaDailyPlan, AulaDailyPlanTask)]:
        for weekplan in weekplans:
            for dailyplan in weekplan.daily_plans:
                if not self._filter_plan(dailyplan): continue
                for task in dailyplan.tasks:
                    if not self._filter_task(task): continue
                    yield weekplan, dailyplan, task

    def _create_calendar_event(self, weekplan: AulaWeeklyPlan, dailyplan: AulaDailyPlan, task: AulaDailyPlanTask) -> CalendarEvent:
        """Return a CalendarEvent from a API weekplan."""
        icon = WEEKLY_PLAN_TASK_ICON.get(task.type, "")
        summary = task.title if task.title else task.content
        if len(summary) > 75: summary = summary[:73] + "..."
        summaryparts = summary.split("\n", 1)
        summary = summaryparts[0]
        if len(summaryparts) > 1: summary += " ..."
        if task.pill:
            summary = f"[{task.pill}] {summary}"
        summary = f"{icon} {summary}" if icon else summary

        description_parts: list[str] = []
        if task.title:
            description_parts.append(task.title)
        description_parts.append(task.content)
        if task.group:
            description_parts.append(task.group)
        if task.author:
            description_parts.append(task.author)
        description = "\n".join(description_parts)

        start_date = dailyplan.date
        end_date = start_date + timedelta(days=1)

        return CalendarEvent(
            uid=str(task.id),
            summary=summary,
            start=start_date,
            end=end_date,
            description=None if len(description.strip()) == 0 else description,
        )


class AulaEasyiqWeekplanCalendar(AulaCalendarEntityBase, CalendarEntity): # type: ignore
    """A calendar entity for EasyIQ weekly plans (widget 0001)."""
    _profile: AulaChildProfile
    _institution: AulaInstitutionProfile
    _data_coordinator: AulaDataCoordinator

    def __init__(self, calendar_coordinator: AulaCalendarCoordinator, data_coordinator: AulaDataCoordinator, profile: AulaChildProfile, institution: AulaInstitutionProfile):
        super().__init__(calendar_coordinator, name="easyiq_weekplan")
        self._data_coordinator = data_coordinator
        self._profile = profile
        first_name = profile.first_name
        institution_name = institution.institution_name
        self._attr_unique_id = f"{self._attr_unique_id}_{first_name}_{institution_name}"
        self._attr_translation_placeholders = { "name": first_name, "institution": institution_name }

    async def async_will_remove_from_hass(self):
        await self.coordinator.async_remove_easyiq_weekplan_key(self._profile)
        return await super().async_will_remove_from_hass()

    async def async_added_to_hass(self):
        await self.coordinator.async_add_easyiq_weekplan_key(self._profile)
        return await super().async_added_to_hass()

    def _handle_data_updated(self, data: AulaCalendarCoordinatorData) -> bool:
        if self._profile.id in data.updated_easyiq_weekplans_for_listener_keys:
            return True
        return False

    @property
    def event(self) -> CalendarEvent | None:
        current_time = now()
        plans = self.coordinator.get_easyiq_weekly_plans(self._profile)
        for plan, dayplan, event in self._plans_iterable(plans):
            event_end = datetime.combine(dayplan.date, event.end_time)
            if event_end >= current_time:
                return self._create_calendar_event(dayplan, event)
        return None

    async def async_get_events(self, hass: HomeAssistant, start_date: datetime, end_date: datetime) -> List[CalendarEvent]:
        plans = await self.coordinator.get_easyiq_weekly_plans_for_interval([self._profile], start_date, end_date)
        events = list[CalendarEvent]()
        for plan, dayplan, event in self._plans_iterable(plans):
            calendar_event = self._create_calendar_event(dayplan, event)
            if _is_event_in_range(calendar_event, start_date, end_date):
                events.append(calendar_event)
        return events

    def _plans_iterable(self, plans: List[AulaEasyiqWeeklyPlan]):
        for plan in plans:
            for dayplan in plan.daily_plans:
                for event in dayplan.events:
                    yield plan, dayplan, event

    def _create_calendar_event(self, dayplan: AulaEasyiqDailyPlan, event: AulaEasyiqEvent) -> CalendarEvent:
        summary = event.title if event.title else event.description
        if len(summary) > 75: summary = summary[:73] + "..."
        summaryparts = summary.split("\n", 1)
        summary = summaryparts[0]
        if len(summaryparts) > 1: summary += " ..."

        description = event.description
        if event.owner_name:
            description = f"{event.owner_name}\n{description}" if description else event.owner_name

        start = datetime.combine(dayplan.date, event.start_time)
        end = datetime.combine(dayplan.date, event.end_time)

        return CalendarEvent(
            uid=str(event.id),
            summary=summary,
            start=start,
            end=end,
            description=None if not description or len(description.strip()) == 0 else description,
        )
