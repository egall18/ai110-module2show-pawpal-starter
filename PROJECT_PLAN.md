# PawPal+ — Project Plan & Status

> Working notes: what the project is, what already exists, and what still needs building.
> Last reviewed: 2026-06-26

## Goal (from the scenario)

A **Streamlit app** that helps a busy pet owner plan daily care tasks. The app should:

- Capture **owner + pet** info
- Let the user **add/edit tasks** (duration + priority at minimum)
- **Generate a daily schedule** that picks and orders tasks based on constraints (time available, priority, preferences)
- **Display the plan clearly** and ideally **explain the reasoning**
- Include **tests** for the most important scheduling behaviors

Intended flow: **design (UML) → class stubs → scheduling logic → tests → wire into UI → refine UML**.

---

## Core User Actions

The minimum viable loop — **profile → tasks → plan**:

1. **Set up an owner + pet profile** — enter owner name, available time budget, and pet info (name, species, preferences). Backed by `Owner` + `Pet`.
2. **Add / manage care tasks** — add, edit, and remove tasks with at minimum a duration and priority. Backed by `Task`.
3. **Generate & view today's plan** — produce a time-ordered daily plan that respects priority and the time budget, with an explanation of why each task was chosen and placed. Backed by `Scheduler` + `Plan`.

These form a dependency chain (each step needs the previous one) and double as the README demo walkthrough.

---

## Current State (inventory)

| File | Status | Notes |
|------|--------|-------|
| `README.md` | ✅ Present | Scenario + instructions; several template sections to fill (sample output, smarter-scheduling table, demo walkthrough) |
| `app.py` | ⚠️ Thin UI only | Collects owner/pet/task inputs; "Generate schedule" button only shows a "Not implemented" warning — nothing to call yet |
| `diagrams/uml.mmd` | ❌ Placeholder | Generic `ClassName`/`AnotherClass` skeleton — no real design |
| `requirements.txt` | ✅ Present | `streamlit>=1.30`, `pytest>=7.0` |
| `ai_interactions.md` | ❌ Empty template | Stretch-only; not required for core |
| `reflection.md` | ❌ Empty template | To fill at the end |
| Backend Python logic | ❌ Missing | No `Task`/`Pet`/`Owner`/`Scheduler` classes exist |
| Test suite | ❌ Missing | No `tests/` or `test_*.py` files |

**Bottom line:** UI shell + docs scaffolding exist. All domain logic, the scheduler, and tests are **unbuilt**.

---

## What Needs Building

### 1. Domain model (Python classes)
Proposed starting design (refine in UML first):

- **`Task`** — `title`, `duration_minutes`, `priority` (low/med/high), optional `fixed_time`, `category`, `recurring`
- **`Pet`** — `name`, `species`, optional preferences/needs
- **`Owner`** — `name`, available time window / daily minutes budget, preferences
- **`Scheduler`** — takes tasks + constraints, produces an ordered `Plan`
- **`Plan` / `ScheduledTask`** — task + assigned start time; plus a human-readable explanation

### 2. Scheduling logic
Per the README's "Smarter Scheduling" table:

- [ ] **Task sorting** — by priority, then duration (tie-breaks)
- [ ] **Filtering** — skip/defer tasks when the time budget runs out
- [ ] **Conflict handling** — avoid overlapping time slots; honor fixed-time tasks
- [ ] **Recurring tasks** — daily vs. weekly handling
- [ ] **Explanation** — why each task was chosen and when (the "explain the plan" requirement)

### 3. Tests (`pytest`)
- [ ] High-priority tasks scheduled before low-priority
- [ ] Tasks dropped/deferred when total duration exceeds available time
- [ ] No overlapping time slots
- [ ] Fixed-time tasks land at their fixed time
- [ ] Edge cases: empty task list, zero time available, ties

### 4. UI wiring (`app.py`)
- [ ] Replace the "Not implemented" warning: call the real scheduler on "Generate schedule"
- [ ] Render the resulting plan (time-ordered) and the explanation
- [ ] Optional: edit/remove tasks, owner time-budget input

### 5. Docs to finish
- [ ] `diagrams/uml.mmd` — replace placeholder with real classes/relationships, keep in sync with code
- [ ] `README.md` — fill sample output, smarter-scheduling table, demo walkthrough
- [ ] `reflection.md` — complete at the end
- [ ] `ai_interactions.md` — only if attempting stretch features

---

## Suggested Build Order

1. Draft real UML in `diagrams/uml.mmd`
2. Create class stubs (no logic) in a `pawpal/` package or single module
3. Implement scheduling logic incrementally (sort → filter → conflicts → explain)
4. Add `pytest` tests alongside each behavior
5. Wire scheduler into `app.py`
6. Fill in README sample output + tables, then `reflection.md`
