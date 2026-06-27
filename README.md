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

**What the tests cover** (`tests/test_pawpal.py`, 50 tests):

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
collected 50 items

tests\test_pawpal.py ..................................................  [100%]

============================= 50 passed in 0.06s ==============================
```

**Confidence level: ★★★★☆ (4/5).** The core scheduling, sorting, filtering,
recurrence, and conflict logic are well covered by 50 passing tests, including
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

## 📸 Demo Walkthrough

Launch the app with `streamlit run app.py`.

### Main UI features and what you can do

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
