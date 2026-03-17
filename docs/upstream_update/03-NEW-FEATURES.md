# New Features in Upstream

## Summary

| Feature | PR | Applicable? | Priority |
|---------|-----|-------------|----------|
| MitID Authentication | #286 | YES - Critical | HIGH |
| MitID Token (hardware) Login | #292 | YES - if adopting MitID | MEDIUM |
| MitID Iteration 2 (optimization) | #293 | YES - if adopting MitID | HIGH |
| Teacher Full Name Display | #294 | Different arch, concept useful | LOW |
| Multiple Company Support | #296 | YES - if adopting MitID | MEDIUM |
| Post-broker-login Fixes | Various | YES - if adopting MitID | HIGH |

---

## 1. MitID Authentication (PR #286)

See [01-MITID-AUTHENTICATION.md](01-MITID-AUTHENTICATION.md) for full details.

**Summary:** Complete replacement of UniLogin authentication with MitID OAuth 2.0/OIDC/SAML flow. This is the most critical upstream change. Without it, our fork will stop working when UniLogin is fully deprecated.

---

## 2. MitID Hardware Token Login (PR #292, by jballe)

**What it does:** Adds support for MitID hardware token (code device / noglekort) authentication as an alternative to the MitID app. Users who don't have the MitID app on their phone can use a physical token device instead.

**New config options:**
- `mitid_use_token` (bool): Whether to use hardware token instead of app
- `mitid_password` (str): MitID password for token auth
- `mitid_token` (str): Token code from hardware device

**Known bugs in upstream PR:**
- `_LOGGER.inf` typo (should be `_LOGGER.info`) in reconfigure flow
- `user_input.password` / `user_input.token` (should be `user_input.get(CONF_MITID_PASSWORD)` / `user_input.get(CONF_MITID_TOKEN)`) in reconfigure flow

**Applicability:** Only relevant if we adopt MitID auth. Should be included in our MitID implementation with the bugs fixed.

---

## 3. MitID Iteration 2 - Optimization (PR #293)

**What it does:** Hardens the MitID auth flow after initial release:

- **CSRF token safety:** `_get_csrf_token()` helper returns `None` instead of crashing when cookie missing
- **Token expiration tracking:** Calculates and logs `expires_at` timestamp
- **Null-safe JSON parsing:** `.get()` chains throughout client instead of direct key access
- **400 Bad Request handling:** Proper error handling for bad token scenarios
- **Authorization header removal:** Aula uses query params for tokens, NOT headers (setting both = 400 error)
- **Version loop guard:** Max attempts on API version auto-increment
- **Platform unload fix:** Proper `async_unload_platforms()` usage

**Applicability:** All of these hardening improvements should be included if we adopt MitID auth. The null-safe JSON parsing pattern is also good practice for our existing code.

---

## 4. Teacher Full Name Display (PR #294)

**What it does:** Adds `CONF_TEACHER_FULL_NAME` config option to show full teacher names instead of initials in the school schedule calendar. Modifies the calendar lesson parser to accept `use_full_name` parameter.

**Applicability:** Our fork has a completely different calendar implementation with typed models. The concept is useful but would need to be implemented differently in our architecture. LOW PRIORITY - cosmetic feature.

---

## 5. Multiple Company Support (PR #296)

**What it does:** Improves MitID identity selection when a user has access through multiple companies/institutions:

- Better CSS selector for identity options (`a.list-link` instead of `div.list-link-box`)
- Shows company detail text in identity selection UI
- Fixes `ChosenOptionJson` extraction from `data-loginoptions` attribute
- Adds S4 combination ID support (MitID chip authenticator)

**Applicability:** Only relevant if we adopt MitID auth. Should be included from the start.

---

## 6. Post-Broker-Login Fixes (Various commits)

**What they do:** A series of fixes to the SAML redirect chain after MitID authentication:

- Extract form action URL from HTML instead of constructing manually
- Submit actual form data found on the page
- Handle role selection forms (auto-select `KONTAKT` / guardian role)
- Follow full redirect chain with `allow_redirects=True`
- Handle intermediate confirmation pages (200 OK with additional forms)

**Applicability:** Critical if adopting MitID auth. These fixes address real-world edge cases that will affect many users (multiple roles, multiple institutions, etc.).
