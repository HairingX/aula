# Data Flow

## High-Level Data Flow

```
                        HOME ASSISTANT
                     ┌──────────────────────────────────────────────┐
                     │                                              │
   ┌─────────┐      │  ┌──────────┐     ┌─────────────────────┐   │
   │ User    │──────┼──│ Config   │────>│ AulaClient          │   │
   │ (HA UI) │      │  │ Flow     │     │ (facade)            │   │
   └─────────┘      │  └──────────┘     └─────────┬───────────┘   │
                     │                             │               │
                     │                    ┌────────┴────────┐      │
                     │                    │                 │      │
                     │              ┌─────┴──────┐  ┌──────┴────┐ │
                     │              │ Data       │  │ Calendar  │ │
                     │              │ Coordinator│  │ Coordinator│ │
                     │              │ (5 min)    │  │ (10 min)  │ │
                     │              └─────┬──────┘  └──────┬────┘ │
                     │                    │                 │      │
                     │              ┌─────┴─────────────────┴────┐ │
                     │              │ AulaProxyClient             │ │
                     │              │ (HTTP, login, parsing)      │ │
                     │              └─────┬──────────────────────┘ │
                     │                    │                         │
                     └────────────────────┼─────────────────────────┘
                                          │ HTTPS
            ┌─────────────────────────────┼──────────────────────┐
            │         EXTERNAL APIs       │                      │
            │  ┌──────────────────────────┴───────────────────┐  │
            │  │ Aula.dk API (v22)                            │  │
            │  │ - profiles.getProfilesByLogin                │  │
            │  │ - presence.getDailyOverview                  │  │
            │  │ - calendar.getEventsByProfileIdsAndResources │  │
            │  │ - calendar.getBirthdayEventsForInstitutions  │  │
            │  │ - messaging.getThreads / getMessagesForThread│  │
            │  │ - notifications.getNotificationsFor...       │  │
            │  │ - aulaToken.getAulaToken                     │  │
            │  └──────────────────────────────────────────────┘  │
            │  ┌─────────────────────┐  ┌──────────────────────┐ │
            │  │ Meebook API         │  │ MinUddannelse API    │ │
            │  │ (weekly plans)      │  │ (plans/assignments)  │ │
            │  └─────────────────────┘  └──────────────────────┘ │
            │  ┌─────────────────────┐  ┌──────────────────────┐ │
            │  │ EasyIQ API          │  │ Systematic API       │ │
            │  │ (weekly plans)      │  │ (reminders)          │ │
            │  └─────────────────────┘  └──────────────────────┘ │
            └────────────────────────────────────────────────────┘
```

## Startup Data Flow

```
1. async_setup_entry() called by HA
   │
   ├── Creates AulaClient(username, password)
   ├── Creates AulaDataCoordinator(entry.title, hass, client)
   ├── Creates AulaCalendarCoordinator(entry.title, hass, client)
   │
   ├── data_coordinator.async_config_entry_first_refresh()
   │   │
   │   ├── _async_setup() → connection_check() → login to Aula
   │   └── _async_update_data() → _fetch_data()
   │       │
   │       ├── client.login() → profiles, widgets, API version
   │       ├── client.get_daily_overviews(profiles) → presence
   │       ├── client.get_message_threads() → messages
   │       └── client.get_notifications(children) → notifications
   │
   ├── set_hass_data(hass, entry, hass_data)  → store in hass.data
   │
   └── async_forward_entry_setups(entry, PLATFORMS)
       │
       ├── sensor.async_setup_entry()
       │   └── Creates 3 sensors per child (status, presence, duration)
       │
       ├── binary_sensor.async_setup_entry()
       │   └── Creates 5 binary sensors (messages, gallery, calendar, posts, presence)
       │
       └── calendar.async_setup_entry()
           └── Creates 3 calendars per child (events, weekly_plans, birthdays)
```

## Polling Data Flow (Ongoing Operation)

### Data Coordinator (Every 5 Minutes)

