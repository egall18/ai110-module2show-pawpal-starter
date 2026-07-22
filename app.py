import streamlit as st

from pawpal_system import (
    Owner,
    Pet,
    Priority,
    Scheduler,
    Task,
    load_from_json,
    parse_time,
    save_to_json,
)

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to PawPal+ — a pet care planning assistant.

Enter your owner info, add one or more pets, give each pet some care tasks,
then generate a daily plan. The scheduling logic lives in `pawpal_system.py`;
this page is the interactive demo.
"""
)

with st.expander("Scenario", expanded=False):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.
"""
    )

st.divider()

PRIORITY_MAP = {"low": Priority.LOW, "medium": Priority.MEDIUM, "high": Priority.HIGH}
DATA_FILE = "data.json"

# ---------------------------------------------------------------------------
# Session "vault": create the Owner and the list of Pets once, reuse on rerun.
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan")
if "pets" not in st.session_state:
    st.session_state.pets = []
if "loaded_data_once" not in st.session_state:
    st.session_state.loaded_data_once = False

# Hydrate from disk once per browser session if data exists.
if not st.session_state.loaded_data_once:
    try:
        owner, pets = load_from_json(DATA_FILE)
        st.session_state.owner = owner
        st.session_state.pets = pets
        st.session_state.loaded_data_once = True
        st.info("Loaded saved data from data.json")
    except FileNotFoundError:
        st.session_state.loaded_data_once = True
    except (ValueError, KeyError, TypeError) as exc:
        st.session_state.loaded_data_once = True
        st.warning(f"Could not load data.json: {exc}")

# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------
st.subheader("Owner")
owner_name = st.text_input("Owner name", value=st.session_state.owner.name)
oc1, oc2 = st.columns(2)
with oc1:
    start_time = st.text_input(
        "Day starts at (HH:MM)", value=st.session_state.owner.start_time
    )
with oc2:
    available_minutes = st.number_input(
        "Available minutes today",
        min_value=0,
        max_value=1440,
        value=st.session_state.owner.available_minutes,
        step=15,
    )

# Keep the persisted Owner's editable fields in sync with the inputs each run.
st.session_state.owner.name = owner_name
st.session_state.owner.available_minutes = int(available_minutes)
start_time_valid = True
try:
    parse_time(start_time.strip())
except ValueError:
    start_time_valid = False
    st.error("Owner start time must be valid HH:MM (for example, 08:00).")
if start_time_valid:
    st.session_state.owner.start_time = start_time.strip()

dc1, dc2 = st.columns(2)
with dc1:
    if st.button("Save data"):
        save_to_json(DATA_FILE, st.session_state.owner, st.session_state.pets)
        st.success("Saved owner, pets, and tasks to data.json")
with dc2:
    if st.button("Reload data"):
        try:
            owner, pets = load_from_json(DATA_FILE)
            st.session_state.owner = owner
            st.session_state.pets = pets
            st.success("Reloaded owner, pets, and tasks from data.json")
            st.rerun()
        except FileNotFoundError:
            st.warning("No data.json found yet. Use Save data first.")
        except (ValueError, KeyError, TypeError) as exc:
            st.error(f"Failed to reload data.json: {exc}")

st.divider()

# ---------------------------------------------------------------------------
# Add a Pet  ->  handled by the Pet constructor, stored in the session vault
# ---------------------------------------------------------------------------
st.subheader("Add a Pet")
with st.form("add_pet_form", clear_on_submit=True):
    new_pet_name = st.text_input("Pet name", value="")
    new_pet_species = st.selectbox("Species", ["dog", "cat", "other"])
    if st.form_submit_button("Add pet"):
        if new_pet_name.strip():
            st.session_state.pets.append(
                Pet(name=new_pet_name.strip(), species=new_pet_species)
            )
            st.success(f"Added {new_pet_name.strip()}.")
        else:
            st.warning("Give the pet a name first.")

if st.session_state.pets:
    st.write(
        "Your pets: "
        + ", ".join(f"{p.name} ({p.species})" for p in st.session_state.pets)
    )
else:
    st.info("No pets yet. Add one above.")

