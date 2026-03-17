# Authentication Flow

## Overview

Aula uses **UniLogin** (Danish single sign-on for schools) for authentication. Since Aula does not offer a public API with OAuth/API keys, the integration simulates a browser login by navigating through HTML login forms with BeautifulSoup.

## Login Process (Step-by-Step)

```
┌──────────────────────────────────────────────────────────────────┐
│ STEP 1: Check existing session                                   │
│                                                                  │
│ GET aula.dk/api/v22?method=profiles.getProfilesByLogin           │
│ → If status == "OK": Reuse session, return cached profiles       │
│ → Otherwise: Continue to step 2                                  │
└──────────────────────────────┬───────────────────────────────────┘
                               │ session expired
                               v
┌──────────────────────────────────────────────────────────────────┐
│ STEP 2: Initiate login                                           │
│                                                                  │
│ GET https://login.aula.dk/auth/login.php?type=unilogin           │
│ Headers: Simulated Firefox browser (User-Agent, Accept, etc.)    │
│ → Receives HTML with login form                                  │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               v
┌──────────────────────────────────────────────────────────────────┐
│ STEP 3: Select UniLogin                                          │
│                                                                  │
│ Parse HTML with BeautifulSoup → find form action URL             │
│ POST to broker.unilogin.dk with selectedIdp=uni_idp              │
│ → Selects UniLogin over MitID or local login                     │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               v
┌──────────────────────────────────────────────────────────────────┐
│ STEP 4: Navigate login forms (loop, max 10 redirects)            │
│                                                                  │
│ For each form:                                                   │
│   1. Parse HTML with BeautifulSoup                               │
│   2. Find all <input> fields with name/value                     │
│   3. Fill with user data:                                        │
│      - username                                                  │
│      - password                                                  │
│      - selected-aktoer = "KONTAKT" (parent role)                │
│   4. POST the form                                               │
│   5. Check for errors:                                           │
│      - "brugernavn"/"user" + "ugyldig"/"invalid" → error        │
│      - "kode"/"password" + "forkert"/"wrong" → error            │
│   6. Check if redirect ends at aula.dk/portal/ → success        │
│                                                                  │
│ Typical flow: username page → password page → actor selection    │
└──────────────────────────────┬───────────────────────────────────┘
                               │ redirect to aula.dk/portal/
                               v
┌──────────────────────────────────────────────────────────────────┐
│ STEP 5: Find correct API version                                 │
│                                                                  │
│ Start at API v22                                                 │
│ GET aula.dk/api/v{version}?method=profiles.getProfilesByLogin    │
│ → 200 OK: Parse profiles, continue                               │
│ → 410 GONE: Try version+1 (max 10 attempts)                     │
│ → 403 FORBIDDEN: Credentials rejected → AulaCredentialError     │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               v
┌──────────────────────────────────────────────────────────────────┐
│ STEP 6: Fetch profile context                                    │
│                                                                  │
│ GET ?method=profiles.getProfileContext&portalrole=guardian        │
│ → Sets userId on profiles and children                           │
│ → Fetches available widgets (features)                           │
│                                                                  │
│ GET ?method=profiles.getProfileMasterData&instProfileIds[]=...   │
│ → Sets main group (class) on children, e.g., "3A"               │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               v
┌──────────────────────────────────────────────────────────────────┐
│ RESULT: AulaLoginData                                            │
│                                                                  │
│ profiles: List[AulaProfile]  (parents with children)             │
│ widgets: List[AulaWidget]    (available features)                │
│ api_version: int             (correct API version)               │
└──────────────────────────────────────────────────────────────────┘
```

## Session Management

### Requests Session
- One `requests.Session()` instance per `AulaProxyClient`
- Automatically persists cookies between all calls
- Provides automatic session recognition at Aula

### CSRF Token
- Extracted from session cookies: `Csrfp-Token`
- Sent as header `csrfp-token` on all POST calls to the API
- Maintained automatically by the session object

## Widget Tokens

Certain features (Meebook weekly plans, MinUddannelse, EasyIQ) require separate tokens.

```
┌─────────────────────────────────────────────────────────────┐
│ Token Retrieval                                             │
│                                                             │
│ GET ?method=aulaToken.getAulaToken&widgetId={widget_id}     │
│ → Returns bearer token specific to the widget               │
│                                                             │
│ Caching:                                                    │
│ - Stored in _tokens[widget_id] = AulaToken(token, timestamp)│
│ - Reused if < 40 minutes old                                │
│ - Auto-refresh on expiry or 401 error                      │
│                                                             │
│ Usage:                                                      │
│ Authorization: Bearer {token}                               │
│ Sent to third-party APIs (Meebook, MinUddannelse, etc.)    │
└─────────────────────────────────────────────────────────────┘
```

## Error Handling During Login

| Situation | Error Type | Handling |
|-----------|-----------|---------|
| Invalid username | `AulaCredentialError` | Config flow shows "invalid_auth" |
| Invalid password | `AulaCredentialError` | Config flow shows "invalid_auth" |
| Login form not found | `ParseError` | Config flow shows "invalid_response" |
| API returns 403 | `AulaCredentialError` | Triggers re-auth flow |
| API returns 410 | Auto-increment version | Tries next API version |
| API version > 10 over baseline | `ConnectionRefusedError` | Gives up |
| HTML alert message found | `ConnectionAbortedError` | Shows error message |

## Security Considerations

- Credentials are stored in Home Assistant's config entry (encrypted by HA)
- Passwords are only sent over HTTPS
- Session cookies are stored only in memory (not persisted to disk)
- UniLogin passwords expire periodically (Aula requirement)
- User-Agent header simulates a real browser to avoid blocking
