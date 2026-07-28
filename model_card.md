# PawPal+ Model Card

## Overview

PawPal+ is a Streamlit-based pet care planning assistant. It helps users organize pet tasks, generate a daily plan, and ask AI questions about that plan using the current owner, pet, and task context.

This model card documents how AI is used in the project, how I collaborated with AI during development, what worked well, what did not, and what limitations remain.

## Intended Use

PawPal+ is intended for:

- planning pet care tasks,
- asking contextual questions about a pet's schedule,
- generating a grounded, human-readable summary of what should happen today.

It is not intended to replace veterinary advice or make medical decisions without human review.

## AI Behavior in the Project

The app sends a structured context to one of several AI providers and asks it to answer a planning question using only the supplied data. The system then checks the response for grounding and required planning details such as time, place, priority, and duration.

If the response is weak, missing required details, or the provider fails, the app falls back to a deterministic scheduler-based summary instead of showing a potentially misleading answer.

## Responsible-AI Collaboration

I used AI as a development assistant in three main ways:

- **Design critique:** I asked AI to review my class and scheduler design for missing relationships and weak spots.
- **Implementation help:** I used AI to discuss code patterns for sorting, scheduling, recurrence, and structured prompting.
- **Testing and refinement:** I asked AI to help draft tests and to suggest ways to simplify or improve specific functions.

### One helpful AI suggestion

A helpful suggestion was to make the assistant context more structured so the model would receive explicit fields like task title, place, time, priority, duration, status, and recurrence. That improved answer quality because the model had better input data and could stay grounded in the actual schedule.

### One flawed AI suggestion

A flawed suggestion was to trust a simpler direct sort on the raw time strings for scheduling output. That approach was technically convenient, but I kept the more explicit `parse_time`-based version because it better matches the meaning of the data and is safer if the input format changes.

## Data and Inputs

The assistant uses:

- owner information,
- pet information,
- task titles, durations, priorities, times, recurrence, and completion state,
- the current day being planned.

The system does not train on user data. It only uses the current session and locally stored project data files.

## Output Checks and Reliability

To reduce the chance of misleading results, the app includes:

- input validation for assistant questions,
- output guardrails that check whether responses mention known task titles and required planning details,
- provider failover if an AI service is unavailable,
- a deterministic fallback answer from the scheduler,
- automated evaluation checks in `ai_eval.py` and `tests/test_ai_reliability.py`.

### Testing Summary

The project currently shows reliable behavior in both automated tests and the AI
evaluation harness.

| Test Input | Evaluation Criteria | Result |
|---|---|---|
| `python -m pytest -q` | Core app, scheduler, UI smoke tests, and AI reliability checks should pass | `66/66 passed` |
| `python ai_eval.py` with grounded context | Answer should mention known task titles and required planning details | `PASS` |
| `python ai_eval.py` with missing details | Guardrail should flag weak responses and fall back safely | `PASS` |
| `python ai_eval.py` with ungrounded answer | Response should be rejected as not grounded in the plan | `PASS` |

Short summary: **66 out of 66 automated tests passed**, and **3 out of 3
reliability checks passed** in the evaluator. The AI performed well when the
context was complete and was safely redirected to fallback behavior when the
answer was missing required planning details or task grounding.

## Limitations

PawPal+ is useful for scheduling and explanation, but it has clear limits:

- It cannot guarantee that every AI answer is perfect or exhaustive.
- It depends on the quality of the user-provided task data.
- It is not a medical or emergency assistant.
- It may fall back to a local summary if the model output is incomplete or if a provider fails.
- The reliability checks look for grounded planning details, but they do not fully understand all possible forms of incorrect or unsafe advice.

## What I Learned

This project taught me that AI is most useful when it is part of a larger software system with constraints, checks, and fallback behavior. I also learned that the human developer has to remain responsible for system design, verification, and the final decision about whether an AI answer is acceptable.

## Evaluation Notes

I verified the project through:

- the main pytest suite,
- the AI reliability evaluator,
- manual UI runs in Streamlit,
- inspection of fallback and guardrail behavior.

The current implementation passed the test suite at the time this card was written.

## Reflection and Ethics

### Limitations and Biases

PawPal+ is limited by the quality and completeness of the task data the user
enters. If the owner omits a task, a priority, or a fixed time, the assistant
can only reason from incomplete context. The system also reflects the
assumptions built into the scheduling logic, such as prioritizing high-priority
tasks and using a greedy time-budget filter, which may not match every user's
preferences.

The AI providers themselves can also introduce bias or hallucination risk. Even
with guardrails, a model may overstate confidence, omit details, or produce a
response that sounds plausible but is not fully grounded in the schedule.

### Misuse and Prevention

This AI could be misused as if it were a veterinary or medical decision-maker.
That would be inappropriate because it is only a planning assistant and not a
licensed professional. To reduce that risk, the project makes its scope
explicit, uses grounded task context, and falls back to a deterministic
scheduler summary when the model output is weak, missing details, or not tied
to known tasks.

The app also uses input validation, provider failover, and output checks so it
does not blindly trust every response. Those guardrails reduce the chance that
someone sees a polished but unreliable answer and mistakes it for expert advice.

### What Surprised Me During Reliability Testing

The most surprising result was that the model could sound confident while still
missing important planning details. A response could mention a task in general
terms, but still fail the reliability check because it did not name the task,
place, time, priority, or duration clearly enough.

Another takeaway was that the fallback path is not a failure state; it is a
useful feature. When the AI provider failed or returned weak output, the
deterministic scheduler-based summary still gave the user something reliable to
act on.

### Collaboration With AI

I used AI as a collaborator throughout the project for design review,
implementation help, and test drafting. One helpful suggestion was structuring
the assistant context with explicit fields like task title, place, time,
priority, duration, status, and recurrence. That made the assistant's answers
more grounded and easier to verify.

One flawed suggestion was to sort task times directly as strings for scheduling.
That can work in some cases, but I kept the `parse_time`-based approach because
it is clearer, more robust, and less fragile if formatting changes later.
