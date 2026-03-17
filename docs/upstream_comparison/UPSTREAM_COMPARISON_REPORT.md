# Upstream Comparison Report: scaarup/aula vs HairingX/aula

**Date:** 2026-03-17
**Upstream:** scaarup/aula (upstream/main at a551ba2)
**Fork:** HairingX/aula (main at 8a53fe4)
**Common ancestor:** 2bcedd0

---

## Executive Summary

The upstream repository has undergone a **fundamental authentication rewrite** from UniLogin (username/password via BeautifulSoup form scraping) to **MitID OAuth 2.0/OIDC + SAML** authentication. This is the single most critical change. Our fork still uses the old UniLogin flow, which **will stop working** (or may have already stopped) as Aula providers migrate away from UniLogin to MitID.

### Critical Findings

| # | Issue | Severity | Our Status |
|---|-------|----------|------------|
| 1 | **MitID Authentication** - Complete auth rewrite | **CRITICAL** | NOT IMPLEMENTED - We still use UniLogin |
| 2 | API Version v19 vs v22 | HIGH | We use v19 (aula_proxy/const.py), upstream uses v22 |
| 3 | Token-based session management (OAuth tokens + refresh) | HIGH | NOT IMPLEMENTED - We use cookie sessions |
| 4 | Missing dependencies (pycryptodome, qrcode, requests) | HIGH | Missing from manifest.json |
| 5 | Calendar unload crash when schoolschedule disabled | LOW | We always unload Calendar platform (same potential bug) |
| 6 | lxml version constraint | LOW | We use unpinned "lxml", upstream uses "lxml>=5.3.0" |

---

## 1. CRITICAL: MitID Authentication Rewrite

### What Upstream Changed

Upstream completely replaced the authentication system across **4 major PRs**:

1. **PR #286** (`aeb32c3`) - "Change authentication flow to MitID" - Initial rewrite
2. **PR #293** (`f79c3c5`) - "Optimize login flow and refresh token process" - Iteration 2
3. **PR #292** (`301a5ea`) - "MitID token login" - Added TOKEN auth method (code token device)
4. **PR #296** (`784d6c6`) - Bug fixes: S4 combination ID, 'name' KeyError, multiple companies

### New Files Added (We Don't Have ANY of These)

```
custom_components/aula/aula_login_client/__init__.py
custom_components/aula/aula_login_client/client.py              (1697 lines!)
custom_components/aula/aula_login_client/exceptions.py
custom_components/aula/aula_login_client/mitid_browserclient/BrowserClient.py
custom_components/aula/aula_login_client/mitid_browserclient/CustomSRP.py
custom_components/aula/aula_login_client/mitid_browserclient/Helpers.py
custom_components/aula/aula_login_client/mitid_browserclient/__init__.py
custom_components/aula/aula_login_client/mitid_browserclient/login_flows/__init__.py
custom_components/aula/aula_login_client/mitid_browserclient/login_flows/aula.py
custom_components/aula/views.py                                  (Web UI for MitID QR/identity)
```

### Upstream Authentication Flow (NEW - MitID OAuth 2.0)

```
1. OAuth 2.0 Authorization (PKCE) → login.aula.dk/simplesaml/module.php/oidc/authorize.php
2. SAML redirect chain → broker.unilogin.dk → nemlog-in.mitid.dk
3. MitID Initialize → nemlog-in.mitid.dk/login/mitid/initialize
4. MitID BrowserClient (SRP crypto) → User approves via MitID App OR code token
5. MitID Completion → nemlog-in.mitid.dk/login/mitid (POST with auth code)
6. Identity selection (if multiple) → Choose between profiles
7. SAML broker flow → broker.unilogin.dk endpoint → role selection ("KONTAKT")
8. SAML response to Aula → login.aula.dk/simplesaml/module.php/saml/sp/saml2-acs.php
9. OAuth callback → Extract authorization code from redirect
10. Token exchange → login.aula.dk/simplesaml/module.php/oidc/token.php
11. API access → https://www.aula.dk/api/v22/?method=...&access_token=TOKEN
```

