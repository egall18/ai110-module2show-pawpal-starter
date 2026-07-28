"""Reliability helpers for AI assistant outputs.

These functions are pure so they can be reused by the UI and tested directly.
"""

from typing import List, Tuple


REQUIRED_TERMS = ("time", "place", "priority", "duration")


def extract_task_titles(context_text: str) -> List[str]:
    """Extract task titles from context lines emitted by _build_pet_context.

    Expected line shape:
    - title=Morning walk; place=Park; time=08:00; ...
    """
    titles: List[str] = []
    for raw in context_text.splitlines():
        line = raw.strip()
        if not line.startswith("- title="):
            continue
        fragment = line[len("- title=") :]
        title = fragment.split(";", 1)[0].strip()
        if title:
            titles.append(title)
    return titles


def evaluate_answer_quality(answer_text: str, context_text: str) -> Tuple[bool, List[str]]:
    """Return (passes, reasons) for a grounded assistant answer.

    Criteria:
    - Must include at least one known task title when tasks exist.
    - Must include all required planning terms (time/place/priority/duration).
    """
    reasons: List[str] = []
    answer_lower = (answer_text or "").lower()

    titles = extract_task_titles(context_text)
    if titles:
        has_title = any(title.lower() in answer_lower for title in titles)
        if not has_title:
            reasons.append("No known task title from context was mentioned.")

    missing_terms = [term for term in REQUIRED_TERMS if term not in answer_lower]
    if missing_terms:
        reasons.append(
            "Missing required planning detail(s): " + ", ".join(missing_terms)
        )

    return (len(reasons) == 0, reasons)
