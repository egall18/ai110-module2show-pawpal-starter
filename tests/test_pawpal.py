"""Tests for the PawPal+ logic layer.

Covers the time helpers, the domain-model methods, each scheduler stage in
isolation, and the full build_plan pipeline, plus the edge cases we identified
up front (empty list, zero time, budget overflow, fixed-time collisions,
recurrence filtering, and priority sorting).
"""

from datetime import date

import pytest

from pawpal_system import (
    Owner,
    Pet,
    Plan,
    Priority,
    ScheduledTask,
    Scheduler,
    Task,
    format_time,
    parse_time,
)


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------


def test_parse_time_basic():
    assert parse_time("00:00") == 0
    assert parse_time("08:30") == 510
    assert parse_time("23:59") == 1439


def test_format_time_basic():
    assert format_time(0) == "00:00"
    assert format_time(510) == "08:30"
    assert format_time(1439) == "23:59"


def test_parse_format_round_trip():
    for hhmm in ("00:00", "07:05", "12:00", "19:45", "23:59"):
        assert format_time(parse_time(hhmm)) == hhmm


@pytest.mark.parametrize("bad", ["8:30:00", "0830", "24:00", "08:60", "ab:cd"])
def test_parse_time_rejects_bad_input(bad):
    with pytest.raises(ValueError):
        parse_time(bad)


# ---------------------------------------------------------------------------
# Domain model
# ---------------------------------------------------------------------------


def test_priority_ordering():
    assert Priority.HIGH > Priority.MEDIUM > Priority.LOW


def test_is_fixed():
    assert Task("Feed", 10, fixed_time="09:00").is_fixed() is True
    assert Task("Walk", 30).is_fixed() is False


def test_mark_complete_changes_status():
    """Task Completion: mark_complete() flips the task's status to done."""
    task = Task("Morning walk", 30)
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_adding_task_increases_pet_task_count():
    """Task Addition: adding a task to a Pet grows that pet's task count."""
    pet = Pet("Mochi", species="dog")
    assert len(pet.tasks) == 0
    pet.add_task(Task("Morning walk", 30))
    assert len(pet.tasks) == 1
    pet.add_task(Task("Feeding", 10))
    assert len(pet.tasks) == 2
    # add_task also links each task back to the pet.
    assert all(t.pet_name == "Mochi" for t in pet.tasks)


def test_is_active_on():
    daily = Task("Walk", 30)  # days=None -> every day
    weekly = Task("Bath", 20, days=("Sun",))
    assert daily.is_active_on("Mon") is True
    assert daily.is_active_on(None) is True
    assert weekly.is_active_on("Sun") is True
    assert weekly.is_active_on("Mon") is False
    assert weekly.is_active_on(None) is True  # no specific day requested


# ---------------------------------------------------------------------------
# Scheduler: individual stages
# ---------------------------------------------------------------------------


@pytest.fixture
def owner():
    return Owner("Jordan", available_minutes=120, start_time="08:00")


def test_sort_tasks_by_priority_then_duration(owner):
    tasks = [
        Task("low", 10, Priority.LOW),
        Task("high-long", 60, Priority.HIGH),
        Task("high-short", 15, Priority.HIGH),
        Task("med", 20, Priority.MEDIUM),
    ]
    ordered = Scheduler(owner).sort_tasks(tasks)
    titles = [t.title for t in ordered]
    # High priority first; within HIGH the shorter task comes first.
    assert titles == ["high-short", "high-long", "med", "low"]


def test_filter_by_recurrence(owner):
    tasks = [
        Task("daily", 10),
        Task("sunday", 10, days=("Sun",)),
        Task("weekdays", 10, days=("Mon", "Tue", "Wed", "Thu", "Fri")),
    ]
    kept = Scheduler(owner).filter_by_recurrence(tasks, "Mon")
    titles = {t.title for t in kept}
    assert titles == {"daily", "weekdays"}


