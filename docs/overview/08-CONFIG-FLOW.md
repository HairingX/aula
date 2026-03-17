# Config Flow

## Overview

The config flow handles three scenarios:
1. **Initial setup** - New integration installation
2. **Reconfiguration** - Updating credentials for an existing installation
3. **Re-authentication** - Triggered automatically when credentials expire

## Flow Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    INITIAL SETUP                              │
│                                                              │
│  async_step_user()                                           │
│       │                                                      │
│       v                                                      │
│  async_show_configure() → Shows form:                        │
│       │   - Entity ID (unique identifier)                    │
│       │   - Username (UniLogin)                              │
│       │   - Password                                         │
│       │                                                      │
│       v                                                      │
│  async_step_conf()                                           │
│       │                                                      │
│       ├── Validate Entity ID (non-empty, unique)             │
│       ├── _async_try_set_username_password()                 │
│       │     ├── Validate username non-empty                  │
│       │     ├── Validate password non-empty                  │
│       │     └── _check_connection() via executor             │
│       │           └── AulaClient.connection_check()          │
│       │                                                      │
│       ├── On success: Create config entry                    │
│       └── On error: Show form again with error message       │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    RECONFIGURATION                            │
│                                                              │
│  User clicks "Reconfigure" in HA UI                          │
│       │                                                      │
│       v                                                      │
│  async_step_reconfigure()                                    │
│       │   Loads existing username, password, ID              │
│       │                                                      │
│       v                                                      │
│  async_show_reconfigure() → Shows form:                      │
│       │   - Username (pre-filled)                            │
│       │   - Password (pre-filled)                            │
│       │   (Entity ID cannot be changed)                      │
│       │                                                      │
│       v                                                      │
│  async_step_reconf()                                         │
│       │                                                      │
│       ├── _async_try_set_username_password()                 │
│       │     └── Validates and tests connection               │
│       │                                                      │
│       ├── On success: async_update_reload_and_abort()        │
│       │     └── Updates config entry + reloads integration   │
│       └── On error: Show form again with error message       │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    RE-AUTHENTICATION                          │
│                                                              │
│  Coordinator raises ConfigEntryAuthFailed                    │
│       │   (due to AulaCredentialError during update)         │
│       │                                                      │
│       v                                                      │
│  HA shows "Re-authenticate" button to user                   │
│       │                                                      │
│       v                                                      │
│  async_step_reauth()                                         │
│       │   Loads existing config entry data                   │
│       │                                                      │
│       v                                                      │
│  async_show_reconfigure() → Same form as reconfiguration     │
│       │                                                      │
│       v                                                      │
│  async_step_reconf() → Same handling as reconfiguration      │
└──────────────────────────────────────────────────────────────┘
```

## Config Entry Data

Data stored in the config entry:

```python
entry.data = {
    CONF_USERNAME: "username",  # UniLogin username
    CONF_PASSWORD: "password",  # UniLogin password
}
entry.unique_id = "entity_id"  # User-chosen unique identifier
entry.title = "entity_id"      # Display name in HA
```

## Connection Validation

Before saving any configuration, credentials are validated:

```python
def _check_connection(self) -> AulaClient | Exception:
    client = AulaClient(self._username, self._password)
    result = client.connection_check()  # Attempts login
    if isinstance(result, Exception):
        return result
    return client
```

`connection_check()` calls `login()` on the proxy client, which performs the full UniLogin authentication flow. If successful, the client is ready to use.

## Error Mapping

```python
@staticmethod
def _parse_error(error: Exception) -> str:
    if isinstance(error, AulaCredentialError):
        return "invalid_auth"
    elif isinstance(error, ParseError):
        return "invalid_response"
    else:
        return str(error)
```

| Error | User Message (English) | User Message (Danish) |
|-------|----------------------|---------------------|
| `invalid_id` | "Entity ID is required" | "Entity ID er påkrævet" |
| `id_already_in_use` | "Entity ID is already in use" | "Entity ID er allerede i brug" |
| `invalid_auth` | "Invalid credentials" | "Ugyldige loginoplysninger" |
| `invalid_response` | "Invalid response from Aula" | "Ugyldigt svar fra Aula" |
| `invalid_email` | "Username is required" | "Brugernavn er påkrævet" |
| `invalid_password` | "Password is required" | "Adgangskode er påkrævet" |

## Entry Lifecycle

```
Setup:
    async_setup_entry()
    ├── Creates client and coordinators
    ├── First refresh (login + data fetch)
    ├── Stores in hass.data
    ├── Forwards to platforms
    └── Registers update listener

Reload (on config change):
    async_reload_entry()
    └── hass.config_entries.async_reload(entry_id)
        ├── Calls async_unload_entry()
        └── Calls async_setup_entry()

Unload:
    async_unload_entry()
    ├── Unloads all platforms
    └── Removes data from hass.data
```

## Localization

The config flow supports two languages:
- **English** (`translations/en.json`)
- **Danish** (`translations/da.json`)

HA automatically selects the user's configured language.
