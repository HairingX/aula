
from .aula_proxy.module import (
    AulaCalendarEvent,
    AulaCalendarEventLesson,
    AulaCalendarEventLessonParticipant,
    AulaCalendarEventResource,
    AulaCalendarEventTimeSlot,
    AulaCalendarEventTimeSlotEntry,
    AulaCalendarEventTimeSlotEntryAnswer,
    AulaCalendarEventTimeSlotEntryIndex,
    AulaMessage,
    AulaMessageText,
    AulaMessageThread,
    AulaThreadRecipient,
    AulaThreadRegardingChild,
    AulaChildProfile,
    AulaDailyOverview,
    AulaGroup,
    AulaInstitutionProfile,
    AulaLocation,
    AulaProfile,
    AulaProfileAddress,
    AulaProfilePicture,
    AulaToken,
    AulaWidget,
)

from .aula_client import AulaClient
from .aula_coordinator import AulaCoordinator, AulaCoordinatorData
from .aula_data import AulaHassData, get_aula_client, get_aula_coordinator, get_hass_data, set_hass_data, remove_hass_data

# Add other imports here as needed

__all__ = [
    #models
    'AulaCalendarEvent',
    'AulaCalendarEventLesson',
    'AulaCalendarEventLessonParticipant',
    'AulaCalendarEventResource',
    'AulaCalendarEventTimeSlot',
    'AulaCalendarEventTimeSlotEntry',
    'AulaCalendarEventTimeSlotEntryAnswer',
    'AulaCalendarEventTimeSlotEntryIndex',

    'AulaMessage',
    'AulaMessageText',
    'AulaMessageThread',
    'AulaThreadRecipient',
    'AulaThreadRegardingChild',

    'AulaChildProfile',
    'AulaDailyOverview',
    'AulaGroup',
    'AulaInstitutionProfile',
    'AulaLocation',
    'AulaProfile',
    'AulaProfileAddress',
    'AulaProfilePicture',
    'AulaToken',
    'AulaWidget',

    "AulaClient",
    "AulaCoordinator",
    "AulaCoordinatorData",
    "AulaHassData",
    "get_aula_client",
    "get_aula_coordinator",
    "get_hass_data",
    "set_hass_data",
    "remove_hass_data",
]