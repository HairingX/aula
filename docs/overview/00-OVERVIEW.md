# Aula Home Assistant Integration - Documentation Overview

## What is this?

Aula is a custom Home Assistant integration that connects the Danish school communication platform [Aula](https://www.aula.dk) with Home Assistant. The integration fetches data about children's presence, calendar events, messages, notifications, weekly plans, and birthdays, and exposes them as HA entities (sensors, binary sensors, and calendars).

## Documents

| Document | Content |
|----------|---------|
| [01-ARCHITECTURE.md](01-ARCHITECTURE.md) | High-level architecture, layering, and component overview |
| [02-AUTHENTICATION-FLOW.md](02-AUTHENTICATION-FLOW.md) | Login process via UniLogin, session and token management |
| [03-DATA-FLOW.md](03-DATA-FLOW.md) | How data flows from API to Home Assistant entities |
| [04-ENTITIES.md](04-ENTITIES.md) | All entities: sensors, binary sensors, and calendars |
| [05-API-ENDPOINTS.md](05-API-ENDPOINTS.md) | All API endpoints, request/response formats, and third-party integrations |
| [06-DATA-MODELS.md](06-DATA-MODELS.md) | All dataclasses, parsers, and type relationships |
| [07-COORDINATOR-PATTERN.md](07-COORDINATOR-PATTERN.md) | Polling strategy, caching, listener pattern, and smart updates |
| [08-CONFIG-FLOW.md](08-CONFIG-FLOW.md) | Setup, reconfiguration, re-authentication, and error handling |
| [09-FILE-STRUCTURE.md](09-FILE-STRUCTURE.md) | Complete file structure with description of each file |

## Quick Architecture Overview

```
User configures via HA UI (config_flow.py)
         |
         v
    AulaClient (facade)
         |
         v
    AulaProxyClient (HTTP, BeautifulSoup login scraping)
         |
         v
    Aula API (aula.dk/api/v22) + Meebook/MinUddannelse/EasyIQ/Systematic
         |
         v
    Parsers (JSON -> @dataclass models)
         |
         v
    Coordinators (polling + caching)
    ├── AulaDataCoordinator (5 min) -> profiles, daily overviews, messages, notifications
    └── AulaCalendarCoordinator (10 min) -> calendar, birthdays, weekly plans
         |
         v
    HA Entities
    ├── Sensors: status, presence, duration
    ├── Binary Sensors: unread messages/gallery/calendar/posts/presence
    └── Calendars: events, weekly plans, birthdays
```

## Technical Requirements

- Python 3.13
- Home Assistant 2024.9.3+
- Dependencies: `beautifulsoup4`, `lxml`
- IoT Class: `cloud_polling`
