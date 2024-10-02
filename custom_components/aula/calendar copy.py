# from datetime import datetime
# from typing import List
# from homeassistant.components.calendar import CalendarEntity,CalendarEvent
# from homeassistant.config_entries import ConfigEntry
# from homeassistant.core import HomeAssistant
# from homeassistant.helpers.entity_platform import AddEntitiesCallback
# from homeassistant.util import Throttle
# import logging

# from .aula_data_coordinator import AulaDataCoordinator
# from .aula_proxy.models.aula_profile_models import AulaChildProfile
# from .entity import AulaEntityBase
# from .aula_data import get_aula_data_coordinator
# from .const import DOMAIN

# _LOGGER = logging.getLogger(__name__)

# async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
#     coordinator = get_aula_data_coordinator(hass, entry)
#     coordinator.data['daily_overviews']

#     entities: List[CalendarEntity] = []
#     for child in coordinator.data['children']:
#         entities.append(AulaCalendar(coordinator, child))
#     async_add_entities(entities)

# class AulaCalendar(AulaEntityBase[AulaChildProfile], CalendarEntity): # type: ignore
#     def __init__(self, coordinator: AulaDataCoordinator, child: AulaChildProfile):
#         super().__init__(coordinator, name="calendar", context=child)
#         name = child["name"].split()[0]
#         institution = child["institution_profile"]["institution_name"]
#         self._attr_unique_id = f"{self._attr_unique_id}_{name}_{institution}"
#         self._attr_translation_placeholders = { "name": name, "institution": institution }
#         self._init_data()

#         # self.data = CalendarData(hass,calendar,childid)
#         # self._cal_data = {}
#         # self._name = "Skoleskema "+name

#     @property
#     def event(self):
#         """Return the next upcoming event."""
#         return self.data.event

#     async def async_get_events(self, hass, start_date, end_date):
#         """Get all events in a specific time frame."""
#         return await self.data.async_get_events(hass, start_date, end_date)

# class CalendarData:
#     def __init__(self,hass,calendar,childid):
#         self.event = None

#         self._hass = hass
#         self._calendar = calendar
#         self._childid = childid

#         self.all_events = []
#         self._client = hass.data[DOMAIN]["client"]

#     def parseCalendarData(self,i=None):
#         import json
#         try:
#             with open('skoleskema.json', 'r') as openfile:
#                 _data = json.load(openfile)
#             data = json.loads(_data)
#         except:
#             _LOGGER.warn("Could not open and parse file skoleskema.json!")
#             return False
#         events = []
#         _LOGGER.debug("Parsing skoleskema.json...")
#         for c in data['data']:
#             if c['type'] == "lesson" and c['belongsToProfiles'][0] == self._childid:
#                 summary = c['title']
#                 start = datetime.strptime(c['startDateTime'],"%Y-%m-%dT%H:%M:%S%z")
#                 end = datetime.strptime(c['endDateTime'],"%Y-%m-%dT%H:%M:%S%z")
#                 vikar = 0
#                 for p in c['lesson']['participants']:
#                     if p['participantRole'] == 'substituteTeacher':
#                         teacher = "VIKAR: "+p['teacherName']
#                         vikar = 1
#                         break
#                 if vikar == 0:
#                     try:
#                         teacher = c['lesson']['participants'][0]['teacherInitials']
#                     except:
#                         try:
#                             _LOGGER.debug("Lesson json dump"+str(c['lesson']))
#                             teacher = c['lesson']['participants'][0]['teacherName']
#                         except:
#                             _LOGGER.debug("Could not find any teacher information for "+summary+" at "+str(start))
#                             teacher = ""
#                 event = CalendarEvent(
#                     summary=summary+", "+teacher,
#                     start = start,
#                     end = end,
#                 )
#                 events.append(event)
#         return events

#     async def async_get_events(self, hass, start_date, end_date):
#         events = self.parseCalendarData()
#         return events