def test_filter_by_budget_keeps_fitting_and_skips_overflow():
    owner = Owner("J", available_minutes=45)
    tasks = [Task("a", 30), Task("b", 10), Task("c", 60)]
    kept, skipped = Scheduler(owner).filter_by_budget(tasks)
    assert [t.title for t in kept] == ["a", "b"]  # 30 + 10 = 40 <= 45
    assert len(skipped) == 1
    assert skipped[0].task.title == "c"
    assert "needs 60 min" in skipped[0].reason


def test_filter_by_budget_best_effort_fill():
    # A big task that doesn't fit shouldn't block a later small one.
    owner = Owner("J", available_minutes=40)
    tasks = [Task("big", 60), Task("small", 30)]
    kept, skipped = Scheduler(owner).filter_by_budget(tasks)
    assert [t.title for t in kept] == ["small"]
    assert [s.task.title for s in skipped] == ["big"]


def test_assign_times_no_overlap(owner):
    tasks = [Task("a", 30), Task("b", 20), Task("c", 10)]
    scheduled, skipped = Scheduler(owner).assign_times(tasks)
    assert skipped == []
    assert len(scheduled) == 3
    # Verify sequential, non-overlapping placement.
    ends = [parse_time(st.end_time) for st in scheduled]
    starts = [parse_time(st.start_time) for st in scheduled]
    assert starts[0] == parse_time("08:00")
    for i in range(1, len(scheduled)):
        assert starts[i] >= ends[i - 1]


def test_assign_times_anchors_fixed_task(owner):
    tasks = [Task("walk", 30), Task("feed", 10, fixed_time="09:00")]
    scheduled, skipped = Scheduler(owner).assign_times(tasks)
    by_title = {st.task.title: st for st in scheduled}
    assert by_title["feed"].start_time == "09:00"
    assert by_title["feed"].end_time == "09:10"


def test_assign_times_skips_fixed_collision(owner):
    tasks = [
        Task("feed", 30, fixed_time="09:00"),
        Task("meds", 15, fixed_time="09:10"),  # collides with feed (09:00-09:30)
    ]
    scheduled, skipped = Scheduler(owner).assign_times(tasks)
    assert [st.task.title for st in scheduled] == ["feed"]
    assert len(skipped) == 1
    assert skipped[0].task.title == "meds"
    assert "conflicts" in skipped[0].reason


def test_assign_times_no_slot_available():
    owner = Owner("J", available_minutes=20, start_time="08:00")
    tasks = [Task("long", 30)]  # won't fit in a 20-minute window
    scheduled, skipped = Scheduler(owner).assign_times(tasks)
    assert scheduled == []
    assert skipped[0].reason == "No free time slot available"


# ---------------------------------------------------------------------------
# Scheduler: full pipeline
# ---------------------------------------------------------------------------


def test_build_plan_integration():
    owner = Owner("Jordan", available_minutes=90, start_time="08:00")
    tasks = [
        Task("Morning walk", 30, Priority.HIGH),
        Task("Feeding", 10, Priority.HIGH, fixed_time="09:00"),
        Task("Meds", 5, Priority.MEDIUM),
        Task("Long grooming", 60, Priority.LOW),
        Task("Weekly bath", 20, Priority.MEDIUM, days=("Sun",)),
    ]
    plan = Scheduler(owner, tasks).build_plan(day_of_week="Mon")

    scheduled_titles = [st.task.title for st in plan.scheduled]
    skipped_titles = [s.task.title for s in plan.skipped]

    assert "Weekly bath" not in scheduled_titles  # filtered by recurrence
    assert "Weekly bath" not in skipped_titles
    assert "Long grooming" in skipped_titles  # over budget
    assert "Feeding" in scheduled_titles
    # No overlaps in the final schedule.
    starts = [parse_time(st.start_time) for st in plan.scheduled]
    assert starts == sorted(starts)


def test_build_plan_empty_task_list(owner):
    plan = Scheduler(owner, []).build_plan()
    assert plan.scheduled == []
    assert plan.skipped == []
    assert plan.total_minutes() == 0


def test_build_plan_zero_available_time():
    owner = Owner("J", available_minutes=0)
    tasks = [Task("walk", 30)]
    plan = Scheduler(owner, tasks).build_plan()
    assert plan.scheduled == []
    assert len(plan.skipped) == 1


