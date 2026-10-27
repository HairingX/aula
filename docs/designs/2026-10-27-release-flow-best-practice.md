# Release flow: tested commit, version only in tag and zip

Status: proposed (Stage 2). Branch: `chore/release-flow-best-practice`.

## 1. Plan (Stage 1)

**Task.** Bring the release flow of this repository up to the release practice used by the
maintainer's sibling integration (`ha_duka_connect`), which was rebuilt after releases shipped
with wrong version numbers. Every rule below is verified against this repository's tags,
release assets and workflow runs as of 2026-10-27.

**Acceptance criteria.**
1. The zip a release carries has a `manifest.json` whose `version` equals the release's tag; the
   workflow refuses to publish otherwise.
2. The released commit is the commit that was tested (unit tests) and validated (hassfest, HACS)
   in the same workflow run.
3. Nothing is pushed to `main` by a release; `main` can be protected so it takes pull requests only.
4. The version is worked out, never typed, except to start a new major or correct a wrong one;
   any version not higher than every existing tag is refused.
5. A release with no pull request merged since the previous release is refused.
6. Release candidates (pre-releases) and test builds of a development branch are possible, both
   with the correct version in their zip, and HACS offers them only to users who opt in.
7. The release-drafter configuration produces no deprecation warnings.
8. The draft release is deleted only after the GitHub release exists.

**Out of scope.** Integration code; re-publishing historic releases; GitHub repository settings
(rulesets), which need the owner's admin rights and are listed as follow-up in section 7.

## 2. Problem statement - facts found

Verified by downloading every release asset (`aula.zip`) and reading `manifest.json` in it, and by
reading the tags:

| Finding | Evidence |
|---|---|
| Release `v0.2.0` installs as version `0.1.10` | `manifest.json` in the `v0.2.0` zip says `0.1.10` |
| Release `v0.1.0` has no usable zip | the asset download is not a zip file |
| Tags `v0.1.2`-`v0.2.5` point at commits whose manifest names the previous version; `v0.1.0`, `v0.1.1` at `0.2.0`, `v0.1.10` at `0.2.0`, `v0.2.1` at `0.1.10` | `git show <tag>:custom_components/aula/manifest.json` |
| Releases up to `v0.2.8` shipped test modules and fixtures to users (5-7 `test_*` files) | zip listings; fixed in #12, unreleased |
| Zips `v0.1.1`-`v0.2.8` except `v0.2.0` carry the right version | zip manifests |
| Release Drafter emits 9 deprecation warnings per run | run 33006859441, job 98302733889 |

Weaknesses of the current flow (`release.yml` + composite `release-publish`), each read from the code:

- **W1 Push to main.** The bump is committed and pushed straight to `main`
  (`git push origin HEAD:main`), so `main` cannot be protected and the released commit was
  never reviewed.
- **W2 Untested commit.** Nothing runs tests, hassfest or HACS validation on the commit that is
  tagged and zipped.
- **W3 Zip not checked.** The zip is built with `zip -r`; nothing checks its manifest says the
  version released. The `v0.2.0` defect is exactly this.
- **W4 Weak version check.** Only "tag does not exist" is checked: an override such as `0.1.11`
  would be released below `0.2.8`. The format accepts arbitrary `X.Y.Z-suffix`, which is not
  PEP 440 canonical, so the tag and manifest can spell one version two ways.
- **W5 Draft deleted before publish.** If `gh release create` fails, the notes are gone while
  the tag and the bump commit are already pushed: a half-done release.
- **W6 Release from moving `main`.** The workflow checks out `main` twice, and `gh release create
  --target main`; a merge during the run changes what is released.
- **W7 Empty releases possible.** Nothing refuses a release with no merged pull request.
- **W8 `release-dev.yml` ships a wrong version.** It zips the working tree unchanged, so a dev
  build tagged `v0.3.0-dev.1` installs with the manifest's version (today `0.2.8`); and
  `svenstaro/upload-release-action` creates a missing tag at the default branch, not at the commit
  that was zipped.
- **W9 A wrong label can release a major.** `version-resolver.major.labels: ['major']`.
- **W10 Deprecated drafter syntax**, and notes list chores and dependency bumps users do not get.
- **W11 Steps run as `bash -e` without `pipefail`** (no explicit `shell: bash`), so a failing
  command piped into another fails nothing.

## 3. Affected components