st.divider()

# ---------------------------------------------------------------------------
# Schedule a Task  ->  handled by Pet.add_task()
# ---------------------------------------------------------------------------
st.subheader("Schedule a Task")
if not st.session_state.pets:
    st.info("Add a pet before adding tasks.")
else:
    with st.form("add_task_form", clear_on_submit=True):
        target_pet = st.selectbox(
            "For which pet?", [p.name for p in st.session_state.pets]
        )
        task_title = st.text_input("Task title", value="Morning walk")
        tc1, tc2 = st.columns(2)
        with tc1:
            duration = st.number_input(
                "Duration (minutes)", min_value=1, max_value=240, value=20
            )
        with tc2:
            priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
        tc3, tc4 = st.columns(2)
        with tc3:
            fixed_time = st.text_input(
                "Fixed time (optional, HH:MM)",
                value="",
                help="Leave blank for a flexible task the scheduler can place anywhere.",
            )
        with tc4:
            frequency = st.selectbox(
                "Repeats", ["none", "daily", "weekly"],
                help="Recurring tasks regenerate for the next day/week when completed.",
            )
        if st.form_submit_button("Add task"):
            clean_fixed = fixed_time.strip() or None
            fixed_valid = True
            if clean_fixed is not None:
                try:
                    parse_time(clean_fixed)
                except ValueError:
                    fixed_valid = False
                    st.warning("Fixed time must be valid HH:MM (for example, 09:30).")
            if fixed_valid:
                pet = next(p for p in st.session_state.pets if p.name == target_pet)
                pet.add_task(
                    Task(
                        title=task_title,
                        duration_minutes=int(duration),
                        priority=PRIORITY_MAP[priority],
                        fixed_time=clean_fixed,
                        frequency=frequency,
                    )
                )
                st.success(f"Added '{task_title}' for {pet.name}.")

# A single scheduler instance powers the display-layer algorithms below.
view = Scheduler(st.session_state.owner)
all_tasks = [t for p in st.session_state.pets for t in p.tasks]

# Conflict warnings (detect_conflicts) — shown up front so the owner sees a
# clash before relying on the plan.
conflicts = view.detect_conflicts(all_tasks)
for warning in conflicts:
    st.warning(warning.replace("WARNING: ", ""))

# Show each pet's tasks, sorted chronologically by time (sort_by_time).
any_tasks = False
for p in st.session_state.pets:
    if p.tasks:
        any_tasks = True
        st.write(f"**{p.name}'s tasks** (sorted by time)")
        try:
            sorted_tasks = view.sort_by_time(p.tasks)
        except ValueError as exc:
            st.error(f"Could not sort {p.name}'s tasks by time: {exc}")
            sorted_tasks = p.tasks
        st.table(
            [
                {
                    "Time": t.fixed_time or "flexible",
                    "Task": t.title,
                    "Duration": t.duration_minutes,
                    "Priority": t.priority.name.lower(),
                    "Repeats": t.frequency,
                    "Done": "✓" if t.completed else "",
                }
                for t in sorted_tasks
            ]
        )
if st.session_state.pets and not any_tasks:
    st.caption("No tasks yet — add one above.")

