# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Aula is a Home Assistant custom integration for the Danish Aula school/institution platform. It provides calendar events, presence tracking, messaging, and notification monitoring as HA sensors, binary sensors, and calendar entities.

## Development Commands

**Run Home Assistant locally (dev container):**
```bash
scripts/develop.sh
```
HA runs on port 8123 (mapped to 1337 in devcontainer).

**Run tests:**
```bash
python -m unittest discover -v -s ./custom_components/aula/aula_proxy -p "test_*.py"
```

**Run a single test:**
```bash
python -m unittest custom_components.aula.aula_proxy.test_messages.TestMessages.test_getProfilesByLogin
```

**Formatting:** Black with isort (`--profile black`), configured for format-on-save in VSCode.

**CI validation:** HACS validation and hassfest run on push/PR via GitHub Actions.

## Architecture

```
Config Flow (Unilogin credentials)
    → AulaClient (aula_client.py)
        → AulaProxyClient (aula_proxy/aula_proxy_client.py) - HTTP client, BeautifulSoup login scraping
            → Models (aula_proxy/models/) - @dataclass types
            → Parsers (aula_proxy/models/) - JSON → dataclass conversion
    → Coordinators
        ├─ AulaDataCoordinator (5 min) - profiles, daily overviews, messages, notifications
        └─ AulaCalendarCoordinator (10 min) - birthdays, events, weekly plans
    → Entities
        ├─ Sensors: status, presence, duration
        ├─ Binary Sensors: unread messages/gallery/calendar/posts/presence
        └─ Calendars: events, birthdays, weekly plans
```

**Key files:**
- `custom_components/aula/__init__.py` — Platform setup and entry point
- `custom_components/aula/aula_proxy/aula_proxy_client.py` — Core HTTP client (~1000 lines)
- `custom_components/aula/aula_proxy/models/` — All dataclass models and their parsers
- `custom_components/aula/const.py` — Integration constants; `aula_proxy/const.py` — API endpoints and widget IDs
- `custom_components/aula/config_flow.py` — Auth config flow (conf, reauth, reconf steps)

## Key Patterns

- **Model + Parser pairs:** Each data type has a `aula_*_models.py` (dataclasses) and `aula_*_parser.py` (JSON parsing). Parsers are static methods that convert raw API JSON to typed dataclasses.
- **Entity base classes:** `AulaEntityBase[T]` for sensors/binary sensors, `AulaCalendarEntityBase` for calendars — both extend HA's `CoordinatorEntity`.
- **Widget detection:** `has_widget(AulaWidgetId.X)` checks which Aula features are available for a given institution.
- **Blocking HTTP in async:** Uses `async_add_executor_job()` to run synchronous HTTP calls from async HA context.
- **Localization:** `strings.json` with translations in `translations/en.json` and `translations/da.json`.

## Release Process

When the maintainer asks to "release" (or cut/publish a release), follow this exact
process. It is split across four GitHub Actions workflows in `.github/workflows/` plus
one shared composite action in `.github/actions/release-publish/`. **Two preconditions
must both be satisfied before anything can be published: (1) the draft release must
exist (default flow only — see step 3a vs 3b), and (2) the maintainer must have
explicitly approved it.**

1. **Draft is produced automatically — wait for it.** `release-drafter.yml` runs on every
   push to `main` and maintains a single GitHub **draft release** whose notes are
   auto-generated and categorized from merged PR labels (it also auto-labels PRs). The
   draft's `tag_name` is `v$RESOLVED_VERSION` — the version is itself resolved from PR
   labels (`major` / `minor` / `patch`, defaulting to `patch`). After the relevant changes
   are merged to `main`, **wait until the Release Drafter workflow run has completed** so
   the draft reflects them. Never publish before the draft is up to date — the publish
   step reuses the draft's body as the release notes.

2. **Review and approval — mandatory, maintainer only.** Present the current draft release
   notes to the maintainer and get **explicit approval** of the content (and the version
   number that release-drafter resolved) before proceeding. Do NOT publish a release
   without this approval, even if asked to "just release it" — confirm the draft first.

3. **Publish.** Pick the right workflow based on whether you accept the draft's resolved
   version or need to override it:

   **3a. Default path — `Release` workflow (`release.yml`).** Manual
   `workflow_dispatch` with **no input**. It reads `tag_name` from the newest draft
   release (`gh api repos/{owner}/{repo}/releases`, filtered to drafts and sorted by
   `created_at` desc), strips the leading `v`, and uses that as the version. **Fails
   fast** if no draft exists or the format is unexpected. This is the path you should
   use most of the time.

   **3b. Manual override — `Release (manual version)` workflow (`release-manual.yml`).**
   Manual `workflow_dispatch` taking a **required `version` input** (e.g. `0.2.6` —
   without the `v` prefix; format `X.Y.Z` or `X.Y.Z-suffix`). Runs **regardless of draft
   state**. Use this only when the draft's resolved version is wrong (e.g. you want to
   jump minor without re-labelling already-merged PRs). If a draft exists, its body is
   still captured as release notes and the draft is deleted.

   Both 3a and 3b delegate to the shared composite action
   `.github/actions/release-publish/action.yml`, which (in order): validates the version,
   verifies tag `v$VERSION` does not already exist, bumps
   `custom_components/aula/manifest.json` via `.github/scripts/update_hacs_manifest.py`,
   commits the bump and pushes to `main`, creates and pushes tag `v$VERSION`, builds
   `aula.zip` (excluding `test_*`, `__pycache__`, `*.pyc`), **captures the Release Drafter
   draft's body as the release notes and deletes the draft (if present)**, then publishes
   the GitHub Release for `v$VERSION` with `aula.zip` attached. Do not bump the manifest
   or create the tag by hand; the composite owns version bump, tag, zip, and publish.

   Both workflows declare `concurrency: release` so two simultaneous release runs are
   serialized rather than racing each other.

4. **Dev/pre-releases** use a separate workflow, `release-dev.yml` (`Release dev`): a manual
   `workflow_dispatch` taking a `tag` input (e.g. `v0.3.0-dev.1`) that builds `aula.zip` and
   uploads it as a **prerelease** asset. Use this only when a dev/prerelease build is
   explicitly requested; it does not bump the manifest and does not interact with the
   draft.

Summary of ownership: Release Drafter (automatic, on push to `main`) owns the draft notes
and the resolved version → maintainer approves → the `Release` workflow (default) or
`Release (manual version)` workflow (override) dispatches the shared composite, which
owns version bump, tagging, zipping, and publishing. Build + draft must be in place
(default path), and approval given, before any release.

## Agent Workflow (MANDATORY)

**All code changes MUST follow the agent workflow process defined in `docs/AGENT_WORKFLOW.md`.** This process requires every task to pass through 9 stages: Project Management → Design Document → Design Review (multi-team) → Implementation → QA Review → Performance Review → Network & Data Review → HASS Compliance → Final Verification. **NO code may be written until the design document is reviewed and approved by all specialist agent teams (Stage 3).** No stage may be skipped. Read the full process document before starting any task.

## Conventions

- All documentation, comments, and commit messages must be written in English unless explicitly told otherwise
- Python 3.14, minimum Home Assistant 2026.3.0
- 4-space indentation, LF line endings
- unittest framework (not pytest) for tests; test fixtures are JSON files in `aula_proxy/test_messages/`
- Version tracked in `custom_components/aula/manifest.json`
