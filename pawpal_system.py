"""PawPal+ logic layer.

The full domain model and scheduling engine for the pet-care daily planner.
These are stubs: attributes are declared, but methods contain no logic yet.
Keep this in sync with diagrams/uml.mmd.

Core flow: Owner + Pet profile -> Tasks -> Scheduler -> Plan
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


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


@dataclass
class Task:
    """A single care task to be scheduled."""

    title: str
    duration_minutes: int
    priority: Priority = Priority.MEDIUM
    category: str = "general"
    fixed_time: str | None = None
    recurrence: str = "daily"

    def is_fixed(self) -> bool:
        """Return True if this task must occur at a specific time."""
        raise NotImplementedError


@dataclass
class ScheduledTask:
    """A task placed into the plan at a concrete time, with a reason."""

    task: Task
    start_time: str
    end_time: str
    reason: str = ""


@dataclass
class Plan:
    """The result of scheduling: what was placed, what was skipped, and why."""

    scheduled: list[ScheduledTask] = field(default_factory=list)
    skipped: list[Task] = field(default_factory=list)
    explanation: str = ""

    def total_minutes(self) -> int:
        """Return the total scheduled time across all placed tasks."""
        raise NotImplementedError

    def summary(self) -> str:
        """Return a human-readable summary of the plan."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Scheduling engine
# ---------------------------------------------------------------------------


class Scheduler:
    """Builds a daily Plan from an Owner and a set of Tasks."""

    def __init__(self, owner: Owner, tasks: list[Task] | None = None) -> None:
        self.owner = owner
        self.tasks: list[Task] = tasks if tasks is not None else []

    def sort_tasks(self, tasks: list[Task]) -> list[Task]:
        """Order tasks for scheduling (e.g. by priority, then duration)."""
        raise NotImplementedError

    def filter_by_budget(self, tasks: list[Task]) -> list[Task]:
        """Drop or defer tasks that exceed the owner's available time."""
        raise NotImplementedError

    def assign_times(self, tasks: list[Task]) -> list[ScheduledTask]:
        """Assign concrete start/end times, avoiding overlaps."""
        raise NotImplementedError

    def build_plan(self) -> Plan:
        """Run the full pipeline and return the resulting Plan."""
        raise NotImplementedError