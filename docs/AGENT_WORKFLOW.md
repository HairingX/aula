# Agent Workflow Process

This document defines the mandatory workflow that all Claude Code agents must follow when making changes to this codebase. No code changes may be merged or committed without passing through every applicable stage described below.

## Workflow Overview

Every task follows this pipeline:

```
1. PROJECT MANAGEMENT       →  Analyze & plan the task
2. DESIGN DOCUMENT          →  Write a formal design proposal (NO code yet)
3. DESIGN REVIEW            →  Multi-team review of the design document
   ├─ 3a. Architecture      →  Structural fit, patterns, separation of concerns
   ├─ 3b. Code Trace        →  Trace affected flows to verify design won't break them
   ├─ 3c. Performance       →  Will the design introduce bottlenecks or concurrency issues?
   ├─ 3d. Network & Data    →  Are networking and data integrity concerns addressed?
   ├─ 3e. HASS Compliance   →  Does the design align with Home Assistant requirements?
   └─ 3f. Consensus         →  All teams approve or request redesign
4. IMPLEMENTATION           →  Write the code (only after design is approved)
5. QA REVIEW                →  Verify correctness & quality
6. PERFORMANCE REVIEW       →  Check for bottlenecks & concurrency issues in actual code
7. NETWORK & DATA REVIEW    →  Validate networking and data integrity in actual code
8. HASS COMPLIANCE          →  Ensure Home Assistant best practices in actual code
9. FINAL VERIFICATION       →  End-to-end validation before commit
```

**Critical rule:** NO code is written until Stage 3 is fully approved. The design document must be reviewed and accepted by all relevant agent teams first. If a design review team rejects, the process returns to Stage 2 for redesign — not to implementation.

Each stage acts as a gate. If a stage identifies issues, the pipeline returns to the appropriate earlier stage for correction. Changes are not committed until all stages pass.

---

## Stage 1: Project Management Agent

**Role:** Receives the task, analyzes scope, breaks it into sub-tasks, and orchestrates the entire pipeline.

**Responsibilities:**
- Analyze the task requirements and acceptance criteria
- Break complex tasks into discrete, reviewable units of work
- Assign work to the appropriate specialist stages
- Track progress through the pipeline and ensure no stage is skipped
- Escalate ambiguities back to the user before work begins

**Output:** A structured plan with:
- Task description and goals
- List of files likely affected
- Risks and dependencies identified
- Ordered sub-tasks with assigned review stages

---

## Stage 2: Design Document

**Role:** Produce a written design proposal that describes the planned changes **before any code is written**. This document is the input for the multi-team design review in Stage 3.

**When required:**
- **Full design document** — for new features, refactors, architectural changes, or any change touching 3+ files
- **Lightweight design note** — for bug fixes, single-file changes, or config-only changes (a short paragraph covering what/why/where is sufficient)

**The design document must be saved** to `docs/designs/` as a markdown file (e.g., `docs/designs/YYYY-MM-DD-short-description.md`) so it can be referenced during review and in the future.

**Required sections for a full design document:**

### 2a. Problem Statement
- What is the task or problem being solved?
- What are the acceptance criteria?

### 2b. Affected Components
- List every file, class, method, and data flow that will be modified or is likely impacted
- Include a dependency map showing what calls what

### 2c. Proposed Solution
- Describe the planned changes in detail — what will be added, modified, or removed
- Include pseudocode or interface sketches where helpful (NOT actual implementation code)
- Explain design choices and why alternatives were rejected

### 2d. Code Trace Analysis
- For each affected flow (e.g., config flow, data coordinator update, entity refresh), trace the full call path from entry point to output
- Identify every branch, caller, and downstream consumer that touches the changed code
- Mark potential breakage points — places where the proposed change could alter existing behavior
- Document expected behavior before and after the change for each traced flow

### 2e. Risk Assessment
- What could go wrong? List edge cases, failure modes, and backward-compatibility concerns
- What existing tests cover the affected flows?
- What new tests will be needed?

### 2f. Best Practice Checklist
- Does the design follow established project patterns? (Model+Parser, CoordinatorEntity, widget detection, etc.)
- Are naming conventions respected?
- Is the solution minimal — no over-engineering?
- Are there performance or concurrency implications?

**Output:** A design document saved to `docs/designs/` ready for Stage 3 review.

---

## Stage 3: Design Review (Multi-Team)

**Role:** Multiple specialist agent teams review the design document from Stage 2. **No code is written until all teams approve.** This is the most important gate in the process — catching design flaws here is orders of magnitude cheaper than catching them in code.

**Process:** Each sub-team reviews independently and produces a verdict: APPROVE, REQUEST CHANGES, or BLOCK. All teams must approve before proceeding to Stage 4.

### 3a. Architecture Review Team
- Does the design fit the existing architecture?
- Verify adherence to established patterns:
  - Model + Parser pairs for data types
  - Entity base classes (`AulaEntityBase[T]`, `AulaCalendarEntityBase`)
  - Widget detection pattern (`has_widget()`)
  - Coordinator pattern for data fetching
