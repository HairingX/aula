# Bad Practices & Home Assistant Best Practice Violations

Modern Home Assistant (2024-2025+) best practices that this integration violates.

Each finding has been cross-verified by independent review agents.

---

## HOME ASSISTANT PLATFORM PATTERNS

### 1. No `entry.runtime_data` usage (HA 2024.x+)
**Status: CONFIRMED**

**File:** `custom_components/aula/__init__.py:40-46`

**Problem:** Stores runtime data manually in `hass.data[DOMAIN][entry.entry_id]`. Modern HA uses typed `entry.runtime_data`.

**Note from second review:** The integration DOES have manual cleanup via `remove_hass_data()` in `async_unload_entry`, so the claim of "no automatic cleanup" is overstated. However, migration to `runtime_data` is still recommended.

**Fix risk: Low-Medium.** Requires updating `aula_data.py` and all callers of `get_hass_data`, `get_aula_data_coordinator`, `get_aula_calendar_coordinator` etc. Not a simple drop-in.

---

### 2. No EntityDescription usage
**Status: CONFIRMED (impact overstated)**

**Files:** `custom_components/aula/sensor.py`, `custom_components/aula/binary_sensor.py`

**Note from second review:** These entities have significant per-entity logic in `_set_values()` (complex attribute building, icon changes, value computation). `EntityDescription` works best for mostly declarative entities. Forced conversion could make code harder to read, not easier.

**Fix risk: Medium.** The suggested pattern oversimplifies. Consider adopting EntityDescription only for entities that are truly declarative.

---

### 3. Missing entity categories
**Status: PARTIALLY CORRECT**

**Files:** `sensor.py`, `binary_sensor.py`

**Note from second review:** The suggestion to use `EntityCategory.DIAGNOSTIC` for "unread messages" is wrong. `DIAGNOSTIC` is for internal integration health, not user-facing data. Some entities may benefit from categorization, but the specific recommendation needs rethinking per entity.

---

### 4. Synchronous HTTP client (blocking I/O)
**Status: CONFIRMED**

**File:** `custom_components/aula/aula_proxy/aula_proxy_client.py`

**Fix risk: Very High.** The login flow involves complex redirect-following and HTML form scraping with BeautifulSoup that would need complete reimplementation with `aiohttp`. The current `async_add_executor_job()` approach, while suboptimal, is functional and commonly used in HACS integrations. This is a long-term architectural goal, not a quick fix.

---

### 5. Missing Options Flow
**Status: CONFIRMED**

**Files:** `config_flow.py`, `strings.json`

`strings.json` defines an "options" step UI but no `OptionsFlowHandler` is implemented. Users cannot change settings after initial setup.

**Fix risk: None** (purely additive).

---

### 6. CONF_ID not persisted in config entry
**Status: PARTIALLY CORRECT (low practical impact)**

**File:** `custom_components/aula/config_flow.py:51-56`

**Note from second review:** While CONF_ID is not in `entry.data`, it IS preserved as `unique_id` (via `async_set_unique_id`) and as `entry.title`. The reconfigure/reauth flows don't display the ID field to the user, so the empty `_id` is unused in those flows.

**Fix risk: Low.** Adding CONF_ID to stored data is safe but impact is minimal.

---

### 7. Missing minimum HA version in manifest
**Status: CONFIRMED**

**File:** `custom_components/aula/manifest.json`

Add `"homeassistant": "2024.9.3"` per project requirements.

**Fix risk: None.**

---

### 8. `always_update=True` on coordinators
**Status: PARTIALLY CORRECT**

**Files:** `aula_data_coordinator.py:50`, `aula_calendar_coordinator.py:65`

**Note from second review:**
- **Data coordinator:** `AulaEntityBase._handle_coordinator_update()` always calls `async_write_ha_state()` without checking changes -- wasteful with `always_update=True`.
- **Calendar coordinator:** Already has its own deduplication logic in `_handle_data_updated` which returns `True`/`False`. `always_update=True` is actually needed here because the coordinator data contains lists of updated keys, and each entity must check if its key was updated.

**Fix risk: Medium for calendar coordinator.** Implementing `__eq__` and `always_update=False` on the calendar coordinator could break its notification mechanism.

---

### 9. `device_info` as `@property` instead of `_attr_device_info`
**Status: CONFIRMED**

**File:** `custom_components/aula/entity.py:37-45, 66-74`

**Note from second review:** `self.coordinator.aula_version` is updated during `_fetch_data`, so the property approach would reflect changes while `_attr_device_info` set in `__init__` would not. In practice, `aula_version` is unlikely to change during runtime, so risk is negligible.

**Fix risk: Low.**

---

