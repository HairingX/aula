# File Structure

## Complete File Tree

```
custom_components/aula/
│
├── __init__.py                              # Integration entry point
│   - async_setup_entry(): Creates client, coordinators, forwards platforms
│   - async_unload_entry(): Cleans up platforms and data
│   - async_reload_entry(): Reloads on config change
│   - PLATFORMS: [SENSOR, BINARY_SENSOR, CALENDAR]
│
├── config_flow.py                           # Configuration UI
│   - AulaCustomConfigFlow: Handles setup, reauth, reconfigure
│   - Connection validation before saving
│   - Error mapping and user-friendly messages
│
├── const.py                                 # Integration constants
│   - DOMAIN, API URLs, STARTUP banner
│   - Third-party API base URLs (Meebook, MinUddannelse, EasyIQ, Systematic)
│
├── manifest.json                            # Integration metadata
│   - Version: 0.1.8
│   - Requirements: beautifulsoup4, lxml
│   - Min HA version: 2024.9.3
│
├── entity.py                                # Base entity classes
│   - AulaEntityBase[T]: Generic data coordinator entity
│   - AulaCalendarEntityBase: Calendar coordinator entity
│   - Shared device_info configuration
│
├── sensor.py                                # Sensor entities (~200 lines)
│   - AulaStatusSensor: Detailed presence (enum 0-10)
│   - AulaPresenceSensor: Simple presence (present/not_present/unknown)
│   - AulaPresenceDurationSensor: Minutes present (measurement)
│
├── binary_sensor.py                         # Binary sensor entities (~250 lines)
│   - AulaUnreadMessageBinarySensor: Unread messages with preview
│   - AulaUnreadGalleryBinarySensor: New photos/videos
│   - AulaUnreadCalendarEventBinarySensor: Calendar notifications
│   - AulaUnreadPostBinarySensor: New posts
│   - AulaUnreadPresenceBinarySensor: Vacation/absence requests
│
├── calendar.py                              # Calendar entities (~400 lines)
│   - AulaEventCalendar: School events with filtering/timeslots
│   - AulaWeeklyPlanCalendar: Meebook weekly plans as events
│   - AulaBirthdayCalendar: Child birthdays
│
├── aula_client.py                           # Client facade (~100 lines)
│   - AulaClient: Simple wrapper over AulaProxyClient
│   - Exposes: login(), get_daily_overviews(), get_calendar_events(), etc.
│
├── aula_data.py                             # HA data types
│   - AulaHassData: TypedDict for hass.data storage
│   - set_hass_data() / get_hass_data() / remove_hass_data()
│
├── aula_data_coordinator.py                 # Data coordinator (~140 lines)
│   - AulaDataCoordinator: 5-minute polling
│   - AulaDataCoordinatorData: Profiles, presence, messages, notifications
│   - Widget support detection methods
│
├── aula_calendar_coordinator.py             # Calendar coordinator (~300 lines)
│   - AulaCalendarCoordinator: 10-minute polling with smart caching
│   - Listener registration/deregistration per entity
│   - Separate fetch logic for birthdays, events, weekly plans
│
├── module.py                                # Public exports
│   - Re-exports key classes for external use
│
├── services.yaml                            # Service definitions
│   - aula.api_call: Custom API calls with uri and post_data
│
├── strings.json                             # Localization keys
│   - Config flow strings, entity names, state translations
│
├── translations/
│   ├── en.json                              # English translations
│   └── da.json                              # Danish translations
│
└── aula_proxy/                              # API client module
    │
    ├── aula_proxy_client.py                 # Core HTTP client (~1000 lines)
    │   - UniLogin authentication (form scraping with BeautifulSoup)
    │   - Session and CSRF token management
    │   - Widget token caching (40-min expiry)
    │   - API version auto-discovery
    │   - Retry logic (3 attempts)
    │   - All API endpoint methods
    │
    ├── aula_errors.py                       # Custom exceptions
    │   - AulaCredentialError: Invalid login
    │   - ParseError: Unparseable response
    │
    ├── const.py                             # Proxy constants
    │   - API_VERSION (22), API base URL
    │   - Third-party API URLs
    │
    ├── module.py                            # Module re-exports
    │
    ├── models/                              # Data models
    │   │
    │   ├── constants.py                     # Enums and constants
    │   │   - AulaWidgetId: Widget ID enum (0001, 0004, 0029, 0030, 0062)
    │   │   - AulaCalendarEventType: Event type enum
    │   │
    │   ├── module.py                        # Model re-exports
    │   │
    │   ├── aula_profile_models.py           # Profile dataclasses
    │   │   - AulaLoginData, AulaProfile, AulaChildProfile
    │   │   - AulaInstitutionProfile, AulaInstitutionGroup
    │   │   - AulaToken, AulaWidget, AulaProfilePicture
    │   │   - AulaDailyOverview, AulaLocation
    │   │
    │   ├── aula_profile_parser.py           # Profile JSON parser
    │   │   - parse_profiles_response()
    │   │   - parse_widgets()
    │   │   - parse_profile_master_data_response()
    │   │   - parse_daily_overview_response()
    │   │
    │   ├── aula_calendar_models.py          # Calendar event dataclasses
    │   │   - AulaCalendarEvent, AulaCalendarEventTimeSlot
    │   │   - AulaCalendarEventLesson, AulaCalendarEventResource
    │   │
    │   ├── aula_calendar_parser.py          # Calendar JSON parser
    │   │
    │   ├── aula_message_thread_models.py    # Message dataclasses
    │   │   - AulaMessageThread, AulaMessage
    │   │   - AulaThreadRecipient, AulaMessageText
    │   │
    │   ├── aula_message_thread_parser.py    # Message JSON parser
    │   │
    │   ├── aula_notification_models.py       # Notification dataclasses
    │   │   - AulaNotificationBase (base class)
    │   │   - AulaCalendarEventNotification
    │   │   - AulaGalleryNotification, AulaAlbumNotification
    │   │   - AulaMessageNotification
    │   │   - AulaPostNotification
    │   │   - AulaPresenceNotification
    │   │   - AULA_NOTIFICATION_TYPES (union type)
    │   │
    │   ├── aula_notification_parser.py      # Notification JSON parser
    │   │
    │   ├── aula_weekly_plan_models.py       # Weekly plan dataclasses
    │   │   - AulaWeeklyPlan, AulaDailyPlan, AulaDailyPlanTask
    │   │
    │   ├── aula_weekly_plan_parser.py       # Weekly plan JSON parser
    │   │
    │   ├── aula_birthday_models.py          # Birthday dataclasses
    │   │   - AulaBirthdayEvent
    │   │
    │   └── aula_birthday_parser.py          # Birthday JSON parser
    │
    ├── responses/                           # API response TypedDicts
    │   ├── get_profiles_by_login_response.py
    │   ├── get_profile_context_response.py
    │   ├── get_profile_master_data_response.py
    │   ├── get_daily_overview_response.py
    │   ├── get_events_by_profile_ids_and_resource_ids.py
    │   ├── get_birthday_events_for_institutions.py
    │   ├── get_message_threads_response.py
    │   ├── get_messages_for_thread_response.py
    │   ├── get_notifications_response.py
    │   └── get_weekly_plans_response.py
    │
    ├── utils/
    │   └── list_utils.py                    # Utility functions
    │
    └── test_messages/                       # Test fixtures
        └── *.json                           # Sample API response JSON
```