# ---------------------------------------------------------------------------
# Efficiency improvements: buffer, fixed-time window, completed tasks
# ---------------------------------------------------------------------------


def test_buffer_inserts_gap_between_tasks():
    owner = Owner("J", available_minutes=120, start_time="08:00")
    tasks = [Task("a", 30), Task("b", 30)]
    scheduled, _ = Scheduler(owner, buffer_minutes=10).assign_times(tasks)
    by_title = {st.task.title: st for st in scheduled}
    # 'a' at 08:00-08:30, then a 10-min buffer, so 'b' starts no earlier 08:40.
    assert by_title["a"].end_time == "08:30"
    assert parse_time(by_title["b"].start_time) >= parse_time("08:40")


def test_no_buffer_by_default_places_back_to_back():
    owner = Owner("J", available_minutes=120, start_time="08:00")
    tasks = [Task("a", 30), Task("b", 30)]
    scheduled, _ = Scheduler(owner).assign_times(tasks)
    by_title = {st.task.title: st for st in scheduled}
    assert by_title["b"].start_time == "08:30"  # immediately after 'a'


def test_fixed_time_outside_window_is_skipped():
    owner = Owner("J", available_minutes=120, start_time="08:00")  # window 08:00-10:00
    tasks = [Task("late meds", 10, fixed_time="14:00")]
    scheduled, skipped = Scheduler(owner).assign_times(tasks)
    assert scheduled == []
    assert len(skipped) == 1
    assert "outside the available window" in skipped[0].reason


def test_fixed_time_running_past_window_end_is_skipped():
    owner = Owner("J", available_minutes=60, start_time="08:00")  # window 08:00-09:00
    tasks = [Task("long fixed", 30, fixed_time="08:45")]  # would end 09:15
    scheduled, skipped = Scheduler(owner).assign_times(tasks)
    assert scheduled == []
    assert "outside the available window" in skipped[0].reason


def test_completed_tasks_excluded_from_plan():
    owner = Owner("J", available_minutes=120, start_time="08:00")
    done = Task("already walked", 30)
    done.mark_complete()
    todo = Task("feed", 10)
    plan = Scheduler(owner, [done, todo]).build_plan()
    titles = [st.task.title for st in plan.scheduled]
    assert titles == ["feed"]
    # The completed task isn't scheduled and isn't reported as skipped either.
    assert all(sk.task.title != "already walked" for sk in plan.skipped)


def test_completed_task_frees_time_for_others():
    owner = Owner("J", available_minutes=40, start_time="08:00")
    big_done = Task("big done", 60)
    big_done.mark_complete()
    small = Task("small", 30)
    plan = Scheduler(owner, [big_done, small]).build_plan()
    # Without excluding the completed 60-min task, 'small' could be crowded out;
    # since it's excluded, 'small' fits comfortably.
    assert [st.task.title for st in plan.scheduled] == ["small"]


# ---------------------------------------------------------------------------
# Sorting by time and filtering (Step 2)
# ---------------------------------------------------------------------------


def test_sort_by_time_orders_chronologically(owner):
    tasks = [
        Task("c", 10, fixed_time="12:00"),
        Task("a", 10, fixed_time="07:30"),
        Task("b", 10, fixed_time="09:15"),
    ]
    ordered = Scheduler(owner).sort_by_time(tasks)
    assert [t.title for t in ordered] == ["a", "b", "c"]


def test_sort_by_time_puts_flexible_tasks_last(owner):
    tasks = [Task("flex", 10), Task("fixed", 10, fixed_time="10:00")]
    ordered = Scheduler(owner).sort_by_time(tasks)
    assert [t.title for t in ordered] == ["fixed", "flex"]


def test_filter_tasks_by_pet_name(owner):
    tasks = [
        Task("walk", 30, pet_name="Mochi"),
        Task("play", 15, pet_name="Luna"),
        Task("feed", 10, pet_name="Mochi"),
    ]
    mochi = Scheduler(owner).filter_tasks(tasks, pet_name="Mochi")
    assert {t.title for t in mochi} == {"walk", "feed"}