- Assess impact on existing components
- Flag over-engineering or unnecessary abstractions
- Ensure separation of concerns between layers (proxy client → models → coordinators → entities)
- **Reject if:** design violates architectural patterns, introduces circular dependencies, breaks model/parser separation, or adds unnecessary coupling

### 3b. Code Trace Review Team
- Verify the code trace analysis from Section 2d is complete and correct
- Independently trace affected flows through the actual codebase to confirm the design's trace
- Identify any flows the design document missed
- For each breakage point identified, confirm the design accounts for it
- Simulate the change mentally: walk through each affected flow with the proposed changes applied and verify the output remains correct
- **Reject if:** trace is incomplete, flows are missed, or the design would break an existing flow that wasn't accounted for

### 3c. Performance & Concurrency Review Team
- Will the design introduce performance bottlenecks?
- Are there new async/sync boundaries? New blocking calls?
- Could the design cause deadlocks, race conditions, or resource leaks?
- Are coordinator update intervals affected?
- **Reject if:** design introduces foreseeable performance degradation, concurrency hazards, or resource management issues

### 3d. Network & Data Integrity Review Team
- Does the design properly handle network failures in any new or modified HTTP flows?
- Are data transformations (parsing, serialization) preserving correctness?
- Are null/empty cases handled in the design?
- Could the change introduce data loss or corruption?
- **Reject if:** design has unhandled network error paths or data integrity risks

### 3e. HASS Compliance Review Team
- Does the design align with Home Assistant custom component requirements?
- Are HA patterns followed (config flow, entity registration, coordinator pattern)?
- Will the change affect HACS or hassfest validation?
- Are deprecated HA APIs being used where alternatives exist?
- **Reject if:** design conflicts with HA requirements or uses deprecated patterns

### 3f. Consensus Gate
- Collect verdicts from all review teams
- If any team issued REQUEST CHANGES or BLOCK: return to Stage 2 with specific feedback
- The design document is updated, and Stage 3 is repeated
- **Only when all teams APPROVE:** proceed to Stage 4

**Output:** Either:
- **DESIGN APPROVED** — with sign-off from all teams, proceed to implementation
- **REDESIGN REQUIRED** — with specific feedback from each objecting team, return to Stage 2

---

## Stage 4: Implementation

**Role:** Write the actual code changes. **Only begins after Stage 3 design approval.**

**Responsibilities:**
- Follow the plan from Stage 1 and the design approved in Stages 2-3
- Adhere strictly to project conventions:
  - Python 3.14 compatible code
  - 4-space indentation, LF line endings
  - Black formatting with isort (`--profile black`)
  - English for all comments, docstrings, and commit messages
  - unittest framework for tests (not pytest)
  - Test fixtures as JSON files in `aula_proxy/test_messages/`
- Write minimal, focused changes — only what is required for the task
- Include tests for new or changed behavior

---

## Stage 5: QA Review

**Role:** Verify correctness, code quality, and adherence to standards.

**Responsibilities:**

### 5a. Code Quality
- Verify naming conventions are consistent with existing codebase:
  - Classes: `PascalCase`
  - Functions/methods: `snake_case`
  - Constants: `UPPER_SNAKE_CASE`
  - Private members: `_leading_underscore`
- Check method length — flag methods exceeding ~50 lines for potential decomposition
- Verify no unused imports, variables, or dead code is introduced
- Ensure type hints are used consistently with existing patterns

### 5b. Test Verification
- Run the full test suite: `python -m unittest discover -v -s ./custom_components/aula/aula_proxy -p "test_*.py"`
- Verify new tests cover the changed behavior
- Check edge cases: `None` values, empty collections, malformed API responses
- Verify test fixtures are realistic and match actual Aula API response structures

### 5c. Security Review
- Check for OWASP Top 10 vulnerabilities (injection, XSS, etc.)
- Verify no secrets, credentials, or tokens are hardcoded
- Ensure user input is validated at system boundaries (config flow inputs, API responses)
- Check that session handling follows secure practices

### 5d. Formatting Verification
- Run Black and isort to verify formatting compliance
- Verify no trailing whitespace or mixed line endings

**Rejection criteria:**
- Any test failure
- Naming inconsistencies
- Security vulnerabilities
- Formatting violations

---

## Stage 6: Performance Review

**Role:** Identify performance issues, bottlenecks, and concurrency problems.

**Responsibilities:**

### 6a. Performance
- Check for unnecessary API calls or redundant data fetching
- Verify coordinator update intervals are appropriate (data: 5 min, calendar: 10 min)
- Look for O(n²) or worse algorithmic complexity where linear alternatives exist
- Check for unnecessary object creation in hot paths
- Verify lazy loading is used where appropriate

