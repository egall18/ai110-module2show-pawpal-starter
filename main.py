"""Temporary testing ground for PawPal+.

Run this from the terminal to verify the logic layer works end to end:

    python main.py

This is NOT the real app (that's app.py / Streamlit). It builds an owner and
pets, attaches tasks via Pet.add_task(), then exercises sorting, filtering,
recurring-task regeneration, conflict detection, and full plan building.
"""

from pawpal_system import Owner, Pet, Priority, Scheduler, Task


def banner(title: str) -> None:
    print("\n" + "=" * 52)
    print(f"  {title}")
    print("=" * 52)


def main() -> None:
    owner = Owner(name="Jordan", available_minutes=180, start_time="08:00")

    # Two pets; tasks are attached through Pet.add_task() so each task is
    # linked to its pet automatically (no hand-typed pet_name strings).
    mochi = Pet(name="Mochi", species="dog", needs=["walks", "training"])
    luna = Pet(name="Luna", species="cat", needs=["play", "grooming"])
    pets = [mochi, luna]

    # Added intentionally OUT OF ORDER by time to prove sort_by_time() works.
    mochi.add_task(Task("Training session", 20, Priority.MEDIUM, fixed_time="11:00"))
    mochi.add_task(Task("Morning walk", 30, Priority.HIGH, fixed_time="08:00",
                        frequency="daily"))
    mochi.add_task(Task("Feeding", 10, Priority.HIGH, fixed_time="09:00"))
    luna.add_task(Task("Play time", 15, Priority.MEDIUM))  # flexible
    luna.add_task(Task("Litter cleanup", 10, Priority.LOW, fixed_time="09:00"))
    luna.add_task(Task("Weekly grooming", 25, Priority.LOW, frequency="weekly"))

    all_tasks = [t for p in pets for t in p.tasks]
    scheduler = Scheduler(owner, all_tasks, buffer_minutes=5)

    # --- Sorting by time -----------------------------------------------------
    banner("Tasks sorted by time")
    for t in scheduler.sort_by_time(all_tasks):
        when = t.fixed_time or "flexible"
        print(f"  {when:>9}  {t.title} ({t.pet_name})")

    # --- Filtering -----------------------------------------------------------
    banner("Filter: only Mochi's tasks")
    for t in scheduler.filter_tasks(all_tasks, pet_name="Mochi"):
        print(f"  - {t.title}")

    banner("Filter: only incomplete tasks")
    for t in scheduler.filter_tasks(all_tasks, completed=False):
        print(f"  - {t.title} ({t.pet_name})")

    # --- Conflict detection --------------------------------------------------
    # Feeding (Mochi) and Litter cleanup (Luna) are both at 09:00.
    banner("Conflict detection")
    conflicts = scheduler.detect_conflicts(all_tasks)
    if conflicts:
        for warning in conflicts:
            print(f"  {warning}")
    else:
        print("  No conflicts found.")

    # --- Recurring tasks -----------------------------------------------------
    banner("Recurring task regeneration")
    walk = mochi.tasks[1]  # the daily Morning walk
    print(f"  Before: Mochi has {len(mochi.tasks)} tasks; "
          f"'{walk.title}' completed={walk.completed}")
    upcoming = mochi.complete_task(walk)
    print(f"  Completed '{walk.title}' -> spawned next occurrence "
          f"due {upcoming.due_date}")
    print(f"  After:  Mochi has {len(mochi.tasks)} tasks")

    # --- Full plan -----------------------------------------------------------
    banner("Today's Schedule (Mon)")
    plan = Scheduler(owner, [t for p in pets for t in p.tasks],
                     buffer_minutes=5).build_plan(day_of_week="Mon")
    for st in plan.scheduled:
        print(f"  {st.start_time}-{st.end_time}  {st.task.title} "
              f"({st.task.pet_name})")
    if plan.skipped:
        print("  Not scheduled:")
        for sk in plan.skipped:
            print(f"    - {sk.task.title}: {sk.reason}")
    print()
    print(plan.explanation)


if __name__ == "__main__":
    main()