def test_filter_tasks_by_completion_status(owner):
    done = Task("done", 10)
    done.mark_complete()
    pending = Task("pending", 10)
    sched = Scheduler(owner)
    assert [t.title for t in sched.filter_tasks([done, pending], completed=True)] == ["done"]
    assert [t.title for t in sched.filter_tasks([done, pending], completed=False)] == ["pending"]


def test_filter_tasks_combined(owner):
    tasks = [
        Task("a", 10, pet_name="Mochi"),
        Task("b", 10, pet_name="Mochi", completed=True),
        Task("c", 10, pet_name="Luna"),
    ]
    result = Scheduler(owner).filter_tasks(tasks, pet_name="Mochi", completed=False)
    assert [t.title for t in result] == ["a"]


# ---------------------------------------------------------------------------
# Recurring tasks (Step 3)
# ---------------------------------------------------------------------------


def test_next_occurrence_none_for_one_off():
    assert Task("walk", 30).next_occurrence() is None
    assert Task("walk", 30, frequency="none").next_occurrence() is None


def test_next_occurrence_daily_advances_one_day():
    task = Task("feed", 10, frequency="daily", due_date=date(2026, 6, 26))
    nxt = task.next_occurrence()
    assert nxt is not None
    assert nxt.due_date == date(2026, 6, 27)
    assert nxt.completed is False
    assert nxt.title == "feed" and nxt.frequency == "daily"


def test_next_occurrence_weekly_advances_one_week():
    task = Task("bath", 20, frequency="weekly", due_date=date(2026, 6, 26))
    nxt = task.next_occurrence()
    assert nxt.due_date == date(2026, 7, 3)


def test_complete_task_spawns_next_occurrence_on_pet():
    pet = Pet("Mochi")
    walk = Task("walk", 30, frequency="daily", due_date=date(2026, 6, 26))
    pet.add_task(walk)
    assert len(pet.tasks) == 1
    upcoming = pet.complete_task(walk)
    assert walk.completed is True
    assert len(pet.tasks) == 2  # next occurrence auto-added
    assert upcoming.due_date == date(2026, 6, 27)
    assert upcoming.pet_name == "Mochi"


def test_complete_task_no_spawn_for_one_off():
    pet = Pet("Luna")
    task = Task("nail trim", 10)  # frequency defaults to "none"
    pet.add_task(task)
    result = pet.complete_task(task)
    assert result is None
    assert len(pet.tasks) == 1


# ---------------------------------------------------------------------------
# Conflict detection (Step 4)
# ---------------------------------------------------------------------------


def test_detect_conflicts_flags_same_fixed_time(owner):
    tasks = [
        Task("meds", 10, fixed_time="09:00"),
        Task("feed", 10, fixed_time="09:00"),
        Task("walk", 30),  # flexible, ignored
    ]
    warnings = Scheduler(owner).detect_conflicts(tasks)
    assert len(warnings) == 1
    assert "09:00" in warnings[0]
    assert "meds" in warnings[0] and "feed" in warnings[0]


def test_detect_conflicts_none_when_times_differ(owner):
    tasks = [
        Task("meds", 10, fixed_time="09:00"),
        Task("feed", 10, fixed_time="10:00"),
    ]
    assert Scheduler(owner).detect_conflicts(tasks) == []


# ---------------------------------------------------------------------------
# Plan helpers
# ---------------------------------------------------------------------------


def test_plan_total_minutes():
    plan = Plan(
        scheduled=[
            ScheduledTask(Task("a", 30), "08:00", "08:30"),
            ScheduledTask(Task("b", 15), "08:30", "08:45"),
        ]
    )
    assert plan.total_minutes() == 45


def test_plan_summary_empty():
    assert Plan().summary() == "No tasks scheduled."


def test_plan_summary_lists_tasks():
    plan = Plan(
        scheduled=[ScheduledTask(Task("Walk", 30, Priority.HIGH), "08:00", "08:30")]
    )
    summary = plan.summary()
    assert "08:00-08:30" in summary
    assert "Walk" in summary
    assert "high" in summary