"""PawPal+ logic layer.

The full domain model and scheduling engine for the pet-care daily planner.
Keep this in sync with diagrams/uml.mmd.

Core flow: Owner + Pet profile -> Tasks -> Scheduler -> Plan
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------
# All scheduling math works in "minutes since midnight" so we never juggle
# "HH:MM" strings inside the logic. Strings live only at the UI boundary.


def parse_time(hhmm: str) -> int:
    """Convert an "HH:MM" string into minutes since midnight."""
    parts = hhmm.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Expected time as 'HH:MM', got {hhmm!r}")
    hours, minutes = int(parts[0]), int(parts[1])
    if not (0 <= hours < 24 and 0 <= minutes < 60):
        raise ValueError(f"Time out of range: {hhmm!r}")
    return hours * 60 + minutes


def format_time(minutes: int) -> str:
    """Convert minutes since midnight back into an "HH:MM" string."""
    hours, mins = divmod(int(minutes), 60)
    return f"{hours:02d}:{mins:02d}"


def _overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    """Return True if two [start, end) minute intervals overlap."""
    return a[0] < b[1] and b[0] < a[1]


# ---------------------------------------------------------------------------
# Domain model
# ---------------------------------------------------------------------------


class Priority(IntEnum):
    """Task priority. IntEnum so HIGH > MEDIUM > LOW compares naturally."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclass
class Owner:
    """The pet owner and their scheduling constraints."""

    name: str
    available_minutes: int = 120
    start_time: str = "08:00"
    preferences: list[str] = field(default_factory=list)


@dataclass
class Pet:
    """A pet being cared for."""

    name: str
    species: str = "dog"
    needs: list[str] = field(default_factory=list)
    tasks: list["Task"] = field(default_factory=list)

    def add_task(self, task: "Task") -> None:
        """Attach a care task to this pet and stamp it with the pet's name."""
        task.pet_name = self.name
        self.tasks.append(task)


@dataclass
class Task:
    """A single care task to be scheduled.

    pet_name links the task to a specific Pet (None = the default/only pet).
    days lists the weekdays the task applies to (None = every day); this is
    what makes recurring vs. one-off scheduling possible.
    """

    title: str
    duration_minutes: int
    priority: Priority = Priority.MEDIUM
    category: str = "general"
    pet_name: str | None = None
    fixed_time: str | None = None
    days: tuple[str, ...] | None = None
    completed: bool = False

    def is_fixed(self) -> bool:
        """Return True if this task must occur at a specific time."""
        return self.fixed_time is not None

    def mark_complete(self) -> None:
        """Mark this task as done."""
        self.completed = True

    def is_active_on(self, day_of_week: str | None) -> bool:
        """Return True if this task should run on the given weekday.

        A day_of_week of None (no specific day requested) means "include
        everything"; a task with days=None means "runs every day".
        """
        if day_of_week is None or self.days is None:
            return True
        return day_of_week in self.days


@dataclass
class ScheduledTask:
    """A task placed into the plan at a concrete time, with a reason."""

    task: Task
    start_time: str
    end_time: str
    reason: str = ""


@dataclass
class SkippedTask:
    """A task that was left out of the plan, and why."""

    task: Task
    reason: str = ""


