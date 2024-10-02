from enum import StrEnum


class AULA_WIDGET_ID(StrEnum):
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


class AULA_CALENDAR_EVENT_TYPE(StrEnum):
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