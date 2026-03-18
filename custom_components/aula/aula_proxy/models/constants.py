from enum import StrEnum


class AulaWidgetId(StrEnum):
    EASYIQ_WEEKPLAN = "0001"
    """0001 - Week plan posted on easyiqcloud.dk/api/aula."""
    # MEEBOOK_PARENTS = "0003"
    # """0003 - Books the students/children will work with in the current week."""
    WEEKPLAN_PARENTS = "0004"
    """0004 - Week plan for each student/child."""
    # USEFUL_LINKS = "0013"
    # """0013 - Useful links for the user.."""
    MY_EDUCATION_WEEKLETTER = "0029"
    """0029 - Weekletter posted on minuddannelse.net/aula."""
    MY_EDUCATION_ASSIGNMENTS = "0030"
    """0030 - Assignments posted on minuddannelse.net/aula."""
    # BRAIN_AND_HEART_SCHOOL = "0040"
    # """0040 - Employees can be sent directly to the homepage (via the Aula homepage) or the class list (via the class group in Aula) to Brain&Heart School."""
    # ABSENCE_PARENT_REPORTING = "0047"
    # """0047 - Absence helps you see your children's absences and allows you to report them sick."""
    REMINDERS = "0062"
    """0062 - Reminders posted on systematic-momo.dk/api/aula"""
    # MEEBOOK_OVERVIEW = "0119"
    # """0119 - Notifications from Meebook for parents in Aula. The widget also contains quicklinks for navigation to Meebook from Aula."""


class AulaCalendarEventType(StrEnum):
    EVENT = 'event'
    LESSON = 'lesson'
    HOLIDAY = 'holiday'
    PRESENCE_HOLIDAY = 'presence_holiday'
    BIRTHDAY = 'birthday'
    OTHER = 'other'
    EXCURSION = 'excursion'
    SCHOOL_HOME_MEETING = 'school_home_meeting'
    PARENTAL_MEETING = 'parental_meeting'
    PERFORMANCE_MEETING = 'performance_meeting'
    VACATION_REGISTRATION = 'vacation_registration'


CALENDAR_EVENT_ICON: dict[str, str] = {
    AulaCalendarEventType.BIRTHDAY: "🎁",
    AulaCalendarEventType.LESSON: "",
    AulaCalendarEventType.EVENT: "⭐",
    AulaCalendarEventType.HOLIDAY: "🏖️",
    AulaCalendarEventType.PRESENCE_HOLIDAY: "🏖️",
    AulaCalendarEventType.EXCURSION: "🚌",
    AulaCalendarEventType.SCHOOL_HOME_MEETING: "👥",
    AulaCalendarEventType.PARENTAL_MEETING: "👥",
    AulaCalendarEventType.PERFORMANCE_MEETING: "👥",
    AulaCalendarEventType.VACATION_REGISTRATION: "🏖️",
    AulaCalendarEventType.OTHER: "📌",
}


class AulaWeeklyPlanTaskType(StrEnum):
    TASK = "task"
    COMMENT = "comment"


WEEKLY_PLAN_TASK_ICON: dict[str, str] = {
    AulaWeeklyPlanTaskType.TASK: "🔴",
    AulaWeeklyPlanTaskType.COMMENT: "ℹ️",
}


# --- UI Labels ---
# All user-facing text in one place.
# To add a new language: add a new key to _LABELS and set DEFAULT_LANGUAGE.
# On config flow integration, DEFAULT_LANGUAGE can be replaced by a config entry option.

_language = "da"

_LABELS: dict[str, dict[str, str]] = {
    "da": {
        "substitute": "Vikar",
        "bring_children": "Medbring",
        "status_prefix": "Status",
        "birthday_turns": "fylder",
        "response_waiting": "Afventer svar",
        "response_accepted": "Accepteret",
        "response_declined": "Afvist",
    },
    "en": {
        "substitute": "Substitute",
        "bring_children": "Bring",
        "status_prefix": "Status",
        "birthday_turns": "turns",
        "response_waiting": "Awaiting response",
        "response_accepted": "Accepted",
        "response_declined": "Declined",
    },
}


def set_language(language: str) -> None:
    """Set the UI language. Call from config flow / async_setup_entry."""
    global _language
    _language = language


def get_label(key: str) -> str:
    """Get a UI label for the current language, falling back to key name."""
    return _LABELS.get(_language, _LABELS["da"]).get(key, key)