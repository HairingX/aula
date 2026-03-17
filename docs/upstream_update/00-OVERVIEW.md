# Upstream Update Analysis: scaarup/aula -> HairingX/aula

**Date:** 2026-03-17
**Upstream repo:** https://github.com/scaarup/aula (branch: main)
**Our fork:** https://github.com/HairingX/aula (branch: main)
**Fork divergence point:** commit `2bcedd0`

## Executive Summary

The upstream repository (scaarup/aula) has undergone a **fundamental architectural change**: migrating from UniLogin username/password authentication to MitID OAuth 2.0/OIDC/SAML authentication. This is the single most critical change, as UniLogin providers are being phased out in Denmark in favor of MitID.

Our fork has diverged significantly from upstream with a much richer typed architecture (dataclass models, parsers, coordinators, typed entities). The upstream MitID changes live in a completely separate authentication package (`aula_login_client/`) that does NOT modify the old `aula_proxy/` code our fork is built on.

## Key Findings

### CRITICAL: MitID Authentication Required
- **Impact:** HIGH - Login will break when UniLogin is fully deprecated
- **Upstream fix:** Complete new auth package (`aula_login_client/`) with MitID support
- **Our status:** We still use UniLogin (BeautifulSoup form scraping)
- **Action needed:** Port MitID authentication or adapt upstream's `aula_login_client/` package
- See: [01-MITID-AUTHENTICATION.md](01-MITID-AUTHENTICATION.md)

### API Version Mismatch
- **Impact:** MEDIUM - Could cause 410 Gone errors if Aula deprecates old versions
- **Upstream:** Uses `API_VERSION = "22"` in const.py
- **Our fork:** Uses `API_VERSION = "19"` in const.py, `API_VERSION = "22"` in aula_proxy/const.py
- **Note:** Our proxy client already has auto-version-increment on HTTP 410
- See: [02-BUG-FIXES.md](02-BUG-FIXES.md)

### Bug Fixes to Evaluate
- Calendar platform unload when schoolschedule disabled (PR #300)
- Entity unavailable flipping on token refresh (PR #303) - MitID-specific
- lxml version pinning for HA 2026.3 (PR #314) - we're already fine
- ISO 8601 week number formatting (PR #200)
- See: [02-BUG-FIXES.md](02-BUG-FIXES.md)

### New Features in Upstream
- MitID token (hardware device) login support (PR #292)
- Teacher full name display option (PR #294)
- Multiple company/identity support (PR #296)
- See: [03-NEW-FEATURES.md](03-NEW-FEATURES.md)

## Documents in This Folder

| File | Description |
|------|-------------|
| [00-OVERVIEW.md](00-OVERVIEW.md) | This file - executive summary |
| [01-MITID-AUTHENTICATION.md](01-MITID-AUTHENTICATION.md) | Full analysis of MitID auth changes and porting strategy |
| [02-BUG-FIXES.md](02-BUG-FIXES.md) | All upstream bug fixes and their applicability to our fork |
| [03-NEW-FEATURES.md](03-NEW-FEATURES.md) | New features added upstream |
| [04-ARCHITECTURE-COMPARISON.md](04-ARCHITECTURE-COMPARISON.md) | Side-by-side architecture comparison |
| [05-MIGRATION-PLAN.md](05-MIGRATION-PLAN.md) | Recommended migration/porting plan |