```
_async_update_data()
│
└── async_add_executor_job(_fetch_data)    ← runs in thread (synchronous HTTP)
    │
    ├── client.login()                     ← reuses session if active
    │   └── Returns: profiles, widgets, api_version
    │
    ├── client.get_daily_overviews(profiles)
    │   └── For each profile's institutions:
    │       GET ?method=presence.getDailyOverview
    │       → Parser → List[AulaDailyOverview]
    │
    ├── client.get_message_threads()
    │   ├── GET ?method=messaging.getThreads&sortOn=date&orderDirection=desc&page=0
    │   └── For each thread with unread messages:
    │       GET ?method=messaging.getMessagesForThread&threadId={id}&page=0
    │       → Parser → List[AulaMessageThread] with AulaMessage objects
    │
    └── client.get_notifications(children)
        └── For each child:
            GET ?method=notifications.getNotificationsForActiveProfile
            → Parser → List[AULA_NOTIFICATION_TYPES]
            (Album, Calendar, Gallery, Message, Post, Presence)
```

### Calendar Coordinator (Every 10 Minutes, with Smart Caching)

```
_async_update_data()
│
└── async_add_executor_job(_fetch_data, listeners...)
    │
    ├── client.login()
    │
    ├── _fetch_birthdays(listeners)
    │   │ Check: last_updated > 1 day or new date?
    │   │ → No: Reuse cached data
    │   │ → Yes:
    │   └── client.get_birthday_events(profiles, now, now+2 weeks)
    │       GET ?method=calendar.getBirthdayEventsForInstitutions
    │       → Parser → List[AulaBirthdayEvent]
    │
    ├── _fetch_events(listeners)
    │   │ Check: last_updated > 6 hours or new date?
    │   │ → No: Reuse cached data
    │   │ → Yes:
    │   └── client.get_calendar_events(institutions, now, now+2 weeks)
    │       GET ?method=calendar.getEventsByProfileIdsAndResourceIds
    │       → Parser → List[AulaCalendarEvent]
    │
    └── _fetch_weekly_plans(listeners)
        │ Check: last_updated > 6 hours or new date?
        │ → No: Reuse cached data
        │ → Yes:
        └── client.get_weekly_plans(profiles, now, now+2 weeks)
            GET Meebook API with widget token
            → Parser → List[AulaWeeklyPlan]
```

## Data Transformation

### From API JSON to HA Entity State

```
Example: Presence status for a child

API Response (JSON):
{
  "data": {
    "dailyOverviews": [{
      "status": 3,
      "checkInTime": "07:45",
      "checkOutTime": null,
      "exitWith": "Mom",
      "institutionProfile": { "id": 12345 }
    }]
  }
}
        │
        │ AulaDailyOverviewParser.parse()
        v
AulaDailyOverview(
    status=3,
    check_in_time=time(7, 45),
    check_out_time=None,
    exit_with="Mom",
    institution_profile_id=12345
)
        │
        │ AulaDataCoordinator → AulaDataCoordinatorData
        v
AulaDataCoordinatorData(
    daily_overviews=[AulaDailyOverview(...)],
    children=[AulaChildProfile(...)],
    ...
)
        │
        │ AulaStatusSensor.native_value (matches child to daily_overview)
        v
HA Sensor Entity:
  state: "3"  (enum: "Present")
  attributes:
    check_in_time: "07:45"
    check_out_time: null
    exit_with: "Mom"
    institution_name: "City School"
    main_group: "3A"
```

## Async vs. Synchronous

All HTTP communication is **synchronous** (uses the `requests` library, not `aiohttp`). To avoid blocking Home Assistant's event loop, all API calls run via:

```python
await self.hass.async_add_executor_job(self._fetch_data)
```

This runs the synchronous code in an executor thread, keeping HA's async event loop free.

## Timeout

Both coordinators have a **10-second timeout** on the entire update operation:

```python
async with async_timeout.timeout(10):
    data = await self.hass.async_add_executor_job(self._fetch_data)
```

If API calls take longer than 10 seconds, `asyncio.TimeoutError` is raised, which the coordinator handles automatically.
