# Structural & Architectural Issues

Code organization, design, and architectural problems.

Each finding has been cross-verified by independent review agents.

---

## ARCHITECTURE

### 1. God method: `login()` is 228 lines
**Status: CONFIRMED**

**File:** `custom_components/aula/aula_proxy/aula_proxy_client.py:89-317`

Single method handles session reuse, HTML form navigation, redirect loops, error detection, profile fetching, widget detection, and master data parsing.

**Suggested refactor:**
```
login()
  +-- _try_existing_session()
  +-- _submit_login_forms()
  +-- _handle_login_redirects()
  +-- _fetch_profiles()
  +-- _fetch_widgets()
  +-- _fetch_master_data()
```

---

### 2. No separation of concerns in AulaProxyClient
**Status: CONFIRMED**

**File:** `custom_components/aula/aula_proxy/aula_proxy_client.py` (997 lines)

Single class handles HTTP session management, login/authentication, HTML scraping, API calls, response parsing, retry logic, token management, and error handling.

---

### 3. Calendar entity file contains 3 classes
**Status: CONFIRMED (corrected from original)**

**File:** `custom_components/aula/calendar.py` (404 lines)

Contains 3 calendar entity classes (not 4 as originally stated): `AulaBirthdayCalendar`, `AulaEventCalendar`, and `AulaWeeklyPlanCalendar`. Whether splitting is warranted is debatable for 3 related classes.

---

### 4. Entity unique_id defaults to translation_key in base class
**Status: PARTIALLY CORRECT (no runtime impact)**

**File:** `custom_components/aula/entity.py:20-21`

```python
self._attr_translation_key = name
self._attr_unique_id = self._attr_translation_key
```

**Note from second review:** Every subclass overrides this by appending `_{first_name}_{institution_name}` before entities are registered with HA. The base class default is not globally unique, but no actual conflicts occur. Valid concern from defensive coding perspective only.

---

## FILE ORGANIZATION

### 5. Model/parser pairs are inconsistently named
**Status: CONFIRMED**

| Model File | Parser File | Issue |
|-----------|-------------|-------|
| `aula_notification_models.py` | `aula_notification_parser.py` | Filename typo fixed |
| `aula_weekly_newsletter_models.py` | `aula_weekly_newsletter_parser.py` | Parser entirely commented out |

**Note:** `aula_notication_models.py` has been renamed to `aula_notification_models.py` and imports updated.

---

### 6. Constants duplicated across two files with conflicting versions
**Status: CONFIRMED (understated in original analysis)**

**Files:**
- `custom_components/aula/const.py` - `API_VERSION = "19"`
- `custom_components/aula/aula_proxy/const.py` - `API_VERSION = "22"`

The two files have largely **duplicated** constants (`STARTUP`, `DOMAIN`, API URLs) with **different `API_VERSION` values** (19 vs 22). The proxy client imports from `aula_proxy/const.py` (version 22). This is more serious than originally stated -- conflicting versions could cause subtle bugs if the wrong constant is imported.

---

## CODE DUPLICATION

### 7. Retry loop pattern duplicated 7 times
**Status: CONFIRMED**

**File:** `custom_components/aula/aula_proxy/aula_proxy_client.py`

**Locations:** `get_birthday_events()`, `get_calendar_events()`, `get_daily_overviews()`, `get_message_threads()`, `get_messages()`, `get_notifications()`, `get_weekly_plans()`

Each method repeats the same ~10-line retry pattern. A generic helper would eliminate ~70+ lines.

---

### 8. Device info duplicated in two base entity classes
**Status: CONFIRMED**

**File:** `custom_components/aula/entity.py:37-45, 66-74`

`AulaEntityBase` and `AulaCalendarEntityBase` have near-identical `device_info` properties. Could share via mixin or common base.

---

### 9. Calendar coordinator has 3 near-identical listener patterns
**Status: CONFIRMED**

**File:** `custom_components/aula/aula_calendar_coordinator.py:170-300`

`async_add_birthday_listener/key`, `async_add_calendar_event_listener/key`, and `async_add_weekly_plan_listener/key` follow the same pattern with different data types. Generalization is possible but would add complexity via generics.

---

## SERVICES

### 10. Service defined but not registered
**Status: CONFIRMED**

**File:** `custom_components/aula/services.yaml`

Defines an `api_call` service but no `hass.services.async_register()` call exists anywhere. The service is non-functional.

**Note from second review:** Removing `services.yaml` requires also removing corresponding entries in `strings.json` and `translations/` to avoid HACS validation failures.

---

## REMOVED (disproven by second review)

### ~~Tight coupling - coordinators call `self._client._proxy.login()`~~
**Status: INCORRECT** - Coordinators call `self._client.login()` (proper public API), not `self._client._proxy.login()`. `AulaClient` properly encapsulates the proxy.

### ~~AulaData is a thin wrapper with no clear purpose~~
**Status: INCORRECT** - The original finding mischaracterized the file. `aula_data.py` is 39 lines containing `AulaHassData` (a TypedDict) plus 6 helper functions providing a typed access layer for `hass.data`. It serves a clear purpose.

---

## ADDITIONAL FINDING (discovered during second review)

### 11. Constructor argument mismatch in `__init__.py`
**Status: NEEDS VERIFICATION**

**File:** `custom_components/aula/__init__.py:39`

Second review agent found that `AulaCalendarCoordinator(entry.title, hass, client, entry)` passes 4 arguments, but the constructor at `aula_calendar_coordinator.py:53` only accepts 3 (`device_id, hass, client`). This would cause a `TypeError` at runtime. If the integration is working in production, one of the files may have been recently updated without the other.

**This was not caught by the original analysis and needs immediate investigation.**

---

## SUMMARY: Priority Refactoring Targets

| Priority | Item | Effort | Impact | Fix Risk |
|----------|------|--------|--------|----------|
| **Critical** | Constructor arg mismatch (#11) | Low | Crash | Low |
| **High** | Conflicting API_VERSION constants (#6) | Low | Subtle bugs | Low |
| **High** | Extract retry logic to helper (#7) | Low | -70 lines duplication | Low |
| **Medium** | Split `login()` into smaller methods (#1) | Medium | Maintainability | Low |
| **Medium** | Remove non-functional service (#10) | Low | Cleanup | Low |
| **Low** | Fix filename typo (#5) | Low | Consistency | Low |
| **Low** | Deduplicate device_info (#8) | Low | Less duplication | Low |
