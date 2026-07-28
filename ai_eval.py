"""Small reliability harness for PawPal+ assistant output checks.

Run:
    python ai_eval.py
"""

from ai_reliability import evaluate_answer_quality


def _sample_context() -> str:
    return "\n".join(
        [
            "Owner: Jordan",
            "Pet: Mochi (dog)",
            "",
            "Tasks:",
            "- title=Morning walk; place=Park; time=08:00; priority=high; duration=30 min; status=not completed; repeats=daily",
            "- title=Feeding; place=Kitchen; time=09:00; priority=high; duration=10 min; status=not completed; repeats=daily",
        ]
    )


def main() -> None:
    context_text = _sample_context()
    cases = [
        {
            "name": "good_answer",
            "answer": (
                "Start with Morning walk at time 08:00 in the place Park. "
                "Its priority is high and duration is 30 minutes."
            ),
            "expected": True,
        },
        {
            "name": "missing_required_details",
            "answer": "Do a quick walk and feeding soon.",
            "expected": False,
        },
        {
            "name": "not_grounded_in_task_titles",
            "answer": (
                "Time is 08:00, place is home, priority high, duration 30 minutes, "
                "start with exercise."
            ),
            "expected": False,
        },
    ]

    passed = 0
    for case in cases:
        ok, reasons = evaluate_answer_quality(case["answer"], context_text)
        matches = ok == case["expected"]
        status = "PASS" if matches else "FAIL"
        print(f"[{status}] {case['name']}")
        if reasons:
            for reason in reasons:
                print(f"  - {reason}")
        if matches:
            passed += 1

    print(f"\nSummary: {passed}/{len(cases)} checks matched expected behavior.")


if __name__ == "__main__":
    main()
