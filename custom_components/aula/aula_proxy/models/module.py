from .constants import AulaCalendarEventType

from .aula_birthday_parser import AulaBirthdayParser
from .aula_calendar_parser import AulaCalendarParser
from .aula_message_thread_parser import AulaMessageThreadParser
from .aula_notification_parser import AulaNotificationParser
from .aula_profile_parser import AulaProfileParser
from .aula_weekly_plan_parser import AulaWeeklyPlanParser

from .aula_birthday_models import (
    AulaBirthdayEvent,
)
from .aula_calendar_models import (
    AulaCalendarEvent,
    AulaCalendarEventLesson,
    AulaCalendarEventLessonParticipant,
    AulaCalendarEventResource,
    AulaCalendarEventTimeSlot,
    AulaCalendarEventTimeSlotEntry,
    AulaCalendarEventTimeSlotEntryAnswer,
    AulaCalendarEventTimeSlotEntryIndex,
)
from .aula_message_thread_models import (
    AulaMessage,
    AulaMessageText,
    AulaMessageThread,
    AulaThreadRecipient,
    AulaThreadRegardingChild,
)
from .aula_notication_models import(
    AulaNotificationBase,
    AulaAlbumNotification,
    AulaCalendarEventNotification,
    AulaGalleryNotification,
    AulaMessageNotification,
    AulaPostNotification,
    NotificationArea,
    NotificationType,
    NotificationEventType,
    AULA_NOTIFICATION_TYPES,
)
from .aula_profile_models import (
    AulaChildProfile,
    AulaDailyOverview,
    AulaInstitutionProfile,
    AulaLocation,
    AulaLoginData,
    AulaProfile,
    AulaProfilePicture,
    AulaToken,
    AulaWidget,
)
from .aula_weekly_newsletter_models import (
    AulaWeeklyNewsletter,
    AulaWeeklyNewsletters,
)
from .aula_weekly_plan_models import(
    AulaWeeklyPlan,
    AulaDailyPlan,
    AulaDailyPlanTask
)

# Add other imports here as needed

__all__ = [
    #constants
    'AulaCalendarEventType',

    #parsers
    'AulaBirthdayParser',
    'AulaCalendarParser',
    'AulaMessageThreadParser',
    'AulaNotificationParser',
    'AulaProfileParser',
    'AulaWeeklyPlanParser',

    #models
    #birthday
    'AulaBirthdayEvent',
    #calendar
    'AulaCalendarEvent',
    'AulaCalendarEventLesson',
    'AulaCalendarEventLessonParticipant',
    'AulaCalendarEventResource',
    'AulaCalendarEventTimeSlot',
    'AulaCalendarEventTimeSlotEntry',
    'AulaCalendarEventTimeSlotEntryAnswer',
    'AulaCalendarEventTimeSlotEntryIndex',
    #message
    'AulaMessage',
    'AulaMessageText',
    'AulaMessageThread',
    'AulaThreadRecipient',
    'AulaThreadRegardingChild',
    #notification
    'AulaNotificationBase',
    'AulaAlbumNotification',
    'AulaCalendarEventNotification',
    'AulaGalleryNotification',
    'AulaMessageNotification',
    'AulaPostNotification',
    'NotificationArea',
    'NotificationEventType',
    'NotificationType',
    'AULA_NOTIFICATION_TYPES',
    #profile
    'AulaChildProfile',
    'AulaDailyOverview',
    'AulaInstitutionProfile',
    'AulaLocation',
    'AulaLoginData',
    'AulaProfile',
    'AulaProfilePicture',
    'AulaToken',
    'AulaWidget',
    #weekly_newsletter
    'AulaWeeklyNewsletter',
    'AulaWeeklyNewsletters',
    #weekly_plan
    'AulaWeeklyPlan',
    'AulaDailyPlan',
    'AulaDailyPlanTask',
]