# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## ✨ Features

PawPal+ implements the following algorithms in `pawpal_system.py` (all surfaced
in the Streamlit UI):

- **Sorting by time** — `Scheduler.sort_by_time()` returns tasks in chronological
  order by their fixed time; flexible (untimed) tasks sort last.
- **Priority-aware scheduling** — `sort_tasks()` orders by priority (high first),
  with shorter tasks winning ties so more tasks fit the day.
- **Filtering** — `filter_tasks()` filters by pet and/or completion status;
  `filter_by_recurrence()` selects only tasks active on a chosen weekday.
- **Time-budget filtering** — `filter_by_budget()` greedily keeps tasks that fit
  the owner's available minutes and records a reason for each one skipped.
- **Conflict warnings** — `detect_conflicts()` flags tasks booked at the same
  fixed time and returns warning messages (it never crashes the app).
- **Fixed-time anchoring & overlap handling** — `assign_times()` anchors
  fixed-time tasks, fills flexible ones into the earliest open slot, and skips
  tasks that overlap or fall outside the available window.
- **Buffer between tasks** — an optional gap so the owner isn't expected to
  switch from one task to the next instantly.
- **Daily / weekly recurrence** — completing a recurring task
  (`Pet.complete_task()` → `Task.next_occurrence()`) automatically creates the
  next occurrence with its due date advanced via `timedelta`.
- **Priority-then-time scheduling** — `sort_by_priority_then_time()` orders by
  priority first and breaks ties by the earlier clock time.
- **Next available slot** — `next_available_slot(duration)` answers "when can I
  fit a 30-minute task today?" by scanning the gaps in the current plan.
- **Data persistence** — `save_to_json()` / `load_from_json()` remember pets and
  tasks between runs via a `data.json` file.
- **Plan explanation** — every plan reports what was scheduled, what was skipped
  and why, and total time used.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Running the terminal testing ground (`python main.py`) produces the plan below.
It builds a day for one owner (Jordan) with two pets (Mochi the dog, Luna the
cat) and six tasks, then schedules them around their constraints:

```
================================================
  Today's Schedule for Jordan
  Pets: Mochi, Luna
================================================
  08:00-08:30  Morning walk  (Mochi, 30 min, high)
  08:30-08:45  Play time  (Luna, 15 min, medium)
  08:45-08:55  Litter cleanup  (Luna, 10 min, low)
  09:00-09:10  Feeding  (Mochi, 10 min, high)
  09:10-09:30  Training session  (Mochi, 20 min, medium)
================================================
Plan for Jordan (Mon): scheduled 5 task(s) using 85 of 120 available minutes.
```

Notice that the two fixed-time tasks (Litter cleanup at 08:45, Feeding at
09:00) are anchored to their times while the flexible tasks fill the gaps
around them, and the Sunday-only "Weekly grooming" task is correctly left out
on a Monday.

## 🧪 Testing PawPal+

Run the full automated test suite from the project root:

```bash
python -m pytest
```

**What the tests cover** (`tests/test_pawpal.py` + `tests/test_app_ui.py`,
62 collected tests in the
latest verified run):

- **Time helpers** — `parse_time`/`format_time` round-trips and rejection of bad input
- **Domain model** — priority ordering, `is_fixed`, `is_active_on`, `mark_complete`, `Pet.add_task`
- **Sorting correctness** — `sort_by_time` returns tasks in chronological order (flexible tasks last); priority sort with duration tie-breaks
- **Filtering** — `filter_tasks` by pet name, by completion status, and combined
- **Recurrence logic** — completing a daily task creates a new task due the next day; weekly advances a week; one-off tasks don't regenerate; completing twice spawns two future tasks
- **Conflict detection** — `detect_conflicts` flags duplicate fixed times (including across different pets) and stays quiet when times differ
- **Scheduling pipeline** — budget filtering, fixed-time anchoring/collisions, buffers, fixed-time window checks, completed-task exclusion, and full `build_plan` integration
- **Edge cases** — a pet with no tasks, empty/single-item lists, zero available time

Successful run:

```
============================= test session starts =============================
platform win32 -- Python 3.14.4, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\Erik Gallardo\Desktop\codepath-ai\ai110-module2show-pawpal-starter
plugins: anyio-4.14.1
collected 62 items

tests\test_app_ui.py ...                                                         [  4%]
tests\test_pawpal.py ...........................................................  [100%]

============================= 62 passed in 1.05s ==============================
```

