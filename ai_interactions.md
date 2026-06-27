# AI Interactions Log

> **Stretch features only.** Only fill in the sections that apply to stretch features you attempted. If you did not attempt a stretch feature, leave its section blank or delete it. This file is not required for the core project.

---

## Agent Workflow (SF7)

> Document your experience using an AI agent (e.g., Cursor Agent, Claude, Copilot) to make multi-step changes autonomously.

**What task did you give the agent?**

I asked the agent (Claude in Claude Code) to add four advanced capabilities to
PawPal+ in one pass: a "next available slot" finder, priority-then-time
scheduling, JSON data persistence, and professional CLI formatting (tabulate +
emojis) — along with tests and documentation for each.

**What did the agent do?**

It worked through the change across several files:

- **`pawpal_system.py`** — added `Scheduler.next_available_slot()`,
  `Scheduler.sort_by_priority_then_time()`, and module-level `save_to_json()` /
  `load_from_json()` with `_to_dict`/`_from_dict` converters (handling the
  `Priority` enum, `date` objects, and tuples).
- **`tests/test_pawpal.py`** — added 6 tests (next-slot, priority-then-time, and
  a persistence round-trip using pytest's `tmp_path`), bringing the suite to 56.
- **`main.py`** — rewrote the demo to use `tabulate` tables, task-type emojis,
  color-coded priority dots, and status icons, plus a save→load round-trip.
- **`requirements.txt`** — added `tabulate`; **`.gitignore`** — ignored
  `data.json`.
- **`README.md`** — documented persistence, formatting, and priority CLI output.
- Ran `python -m pytest` (56 passing) and `python main.py` to verify.

**What did you have to verify or fix manually?**

- **UTF-8 / emoji crash.** The first run of the formatted demo crashed with a
  `UnicodeEncodeError` because the Windows terminal defaults to cp1252. I had it
  add `sys.stdout.reconfigure(encoding="utf-8")` to `main.py`. (Earlier, the same
  issue forced changing a `⚠️` in the logic layer to a plain `WARNING:` so the
  library code stays terminal-safe.)
- **Serialization edge cases.** I checked that the JSON round-trip actually
  preserved the `Priority` enum and `date` values rather than turning them into
  ints/strings — the tests confirm this.
- **Scope of "persistence methods."** The spec said "methods"; the agent
  implemented module-level functions instead of class methods. I accepted this
  as cleaner (the data spans multiple objects), but it was a deliberate human
  call, not something to take for granted.

---

## Prompt Comparison (SF11)

> Compare two different prompts (or two different models) on the same task.

**Task compared:** the logic for *rescheduling weekly (recurring) tasks* — when a
recurring task is completed, how should the next occurrence be produced?

> **Honesty note:** Option A is the approach Claude (this assistant) proposed and
> I implemented. Option B is a genuinely different design that was also generated
> with Claude as a contrasting option, so this is really a *prompt/approach*
> comparison rather than a cross-vendor model comparison. To turn it into a true
> two-model comparison, paste a second tool's (e.g. Gemini/Copilot) output into
> the Option B column.

| | Option A (event-driven) | Option B (rule-based / date-range) |
|-|-------------------------|------------------------------------|
| **Model / tool used** | Claude (Claude Code) | Claude, prompted for a different design |
| **Prompt** | "When a daily/weekly task is marked complete, create the next occurrence." | "Given a recurrence rule, precompute all occurrences between two dates." |
| **Response summary** | Add `Task.next_occurrence()` that returns a copy with `due_date` advanced by `timedelta`; `Pet.complete_task()` spawns it on completion. | Store a recurrence rule per task and expand it into a list of dated instances for a requested window (week/month). |
| **What was useful** | Simple, lazy (only creates the next one when needed), maps directly to the user action of "I finished this." | Powerful for calendar views — you can show every future occurrence at once. |
| **Problems noticed** | No look-ahead: you only ever see the *next* instance, not a full month. | Heavier: needs date-range inputs, can generate many objects, and risks drift if rules and completion state get out of sync. |
| **Decision** | **Chosen.** | Rejected for now. |

**Which approach did you use in your final implementation and why?**

I used **Option A (event-driven)**. For a daily pet-care planner the user's mental
model is "I did this task — when's the next one?", which the
complete-then-spawn-next design matches exactly. It's also the lighter
implementation: a single `timedelta` advance with no date-range bookkeeping, and
it keeps completion state and recurrence in one place. Option B's full-calendar
expansion is the better fit if PawPal+ ever grows a month view, so I noted it as
a future direction rather than discarding it entirely.
