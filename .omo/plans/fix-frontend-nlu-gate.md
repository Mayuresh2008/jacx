# fix-frontend-nlu-gate - Work Plan

## TL;DR (For humans)

**What you'll get:** Fix all 6 failing manual commands so they execute locally without AI fallback. The backend NLU already handles them perfectly (106/106 tests pass) — only the frontend regex gate needs updating.

**Why this approach:** The frontend `InputArea.tsx` has its own `STEP1_COMMAND_PATTERNS` regex array that acts as a gatekeeper. If a command doesn't match any frontend regex, it goes to the AI chat stream instead of the `/v1/step1/commands/execute` endpoint. The backend is correct; the frontend gate is incomplete.

**What it will NOT do:** No backend changes. No new NLU patterns. No new tools. No AI model changes.

**Effort:** Short
**Risk:** Low — frontend-only regex additions, backend already verified with 106 passing tests
**Decisions to sanity-check:** None — the backend patterns are the source of truth, frontend just needs to match them

Your next move: approve this plan. Full execution detail follows below.

---

> TL;DR (machine): Short effort, low risk. Update frontend STEP1_COMMAND_PATTERNS regexes in InputArea.tsx to cover all NLU patterns the backend already handles. 1 todo + verification.

## Scope
### Must have
- Update `STEP1_COMMAND_PATTERNS` in `frontend/src/components/Chat/InputArea.tsx` to cover all 6 failing command patterns
- Add patterns for: `pull up`, `bring up`, `show me`, `take me to`, `head to` as website-in-browser action verbs
- Add pattern for: `use/with/in X to/for Y on Z` browser-to-search without requiring "and"
- Add pattern for: `official page for X` requests
- All existing passing commands must continue to work (regression check)

### Must NOT have (guardrails, anti-slop, scope boundaries)
- No changes to backend Python code (nlu_parser.py, orchestrator.py, command_parser.py)
- No new regex patterns beyond what the backend already supports
- No changes to the `/v1/step1/commands/execute` endpoint
- No new dependencies or packages
- No changes to test files

## Verification strategy
> Zero human intervention - all verification is agent-executed.
- Test decision: tests-after + existing pytest suite
- Evidence: `.omo/evidence/` directory

## Execution strategy
### Parallel execution waves
> Target 5-8 todos per wave. Fewer than 3 (except the final) means under-split.

Wave 1: Single todo — update frontend regexes
Wave 2: Verification — run backend tests + manual UI test

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| 1 | none | F1-F4 | — |

## Todos
> Implementation + Test = ONE todo. Never separate.

- [ ] 1. Update frontend STEP1_COMMAND_PATTERNS to cover all NLU command variants
  What to do / Must NOT do:
  - Edit `frontend/src/components/Chat/InputArea.tsx`, specifically the `STEP1_COMMAND_PATTERNS` array (lines 52-90)
  - Add new patterns for the 6 failing commands. The backend already handles these — we're just making the frontend send them to the right endpoint.
  - MUST add these specific patterns:
    1. **"Pull up Netflix using Google"** / **"Bring up YouTube in Brave"** / **"Show me X on Y"** / **"Take me to X using Y"** / **"Head to X"**: Add `pull up|bring up|show me|take me to|head to` to the website-in-browser pattern's action verbs list
    2. **"Use Brave to hunt for GTA V on Steam"** / **"With Chrome, look for React dashboard on GitHub"**: Add a new pattern for `use/with/in <browser> (to) <search verb> <query> on <platform>` — this does NOT require "and"
    3. **"find the official page for instagram on whichever browser you want"**: Add a pattern for `official (page|website|site) for <entity>` requests
  - MUST NOT change any existing patterns that already work
  - MUST NOT modify backend Python files
  - MUST NOT add patterns for commands the backend doesn't support
  Parallelization: Wave 1 | Blocked by: none | Blocks: F1-F4
  References:
    - `frontend/src/components/Chat/InputArea.tsx:52-90` — the STEP1_COMMAND_PATTERNS array
    - `frontend/src/components/Chat/InputArea.tsx:92-101` — the matchesStep1Command function
    - `frontend/src/components/Chat/InputArea.tsx:103-128` — the executeStep1Command function
    - `src/openjarvis/step1/nlu_parser.py:835-926` — _parse_nlu_open_website_in_browser (backend pattern for "Pull up X using Y")
    - `src/openjarvis/step1/nlu_parser.py:445-511` — _parse_nlu_browser_to_search (backend pattern for "Use X to hunt for Y on Z")
    - `src/openjarvis/step1/nlu_parser.py:934-986` — _parse_nlu_official_page (backend pattern for "official page for X")
  Acceptance criteria (agent-executable):
    - All 6 commands match STEP1_COMMAND_PATTERNS: `matchesStep1Command("Pull up Netflix using Google").matched === true`
    - All 6 commands match: `matchesStep1Command("Use Brave to hunt for GTA V on Steam").matched === true`
    - All 6 commands match: `matchesStep1Command("With Chrome, look for React dashboard on GitHub").matched === true`
    - All 6 commands match: `matchesStep1Command("Bring up YouTube in Brave").matched === true`
    - All 6 commands match: `matchesStep1Command("find the official page for instagram on whichever browser you want").matched === true`
    - All 6 commands match: `matchesStep1Command("find the official page for carta using whichever browser is available").matched === true`
    - Existing passing commands still match (no regression)
    - Backend tests still pass: `python -m pytest tests/step1/test_step4.py -v` → 106 passed
  QA scenarios:
    - Happy: `python -m pytest tests/step1/test_step4.py -v` → 106 passed (backend unchanged)
    - Happy: Create a small inline test script that imports matchesStep1Command and verifies all 6 commands return `{matched: true}`
    - Failure: Verify "Pull up Netflix using Google" now routes to `/v1/step1/commands/execute` not AI chat
  Commit: Y | fix(frontend): add missing NLU command patterns to STEP1_COMMAND_PATTERNS

## Final verification wave
> Runs in parallel after ALL todos. ALL must APPROVE. Surface results and wait for the user's explicit okay before declaring complete.
- [ ] F1. Plan compliance audit — all 6 commands route to Step 1 endpoint, not AI chat
- [ ] F2. Code quality review — regexes are correct, no false positives on unrelated commands
- [ ] F3. Real manual QA — run `start-step1.bat`, test all 6 commands in the UI
- [ ] F4. Scope fidelity — no backend changes, no new dependencies, no test modifications

## Commit strategy
Single commit: `fix(frontend): add missing NLU command patterns to STEP1_COMMAND_PATTERNS`

## Success criteria
- All 6 manual test commands execute locally (ai_called=false) without AI fallback
- No "AI fallback unavailable" messages
- No API-key errors
- No whole-sentence Google searches for recognized commands
- All 106 backend tests still pass
- No regression on existing working commands
