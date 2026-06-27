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