@dataclass
class Plan:
    """The result of scheduling: what was placed, what was skipped, and why."""

    scheduled: list[ScheduledTask] = field(default_factory=list)
    skipped: list[SkippedTask] = field(default_factory=list)
    explanation: str = ""

    def total_minutes(self) -> int:
        """Return the total scheduled time across all placed tasks."""
        return sum(st.task.duration_minutes for st in self.scheduled)

    def summary(self) -> str:
        """Return a human-readable, time-ordered summary of the plan."""
        if not self.scheduled:
            return "No tasks scheduled."
        lines = []
        for st in self.scheduled:
            lines.append(
                f"{st.start_time}-{st.end_time}  {st.task.title} "
                f"({st.task.duration_minutes} min) [{st.task.priority.name.lower()}]"
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Scheduling engine
# ---------------------------------------------------------------------------


class Scheduler:
    """Builds a daily Plan from an Owner and a set of Tasks."""

    def __init__(self, owner: Owner, tasks: list[Task] | None = None) -> None:
        """Create a scheduler for an owner and an optional list of tasks."""
        self.owner = owner
        self.tasks: list[Task] = tasks if tasks is not None else []

    def filter_by_recurrence(
        self, tasks: list[Task], day_of_week: str | None
    ) -> list[Task]:
        """Keep only tasks active on the requested day (handles recurrence)."""
        return [t for t in tasks if t.is_active_on(day_of_week)]

    def sort_tasks(self, tasks: list[Task]) -> list[Task]:
        """Order by priority (high first), then shorter tasks first on ties."""
        return sorted(
            tasks, key=lambda t: (-int(t.priority), t.duration_minutes, t.title)
        )

    def filter_by_budget(
        self, tasks: list[Task]
    ) -> tuple[list[Task], list[SkippedTask]]:
        """Split tasks into those that fit the time budget and those that don't.

        Best-effort greedy fill: walk the (already sorted) tasks and keep each
        one that still fits the owner's available minutes. A task that does not
        fit is skipped, but we keep trying later (shorter) tasks.
        Returns (kept, skipped); each SkippedTask carries the reason it was cut.
        """
        kept: list[Task] = []
        skipped: list[SkippedTask] = []
        used = 0
        budget = self.owner.available_minutes
        for task in tasks:
            if used + task.duration_minutes <= budget:
                kept.append(task)
                used += task.duration_minutes
            else:
                remaining = budget - used
                skipped.append(
                    SkippedTask(
                        task,
                        f"Not enough time left ({remaining} min free, "
                        f"needs {task.duration_minutes} min)",
                    )
                )
        return kept, skipped

    def assign_times(
        self, tasks: list[Task]
    ) -> tuple[list[ScheduledTask], list[SkippedTask]]:
        """Assign concrete start/end times, avoiding overlaps.

        Fixed-time tasks are anchored first; flexible tasks fill the earliest
        open slot within the owner's time window. Tasks that cannot be placed
        (fixed-time collisions, or no free slot) are returned as skipped.
        """
        window_start = parse_time(self.owner.start_time)
        window_end = window_start + self.owner.available_minutes

        scheduled: list[ScheduledTask] = []
        skipped: list[SkippedTask] = []
        occupied: list[tuple[int, int]] = []

        fixed = [t for t in tasks if t.is_fixed()]
        flexible = [t for t in tasks if not t.is_fixed()]

        # Anchor fixed-time tasks at their requested time.
        for task in fixed:
            start = parse_time(task.fixed_time)  # type: ignore[arg-type]
            end = start + task.duration_minutes
            if any(_overlaps((start, end), slot) for slot in occupied):
                skipped.append(
                    SkippedTask(
                        task,
                        f"Fixed time {task.fixed_time} conflicts with "
                        "another task",
                    )
                )
                continue
            occupied.append((start, end))
            scheduled.append(
                ScheduledTask(
                    task,
                    format_time(start),
                    format_time(end),
                    f"Anchored at its fixed time {task.fixed_time}",
                )
            )

        # Fill flexible tasks into the earliest open slot.
        for task in flexible:
            start = self._find_slot(
                task.duration_minutes, window_start, window_end, occupied
            )
            if start is None:
                skipped.append(
                    SkippedTask(task, "No free time slot available")
                )
                continue
            end = start + task.duration_minutes
            occupied.append((start, end))
            scheduled.append(
                ScheduledTask(
                    task,
                    format_time(start),
                    format_time(end),
                    f"Placed in first open slot "
                    f"({task.priority.name.lower()} priority)",
                )
            )

        scheduled.sort(key=lambda st: parse_time(st.start_time))
        return scheduled, skipped

    def build_plan(self, day_of_week: str | None = None) -> Plan:
        """Run the full pipeline and return the resulting Plan.

        Pipeline: filter_by_recurrence -> sort_tasks -> filter_by_budget
        -> assign_times, collecting skipped tasks from every stage.
        """
        active = self.filter_by_recurrence(self.tasks, day_of_week)
        ordered = self.sort_tasks(active)
        kept, over_budget = self.filter_by_budget(ordered)
        scheduled, unplaceable = self.assign_times(kept)

        plan = Plan(scheduled=scheduled, skipped=over_budget + unplaceable)
        plan.explanation = self._explain(plan, day_of_week)
        return plan

    # -- internal helpers ---------------------------------------------------

    def _find_slot(
        self,
        duration: int,
        window_start: int,
        window_end: int,
        occupied: list[tuple[int, int]],
    ) -> int | None:
        """Return the earliest start minute with a free gap of `duration`."""
        cursor = window_start
        for start, end in sorted(occupied):
            if start - cursor >= duration:
                return cursor
            cursor = max(cursor, end)
        if window_end - cursor >= duration:
            return cursor
        return None

    def _explain(self, plan: Plan, day_of_week: str | None) -> str:
        """Build a human-readable explanation of the plan's decisions."""
        day = day_of_week or "today"
        parts = [
            f"Plan for {self.owner.name} ({day}): "
            f"scheduled {len(plan.scheduled)} task(s) using "
            f"{plan.total_minutes()} of {self.owner.available_minutes} "
            "available minutes."
        ]
        if plan.skipped:
            parts.append(f"Skipped {len(plan.skipped)} task(s):")
            for sk in plan.skipped:
                parts.append(f"  - {sk.task.title}: {sk.reason}")
        return "\n".join(parts)