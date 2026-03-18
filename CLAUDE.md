# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Aula is a Home Assistant custom integration for the Danish Aula school/institution platform. It provides calendar events, presence tracking, messaging, and notification monitoring as HA sensors, binary sensors, and calendar entities.

## Development Commands

**Run Home Assistant locally (dev container):**
```bash
scripts/develop.sh
```
HA runs on port 8123 (mapped to 1337 in devcontainer).

**Run tests:**
```bash
python -m unittest discover -v -s ./custom_components/aula/aula_proxy -p "test_*.py"
```

**Run a single test:**
```bash
python -m unittest custom_components.aula.aula_proxy.test_messages.TestMessages.test_getProfilesByLogin
```

**Formatting:** Black with isort (`--profile black`), configured for format-on-save in VSCode.

**CI validation:** HACS validation and hassfest run on push/PR via GitHub Actions.

## Architecture

```
Config Flow (Unilogin credentials)
    → AulaClient (aula_client.py)
        → AulaProxyClient (aula_proxy/aula_proxy_client.py) - HTTP client, BeautifulSoup login scraping
            → Models (aula_proxy/models/) - @dataclass types
            → Parsers (aula_proxy/models/) - JSON → dataclass conversion
    → Coordinators
        ├─ AulaDataCoordinator (5 min) - profiles, daily overviews, messages, notifications
        └─ AulaCalendarCoordinator (10 min) - birthdays, events, weekly plans
    → Entities
        ├─ Sensors: status, presence, duration
        ├─ Binary Sensors: unread messages/gallery/calendar/posts/presence
        └─ Calendars: events, birthdays, weekly plans
```

**Key files:**
- `custom_components/aula/__init__.py` — Platform setup and entry point
- `custom_components/aula/aula_proxy/aula_proxy_client.py` — Core HTTP client (~1000 lines)
- `custom_components/aula/aula_proxy/models/` — All dataclass models and their parsers
- `custom_components/aula/const.py` — Integration constants; `aula_proxy/const.py` — API endpoints and widget IDs
- `custom_components/aula/config_flow.py` — Auth config flow (conf, reauth, reconf steps)

## Key Patterns

- **Model + Parser pairs:** Each data type has a `aula_*_models.py` (dataclasses) and `aula_*_parser.py` (JSON parsing). Parsers are static methods that convert raw API JSON to typed dataclasses.
- **Entity base classes:** `AulaEntityBase[T]` for sensors/binary sensors, `AulaCalendarEntityBase` for calendars — both extend HA's `CoordinatorEntity`.
- **Widget detection:** `has_widget(AulaWidgetId.X)` checks which Aula features are available for a given institution.
- **Blocking HTTP in async:** Uses `async_add_executor_job()` to run synchronous HTTP calls from async HA context.
- **Localization:** `strings.json` with translations in `translations/en.json` and `translations/da.json`.

## Agent Workflow (MANDATORY)

**All code changes MUST follow the agent workflow process defined in `docs/AGENT_WORKFLOW.md`.** This process requires every task to pass through 9 stages: Project Management → Design Document → Design Review (multi-team) → Implementation → QA Review → Performance Review → Network & Data Review → HASS Compliance → Final Verification. **NO code may be written until the design document is reviewed and approved by all specialist agent teams (Stage 3).** No stage may be skipped. Read the full process document before starting any task.

## Conventions

- All documentation, comments, and commit messages must be written in English unless explicitly told otherwise
- Python 3.14, minimum Home Assistant 2026.3.0
- 4-space indentation, LF line endings
- unittest framework (not pytest) for tests; test fixtures are JSON files in `aula_proxy/test_messages/`
- Version tracked in `custom_components/aula/manifest.json`
