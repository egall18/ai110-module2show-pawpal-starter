import streamlit as st

from pawpal_system import Owner, Pet, Priority, Scheduler, Task

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

# ---------------------------------------------------------------------------
# Session "vault": create the Owner and the list of Pets once, reuse on rerun.
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan")
if "pets" not in st.session_state:
    st.session_state.pets = []

# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------
st.subheader("Owner")
owner_name = st.text_input("Owner name", value=st.session_state.owner.name)
oc1, oc2 = st.columns(2)
with oc1:
    start_time = st.text_input("Day starts at (HH:MM)", value="08:00")
with oc2:
    available_minutes = st.number_input(
        "Available minutes today", min_value=0, max_value=1440, value=120, step=15
    )

# Keep the persisted Owner's editable fields in sync with the inputs each run.
st.session_state.owner.name = owner_name
st.session_state.owner.start_time = start_time
st.session_state.owner.available_minutes = int(available_minutes)

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
            pet = next(p for p in st.session_state.pets if p.name == target_pet)
            pet.add_task(
                Task(
                    title=task_title,
                    duration_minutes=int(duration),
                    priority=PRIORITY_MAP[priority],
                    fixed_time=fixed_time.strip() or None,
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
                for t in view.sort_by_time(p.tasks)
            ]
        )
if st.session_state.pets and not any_tasks:
    st.caption("No tasks yet — add one above.")

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