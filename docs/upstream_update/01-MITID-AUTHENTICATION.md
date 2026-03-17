# MitID Authentication - Upstream Changes Analysis

## Background

Denmark is transitioning from UniLogin to MitID for authentication across public services, including Aula (the school/institution platform). The upstream repo has implemented full MitID support across multiple PRs.

## Timeline of Upstream MitID Changes

### PR #286 - Initial MitID Authentication (commit `aeb32c3`)
**"Change authentication flow to MitID"**

The foundational change. Replaces the entire UniLogin username/password scraping-based auth with MitID OAuth 2.0/OIDC/SAML flow.

#### New Files Added

| File | Lines | Purpose |
|------|-------|---------|
| `aula_login_client/__init__.py` | ~10 | Package init, exports `AulaLoginClient` and exceptions |
| `aula_login_client/client.py` | ~1410 | Main auth client: OAuth 2.0 PKCE, SAML redirect chain, MitID BrowserClient integration, token exchange/refresh/validation |
| `aula_login_client/exceptions.py` | ~30 | Custom exceptions: `AulaAuthenticationError`, `MitIDError`, `TokenExpiredError`, `APIError`, `ConfigurationError`, `NetworkError`, `SAMLError`, `OAuthError` |
| `aula_login_client/mitid_browserclient/BrowserClient.py` | ~770 | Simulates MitID browser client, handles SRP protocol, app/token/password authenticators |
| `aula_login_client/mitid_browserclient/CustomSRP.py` | ~158 | Custom SRP (Secure Remote Password) implementation for MitID |
| `aula_login_client/mitid_browserclient/Helpers.py` | ~95 | Helper functions: auth code extraction, NemLogin parameter generation, identity selection |
| `aula_login_client/mitid_browserclient/login_flows/aula.py` | ~473 | Standalone login flow script for Aula via MitID |
| `views.py` | ~203 | Three HA HTTP views: `AulaAuthView` (HTML page with QR code and status polling), `AulaAuthStatusView` (JSON status endpoint), `AulaAuthSelectIdentityView` (identity selection POST endpoint) |

#### Key Changes to Existing Files

**`const.py`** - Added constants:
```python
CONF_MITID_USERNAME = "mitid_username"
CONF_MITID_PASSWORD = "mitid_password"
CONF_AUTH_METHOD = "auth_method"
CONF_MITID_IDENTITY = "mitid_identity"
AUTH_METHOD_APP = "APP"
AUTH_METHOD_TOKEN = "TOKEN"
CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_TOKEN_EXPIRES_AT = "token_expires_at"
# API_VERSION bumped from "20" to "22"
```

**`__init__.py`** - Complete rewrite:
- Extracts MitID credentials and stored tokens from config entry
- Creates `Client` with token-based auth
- Adds `async_update_tokens()` for persisting refreshed tokens to config entry
- Creates client in `async_setup_entry` and performs login before forwarding platforms

**`config_flow.py`** - Complete rewrite (VERSION = 2):
- Multi-step flow using HA's `async_external_step` pattern
- `async_step_user` collects MitID username and feature flags
- `async_step_authenticate` opens browser auth page with QR code
- `_authenticate_async` runs `AulaLoginClient.authenticate()` in background
- `_monitor_client_status` polls MitID client status
- Uses `concurrent.futures.Future` for identity selection callback
- Adds `async_step_reauth` and `async_step_reconfigure` flows
- Removes old UniLogin `CONF_USERNAME`/`CONF_PASSWORD` schema

