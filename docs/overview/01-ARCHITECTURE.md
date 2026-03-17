# Architecture

## Layered Architecture

The integration is built in four clear layers, from low-level HTTP communication to high-level Home Assistant entities:

```
┌─────────────────────────────────────────────────────────────────┐
│                    LAYER 4: HOME ASSISTANT ENTITIES              │
│  sensor.py  │  binary_sensor.py  │  calendar.py  │  entity.py  │
│                                                                 │
│  Presents data as HA entities with states and attributes.       │
│  Inherits from CoordinatorEntity for automatic updates.         │
└────────────────────────────┬────────────────────────────────────┘
                             │ subscribes to
┌────────────────────────────┴────────────────────────────────────┐
│                    LAYER 3: COORDINATORS                         │
│  aula_data_coordinator.py  │  aula_calendar_coordinator.py      │
│                                                                 │
│  Polls the API at fixed intervals (5 / 10 min).                │
│  Caches data. Controls when data should be reloaded.           │
│  Handles errors and re-authentication.                         │
└────────────────────────────┬────────────────────────────────────┘
                             │ calls
┌────────────────────────────┴────────────────────────────────────┐
│                    LAYER 2: CLIENT + PARSERS                     │
│  aula_client.py (facade)                                        │
│  aula_proxy/aula_proxy_client.py (HTTP client)                 │
│  aula_proxy/models/*_parser.py (JSON → dataclass)              │
│                                                                 │
│  AulaClient is a simple facade exposing clean methods.          │
│  AulaProxyClient handles HTTP, login, sessions, tokens.        │
│  Parsers convert raw JSON to strongly-typed dataclasses.        │
└────────────────────────────┬────────────────────────────────────┘
                             │ communicates with
┌────────────────────────────┴────────────────────────────────────┐
│                    LAYER 1: EXTERNAL APIs                        │
│  Aula.dk (v22)  │  Meebook  │  MinUddannelse  │  EasyIQ       │
│                                                                 │
│  REST APIs requiring session cookies and CSRF tokens.          │
│  Authentication via UniLogin (Danish SSO for schools).          │
└─────────────────────────────────────────────────────────────────┘
```

## Component Overview

### Entry Point (`__init__.py`)
- Registers the integration with Home Assistant
- Creates `AulaClient` with username/password from config entry
- Initializes both coordinators
- Performs first data refresh (`async_config_entry_first_refresh`)
- Forwards entry setup to platforms: SENSOR, BINARY_SENSOR, CALENDAR
- Listens for configuration changes and reloads as needed

### Config Flow (`config_flow.py`)
- Controls the setup UI in Home Assistant
- Handles initial configuration, reconfiguration, and re-authentication
- Validates credentials against the Aula API before saving

### AulaClient (`aula_client.py`)
- **Facade pattern**: Simple interface over the more complex proxy client
- Exposes clean methods: `login()`, `get_daily_overviews()`, `get_calendar_events()`, etc.
- Delegates all HTTP work to `AulaProxyClient`

### AulaProxyClient (`aula_proxy/aula_proxy_client.py`)
- ~1000 lines core HTTP client
- Handles the complex UniLogin authentication with form scraping
- Session management with persistent cookies
- CSRF token management
- Widget token caching (40-minute lifetime)
- Automatic API version discovery (starts at v22, tries newer on 410 GONE)
- Retry logic (3 attempts on server errors)

### Models (`aula_proxy/models/`)
- Python `@dataclass` classes for all data types
- Separate parser classes with static methods for JSON → dataclass conversion
- Model-parser pairs: `aula_*_models.py` + `aula_*_parser.py`

### Coordinators
- **AulaDataCoordinator** (5 min): Profiles, daily presence, messages, notifications
- **AulaCalendarCoordinator** (10 min): Calendar events, birthdays, weekly plans
- Both use HA's `DataUpdateCoordinator` base class
- Run synchronous HTTP calls via `async_add_executor_job()`

### Entities
- **Sensors**: 3 per child (status, presence, duration)
- **Binary Sensors**: 5 per integration (unread messages, gallery, calendar, posts, presence)
- **Calendars**: 3 per child (events, weekly plans, birthdays)
- All inherit from `CoordinatorEntity` and update automatically on coordinator refresh

## Design Principles

1. **Separation of concerns**: Each layer has its own responsibility
2. **Coordinator pattern**: HA's recommended pattern for cloud-polling integrations
3. **Facade pattern**: `AulaClient` hides proxy complexity
4. **Model-Parser pairs**: Separation of data representation and parsing
5. **Listener-based caching**: Calendar coordinator only fetches data for entities actually in use
6. **Smart update intervals**: Different data types update at different frequencies based on how quickly they change
