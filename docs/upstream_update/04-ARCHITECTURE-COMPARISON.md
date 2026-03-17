# Architecture Comparison: Our Fork vs Upstream

## High-Level Architecture

### Our Fork (HairingX/aula)
```
Config Flow (UniLogin credentials)
    -> AulaClient (aula_client.py)
        -> AulaProxyClient (aula_proxy/aula_proxy_client.py)
            - HTTP client with BeautifulSoup login scraping
            - Session/cookie-based auth
            - Auto API version increment on 410
            -> Models (aula_proxy/models/) - @dataclass types
            -> Parsers (aula_proxy/models/) - JSON -> dataclass conversion
    -> Coordinators
        +-- AulaDataCoordinator (5 min) - profiles, daily overviews, messages, notifications
        +-- AulaCalendarCoordinator (10 min) - birthdays, events, weekly plans
    -> Entities
        +-- Sensors: status, presence, duration (typed AulaEntityBase[T])
        +-- Binary Sensors: unread messages/gallery/calendar/posts/presence
        +-- Calendars: events, birthdays, weekly plans
```

### Upstream (scaarup/aula)
```
Config Flow (MitID external auth with QR code)
    -> views.py (HTTP views for auth UI)
    -> AulaLoginClient (aula_login_client/)
        - OAuth 2.0 PKCE + SAML + SRP protocol
        - Token-based auth (access_token as query param)
        - Automatic token refresh
        -> mitid_browserclient/ (MitID protocol simulation)
    -> Client (client.py)
        - Monolithic HTTP client (~1100 lines)
        - Raw dict data access
        - DataUpdateCoordinator inline in sensor.py
    -> Entities
        +-- Sensors: single AulaSensor class, raw dict access
        +-- Binary Sensors: single AulaBinarySensor, message only
        +-- Calendar: reads skoleskema.json, single entity
```

## File-by-File Comparison

### Files Only in Our Fork
| File | Purpose |
|------|---------|
| `aula_proxy/` (entire directory) | Typed proxy client with models, parsers, responses, tests |
| `aula_client.py` | Wrapper around proxy client |
| `aula_data.py` | Shared data types |
| `aula_data_coordinator.py` | 5-min data update coordinator |
| `aula_calendar_coordinator.py` | 10-min calendar update coordinator |
| `entity.py` | Base entity classes with generics |
| `module.py` | Module-level utilities |
| `_original_client.py` | Reference copy of original upstream client |

### Files Only in Upstream
| File | Purpose |
|------|---------|
| `aula_login_client/` (entire directory) | MitID authentication package |
| `aula_login_client/client.py` (~1410 lines) | OAuth 2.0/OIDC/SAML auth client |
| `aula_login_client/exceptions.py` | Auth-specific exceptions |
| `aula_login_client/mitid_browserclient/` | MitID protocol implementation |
| `views.py` (~203 lines) | HTTP views for MitID auth UI |
| `client.py` (~1100 lines) | Monolithic API client |
| `tests/` | pytest-based tests |

### Files in Both (Significantly Different)

#### `__init__.py`
| Aspect | Our Fork | Upstream |
|--------|----------|----------|
| Platforms | SENSOR, BINARY_SENSOR, CALENDAR | SENSOR, BINARY_SENSOR, CALENDAR (conditional) |
| Client creation | AulaClient wrapping AulaProxyClient | Client with AulaLoginClient |
| Coordinators | 2 separate (data + calendar) | Inline in sensor.py |
| Token handling | Session cookies | OAuth tokens in runtime storage |
| Setup | Coordinator-first, then platforms | Client login, then platforms |

#### `config_flow.py`
| Aspect | Our Fork | Upstream |
|--------|----------|----------|
| VERSION | 1 | 2 |
| Auth method | UniLogin username/password form | MitID external step with web UI |
| Steps | user -> conf, reauth -> reconf | user -> authenticate -> complete, reauth -> reauth_confirm |
| Validation | AulaClient.connection_check() | AulaLoginClient.authenticate() |
| UI | Simple form (username, password, checkboxes) | External browser page with QR code |

#### `const.py`
| Aspect | Our Fork | Upstream |
|--------|----------|----------|
| API_VERSION | "19" (outer), "22" (proxy) | "22" |
| Auth constants | CONF_USERNAME, CONF_PASSWORD | CONF_MITID_USERNAME, CONF_MITID_PASSWORD, CONF_AUTH_METHOD, token constants |
| API URLs | Duplicated in outer and proxy const | Single location |

#### `sensor.py`
| Aspect | Our Fork | Upstream |
|--------|----------|----------|
| Entity classes | AulaStatusSensor, AulaPresenceSensor, AulaPresenceDurationSensor | Single AulaSensor |
| Base class | AulaEntityBase[T] (generic) | CoordinatorEntity directly |
| Data access | Typed dataclass models | Raw dict access |
| Coordinator | External AulaDataCoordinator | Inline DataUpdateCoordinator |

#### `binary_sensor.py`
| Aspect | Our Fork | Upstream |
|--------|----------|----------|
| Entities | 5 types (messages, gallery, calendar, posts, presence) | 1 type (messages only) |
| Base class | AulaEntityBase[T] (generic) | CoordinatorEntity directly |
| Data access | Typed models | Raw dict access |

#### `calendar.py`
| Aspect | Our Fork | Upstream |
|--------|----------|----------|
| Entities | 3 types (events, birthdays, weekly plans) | 1 type (school schedule) |
| Data source | API via coordinator | skoleskema.json file |
| Coordinator | External AulaCalendarCoordinator | None (file-based) |

#### `manifest.json`
| Aspect | Our Fork | Upstream |
|--------|----------|----------|
| Version | 0.1.9 | 0.1.59 |
| Requirements | beautifulsoup4, lxml | beautifulsoup4==4.12.3, lxml>=5.3.0, pycryptodome, qrcode, requests |
| Codeowners | @hairingx | @scaarup |

## What We Have That Upstream Doesn't

1. **Typed data models** - Full @dataclass models for all Aula data types
2. **Parser layer** - Clean JSON-to-dataclass conversion with error handling
3. **Dual coordinators** - Separate update intervals for data vs calendar
4. **Rich entity types** - 5 binary sensors, 3 calendar types, 3 sensor types
5. **Birthday calendar** - Dedicated birthday tracking with age display
6. **Weekly plan calendar** - Dedicated weekly plan entity
7. **Presence tracking** - Duration sensor, vacation binary sensor
8. **Widget detection** - `has_widget()` checks for feature availability
9. **Unit tests** - unittest framework with JSON fixtures
10. **Auto API version increment** - Graceful handling of API version deprecation

## What Upstream Has That We Don't

1. **MitID authentication** - The critical missing piece
2. **Token-based auth** - OAuth tokens instead of session cookies
3. **Token refresh** - Automatic, non-disruptive token renewal
4. **External auth UI** - QR code display for MitID app approval
5. **Multiple identity support** - Selecting between companies/institutions
6. **Hardware token support** - MitID code device authentication
7. **Teacher full name option** - Config option for school schedule display
