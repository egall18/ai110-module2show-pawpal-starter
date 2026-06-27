"""Temporary testing ground for PawPal+.

Run this from the terminal to verify the logic layer works end to end:

    python main.py

This is NOT the real app (that's app.py / Streamlit). It builds an owner and
pets, attaches tasks via Pet.add_task(), then exercises priority sorting,
filtering, the "next available slot" finder, conflict detection, recurring-task
regeneration, JSON persistence, and full plan building — with emoji-coded,
tabulated output.
"""

import sys

from tabulate import tabulate

from pawpal_system import (
    Owner,
    Pet,
    Priority,
    Scheduler,
    load_from_json,
    save_to_json,
)
from pawpal_system import Task

# Emojis need a UTF-8 stdout; Windows terminals often default to cp1252.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DATA_FILE = "data.json"

# Emoji for different task types (matched by keyword in the title).
TYPE_EMOJI = {
    "walk": "🦮", "feed": "🍖", "med": "💊", "groom": "🛁", "bath": "🛁",
    "play": "🎾", "train": "🎓", "litter": "🧹", "clean": "🧹", "vet": "🩺",
}
# Color-coded priority indicators.
PRIORITY_DOT = {Priority.HIGH: "🔴", Priority.MEDIUM: "🟡", Priority.LOW: "🟢"}


def type_emoji(task: Task) -> str:
    title = task.title.lower()
    for keyword, emoji in TYPE_EMOJI.items():
        if keyword in title:
            return emoji
    return "🐾"


def status_icon(task: Task) -> str:
    if task.completed:
        return "✅ done"
    return "⏰ fixed" if task.is_fixed() else "🕒 flexible"


def banner(title: str) -> None:
    print(f"\n{'=' * 56}\n  {title}\n{'=' * 56}")


def main() -> None:
    owner = Owner(name="Jordan", available_minutes=180, start_time="08:00")
    mochi = Pet(name="Mochi", species="dog", needs=["walks", "training"])
    luna = Pet(name="Luna", species="cat", needs=["play", "grooming"])
    pets = [mochi, luna]

    # Added out of order; tasks link to their pet via add_task().
    mochi.add_task(Task("Training session", 20, Priority.MEDIUM, fixed_time="11:00"))
    mochi.add_task(Task("Morning walk", 30, Priority.HIGH, fixed_time="08:00",
                        frequency="daily"))
    mochi.add_task(Task("Feeding", 10, Priority.HIGH, fixed_time="09:00"))
    luna.add_task(Task("Play time", 15, Priority.MEDIUM))
    luna.add_task(Task("Litter cleanup", 10, Priority.LOW, fixed_time="09:00"))
    luna.add_task(Task("Weekly grooming", 25, Priority.LOW, frequency="weekly"))

    all_tasks = [t for p in pets for t in p.tasks]
    scheduler = Scheduler(owner, all_tasks, buffer_minutes=5)

    # --- Priority-then-time sorting (Challenge 3) ----------------------------
    banner("Tasks by priority, then time")
    rows = [
        [f"{type_emoji(t)} {t.title}", PRIORITY_DOT[t.priority] + " " + t.priority.name,
         t.fixed_time or "—", t.pet_name, status_icon(t)]
        for t in scheduler.sort_by_priority_then_time(all_tasks)
    ]
    print(tabulate(rows, headers=["Task", "Priority", "Time", "Pet", "Status"],
                   tablefmt="rounded_grid"))

    # --- Filtering -----------------------------------------------------------
    banner("Filter: only Mochi's tasks")
    for t in scheduler.filter_tasks(all_tasks, pet_name="Mochi"):
        print(f"  {type_emoji(t)} {t.title}")

    # --- Next available slot (Challenge 1) -----------------------------------
    banner("Next available slot finder")
    for minutes in (15, 30, 60):
        slot = scheduler.next_available_slot(minutes)
        where = f"starts at {slot}" if slot else "no room left today"
        print(f"  A {minutes}-min task -> {where}")

    # --- Conflict detection --------------------------------------------------
    banner("Conflict detection")
    conflicts = scheduler.detect_conflicts(all_tasks)
    for warning in conflicts or ["No conflicts found."]:
        print(f"  {warning}")

    # --- Recurring tasks -----------------------------------------------------
    banner("Recurring task regeneration")
    walk = mochi.tasks[1]  # the daily Morning walk
    print(f"  Mochi has {len(mochi.tasks)} tasks; completing '{walk.title}'...")
    upcoming = mochi.complete_task(walk)
    print(f"  -> spawned next occurrence due {upcoming.due_date}; "
          f"Mochi now has {len(mochi.tasks)} tasks")

    # --- Persistence (Challenge 2) -------------------------------------------
    banner("Persistence round-trip")
    save_to_json(DATA_FILE, owner, pets)
    print(f"  Saved owner + {len(pets)} pets to {DATA_FILE}")
    loaded_owner, loaded_pets = load_from_json(DATA_FILE)
    loaded_count = sum(len(p.tasks) for p in loaded_pets)
    print(f"  Reloaded {loaded_owner.name} with {len(loaded_pets)} pets "
          f"and {loaded_count} tasks from disk")

    # --- Full plan -----------------------------------------------------------
    banner("Today's Schedule (Mon)")
    plan = Scheduler(loaded_owner, [t for p in loaded_pets for t in p.tasks],
                     buffer_minutes=5).build_plan(day_of_week="Mon")
    rows = [
        [f"{st.start_time}-{st.end_time}", f"{type_emoji(st.task)} {st.task.title}",
         st.task.pet_name, PRIORITY_DOT[st.task.priority] + " " + st.task.priority.name]
        for st in plan.scheduled
    ]
    print(tabulate(rows, headers=["When", "Task", "Pet", "Priority"],
                   tablefmt="rounded_grid"))
    if plan.skipped:
        print("\n  Not scheduled:")
        for sk in plan.skipped:
            print(f"    - {sk.task.title}: {sk.reason}")


if __name__ == "__main__":
    main()