### Our Authentication Flow (OLD - UniLogin Form Scraping)

```
1. GET login.aula.dk/auth/login.php?type=unilogin
2. Parse HTML form → POST selectedIdp=uni_idp to broker.unilogin.dk
3. Loop through HTML forms filling username, password, selected-aktoer=KONTAKT
4. Follow redirects until reaching https://www.aula.dk:443/portal/
5. Session cookies used for all subsequent API calls
6. API access → https://www.aula.dk/api/v{VERSION}/?method=...  (cookie auth)
```

### Key Differences

| Aspect | Our Fork (UniLogin) | Upstream (MitID) |
|--------|-------------------|------------------|
| Auth method | Username + password form scraping | MitID App (QR) or Code Token |
| Session type | Cookie-based (`Csrfp-Token`) | OAuth 2.0 Bearer tokens (access + refresh) |
| Token refresh | Re-login when session expires | Refresh token grant |
| API auth | Cookie session | `?access_token=TOKEN` query param |
| Config flow | Simple username/password form | External step with web UI for QR code |
| API version | v19 | v22 |
| Dependencies | beautifulsoup4, lxml | beautifulsoup4, lxml, **pycryptodome**, **qrcode**, **requests** |

### Impact on Our Fork

**Our UniLogin flow (`aula_proxy_client.py:89-260`) will break** when Aula fully deprecates UniLogin. The `selectedIdp=uni_idp` form submission and username/password filling will no longer be an option.

---

## 2. Upstream Config Flow Rewrite

### Upstream (NEW)

- **Config flow VERSION = 2** (ours is VERSION = 1)
- Uses `async_external_step()` to open a web page (`/api/aula/auth/{flow_id}`) showing MitID QR code
- Background async authentication with status polling
- Stores OAuth tokens (`access_token`, `refresh_token`, `token_expires_at`) in config entry
- Supports identity selection when user has multiple profiles
- Has `async_step_reauth` for token renewal
- New views.py provides 3 HTTP endpoints:
  - `/api/aula/auth/{flow_id}` - HTML page with QR code display
  - `/api/aula/auth/{flow_id}/status` - JSON status polling
  - `/api/aula/auth/{flow_id}/select_identity` - Identity selection POST

### Our Fork (CURRENT)

- Config flow VERSION = 1
- Simple form with username + password fields
- Synchronous `_check_connection()` call to validate credentials
- Stores `username` and `password` in config entry
- Has `async_step_reconfigure` and `async_step_reauth` for credential updates
- No web UI views, no external step

### New Constants Upstream Has That We Don't

```python
CONF_MITID_USERNAME = "mitid_username"
CONF_MITID_PASSWORD = "mitid_password"
CONF_MITID_TOKEN = "mitid_token"
CONF_AUTH_METHOD = "auth_method"
CONF_MITID_IDENTITY = "mitid_identity"
CONF_MITID_USE_TOKEN = "mitid_use_token"
AUTH_METHOD_APP = "APP"
AUTH_METHOD_TOKEN = "TOKEN"
CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_TOKEN_EXPIRES_AT = "token_expires_at"
CONF_TEACHER_FULL_NAME = "teacher_full_name"
CONF_SCHOOLSCHEDULE = "schoolschedule"
CONF_UGEPLAN = "ugeplan"
CONF_MU_OPGAVER = "mu_opgaver"
```

---

## 3. Upstream `__init__.py` Changes

### Token Management in Entry Setup

Upstream's `async_setup_entry` now:
- Extracts stored OAuth tokens from config entry data
- Creates `Client` with token storage and HA references for persistence
- Calls `client.login()` which checks/refreshes tokens before full re-auth
- Has `async_update_tokens()` that stores tokens in **runtime storage only** (not config entry data) to prevent reload cycles

### Unavailable Flipping Fix (PR #303, commit `418cc93`)

