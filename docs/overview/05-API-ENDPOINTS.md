# API Endpoints

## Primary API

**Base URL**: `https://www.aula.dk/api/v{version}` (version starts at 22, auto-discovery)

All calls use session cookies + CSRF token header.

### Profile Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `?method=profiles.getProfilesByLogin` | GET | Fetches all profiles (parents + children) for the logged-in user |
| `?method=profiles.getProfileContext&portalrole=guardian` | GET | Fetches user ID, widget configurations, and institution data |
| `?method=profiles.getProfileMasterData&instProfileIds[]={ids}` | GET | Fetches main group assignments (class) for children |

### Presence Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `?method=presence.getDailyOverview&instProfileIds[]={ids}` | GET | Fetches daily presence status for all children |

**Response data** (per child):
- `status` (int 0-10): Presence code
- `checkInTime` / `checkOutTime`: Check-in/out times
- `exitWith`: Who picks up the child
- `location`: Location data (name, description, icon)

### Calendar Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `?method=calendar.getEventsByProfileIdsAndResourceIds&instProfileIds[]={ids}&resourceIds[]={ids}&start={start}&end={end}` | GET | Fetches calendar events for institutions |
| `?method=calendar.getBirthdayEventsForInstitutions&instCodes[]={codes}&start={start}&end={end}` | GET | Fetches birthday events |

**Date format**: `2024-10-16T00:00:00.0000+02:00` (URL-encoded `+` as `%2B`)

### Message Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `?method=messaging.getThreads&sortOn=date&orderDirection=desc&page=0` | GET | Fetches message threads (sorted newest first) |
| `?method=messaging.getMessagesForThread&threadId={id}&page=0` | GET | Fetches messages in a specific thread |

### Notification Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `?method=notifications.getNotificationsForActiveProfile&activeChildrenIds[]={ids}` | GET | Fetches notifications for children |

**Notification types**:
- `CALENDAR` - Calendar events
- `GALLERY` - New photos/videos
- `MESSAGES` - New messages
- `POSTS` - New posts
- `PRESENCE` - Absence/vacation registration
- `ALBUM` - New album additions

### Token Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `?method=aulaToken.getAulaToken&widgetId={widget_id}` | GET | Fetches bearer token for third-party widget |

---

## Third-Party APIs

These APIs require widget tokens fetched via `aulaToken.getAulaToken`.

### Meebook API (Weekly Plans)

**Base URL**: `https://app.meebook.com/aulaapi`
**Widget ID**: `0004` (WEEKPLAN_PARENTS)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/weeklyplansandevents/v2?childFilter[]={ids}&isMobileApp=false&start={start}&end={end}` | GET | Fetches weekly plans |

**Headers**:
```
Authorization: Bearer {widget_token}
Content-Type: application/json
```

### MinUddannelse API (Plans/Assignments)

**Base URL**: `https://api.minuddannelse.net/aula`
**Widget IDs**: `0029` (WEEKLETTER), `0030` (ASSIGNMENTS)

*Not fully implemented - missing test data*

### EasyIQ API (Weekly Plans)

**Base URL**: `https://api.easyiqcloud.dk/api/aula`
**Widget ID**: `0001` (EASYIQ_WEEKPLAN)

*Not fully implemented - missing test data*

### Systematic API (Reminders)

**Base URL**: `https://systematic-momo.dk/api/aula`
**Widget ID**: `0062` (REMINDERS)

*Not fully implemented - missing test data*

---

## Widget Detection

Widgets represent optional features in Aula. Not all institutions have all widgets.

| Widget ID | Constant | Feature |
|-----------|----------|---------|
| `0001` | `EASYIQ_WEEKPLAN` | EasyIQ weekly plans |
| `0004` | `WEEKPLAN_PARENTS` | Meebook weekly plans for parents |
| `0029` | `MY_EDUCATION_WEEKLETTER` | Weekly newsletter from MinUddannelse |
| `0030` | `MY_EDUCATION_ASSIGNMENTS` | Assignments from MinUddannelse |
| `0062` | `REMINDERS` | Reminders from Systematic |

**Detection flow**:
1. During login, `profiles.getProfileContext` is fetched
2. Response includes `pageConfiguration.widgetConfigurations`
3. Parsed into `List[AulaWidget]`
4. Coordinators check `has_widget(AulaWidgetId.X)` to determine which data to fetch

---

## Custom API Service

The integration exposes an `api_call` service in Home Assistant:

```yaml
service: aula.api_call
data:
  uri: "?method=presence.updatePresenceTemplate"
  post_data: '{"key": "value"}'  # optional
```

This allows users to make arbitrary API calls to Aula (e.g., to update presence).

---

## Retry Logic

```
For each API call (max 3 attempts):
├── Send request
├── Check response:
│   ├── 200 OK → Parse and return
│   ├── 401 Unauthorized → Refresh token, retry
│   ├── 5xx Server Error → Retry
│   ├── 410 GONE → Increment API version, retry
│   ├── 403 Forbidden → Raise AulaCredentialError
│   └── Other 4xx → Raise ConnectionRefusedError
└── Error after 3 attempts → Raise error
```

## Rate Limiting

The Aula API does not have officially documented rate limiting, but the integration limits calls via:
- Data coordinator: Max 1 call per 5 minutes
- Calendar coordinator: Max 1 call per 10 minutes
- Smart caching in calendar: Birthdays only once daily, events/weekly plans every 6 hours
