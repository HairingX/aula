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

**CI validation:** unit tests (including the release scripts in `.github/scripts`), HACS validation and hassfest run on push/PR via GitHub Actions, and again on the exact commit a release or test build publishes.

**Release script tests:**
```bash
python -m unittest discover -v -s ./.github/scripts -p "test_*.py"
```

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

When the maintainer asks to "release" (or cut/publish a release), follow this process. Design
and rationale: `docs/designs/2026-10-27-release-flow-best-practice.md`.

**The manifest in the repository always says `0.0.0`, and the draft release is never published
by hand.** HACS installs the zip a release carries (`zip_release` and `filename` in `hacs.json`),
and only the `Release` workflow builds it: the manifest in the zip says the release's version,
and the workflow refuses to publish a zip whose manifest says anything else. A HACS install of a
branch instead of a release shows version `0.0.0`.

Why: tags `v0.1.0`-`v0.2.5` pointed at commits whose manifest named another version, and the
`v0.2.0` zip installs as `0.1.10`, because the version was committed to `main` by hand or after
tagging. Now nothing is committed by a release: the tested commit is tagged, and the version
exists only in the tag and the zip.

**How the release text is authored - never by hand.** Release Drafter keeps a draft release
whose notes are made from merged pull request **titles** and **labels**. To shape what a
release says, shape the pull requests: the title becomes the changelog line, and the labels
decide the section and the version. Notes list only what users get: `chore`, `documentation`,
`dependencies` and `skip-changelog` are left out.

**Branches and labels.** Name a branch by the kind of change; the autolabeler labels its pull
request from the name: `feature/<what>` -> `feature request`, `fix/<what>` -> `bug`,
`docs/<what>` -> `documentation`, `chore/<what>` (CI, tooling, anything that stays in the
repository) -> `chore`. A change to what users install is a `fix/` or a `feature/`, never a
`chore/`. Put `breaking-change` or `minor` on a pull request that needs a minor bump; a patch is
the default. **No label gives a major version**: a label placed wrongly must not release one.

1. **Wait for the draft.** `release-drafter.yml` runs on every push to `main` and keeps one
   draft release proposing the next version (`v$RESOLVED_VERSION`). After the changes are merged,
   wait until the Release Drafter run on `main` has completed. The `Release` workflow refuses to
   use a draft that is not up to date with `main`.

2. **Review and approval - mandatory, maintainer only.** Present the draft's notes and the
   version to the maintainer and get **explicit approval** before running Release. Do NOT
   release without it, even if asked to "just release it" - confirm the draft first.

3. **Run the `Release` workflow** (`release.yml`) from the Actions tab, on `main`, choosing
   **release candidate** or **final release**. It works out the version: the next release
   candidate of the open series (`0.3.0rc1` -> `0.3.0rc2`), or the final release that ends it
   (`0.3.0`); a draft naming a higher version starts a new series (`0.3.0rc1`). Type a version
   (canonical PEP 440 without `v`, of the kind chosen) only for a new major, or to override a
   version worked out wrongly.

   It refuses: a version not higher than every release tagged; a non-canonical version; a new
   major not typed as override; a release with no pull request merged since the previous release
   (for a final release, the previous final release). It then runs the unit tests and the hassfest
   and HACS validation on the exact commit, builds `aula.zip` from that commit with the
   manifest's version set (tests, `__pycache__` and `*.pyc` left out) and checks it, tags that
   commit, and publishes the GitHub release with the zip - a release candidate as a pre-release,
   which HACS offers only to users who switch beta versions on.

   A release candidate's notes are written by GitHub from the pull requests since the previous
   release candidate or final release (`.github/release.yml` groups them). A final release's notes
   are the draft's body, and the final release deletes the draft; a release candidate keeps it.

   If publishing fails part-way, use **Re-run failed jobs**: it accepts the tag it already pushed
   on the same commit and uploads the zip to the release it already created. **Re-run all jobs**
   is refused once the version is tagged.

4. **Test builds** (`test-build.yml`, `Test build`): to try a development branch on a real Home
   Assistant, run it from the Actions tab on that branch. It tests and validates the branch's
   commit and publishes it as a pre-release such as `v0.2.9b1` (the next release's version with
   the first free `b<n>`); the commit is tagged, the version is set only in the zip. A new test
   build of the branch replaces the previous one; closing the pull request or deleting the branch
   removes them (`test-build-cleanup.yml`). HACS offers the newest pre-release to beta users,
   test build or release candidate alike. A test build needs a draft release: after a final
   release, wait for the next merge into `main`. Test-build tags never count as releases.

Never create tags, edit the manifest's version or publish the draft by hand: the workflows own the
version, the tag, the zip and the release. `Release` and `Test build` share the concurrency group
`release`, so they never run at the same time.

## Agent Workflow (MANDATORY)

**All code changes MUST follow the agent workflow process defined in `docs/AGENT_WORKFLOW.md`.** This process requires every task to pass through 9 stages: Project Management → Design Document → Design Review (multi-team) → Implementation → QA Review → Performance Review → Network & Data Review → HASS Compliance → Final Verification. **NO code may be written until the design document is reviewed and approved by all specialist agent teams (Stage 3).** No stage may be skipped. Read the full process document before starting any task.

## Conventions

- All documentation, comments, and commit messages must be written in English unless explicitly told otherwise
- Python 3.14, minimum Home Assistant 2026.3.0
- 4-space indentation, LF line endings
- unittest framework (not pytest) for tests; test fixtures are JSON files in `aula_proxy/test_messages/`
- The version lives in the release tag and the release zip; `custom_components/aula/manifest.json` says `0.0.0` (see Release Process)
