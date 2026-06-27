# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

I started by identifying the three core actions a user should be able to perform, since they define the minimum useful loop of the app:

1. **Set up an owner and pet profile.** The user enters their own name and how much time they have available today, along with basic pet info (name, species, any preferences or needs). This gives the app the context and the time budget it needs before it can plan anything.
2. **Add and manage care tasks.** The user can add, edit, and remove care tasks — things like walks, feeding, medication, or grooming. Each task carries at minimum a duration and a priority, which are the inputs the scheduler reasons about.
3. **Generate and view today's plan.** The user asks the app to build a daily plan. It produces a time-ordered schedule that respects task priority and the owner's available time, and it explains why each task was chosen and when it was placed (including what got skipped if there wasn't enough time).

These actions form a dependency chain — profile first, then tasks, then the plan — and each one maps onto a class in my initial UML:

- **`Owner`** holds the owner's name, available time budget, start time, and preferences.
- **`Pet`** holds the pet's name, species, and care needs.
- **`Task`** represents a single care task with a title, duration, priority, category, and optional fixed time or recurrence.
- **`Priority`** is an enumeration (low / medium / high) so priority comparisons are consistent.
- **`Scheduler`** is the engine: it takes the owner and the list of tasks and runs sorting, time-budget filtering, and time assignment to build a plan. I deliberately split these into small methods so each scheduling behavior can be tested on its own.
- **`Plan`** is the result — the scheduled tasks, any skipped tasks, and a human-readable explanation.
- **`ScheduledTask`** wraps a task with its assigned start/end time and the reason it was placed there.

**b. Design changes**

Yes. Before writing any scheduling logic, I reviewed the initial design for missing relationships and weak spots, and that review led to four changes:

1. **Linked tasks to a specific pet.** In my first design, `Pet` was effectively orphaned — nothing connected a `Task` to the pet it was for, so with more than one pet there was no way to tell which animal a "walk" belonged to. I added a `pet_name` field to `Task` so each task points at its pet, while keeping it optional so a single-pet setup still works without extra ceremony.

2. **Switched time handling to minutes since midnight.** Originally every time was an `"HH:MM"` string, which meant every part of the scheduler would have had to parse and re-format strings to do basic math (overlaps, fitting the time budget, placing the next task). I added `parse_time` and `format_time` helpers and moved the logic to work in integer minutes, keeping strings only at the UI boundary. This removes a whole class of parsing bugs and avoids duplicating that conversion in several methods.

3. **Made the "why" survive the scheduling pipeline.** The project requires the app to explain its plan, but my first method signatures returned plain lists of tasks, which threw away the reason a task was dropped. I added a `SkippedTask` class (mirroring `ScheduledTask`) and changed `filter_by_budget` and `assign_times` to return both the kept tasks and the skipped ones with reasons. This also surfaced that tasks can be skipped at more than one stage — a fixed-time task can fit the time budget but still fail to place if it collides with another fixed task.

4. **Made recurrence actually work.** I originally had a vague `recurrence` string on `Task` that nothing consumed, since the scheduler had no notion of which day it was planning. I replaced it with a `days` field (which weekdays the task applies to) plus an `is_active_on` method, and added a `filter_by_recurrence` step and a `day_of_week` argument to `build_plan` so daily vs. weekly tasks are handled correctly.

The common thread was catching design gaps *before* coding: an unused class, an unused field, error-prone data representations, and method signatures that quietly dropped information the app was required to show.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

My scheduler reasons about several constraints, in roughly this order of
importance:

1. **Available time (the budget).** The owner has a fixed number of minutes per
   day. This is the hardest constraint — nothing can be scheduled past it — so it
   drives `filter_by_budget()`.
2. **Priority.** High-priority tasks (meds, walks) should be placed before
   low-priority ones (enrichment), so `sort_tasks()` orders by priority first.
3. **Fixed times.** Some tasks must happen at a specific time (feeding at 09:00),
   so those are anchored first and everything else fills the gaps around them.
4. **No overlaps / a buffer.** Two tasks can't occupy the same minutes, and the
   owner needs a moment to switch between them.
5. **Recurrence (which day).** Weekly tasks should only appear on their day.

I decided time and priority mattered most because they map directly to the
owner's real problem: "I only have so much time — make sure the important things
happen." Preferences and buffers are refinements layered on top once the core
time-and-priority logic was correct.



**b. Tradeoffs**

One deliberate tradeoff is in my conflict detection. `Scheduler.detect_conflicts()`
is intentionally "lightweight": it only flags tasks that share the **exact same
`fixed_time`** (e.g. two tasks both pinned to 09:00). It does **not** check
whether two tasks with different start times *overlap* because of their
durations — for example, a 30-minute task at 09:00 and another at 09:15 will
not be reported as a conflict by this method, even though they collide.

This tradeoff is reasonable here for two reasons. First, it's a cheap, easy-to-
read pre-check that gives the owner a clear, early warning ("these two things
are booked for the same minute") without the program crashing or doing heavy
interval math. Second, true duration-based overlaps are still handled where it
actually matters: when the plan is built, `assign_times()` places fixed-time
tasks one at a time and skips any whose interval overlaps one already placed,
with a reason. So `detect_conflicts()` is an informational heads-up, while the
real overlap safety net lives in the scheduling step. If this were a production
calendar app I would unify the two and have `detect_conflicts()` reason about
full intervals, but for a daily pet-care planner the exact-match warning is a
good simplicity-vs-completeness balance.

A second, related tradeoff: `filter_by_budget()` is greedy. It keeps tasks in
priority order until the time budget runs out, which is simple and predictable
but not globally optimal — one long high-priority task can crowd out two
shorter medium tasks that together would have delivered more value. For a busy
owner who wants their most important tasks done first, "highest priority wins"
is the more intuitive behavior than a value-maximizing knapsack solver.

---

## 3. AI Collaboration

**a. How you used AI**

I used an AI coding assistant throughout, but in different modes for different
phases:

- **Design review / brainstorming.** Before writing scheduling logic, I had the
  assistant review my initial class design for missing relationships and weak
  spots. This is what surfaced that `Pet` was orphaned and that `recurrence` was
  an unused field — both of which I fixed before coding.
- **Implementation.** I asked targeted "how do I" questions — e.g. how to use a
  `lambda` as a `sorted()` key to order `"HH:MM"` strings, and how to use
  `timedelta` to advance a due date by a day or a week.
- **Test drafting.** I had the assistant draft `pytest` cases from a list of
  behaviors and edge cases (empty task list, two tasks at the same time,
  recurrence boundaries), then reviewed and trimmed them.
- **Refactoring / evaluation.** Late in the project I shared individual methods
  and asked how they could be simplified for readability or performance.

The most helpful prompts were **specific and scoped**: "sort these objects by an
`HH:MM` attribute," not "write my scheduler." Asking the assistant to *critique*
my design before implementing was the single highest-value use — it caught
problems while they were still cheap to fix.

**b. Judgment and verification**

The clearest example of *not* accepting a suggestion as-is was the `sort_by_time`
sort key. The assistant pointed out I could sort the `"HH:MM"` strings directly
(`key=lambda t: t.fixed_time`) since zero-padded times sort lexicographically —
shorter and arguably more "Pythonic." I **kept my `parse_time`-based version**
instead, because it states intent (chronological, not alphabetical), it doesn't
silently break if a time is ever stored without zero-padding, and it cleanly
handles flexible tasks that have no time at all. The clever one-liner was correct
today but fragile to future changes.

I verified AI-suggested code in three ways: I ran the **test suite** (50 tests)
after every change, I ran **`main.py`** to eyeball real output, and I traced
edge cases by hand (e.g. confirming a fixed-time task that ends after the window
is actually skipped). When a suggestion and a test disagreed, I treated the test
as the source of truth and investigated whether the bug was in my test or the
logic.

---

## 4. Testing and Verification

**a. What you tested**

I wrote 50 `pytest` tests covering each layer:

- **Time helpers** — `parse_time`/`format_time` round-trips and rejection of bad
  input like `"24:00"`.
- **Sorting** — `sort_by_time` returns tasks chronologically, with flexible tasks
  last.
- **Filtering** — by pet name, by completion status, and combined.
- **Recurrence** — completing a daily task creates one due the next day; weekly
  advances a week; one-off tasks don't regenerate; completing twice spawns two.
- **Conflict detection** — flags duplicate fixed times (even across pets), quiet
  when times differ.
- **Scheduling pipeline** — budget limits, fixed-time anchoring and collisions,
  buffers, window checks, completed-task exclusion, and full `build_plan`.
- **Edge cases** — a pet with no tasks, empty/single lists, zero available time.

These mattered because the scheduler is built from small composable methods, and
testing each one in isolation meant a failure pointed straight at the responsible
piece instead of the whole pipeline.

**b. Confidence**

I'm fairly confident — about **4 out of 5**. The core sorting, filtering,
recurrence, and conflict logic are well covered and all 50 tests pass. The gaps I
would close next: conflict detection only catches exact same-time clashes (not
duration overlaps); recurrence date math hasn't been stress-tested across
month/leap-year/DST boundaries; and there are no automated tests for the
Streamlit UI in `app.py`, which I've only verified manually.

---

## 5. Reflection

**a. What went well**

I'm most satisfied with how the scheduler decomposed into small, single-purpose
methods (`sort_tasks`, `filter_by_budget`, `assign_times`, `detect_conflicts`,
…). That structure made the logic easy to test, easy to explain, and easy to
extend — adding buffers, recurrence, and conflict detection later didn't require
rewriting the core, just adding stages. The "explain the plan" feature also
turned out well: because skipped tasks carry reasons, the app can always tell the
owner *why* something didn't make the cut.

**b. What you would improve**

The recurrence model is the part I'd redesign. I ended up with **two** related
fields — `days` (which weekdays a task is active for `build_plan`) and
`frequency`/`due_date` (how a completed task regenerates). They serve different
purposes but overlap conceptually, and a future reader could easily confuse them.
Given another iteration I'd unify them into one clear recurrence representation.
I'd also upgrade `detect_conflicts` to reason about full duration overlaps rather
than exact-time matches.

**c. Key takeaway — being the "lead architect" with AI**

Working across **separate chat sessions for each phase** (design, implementation,
testing, finalization) kept me organized: each session had a clear goal and
context, so I wasn't dragging implementation details into a design conversation or
vice versa. It also forced me to re-state the current state of the system at each
phase boundary, which doubled as a sanity check.

The biggest lesson was that the AI is a fast, capable *builder*, but I had to be
the *architect*. The assistant would happily implement whatever I asked — clever
one-liners, extra fields, quick fixes — but it didn't own the system's coherence;
I did. The high-leverage moves were mine: deciding the class responsibilities,
asking it to critique my design before coding, rejecting a suggestion that was
clever but fragile, and using tests as the final arbiter. AI made each step
faster, but judgment about *what* to build and *whether the result was right*
stayed with me.