### 10. `@final` override on `state_attributes`
**Status: CONFIRMED**

**File:** `custom_components/aula/calendar.py:283-320`

Overrides `CalendarEntity.state_attributes` which is marked `@final` in HA. Python's `@final` from `typing` is not enforced at runtime, but it's semantically wrong.

**Fix:** Migrate weekly plan attributes to `extra_state_attributes` instead.

**Fix risk: Medium.** Requires understanding exactly which attributes are custom additions vs base class defaults.

---

## PYTHON BEST PRACTICES

### 11. Exception as return value (anti-pattern)
**Status: CONFIRMED (fix location needs adjustment)**

**Files:** `aula_data_coordinator.py:138-140`, `aula_calendar_coordinator.py:124`

**Note from second review:** The fix should NOT raise `UpdateFailed` inside `_fetch_data` (runs in executor thread). Instead, let exceptions propagate naturally from `_fetch_data`, and let `_async_update_data` catch and re-raise as `UpdateFailed` (which it already does in its outer try/except). Simplest fix: remove the try/except in `_fetch_data` entirely.

---

### 12. No session lifecycle management
**Status: CONFIRMED**

**File:** `custom_components/aula/aula_proxy/aula_proxy_client.py`

Add a `close()` method and call it from `async_unload_entry`.

**Fix risk: None.**

---

### 13. Credentials stored as plain-text instance attributes
**Status: PARTIALLY CORRECT (fix would break functionality)**

**File:** `custom_components/aula/aula_proxy/aula_proxy_client.py:49-50`

**Note from second review:** Clearing credentials after first login is NOT possible. The `login()` method is called on every coordinator refresh (checks token expiry and re-logs in). Credentials must persist for the client's lifetime.

**Fix risk: High** -- clearing credentials would break re-login flow. **Do not fix.**

---

### 14. No exponential backoff on retries
**Status: CONFIRMED**

**File:** `custom_components/aula/aula_proxy/aula_proxy_client.py:320-570`

Retry loops immediately retry without backoff, creating burst requests under load.

**Fix risk: Low.**

---

### 15. Massive code duplication in retry pattern
**Status: CONFIRMED**

**File:** `custom_components/aula/aula_proxy/aula_proxy_client.py`

Same retry-loop pattern copy-pasted 7 times across methods.

**Note from second review:** A generic helper needs to handle GET vs POST, different headers, and the weekly plans method's extra loop. Design carefully.

**Fix risk: Low** (with careful design).

---

### 16. Silent defaults in parser utility methods
**Status: CONFIRMED (fix needs careful audit)**

**File:** `custom_components/aula/aula_proxy/models/aula_parser.py:69, 88`

`_parse_int()` returns `-1` for `None`; `_parse_str()` returns `""` for `None`.

**Note from second review:** Changing `_parse_int` to raise on `None` could break many call sites. The nullable variants (`_parse_nullable_int`, `_parse_nullable_str`) already return `None` for `None` and are used where nullability is expected. Would need careful audit of all callers before changing.

**Fix risk: Medium.**

---

### 17. Inconsistent parser error handling
**Status: CONFIRMED**

Some parsers raise `ValueError()` with no message, others return `None`, others use silent defaults. No consistent contract.

**Fix risk: Low** for adding messages to ValueError calls. **Medium** for standardizing the contract across all parsers.

---

### 18. Thread safety concerns
**Status: PARTIALLY CORRECT (low practical risk)**

**Note from second review:** `requests.Session` itself is thread-safe for basic operations. Both coordinators run on different intervals (5 min vs 10 min), so concurrent updates are possible but unlikely. The token dict mutation is the most realistic concern, but practical risk is low.

**Fix risk: Low** for adding locks, but could introduce deadlocks if not careful.

---

## TEST QUALITY

### 19. Test accesses dataclass as dictionary
**Status: CONFIRMED (test is provably broken)**

**File:** `custom_components/aula/aula_proxy/test_messages.py:14-62`

The test uses `profile["profile_id"]` but `AulaProfile` is a dataclass. This test **fails at runtime** with `TypeError: 'AulaProfile' object is not subscriptable`.

**Fix risk: None.** Change to attribute access (`profile.profile_id`).

---

### 20. Only 1 test method for entire proxy layer
**Status: CONFIRMED**

**File:** `custom_components/aula/aula_proxy/test_messages.py`

Single test covers only profile parsing. No tests for any other functionality.

**Fix risk: None** (purely additive).

---

### 21. Hardcoded test file path
**Status: CONFIRMED**

**File:** `custom_components/aula/aula_proxy/test_messages.py:10`

Uses path relative to CWD. Should use `pathlib.Path(__file__).parent`.

**Fix risk: None.**
