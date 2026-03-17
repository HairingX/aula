# Entities

## Entity Overview

The integration creates the following entities per configured Aula account:

| Type | Entity | Count | Purpose |
|------|--------|-------|---------|
| Sensor | Status | 1 per child | Detailed presence status (0-10) |
| Sensor | Presence | 1 per child | Simple presence (present/not_present/unknown) |
| Sensor | Duration | 1 per child | Minutes present |
| Binary Sensor | Unread Message | 1 per integration | Unread messages |
| Binary Sensor | Unread Gallery | 1 per integration | New photos/videos |
| Binary Sensor | Unread Calendar | 1 per integration | Calendar notifications |
| Binary Sensor | Unread Post | 1 per integration | New posts |
| Binary Sensor | Unread Presence | 1 per integration | Absence/vacation registration |
| Calendar | Events | 1 per child | School calendar |
| Calendar | Weekly Plans | 1 per child | Weekly plans (Meebook) |
| Calendar | Birthdays | 1 per child | Birthdays |

---

## Sensors (3 per child)

### AulaStatusSensor - Detailed Presence Status

**Device Class**: `ENUM`
**Possible states** (0-10):

| Code | Meaning | Icon |
|------|---------|------|
| 0 | Not present | `mdi:map-marker` |
| 1 | Sick | `mdi:hospital-marker` |
| 2 | Reported absent | `mdi:map-marker-remove` |
| 3 | Present | `mdi:map-marker-check` |
| 4 | Field trip | `mdi:map-marker-distance` |
| 5 | Sleeping | `mdi:power-sleep` |
| 6 | Spare time activity | `mdi:map-marker-star` |
| 7 | Present at location | `mdi:map-marker-check` |
| 8 | Checked out | `mdi:map-marker-left` |
| 9-10 | Reserved | `mdi:map-marker-question` |

**State attributes**:
- `check_in_time` - Check-in time
- `check_out_time` - Check-out time
- `check_in_time_expected` - Expected check-in
- `check_out_time_expected` - Expected check-out
- `exit_with` - Who picks up the child
- `institution_name` - School/institution name
- `main_group` - Class/group (e.g., "3A")
- `location_description` - Location description
- `location_name` - Location name
- `location_icon` - Location icon (if available)

**Data source**: `AulaDailyOverview` matched via institution profile ID

---

### AulaPresenceSensor - Simple Presence

**Device Class**: `ENUM`
**Possible states**: `present`, `not_present`, `unknown`

**Mapping from status codes**:
- Status 0, 2, 8 → `not_present`
- Status 3, 4, 5, 6, 7 → `present`
- Status 1, 9, 10 → `unknown`

Has the same attributes as AulaStatusSensor.

---

### AulaPresenceDurationSensor - Presence Duration

**Device Class**: `DURATION`
**Unit**: Minutes
**State Class**: `MEASUREMENT`

**Calculation**:
- If checked in and NOT checked out: `now() - check_in_time` (updates continuously)
- If checked in AND checked out: `check_out_time - check_in_time` (fixed value)
- No check-in: `None`

**State attributes**:
- `check_in_time`
- `check_out_time`
- `main_group`

---

## Binary Sensors (5 per integration)

All binary sensors share the same pattern:
- **ON**: When there are unread notifications of the given type
- **OFF**: No unread notifications
- Data comes from `AulaDataCoordinator.notifications`

### AulaUnreadMessageBinarySensor

**Icon**: `mdi:message-badge` / `mdi:message-badge-outline`

**Prioritization**: Shows the newest non-muted message first. If all are muted, shows the newest muted one.

**State attributes**:
- `total` - Count of unread threads
- `subject` - Subject of newest message
- `text` - Message text (HTML)
- `sender` - Sender name
- `timestamp` - Timestamp
- `sensitive` - Whether the message is sensitive
- `muted` - Whether the thread is muted
- `marked` - Whether the thread is marked
- `recipients` - List of recipients

