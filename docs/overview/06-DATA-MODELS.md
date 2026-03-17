# Data Models

## Overview

All data models live in `custom_components/aula/aula_proxy/models/` and follow a consistent pattern:
- **Models** (`aula_*_models.py`): Python `@dataclass` classes representing data structures
- **Parsers** (`aula_*_parser.py`): Static methods that convert raw API JSON into model instances

## Model-Parser Pairs

| Model File | Parser File | Purpose |
|------------|-------------|---------|
| `aula_profile_models.py` | `aula_profile_parser.py` | Profiles, children, institutions, daily overviews |
| `aula_calendar_models.py` | `aula_calendar_parser.py` | Calendar events, timeslots, lessons, resources |
| `aula_message_thread_models.py` | `aula_message_thread_parser.py` | Message threads, messages, recipients |
| `aula_notication_models.py` | `aula_notification_parser.py` | All notification types |
| `aula_weekly_plan_models.py` | `aula_weekly_plan_parser.py` | Weekly plans, daily plans, tasks |
| `aula_birthday_models.py` | `aula_birthday_parser.py` | Birthday events |

---

## Profile Models (`aula_profile_models.py`)

### Hierarchy

```
AulaLoginData
├── profiles: List[AulaProfile]
├── widgets: List[AulaWidget]
└── api_version: int

AulaProfile (parent/guardian)
├── id: int
├── institution_profiles: List[AulaInstitutionProfile]
├── children: List[AulaChildProfile]
├── user_id: str (set after login from getProfileContext)
└── profile_picture: Optional[AulaProfilePicture]

AulaChildProfile
├── id: int
├── name: str
├── institution_profile: AulaInstitutionProfile
├── institution_code: str
├── user_id: str (set after login from getProfileContext)
├── main_group: Optional[AulaInstitutionGroup] (set from getProfileMasterData)
└── profile_picture: Optional[AulaProfilePicture]

AulaInstitutionProfile
├── id: int
├── institution_code: str
└── institution_name: str

AulaInstitutionGroup
├── id: int
└── name: str (e.g., "3A")
```

### Supporting Models

```
AulaToken
├── token: str (bearer token)
└── timestamp: datetime (when token was acquired)

AulaWidget
├── id: int
└── widget_id: str (e.g., "0004")

AulaProfilePicture
├── id: int
└── url: str

AulaDailyOverview
├── status: int (0-10)
├── check_in_time: Optional[time]
├── check_out_time: Optional[time]
├── check_in_time_expected: Optional[time]
├── check_out_time_expected: Optional[time]
├── exit_with: Optional[str]
├── institution_profile_id: int
└── location: Optional[AulaLocation]

AulaLocation
├── id: int
├── name: str
├── description: Optional[str]
└── icon: Optional[str]
```

---

## Calendar Models (`aula_calendar_models.py`)

```
AulaCalendarEvent
├── id: int
├── title: str
├── description: Optional[str]
├── type: AulaCalendarEventType (enum)
├── start_datetime: datetime
├── end_datetime: datetime
├── all_day: bool
├── is_private: bool
├── institution_code: str
├── institution_name: str
├── primary_resource: Optional[AulaCalendarEventResource]
├── resources: List[AulaCalendarEventResource]
├── time_slots: List[AulaCalendarEventTimeSlot]
├── lesson: Optional[AulaCalendarEventLesson]
├── required_profiles: List[int] (institution profile IDs)
├── response_required: bool
├── response_deadline: Optional[datetime]
└── is_cancelled: bool

AulaCalendarEventTimeSlot
├── id: int
├── start_datetime: datetime
├── end_datetime: datetime
├── is_booked: bool
└── booked_by_profile_id: Optional[int]

AulaCalendarEventLesson
├── subject: str
├── participants: List[str] (teacher names)
└── note: Optional[str]

AulaCalendarEventResource
├── id: int
├── name: str
└── type: str
```

### Calendar Event Types (enum)

```python
class AulaCalendarEventType(str, Enum):
    EVENT = "event"
    LESSON = "lesson"
    HOLIDAY = "holiday"
    PRESENCE_HOLIDAY = "presence_holiday"
    BIRTHDAY = "birthday"
    EXCURSION = "excursion"
    SCHOOL_HOME_MEETING = "school_home_meeting"
    PARENTAL_MEETING = "parental_meeting"
    PERFORMANCE_MEETING = "performance_meeting"
    VACATION_REGISTRATION = "vacation_registration"
    OTHER = "other"
```

---

## Message Models (`aula_message_thread_models.py`)

