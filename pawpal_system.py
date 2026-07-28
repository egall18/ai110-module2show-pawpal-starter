"""PawPal+ logic layer.

The full domain model and scheduling engine for the pet-care daily planner.
Keep this in sync with diagrams/uml.mmd.

Core flow: Owner + Pet profile -> Tasks -> Scheduler -> Plan
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from enum import IntEnum
from typing import Optional


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

    def complete_task(self, task: "Task") -> "Optional[Task]":
        """Mark a task done; if it recurs, auto-create and attach the next one.

        Returns the newly created next occurrence, or None for one-off tasks.
        """
        task.mark_complete()
        upcoming = task.next_occurrence()
        if upcoming is not None:
            self.add_task(upcoming)
        return upcoming


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
    place: str = ""
    pet_name: Optional[str] = None
    fixed_time: Optional[str] = None
    days: Optional[tuple[str, ...]] = None
    completed: bool = False
    frequency: str = "none"  # "none" | "daily" | "weekly"
    due_date: Optional[date] = None

    def is_fixed(self) -> bool:
        """Return True if this task must occur at a specific time."""
        return self.fixed_time is not None

    def mark_complete(self) -> None:
        """Mark this task as done."""
        self.completed = True

    def next_occurrence(self) -> "Optional[Task]":
        """Return a fresh, uncompleted copy due on the next date, or None.

        Daily tasks advance by one day, weekly tasks by one week (via
        timedelta). Non-recurring tasks return None.
        """
        if self.frequency == "daily":
            delta = timedelta(days=1)
        elif self.frequency == "weekly":
            delta = timedelta(weeks=1)
        else:
            return None
        base = self.due_date or date.today()
        return replace(self, completed=False, due_date=base + delta)

    def is_active_on(self, day_of_week: Optional[str]) -> bool:
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

    def __init__(
        self,
        owner: Owner,
        tasks: Optional[list[Task]] = None,
        buffer_minutes: int = 0,
    ) -> None:
        """Create a scheduler for an owner and an optional list of tasks.

        buffer_minutes inserts a gap between consecutive tasks so the owner
        isn't expected to switch instantly from one task to the next.
        """
        self.owner = owner
        self.tasks: list[Task] = tasks if tasks is not None else []
        self.buffer_minutes = buffer_minutes

    def filter_by_recurrence(
        self, tasks: list[Task], day_of_week: Optional[str]
    ) -> list[Task]:
        """Keep only tasks active on the requested day (handles recurrence)."""
        return [t for t in tasks if t.is_active_on(day_of_week)]

    def sort_tasks(self, tasks: list[Task]) -> list[Task]:
        """Order by priority (high first), then shorter tasks first on ties."""
        return sorted(
            tasks, key=lambda t: (-int(t.priority), t.duration_minutes, t.title)
        )

    def sort_by_time(self, tasks: Optional[list[Task]] = None) -> list[Task]:
        """Return tasks ordered chronologically by their fixed_time ("HH:MM").

        A lambda key converts each "HH:MM" string to minutes so the sort is
        truly chronological. Flexible tasks (no fixed_time) sort to the end.
        """
        items = self.tasks if tasks is None else tasks
        return sorted(
            items,
            key=lambda t: parse_time(t.fixed_time) if t.fixed_time else 24 * 60,
        )

    def sort_by_priority_then_time(
        self, tasks: Optional[list[Task]] = None
    ) -> list[Task]:
        """Sort by priority (high first), then chronologically by fixed_time.

        This is the "priority-based scheduling" order: the most important tasks
        come first, and ties are broken by the earlier clock time (flexible,
        untimed tasks sort last). Title is a final tie-break for stable output.
        """
        items = self.tasks if tasks is None else tasks
        return sorted(
            items,
            key=lambda t: (
                -int(t.priority),
                parse_time(t.fixed_time) if t.fixed_time else 24 * 60,
                t.title,
            ),
        )

    def next_available_slot(
        self, duration_minutes: int, day_of_week: Optional[str] = None
    ) -> Optional[str]:
        """Return the earliest "HH:MM" a new task of `duration_minutes` would fit.

        Builds today's plan, then searches the gaps around already-scheduled
        tasks (honoring the buffer) for the first opening big enough. Returns
        None if there is no room left in the owner's window. Useful for "when
        can I squeeze in a 30-minute vet call?" style questions.
        """
        plan = self.build_plan(day_of_week=day_of_week)
        window_start = parse_time(self.owner.start_time)
        window_end = window_start + self.owner.available_minutes
        occupied = [
            (parse_time(s.start_time), parse_time(s.end_time))
            for s in plan.scheduled
        ]
        start = self._find_slot(
            duration_minutes, window_start, window_end, occupied
        )
        return format_time(start) if start is not None else None

    def filter_tasks(
        self,
        tasks: Optional[list[Task]] = None,
        *,
        pet_name: Optional[str] = None,
        completed: Optional[bool] = None,
    ) -> list[Task]:
        """Return tasks filtered by pet name and/or completion status.

        Either filter is optional; pass one or both. None means "don't filter
        on that field".
        """
        items = self.tasks if tasks is None else tasks
        result = list(items)
        if pet_name is not None:
            result = [t for t in result if t.pet_name == pet_name]
        if completed is not None:
            result = [t for t in result if t.completed == completed]
        return result

    def detect_conflicts(self, tasks: Optional[list[Task]] = None) -> list[str]:
        """Lightweight conflict check: warn when tasks share the same fixed_time.

        Returns human-readable warning strings (empty list if no conflicts) so
        the caller can surface them without the program crashing. This only
        catches exact start-time clashes; full duration overlaps are resolved
        later by assign_times during scheduling.
        """
        items = self.tasks if tasks is None else tasks
        by_time: dict[str, list[Task]] = {}
        for task in items:
            if task.fixed_time is not None:
                by_time.setdefault(task.fixed_time, []).append(task)

        warnings: list[str] = []
        for time_str, group in sorted(by_time.items()):
            if len(group) > 1:
                titles = ", ".join(t.title for t in group)
                warnings.append(
                    f"WARNING: Conflict at {time_str}: {titles} are scheduled "
                    "at the same time."
                )
        return warnings

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
            if start < window_start or end > window_end:
                skipped.append(
                    SkippedTask(
                        task,
                        f"Fixed time {task.fixed_time} is outside the "
                        f"available window "
                        f"({self.owner.start_time}-{format_time(window_end)})",
                    )
                )
                continue
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
            # (buffer is applied inside _find_slot via self.buffer_minutes)
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

    def build_plan(self, day_of_week: Optional[str] = None) -> Plan:
        """Run the full pipeline and return the resulting Plan.

        Pipeline: drop completed -> filter_by_recurrence -> sort_tasks
        -> filter_by_budget -> assign_times, collecting skipped tasks from
        every stage.
        """
        pending = [t for t in self.tasks if not t.completed]
        active = self.filter_by_recurrence(pending, day_of_week)
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
    ) -> Optional[int]:
        """Return the earliest start minute with a free gap of `duration`.

        Honors self.buffer_minutes: a placed task must leave a buffer gap
        before the next occupied block, and starts a buffer after the previous.
        """
        buffer = self.buffer_minutes
        cursor = window_start
        for start, end in sorted(occupied):
            if start - cursor >= duration + buffer:
                return cursor
            cursor = max(cursor, end + buffer)
        if window_end - cursor >= duration:
            return cursor
        return None

    def _explain(self, plan: Plan, day_of_week: Optional[str]) -> str:
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


# ---------------------------------------------------------------------------
# Persistence (data.json)
# ---------------------------------------------------------------------------
# JSON can't serialize our dataclasses, the Priority enum, or date objects
# directly, so we convert to/from plain dicts by hand. Enum -> int,
# date -> ISO string, tuple -> list; everything reverses on load.


def _task_to_dict(task: Task) -> dict:
    """Convert a Task into a JSON-safe dict."""
    return {
        "title": task.title,
        "duration_minutes": task.duration_minutes,
        "priority": int(task.priority),
        "category": task.category,
        "place": task.place,
        "pet_name": task.pet_name,
        "fixed_time": task.fixed_time,
        "days": list(task.days) if task.days else None,
        "completed": task.completed,
        "frequency": task.frequency,
        "due_date": task.due_date.isoformat() if task.due_date else None,
    }


def _task_from_dict(data: dict) -> Task:
    """Rebuild a Task from a dict produced by _task_to_dict()."""
    return Task(
        title=data["title"],
        duration_minutes=data["duration_minutes"],
        priority=Priority(data.get("priority", int(Priority.MEDIUM))),
        category=data.get("category", "general"),
        place=data.get("place", ""),
        pet_name=data.get("pet_name"),
        fixed_time=data.get("fixed_time"),
        days=tuple(data["days"]) if data.get("days") else None,
        completed=data.get("completed", False),
        frequency=data.get("frequency", "none"),
        due_date=date.fromisoformat(data["due_date"]) if data.get("due_date") else None,
    )


def _pet_to_dict(pet: Pet) -> dict:
    """Convert a Pet (and its tasks) into a JSON-safe dict."""
    return {
        "name": pet.name,
        "species": pet.species,
        "needs": list(pet.needs),
        "tasks": [_task_to_dict(t) for t in pet.tasks],
    }


def _pet_from_dict(data: dict) -> Pet:
    """Rebuild a Pet (and its tasks) from a dict."""
    pet = Pet(
        name=data["name"],
        species=data.get("species", "dog"),
        needs=list(data.get("needs", [])),
    )
    pet.tasks = [_task_from_dict(t) for t in data.get("tasks", [])]
    return pet


def _owner_to_dict(owner: Owner) -> dict:
    """Convert an Owner into a JSON-safe dict."""
    return {
        "name": owner.name,
        "available_minutes": owner.available_minutes,
        "start_time": owner.start_time,
        "preferences": list(owner.preferences),
    }


def _owner_from_dict(data: dict) -> Owner:
    """Rebuild an Owner from a dict."""
    return Owner(
        name=data["name"],
        available_minutes=data.get("available_minutes", 120),
        start_time=data.get("start_time", "08:00"),
        preferences=list(data.get("preferences", [])),
    )


def save_to_json(path: str, owner: Owner, pets: list[Pet]) -> None:
    """Save the owner and all pets (with their tasks) to a JSON file."""
    data = {
        "owner": _owner_to_dict(owner),
        "pets": [_pet_to_dict(p) for p in pets],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def load_from_json(path: str) -> tuple[Owner, list[Pet]]:
    """Load the owner and pets from a JSON file written by save_to_json()."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    owner = _owner_from_dict(data["owner"])
    pets = [_pet_from_dict(p) for p in data.get("pets", [])]
    return owner, pets