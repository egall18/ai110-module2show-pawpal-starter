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

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