**Confidence level: ★★★★☆ (4/5).** The core scheduling, sorting, filtering,
recurrence, and conflict logic are well covered by 62 passing tests, including
the main edge cases. I held back the fifth star because conflict detection only
catches exact same-time clashes (duration overlaps are handled separately in
`assign_times`), recurrence date math hasn't been stress-tested across DST or
leap-year boundaries, and there are no UI-level tests for `app.py`.

## 📐 Smarter Scheduling

All scheduling lives in `pawpal_system.py`. The core plan is built by a pipeline
inside `Scheduler.build_plan()`: drop completed → filter by recurrence → sort →
filter by budget → assign times. On top of that, several standalone algorithmic
methods support sorting, filtering, conflict detection, and recurrence.

### Sorting behavior

- **`Scheduler.sort_by_time()`** — orders tasks chronologically by their
  `fixed_time`, using a lambda key that converts each `"HH:MM"` string to
  minutes (`parse_time`). Flexible tasks (no fixed time) sort to the end.
- **`Scheduler.sort_tasks()`** — the scheduling sort: highest priority first,
  shorter task wins ties so more tasks fit.

### Filtering behavior

- **`Scheduler.filter_tasks(pet_name=..., completed=...)`** — filters a task
  list by pet name, completion status, or both (each filter is optional).
- **`Scheduler.filter_by_recurrence()`** + **`Task.is_active_on()`** — keeps
  only the tasks active on the requested weekday (`days` field; `None` = every
  day), selected via `build_plan(day_of_week=...)`.
- **`Scheduler.filter_by_budget()`** — best-effort greedy fill: skips a task
  that won't fit the time budget but keeps trying later, shorter ones; each
  skip carries a reason.

### Conflict detection

- **`Scheduler.detect_conflicts()`** — a lightweight check that returns warning
  **strings** (never crashes) when two tasks share the same `fixed_time`. Catches
  exact start-time clashes for an early heads-up.
- **`Scheduler.assign_times()` / `_find_slot()`** — the real overlap safety net:
  anchors fixed-time tasks, fills flexible tasks into the earliest open gap, and
  skips any task whose interval would overlap one already placed (full
  duration-aware overlap, not just exact matches).

### Recurring task logic

- **`Task.next_occurrence()`** — returns a fresh, uncompleted copy of a
  recurring task with its `due_date` advanced via `timedelta` (`daily` → +1 day,
  `weekly` → +1 week); returns `None` for one-off tasks.
- **`Pet.complete_task()`** — marks a task done and, if it recurs, automatically
  creates and attaches the next occurrence to the pet.

### Other constraints

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Buffer between tasks | `Scheduler(buffer_minutes=...)`, `_find_slot` | Optional gap between consecutive tasks so the owner isn't expected to switch instantly |
| Fixed-time window check | `assign_times` | Skips fixed-time tasks that fall outside the owner's available window |
| Completed tasks | `Task.mark_complete`, `build_plan` | Done tasks are excluded from today's plan, freeing their time for others |
| Next available slot | `next_available_slot(duration)` | Finds the earliest opening big enough for a new task in today's plan |

### Priority-then-time scheduling (CLI example)

`Scheduler.sort_by_priority_then_time()` orders the most important tasks first,
then by the earlier clock time (untimed tasks last). From `python main.py`:

```
╭────────────────────┬────────────┬────────┬───────┬────────────╮
│ Task               │ Priority   │ Time   │ Pet   │ Status     │
├────────────────────┼────────────┼────────┼───────┼────────────┤
│ 🦮 Morning walk     │ 🔴 HIGH     │ 08:00  │ Mochi │ ⏰ fixed    │
│ 🍖 Feeding          │ 🔴 HIGH     │ 09:00  │ Mochi │ ⏰ fixed    │
│ 🎓 Training session │ 🟡 MEDIUM   │ 11:00  │ Mochi │ ⏰ fixed    │
│ 🎾 Play time        │ 🟡 MEDIUM   │ —      │ Luna  │ 🕒 flexible │
│ 🧹 Litter cleanup   │ 🟢 LOW      │ 09:00  │ Luna  │ ⏰ fixed    │
│ 🛁 Weekly grooming  │ 🟢 LOW      │ —      │ Luna  │ 🕒 flexible │
╰────────────────────┴────────────┴────────┴───────┴────────────╯
```

Both HIGH tasks come before all MEDIUM tasks, which come before LOW — and within
each priority the earlier fixed time wins.

## 💾 Data Persistence

PawPal+ can remember pets and tasks between runs by saving them to a JSON file.

- **Methods (`pawpal_system.py`):** `save_to_json(path, owner, pets)` writes the
  owner and every pet (with its tasks) to disk; `load_from_json(path)` reads them
  back and returns `(owner, pets)`.
