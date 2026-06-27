"""Temporary testing ground for PawPal+.

Run this from the terminal to verify the logic layer works end to end:

    python main.py

This is NOT the real app (that's app.py / Streamlit). It just wires up a
realistic owner, a couple of pets, and some tasks, then prints the plan.
"""

from pawpal_system import Owner, Pet, Priority, Scheduler, Task


def main() -> None:
    # 1. The owner and their daily time budget.
    owner = Owner(
        name="Jordan",
        available_minutes=120,
        start_time="08:00",
        preferences=["morning walks first"],
    )

    # 2. At least two pets.
    pets = [
        Pet(name="Mochi", species="dog", needs=["walks", "training"]),
        Pet(name="Luna", species="cat", needs=["play", "grooming"]),
    ]

    # 3. At least three tasks, with different times, linked to the pets.
    tasks = [
        Task("Morning walk", 30, Priority.HIGH, pet_name="Mochi"),
        Task("Feeding", 10, Priority.HIGH, pet_name="Mochi", fixed_time="09:00"),
        Task("Training session", 20, Priority.MEDIUM, pet_name="Mochi"),
        Task("Play time", 15, Priority.MEDIUM, pet_name="Luna"),
        Task("Litter cleanup", 10, Priority.LOW, pet_name="Luna", fixed_time="08:45"),
        Task("Weekly grooming", 25, Priority.LOW, pet_name="Luna", days=("Sun",)),
    ]

    # 4. Build and print today's schedule.
    scheduler = Scheduler(owner, tasks)
    plan = scheduler.build_plan(day_of_week="Mon")

    print("=" * 48)
    print(f"  Today's Schedule for {owner.name}")
    print(f"  Pets: {', '.join(p.name for p in pets)}")
    print("=" * 48)

    if not plan.scheduled:
        print("Nothing scheduled today.")
    for st in plan.scheduled:
        pet = st.task.pet_name or "—"
        print(
            f"  {st.start_time}-{st.end_time}  {st.task.title}  "
            f"({pet}, {st.task.duration_minutes} min, "
            f"{st.task.priority.name.lower()})"
        )

    if plan.skipped:
        print("-" * 48)
        print("  Not scheduled:")
        for sk in plan.skipped:
            print(f"  - {sk.task.title}: {sk.reason}")

    print("=" * 48)
    print(plan.explanation)


if __name__ == "__main__":
    main()