# Upstream Bug Fixes Analysis

## Summary Table

| PR | Fix | Severity | Applies to Our Fork? | Status |
|----|-----|----------|----------------------|--------|
| #300 | Calendar unload when schoolschedule disabled | Medium | Partially | Needs review |
| #303 | Entity unavailable flipping on token refresh | High | No | MitID-specific |
| #314 | lxml version pinning for HA 2026.3 | Medium | No | We have no pin |
| #294 | Teacher full name display | Feature | No | Different calendar arch |
| #200 | ISO 8601 week number formatting | Medium | Needs check | Could affect weekly plans |
| #216 | Calendar null-safety for primaryResource | Low | No | Different calendar arch |
| #192 | Ugeplaner task author null handling | Low | No | Different client arch |

---

## Detailed Analysis

### PR #300 - Calendar Platform Unload (commit `17315b4`)

**Bug:** When unloading a config entry, the code always tried to unload the "calendar" platform even if `CONF_SCHOOLSCHEDULE` was `False`. This caused an error because the calendar platform was never set up.

**Upstream fix in `__init__.py`:**
```python
# Only include "calendar" in platforms_to_unload when schoolschedule is enabled
platforms_to_unload = ["sensor", "binary_sensor"]
if entry.data.get(CONF_SCHOOLSCHEDULE, True):
    platforms_to_unload.append("calendar")
```

**Our fork status:**
Our `__init__.py` always unloads all three platforms:
```python
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.CALENDAR]
# ...
return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
```

**Assessment:** LOW RISK currently. Our fork always sets up the calendar platform (we don't have a schoolschedule toggle). However, if we add a conditional calendar setup in the future, or if the calendar coordinator fails to initialize, the unconditional unload could cause errors. Worth noting but not urgent.

---

### PR #303 - Entity Unavailable Flipping (commit `418cc93`)

**Bug:** Token refresh called `hass.config_entries.async_update_entry(entry, data=new_data)` which triggers a config entry reload cycle, causing entities to flip to "unavailable" every time tokens were refreshed. Also had concurrent token refresh race conditions.

**Upstream fix:**
- Changed `async_update_tokens()` to update runtime storage (`hass.data[DOMAIN][entry.entry_id]["tokens"]`) instead of `entry.data`
- Added `threading.Lock` (`_token_refresh_lock`) in `client.py` to prevent concurrent refresh
- Made token persistence fire-and-forget (non-blocking)
- Made `_ensure_valid_token()` return `bool` with proper error handling

**Our fork status:** NOT APPLICABLE. We don't have MitID token refresh. Our auth is session/cookie-based via UniLogin. However, **if we adopt MitID auth, this fix must be included from the start.**

---

### PR #314 - lxml Version Constraint (commits `8345f7c`, `d3e834f`)

**Bug:** `lxml==5.3.0` exact pin prevented installation on Home Assistant 2026.3 which ships with a newer lxml.

**Upstream fix:** Changed `lxml==5.3.0` to `lxml>=5.3.0`.

**Our fork status:** NOT AFFECTED. Our `manifest.json` has `"lxml"` with no version constraint, which is already more permissive.

---

### PR #200 - ISO 8601 Week Numbers (commit `796dc53`)

**Bug:** Used `%W` (Sunday-start, zero-padded) instead of `%V` (ISO 8601, Monday-start) for week number formatting. This caused wrong week plans to be fetched, especially around year boundaries.

**Upstream fix:** Changed `strftime("%Y-W%W")` to `strftime("%Y-W%V")` in two places in `client.py` (MU Opgaver and Ugeplan sections).

**Our fork status:** NEEDS VERIFICATION. Our `aula_proxy_client.py` handles weekly plans. Checking the code:

In our `aula_proxy_client.py`, the weekly plan methods use `isoformat()` and `isocalendar()` for date handling rather than `strftime` with `%W`. Our code in `get_weekly_plans()` passes dates directly, not week numbers. **We likely do NOT have this bug** due to our different implementation, but should be verified by testing around year boundaries (e.g., Dec 31 / Jan 1).

---

### PR #216 - Calendar Null Safety (commit `35e745b`)

**Bug:** Calendar parsing crashed when `primaryResource` was `None` (not just missing) - `.get('name')` fails on `None`.

**Upstream fix:** Used `(lesson.get("primaryResource", {}) or {}).get("name")` pattern.

**Our fork status:** NOT APPLICABLE. Our fork uses typed dataclass models with parsers that handle null values at parse time. Our calendar entities (`AulaEventCalendar`, `AulaWeeklyPlanCalendar`, `AulaBirthdayCalendar`) use coordinated data that's already been safely parsed.

---

### PR #192 - Ugeplaner Task Author Null Handling

**Bug:** `task.get('author')` could be `None`, causing crashes. Also needed to distinguish between task types (`comment`, `task`, `assignment`) to use correct field.

**Our fork status:** NOT APPLICABLE. Different client architecture with typed models.

---

## API Version Mismatch

**Upstream:** `API_VERSION = "22"` in `const.py`
**Our fork:** `API_VERSION = "19"` in `const.py`, `API_VERSION = "22"` in `aula_proxy/const.py`

Our proxy client imports from `aula_proxy/const.py` which already has `"22"`, so the actual API calls use version 22. The outer `const.py` with `"19"` appears to be unused by the proxy client. Additionally, our proxy client has auto-version-increment logic on HTTP 410 responses, providing automatic fallback.

**Assessment:** LOW RISK. The proxy client already uses v22 and has auto-increment fallback. The `const.py` value of `"19"` should be updated to `"22"` for consistency but is not functionally critical.