- **How serialization works:** JSON can't directly encode our dataclasses, the
  `Priority` enum, or `date` objects, so the module converts each object to a
  plain dict first (helpers `_task_to_dict`, `_pet_to_dict`, `_owner_to_dict` and
  their `_from_dict` partners). Enums are stored as ints, dates as ISO strings,
  and tuples as lists; everything is reversed on load.
- **File written:** `data.json` (git-ignored, since it's runtime data).
- **Files modified for this feature:** `pawpal_system.py` (the methods),
  `main.py` (a save → load round-trip demo), `.gitignore` (ignore `data.json`),
  and `tests/test_pawpal.py` (round-trip tests).

```python
from pawpal_system import save_to_json, load_from_json
save_to_json("data.json", owner, pets)        # before quitting
owner, pets = load_from_json("data.json")      # next run
```

## 🎨 CLI Output Formatting

The terminal demo (`main.py`) uses friendly, structured output:

- **`tabulate`** (added to `requirements.txt`) renders the task and schedule
  tables with the `rounded_grid` style.
- **Task-type emojis** — 🦮 walk, 🍖 feeding, 💊 meds, 🛁 grooming, 🎾 play,
  🎓 training, 🧹 cleanup, 🩺 vet (matched by keyword in `type_emoji()`).
- **Color-coded priority dots** — 🔴 HIGH, 🟡 MEDIUM, 🟢 LOW (`PRIORITY_DOT`).
- **Status icons** — ✅ done, ⏰ fixed-time, 🕒 flexible (`status_icon()`).
- `main.py` reconfigures stdout to UTF-8 so the emojis render on Windows
  terminals that default to cp1252.

## 📸 Demo Walkthrough

Launch the app with `streamlit run app.py`.

### Main UI features and what you can do

## Portfolio README

### Original Project

PawPal+ started as the Module 1-3 pet-care planner project. Its original goal was to help a busy pet owner organize daily pet tasks, respect time and priority constraints, and generate a readable schedule that explains what fit and what did not.

At its core, the original system handled owner/pet setup, task entry, priority-aware scheduling, recurrence, conflict warnings, and JSON persistence. The current version keeps that foundation and extends it with an AI assistant that can answer planning questions in context.

### Title and Summary

**PawPal+** is a Streamlit-based pet-care planning assistant. It matters because it turns a list of pet chores into an actionable schedule and then layers AI on top so the user can ask planning questions, get a grounded answer, and see a fallback when the model output is unreliable.

GitHub artifact: [PawPal+ code repository](https://github.com/egall18/ai110-module2show-pawpal-starter)

### Architecture Overview

The project is organized around a small set of cooperating parts:

- The Streamlit UI in `app.py` collects user input, builds pet context, and displays schedules and AI answers.
- The scheduler in `pawpal_system.py` turns tasks into a daily plan and explains what was scheduled or skipped.
- The reliability helpers in `ai_reliability.py` validate questions and check whether AI answers are grounded in known task data.
- The evaluator in `ai_eval.py` runs sample checks so the AI behavior can be tested consistently.
- The system diagram in `diagrams/system_diagram.mmd` shows the data flow from user input to AI routing, fallback, testing, and human review.

In short: input comes from the user, planning context is assembled, the AI provider is chosen, the response is checked, and the app either shows the model answer or a deterministic scheduler-based fallback.

### Setup Instructions

1. Create and activate a virtual environment.

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install the dependencies.

```bash
pip install -r requirements.txt
```

3. Add your local API keys in `.env` if you want to use Gemini, OpenAI, or Claude.

4. Run the Streamlit app.

```bash
streamlit run app.py
```

5. Run the tests and the reliability evaluator.

```bash
python -m pytest
python ai_eval.py
```

### Sample Interactions

Example 1: schedule planning

```text
Input: What is the best plan for my dog today? Include time, place, priority, completion status, and duration.
Expected AI output: a schedule-style answer that mentions the dog's tasks, when they happen, where they happen, and why they were chosen.
```

Example 2: constrained planning

```text
Input: If I only have 30 minutes, which tasks should I do now?
Expected AI output: a short recommendation that picks the highest-value tasks that fit the time window and explains the trade-off.
```

Example 3: reliability fallback

```text
Input: an empty or overly long assistant question
Expected AI output: the app blocks the request with a guardrail message instead of sending an unsafe query to a model.
```

### 4b) Reproducible Execution Evidence

The evidence below is text-based so a grader can verify behavior without a
video. It includes command output plus three representative AI reliability
cases.

```bash
$ python -m pytest -q
..................................................................       [100%]
66 passed in 1.16s

$ python ai_eval.py
[PASS] good_answer
[PASS] missing_required_details
  - Missing required planning detail(s): time, place, priority, duration
[PASS] not_grounded_in_task_titles
  - No known task title from context was mentioned.

Summary: 3/3 checks matched expected behavior.
```

| Test input | Behavior checked | Result |
|---|---|---|
| `Start with Morning walk at time 08:00 in the place Park. Its priority is high and duration is 30 minutes.` | Grounded answer should mention a known task and required planning details | `PASS` |
| `Do a quick walk and feeding soon.` | Guardrail should flag missing planning details and fall back safely | `PASS` |
| `Time is 08:00, place home, priority high, duration 30 min. start with exercise.` | Response should be rejected if it is not grounded in a known task title | `PASS` |

These checks demonstrate the AI behavior end to end: the assistant uses task
context, the reliability layer evaluates the answer, and the app falls back
when the output is weak or ungrounded.

### Design Decisions

I kept the original scheduler as the source of truth for planning and used AI as a helper, not as the only decision-maker. That makes the system more reliable because the deterministic scheduler still produces a valid plan if a model fails or gives a weak answer.

I also chose a multi-provider design with Gemini, OpenAI, and Claude support because provider access, quotas, and model behavior can vary. The trade-off is more branching and more configuration, but the payoff is better resilience and easier demos.

Another deliberate trade-off is the output guardrail. Rather than trusting every AI answer, the app checks for grounded task titles and required planning terms before showing the result. That makes the experience safer, even if it occasionally falls back to the local summary.

### Testing Summary

The project currently passes the full test suite, including scheduler logic, recurrence, UI smoke tests, and the new AI reliability checks. The reliability evaluator also runs sample checks that show when an answer passes or fails the guardrail.

What worked well was the separation between deterministic scheduling and AI response checking. What was weaker earlier in the process was unstructured assistant output, which is why the guardrail and fallback path were added.

I learned that the best way to make AI useful in an app is to place it inside a system with checks, not to let it operate alone.

### Reflection

This project taught me that AI features are strongest when they are constrained by real system logic, tested like software, and backed by clear fallback behavior. It also showed me that the same project can support both a deterministic planner and a conversational assistant without sacrificing reliability.

What this project says about me as an AI engineer: I build AI systems as
products, not demos. I care about grounding, validation, fallback behavior, and
reproducible testing, which means I optimize for trustworthiness and
maintainability as much as for model quality.

The graded responsible-AI reflection belongs in `model_card.md`, not here, so this README stays focused on project understanding, setup, and implementation details for reviewers and employers.

See [model_card.md](model_card.md) for the graded responsible-AI reflection.

- **Owner** — set your name, the time your day starts (`HH:MM`), and how many
  minutes you have available today (your time budget).
- **Add a Pet** — create one or more pets (name + species). Pets persist in the
  session so you can build up a household.
- **Schedule a Task** — for a chosen pet, add a task with a duration, priority,
  an optional fixed time, and an optional **Repeats** setting (daily/weekly).
- **Task tables** — each pet's tasks are shown **sorted by time**, with priority,
  repeat setting, and a done indicator.
- **Conflict warnings** — if two tasks share a fixed time, a yellow warning
  appears above the tables (and again next to the plan).
- **Mark a task complete** — finishing a recurring task automatically creates its
  next occurrence; a success message shows the new due date.
- **Build Schedule** — pick a day and generate a time-ordered plan with a "Why"
  for each task, a list of anything not scheduled (with reasons), and a full
  plan explanation.

### Example workflow

1. Enter the owner (e.g. *Jordan*, start `08:00`, 120 minutes available).
2. Add a pet → *Mochi (dog)*. Add another → *Luna (cat)*.
3. Schedule tasks: a high-priority *Morning walk* (30 min, daily) for Mochi, a
   *Feeding* fixed at `09:00`, and a *Play time* (15 min) for Luna.
4. Review the **sorted** task tables and any **conflict warning**.
5. Mark *Morning walk* complete → its next daily occurrence is created
   automatically.
6. Click **Generate schedule** to see today's time-ordered plan and reasoning.

### Key Scheduler behaviors shown

- **Sorting by time** — tasks always display and schedule in chronological order.
- **Conflict warnings** — two tasks at the same fixed time are flagged.
- **Fixed-time anchoring + skips** — fixed tasks lock to their time; tasks that
  don't fit the budget, overlap, or fall outside the window are skipped with a
  reason.
- **Recurrence** — completing a daily/weekly task regenerates the next one.

### Sample CLI output (`python main.py`)

The terminal demo exercises the same logic without the UI:

```
====================================================
  Tasks sorted by time
====================================================
      08:00  Morning walk (Mochi)
      09:00  Feeding (Mochi)
      09:00  Litter cleanup (Luna)
      11:00  Training session (Mochi)
   flexible  Play time (Luna)
   flexible  Weekly grooming (Luna)

====================================================
  Filter: only Mochi's tasks
====================================================
  - Training session
  - Morning walk
  - Feeding

====================================================
  Conflict detection
====================================================
  WARNING: Conflict at 09:00: Feeding, Litter cleanup are scheduled at the same time.

====================================================
  Recurring task regeneration
====================================================
  Before: Mochi has 3 tasks; 'Morning walk' completed=False
  Completed 'Morning walk' -> spawned next occurrence due 2026-06-27
  After:  Mochi has 4 tasks

====================================================
  Today's Schedule (Mon)
====================================================
  08:00-08:30  Morning walk (Mochi)
  08:35-08:50  Play time (Luna)
  09:00-09:10  Feeding (Mochi)
  09:15-09:40  Weekly grooming (Luna)
  Not scheduled:
    - Training session: Fixed time 11:00 is outside the available window (08:00-11:00)
    - Litter cleanup: Fixed time 09:00 conflicts with another task

Plan for Jordan (Mon): scheduled 4 task(s) using 80 of 180 available minutes.
```

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->

## Project 4 (Applied AI System) Rubric Coverage

### 1) Base project + original scope

- **Base project:** PawPal+ pet care planner.
- **Original goal:** collect owner/pet/task inputs and generate a daily care plan
  under time/priority constraints.
- **Original capabilities:** scheduling pipeline, conflict warnings, recurrence,
  persistence, and Streamlit UI interactions.

### 2) Substantial new AI feature (reliability mechanism)

PawPal+ extends the base planner with an **AI reliability harness** integrated
into the UI flow:

- **Provider failover:** routes through Gemini/OpenAI/Claude and automatically
  falls back when a provider fails.
- **Input guardrail:** validates custom questions (non-empty, max length).
- **Output guardrail:** checks whether AI output is grounded in known task
  titles and includes required planning details (`time`, `place`, `priority`,
  `duration`).
- **Deterministic fallback:** if checks fail, the app shows a scheduler-based
  local answer instead of low-quality model output.

Implementation files:

- `app.py` (provider routing + guardrails + fallback UI behavior)
- `ai_reliability.py` (pure reliability checks)
- `ai_eval.py` (evaluation harness)

### 3) System architecture diagram

- Data-flow Mermaid source: `diagrams/applied_ai_architecture.mmd`
- Class UML: `diagrams/uml_final.mmd`

The applied-AI architecture diagram shows full flow from user input to
provider routing, reliability checks, and fallback output.

### 4) Functional end-to-end demonstration

Run the full system:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Run tests:

```bash
python -m pytest
```

Run reliability evaluator:

```bash
python ai_eval.py
```

Example assistant prompts (in the UI):

```text
1) What is the best plan for my dog today? Include time, place, priority, completion status, and duration.
2) Which tasks are high priority and what should happen first?
3) If I only have 30 minutes, which tasks should I do now?
```

### 5) Reliability / evaluation / guardrail evidence

Reliability examples (input -> behavior -> result):

```text
Input: empty question
Behavior: input guardrail blocks request
Result: warning shown; no provider call is made
```

```text
Input: provider returns 429 or 404
Behavior: failover tries the next configured provider
Result: AI answer from fallback provider, or local deterministic summary if all fail
```

```text
Input: AI answer omits task grounding or misses required details
Behavior: output reliability check fails
Result: app warns and replaces AI answer with local scheduler-based fallback
```

```text
Input: any assistant request (including failures)
Behavior: structured event logging to ai_events.jsonl
Result: reproducible audit trail with provider attempts, latency, and guardrail outcomes
```

Runtime logging details:

- Log file: `ai_events.jsonl`
- Writer: `ai_logging.py`
- Events include: request blocked, provider error, quality-guardrail failure,
  successful AI output, and local fallback path
- Safety: logs never store API keys or full context payloads

### 6) Documentation and setup instructions

This README includes:

- project goals and capabilities,
- install/run/test steps,
- sample workflows and outputs,
- Project 4 reliability architecture and evaluation instructions.

### 7) Reflection

See `reflection.md` for:

- how AI was used for prompting/debugging/design,
- examples of helpful and flawed suggestions,
- limitations and future improvement ideas.