**`client.py`** (upstream's equivalent of our `aula_proxy_client.py`) - Major rewrite:
- Constructor takes `mitid_username`, `auth_method`, `mitid_password`, `stored_tokens`, `mitid_identity`, `hass`, `config_entry`
- Creates `AulaLoginClient` internally
- New `login()`: checks stored tokens -> tries refresh via `renew_access_token()` -> falls back to full MitID auth
- Token passed as `&access_token=` query parameter (NOT Authorization header)
- New methods: `_apply_token_to_session()`, `_verify_api_access()`, `_ensure_valid_token()`, `_get_access_token_param()`

**`manifest.json`** - Added dependencies:
```json
"pycryptodome>=3.19.0",
"qrcode>=7.4.0",
"requests>=2.31.0"
```

---

### PR #293 - MitID Iteration 2: Optimization (commits `e667c69`, `5868510`, `8b57512`)

**`e667c69` - "Optimize login flow and refresh token process":**
- Added `_get_csrf_token()` helper that safely gets CSRF token (returns None instead of crashing)
- Made CSRF token optional in headers throughout
- Added token expiration time logging
- `aula_login_client/client.py`: Added `expires_at` timestamp calculation from `expires_in`
- `__init__.py`: Rewrote `async_unload_entry` to use `async_unload_platforms()` with all 3 platforms
- `config_flow.py`: Extracted config entry creation into `async_step_complete` (because `async_external_step` can only transition to `async_external_step_done`)

**`5868510` - Client hardening:**
- Removed `Authorization` header from `_apply_token_to_session()` - Aula uses query params, setting both causes 400 errors
- Added max version attempts loop guard
- Added 400 Bad Request handling
- Added null-safe JSON parsing throughout (`.get()` chains instead of direct key access)
- Defensive coding for profile context, widgets, message threads, daily overview

**`8b57512` - Minor fixes:**
- Fixed reference to `self._username` -> `self._mitid_username` in Meebook API calls
- Fixed early return when school schedule is disabled

---

### Auth Flow Debugging & Fixes (commits `ba72ef9` through `b5616b4`)

Iterative debugging of the post-broker-login redirect handling:

| Commit | Change |
|--------|--------|
| `ba72ef9` | Added parameter logging before `post-broker-login` POST |
| `454475e` | Added logging of broker redirect URLs and form details |
| `84c7d23` | **Critical fix**: Extract form action URL from broker response HTML instead of constructing manually. Submit actual form data instead of empty POST. |
| `ad9ef02` | Added full page HTML logging, select/button inspection |
| `e84f225` | Changed broker redirect to use `allow_redirects=True` to follow full redirect chain |
| `2be63f5` | **Key fix**: If broker response contains role selection form (`selected-aktoer`), auto-set to `'KONTAKT'` (guardian role) |
| `ea3ea1c` | Complete Black formatting pass + accumulated fixes. Handle intermediate confirmation pages (200 OK responses from post-broker-login with additional forms) |
| `ce15889` | Changed 21 log calls from INFO to DEBUG to reduce noise |
| `b5616b4` | Merge commit combining all above fixes |

---

### PR #296 - S4 Combination ID + Auth Name Fixes

**`9894861` - Fix "No such combination ID (S4)":**
- `BrowserClient.py`: Added `case "S4"` (App + MitID chip) mapping to `"APP"` authenticator

**`260da4c` - Fix "Authentication failed: 'name'":**
- `aula_login_client/client.py`: Fixed crash when `<input>` tag has no `name` attribute during NemLogin identity page parsing

**`7ca7e3f` - "Support multiple companies + adding details":**
- Changed identity option CSS selector from `div.list-link-box` to `a.list-link`
- Added company detail text (`div.link-list-detail`) to identity names
- Fixed `ChosenOptionJson` extraction to read from `<a>` tag's `data-loginoptions` attribute

---

### PR #292 - MitID Token Login (by jballe)

Adds support for MitID hardware token (code device) authentication as alternative to app-based auth.

**New constants:**
```python
CONF_MITID_TOKEN = "mitid_token"
CONF_MITID_USE_TOKEN = "mitid_use_token"
```

**Config flow changes:**
- Added `CONF_MITID_USE_TOKEN`, `CONF_MITID_PASSWORD`, `CONF_MITID_TOKEN` to AUTH_SCHEMA
- If `mitid_use_token` is True, sets `auth_method = AUTH_METHOD_TOKEN`
- **Known bugs in this PR:** `_LOGGER.inf` (typo for `.info`), `user_input.password` / `user_input.token` (should be `user_input.get(...)`)

**`BrowserClient.py`**: If `auth_method == "TOKEN"`, uses hardware token code instead of app approval.

---

## How MitID Auth Flow Works (Technical)

```
1. User enters MitID username in HA config flow
2. HA opens external auth page (views.py -> AulaAuthView)
   - Shows QR code for MitID app
   - Polls for status via AulaAuthStatusView
3. Background: AulaLoginClient.authenticate() runs
   a. OAuth 2.0 PKCE authorization request to Aula
   b. Redirect to NemLogin (Danish national identity provider)
   c. NemLogin redirects to MitID
   d. BrowserClient simulates MitID SRP protocol
      - SRP (Secure Remote Password) key exchange
      - App/Token/Password authenticator selection
   e. MitID approval -> auth code
   f. Auth code exchange for access_token + refresh_token
4. Tokens stored in config entry
5. On each API call: access_token appended as query param
6. Token refresh: automatic via refresh_token before expiry
```

## Impact on Our Fork

Our fork currently uses UniLogin authentication (`aula_proxy_client.py` login method):
1. Navigates to `https://login.aula.dk/auth/login.php?type=unilogin`
2. Scrapes HTML forms with BeautifulSoup
3. Submits username/password to UniLogin broker
4. Follows redirects back to Aula
5. Extracts session cookies

**When UniLogin is deprecated, our login will completely stop working.**

The upstream `aula_login_client/` package is essentially standalone and could potentially be adapted to work with our proxy client architecture, replacing only the login mechanism while keeping our typed models, parsers, and coordinators.

## Key Technical Notes for Porting

1. Token is passed as `&access_token=` query parameter, NOT as Authorization header (setting both causes 400 errors)
2. CSRF token (`Csrfp-Token`) may become optional/unavailable with the new auth
3. The `aula_login_client/` package has no dependency on the upstream `client.py` - it's a standalone auth module
4. New dependencies required: `pycryptodome>=3.19.0`, `qrcode>=7.4.0`
5. Config flow VERSION must be bumped to 2 with migration logic
6. HA's `async_external_step` pattern requires HTTP views registered via `after_dependencies: ["http"]`
7. `views.py` serves an HTML page with inline JavaScript for QR code display and status polling
