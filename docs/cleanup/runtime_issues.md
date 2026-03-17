# Runtime Issues

Critical issues that cause or can cause actual runtime errors, crashes, or incorrect behavior.

Each finding has been cross-verified by independent review agents.

---

## CRITICAL

### 1. `isinstance(error.args, str)` is always False
**Status: CONFIRMED**

**Files:**
- `custom_components/aula/aula_data_coordinator.py:98`
- `custom_components/aula/aula_calendar_coordinator.py:119`
- `custom_components/aula/config_flow.py:147`

**Problem:** `Exception.args` is always a `tuple`, never a `str`. This means the branch is dead code and error messages are never propagated.

```python
# Current (BROKEN):
if isinstance(error.args, str) and len(error.args) > 0:
    raise UpdateFailed(error.args) from error

# Fix:
if error.args and isinstance(error.args[0], str):
    raise UpdateFailed(error.args[0]) from error
```

---

### 2. IndexError on `.split()[0]` with empty displayName
**Status: CONFIRMED**

**File:** `custom_components/aula/aula_proxy/models/aula_profile_parser.py:20, 50`

**Problem:** If `data.get("displayName")` or `data.get("name")` is `None`, `_parse_str()` returns `""`, and `"".split()` returns `[]`, so `[0]` raises `IndexError`.

```python
# Current (CRASHES on empty name):
first_name = AulaProfileParser._parse_str(data.get("displayName")).split()[0]

# Fix:
display_name = AulaProfileParser._parse_str(data.get("displayName"))
first_name = display_name.split()[0] if display_name.strip() else ""
```

---

### 3. Notification parser uses wrong field for folder_id
**Status: CONFIRMED (fix needs investigation)**

**File:** `custom_components/aula/aula_proxy/models/aula_notification_parser.py:43`

**Problem:** Uses `data.get("institutionCode")` (a string like "DK-12345") for `folder_id` (an int). `_parse_int()` will return `-1` for all notifications.

**Note from second review:** The suggested fix field `folderId` needs to be verified against the actual Aula API response structure. Check the response TypedDicts or actual API responses before fixing.

---

### 4. KeyError on missing CSRF token
**Status: CONFIRMED (fix needs adjustment)**

**File:** `custom_components/aula/aula_proxy/aula_proxy_client.py:60`

**Problem:** Direct dict key access `["Csrfp-Token"]` raises `KeyError` if the cookie is missing (e.g., login partially failed).

**Note from second review:** Suggested fix uses `AulaError` which does not exist. Use an existing exception class like `AulaCredentialError` or a plain `ConnectionError`.

```python
# Fix:
cookies = self._session.cookies.get_dict()
csrf_token = cookies.get("Csrfp-Token")
if not csrf_token:
    raise ConnectionError("Login failed: missing CSRF token")
```

---

## HIGH

### 5. No HTTP timeouts on any request
**Status: CONFIRMED**

**File:** `custom_components/aula/aula_proxy/aula_proxy_client.py` (24+ HTTP calls)

**Problem:** No `timeout` parameter on any `requests.Session` call. Can hang indefinitely, consuming a thread pool slot (via executor job) and potentially causing watchdog restarts.

```python
# Fix (consider separate connect/read timeouts):
response = self._session.get(url, headers=headers, timeout=(10, 30))
```

---

### 6. Bare `except:` swallows all exceptions
**Status: CONFIRMED**

**File:** `custom_components/aula/aula_proxy/aula_proxy_client.py:84`

**Problem:** Catches `KeyboardInterrupt`, `SystemExit`, `MemoryError`, etc.

**Note from second review:** `JSONDecodeError` is a subclass of `ValueError`, so catching both is redundant but explicit and harmless.

```python
# Fix:
except (json.JSONDecodeError, ValueError):
    responsedata = {"raw_response": response.text}
```

---

### 7. `connection_check()` never returns a value
**Status: CONFIRMED (low impact)**

**File:** `custom_components/aula/aula_client.py:33-42`

**Problem:** Return type is `Exception | None` but method never explicitly returns.

**Note from second review:** Works correctly by accident -- callers catch exceptions and never check the return value. Fix is cosmetic: change return type to `-> None`.

---

## MEDIUM

### 8. Retry logic doesn't handle connection errors
**Status: CONFIRMED (enhancement, not bug)**

**File:** `custom_components/aula/aula_proxy/aula_proxy_client.py:973-984`

**Problem:** `_should_retry_request()` only retries on HTTP status codes. Connection errors (`ConnectionError`, `Timeout`) raise exceptions before a `Response` exists, bypassing retry logic entirely. These surface as unhandled exceptions caught by the coordinator's error handling.

---

### 9. `.json()` calls without error handling
**Status: CONFIRMED**

**File:** `custom_components/aula/aula_proxy/aula_proxy_client.py` (lines 110, 236, 266, 295, 341, 383, 415, 448, 485, 518, 564, 814, 847)

**Problem:** 13+ calls to `response.json()` that can raise `JSONDecodeError` if the API returns non-JSON (e.g., HTML error page, 502 gateway response). Most are preceded by status code checks, reducing likelihood but not eliminating risk.

---

### 10. Wrong log message in notifications method
**Status: CONFIRMED**

**File:** `custom_components/aula/aula_proxy/aula_proxy_client.py:522`

**Problem:** Log message says `"method=messaging.getMessagesForThread response: ..."` but this is in the notifications method. Copy-paste error. Trivial fix.

---

## REMOVED (disproven by second review)

### ~~IndexError on `_parse_int_list()` with empty list~~
**Status: INCORRECT** - The outer check `if value and isinstance(value, list)` already guards against empty lists. An empty list `[]` is falsy, so `isinstance(value[0], int)` is never reached.

### ~~Potential IndexError on `meta.keys[0]`~~
**Status: INCORRECT** - Listener lifecycle guarantees non-empty keys. `async_remove_*_key` methods remove the entire listener entry when `len(meta.keys) == 0`, so any listener in the dict is guaranteed to have at least one key.