# Edit/delete an existing task.
editable = [
    (pet, idx, task)
    for pet in st.session_state.pets
    for idx, task in enumerate(pet.tasks)
]
if editable:
    with st.expander("Edit or delete a task"):
        task_idx = st.selectbox(
            "Choose a task",
            range(len(editable)),
            format_func=lambda i: (
                f"{editable[i][0].name}: {editable[i][2].title} "
                f"({editable[i][2].duration_minutes} min)"
            ),
        )
        pet, idx, task = editable[task_idx]

        with st.form("edit_task_form"):
            new_title = st.text_input("Title", value=task.title)
            ec1, ec2 = st.columns(2)
            with ec1:
                new_duration = st.number_input(
                    "Duration (minutes)",
                    min_value=1,
                    max_value=240,
                    value=int(task.duration_minutes),
                    step=1,
                )
            with ec2:
                priority_options = ["low", "medium", "high"]
                current_priority = task.priority.name.lower()
                new_priority = st.selectbox(
                    "Priority",
                    priority_options,
                    index=priority_options.index(current_priority),
                )

            ec3, ec4 = st.columns(2)
            with ec3:
                new_fixed_time = st.text_input(
                    "Fixed time (optional, HH:MM)",
                    value=task.fixed_time or "",
                )
            with ec4:
                new_frequency = st.selectbox(
                    "Repeats",
                    ["none", "daily", "weekly"],
                    index=["none", "daily", "weekly"].index(task.frequency),
                )

            save_changes = st.form_submit_button("Save changes")
            delete_task = st.form_submit_button("Delete task")

        if save_changes:
            clean_fixed = new_fixed_time.strip() or None
            edit_fixed_valid = True
            if clean_fixed is not None:
                try:
                    parse_time(clean_fixed)
                except ValueError:
                    edit_fixed_valid = False
                    st.warning("Fixed time must be valid HH:MM (for example, 09:30).")
            if edit_fixed_valid:
                task.title = new_title.strip() or task.title
                task.duration_minutes = int(new_duration)
                task.priority = PRIORITY_MAP[new_priority]
                task.fixed_time = clean_fixed
                task.frequency = new_frequency
                st.success(f"Updated '{task.title}' for {pet.name}.")
                st.rerun()

        if delete_task:
            removed_title = pet.tasks[idx].title
            del pet.tasks[idx]
            st.success(f"Deleted '{removed_title}' for {pet.name}.")
            st.rerun()

# Mark a task complete -> uses Pet.complete_task() (recurring tasks regenerate).
incomplete = [(p, t) for p in st.session_state.pets for t in p.tasks if not t.completed]
if incomplete:
    with st.expander("Mark a task complete"):
        idx = st.selectbox(
            "Which task did you finish?",
            range(len(incomplete)),
            format_func=lambda i: f"{incomplete[i][0].name}: {incomplete[i][1].title}",
        )
        if st.button("Mark complete"):
            pet, task = incomplete[idx]
            upcoming = pet.complete_task(task)
            if upcoming is not None:
                st.success(
                    f"Completed '{task.title}'. A new {task.frequency} occurrence "
                    f"was created (due {upcoming.due_date})."
                )
            else:
                st.success(f"Completed '{task.title}'.")

st.divider()

# ---------------------------------------------------------------------------
# Build Schedule  ->  gather every pet's tasks and run the Scheduler
# ---------------------------------------------------------------------------
st.subheader("Build Schedule")
day_of_week = st.selectbox(
    "Plan for which day?",
    ["Any day", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    index=0,
)

if st.button("Generate schedule"):
    if not start_time_valid:
        st.warning("Fix owner start time first (use HH:MM).")
        st.stop()
    if not all_tasks:
        st.warning("Add at least one task first.")
    else:
        # Re-surface any conflicts right next to the plan.
        for warning in view.detect_conflicts(all_tasks):
            st.warning(warning.replace("WARNING: ", ""))

        day = None if day_of_week == "Any day" else day_of_week
        plan = Scheduler(st.session_state.owner, all_tasks).build_plan(day_of_week=day)

        st.markdown("### 🗓️ Today's Plan")
        if plan.scheduled:
            st.table(
                [
                    {
                        "Start": s.start_time,
                        "End": s.end_time,
                        "Task": s.task.title,
                        "Pet": s.task.pet_name or "—",
                        "Priority": s.task.priority.name.lower(),
                        "Why": s.reason,
                    }
                    for s in plan.scheduled
                ]
            )
            st.success(
                f"Scheduled {len(plan.scheduled)} task(s) using "
                f"{plan.total_minutes()} of "
                f"{st.session_state.owner.available_minutes} available minutes."
            )
        else:
            st.info("Nothing could be scheduled with the current constraints.")

        if plan.skipped:
            st.markdown("### ⏭️ Not Scheduled")
            for sk in plan.skipped:
                st.write(f"- **{sk.task.title}** — {sk.reason}")

        with st.expander("Plan explanation"):
            st.text(plan.explanation)