### 6b. Concurrency & Threading
- Verify `async_add_executor_job()` is used correctly for blocking HTTP calls
- Check for potential deadlocks in async/sync bridges
- Ensure thread safety of shared state
- Verify no blocking I/O in the async event loop
- Check that coordinator locks prevent concurrent update races

### 6c. Resource Management
- Verify HTTP sessions are properly managed and closed
- Check for resource leaks (file handles, connections)
- Ensure proper cleanup in error paths and during HA shutdown

**Rejection criteria:**
- Blocking calls in async context without `async_add_executor_job()`
- Potential deadlocks or race conditions
- Resource leaks
- Unnecessary repeated API calls within a single update cycle

---

## Stage 7: Network & Data Integrity Review

**Role:** Validate networking patterns and ensure data correctness.

**Responsibilities:**

### 7a. Network
- Verify proper error handling for HTTP failures (timeouts, 4xx, 5xx)
- Check retry logic is appropriate (not excessive, with backoff)
- Verify SSL/TLS is enforced for all external connections
- Check that the login/session flow handles token expiry gracefully
- Validate proper handling of network interruptions

### 7b. Data Integrity
- Verify parsers handle missing or null fields gracefully
- Check that data transformations preserve correctness (dates, timezones, encodings)
- Ensure no data loss during model conversions
- Verify that API response structures are validated before parsing
- Check that cached data is invalidated appropriately

**Rejection criteria:**
- Unhandled network errors that would crash the integration
- Data corruption or silent data loss
- Missing null/empty checks on external API data

---

## Stage 8: Home Assistant Compliance Review

**Role:** Ensure the integration meets all Home Assistant requirements and best practices.

**Responsibilities:**

### 8a. HASS Integration Standards
- Verify compliance with HA custom component requirements
- Check entity registration follows HA patterns
- Ensure config flow follows HA standards (including error handling, reauth, reconfigure)
- Verify `manifest.json` is correct (version, dependencies, requirements)
- Check that `strings.json` and translations are in sync

### 8b. HASS Best Practices
- Verify use of HA helper functions and utilities where available
- Check that entities properly implement `available`, `should_poll`, `unique_id`
- Ensure proper use of `CoordinatorEntity` pattern
- Verify entities clean up properly on unload
- Check that device info and entity attributes follow HA conventions

### 8c. CI/CD & Distribution
- Verify HACS validation would pass (`hacs-validate.yml`)
- Verify hassfest validation would pass
- Check that GitHub Actions workflows are correct and up to date
- Ensure release workflow compatibility (`release.yml`, `release-dev.yml`)

### 8d. Library Currency
- Check if dependencies in `manifest.json` are current
- Flag deprecated HA APIs or patterns being used
- Suggest upgrades where newer HA APIs provide better functionality

**Rejection criteria:**
- Fails HACS or hassfest validation
- Uses deprecated HA APIs when alternatives exist
- Missing or incorrect translations
- Entity registration that doesn't follow HA patterns

---

## Stage 9: Final Verification

**Role:** End-to-end validation that all stages passed and the change is ready.

**Responsibilities:**
- Confirm all previous stages have passed without unresolved issues
- Run the full test suite one final time
- Verify the change set is minimal and focused (no unrelated modifications)
- Ensure commit message accurately describes the change
- Verify no temporary debug code, TODOs, or commented-out code remains
- Confirm formatting is clean (Black + isort)

**Output:** Either:
- **APPROVED** — The change is ready to commit
- **REJECTED** — With specific issues and the stage to return to

---

## How Agents Must Apply This Process

When an agent receives a task:

1. **Read this document first** — before making any changes
2. **Execute each stage sequentially** — use sub-agents for specialist reviews where possible
3. **NEVER write code before the design is approved** — Stages 2-3 must complete before Stage 4
4. **Save design documents to `docs/designs/`** — they are permanent project artifacts
5. **Document findings at each stage** — so the user can see what was checked
6. **Do not skip stages** — even for "trivial" changes, at minimum do a lightweight pass of each stage
7. **Return to earlier stages when issues are found** — iterate until all stages pass
8. **Report the final status** — summarize what was checked and the outcome

### Lightweight vs. Full Review

For small changes (typo fixes, single-file bug fixes, config-only changes):
- Stage 2 may be a short design note (a paragraph) instead of a full document
- Stage 3 review teams do a quick sanity check rather than full analysis
- Stages 5-8 must always be done in full

For significant changes (new features, refactors, architectural changes, multi-file changes):
- All stages must be done in full
- Stage 2 must produce a complete design document with all sections
- Stage 3 must have explicit APPROVE/REJECT from each review team
- If any review team rejects, return to Stage 2 and redesign before touching any code

---

## Reference

- Project architecture: `docs/overview/01-ARCHITECTURE.md`
- Data flow: `docs/overview/03-DATA-FLOW.md`
- Project conventions: `CLAUDE.md`
- CI workflows: `.github/workflows/`
- HA integration requirements: https://developers.home-assistant.io/docs/creating_integration_manifest
