import streamlit as st
import json
import os
import urllib.error
import urllib.parse
import urllib.request

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


def _load_project_env(path=".env"):
    """Load simple KEY=VALUE pairs from a local .env file.

    This keeps API keys scoped to this project without requiring global shell
    profile changes. Existing environment variables win.
    """
    if not os.path.exists(path):
        return

    with open(path, encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                os.environ.setdefault(key, value)


_load_project_env()


def _build_pet_context(owner, pet, day_of_week):
    """Build a compact, structured context string for assistant questions."""
    tasks = list(pet.tasks)
    scheduler = Scheduler(owner)
    try:
        ordered = scheduler.sort_by_time(tasks)
    except ValueError:
        ordered = tasks

    plan = Scheduler(owner, tasks).build_plan(day_of_week=day_of_week)
    lines = [
        f"Owner: {owner.name}",
        f"Pet: {pet.name} ({pet.species})",
        f"Owner start time: {owner.start_time}",
        f"Owner available minutes: {owner.available_minutes}",
        f"Requested day: {day_of_week or 'Any day'}",
        "",
        "Tasks:",
    ]
    if not ordered:
        lines.append("- No tasks added for this pet.")
    for task in ordered:
        status = "completed" if task.completed else "not completed"
        lines.append(
            "- "
            f"title={task.title}; "
            f"place={task.place or 'unspecified'}; "
            f"time={task.fixed_time or 'flexible'}; "
            f"priority={task.priority.name.lower()}; "
            f"duration={task.duration_minutes} min; "
            f"status={status}; "
            f"repeats={task.frequency}"
        )

    lines.append("")
    lines.append("Scheduled plan:")
    if not plan.scheduled:
        lines.append("- No tasks could be scheduled.")
    for item in plan.scheduled:
        lines.append(
            "- "
            f"{item.start_time}-{item.end_time}: "
            f"{item.task.title} at {item.task.place or 'unspecified'} "
            f"({item.task.duration_minutes} min, {item.task.priority.name.lower()})"
        )

    if plan.skipped:
        lines.append("")
        lines.append("Skipped:")
        for skipped in plan.skipped:
            lines.append(f"- {skipped.task.title}: {skipped.reason}")

    return "\n".join(lines)


def _ask_openai_assistant(question, context_text):
    """Call OpenAI if OPENAI_API_KEY is available; return None when unavailable."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a pet care planning assistant. Answer using only "
                    "the provided data. Be specific about time, place, "
                    "priority, completed status, and duration. If something is "
                    "missing, say so plainly."
                ),
            },
            {
                "role": "user",
                "content": f"Question:\n{question}\n\nContext:\n{context_text}",
            },
        ],
        "temperature": 0.2,
    }

    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            return (
                "AI request failed (401): invalid OpenAI API key. "
                "Update OPENAI_API_KEY in your local .env, restart the app, "
                "and try again."
            )
        if exc.code == 429:
            return (
                "AI request failed (429): rate limit or quota reached. "
                "Please check your OpenAI usage/billing and retry."
            )
        return f"AI request failed ({exc.code}): request was rejected by OpenAI."
    except Exception as exc:
        return f"AI request failed: {exc}"


def _ask_claude_assistant(question, context_text):
    """Call Claude if CLAUDE_API_KEY is available; return None when unavailable."""
    api_key = os.getenv("CLAUDE_API_KEY", "").strip()
    if not api_key:
        return None

    model = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
    payload = {
        "model": model,
        "max_tokens": 1024,
        "system": (
            "You are a pet care planning assistant. Answer using only "
            "the provided data. Be specific about time, place, "
            "priority, completed status, and duration. If something is "
            "missing, say so plainly."
        ),
        "messages": [
            {
                "role": "user",
                "content": f"Question:\n{question}\n\nContext:\n{context_text}",
            }
        ],
    }

    request = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
        content = body.get("content", [])
        if content and "text" in content[0]:
            return content[0]["text"]
        return "AI request failed: Claude returned no text content."
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            return (
                "AI request failed (401): invalid Claude API key. "
                "Update CLAUDE_API_KEY in your local .env, restart the app, "
                "and try again."
            )
        if exc.code == 429:
            return (
                "AI request failed (429): rate limit or quota reached. "
                "Please check your Claude usage/billing and retry."
            )
        return f"AI request failed ({exc.code}): request was rejected by Claude."
    except Exception as exc:
        return f"AI request failed: {exc}"


def _ask_gemini_assistant(question, context_text):
    """Call Gemini if GEMINI_API_KEY is available; return None when unavailable."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None

    raw_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()

    def _normalize_model_name(name):
        clean = (name or "").strip()
        if clean.startswith("models/"):
            return clean.split("/", 1)[1]
        return clean

    # Try configured model first, then common fallbacks for key/project variance.
    candidates = [
        _normalize_model_name(raw_model) or "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-2.0-flash",
        "gemini-1.5-pro-latest",
    ]
    seen = set()
    model_candidates = []
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            model_candidates.append(candidate)

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            "You are a pet care planning assistant. Answer using only "
                            "the provided data. Be specific about time, place, "
                            "priority, completed status, and duration. If something is "
                            "missing, say so plainly.\n\n"
                            f"Question:\n{question}\n\nContext:\n{context_text}"
                        )
                    }
                ]
            }
        ],
        "generationConfig": {"temperature": 0.2},
    }

    had_404 = False
    for model in model_candidates:
        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{urllib.parse.quote(model)}:generateContent"
        )
        request = urllib.request.Request(
            f"{endpoint}?key={urllib.parse.quote(api_key)}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = json.loads(response.read().decode("utf-8"))
            candidates = body.get("candidates", [])
            if not candidates:
                return "AI request failed: Gemini returned no candidates."
            parts = candidates[0].get("content", {}).get("parts", [])
            text_chunks = [p.get("text", "") for p in parts if p.get("text")]
            if not text_chunks:
                return "AI request failed: Gemini returned an empty response."
            return "\n".join(text_chunks)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                had_404 = True
                continue
            if exc.code == 400:
                return (
                    "AI request failed (400): bad Gemini request. "
                    "Check GEMINI_MODEL and request configuration in .env."
                )
            if exc.code == 401:
                return (
                    "AI request failed (401): invalid Gemini API key. "
                    "Update GEMINI_API_KEY in your local .env, restart the app, "
                    "and try again."
                )
            if exc.code == 403:
                return (
                    "AI request failed (403): Gemini API access denied. "
                    "Check API enablement and project permissions."
                )
            if exc.code == 429:
                return (
                    "AI request failed (429): rate limit or quota reached. "
                    "Please check your Google AI usage/billing and retry."
                )
            return f"AI request failed ({exc.code}): request was rejected by Gemini."
        except Exception as exc:
            return f"AI request failed: {exc}"

    if had_404:
        tried = ", ".join(model_candidates)
        return (
            "AI request failed (404): no supported Gemini model found for this key/project. "
            f"Tried: {tried}. Set GEMINI_MODEL in .env to a model available to your account."
        )
    return "AI request failed: unable to reach Gemini model endpoint."


def _ask_ai_assistant(question, context_text):
    """Dispatch to configured AI provider; auto-detect if not explicitly set."""
    provider = os.getenv("AI_PROVIDER", "").strip().lower()

    if provider == "gemini":
        if not os.getenv("GEMINI_API_KEY", "").strip():
            return (
                "Gemini is selected, but GEMINI_API_KEY is missing in .env. "
                "Add GEMINI_API_KEY, restart the app, and try again."
            )
        return _ask_gemini_assistant(question, context_text)

    if provider == "openai":
        if not os.getenv("OPENAI_API_KEY", "").strip():
            return (
                "OpenAI is selected, but OPENAI_API_KEY is missing in .env. "
                "Add OPENAI_API_KEY, restart the app, and try again."
            )
        return _ask_openai_assistant(question, context_text)

    if provider == "claude":
        if not os.getenv("CLAUDE_API_KEY", "").strip():
            return (
                "Claude is selected, but CLAUDE_API_KEY is missing in .env. "
                "Add CLAUDE_API_KEY, restart the app, and try again."
            )
        return _ask_claude_assistant(question, context_text)

    # Auto-detect: try Gemini first, then OpenAI, then Claude.
    if os.getenv("GEMINI_API_KEY", "").strip():
        return _ask_gemini_assistant(question, context_text)
    if os.getenv("OPENAI_API_KEY", "").strip():
        return _ask_openai_assistant(question, context_text)
    if os.getenv("CLAUDE_API_KEY", "").strip():
        return _ask_claude_assistant(question, context_text)
    return None


def _local_assistant_answer(owner, pet, day_of_week):
    """Fallback answer when no API key is configured."""
    plan = Scheduler(owner, list(pet.tasks)).build_plan(day_of_week=day_of_week)
    lines = [f"Planned day for {pet.name}:"]
    if not plan.scheduled:
        lines.append("- No tasks could be scheduled with current constraints.")
    for item in plan.scheduled:
        lines.append(
            "- "
            f"{item.start_time}-{item.end_time}: {item.task.title} "
            f"at {item.task.place or 'unspecified'} | "
            f"priority={item.task.priority.name.lower()} | "
            f"duration={item.task.duration_minutes} min | "
            f"status={'completed' if item.task.completed else 'not completed'}"
        )

    if plan.skipped:
        lines.append("Skipped tasks:")
        for skipped in plan.skipped:
            lines.append(f"- {skipped.task.title}: {skipped.reason}")

    lines.append("")
    lines.append(
        "Tip: set GEMINI_API_KEY, OPENAI_API_KEY, or CLAUDE_API_KEY in your local .env "
        "to get natural-language AI responses to your custom questions."
    )
    return "\n".join(lines)

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
        task_place = st.text_input("Place (optional)", value="")
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
                        place=task_place.strip(),
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
                    "Place": t.place or "—",
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

            new_place = st.text_input("Place (optional)", value=task.place)

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
                task.place = new_place.strip()
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

st.subheader("Ask AI Assistant")
dogs = [p for p in st.session_state.pets if p.species.lower() == "dog"]
if not dogs:
    st.caption("Add at least one dog to ask for a dog-specific plan.")
else:
    selected_dog_name = st.selectbox(
        "Which dog?",
        [d.name for d in dogs],
        key="assistant_dog_select",
    )
    assistant_day = st.selectbox(
        "Assistant day",
        ["Any day", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        index=0,
        key="assistant_day_select",
    )
    assistant_question = st.text_area(
        "Question for assistant",
        value=(
            "What is the best plan for my dog today? Include time, place, "
            "priority, completion status, and duration."
        ),
        height=120,
    )
    if st.button("Ask assistant"):
        selected_dog = next(d for d in dogs if d.name == selected_dog_name)
        day = None if assistant_day == "Any day" else assistant_day
        context_text = _build_pet_context(st.session_state.owner, selected_dog, day)
        with st.spinner("Preparing assistant response..."):
            ai_answer = _ask_ai_assistant(assistant_question.strip(), context_text)
        if ai_answer is None:
            st.info(_local_assistant_answer(st.session_state.owner, selected_dog, day))
        elif ai_answer.startswith("AI request failed (429)"):
            st.warning(ai_answer)
            st.info(_local_assistant_answer(st.session_state.owner, selected_dog, day))
        else:
            st.markdown(ai_answer)

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
                        "Place": s.task.place or "—",
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