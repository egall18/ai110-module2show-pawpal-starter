from ai_reliability import evaluate_answer_quality, extract_task_titles


def _context() -> str:
    return "\n".join(
        [
            "Tasks:",
            "- title=Morning walk; place=Park; time=08:00; priority=high; duration=30 min; status=not completed; repeats=daily",
            "- title=Feeding; place=Kitchen; time=09:00; priority=high; duration=10 min; status=not completed; repeats=daily",
        ]
    )


def test_extract_task_titles_reads_context_lines():
    assert extract_task_titles(_context()) == ["Morning walk", "Feeding"]


def test_evaluate_answer_quality_passes_for_grounded_complete_answer():
    answer = (
        "Morning walk should happen at time 08:00 in place Park. "
        "Its priority is high and duration is 30 min."
    )
    ok, reasons = evaluate_answer_quality(answer, _context())
    assert ok is True
    assert reasons == []


def test_evaluate_answer_quality_fails_when_not_grounded():
    answer = "Time 08:00, place home, priority high, duration 30 min."
    ok, reasons = evaluate_answer_quality(answer, _context())
    assert ok is False
    assert any("No known task title" in reason for reason in reasons)


def test_evaluate_answer_quality_fails_when_required_terms_missing():
    answer = "Morning walk sounds good."
    ok, reasons = evaluate_answer_quality(answer, _context())
    assert ok is False
    assert any("Missing required planning detail" in reason for reason in reasons)