Added runtime token storage and non-blocking token persistence:
- Token refresh uses a `threading.Lock()` to prevent concurrent refresh attempts
- `async_update_tokens` now writes to `hass.data` (runtime) not `entry.data` (persistent)
- Token persistence is scheduled as background task, never blocks coordinator

### Calendar Unload Fix (PR #300, commit `17315b4`)

```python
# BEFORE (bug):
platforms_to_unload = ["sensor", "binary_sensor", "calendar"]

# AFTER (fix):
platforms_to_unload = ["sensor", "binary_sensor"]
if entry.data.get(CONF_SCHOOLSCHEDULE, True):
    platforms_to_unload.append("calendar")
```

**Our status:** We always include `Platform.CALENDAR` in PLATFORMS list. This could crash if calendar platform was never set up. However, our architecture is different enough that this may not be a direct issue.

---

## 4. Upstream `client.py` Changes

Upstream's client.py was heavily rewritten:
- No longer uses cookie-based sessions
- Uses `AulaLoginClient` for authentication
- Passes `access_token` as query parameter to all API calls
- Has `_ensure_valid_token()` with thread-safe lock and graceful error handling
- Token refresh is non-blocking and writes to runtime storage
- `_verify_api_access()` loops through API versions (like we do) but uses token auth

---

## 5. Bug Fixes in Detail

### 5a. Fix "No such combination ID (S4)" - commit `9894861`

In `BrowserClient.py`, the MitID combination ID mapper was missing S4:

```python
# ADDED:
case "S4":  # App + MitID chip
    return "APP"
```

**Our status:** N/A - we don't have MitID BrowserClient. Will need this when implementing MitID.

### 5b. Fix "Authentication failed: 'name'" - commit `260da4c`

In `aula_login_client/client.py`, the identity selection form parsing had a KeyError:

```python
# BEFORE (bug):
data[soup_input["name"]] = soup_input["value"]  # KeyError when input has no "name"

# AFTER (fix):
try:
    name = soup_input["name"]
except:
    continue  # Skip inputs without name attribute
try:
    data[name] = soup_input["value"]
except:
    data[name] = ""
```

**Our status:** N/A - we don't have this identity selection code. Will need this when implementing MitID.

### 5c. Support Multiple Companies + Details - commit `7ca7e3f`

Changed identity selection to:
- Use `a.list-link` selector (instead of `div.list-link-box`)
- Include `div.link-list-detail` text in identity name
- Simplified `data-loginoptions` extraction

**Our status:** N/A - same as above.

### 5d. Teacher Full Name Config - PR #294, commit `c404f17`

Added `CONF_TEACHER_FULL_NAME` config option to show teacher full names instead of initials in school schedule calendar. Changes in `calendar.py`, `const.py`, `config_flow.py`, and translations.

**Our status:** We don't have this feature. Low priority - nice-to-have.

### 5e. lxml Version Constraint - PR #314

Changed from pinned `lxml==5.3.0` to `lxml>=5.3.0` for HA 2026.3 compatibility.

**Our status:** We use unpinned `"lxml"` in manifest.json. This is actually fine but less explicit.

### 5f. Post-Broker-Login Fix - commit `b5616b4`

Major fix for the SAML broker flow. The `_process_broker_response` method was heavily enhanced with:
- Form data extraction and role selection (`selected-aktoer=KONTAKT`)
- Handling intermediate confirmation pages
- Better redirect following
- Debug logging throughout

**Our status:** N/A - we don't have this MitID flow yet.

---

## 6. API Version Difference

