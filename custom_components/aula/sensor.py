from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor.const import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.dt import now
from typing import Any, List, TypedDict
import datetime
import logging

from .entity import AulaEntityBase
from .aula_data_coordinator import AulaDataCoordinator, AulaDataCoordinatorData
from .aula_data import get_aula_data_coordinator
from .aula_proxy.models.aula_profile_models import AulaChildProfile, AulaDailyOverview

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Setup sensors from a config entry created in the integrations UI."""
    coordinator = get_aula_data_coordinator(hass, entry)
    entities: List[SensorEntity] = []
    children = coordinator.data["children"]
    for child in children:
        entities.append(AulaStatusSensor(coordinator, child))
        entities.append(AulaPresenceSensor(coordinator, child))
        entities.append(AulaPresenceDurationSensor(coordinator, child))
    async_add_entities(entities)

class AulaStatusSensor(AulaEntityBase[AulaChildProfile], SensorEntity): # type: ignore
    _attr_device_class = SensorDeviceClass.ENUM

    def __init__(self, coordinator: AulaDataCoordinator, child: AulaChildProfile) -> None:
        super().__init__(coordinator, context=child, name="status")
        self._attr_options = [str(val) for val in StateMetaParser.state_options]
        first_name = child["first_name"]
        institution_name = child["institution_profile"]["institution_name"]
        self._attr_unique_id = f"{self._attr_unique_id}_{first_name}_{institution_name}"
        self._attr_translation_placeholders = { "name": first_name, "institution": institution_name }
        self._init_data()

    def _set_values(self, data: AulaDataCoordinatorData, context: AulaChildProfile) -> None:
         # self._attr_translation_placeholders = self.coordinator.data[""]["state"]
        attributes = dict[str, Any]()
        daily_overview: AulaDailyOverview | None = None
        for item in data["daily_overviews"]:
            if item["institution_profile"]["id"] == context["id"]:
                daily_overview = item

        self._attr_icon = "mdi:map-marker-off"
        self._attr_available = daily_overview is not None
        attributes["check_in_time"] = None
        attributes["check_out_time"] = None
        attributes["check_in_time_expected"] = None
        attributes["check_out_time_expected"] = None
        attributes["exit_with"] = None
        attributes["institution_name"] = None
        attributes["location_description"] = None
        attributes["location_icon"] = None
        attributes["location_name"] = None

        if daily_overview is not None:
            self._attr_native_value = str(daily_overview["status"])
            statemeta = StateMetaParser.parse_presence(daily_overview["status"])
            self._attr_icon = statemeta["icon"]
            if "check_in_time" in daily_overview: attributes["check_in_time"] = daily_overview["check_in_time"]
            if "check_out_time" in daily_overview: attributes["check_out_time"] = daily_overview["check_out_time"]
            if "check_in_time_expected" in daily_overview: attributes["check_in_time_expected"] = daily_overview["check_in_time_expected"]
            if "check_out_time_expected" in daily_overview: attributes["check_out_time_expected"] = daily_overview["check_out_time_expected"]
            if "exit_with" in daily_overview: attributes["exit_with"] = daily_overview["exit_with"]
            if "institution_profile" in daily_overview: attributes["institution_name"] = daily_overview["institution_profile"]["institution_name"]
            if "location" in daily_overview and daily_overview["location"] is not None:
                attributes["location_description"] = daily_overview["location"]["description"]
                attributes["location_name"] = daily_overview["location"]["name"]
                if "icon" in daily_overview["location"]: attributes["location_icon"] = daily_overview["location"]["icon"]
        self._attr_extra_state_attributes = attributes

class AulaPresenceSensor(AulaEntityBase[AulaChildProfile], SensorEntity): # type: ignore
    _attr_device_class = SensorDeviceClass.ENUM

    def __init__(self, coordinator: AulaDataCoordinator, child: AulaChildProfile) -> None:
        super().__init__(coordinator, context=child, name="presence")
        self._attr_options = [str(val) for val in StateMetaParser.precense_options]
        first_name = child["first_name"]
        institution_name = child["institution_profile"]["institution_name"]
        self._attr_unique_id = f"{self._attr_unique_id}_{first_name}_{institution_name}"
        self._attr_translation_placeholders = { "name": first_name, "institution": institution_name }
        self._init_data()

    def _set_values(self, data: AulaDataCoordinatorData, context: AulaChildProfile) -> None:
         # self._attr_translation_placeholders = self.coordinator.data[""]["state"]
        attributes = dict[str, Any]()
        daily_overview: AulaDailyOverview | None = None
        for item in data["daily_overviews"]:
            if item["institution_profile"]["id"] == context["id"]:
                daily_overview = item

        self._attr_icon = "mdi:map-marker-off"
        self._attr_available = daily_overview is not None
        attributes["check_in_time"] = None
        attributes["check_out_time"] = None
        attributes["check_in_time_expected"] = None
        attributes["check_out_time_expected"] = None
        attributes["exit_with"] = None
        attributes["institution_name"] = None

        if daily_overview is not None:
            statemeta = StateMetaParser.parse_presence(daily_overview["status"])
            self._attr_native_value = statemeta["presence"]
            self._attr_icon = statemeta["icon"]
            if "check_in_time" in daily_overview: attributes["check_in_time"] = daily_overview["check_in_time"]
            if "check_out_time" in daily_overview: attributes["check_out_time"] = daily_overview["check_out_time"]
            if "check_in_time_expected" in daily_overview: attributes["check_in_time_expected"] = daily_overview["check_in_time_expected"]
            if "check_out_time_expected" in daily_overview: attributes["check_out_time_expected"] = daily_overview["check_out_time_expected"]
            if "exit_with" in daily_overview: attributes["exit_with"] = daily_overview["exit_with"]
            if "institution_profile" in daily_overview: attributes["institution_name"] = daily_overview["institution_profile"]["institution_name"]
        self._attr_extra_state_attributes = attributes

class AulaPresenceDurationSensor(AulaEntityBase[AulaChildProfile], SensorEntity): # type: ignore
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES

    def __init__(self, coordinator: AulaDataCoordinator, child: AulaChildProfile) -> None:
        super().__init__(coordinator, name="presence_duration", context=child)
        first_name = child["first_name"]
        institution_name = child["institution_profile"]["institution_name"]
        self._attr_unique_id = f"{self._attr_unique_id}_{first_name}_{institution_name}"
        self._attr_translation_placeholders = { "name": first_name, "institution": institution_name }
        self._init_data()

    def _set_values(self, data: AulaDataCoordinatorData, context: AulaChildProfile) -> None:
         # self._attr_translation_placeholders = self.coordinator.data[""]["state"]
        attributes = dict[str, Any]()
        daily_overview: AulaDailyOverview | None = None
        for item in data["daily_overviews"]:
            if item["institution_profile"]["id"] == context["id"]:
                daily_overview = item

        self._attr_icon = "mdi:timer"
        self._attr_available = daily_overview is not None
        attributes["check_in_time"] = None
        attributes["check_out_time"] = None

        if daily_overview is not None:
            statemeta = StateMetaParser.parse_presencetimer(daily_overview["status"])
            self._attr_icon = statemeta["icon"]
            intime: datetime.time|None = None
            outtime: datetime.time|None = None

            if "check_in_time" in daily_overview:
                attributes["check_in_time"] = daily_overview["check_in_time"]
                intime = daily_overview["check_in_time"]
            if "check_out_time" in daily_overview:
                attributes["check_out_time"] = daily_overview["check_out_time"]
                outtime = daily_overview["check_out_time"]

            timervalue = 0
            nowtime:datetime.time|None = None
            if intime is not None:
                if outtime is None:
                    nowtime = now().time()
                    if intime > nowtime:
                        outtime = intime
                    else:
                        outtime = nowtime

                indatetime = datetime.datetime.today() + datetime.timedelta(hours=intime.hour, minutes=intime.minute, seconds=intime.second)
                outdatetime = datetime.datetime.today() + datetime.timedelta(hours=outtime.hour, minutes=outtime.minute, seconds=outtime.second)

                timervalue = (outdatetime - indatetime).total_seconds() / 60
                timervalue = round(timervalue, 0)

            _LOGGER.debug(f"Presence duration calculated: {timervalue} (check_in_time={intime}, check_out_time={outtime}{"" if nowtime is None else f"(calculated from current time: '{nowtime}')"})")

            self._attr_native_value = timervalue
        self._attr_extra_state_attributes = attributes

class StateMeta(TypedDict):
    presence: str|None
    icon: str

class StateFlag:
    NOT_PRESENT = 0
    SICK = 1
    REPORTED_ABSCENT = 2
    PRESENT = 3
    FIELD_TRIP = 4
    SLEEPING = 5
    SPARE_TIME_ACTIVITY = 6
    PRESENT_AT_LOCATION = 7
    CHECKED_OUT = 8
    RESERVED_1 = 9
    RESERVED_2 = 10

class PresenceFlag:
    NOT_PRESENT = "not_present"
    PRESENT = "present"
    UNKNOWN = "unknown"

class StateMetaParser:
    state_options: List[int] = [
        StateFlag.NOT_PRESENT,
        StateFlag.SICK,
        StateFlag.REPORTED_ABSCENT,
        StateFlag.PRESENT,
        StateFlag.FIELD_TRIP,
        StateFlag.SLEEPING,
        StateFlag.SPARE_TIME_ACTIVITY,
        StateFlag.PRESENT_AT_LOCATION,
        StateFlag.CHECKED_OUT,
        StateFlag.RESERVED_1,
        StateFlag.RESERVED_2,
    ]

    precense_options: List[str] = [
        PresenceFlag.NOT_PRESENT,
        PresenceFlag.PRESENT,
        PresenceFlag.UNKNOWN,
    ]

    @staticmethod
    def parse_presence(status: int|None) -> StateMeta:
        match status:
            case StateFlag.NOT_PRESENT:
                return { "presence": PresenceFlag.NOT_PRESENT, "icon": "mdi:map-marker-question" }
            case StateFlag.SICK | StateFlag.REPORTED_ABSCENT:
                return { "presence": PresenceFlag.PRESENT, "icon": "mdi:hospital-marker" }
            case StateFlag.SPARE_TIME_ACTIVITY | StateFlag.CHECKED_OUT:
                return { "presence": PresenceFlag.NOT_PRESENT, "icon": "mdi:map-marker-check" }
            case StateFlag.PRESENT | StateFlag.FIELD_TRIP | StateFlag.SLEEPING | StateFlag.PRESENT_AT_LOCATION:
                return { "presence": PresenceFlag.PRESENT, "icon": "mdi:map-marker" }
            case _:
                return { "presence": PresenceFlag.UNKNOWN, "icon": "mdi:map-marker-off" }

    @staticmethod
    def parse_presencetimer(status: int|None) -> StateMeta:
        match status:
            case StateFlag.NOT_PRESENT:
                return { "presence": None, "icon": "mdi:timer" }
            case StateFlag.SICK | StateFlag.REPORTED_ABSCENT:
                return { "presence": None, "icon": "mdi:timer-remove" }
            case StateFlag.SPARE_TIME_ACTIVITY | StateFlag.CHECKED_OUT:
                return { "presence": None, "icon": "mdi:timer-check" }
            case StateFlag.PRESENT | StateFlag.FIELD_TRIP | StateFlag.SLEEPING | StateFlag.PRESENT_AT_LOCATION:
                return { "presence": None, "icon": "mdi:timer-play" }
            case _:
                return { "presence": None, "icon": "mdi:timer-alert" }
