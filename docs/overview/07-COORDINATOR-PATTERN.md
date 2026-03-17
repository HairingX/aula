# Coordinator Pattern

## Overview

The integration uses Home Assistant's **DataUpdateCoordinator** pattern, which is the recommended approach for cloud-polling integrations. Two coordinators handle different data domains with different update frequencies.

## Why Two Coordinators?

| Concern | AulaDataCoordinator | AulaCalendarCoordinator |
|---------|--------------------|-----------------------|
| **Data** | Profiles, presence, messages, notifications | Calendar events, birthdays, weekly plans |
| **Poll interval** | 5 minutes | 10 minutes |
| **Data volatility** | High (presence changes frequently) | Low (events change rarely) |
| **Smart caching** | No (always fetches all data) | Yes (per-type intervals) |
| **Listeners** | None (always fetches everything) | Per-entity listener registration |

## AulaDataCoordinator

### Lifecycle

```
1. __init__(device_id, hass, client)
   └── Sets up coordinator with 5-minute interval

2. _async_setup()  (called once during first refresh)
   └── Runs connection_check() to validate login

3. _async_update_data()  (called every 5 minutes)
   └── async_add_executor_job(_fetch_data)
       ├── client.login()          → profiles, widgets
       ├── client.get_daily_overviews()  → presence data
       ├── client.get_message_threads()  → messages
       └── client.get_notifications()    → notifications
       └── Returns: AulaDataCoordinatorData
```

### Error Handling

```python
try:
    data = await self.hass.async_add_executor_job(self._fetch_data)
except AulaCredentialError:
    raise ConfigEntryAuthFailed  # → triggers re-auth flow, stops future updates
except Exception:
    raise UpdateFailed  # → coordinator retries on next interval
```

### Widget Support Detection

The coordinator exposes methods to check which features are available:

```python
coordinator.weekly_plans_supported()      # Widget 0004
coordinator.easyiq_weekplan_supported()   # Widget 0001
coordinator.reminders_supported()         # Widget 0062
coordinator.weekletters_supported()       # Widget 0029
coordinator.assignments_supported()       # Widget 0030
```

---

## AulaCalendarCoordinator

### Smart Caching Strategy

The calendar coordinator implements a sophisticated caching system that avoids unnecessary API calls:

```
For each data type (birthdays, events, weekly plans):
│
├── Has this data type been fetched before?
│   └── No → Fetch immediately
│
├── Has the type-specific interval elapsed?
│   ├── Birthdays: > 1 day
│   ├── Events: > 6 hours
│   └── Weekly plans: > 6 hours
│   └── If yes → Fetch new data
│
├── Has the date changed since last fetch?
│   └── If yes → Fetch new data (ensures midnight refresh)
│
└── Otherwise → Reuse cached data
```

### Listener Registration Pattern

Calendar entities must register themselves as listeners before they can receive data:

```
Entity added to HA:
    └── async_add_birthday_key(profile)    ← registers interest
        └── Triggers immediate refresh

Entity removed from HA:
    └── async_remove_birthday_key(profile) ← unregisters
        └── Cleans up cached data
```

This ensures:
- Data is only fetched for entities that actually exist
- Removing an entity stops fetching its data
- Adding an entity triggers an immediate data fetch

### Data Maps

The coordinator maintains internal maps keyed by profile/institution ID:

```python
_birthdaymap: dict[int, List[AulaBirthdayEvent]]    # key = child profile ID
_eventmap: dict[int, List[AulaCalendarEvent]]        # key = institution profile ID
_weeklyplanmap: dict[int, List[AulaWeeklyPlan]]      # key = child profile ID
```

### Listener Metadata

Each listener tracks its subscribed keys and last update time:

```python
class AulaCalendarCoordinatorMeta[T]:
    keys: List[T]                          # profiles subscribed
    last_updated: datetime | None = None   # when data was last fetched
```

### Update Flow

```
_fetch_data(birthday_listeners, event_listeners, weekplan_listeners)
│
├── client.login()  (reuse session if possible)
│
├── _fetch_birthdays(birthday_listeners)
│   ├── For each listener:
│   │   ├── Should update? → Fetch from API
│   │   └── Not yet → Copy from existing _birthdaymap
│   └── Return (new_birthdaymap, updated_keys)
│
├── _fetch_events(event_listeners)
│   ├── For each listener:
│   │   ├── Should update? → Fetch from API
│   │   └── Not yet → Copy from existing _eventmap
│   └── Return (new_eventmap, updated_keys)
│
├── _fetch_weekly_plans(weekplan_listeners)
│   ├── For each listener:
│   │   ├── Should update? → Fetch from API
│   │   └── Not yet → Copy from existing _weeklyplanmap
│   └── Return (new_weeklyplanmap, updated_keys)
│
└── Return AulaCalendarCoordinatorData(
        updated_birthdays_for_listener_keys,
        updated_events_for_listener_keys,
        updated_weekly_plans_for_listener_keys
    )
```

### Selective Entity Updates

Calendar entities use `_handle_data_updated()` to only process updates when their specific data has changed:

```python
# In AulaCalendarEntityBase:
def _handle_data_updated(self) -> None:
    data = self.coordinator.data
    if self._listener_key in data.updated_events_for_listener_keys:
        self._process_new_data()  # Only runs when this entity's data was refreshed
```

---

## Coordinator ↔ Entity Communication

```
┌─────────────────────────┐
│    Coordinator          │
│                         │
│  _async_update_data()   │
│        │                │
│        v                │
│  self.async_set_updated │──────────────────┐
│  _data(data)            │                  │
└─────────────────────────┘                  │
                                             │ notifies all subscribers
                              ┌──────────────┼──────────────┐
                              │              │              │
                              v              v              v
                        ┌──────────┐  ┌──────────┐  ┌──────────┐
                        │ Entity 1 │  │ Entity 2 │  │ Entity 3 │
                        │          │  │          │  │          │
                        │ _handle_ │  │ _handle_ │  │ _handle_ │
                        │ coord.   │  │ coord.   │  │ coord.   │
                        │ _update()│  │ _update()│  │ _update()│
                        └──────────┘  └──────────┘  └──────────┘
```

## Timing Summary

| Data Type | Coordinator | Poll Interval | Actual Fetch Interval | Data Window |
|-----------|-------------|---------------|----------------------|-------------|
| Profiles | Data | 5 min | 5 min (always) | Current |
| Presence | Data | 5 min | 5 min (always) | Today |
| Messages | Data | 5 min | 5 min (always) | Latest page |
| Notifications | Data | 5 min | 5 min (always) | Current |
| Calendar Events | Calendar | 10 min | 6 hours (cached) | Now → +2 weeks |
| Birthdays | Calendar | 10 min | 1 day (cached) | Now → +2 weeks |
| Weekly Plans | Calendar | 10 min | 6 hours (cached) | Now → +2 weeks |

## Async Execution Model

Both coordinators run synchronous HTTP code in executor threads:

```python
# Coordinator's update method (async context):
async def _async_update_data(self):
    async with async_timeout.timeout(10):
        data = await self.hass.async_add_executor_job(self._fetch_data)
        return data

# _fetch_data runs synchronously in a thread pool
# This prevents blocking HA's main event loop
```

The 10-second timeout ensures that a hung API call doesn't block the coordinator indefinitely.