## File Size and Complexity

| File | Lines (approx.) | Complexity |
|------|-----------------|------------|
| `aula_proxy_client.py` | ~1000 | High - login flow, all API methods, retry logic |
| `calendar.py` | ~400 | Medium - event filtering, timeslot handling |
| `aula_calendar_coordinator.py` | ~300 | Medium - smart caching, listener management |
| `binary_sensor.py` | ~250 | Low - notification filtering and attribute mapping |
| `sensor.py` | ~200 | Low - status/presence mapping |
| `aula_data_coordinator.py` | ~140 | Low - straightforward polling |
| `config_flow.py` | ~140 | Low - standard HA config flow |
| `aula_client.py` | ~100 | Low - thin facade |
| `__init__.py` | ~77 | Low - standard HA entry point |
| `entity.py` | ~60 | Low - base classes |

## Key Directories

| Directory | Purpose |
|-----------|---------|
| `custom_components/aula/` | Main integration code |
| `custom_components/aula/aula_proxy/` | API client module (standalone) |
| `custom_components/aula/aula_proxy/models/` | All data models and parsers |
| `custom_components/aula/aula_proxy/responses/` | API response type definitions |
| `custom_components/aula/aula_proxy/test_messages/` | JSON test fixtures |
| `custom_components/aula/translations/` | i18n files (en, da) |