```
release-drafter.yml (push main)  --> draft release vX.Y.Z  (notes + proposed version)
                                         |
Release (workflow_dispatch, main) -------+--> prepare: release_version.py next / changes
     |--> tests.yml (workflow_call, ref=sha)
     |--> hacs-validate.yml (workflow_call, ref=sha)
     '--> publish: release_version.py write -> release_zip.py (checks) -> tag sha -> gh release -> delete draft
Test build (workflow_dispatch, branch) --> test_build.py version -> tests/validate -> zip -> tag -> pre-release
Test build cleanup (PR closed / branch deleted) --> delete that branch's test-build pre-releases + tags
```

| File | Change |
|---|---|
| `.github/workflows/release.yml` | rewritten (port of the sibling's) |
| `.github/actions/release-publish/action.yml` | removed |
| `.github/scripts/update_hacs_manifest.py` | removed |
| `.github/scripts/release_version.py` | new (port, unchanged logic) |
| `.github/scripts/release_zip.py` | new (port + leaves test files out) |
| `.github/scripts/test_build.py` | new (version only; no external library) |
| `.github/scripts/test_release_version.py`, `test_release_zip.py`, `test_test_build.py`, `test_workflows.py` | new, `unittest` |
| `.github/workflows/release-dev.yml` | removed, replaced by `test-build.yml` + `test-build-cleanup.yml` |
| `.github/workflows/tests.yml` | `workflow_call` with `ref`; runs the script tests; bash; no persisted credentials |
| `.github/workflows/hacs-validate.yml` | `workflow_call` with `ref`; bash; no persisted credentials; job names kept |
| `.github/workflows/release-drafter.yml` | `permissions: {}`, bash, `github.token` |
| `.github/release-drafter.yml` | v7 syntax; minor at most; user-facing notes only |
| `.github/release.yml` | new: categories for GitHub-generated notes (release candidates) |
| `.github/dependabot.yml` | `dependencies` label on action updates too |
| `custom_components/aula/manifest.json` | `version` -> `0.0.0` |
| `CLAUDE.md`, `docs/AGENT_WORKFLOW.md` | release process rewritten; `release-dev.yml` reference updated |

No Python module of the integration changes. The only runtime consumer of the manifest version is
the startup log line in `__init__.py` (`integration.version`); from a release it logs the
release's version (from the zip), from a checkout `0.0.0`.

## 4. Proposed solution

Port of the sibling's flow, adapted to this repository. Only adaptations are described in detail;
the logic of `release_version.py` is carried over unchanged, with its tests.

**Version kept out of the repository.** `manifest.json` on `main` says `0.0.0`. The release
writes the version into the manifest on the runner, builds the zip, and checks that the zip's
`manifest.json` says that version. The tag is put on the tested commit; nothing is committed.
HACS installs the release's zip (`zip_release: true`, `filename: aula.zip`), so users get the
right version, and a tag never again disagrees with what is installed. This removes W1, W3, W6.

**Release workflow.** `workflow_dispatch` on `main` only, with input `release`
(`release candidate` | `final release`) and an optional `version` override.
1. `prepare`: list tags (`git ls-remote --tags`) and the newest draft; `release_version.py next`
   works out the version: continue an open RC series (`0.3.0rc1` -> `0.3.0rc2`), end it
   (`0.3.0`), or start from the draft's version. Refused: non-canonical PEP 440, not
   `MAJOR.MINOR.PATCH[rcN]`, a new major unless typed as override, kind mismatch, and anything not
   higher than every tag (W4, W9). `release_version.py changes` refuses when no PR was merged
   since the previous release (W7). Records `sha` of `main` at that moment.
2. `test` and `validate`: the existing `tests.yml` and `hacs-validate.yml`, called with that `sha` (W2).
3. `publish` (needs all three): check out `sha`, write the version, require that only the
   manifest changed, build and check the zip, tag `sha` (annotated), `gh release create
   --verify-tag` with the zip, as a pre-release (`--prerelease --latest=false`) for an RC; a final
   release takes the draft's body, an RC GitHub-generated notes from the previous tag. The draft is
   deleted after the release exists (W5).
`permissions: {}` at top, least privilege per job; `concurrency: release`.

**Zip contents.** `release_zip.py` writes the files of `custom_components/aula/`, leaving out
`__pycache__`, `*.pyc`, and test code: any path with a component starting with `test_` (today
`aula_proxy/test_*.py` and `aula_proxy/test_messages/`), the same set `zip -x "*/test_*" -x
"test_*"` excludes now. No other runtime file starts with `test_` (checked with `git ls-files`).
It then refuses the zip unless `manifest.json` is at its root and says the version.

**Test builds** replace `release-dev.yml` (W8): run on a development branch (refused on `main`);
version = the draft's version with the first free `b<n>` (`0.2.9b1`); tests and validation on the
branch's commit; zip with that version, checked; the commit tagged, published as a pre-release
whose notes carry `test-build-branch: <branch>`. A new build replaces the branch's previous one;
`test-build-cleanup.yml` deletes them when the PR closes or the branch is deleted. The sibling's
library-branch logic is dropped: this integration has no separately released library.

**Release Drafter.** v7 `categories` with `when`, a `pre-exclude` category for
`skip-changelog`, `chore`, `documentation`, `dependencies`; `exclusive` categories; version:
`minor` for `breaking-change` or `minor`, otherwise `patch`; no major (W9, W10). Autolabeler by
branch prefix: `fix/` -> `bug`, `feature/` -> `feature request`, `docs/` -> `documentation`,
`chore/` -> `chore`. `enhancement` remains a feature label, so existing PR labels keep working.

**Pipefail.** Every workflow sets `defaults.run.shell: bash` (W11); a test enforces it and that no
step pipes into `head`.

**Tests framework.** The script tests use `unittest` (repository convention) and run in
`tests.yml` with `python -m unittest discover -s .github/scripts -p "test_*.py"`.

**Alternatives rejected.** (a) Keep the bump-commit-to-main model and add checks: it still needs
a push to `main`, so `main` cannot be protected, and the tag would point at an untested commit.
(b) Pin actions by SHA: the sibling uses major versions with Dependabot; consistency wins.

## 5. Code trace

- **Integration runtime.** `async_setup_entry` logs `integration.version`. Before: the version
  committed on `main`. After: from a release zip, the release's version; from a git checkout,
  `0.0.0`. No other reader (`grep` for `manifest`/`version` in `custom_components`).
- **hassfest** requires `version` in a custom integration's manifest and an AwesomeVersion-valid
  value: `0.0.0` passes (the sibling's `main` passes with it).
- **HACS** with `zip_release` installs the asset named by `filename` from the selected release;
  versions shown are release tags. Pre-releases are offered only when the user enables them.
- **Release Drafter** takes the newest non-prerelease release as "last release", so release
  candidates and test builds do not reset the draft; the draft lists everything since the last
  final release.
- **Existing tags** are all `X.Y.Z` (highest `v0.2.8`) and parse as PEP 440; the current draft
  `v0.2.9` gives `0.2.9rc1` or `0.2.9`. PRs #12-#14 are merged after `v0.2.8`, so the
  change check passes.
- **Breakage points.** Check names `Run unit tests`, `Hassfest validation`, `HACS validation` are
  kept so any required status checks stay valid. `workflow_call` adds a caller prefix only to
  runs started by Release/Test build.

## 6. Risks

| Risk | Mitigation |
|---|---|
| Someone publishes the draft by hand | documented as forbidden; the zip would be missing so HACS cannot install it |
| Release run fails after tag push but before release | rerun is refused (tag exists, not higher); fix by deleting the tag - documented |
| `git ls-remote` returns peeled `^{}` refs | `--refs` drops them |
| PR merged during a run | `sha` fixed in `prepare`; later jobs use it |
| Test exclusion drops a runtime file | unit test; zip listing compared with the previous rule in review |
| Branch names `claude/...` get no label | defaults to patch, listed under no category; documented branch naming |

**Tests.** Port of the sibling's tests (version logic, zip, workflows) as `unittest`, plus: a zip
leaves out `test_*` files and directories; test build numbering is unit-tested with tags as input.

## 7. Follow-up for the owner (settings, not code)

1. Ruleset on `main`: pull requests only, required checks `Run unit tests`, `Hassfest validation`,
   `HACS validation`; bypass for the owner only for merging.
2. Optional ruleset for branch names (`feature/`, `fix/`, `docs/`, `chore/`, `dependabot/`).

## 8. Best practice checklist

Follows the sibling repository's flow; least-privilege tokens; `persist-credentials: false` where
nothing is pushed; one source of truth for the version (tag) and a check that the zip agrees; no
over-engineering: release logic is the sibling's, minus the library-branch support this repository
does not need.
