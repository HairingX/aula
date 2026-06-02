---
date: 2026-06-02
status: proposed
author: claude (with maintainer @Patrick)
---

# Split release workflow into draft-driven and manual variants

## 2a. Problem Statement

Today the `Release` workflow ([`.github/workflows/release.yml`](../../.github/workflows/release.yml))
requires the operator to type the version number as a `workflow_dispatch` input
(`X.Y.Z` without the `v` prefix). The Release Drafter already resolves a version
from PR labels (`v$RESOLVED_VERSION` is stored in the draft's `tag_name`), so for
the normal path the operator is repeating information that already exists.

**Goal:** keep the auto-resolved version as the default path while preserving an
escape hatch for explicit overrides.

**Acceptance criteria:**

1. There exist **two** dispatchable release workflows:
   - **Release** (default) — takes **no input**. Resolves the version from the
     newest existing draft release. **Fails loudly** if no draft is found or the
     draft has no parseable `tag_name`.
   - **Release (manual version)** — takes a **required `version` input**. Runs
     **regardless** of whether a draft exists; if a draft exists, its body is
     still used as release notes and the draft is deleted (same behavior as
     today's `release.yml`).
2. The publish-side behavior (manifest bump, commit, tag, zip, notes capture,
   GitHub Release create) is **identical** between the two flows; both reuse a
   single shared implementation so that fixes apply to both.
3. The version-format validation (`^[0-9]+\.[0-9]+\.[0-9]+(-[a-z0-9.-]+)?$`)
   and the tag-uniqueness check (`v$VERSION` must not already exist) are
   preserved.
4. Existing artifact behavior is preserved: `aula.zip` excludes `test_*`,
   `__pycache__`, `*.pyc`.
5. `release-dev.yml` is untouched (it is for prereleases and is unrelated).
6. `CLAUDE.md`'s release-process section is updated to describe both workflows.

## 2b. Affected Components

| File | Change |
|------|--------|
| `.github/workflows/release.yml` | Rewritten. No input; reads draft `tag_name`, fails if absent; delegates publish work to shared composite action. |
| `.github/workflows/release-manual.yml` | **New.** Required `version` input; delegates publish work to shared composite action. |
| `.github/actions/release-publish/action.yml` | **New.** Composite action that owns: validate version, checkout, tag-exists check, manifest bump, commit/push, tag/push, build zip, capture draft body + delete draft, publish GitHub Release. |
| `CLAUDE.md` (Release Process section) | Updated to describe both workflows and when each is used. |
| `.github/workflows/release-drafter.yml` | **Unchanged.** Still produces draft on push to `main`. |
| `.github/workflows/release-dev.yml` | **Unchanged.** Prerelease path unaffected. |
| `.github/scripts/update_hacs_manifest.py` | **Unchanged.** |

**Dependency map (post-change):**

```
release-drafter.yml ──► (maintains draft release)
                         │
                         ▼
release.yml ──► reads draft.tag_name ──► composite action `release-publish`
                                              │
release-manual.yml ──► input.version ─────────┘
                                              │
                                              ▼
                            manifest bump → commit → tag → zip
                                              │
                                              ▼
                            capture + delete draft → publish GitHub Release
```

## 2c. Proposed Solution

### Composite action: `.github/actions/release-publish/action.yml`

A composite (not reusable workflow) because:

- It runs as one job in the calling workflow's UI (cleaner Actions UI than a
  `workflow_call` chain that shows two separate runs).
- Composite actions inherit the caller's permissions and workspace, which fits
  our case (caller already grants `contents: write`).

Composite actions cannot read secrets directly, so the `GITHUB_TOKEN` is passed
as an input. Sketch:

```yaml
name: 'Publish release'
description: 'Bump manifest, tag, zip, capture draft notes, publish GitHub Release'
inputs:
  version:
    description: 'Version (X.Y.Z or X.Y.Z-suffix, no v prefix)'
    required: true
  github-token:
    required: true
runs:
  using: 'composite'
  steps:
    - name: Validate version
      ...                          # same regex as today
    - uses: actions/checkout@v6
      with: { ref: main, fetch-depth: 0 }
    - name: Verify tag does not already exist
      ...                          # same as today
    - name: Bump manifest.json
      ...                          # same as today (calls update_hacs_manifest.py)
    - name: Commit and tag
      ...                          # same as today
    - name: Build zip
      ...                          # same as today
    - name: Capture draft body and delete draft
      ...                          # same as today
    - name: Publish GitHub Release
      ...                          # same as today
```

All of the bash inside these steps is **lifted verbatim** from the current
`release.yml` — no behavior changes inside the publish path. The only mechanical
difference is `${{ inputs.version }}` instead of `${{ github.event.inputs.version }}`
and `${{ inputs.github-token }}` instead of `${{ secrets.GITHUB_TOKEN }}`.

### `release.yml` (default — uses draft)

```yaml
name: Release
on:
  workflow_dispatch: {}

permissions:
  contents: write

concurrency:
  group: release
  cancel-in-progress: false

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - name: Resolve version from latest draft
        id: resolve
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          REPO: ${{ github.repository }}
        run: |
          tag_name=$(gh api "repos/$REPO/releases" \
            --jq '[.[] | select(.draft==true)] | .[0].tag_name // empty')
          if [[ -z "$tag_name" ]]; then
            echo "::error::No draft release found. Wait for Release Drafter, then retry."
            exit 1
          fi
          if [[ ! "$tag_name" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-[a-z0-9.-]+)?$ ]]; then
            echo "::error::Draft tag_name has unexpected format: $tag_name"
            exit 1
          fi
          version="${tag_name#v}"
          echo "Resolved version from draft: $version"
          echo "version=$version" >> "$GITHUB_OUTPUT"

      - uses: actions/checkout@v6      # needed so composite action is on disk
        with: { ref: main }

      - uses: ./.github/actions/release-publish
        with:
          version: ${{ steps.resolve.outputs.version }}
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

Note: the composite itself runs `actions/checkout@v6` again with `fetch-depth: 0`
(needed for tag operations). The outer `actions/checkout@v6` is required only so
that the composite action's `action.yml` is on disk for the runner to find. This
is the standard pattern for local composite actions.

### `release-manual.yml` (manual override)

```yaml
name: Release (manual version)
on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Version to release (e.g. 0.2.6 — without v prefix)'
        required: true

permissions:
  contents: write

concurrency:
  group: release
  cancel-in-progress: false

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v6
        with: { ref: main }

      - uses: ./.github/actions/release-publish
        with:
          version: ${{ inputs.version }}
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

Notable decisions:

- **`concurrency: release`** on **both** workflows so two simultaneous releases
  serialize instead of stomping on each other's tag/push.
- Manual workflow does **not** require a draft; if no draft exists the composite
  publishes with an empty body (same fallback as today). If a draft does exist,
  it is captured and deleted — even if the manual version differs from the
  draft's resolved version, because the draft's body is the running changelog
  since the last release, and is still the correct notes content.
- We do **not** factor the version validator into a separate step in the caller
  — the composite already validates. Caller of `release.yml` doesn't even know
  the version yet at workflow start; only after the resolve step.

### Rejected alternatives

- **Reusable workflow (`workflow_call`)** instead of composite action: rejected
  because reusable workflows show as two separate runs in the Actions UI, which
  is noisier without buying anything here.
- **Single workflow with optional input + branching logic**: rejected per the
  maintainer's explicit request for two workflows. Two named entry points
  communicate intent better at dispatch time.
- **Composite as `release-impl/action.yml`**: name swapped to `release-publish`
  because the action is the publish step, not the whole flow.

## 2d. Code Trace Analysis

**Flow 1 — Default release (`release.yml`):**

1. Maintainer merges PRs to `main` with labels (`bug`, `enhancement`, `chore`,
   `dependencies`, `breaking-change`, or version labels `major`/`minor`/`patch`).
2. `release-drafter.yml` runs on push and updates the single draft release. The
   draft's `tag_name` becomes `v$RESOLVED_VERSION` (default resolution: `patch`).
3. Maintainer reviews the draft body and version in the GitHub Releases UI.
4. Maintainer runs `Release` (workflow_dispatch, no inputs).
5. Job's first step calls `gh api .../releases` and extracts `.[0].tag_name`
   from drafts. Fails if missing or wrong format.
6. Checks out `main`, then runs the composite action with the resolved version.
7. Composite proceeds exactly like today's `release.yml`.

**Flow 2 — Manual override (`release-manual.yml`):**

1. Maintainer runs `Release (manual version)` with `version=X.Y.Z`.
2. Job checks out `main`, runs the composite with the provided version.
3. Composite validates format, checks tag uniqueness, bumps manifest, commits,
   tags, zips, captures-then-deletes draft (if any), publishes.

**Breakage points considered:**

| Point | Before | After |
|-------|--------|-------|
| Releases triggered with `release.yml` + a typed version | Worked | **Breaks** — input no longer exists. Operator must use `release-manual.yml` for that path. **Documented in CLAUDE.md.** |
| Releases triggered with `release.yml` and no draft present | N/A (input was required) | **Fails fast** with a clear error pointing to Release Drafter. |
| Draft `tag_name` is `v` (regex empty) or empty string | N/A | **Fails fast** at format check. |
| Manual release while a draft for a different version exists | Worked — used draft body as notes | **Same behavior preserved.** Captured + deleted by composite. |
| `release-dev.yml` (prerelease) | Worked | **Unchanged.** Separate path. |
| Manifest already at the requested version | Worked — skipped commit, still tagged | **Same logic preserved verbatim in the composite.** |
| Two concurrent release runs | Could race | **Serialized** via `concurrency: release`. |

**No code path outside `.github/workflows/`, `.github/actions/`, and `CLAUDE.md`
changes.** Integration code (`custom_components/aula/**`) is untouched.

## 2e. Risk Assessment

- **Risk: Release Drafter still running when maintainer dispatches `release.yml`.**
  Mitigation: documentation says "wait for the Release Drafter run to complete
  before dispatching `Release`". This matches the existing process; no automation
  needed.
- **Risk: Composite action `actions/checkout` runs twice (outer + inner).** Cost
  is small (~2s). Could be optimized by passing checkout from outer to inner, but
  the inner needs `fetch-depth: 0` for tag operations, and an outer of
  `fetch-depth: 0` would change `release-manual.yml`'s checkout, which is fine
  but verbose. Current sketch keeps the responsibilities separated: outer
  fetches just enough to load the composite, inner does the full fetch.
- **Risk: `gh api` returns drafts in unspecified order; `.[0]` may not be
  newest.** GitHub's `/releases` returns newest-first by `created_at`, but for
  defensiveness we could sort by `created_at` desc explicitly. **Decision:** add
  `sort_by(.created_at) | reverse` to the `jq` to make the "latest" guarantee
  explicit.
- **Risk: Permissions on the composite action's git push.** Composite inherits
  the calling job's `GITHUB_TOKEN`; the calling job's `permissions: contents:
  write` is sufficient for push + tag.
- **Risk: Maintainer accidentally dispatches `Release` for a version already
  released.** Tag-exists check in composite catches this and aborts cleanly.

### Test coverage

- No unit tests touch CI workflows.
- Validation is manual review + first live release. We will:
  - YAML-lint by reading the files back and visually verifying.
  - The first dry test will be the next real release; an unsafe edit could
    block releases. Mitigation: keep all bash step bodies **byte-identical** to
    today's `release.yml` where possible.

## 2f. Best Practice Checklist

- ✅ **English-only** for all YAML comments and CLAUDE.md text (per
  `feedback_no_danish` memory).
- ✅ **Minimal scope** — no edits to unrelated workflows or integration code.
- ✅ **Pattern reuse** — composite action is the GitHub Actions equivalent of
  factoring shared logic.
- ✅ **No over-engineering** — single composite, two thin callers.
- ✅ **Naming consistency** — workflow names (`Release`, `Release (manual
  version)`) match the dispatch-UI convention used by `Release dev`.
- ✅ **Concurrency** — `concurrency: release` on both callers, the canonical
  pattern for serializing publish jobs.
- ✅ **No behavior change inside the publish path** — bash bodies preserved
  verbatim where possible, so the change is a structural refactor + one new
  feature (draft-driven resolution), nothing else.

## Approval

Maintainer must explicitly approve this design before any workflow file is
modified.
