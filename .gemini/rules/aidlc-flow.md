# AI-DLC Working Flow

The AI should follow an AI-Driven Development Lifecycle for all non-trivial tasks in this project.

## 1. Analyze and Clarify

- Start by restating the goal in your own words.
- Call out important constraints, assumptions, and risks.
- If requirements are unclear or there are multiple valid approaches, briefly outline the options and pick one with a short justification.

## 2. Plan

- Break the work into clear, ordered steps.
- Group related changes into batches that can be implemented and verified together.
- Keep the plan lightweight but concrete enough to guide implementation.

## 3. Develop

- Implement changes step by step, following the plan.
- Prefer small, incremental changes over one large, risky change.
- Keep responsibilities separated (e.g., routing, validation, business logic, persistence).
- When modifying existing code, preserve behavior unless a change is explicitly requested.

## 4. Review and Self-Check

- After implementing a batch of changes:
  - Re-read the modified code and check for edge cases.
  - Verify that types and schemas remain consistent across layers.
  - Ensure error handling and logging are appropriate.
- When tests or linting are available, run them and address failures.

## 5. Summarize and Hand Off

- Provide a short, high-signal summary of:
  - Key changes made.
  - Any important trade-offs or limitations.
  - How the changes can be tested or validated by a human.
- If follow-up work is discovered, capture it as clear todos rather than silently ignoring it.