**Sensitive messages**: If `sensitive=true`, text is replaced with: "This message is sensitive. Please log into Aula to read it."

---

### AulaUnreadCalendarEventBinarySensor

**Icon**: `mdi:calendar-badge` / `mdi:calendar-badge-outline`

**Prioritization**: ALERT notifications shown before BADGE notifications.

**State attributes**:
- `total` - Count
- `title` - Event title
- `alert` - Notification type (alert/badge)
- `all_day` - All-day event
- `start_datetime` - Start time
- `end_datetime` - End time

---

### AulaUnreadPostBinarySensor

**Icon**: `mdi:bulletin-board`

**State attributes**:
- `total` - Count
- `title` - Post title
- `alert` - Notification type

---

### AulaUnreadGalleryBinarySensor

**Icon**: `mdi:image-album`

**Counts**: Includes both `AulaGalleryNotification` and `AulaAlbumNotification`.

**State attributes**:
- `total` - Count of new gallery items

---

### AulaUnreadPresenceBinarySensor

**Icon**: `mdi:calendar-multiselect` / `mdi:calendar-multiselect-outline`

**State attributes**:
- `total` - Count
- `title` - Vacation registration name
- `text` - Message
- `alert` - Notification type
- `start_datetime` - Start date
- `end_datetime` - End date

---

## Calendars (3 per child)

### AulaEventCalendar - School Calendar

**Data source**: `calendar.getEventsByProfileIdsAndResourceIds`

**Features**:
- Shows school events (lessons, excursions, holidays, meetings, etc.)
- Filters meetings based on profile type (child vs. parent)
- Handles parent meetings with timeslots (shows only booked time)
- Unbooked timeslots are marked with " <!" in the title
- Includes location from primary resource

**Event types** (from `AulaCalendarEventType`):
- `EVENT` - General event
- `LESSON` - Lesson
- `HOLIDAY` - Holiday
- `PRESENCE_HOLIDAY` - Presence holiday
- `BIRTHDAY` - Birthday
- `EXCURSION` - Excursion
- `SCHOOL_HOME_MEETING` - School-home meeting
- `PARENTAL_MEETING` - Parental meeting
- `PERFORMANCE_MEETING` - Performance review
- `VACATION_REGISTRATION` - Vacation registration
- `OTHER` - Other

---

### AulaWeeklyPlanCalendar - Weekly Plans

**Data source**: Meebook API (requires widget token)

**Features**:
- Each daily task is displayed as a calendar event
- Task names are truncated to 75 characters with "..."
- Includes state attributes with full week overview

**State attributes** (full week overview):
- `monday` through `sunday` - Tasks for each day of the current week
- `monday_next` through `sunday_next` - Tasks for next week
- Each day contains a list of tasks with title and content

---

### AulaBirthdayCalendar - Birthdays

**Data source**: `calendar.getBirthdayEventsForInstitutions`

**Format**: All-day events with title: `"{Full Name} ({Class}) turns {Age} 🎁"`

Example: "Ida Hansen (3A) turns 9 🎁"

---

## Entity Hierarchy

```
CoordinatorEntity[AulaDataCoordinator]
└── AulaEntityBase[CONTEXT_TYPE]
    ├── AulaStatusSensor
    ├── AulaPresenceSensor
    ├── AulaPresenceDurationSensor
    ├── AulaUnreadMessageBinarySensor
    ├── AulaUnreadGalleryBinarySensor
    ├── AulaUnreadCalendarEventBinarySensor
    ├── AulaUnreadPostBinarySensor
    └── AulaUnreadPresenceBinarySensor

CoordinatorEntity[AulaCalendarCoordinator]
└── AulaCalendarEntityBase
    ├── AulaEventCalendar
    ├── AulaWeeklyPlanCalendar
    └── AulaBirthdayCalendar
```

## Device Info

All entities share device info:
- **Manufacturer**: "Aula"
- **Identifier**: Config entry's entity ID
- **Name**: Config entry's title