| | Our Fork | Upstream |
|---|----------|----------|
| `const.py` API_VERSION | `"19"` | `"22"` |
| Main `const.py` API_VERSION | `"19"` (in main const.py) | `"22"` |
| `aula_proxy/const.py` API_VERSION | `"22"` | N/A (doesn't have aula_proxy) |

**Note:** Our main `const.py` says v19 but our `aula_proxy/const.py` says v22. The proxy client uses the proxy const. The main const.py v19 is unused in our architecture.

---

## 7. Dependency Differences

### Our manifest.json
```json
{
    "requirements": ["beautifulsoup4", "lxml"],
    "version": "0.1.9"
}
```

### Upstream manifest.json
```json
{
    "requirements": [
        "beautifulsoup4==4.12.3",
        "lxml>=5.3.0",
        "pycryptodome>=3.19.0",
        "qrcode>=7.4.0",
        "requests>=2.31.0"
    ],
    "version": "0.1.59"
}
```

**New dependencies needed for MitID:**
- `pycryptodome>=3.19.0` - For SRP (Secure Remote Password) crypto in MitID BrowserClient
- `qrcode>=7.4.0` - For generating MitID QR codes displayed in the web UI
- `requests>=2.31.0` - Explicit pinning (we already use requests implicitly)

---

## 8. File Structure Comparison

### Files Only in Upstream (NEW)
```
aula_login_client/__init__.py
aula_login_client/client.py
aula_login_client/exceptions.py
aula_login_client/mitid_browserclient/BrowserClient.py
aula_login_client/mitid_browserclient/CustomSRP.py
aula_login_client/mitid_browserclient/Helpers.py
aula_login_client/mitid_browserclient/__init__.py
aula_login_client/mitid_browserclient/login_flows/__init__.py
aula_login_client/mitid_browserclient/login_flows/aula.py
views.py
services.yaml
binary_sensor.py
```

### Files Only in Our Fork (OUR ADDITIONS)
```
aula_proxy/  (entire directory - our clean architecture rewrite)
  aula_proxy_client.py
  aula_errors.py
  const.py
  models/ (all dataclass models and parsers)
  responses/ (typed response definitions)
  test_messages.py
  utils/
aula_client.py
aula_data.py
aula_data_coordinator.py
aula_calendar_coordinator.py
entity.py
module.py
_original_client.py
```

### Files in Both (DIVERGED)
```
__init__.py          - Completely different architectures
config_flow.py       - Completely different (username/password vs MitID)
const.py             - Different constants
manifest.json        - Different deps and version
sensor.py            - Likely diverged
calendar.py          - Likely diverged
binary_sensor.py     - Likely diverged
strings.json         - Different (MitID fields vs username/password)
translations/da.json - Different
translations/en.json - Different
```

---

## 9. Recommendations

### CRITICAL: MitID Migration Strategy

Since we have significantly rewritten the architecture (typed dataclasses, coordinators, entity base classes), we should NOT simply merge upstream. Instead:

1. **Port the `aula_login_client/` package** as-is from upstream (it's self-contained)
2. **Port the `mitid_browserclient/` package** as-is (pure MitID crypto, self-contained)
3. **Adapt our `aula_proxy_client.py`** to accept OAuth tokens instead of username/password
4. **Rewrite our `config_flow.py`** to use MitID external step flow
5. **Add `views.py`** for the QR code web UI
6. **Update `manifest.json`** with new dependencies
7. **Update `const.py`** with MitID-related constants
8. **Handle migration** from config flow VERSION 1 (username/password) to VERSION 2 (MitID tokens)

### Integration Approach

The key architectural insight is that upstream separated concerns well:
- `aula_login_client/` handles ALL authentication (self-contained, ~2500 lines total)
- `client.py` uses the login client and manages tokens
- `views.py` provides the HA web UI

We can adapt this to our architecture:
- `aula_login_client/` -> Copy as-is
- Our `aula_proxy_client.py` login method -> Replace UniLogin scraping with token-based API calls
- Our `config_flow.py` -> Rewrite for MitID flow
- Our `__init__.py` -> Add token management

### What We Should NOT Lose

Our fork has significant improvements over upstream that we must preserve:
- Typed dataclass models with dedicated parsers
- CoordinatorEntity-based entities with proper update cycles
- Separated data/calendar coordinators with different intervals
- Widget detection system
- Clean error handling hierarchy
- Unit test framework with JSON fixtures
