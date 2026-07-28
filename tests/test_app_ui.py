"""UI-level smoke and interaction tests for the Streamlit app."""

from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_FILE = Path(__file__).resolve().parents[1] / "app.py"


def _new_app_test(monkeypatch, tmp_path):
    """Run the app from an isolated cwd so data.json cannot affect test state."""
    monkeypatch.chdir(tmp_path)
    at = AppTest.from_file(str(APP_FILE))
    at.run(timeout=10)
    return at


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
    at.text_input[2].set_value("Mochi")
    at.button[2].click()
    at.run(timeout=10)

    # Task form appears with this pet as the available target.
    assert any("Added Mochi." == s.value for s in at.success)
    assert at.selectbox[1].label == "For which pet?"
    assert "Mochi" in at.selectbox[1].options


def test_invalid_owner_start_time_shows_error(monkeypatch, tmp_path):
    at = _new_app_test(monkeypatch, tmp_path)

    at.text_input[1].set_value("99:99")
    at.run(timeout=10)

    errors = [e.value for e in at.error]
    assert "Owner start time must be valid HH:MM (for example, 08:00)." in errors


def test_build_schedule_explains_what_it_does(monkeypatch, tmp_path):
    at = _new_app_test(monkeypatch, tmp_path)

    caption_text = "\n".join(c.value for c in at.caption)
    assert "This section turns your saved pets and tasks into a day plan." in caption_text
    assert "what gets scheduled or skipped" in caption_text
