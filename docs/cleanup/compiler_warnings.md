# Compiler, Type, and Static Analysis Issues

Issues that would be caught by type checkers (mypy/pyright), linters, or produce Python warnings.

Each finding has been cross-verified by independent review agents.

---

## TYPE ANNOTATION ISSUES

### 1. Mixed type hint syntax (PEP 604 inconsistency)
**Status: CONFIRMED**

**File:** `custom_components/aula/config_flow.py:2`

**Problem:** Mixes `Optional[X]` (old) with `X | None` (PEP 604). Python 3.13 target means PEP 604 should be used consistently.

```python
# Current:
from typing import Any, Dict, Mapping, Optional

# Fix: Remove Optional, Dict, Mapping imports; use built-in equivalents:
from typing import Any
# Then: dict[str, Any] instead of Dict[str, Any]
#        X | None instead of Optional[X]
```

**Affected files:**
- `config_flow.py:2` - imports `Optional`, `Dict`, `Mapping`
- `aula_proxy/models/aula_profile_models.py`
- `aula_proxy/models/aula_calendar_models.py`
- `aula_proxy/models/aula_message_thread_models.py`
- `aula_proxy/models/aula_notification_models.py`

---

### 2. Redundant `Optional[str|None]` pattern
**Status: CONFIRMED**

**File:** `custom_components/aula/aula_proxy/models/aula_profile_models.py` (10+ instances)

**Problem:** `Optional[str|None]` is doubly redundant. `Optional[X]` already means `X | None`, so `Optional[str|None]` expands to `str | None | None`.

```python
# Current:
field: Optional[str|None] = None

# Fix:
field: str | None = None
```

---

### 3. 17x `# type: ignore` comments
**Status: PARTIALLY CORRECT**

**Files:** Spread across 7 files (entity.py, sensor.py, binary_sensor.py, calendar.py, aula_data.py)

**Root cause:** Multiple inheritance combining `AulaEntityBase[T]` (or `AulaCalendarEntityBase`) with HA entity classes.

**Note from second review:** Fixing the Generic typing may not eliminate all suppressions, as some stem from HA's own type stubs. Each suppression should be evaluated individually.

---

### 4. Config flow parameter types not matching HA convention
**Status: PARTIALLY CORRECT**

**File:** `custom_components/aula/config_flow.py:34, 59, 72, 93`

**Note from second review:** The `Dict[str, str]` is technically correct for this use case (all inputs are strings), but HA convention is `dict[str, Any] | None = None`. Some methods are also missing `| None = None` default. The fix is a convention alignment, not a bug fix.

---

## UNUSED CODE

### 5. ~230 lines of commented-out code in aula_proxy_client.py
**Status: CONFIRMED**

**File:** `custom_components/aula/aula_proxy/aula_proxy_client.py:576-805`

**Content:** Four unimplemented methods (`get_weekly_newsletters`, `get_task_list`, `get_easyiq_weekplan`, `get_reminders`) marked with `#TODO: Not yet implemented`.

**Note from second review:** These represent future feature work and may serve as implementation templates. The developer may prefer to keep them. Decision should be intentional.

---

### 6. ~60 lines of commented-out code in aula_client.py
**Status: CONFIRMED**

**File:** `custom_components/aula/aula_client.py:68-125`

Dead code: `get_widgets_data()`, `update_data()`, `get_data()`. Safe to remove.

---

### 7. Commented-out imports
**Status: CONFIRMED**

**File:** `custom_components/aula/aula_proxy/aula_proxy_client.py:30-32`

```python
# from .const import MIN_UDDANNELSE_API
# from .const import SYSTEMATIC_API
# from .const import EASYIQ_API
```

---

### 8. Commented-out constants
**Status: CONFIRMED**

**File:** `custom_components/aula/aula_proxy/models/constants.py:7-24`

Multiple commented-out `AulaWidgetId` values with descriptive docstrings.

**Note from second review:** These serve as documentation of known widget IDs. Removing loses documentation value. Consider moving to a comment block or separate doc instead of deleting.

---

### 9. Incomplete weekly newsletter parser
**Status: CONFIRMED**

**File:** `custom_components/aula/aula_proxy/models/aula_weekly_newsletter_parser.py`

Entirely commented out with syntax errors (e.g., `for institution in :` on line 77).

**Note from second review:** The corresponding models file (`aula_weekly_newsletter_models.py`) is NOT commented out and IS imported by `module.py`. Removing the parser is safe; removing the models requires updating `module.py` imports.

---

## NAMING AND CONVENTION ISSUES

### 10. Filename typo: "notication" instead of "notification"
**Status: CONFIRMED**

**File:** `custom_components/aula/aula_proxy/models/aula_notification_models.py`

**Note from second review:** The import in `module.py:30` uses the typo'd name. Renaming requires a coordinated update of both the file and the import.

---

### 11. Wildcard imports
**Status: CONFIRMED (mitigated)**

**File:** `custom_components/aula/aula_proxy/aula_proxy_client.py:15`

Uses `from .models.module import *`. The `module.py` file does define `__all__`, which mitigates the worst issues. Still not ideal per PEP 8.

---

## DEPRECATION / MODERNIZATION

### 12. Missing `TYPE_CHECKING` blocks
**Status: CONFIRMED (apply with caution)**

**Files:** All Python files

No files use `from __future__ import annotations` or `if TYPE_CHECKING:` blocks.

**Note from second review:** Adding `from __future__ import annotations` can have subtle side effects with dataclasses and runtime `isinstance` checks on type annotations. Must be applied carefully, especially around dataclass fields.

---

## WARNINGS

### 13. ResourceWarning: unclosed Session
**Status: CONFIRMED**

**File:** `custom_components/aula/aula_proxy/aula_proxy_client.py:56`

`requests.Session()` created but never explicitly closed. May emit `ResourceWarning` during garbage collection.

---

### 14. Print statement in test code
**Status: CONFIRMED**

**File:** `custom_components/aula/aula_proxy/test_messages.py:64`

`print()` statement should use logging or be removed.

---

## REMOVED (disproven by second review)

### ~~`async_timeout` package deprecated~~
**Status: INCORRECT** - The code already uses `asyncio.timeout()` (the modern pattern). Both coordinators import `asyncio` and use `async with asyncio.timeout(10):`. The original finding incorrectly claimed `async_timeout` was imported.
