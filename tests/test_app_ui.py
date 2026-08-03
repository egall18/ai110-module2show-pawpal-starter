"""UI-level smoke and interaction tests for the Streamlit app."""

from datetime import date
from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_FILE = Path(__file__).resolve().parents[1] / "app.py"


def _new_app_test(monkeypatch, tmp_path):
    """Run the app from an isolated cwd so data.json cannot affect test state."""
    monkeypatch.chdir(tmp_path)
    at = AppTest.from_file(str(APP_FILE))
    at.run(timeout=10)
    return at


def _first_by_label(widgets, label):
    return next(w for w in widgets if w.label == label)


def _first_button(widgets, label):
    return next(b for b in widgets if b.label == label)


def test_app_renders_core_sections(monkeypatch, tmp_path):
    at = _new_app_test(monkeypatch, tmp_path)
    hero_text = "\n".join(m.value for m in at.markdown)
    assert "🐾 PawPal+" in hero_text
    subheaders = [s.value for s in at.subheader]
    assert "Owner" in subheaders
    assert "Add a Pet" in subheaders
    assert "Build Schedule" in subheaders


def test_add_pet_updates_task_target_options(monkeypatch, tmp_path):
    at = _new_app_test(monkeypatch, tmp_path)

    # Fill and submit the add-pet form.
    _first_by_label(at.text_input, "Pet name").set_value("Mochi")
    _first_button(at.button, "Add pet").click()
    at.run(timeout=10)

    # Task form appears with this pet as the available target.
    assert any("Added Mochi." == s.value for s in at.success)
    assert _first_by_label(at.selectbox, "For which pet?").label == "For which pet?"
    assert "Mochi" in _first_by_label(at.selectbox, "For which pet?").options


def test_invalid_owner_start_time_shows_error(monkeypatch, tmp_path):
    at = _new_app_test(monkeypatch, tmp_path)

    _first_by_label(at.text_input, "Day starts at (HH:MM)").set_value("99:99")
    at.run(timeout=10)

    errors = [e.value for e in at.error]
    assert "Owner start time must be valid HH:MM (for example, 08:00)." in errors


def test_build_schedule_explains_what_it_does(monkeypatch, tmp_path):
    at = _new_app_test(monkeypatch, tmp_path)

    caption_text = "\n".join(c.value for c in at.caption)
    assert "This section turns your saved pets and tasks into a day plan." in caption_text
    assert "what gets scheduled or skipped" in caption_text

    selectbox_labels = [s.label for s in at.selectbox]
    assert "Plan for which day?" in selectbox_labels
    assert "Plan scope" in selectbox_labels
    assert "Minimum priority" in selectbox_labels
    assert any(sl.label == "Buffer between tasks (min)" for sl in at.slider)


def test_assistant_pet_dropdown_includes_other_species(monkeypatch, tmp_path):
    at = _new_app_test(monkeypatch, tmp_path)

    # Add a pet with species "other".
    _first_by_label(at.text_input, "Pet name").set_value("Nibbles")
    _first_by_label(at.selectbox, "Species").set_value("other")
    _first_button(at.button, "Add pet").click()
    at.run(timeout=10)

    # Assistant picker should be species-agnostic and include this pet.
    assistant_select = next(
        sb for sb in at.selectbox if sb.label == "Which pet?"
    )
    assert "Nibbles" in assistant_select.options


def test_available_days_drive_day_picker(monkeypatch, tmp_path):
    at = _new_app_test(monkeypatch, tmp_path)

    _first_by_label(at.date_input, "Pick available date").set_value(date(2026, 8, 3))
    _first_button(at.button, "Add available date").click()
    at.run(timeout=10)

    _first_by_label(at.date_input, "Pick available date").set_value(date(2026, 8, 5))
    _first_button(at.button, "Add available date").click()
    at.run(timeout=10)

    plan_day = _first_by_label(at.selectbox, "Plan for which day?")
    assert plan_day.options == ["Any day", "Mon", "Wed"]


def test_blocks_duplicate_fixed_time_task_for_same_pet(monkeypatch, tmp_path):
    at = _new_app_test(monkeypatch, tmp_path)

    _first_by_label(at.text_input, "Pet name").set_value("Mochi")
    _first_button(at.button, "Add pet").click()
    at.run(timeout=10)

    _first_by_label(at.selectbox, "For which pet?").set_value("Mochi")
    _first_by_label(at.text_input, "Fixed time (optional, HH:MM)").set_value("09:00")
    _first_by_label(at.multiselect, "Task days").set_value(["Mon"])
    _first_button(at.button, "Add task").click()
    at.run(timeout=10)

    _first_by_label(at.selectbox, "For which pet?").set_value("Mochi")
    _first_by_label(at.text_input, "Fixed time (optional, HH:MM)").set_value("09:00")
    _first_by_label(at.multiselect, "Task days").set_value(["Mon"])
    _first_button(at.button, "Add task").click()
    at.run(timeout=10)

    warnings = [w.value for w in at.warning]
    assert any("Duplicate task:" in msg for msg in warnings)


def test_blocks_same_time_across_pets(monkeypatch, tmp_path):
    at = _new_app_test(monkeypatch, tmp_path)

    _first_by_label(at.text_input, "Pet name").set_value("Mochi")
    _first_button(at.button, "Add pet").click()
    at.run(timeout=10)

    _first_by_label(at.text_input, "Pet name").set_value("Luna")
    _first_button(at.button, "Add pet").click()
    at.run(timeout=10)

    _first_by_label(at.selectbox, "For which pet?").set_value("Mochi")
    _first_by_label(at.text_input, "Fixed time (optional, HH:MM)").set_value("10:00")
    _first_by_label(at.multiselect, "Task days").set_value(["Tue"])
    _first_button(at.button, "Add task").click()
    at.run(timeout=10)

    _first_by_label(at.selectbox, "For which pet?").set_value("Luna")
    _first_by_label(at.text_input, "Fixed time (optional, HH:MM)").set_value("10:00")
    _first_by_label(at.multiselect, "Task days").set_value(["Tue"])
    _first_button(at.button, "Add task").click()
    at.run(timeout=10)

    warnings = [w.value for w in at.warning]
    assert any("Time conflict:" in msg for msg in warnings)