```
AulaMessageThread
├── id: int
├── subject: str
├── last_message_date: datetime
├── is_read: bool
├── is_muted: bool
├── is_marked: bool
├── is_sensitive: bool
├── recipients: List[AulaThreadRecipient]
└── messages: List[AulaMessage] (populated on demand)

AulaMessage
├── id: int
├── sender_name: str
├── send_datetime: datetime
├── text: AulaMessageText
└── has_attachments: bool

AulaMessageText
├── html: str
└── text: str (plain text extraction)

AulaThreadRecipient
├── id: int
├── name: str
└── role: str
```

---

## Notification Models (`aula_notication_models.py`)

All notifications share a base class:

```
AulaNotificationBase
├── id: int
├── notification_type: str ("ALERT" or "BADGE")
├── notification_area: str ("CALENDAR", "GALLERY", "MESSAGES", "POSTS", "PRESENCE", "ALBUM")
└── is_read: bool
```

### Specialized Notification Types

```
AulaCalendarEventNotification (extends AulaNotificationBase)
├── event_title: str
├── all_day: bool
├── start_datetime: Optional[datetime]
└── end_datetime: Optional[datetime]

AulaGalleryNotification (extends AulaNotificationBase)
└── (no additional fields)

AulaAlbumNotification (extends AulaNotificationBase)
└── (no additional fields)

AulaMessageNotification (extends AulaNotificationBase)
└── (no additional fields)

AulaPostNotification (extends AulaNotificationBase)
├── title: str
└── (alert type)

AulaPresenceNotification (extends AulaNotificationBase)
├── vacation_request_name: str
├── message_text: Optional[str]
├── start_datetime: Optional[datetime]
└── end_datetime: Optional[datetime]
```

### Union Type

```python
AULA_NOTIFICATION_TYPES = Union[
    AulaAlbumNotification,
    AulaCalendarEventNotification,
    AulaGalleryNotification,
    AulaMessageNotification,
    AulaPostNotification,
    AulaPresenceNotification,
]
```

---

## Weekly Plan Models (`aula_weekly_plan_models.py`)

```
AulaWeeklyPlan
├── id: int
├── week_number: int
├── year: int
├── title: str
└── daily_plans: List[AulaDailyPlan]

AulaDailyPlan
├── date: date
├── day_of_week: int (0=Monday)
└── tasks: List[AulaDailyPlanTask]

AulaDailyPlanTask
├── id: int
├── title: str
├── content: str (HTML)
├── type: str
└── author: Optional[str]
```

---

## Birthday Models (`aula_birthday_models.py`)

```
AulaBirthdayEvent
├── id: int
├── first_name: str
├── last_name: str
├── birthday_date: date
├── age: int (calculated age at birthday)
├── institution_code: str
└── main_group_name: Optional[str] (e.g., "3A")
```

---

## Coordinator Data Models

These dataclasses are used by coordinators to pass data to entities:

```
AulaDataCoordinatorData (from aula_data_coordinator.py)
├── device_id: str
├── aula_version: int
├── profiles: List[AulaProfile]
├── children: List[AulaChildProfile]
├── daily_overviews: List[AulaDailyOverview]
├── message_threads: List[AulaMessageThread]
└── notifications: List[AULA_NOTIFICATION_TYPES]

AulaCalendarCoordinatorData (from aula_calendar_coordinator.py)
├── updated_birthdays_for_listener_keys: List[int]
├── updated_events_for_listener_keys: List[int]
└── updated_weekly_plans_for_listener_keys: List[int]
```

---

## Parser Pattern

All parsers follow the same pattern - static methods that take raw JSON dictionaries and return typed dataclass instances:

```python
class AulaProfileParser:
    @staticmethod
    def parse_profiles_response(response: AulaGetProfilesByLoginResponse) -> List[AulaProfile]:
        # Extract from response["data"]["profiles"]
        # Map JSON fields to dataclass constructor
        # Handle optional/nullable fields
        # Return list of typed objects

    @staticmethod
    def parse_widgets(widgets_data: List[dict]) -> List[AulaWidget]:
        ...
```

### Response Types

Each API endpoint has a corresponding TypedDict in `aula_proxy/responses/`:
- `AulaGetProfilesByLoginResponse`
- `AulaGetProfileContextResponse`
- `AulaGetProfileMasterDataResponse`
- `AulaGetDailyOverviewResponse`
- `AulaGetEventsByProfileIdsAndResourceIdsResponse`
- `AulaGetBirthdayEventsForInstitutionsResponse`
- `AulaGetMessageThreadsResponse`
- `AulaGetMessagesForThreadResponse`
- `AulaGetNotificationsResponse`
- `AulaGetWeeklyPlansResponse`

These TypedDicts provide type hints for the raw JSON structure returned by each API endpoint.
