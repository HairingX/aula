# Migration Plan: Adopting MitID Authentication

## Strategy

The upstream MitID auth lives in a standalone package (`aula_login_client/`) with no dependencies on the upstream `client.py`. Our strategy should be to **adopt the auth package** while **keeping our superior typed architecture**.

This is NOT a full upstream merge. It's a targeted adoption of the authentication layer.

## Phase 1: Port `aula_login_client/` Package (Critical)

### 1.1 Copy the auth package
Copy the entire `aula_login_client/` directory from upstream:
```
custom_components/aula/aula_login_client/
    __init__.py
    client.py              (~1410 lines - OAuth/SAML/token flow)
    exceptions.py          (custom exception hierarchy)
    mitid_browserclient/
        __init__.py
        BrowserClient.py   (~770 lines - MitID SRP protocol)
        CustomSRP.py       (~158 lines - SRP implementation)
        Helpers.py          (~95 lines - auth helpers)
        login_flows/
            __init__.py
            aula.py         (~473 lines - standalone login flow)
```

### 1.2 Add HTTP views
Copy `views.py` (~203 lines) for the MitID auth UI (QR code page, status polling, identity selection).

### 1.3 Add dependencies to manifest.json
```json
"requirements": [
    "beautifulsoup4",
    "lxml",
    "pycryptodome>=3.19.0",
    "qrcode>=7.4.0",
    "requests>=2.31.0"
]
```

### 1.4 Include all upstream fixes
Ensure the ported code includes ALL fixes from:
- PR #293 (iteration 2 hardening)
- PR #296 (S4, name fix, multiple companies)
- PR #292 (hardware token login) - with bug fixes applied
- All post-broker-login fixes (commits ba72ef9 through b5616b4)

## Phase 2: Adapt Config Flow

### 2.1 Rewrite config_flow.py
- Bump VERSION to 2
- Replace UniLogin form with MitID external auth step
- Add `async_step_authenticate` with external step pattern
- Add `async_step_complete` for config entry creation
- Update reauth/reconfigure flows for MitID
- Add migration logic for VERSION 1 -> 2 entries

### 2.2 Update strings.json and translations
- Replace UniLogin labels with MitID labels
- Add authenticate, select_identity, complete steps
- Add auth_failed, api_error error messages
- Add reauth_successful abort reason
- Update both `en.json` and `da.json`

## Phase 3: Adapt AulaProxyClient Login

### 3.1 Replace login mechanism in `aula_proxy_client.py`
The current `login()` method scrapes UniLogin HTML forms. Replace with:

**Option A: Direct token injection**
- `AulaLoginClient` handles full MitID auth and returns access_token
- Pass token to `AulaProxyClient` which uses it as query parameter
- Remove BeautifulSoup login scraping code

**Option B: Token-to-session bridge**
- `AulaLoginClient` gets access_token
- Use token to establish an Aula session (if Aula supports this)
- Continue using session cookies for API calls

**Recommended: Option A** - cleaner, matches upstream approach.

### 3.2 Modify API call authentication
Currently our proxy client uses session cookies. Change to:
- Append `&access_token=<token>` to all API call URLs
- Do NOT set Authorization header (causes 400 errors)
- Remove cookie-based auth logic

### 3.3 Add token refresh to proxy client
- Store tokens received from `AulaLoginClient`
- Check `expires_at` before each API call
- Call `AulaLoginClient.renew_access_token()` when needed
- Use `threading.Lock` to prevent concurrent refresh (upstream fix from PR #303)
- Persist refreshed tokens to runtime storage (not config entry, to avoid entity unavailable flipping)

### 3.4 Handle CSRF token changes
- Make CSRF token optional (may not be available with token auth)
- Use `_get_csrf_token()` helper pattern from upstream

## Phase 4: Update __init__.py

### 4.1 Token storage setup
```python
async def async_setup_entry(hass, entry):
    # Store initial tokens from config entry
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "tokens": {
            "access_token": entry.data.get(CONF_ACCESS_TOKEN),
            "refresh_token": entry.data.get(CONF_REFRESH_TOKEN),
            "expires_at": entry.data.get(CONF_TOKEN_EXPIRES_AT),
        }
    }
    # ... rest of setup
```

### 4.2 Token update callback
```python
async def async_update_tokens(new_tokens):
    # Update runtime storage (NOT entry.data to avoid reload cycle)
    hass.data[DOMAIN][entry.entry_id]["tokens"] = new_tokens
    # Fire-and-forget persistence to config entry for restart survival
    hass.config_entries.async_update_entry(entry, data={**entry.data, **new_tokens})
```

### 4.3 Pass token callback to client
The proxy client needs a way to persist refreshed tokens back to HA.

## Phase 5: Update Constants

### 5.1 Add MitID constants to const.py
```python
CONF_MITID_USERNAME = "mitid_username"
CONF_MITID_PASSWORD = "mitid_password"
CONF_AUTH_METHOD = "auth_method"
CONF_MITID_IDENTITY = "mitid_identity"
CONF_MITID_TOKEN = "mitid_token"
CONF_MITID_USE_TOKEN = "mitid_use_token"
AUTH_METHOD_APP = "APP"
AUTH_METHOD_TOKEN = "TOKEN"
CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_TOKEN_EXPIRES_AT = "token_expires_at"
```

### 5.2 Align API_VERSION
Update outer `const.py` to `API_VERSION = "22"` for consistency with `aula_proxy/const.py`.

## Phase 6: Testing

### 6.1 Unit tests
- Test `AulaLoginClient` token refresh logic
- Test `AulaProxyClient` with token-based auth
- Test config flow migration (v1 -> v2)
- Test token persistence and recovery

### 6.2 Integration testing
- Test full MitID app login flow
- Test MitID hardware token login flow
- Test multiple identity selection
- Test token refresh (wait for expiration)
- Test HA restart with stored tokens
- Test entity availability during token refresh

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| UniLogin may still be needed during transition | Keep old login as fallback behind config option |
| MitID SRP protocol changes | Pin pycryptodome version, monitor upstream |
| Token refresh race conditions | Use threading.Lock (upstream pattern) |
| Entity unavailable during refresh | Update runtime storage, not config entry |
| Config entry migration failures | Thorough v1->v2 migration with error handling |
| QR code / views security | Validate session tokens in HTTP views |

## Priority Order

1. **Phase 1** - Port auth package (blocks everything else)
2. **Phase 2** - Config flow (needed for user-facing auth)
3. **Phase 3** - Proxy client adaptation (needed for API calls)
4. **Phase 4** - Init/token storage (needed for persistence)
5. **Phase 5** - Constants (quick, do alongside others)
6. **Phase 6** - Testing (ongoing throughout)

## Estimated Scope

- ~2500 lines of new code to port (auth package + views)
- ~300 lines of config flow rewrite
- ~200 lines of proxy client modifications
- ~100 lines of init/const changes
- Total: ~3100 lines of changes
